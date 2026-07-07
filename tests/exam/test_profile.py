"""
Tests for Exam Sprint profile store.

Verifies profile read/write, mastery compatibility, diagnosis init, and reset.
Run with: pytest tests/exam/test_profile.py -v
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_profile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect profile storage to a temp directory for test isolation."""
    exam_dir = tmp_path / "exam_sprint"
    exam_dir.mkdir()

    # Use env var to redirect runtime home
    monkeypatch.setenv("DEEPTUTOR_HOME", str(tmp_path))
    yield tmp_path


# ── load_profile / save_profile ─────────────────────────────────────────────


def test_load_profile_defaults():
    """load_profile returns defaults when no file exists."""
    from deeptutor.exam.profile import load_profile

    profile = load_profile()
    assert profile["exam_name"] == ""
    assert profile["knowledge_points"] == []
    assert profile["diagnosis"] is None


def test_save_and_load_profile():
    """Round-trip save/load preserves data."""
    from deeptutor.exam.profile import load_profile, save_profile

    profile = {
        "exam_name": "test exam",
        "created_at": "2026-01-01T00:00:00",
        "last_updated": "",
        "knowledge_points": [
            {"name": "TCP", "chapter": "transport", "score": 0.8},
        ],
        "diagnosis": None,
    }
    save_profile(profile)

    loaded = load_profile()
    assert loaded["exam_name"] == "test exam"
    assert len(loaded["knowledge_points"]) == 1
    assert loaded["knowledge_points"][0]["name"] == "TCP"
    assert loaded["last_updated"] != ""


# ── load_mastery (compatibility) ────────────────────────────────────────────


def test_load_mastery_empty():
    """load_mastery returns empty list when no profile exists."""
    from deeptutor.exam.profile import load_mastery

    assert load_mastery() == []


def test_load_mastery_from_profile():
    """load_mastery reads from profile.json knowledge_points."""
    from deeptutor.exam.profile import load_mastery, save_profile

    profile = {
        "exam_name": "test",
        "created_at": "",
        "last_updated": "",
        "knowledge_points": [
            {"name": "TCP", "chapter": "L4", "score": 0.7, "last_surface": "quiz"},
            {"name": "UDP", "chapter": "L4", "score": 0.4, "last_surface": "chat"},
        ],
        "diagnosis": None,
    }
    save_profile(profile)

    entries = load_mastery()
    assert len(entries) == 2
    assert entries[0]["knowledge_point"] == "TCP"
    assert entries[0]["score"] == 0.7
    assert entries[0]["surface"] == "quiz"
    assert entries[1]["knowledge_point"] == "UDP"
    assert entries[1]["surface"] == "chat"


# ── update_mastery_score ────────────────────────────────────────────────────


def test_update_mastery_new_entry():
    """New knowledge point creates entry with raw score (no EMA)."""
    from deeptutor.exam.profile import load_mastery, update_mastery_score

    result = update_mastery_score("TCP", 0.6, surface="quiz")
    assert len(result) == 1
    assert result[0]["knowledge_point"] == "TCP"
    assert result[0]["score"] == 0.6


def test_update_mastery_ema_blend():
    """Existing entry uses EMA: 0.7 * old + 0.3 * new."""
    from deeptutor.exam.profile import update_mastery_score, save_profile, load_profile

    # Seed an entry with score 0.5
    profile = {
        "exam_name": "test",
        "created_at": "",
        "last_updated": "",
        "knowledge_points": [
            {"name": "TCP", "chapter": "", "score": 0.5, "total_questions": 0,
             "correct": 0, "error_types": [], "last_practiced": "",
             "practice_count": 0, "last_surface": "quiz"},
        ],
        "diagnosis": None,
    }
    save_profile(profile)

    result = update_mastery_score("TCP", 0.8, surface="quiz")
    expected = round(0.7 * 0.5 + 0.3 * 0.8, 3)
    assert result[0]["score"] == expected


def test_update_mastery_clamps():
    """Score is clamped to [0, 1] before EMA blend."""
    from deeptutor.exam.profile import update_mastery_score

    # New entry with out-of-range score — clamped to 1.0 before write
    result = update_mastery_score("CLAMPTARGET", 1.5)
    clamp_entry = next(e for e in result if e["knowledge_point"] == "CLAMPTARGET")
    assert clamp_entry["score"] == 1.0

    # Verify the score stayed in [0, 1] — the key invariant
    assert 0.0 <= clamp_entry["score"] <= 1.0


# ── init_from_diagnosis ─────────────────────────────────────────────────────


def test_init_from_diagnosis():
    """Diagnosis initializes profile with aggregated knowledge points."""
    from deeptutor.exam.profile import init_from_diagnosis, load_profile

    diagnosis = {
        "total_questions": 3,
        "questions": [
            {"question_id": "q1", "question": "What is TCP?",
             "correct_answer": "Transport protocol", "user_answer": "Transport protocol",
             "is_correct": True, "error_type": "", "knowledge_point": "TCP basics"},
            {"question_id": "q2", "question": "TCP vs UDP?",
             "correct_answer": "Reliable vs unreliable", "user_answer": "Same thing",
             "is_correct": False, "error_type": "concept_confusion",
             "knowledge_point": "TCP basics"},
            {"question_id": "q3", "question": "What is UDP?",
             "correct_answer": "Unreliable protocol", "user_answer": "Unreliable protocol",
             "is_correct": True, "error_type": "", "knowledge_point": "UDP basics"},
        ],
        "overall_score": 0.67,
        "weak_points": ["TCP basics"],
        "strong_points": ["UDP basics"],
    }

    profile = init_from_diagnosis("Network Exam", diagnosis)

    assert profile["exam_name"] == "Network Exam"
    assert len(profile["knowledge_points"]) == 2

    tcp_kp = next(kp for kp in profile["knowledge_points"] if kp["name"] == "TCP basics")
    assert tcp_kp["total_questions"] == 2
    assert tcp_kp["correct"] == 1
    assert tcp_kp["score"] == 0.5
    assert "concept_confusion" in tcp_kp["error_types"]

    udp_kp = next(kp for kp in profile["knowledge_points"] if kp["name"] == "UDP basics")
    assert udp_kp["score"] == 1.0

    assert profile["diagnosis"]["overall_score"] == 0.67
    assert profile["diagnosis"]["total_questions"] == 3
    assert len(profile["diagnosis"]["questions"]) == 3


# ── reset ───────────────────────────────────────────────────────────────────


def test_reset_profile():
    """reset_profile deletes the profile file."""
    from deeptutor.exam.profile import reset_profile, save_profile, load_profile

    save_profile({"exam_name": "test", "created_at": "", "last_updated": "",
                  "knowledge_points": [], "diagnosis": None})
    assert load_profile()["exam_name"] == "test"

    reset_profile()
    assert load_profile()["exam_name"] == ""  # back to defaults


# ── state extensions ────────────────────────────────────────────────────────


def test_state_new_fields():
    """State includes onboarding_completed, diagnosis_completed, kb_name."""
    from deeptutor.exam.state import load_state, update_state

    state = update_state(
        exam_name="Test",
        exam_date="2026-07-20",
        onboarding_completed=True,
        diagnosis_completed=False,
        kb_name="my-kb",
    )
    assert state["onboarding_completed"] is True
    assert state["diagnosis_completed"] is False
    assert state["kb_name"] == "my-kb"

    loaded = load_state()
    assert loaded["onboarding_completed"] is True
    assert loaded["kb_name"] == "my-kb"

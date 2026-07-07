# Exam Sprint 数据架构设计

> V0 阶段数据持久化方案，确保业务闭环完整。

---

## 1. 文件结构

```
data/exam_sprint/
├── state.json                 # 考试状态 + 向导进度
├── profile.json               # 用户画像 + 掌握度（唯一数据源）
├── learn_history/             # 学习材料历史（按时间）
│   └── YYYY-MM-DD_HH-MM_<知识点>.md
└── practice_history.json      # 练习历史（仅错题）
```

---

## 2. state.json — 考试状态

| 字段 | 类型 | 说明 |
|------|------|------|
| `exam_name` | string | 考试名称（如"计算机网络 期末考试"） |
| `exam_date` | string | 考试日期 YYYY-MM-DD |
| `daily_budget_minutes` | int | 每日可用学习时间（分钟） |
| `phase` | string | 当前阶段：phase_planning / sprint_week / score_protection |
| `streak` | int | 连续学习天数 |
| `last_active` | string | 最近活跃时间 ISO datetime |
| `onboarding_completed` | bool | 冷启动向导是否完成 |
| `diagnosis_completed` | bool | 诊断测评是否完成 |
| `kb_name` | string | 关联的知识库名称（可为空） |

**读写模块**：`deeptutor/exam/state.py`（已有，需扩展字段）

---

## 3. profile.json — 用户画像 + 掌握度

### 3.1 顶层结构

```json
{
  "exam_name": "计算机网络",
  "created_at": "2026-07-07T10:00:00",
  "last_updated": "2026-07-07T15:30:00",
  "knowledge_points": [...],
  "diagnosis": { ... }
}
```

### 3.2 knowledge_points 数组

每个知识点一个元素，可追加（诊断初始化一批，后续练习中可新增）。

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 知识点名称 |
| `chapter` | string | 章节归属（来源：KB 优先 → LLM 推断） |
| `score` | float | 掌握度 0.0-1.0（指数移动平均更新） |
| `total_questions` | int | 该知识点累计答题数 |
| `correct` | int | 该知识点累计正确数 |
| `error_types` | string[] | 错因分类（如"概念混淆"、"计算错误"） |
| `last_practiced` | string | 最近练习时间 ISO datetime |
| `practice_count` | int | 累计练习次数 |

### 3.3 diagnosis 对象

诊断测评完成后的完整报告，供用户回溯查看。

| 字段 | 类型 | 说明 |
|------|------|------|
| `completed_at` | string | 诊断完成时间 |
| `total_questions` | int | 诊断总题数（LLM 动态决定） |
| `correct` | int | 正确题数 |
| `overall_score` | float | 综合得分 0.0-1.0 |
| `questions` | array | 每道题的完整记录（见下） |
| `weak_points` | string[] | 薄弱点排序 |
| `strong_points` | string[] | 强项排序 |

**questions 子结构**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `question_id` | string | 题目 ID |
| `question` | string | 题目内容 |
| `correct_answer` | string | 正确答案 |
| `user_answer` | string | 用户作答 |
| `is_correct` | bool | 是否正确 |
| `error_type` | string | 错因分类（答错时） |

### 3.4 双视图模型

| 视图 | 消费者 | 数据来源 |
|------|--------|---------|
| **用户画像（AbilityProfile）** | 后端系统、LLM prompt | profile.json → score / error_types / practice_count |
| **掌握度报告（Mastery Report）** | 前端 Dashboard | profile.json → 渲染为可视化图表 |

同一份数据，两种用途。

---

## 4. learn_history/ — 学习材料历史

每个知识点的每次学习生成一个 Markdown 文件。

**文件命名**：`YYYY-MM-DD_HH-MM_<知识点>.md`

**文件内容**：LLM 生成的完整 Markdown（含 LaTeX 公式）

**前端访问**：`GET /learn/history` → 列出文件列表 → 点击查看内容

---

## 5. practice_history.json — 练习历史（仅错题）

```json
{
  "sessions": [
    {
      "generated_at": "2026-07-07T14:00:00",
      "kb_name": "计算机网络",
      "questions": [
        {
          "question_id": "q1",
          "question": "...",
          "correct_answer": "...",
          "user_answer": "...",
          "explanation": "...",
          "error_type": "概念混淆"
        }
      ]
    }
  ]
}
```

**只保存错题**，正确题目不记录。

---

## 6. 冷启动向导流程

```
Step 1: 考试信息
  输入：考试名称、考试日期、每日可用时间
  写入：state.json

Step 2: 创建知识库
  输入：KB 名称（默认用考试名称填充）、上传文档（可选）
  行为：创建全局 KB → state.json.kb_name = KB 名称
  提示：跳过后 Learn/Practice 将基于通用知识生成，建议上传课程资料

Step 3: 诊断测评
  输入：无（自动生成）
  行为：LLM 根据 KB 内容/考试范围动态决定题数
  写入：profile.json（初始化 knowledge_points + diagnosis）

Step 4: 完成
  展示：诊断结果概览（分数 + 薄弱点）
  写入：state.json.onboarding_completed = true
```

---

## 7. API 变更

### 已有端点（修改）

| 端点 | 变更 |
|------|------|
| `GET /state` | 返回新增字段（kb_name, onboarding_completed, diagnosis_completed） |
| `POST /state` | 接收新增字段 |
| `GET /mastery` | 改为从 profile.json 读取 |
| `POST /mastery/update` | 改为更新 profile.json |
| `POST /learn` | 增加 learn_history 保存逻辑 |

### 新增端点

| 端点 | 方法 | 用途 |
|------|------|------|
| `GET /profile` | GET | 返回完整画像（knowledge_points + diagnosis） |
| `POST /diagnosis/generate` | POST | 生成诊断题（题数由 LLM 动态决定） |
| `POST /diagnosis/submit` | POST | 提交诊断答案 → 初始化 profile.json |
| `GET /practice/history` | POST | 读取错题历史 |
| `POST /state/reset` | POST | 重置全部状态（确认后清空 state + profile + history） |

---

## 8. 数据流

### 冷启动

```
用户输入 → state.json（考试信息）
上传文档 → 全局 KB → state.json（kb_name）
诊断测评 → profile.json（初始化）
```

### 每日循环

```
用户点击 Learn → RAG/LLM 生成 → learn_history/ + Drawer 展示
用户点击 Practice → RAG/LLM 出题 → Drawer 作答 → submit
  → 正确：mastery EMA 更新 profile.json
  → 错误：mastery EMA 更新 + 错题写入 practice_history.json
```

### 掌握度更新公式

```
updated_score = 0.7 * old_score + 0.3 * new_score
```

首次初始化（诊断）时不使用 EMA，直接写入原始正确率。

---

## 9. 用户状态机

```
全新用户（state 不存在）
  → 冷启动向导 Step 1-4
  → onboarding_completed = true

回访用户（state 存在，onboarding_completed = true）
  → 直接进 Dashboard

重置（用户主动触发）
  → 清空 state.json + profile.json + learn_history/ + practice_history.json
  → 回到全新用户状态
```

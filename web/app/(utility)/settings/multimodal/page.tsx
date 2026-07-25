"use client";

import { useTranslation } from "react-i18next";

import { ServiceConfigEditor } from "@/components/settings/ServiceConfigEditor";
import { SettingsPageHeader } from "@/components/settings/shared";

// 多模态（vision）模型配置页：复用通用 ServiceConfigEditor，service="multimodal"。
// 走 llm 逻辑（profile/binding/base_url/api_key/models + context_window 编辑），
// 但不包含 llm 专有的 context-window 自动探测 banner。
export default function MultimodalSettingsPage() {
  const { t } = useTranslation();
  return (
    <div data-tour="tour-multimodal">
      <SettingsPageHeader
        title={t("Multimodal")}
        description={t(
          "Configure the vision-capable model used by video understanding and other multimodal tools.",
        )}
      />
      <ServiceConfigEditor service="multimodal" />
    </div>
  );
}

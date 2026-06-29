# Book Rendering Errors — Fix Log

**分支**: `fix/book-rendering-errors`
**基线**: `main` @ `2ef7f2c`
**日期**: 2026-06-29

---

## 修复概览

| # | 问题 | 优先级 | 状态 | 影响文件 |
|---|------|--------|------|---------|
| 1 | Animation 块生成失败：math-animator 未安装 | P0 | ✅ 已修复 | 运行环境 |
| 2 | Chart 渲染错误：JSON 包含 JS 注释 | P0 | ✅ 已修复 | `web/components/visualize/VisualizationViewer.tsx` |
| 3 | Mermaid 图表解析错误：节点标签含换行符 | P1 | ✅ 已修复 | 多文件（见下） |
| 4 | ConceptGraphBlock 链接 404：URL 模式错误 | P1 | ✅ 已修复 | `web/app/(workspace)/book/components/blocks/ConceptGraphBlock.tsx` |

---

## 详细修复说明

### Fix 1: 安装 math-animator

**现象**: 所有含 Animation 块的章节显示 "generator_error: AnimationGenerator requires the optional math-animator extras"

**修复**: 运行 `pip install -e ".[math-animator]"` 安装 manim 依赖（v0.20.1）

**验证**: 动画块在 Regenerate page 后可正常生成

---

### Fix 2: Chart JSON 注释清洗

**现象**: 图表块显示 "Chart rendering error: Unexpected token '/', ... is not valid JSON"

**根因**: LLM 生成的 Chart.js 配置 JSON 中包含 JavaScript 单行注释（`// 训练损失曲线`），标准 `JSON.parse()` 无法解析

**修复文件**: `web/components/visualize/VisualizationViewer.tsx`

**修复内容**:
```typescript
/** Strip JS-style comments (// and /* … *​/) from JSON-like strings. */
function stripJsonComments(s: string): string {
  let out = s.replace(/\/\/[^\n]*/g, "");
  out = out.replace(/\/\*[\s\S]*?\*\//g, "");
  return out;
}
```

在 `parseChartConfig` 的两次 `JSON.parse` 调用前均加入 `stripJsonComments()` 预处理。

---

### Fix 3: Mermaid 节点换行符

**现象**: 概念图/流程图显示 "Diagram rendering error: Parse error on line 3: SH_Input[输入向量\n(X)]"

**根因**: LLM 生成或后端确定性生成的 Mermaid 源中，节点标签 `[...]` 内包含 `\n` 换行符，Mermaid 解析器不支持

**修复策略**: 前端多层防御

| 文件 | 修复方式 |
|------|---------|
| `web/components/Mermaid.tsx` | 在 `mermaid.render()` 前清洗：`\[([^\]]*)\]` 匹配并折叠换行 |
| `web/app/(workspace)/book/components/blocks/ConceptGraphBlock.tsx` | 同上，在 fenced code block 构建前清洗 |
| `web/app/(workspace)/book/components/blocks/FigureBlock.tsx` | 对 `renderType === "mermaid"` 的内容做相同清洗 |
| `deeptutor/book/blocks/concept_graph.py` | `_escape_label()` 增加 `.replace("\n", " ")` 防御 |

---

### Fix 4: ConceptGraphBlock URL 模式

**现象**: 点击概念图中的章节链接返回 404

**根因**: 链接使用路径模式 `/book/${bookId}?page=...`，但 Next.js 路由中不存在 `/book/[bookId]` 页面

**修复文件**:
- `web/app/(workspace)/book/components/blocks/ConceptGraphBlock.tsx`
  - `/book/${bookId}?page=...` → `/book?book=${encodeURIComponent(bookId)}&page=...`
- `web/app/(workspace)/book/page.tsx`
  - 补充 `page` 查询参数支持，deep-link 时自动选中指定页面

---

## 测试验证

### 验证步骤
1. 访问 `http://127.0.0.1:3782/book`
2. 进入 "序列推荐模型：从原理推导到动手实现"
3. 依次浏览以下章节：
   - 核心机制推导（原 Mermaid 错误）→ 验证概念图正常渲染
   - 主流模型剖析（原 Animation 错误）→ 验证动画块可 Regenerate
   - 模型训练（原 Chart 错误）→ 验证图表正常渲染
4. 点击概念图中的章节链接 → 验证不再 404

### 回归检查
- [ ] 书籍列表页正常
- [ ] 创建新书籍流程正常
- [ ] Spine 编辑器正常
- [ ] Reader 视图正常
- [ ] Chat 面板正常

---

## 提交记录

```
2ef7f2c  chore: baseline snapshot (main)
  ↓
fix/book-rendering-errors  ← 当前分支
  - fix: ConceptGraphBlock URL pattern
  - fix: Chart JSON comment stripping
  - fix: Mermaid newline sanitization (multi-layer)
  - fix: Backend _escape_label newline defense
  - feat: BookPage page query parameter support
```

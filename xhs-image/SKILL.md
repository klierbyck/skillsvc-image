---
name: xhs-image
description: 为小红书、小绿书、XHS、RedNote、贴图号或微信贴图号规划 1-10 张连续图片卡片，并整理必要的平台文案。只提供卡片方案、prompt 和资产依赖，由父级 skillsvc-image 执行生成；纯文字或普通公众号任务不要使用。
---

# 小红书与贴图号图片卡片规划

本目录是 `skillsvc-image` 的图片卡片特殊场景，只负责平台内容与视觉规划。它不选择模型、不调用 CLI、不创建或读取 session，也不管理 API 错误。若本文件被直接调用，先读取 [../SKILL.md](../SKILL.md)，完成规划后回到父级技能执行。

## 适用范围

- 最终交付物明确是小红书、小绿书、XHS、RedNote、贴图号或微信贴图号图文。
- 写上述平台内容时默认按图文任务规划，除非用户明确说“只要文字”或“不要图片”。
- 用户已有最终文案时默认保留，只进行卡片拆分；只有用户要求时才改写。
- 参考材料所属平台不决定输出平台。
- 最终交付物明确是普通公众号文章、封面或正文插图时，改用 `gzh-image`。
- “贴图”“配图”“加图”本身不是平台信号。

## 平台默认值

- 每张卡片默认 `3:4`、`2K`。
- 支持 `1-10` 张：1 张为单卡；2 张为封面加总结；3 张以上为封面、内容卡和可选结尾卡。
- 用户明确指定的比例、尺寸、数量、文字、品牌和风格始终优先。

按需读取视觉资料，不要一次加载全部：

- 风格与 preset：[references/style-presets.md](references/style-presets.md)
- 具体风格：[references/presets/](references/presets/)
- 配色：[references/palettes/](references/palettes/)
- 画布和布局：[references/elements/canvas.md](references/elements/canvas.md)
- 排版：[references/elements/typography.md](references/elements/typography.md)
- 装饰：[references/elements/decorations.md](references/elements/decorations.md)
- 图片效果：[references/elements/image-effects.md](references/elements/image-effects.md)

## 确认与偏好

按以下优先级读取首个存在的 `EXTEND.md`：

1. `.skillsvc-image/xhs-image/EXTEND.md`
2. `${XDG_CONFIG_HOME:-$HOME/.config}/skillsvc-image/xhs-image/EXTEND.md`
3. `$HOME/.skillsvc-image/xhs-image/EXTEND.md`

文件不存在时直接使用内置默认值，不阻塞、不创建配置。只有用户明确要求保存或重新配置偏好时，才读取 [references/config/first-time-setup.md](references/config/first-time-setup.md)。完整 schema 见 [references/config/preferences-schema.md](references/config/preferences-schema.md)。

用户说“直接生成”“不用确认”“按默认出图”或 `--yes` 时不再提问。已给足必要参数时也不重复确认。只有策略、风格、布局、数量或受众仍存在实质歧义时，才按 [references/confirmation.md](references/confirmation.md) 一次性询问缺失项。

## 输出结构

```text
image-cards/{topic-slug}/
├── source-references/
├── post.md
├── analysis.md
├── outline.md
├── prompts/NN-{type}-{slug}.md
├── refs/
└── NN-{type}-{slug}.png
```

详细模式可以额外生成 `outline-strategy-a.md`、`outline-strategy-b.md` 和 `outline-strategy-c.md`。不要在子技能中创建 session 文件或 `generation-manifest.json`；这些由父级技能在实际生成时维护。

覆盖任何 source、outline、prompt 或图片前，先保留带时间戳的备份。prompt 文件是平台规划的 source of truth，必须在返回资产规格前全部写入磁盘。

## 工作流

1. 确定目标平台、受众、主题和用户要求的最终交付内容。
2. 准备 `post.md`。只有主题时创作必要平台文案；有参考内容时提取角度、结构和信息组织后重新表达；已有最终文案时默认保留。
3. 按 [references/workflows/analysis-framework.md](references/workflows/analysis-framework.md) 创建 `analysis.md`，推荐图片数量、内容策略、风格、布局和配色。
4. 仅在存在实质歧义时确认。快速模式创建一份 `outline.md`；详细模式按 [references/workflows/outline-template.md](references/workflows/outline-template.md) 生成三种不同结构后再选定。
5. 按 [references/workflows/prompt-assembly.md](references/workflows/prompt-assembly.md) 为每张卡片写入完整 prompt。
6. 返回带依赖关系的资产规格列表给父级 `skillsvc-image`；不得直接执行图片生成。

## 卡片策略

根据内容选择一种结构，不要固定套用：

- Story-Driven：适合体验、故事、转变和情绪连接。
- Information-Dense：适合教程、对比、清单和知识总结。
- Visual-First：适合产品视觉、生活方式和氛围内容。

封面负责钩子和视觉识别；中间卡片每张只承担一个核心信息任务；结尾卡片仅在需要总结或行动引导时使用。单卡模式将钩子和核心价值合并，不强制生成结尾。

## 资产关系

使用稳定且唯一的 `asset_id`：`card-01`、`card-02` 等。每项规格包含 `asset_id`、role、action、prompt 文件、参考图片、视觉依赖、比例、尺寸和输出路径，但不包含 model 或 session。

```yaml
asset_id: card-02
role: content-card
action: reference
prompt_file: prompts/02-content-topic.md
reference_images: []
reference_asset_id: card-01
aspect_ratio: 3:4
image_size: 2K
output: 02-content-topic.png
```

系列关系规则：

- `card-01` 是默认视觉锚点，必须最先完成。
- 用户直接参考图只关联到需要使用它们的资产，通常是 `card-01`。
- `card-02` 及后续卡片默认将 `reference_asset_id` 指向 `card-01`，以继承人物、产品、配色和媒介语言。
- 视觉锚点只表示父级生成时的参考依赖，不表示共享编辑 session。
- 同一 manifest 的资产由父级按依赖顺序串行调度；不同 manifest 且独立 session 的任务可并行。子技能只描述依赖，不控制执行工具。

## 内容约束

- 不虚构个人体验、产品使用结果、统计数据、用户评价、保证或背书。
- 卡片文字必须来自确认后的 `post.md` 和 `outline.md`，不得为视觉效果自行改变事实。
- 每张卡片的 prompt 必须自足，并重复必要的系列视觉方向和准确文字。
- 水印只在偏好明确启用时写入 prompt，规则见 [references/config/watermark-guide.md](references/config/watermark-guide.md)。
- 用户提供的原始文件不得覆盖。
- 本子技能只规划本地文案和图片卡片，不登录、上传或发布到任何平台。

## 参考资料

- 确认流程：[references/confirmation.md](references/confirmation.md)
- 内容分析：[references/workflows/analysis-framework.md](references/workflows/analysis-framework.md)
- Outline：[references/workflows/outline-template.md](references/workflows/outline-template.md)
- Prompt：[references/workflows/prompt-assembly.md](references/workflows/prompt-assembly.md)
- 偏好配置：[references/config/preferences-schema.md](references/config/preferences-schema.md)
- 首次配置：[references/config/first-time-setup.md](references/config/first-time-setup.md)
- 水印：[references/config/watermark-guide.md](references/config/watermark-guide.md)

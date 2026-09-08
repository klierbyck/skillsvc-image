---
name: gzh-image
description: 为微信公众号文章规划封面和正文配图；也可在用户要求“写公众号文章并配图”时整理必要正文。只提供平台视觉方案和资产规格，由父级 skillsvc-image 执行生成；纯文字、小红书或贴图号任务不要使用。
---

# 微信公众号图片规划

本目录是 `skillsvc-image` 的公众号特殊场景，只负责平台内容与视觉规划。它不选择模型、不调用 CLI、不创建或读取 session，也不管理 API 错误。若本文件被直接调用，先读取 [../SKILL.md](../SKILL.md)，完成规划后回到父级技能执行。

## 适用范围

- 公众号封面、头图、正文配图或完整公众号图文。
- 用户已有正文时，默认保留正文，只规划封面和插图。
- 用户只给主题且要求“写公众号文章并配图”时，可整理必要正文再规划图片。
- 参考公众号文章只说明素材来源，不自动决定最终平台。
- 最终交付物明确是小红书、XHS、RedNote、贴图号或微信贴图号时，改用 `xhs-image`。
- “贴图”“配图”“加图”本身不是平台信号。

## 平台默认值

- 头条封面：`2.35:1`、`2K`。
- 正文插图：`16:9`、`2K`。
- 用户明确指定的比例、尺寸、文字和风格始终优先。
- 默认封面文字为 `title-only`；正文插图除非确有必要，尽量不生成文字。

视觉选择包括 type、palette、rendering、text、mood 和 font。需要选择时读取：

- 自动推荐：[references/auto-selection.md](references/auto-selection.md)
- 类型：[references/types.md](references/types.md)
- 配色：[references/palettes/](references/palettes/)
- 渲染：[references/renderings/](references/renderings/)
- 维度：[references/dimensions/](references/dimensions/)
- 组合预设：[references/style-presets.md](references/style-presets.md)

## 确认与偏好

按以下优先级读取首个存在的 `EXTEND.md`：

1. `.skillsvc-image/gzh-image/EXTEND.md`
2. `${XDG_CONFIG_HOME:-$HOME/.config}/skillsvc-image/gzh-image/EXTEND.md`
3. `$HOME/.skillsvc-image/gzh-image/EXTEND.md`

文件不存在时直接使用内置默认值，不阻塞、不创建配置。只有用户明确要求保存或重新配置偏好时，才读取 [references/config/first-time-setup.md](references/config/first-time-setup.md)。完整 schema 见 [references/config/preferences-schema.md](references/config/preferences-schema.md)。

用户说“直接生成”“不用确认”“按默认出图”或 `--quick` 时不再提问。已给足必要参数时也不重复确认。只有仍存在会显著改变结果的歧义时，才按 [references/workflow/confirm-options.md](references/workflow/confirm-options.md) 一次性询问缺失项。

## 输出结构

封面任务：

```text
cover-image/{topic-slug}/
├── source-{slug}.{ext}
├── refs/
├── prompts/01-cover-{slug}.md
└── cover.png
```

完整文章任务：

```text
wechat-article/{topic-slug}/
├── source-references/
├── article.md
├── visual-plan.md
├── prompts/01-cover-{slug}.md
├── prompts/NN-illustration-{slug}.md
├── cover.png
└── illustration-NN.png
```

不要在子技能中创建 session 文件或 `generation-manifest.json`。这些由父级技能在实际生成时维护。

## 工作流

1. 判断是仅封面、已有文章配图、直接创作图文，还是参考内容创作图文。
2. 保存用户提供的正文和参考材料。参考内容默认是软参考，不复制原文；只有用户明确指定的事实、原文、人物、产品或品牌元素才是硬约束。
3. 新写或实质改写正文时，按 [文案衔接规则](../references/writing-integration.md) 调用包内 [活人写作](../human-writing/SKILL.md)，完成材料检查、正文与改稿后保存 `article.md`，再根据全文创建 `visual-plan.md`。仅封面或已有定稿配图跳过写作改稿。图片位置必须服务于解释、对比、演示、氛围或阅读节奏。
4. 选择平台视觉参数。只在存在实质歧义时确认。
5. 按 [references/workflow/prompt-template.md](references/workflow/prompt-template.md) 为每张图片写入完整 prompt。参考图处理见 [references/workflow/reference-images.md](references/workflow/reference-images.md)。
6. 返回资产规格列表给父级 `skillsvc-image`；不得直接执行图片生成。

## 资产关系

每张图使用稳定且唯一的 `asset_id`：

- 封面：`cover`
- 正文插图：`illustration-01`、`illustration-02` 等

每项规格包含 `asset_id`、role、action、prompt 文件、参考图片、比例、尺寸和输出路径，但不包含 model 或 session：

```yaml
asset_id: cover
role: wechat-cover
action: reference
prompt_file: prompts/01-cover-topic.md
reference_images:
  - refs/ref-01-product.png
reference_asset_id: null
aspect_ratio: 2.35:1
image_size: 2K
output: cover.png
```

正文插图默认是彼此独立的资产，通过 prompt 中的统一视觉方向保持一致。确需沿用某张图的具体人物、产品或场景时，使用 `reference_asset_id` 描述视觉依赖；这不是 session 关系。

## 内容和视觉约束

- 不虚构个人经历、测试结果、引语、数据或产品效果。
- 标题使用用户或正文中的准确文本，不擅自改写。
- 参考图包含必须出现在成品中的人物或产品时，保存到 `refs/`，并在资产规格和 prompt 中同时记录具体保留要求。
- 用户提供的原始文件不得覆盖；修改已有文章时默认输出新的带配图版本。
- 本子技能只规划本地内容，不登录、上传或发布微信公众号内容。

## 参考资料

- 提示词模板：[references/workflow/prompt-template.md](references/workflow/prompt-template.md)
- 参考图处理：[references/workflow/reference-images.md](references/workflow/reference-images.md)
- 选项确认：[references/workflow/confirm-options.md](references/workflow/confirm-options.md)
- 兼容性：[references/compatibility.md](references/compatibility.md)
- 视觉元素：[references/visual-elements.md](references/visual-elements.md)
- 水印：[references/config/watermark-guide.md](references/config/watermark-guide.md)

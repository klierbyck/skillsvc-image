---
name: skillsvc-image
description: 核心使用 https://www.skillsvc.cc 的 gpt-image-2 或 Nano Banana API 进行文生图、参考图生图和持续编辑；扩展支持文章配图、微信公众号图文、小红书图文和贴图号图文，根据必要上下文生成配套图片。只生成本地内容与图片，不负责发布。
---

# skillsvc-image 图片生成

本技能的核心始终是图片生成：普通文生图、参考图生图和基于会话的持续编辑。文章写作与配图、微信公众号图文、小红书图文和贴图号图文只是图文生图扩展，只在最终交付物包含图片时处理必要的正文和结构，以便生成准确的配套图片；它不是通用纯写作或发布技能。微信公众号、小红书和贴图号的具体规则由包内两个平台规则目录负责。

使用随附 CLI 执行 API 请求。它也是 Codex 与其他可运行命令的 AI 共用的稳定接口：

```bash
python3 scripts/generate_image.py generate --prompt "..."
python3 scripts/generate_image.py reference --image /path/ref.png --prompt "..."
python3 scripts/generate_image.py edit --session /path/session.json --prompt "..."
```

以本文件所在目录为基准解析 `scripts/generate_image.py`。仅在配置环境、使用高级参数、对接其他 AI 或排查调用问题时读取 [references/cli.md](references/cli.md)。

本技能拥有模型选择、CLI 调用、输出校验、session 和 `generation-manifest.json`。平台任务、多资产任务或需要 manifest 映射的编辑任务在执行前读取 [references/image-generation-contract.md](references/image-generation-contract.md)。普通单图的 `generate`、`reference` 或直接 `edit` 保持原有独立流程，无需加载平台子技能或共享 contract。平台子技能只负责内容与视觉规划，并返回不含模型和 session 的资产规格；完成规划后必须回到本技能执行。

## 平台技能路由

- 用户明确要求公众号封面、头图、正文配图、公众号图文，或“写公众号文章并配图”时，使用 [gzh-image/SKILL.md](gzh-image/SKILL.md) 完成视觉规划并返回资产规格，然后回到本技能执行生成。
- 用户明确要求小红书、小绿书、XHS、RedNote、贴图号或微信贴图号图文时，使用 [xhs-image/SKILL.md](xhs-image/SKILL.md) 整理文案、卡片结构和资产依赖，然后回到本技能执行生成。
- 用户要求普通文章配图或“写文章并配图”，且没有指定上述平台时，读取 [references/article-illustration.md](references/article-illustration.md)。
- 用户只要求生成或编辑一张普通图片时，直接使用本文件的通用生图流程。
- 用户只要求纯文字写作且不需要任何图片时，不应触发本技能。
- “贴图”“配图”“加图”本身不是平台信号，应结合用户要求的最终交付物判断；确实无法判断目标平台时，只询问一次。
- 以用户要求的最终内容类型决定路由，不以参考材料来自哪个平台决定。例如“参考一篇公众号文章写小红书”仍使用小红书技能。
- 两个平台目录各自拥有独立 `SKILL.md` 和 `references/`，但都属于本技能包并统一调用本技能的生图 CLI；不把平台规则复制进本文件，也不修改用户机器上另外安装的原版技能。

普通生图不经过 `gzh-image` 或 `xhs-image`。根技能直接整理 prompt，并在需要记录时自行创建默认 `asset_id`（例如 `image-01`）；平台子技能不是普通 `generate`、`reference` 或 `edit` 的依赖。

## 包内活人写作

图文任务需要新写或实质改写正文、帖子或卡片文字时，读取 [文案衔接规则](references/writing-integration.md)，由平台模块调用 [human-writing](human-writing/SKILL.md) 完成材料检查、写作与改稿，再返回平台规划。公众号、小红书与贴图号共用这一份写作模块，平台决定篇幅和形式，不强制写成长帖。

已有定稿只配图、只做封面、普通单图与仅编辑图片时不加载写作模块，也不因风格检查重写用户文字。包内模块不负责图片模型、API、session 或 manifest。场景总览见 [scenarios.md](references/scenarios.md)。

## 参考内容原则

- 参考文章、帖子、链接、图片或已有草稿都是可选输入；只有主题时可启动创作。现实题材先补足事实支撑，材料不足则研究、一次性追问或按已有支撑缩短，不能为了配图编造亲历或数据；虚构题材按授权创造。
- 默认只提取参考内容的选题角度、结构、语气、信息组织和视觉节奏，创作新的正文与画面，不复制原文，也不把所有参考细节当成硬性要求。
- 只有用户明确说“必须保持”“严格按照”“原样使用”或指定某个元素时，才把对应内容视为硬约束。
- 参考材料所属平台不等于目标平台，始终以用户明确要求的最终产物为准。

## 默认值与模型路由

- 新建图片的模型优先级为：用户本轮明确指定 > `.env` 中的 `IMAGE_MODEL` > `gpt-image-2`。用户未指定模型时不要传 `--model`，由 CLI 解析环境默认值。
- 用户明确指定 Banana、Nano Banana、nanobanana、香蕉生图或 `nana-banana-2` 时传入 `--model nana-banana-2`；明确指定 GPT 时传入 `--model gpt-image-2`。
- 编辑已有 session 时的优先级为：用户本轮明确指定 > session 原模型 > `.env` 中的 `IMAGE_MODEL` > `gpt-image-2`。默认保持 session 原模型。
- 默认比例为 `16:9`，默认尺寸为 `2K`，默认质量为 `auto`。
- 用户明确指定的比例、尺寸、质量和格式始终优先。`1K`/`2K`/`4K` 表示图片尺寸，`low`/`medium`/`high` 表示渲染质量。
- API 失败后不得静默切换模型。按用户任务合理重试，否则报告原始错误。

## 生成模式

- `generate`：纯文本生成新图片。
- `reference`：参考一张或多张图片的风格、人物、产品或构图线索，但生成一张新图片。不得把它表述成“保持原图其他内容不变”。
- `edit`：修改已有图片。优先通过 `--session` 取得上一张成品并继承历史要求；没有会话时使用 `--image`。

每张需要独立迭代的图片使用独立会话。由本技能把 CLI 返回的 `image`、`session`、`model` 和实际参数写入 `generation-manifest.json`；同一资产后续修改通过 `asset_id` 查找并复用对应会话。视觉参考关系不等于共享编辑会话。

## 从上下文构造提示词

调用 CLI 前，将当前要求与相关对话整理成自足的生产提示词。仅纳入已有依据的内容，例如主体、表达目的、构图、环境、视觉风格、光线、色彩、必须保留和必须避免的细节。

直接图片任务放入 `--prompt`，辅助背景放入可重复的 `--context` 或 `--context-file`。不得加入密钥、无关对话或自行猜测的要求。

编辑图片时：

- 精确描述本轮变化，并在确有必要时指出必须保持不变的部分。
- 默认沿用会话中的模型、比例、尺寸和格式，除非用户要求改变。
- 参考图生成与编辑必须区分：前者借用视觉特征创建新画面，后者修改现有画面。

## 执行与验证

1. 平台、多资产或 manifest 编辑任务读取共享生成契约，并检查每项资产规格都具有稳定且唯一的 `asset_id`；普通单图任务跳过此步骤。
2. CLI 会自动加载技能根目录的 `.env`；确认所需密钥已配置，但不得输出密钥值。
3. 选择 `generate`、`reference` 或 `edit`。只有用户本轮明确指定模型时才传 `--model`；否则让 CLI 按 session、`.env` 和内置默认值解析。manifest 编辑通过 `asset_id` 取得对应 session。
4. 同一 manifest 按资产依赖顺序串行执行，由 CLI 加锁并更新元数据；不得让不同资产共享编辑 session。本地保存失败时使用错误消息中的 `recover --journal` 恢复，不重新调用付费 API。
5. CLI 的 `generated` 仅表示通过完整解码且已保存。使用可用的图片查看工具检查每张成品，包括主体准确性、构图、文字、瑕疵、真实宽高比以及关联图片之间的一致性，并在交付说明或 `visual-plan.md` 记录结果。
6. 若存在能依据原要求直接修正的明显问题，通过该资产自己的会话进行编辑。未经用户要求，不额外消耗付费调用生成备选版本。
7. 返回图片、manifest 和会话的绝对路径，并简要说明使用的模型与尺寸。

## 长文上下文配图

普通长文配图或“写文章并配图”的扩展任务读取 [references/article-illustration.md](references/article-illustration.md)。可以从主题直接整理必要正文，也可以借鉴参考内容；先稳定正文，再根据每个插图位置前后的上下文生成对应画面，不能只使用文章标题。

## 边界

- 不把 API Key 写入提示词、会话文件、源码或回复。
- 不覆盖用户提供的原始参考图，所有结果写入新路径。
- 不生成未要求的批次或试验版本。
- 不登录平台、不创建草稿、不上传或发布文章、帖子和图片。
- 不把纯文字写作扩展成主功能；只有任务需要图片时才处理配套正文。
- 平台规则只在包内各自的独立技能目录中维护；通用 API 层不复制这些规则，只接收已经整理好的提示词和参数。

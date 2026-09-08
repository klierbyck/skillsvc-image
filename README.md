# skillsvc image gen skill

一个以图片生成为核心的通用 AI 技能，通过 [https://www.skillsvc.cc](https://www.skillsvc.cc) API 调用 `gpt-image-2` 或
Nano Banana，支持文生图、参考图生图、连续图片编辑，以及基于完整内容上下文的图文生成。

## 功能

### 核心生图能力

- 文生图：根据提示词和对话上下文生成新图片。
- 参考图生图：参考一张或多张图片的风格、人物、产品或构图，生成全新图片。
- 图片编辑：基于已有图片或 session 持续调整，并保留此前上下文。
- 模型选择：用户可在 `.env` 中通过 `IMAGE_MODEL` 设置默认模型；未配置时使用 `gpt-image-2`。本轮提示词或 CLI 的显式模型选择优先。
- 参数控制：支持宽高比、`1K`/`2K`/`4K`、质量和输出格式。

### 图文扩展

这些能力用于为图片提供准确上下文，不是独立的纯文字写作或发布功能：

- 普通文章：可从主题写文章并配图，也可读取已有文章，在理解完整结构后规划插图。
- 微信公众号：使用内置 `gzh-image` 规则生成封面、正文插图或完整公众号图文。
- 小红书与贴图号：使用内置 `xhs-image` 规则整理文案并生成连续图片卡片。
- 参考内容：文章、帖子、链接和图片默认作为软参考，仅借鉴角度、结构、语气和视觉节奏。
- 图片编辑：每张图片保存独立 session，后续可以继续修改对应图片。

根技能统一负责模型、CLI、图片校验、session 和 `generation-manifest.json`。`gzh-image` 与 `xhs-image` 只生成平台内容、视觉方案、prompt 和资产依赖规格，不能自行选择模型或调用 API。

包内集成 [活人写作](human-writing/SKILL.md)：新写或实质改写图文内容时，先检查材料、完成文案并减少重复和空话，再按平台规划图片。平台形式优先，小红书与贴图号不会被强制写成长帖；已有定稿只配图、仅封面和纯图片编辑不触发改稿。无需另装写作 skill。

完整场景及默认流程见 [场景总览](references/scenarios.md)，模块衔接见 [文案与图片](references/writing-integration.md)。典型流程为“材料检查 → 文案与改稿 → 插图/卡片规划 → 生图 → 文案与画面核对”。文案写作由使用 skill 的助手执行，图片 CLI 不会自动写文章。

本技能只在本地生成文章、提示词、图片和 session，不登录、上传或发布到平台。

## 默认参数

| 场景 | 默认比例 | 默认尺寸 |
|---|---:|---:|
| 普通文生图、参考图生图、图片编辑 | `16:9` | `2K` |
| 微信公众号头条封面 | `2.35:1` | `2K` |
| 微信公众号正文插图 | `16:9` | `2K` |
| 小红书、贴图号图片卡片 | `3:4` | `2K` |

模型不是平台固定值：新任务按本轮明确指定、`.env IMAGE_MODEL`、内置
`gpt-image-2` 的顺序解析；编辑任务还会优先继承 session 模型。用户明确指定的
比例、尺寸、质量和格式始终优先。

## 目录结构

```text
skillsvc-image/
├── SKILL.md                         # 技能入口与任务路由
├── agents/openai.yaml               # Codex 展示元数据
├── scripts/generate_image.py        # 通用生图 CLI
├── references/                      # 共享执行契约、CLI 与普通长文配图规则
├── human-writing/                   # 共享写作规则、文案检查脚本及回归测试
├── gzh-image/               # 公众号封面和正文配图规则
└── xhs-image/                # 小红书与贴图号图片卡片规则
```

两个平台规则目录与 human-writing 文案模块已经包含在本技能中，不需要分别安装，也不需要在项目中创建
`.agents` 目录。

## 安装到 Codex

环境要求：Git、Python 3.9 或更高版本，以及可用的 SkillSvc API Key。

```bash
git clone https://github.com/klierbyck/skillsvc-image.git \
  ~/.codex/skills/skillsvc-image

cd ~/.codex/skills/skillsvc-image
python3 -m pip install -r requirements.txt
cp .env.example .env
chmod 600 .env
```

编辑 `.env`，填写至少一个模型的 API Key。重新打开 Codex 或开始一个新任务后，
可以显式调用 `$skillsvc-image`，也可以直接描述生图需求让 Codex 自动选择。

示例：

```text
使用 $skillsvc-image 生成一张未来城市的横版插画。
使用香蕉生图，参考 /path/reference.png 生成一张 3:4 的小红书封面。
写一篇关于家庭 NAS 的微信公众号文章并配图。
写一组关于春季护肤的小红书图文，共 6 张图。
把刚生成图片的背景改成清晨，其他内容保持不变。
```

更新已安装技能：

```bash
cd ~/.codex/skills/skillsvc-image
git pull
```

## 环境配置

技能会自动读取技能根目录的 `.env`：

```dotenv
GPT_IMAGE_API_KEY=
NANO_BANANA_API_KEY=
IMAGE_MODEL=gpt-image-2
BASE_URL=https://www.skillsvc.cc
```

- `GPT_IMAGE_API_KEY`：调用 `gpt-image-2`。
- `NANO_BANANA_API_KEY`：调用 `nana-banana-2`。
- `IMAGE_MODEL`：可选默认模型，支持 `gpt-image-2` 和 `nana-banana-2`；省略或留空时使用 `gpt-image-2`。
- `BASE_URL`：可选，默认 `https://www.skillsvc.cc`。
- 未使用的模型 Key 可以留空。
- 进程环境变量优先于 `.env`；也可以通过 `--env-file` 指定其他配置文件。
- 默认不读取当前工作目录的 `.env`；自定义 API 地址必须使用 HTTPS，携带凭据的请求不自动跟随重定向。

`.env` 已加入 `.gitignore`，不要把真实密钥提交到 Git。

## 供其他 AI 或命令行使用

任何能够读取文件并执行命令的 AI 都可以使用本技能：让它先读取根目录的
`SKILL.md`，根据任务路由读取对应规则，再调用 `scripts/generate_image.py`。

也可以直接使用 CLI。

文生图：

```bash
python3 scripts/generate_image.py generate \
  --prompt "一座雨后清晨的未来城市" \
  --context "用于技术文章头图，画面干净，避免文字"
```

参考图生图：

```bash
python3 scripts/generate_image.py reference \
  --image /absolute/path/reference.png \
  --prompt "参考配色和插画语言，使用全新构图"
```

指定 Nano Banana 和图片比例：

```bash
python3 scripts/generate_image.py generate \
  --model nana-banana-2 \
  --aspect-ratio 3:4 \
  --image-size 2K \
  --prompt "小红书知识卡片封面"
```

继续编辑上一张图片：

```bash
python3 scripts/generate_image.py edit \
  --session /absolute/path/session.json \
  --prompt "将背景改成清晨，保持人物、构图和配色不变"
```

仅检查请求参数、不调用 API：

```bash
python3 scripts/generate_image.py generate \
  --prompt "测试提示词" \
  --dry-run
```

成功后 CLI 输出 JSON，其中包含图片绝对路径、session 路径、模型和实际参数。
同一张图片的后续调整应继续使用对应 session；不同图片应使用不同 session。

同一 manifest 的资产依次生成，CLI 用跨进程锁保护状态。`status: generated` 表示机器校验与保存成功，真实宽高见 `actual_dimensions`；文字和构图仍需视觉检查。新会话使用相对图像路径，支持整体移动输出目录。

若本地保存失败，保留 `.pending.json` 恢复日志并执行错误消息中的 `recover --journal 路径`，即可补完保存而不重复调用生图 API。详细恢复规则与兼容性见 CLI 文档。

更多参数和 API 映射见 [references/cli.md](references/cli.md)。

## 致谢

本项目沿用并修改了 **baoyu 大佬的生图 skill** 和 **卡兹克大佬的活人写作 skill**，在此基础上整合了文案创作、平台配图规划与 SkillSvc 图片生成流程。感谢两位大佬的分享与贡献。
# CLI 调用约定

`scripts/generate_image.py` 需要 Python 3.9 或更高版本和 `requests`。在技能根目录安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

## 环境配置

在技能根目录的 `.env` 中填写：

```dotenv
GPT_IMAGE_API_KEY=
NANO_BANANA_API_KEY=
IMAGE_MODEL=gpt-image-2
BASE_URL=https://www.skillsvc.cc
```

CLI 会先读取当前目录的 `.env`，再读取技能目录的 `.env`。进程中已经存在的环境变量优先。使用 `--env-file /path/to/.env` 或 `SKILLSVC_IMAGE_ENV_FILE` 可明确选择其他配置文件。

`BASE_URL` 默认是 `https://www.skillsvc.cc`。若存在 `IMAGE_API_BASE_URL`，其优先级更高。兼容 `GPT_API_KEY`、`NANOBANANA_API_KEY` 和 `NANA_API_KEY` 别名。

新建图片时的模型优先级为 `--model` > `IMAGE_MODEL` > `gpt-image-2`。编辑已有 session 时为 `--model` > session 原模型 > `IMAGE_MODEL` > `gpt-image-2`。技能从自然语言识别到用户明确指定模型时会转换成 `--model`；未明确指定时不传该参数。

不要通过命令行参数传递密钥，避免密钥出现在进程列表或 AI 对话记录中。

## 命令

使用默认的 `gpt-image-2`、`16:9`、`2K` 创建图片：

```bash
python3 scripts/generate_image.py generate \
  --prompt "完整、明确的图片提示词" \
  --context "用途、受众和相关上下文" \
  --output-dir ./generated-images
```

根据参考图创建新图片，而不是编辑原图：

```bash
python3 scripts/generate_image.py reference \
  --image /absolute/path/style-reference.png \
  --prompt "沿用参考图的配色和插画语言，创建全新构图"
```

明确使用 Nano Banana：

```bash
python3 scripts/generate_image.py generate \
  --model nana-banana-2 \
  --prompt "完整、明确的图片提示词"
```

沿用记录的上下文编辑上一张成品：

```bash
python3 scripts/generate_image.py edit \
  --session ./generated-images/session_20260906_120000.json \
  --prompt "缩小产品标签，保持构图和配色不变"
```

从没有会话的现有图片开始编辑：

```bash
python3 scripts/generate_image.py edit \
  --image /absolute/path/source.png \
  --prompt "把阴天改成清晨晴天"
```

常用参数：

- `--aspect-ratio 1:1|16:9|9:16|4:3|3:4|3:2|2:3|2.35:1`
- `--image-size 1K|2K|4K`
- `--size WIDTHxHEIGHT`：GPT 精确像素尺寸；宽高必须是 16 的倍数，比例不能超过 3:1；不能与 `--aspect-ratio` 或 `--image-size` 同时使用
- `--quality auto|low|medium|high`
- `--output-format png|jpeg|webp`
- `--prompt-file PATH`：从 UTF-8 文件读取完整 prompt；不能与 `--prompt` 同时使用
- `--context TEXT` 可重复；`--context-file PATH` 可重复
- `reference --image PATH` 可重复，用于一张或多张参考图
- `--manifest PATH --asset-id ID`：成对使用；成功后原子更新对应资产记录
- `reference --reference-asset-id ID`：从同一 manifest 读取视觉锚点图片
- `--session PATH`：创建或继续指定的上下文记录
- `--env-file PATH`：加载指定配置文件
- `--dry-run`：只校验并打印请求计划，不调用 API

成功时，标准输出只包含一个 JSON 对象；诊断信息写入标准错误。`image` 和 `session` 均为绝对路径。

输出文件扩展名以 API 返回图片的实际格式为准。若 `--output` 中的扩展名与实际格式不一致，CLI 会改用实际扩展名。Nano Banana 当前只输出 PNG，因此显式指定其他 `--output-format` 会在请求前报错。

## API 映射

- GPT 文生图：`POST /v1/images/generations`
- GPT 参考图生成/图片编辑：`POST /v1/images/edits`
- Nano Banana 文生图/参考图生成/图片编辑：`POST /v1beta/models/nana-banana-2:generateContent`

GPT 接收像素 `size`；Nano Banana 接收 `aspectRatio` 和 `imageSize`。CLI 会把统一参数转换成各模型所需的格式。

Nano Banana 不支持 `--quality`、`--compression`、`--size` 或非 PNG `--output-format`；CLI 会在 API 调用前拒绝这些参数。

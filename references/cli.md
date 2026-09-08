# CLI 调用约定

`scripts/generate_image.py` 需要 Python 3.9 或更高版本，以及 `requests`、`Pillow`、`filelock`。在技能根目录安装依赖：

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

CLI 默认只读取技能目录的 `.env`，不自动信任当前工作目录的配置。进程中已经存在的环境变量优先。使用 `--env-file /path/to/.env` 或 `SKILLSVC_IMAGE_ENV_FILE` 可明确选择其他可信配置文件；显式文件会替代默认配置文件。

`BASE_URL` 默认是 `https://www.skillsvc.cc`。若存在 `IMAGE_API_BASE_URL`，其优先级更高。兼容 `GPT_API_KEY`、`NANOBANANA_API_KEY` 和 `NANA_API_KEY` 别名。

自定义 API 地址必须使用 HTTPS，不允许 URL 内含用户名、密码、查询参数或片段。携带凭据的 API POST 不自动跟随重定向；配置应直接指向服务的最终地址。

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
- `--session PATH`：创建或继续指定的上下文记录，必须为 `.json`，不能与 manifest、图片或输入文件共用路径
- `--env-file PATH`：加载指定配置文件
- `--dry-run`：只校验并打印请求计划，不调用 API

成功时，标准输出只包含一个 JSON 对象；诊断信息写入标准错误。`image` 和 `session` 均为绝对路径。

输出文件扩展名以 API 返回图片的实际格式为准。若 `--output` 中的扩展名与实际格式不一致，CLI 会改用实际扩展名。Nano Banana 当前只输出 PNG，因此显式指定其他 `--output-format` 会在请求前报错。

图片会执行完整解码和像素上限检查，`actual_dimensions` 记录真实宽高，`parameters` 保留请求参数。`status: generated` 表示图片通过机器校验并已保存，不代表文字、构图或尺寸符合创作要求；视觉检查仍由根技能完成。已有 `complete` 资产仍可读取。

## 并发、迁移与恢复

同一 manifest 的所有生成/编辑通过跨进程锁串行执行，同一 session 也单独加锁；锁等待最多 30 秒，超时后返回可处理的错误。建议同一批资产依次调用 CLI，不要把锁超时当作 API 失败重试。不同 manifest 且独立 session 的任务仍可并行。

图片通过同目录临时文件与硬链接排他发布，需要支持硬链接的本地文件系统（例如 NTFS、ext4、APFS）。`.lock` 文件可在运行后保留；锁是否持有由操作系统决定，不应在任务执行中删除锁文件。

新 session 的图像路径相对 session 保存；manifest 路径也支持相对位置，整个输出目录可整体移动。同一磁盘中分开放置的图片与 session 也须一起移动并保持相对结构。旧 session 的有效绝对路径仍可使用；已经移动且绝对路径失效的旧会话，可通过 `edit --image 新图片路径 --session 旧会话路径` 显式重新关联。属于 manifest 的 session 必须通过 `--manifest ... --asset-id ...` 编辑。

本地保存失败会保留包含图片和待提交元数据的 `.pending.json` 日志，并阻止同一 manifest/session 继续生图。使用错误消息返回的完整日志路径恢复：

```bash
python3 scripts/generate_image.py recover --journal /path/generation-manifest.json.pending.json
```

恢复只补完本地保存，不读取 API 密钥、不联网、不追加编辑轮次。恢复中再次失败时日志仍保留，可在解决磁盘/权限问题后重试恢复命令；目标图片已有不同内容时拒绝覆盖。恢复完成后日志自动删除。恢复前不要移动输出目录或手工修改元数据、图片和日志。

若磁盘连恢复日志都无法写入，CLI 会明确报告结果未持久化，此时无法保证恢复，禁止自动重复付费调用。HTTP 超时也不证明服务端没有生成图片，应先核查结果。

## API 映射

- GPT 文生图：`POST /v1/images/generations`
- GPT 参考图生成/图片编辑：`POST /v1/images/edits`
- Nano Banana 文生图/参考图生成/图片编辑：`POST /v1beta/models/nana-banana-2:generateContent`

GPT 接收像素 `size`；Nano Banana 接收 `aspectRatio` 和 `imageSize`。CLI 会把统一参数转换成各模型所需的格式。

Nano Banana 不支持 `--quality`、`--compression`、`--size` 或非 PNG `--output-format`；CLI 会在 API 调用前拒绝这些参数。

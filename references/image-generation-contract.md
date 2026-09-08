# 图片生成执行契约

本文件仅在平台、多资产或显式使用 manifest 的任务中由根技能 `skillsvc-image` 读取。普通单图 `generate`、`reference` 和直接 `edit` 不依赖本文件。平台子技能只负责规划，不选择模型、不调用 CLI、不创建或读取 session。

## 职责边界

根技能负责：

- 解析模型、API 配置和生成模式；
- 调用 `scripts/generate_image.py`；
- 检查提示词、参考图、输出路径和图片格式；
- 创建、读取和更新 `generation-manifest.json`；
- 维护 `asset_id` 与 image/session 的一一映射；
- 按依赖调度、重试、检查成品并返回最终文件。

平台子技能负责：

- 平台内容、视觉风格、尺寸、图片数量和插图位置；
- 写入完整 prompt 文件；
- 为每张图提供唯一 `asset_id` 和生成规格；
- 描述资产之间的视觉参考或执行依赖；
- 将规格交回根技能，不直接执行生成。

普通单图任务不加载平台子技能。根技能直接从用户要求构造同样的资产规格；若需要 manifest，使用默认 `asset_id`（例如 `image-01`），否则 CLI 的原有独立调用方式保持不变。

## 资产规格

平台子技能返回的每项规格使用以下字段；不得包含 `model` 或 `session`：

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

- `action`: `generate`、`reference` 或 `edit`。编辑只需要给出已有 `asset_id` 和本轮 prompt；session 由根技能查找。
- `reference_images`: 用户提供的直接参考图绝对路径。
- `reference_asset_id`: 引用另一张已生成资产作为视觉锚点。它只建立生成依赖，不代表共享 session。
- `prompt_file`: 必须在执行前存在，且包含完整、自足的最终提示词。
- `output`: 不得覆盖已有文件；修改应使用新输出路径并保留旧候选。

## Manifest

根技能在输出目录维护 `generation-manifest.json`：

```json
{
  "version": 1,
  "assets": {
    "card-01": {
      "role": "cover",
      "prompt_file": "prompts/01-cover-topic.md",
      "image": "01-cover-topic.png",
      "session": "session-01.json",
      "model": "gpt-image-2",
      "parameters": {"aspect_ratio": "3:4", "image_size": "2K"},
      "status": "generated"
    }
  }
}
```

同一 `asset_id` 始终对应同一张可持续编辑的图片。不同资产不得复用编辑 session。CLI 对同一 manifest/session 加跨进程锁，在请求前读取最新状态；同一 manifest 的资产必须依次调度。每次成功生成或编辑后原子写入各元数据文件；跨文件保存中断时保留恢复日志并阻止继续生成，先通过 `recover --journal` 补完本地提交，不能把部分写入的状态当作新编辑起点。

CLI 写入 `status: generated` 和 `actual_dimensions`，表示通过完整解码且已保存。视觉 QA 结果由根技能在交付说明或 `visual-plan.md` 中按 `asset_id` 和图片路径记录，不把机器校验等同于文字、构图与内容检查。读取时兼容旧版 `complete` 状态。

## 执行顺序

1. 验证所有 prompt 文件、直接参考图和 `reference_asset_id`。
2. 按根技能规则解析模型。只有用户本轮明确指定模型时才传 `--model`；否则由 CLI 使用 session、`.env IMAGE_MODEL` 或内置默认值。
3. 无依赖资产可以直接执行；依赖其他资产的项目必须等待锚点成功。
4. `edit` 根据 `asset_id` 从 manifest 取得 session，不接受平台子技能提供 session 路径。
5. 本地保存失败先执行恢复命令，不重复调用 API；锁超时或参数错误先解决原因。网络结果不明时先核查服务端结果，不能盲目再次付费。确认可重试的 API 失败最多重试一次，不静默切换模型。
6. CLI 检查图片完整性并记录真实宽高；根技能核对宽高比、主体、构图、文字和系列一致性，再记录视觉检查结果并交付。

## 文字与后处理

- 不用 SVG、HTML、Canvas 或其他代码渲染替代要求的位图生成。
- 不在生成位图上覆盖、擦除或重画文字。文字错误时更新 prompt，并通过该资产自己的 session 编辑或生成新候选。
- 后处理仅限不改变主要内容的裁剪、缩放、压缩和格式转换。
- 不生成用户未要求的付费备选，不登录、上传或发布到平台。

## CLI

具体参数和 API 映射见 [cli.md](cli.md)。根技能调用 CLI 时，以本技能包根目录为基准解析脚本路径，并在执行前确认文件存在。

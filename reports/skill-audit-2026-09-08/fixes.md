# 7 项审计问题修复说明

日期：2026-09-08。范围：当前仓库；未部署、未提交或推送 Git，未同步其他已安装技能副本。

## 完成内容

| 问题 | 修复 | 主要回归证据 |
| --- | --- | --- |
| F1 配置劫持凭据 | 不再自动加载 CWD `.env`；显式配置仍可用；校验 HTTPS 与 URL 结构；带凭据 POST 禁止自动重定向 | 工作目录恶意配置被忽略；显式配置有效；不安全 endpoint 在请求前被拒绝 |
| F2 并发丢记录 | manifest 全流程跨进程串行锁；session 单独锁；锁内重读、校验与保存 | 两个真实 Python 子进程保留两条资产；同名资产只调用一次模拟 API；并发编辑保留完整历史 |
| F3 路径碰撞 | JSON 元数据路径约束、输入/输出/恢复文件互斥检查；硬链接原子排他发布完整图片 | 同路径 session/image 与 session/manifest 在 API 前拒绝；已有图片字节不被覆盖 |
| F4 伪图片完成 | Pillow 验证结构并完整解码；32 MB / 4000 万像素限制；保存真实尺寸；机器状态改为 generated | 截断输入/响应拒绝；有效 PNG/JPEG/WebP 通过；generated 不等于视觉审核完成 |
| F5 保存失败分叉 | 持久化包含图片与目标元数据的恢复日志；未完成保存阻断后续调用；recover 只重放本地提交 | 图片/session/manifest 写入失败后恢复；恢复再次失败日志保留；恢复不联网、不增加轮次、不覆盖不同图片 |
| F6 目录迁移失败 | 新 session 和 manifest 使用相对路径，同磁盘的外部路径也相对记录；兼容有效旧绝对路径 | 整体移动目录后仍可编辑；旧绝对路径会话仍可使用 |
| F7 session 校验不足 | 校验 version、model、parameters、context、turns、owner 和路径字段；字段错误转为 ValueError | 13 种错误字段结构被拒绝；CLI 返回可解析 JSON 错误而非 traceback |

## 修改文件

- `scripts/generate_image.py`：安全检查、跨进程锁、图像解码、会话 schema、路径、恢复命令。
- `requirements.txt`：新增 Pillow 与 filelock；本机已安装可用版本，未修改全局环境配置。
- `tests/test_generate_image.py`：使用真实可解码 PNG，更新 generated 状态断言。
- `tests/test_security_regressions.py`：26 项新增安全与持久化回归。
- `README.md`、`SKILL.md`、`references/cli.md`、`references/image-generation-contract.md`、`xhs-image/SKILL.md`：同步配置、串行调度、状态、恢复、兼容性规则。
- 本报告目录：保留修复前证据，增加当前回归入口和本修复说明。

## 验证结果

在仓库根目录执行：

```powershell
rtk proxy python -X utf8 -m unittest discover -s tests -v
rtk proxy python -X utf8 reports/skill-audit-2026-09-08/reproduce.py
rtk proxy python -X utf8 -m compileall -q scripts tests reports/skill-audit-2026-09-08/reproduce.py
rtk git diff --check
```

- 全量 54 项测试通过，其中 26 项为新增安全回归。
- 独立安全回归入口 26 项通过。
- Python 编译检查通过；Git diff 空白检查通过。
- 当前 Python 环境没有 Ruff，尝试运行得到 `No module named ruff`，未声称 lint 通过。
- 验证不访问真实生图 API：测试使用假密钥、mock 和禁止网络的断言。真实服务端兼容性、生成质量与线上计费未在本次验证。

## 使用变化与边界

1. CWD 配置需显式传 `--env-file`；API endpoint 必须 HTTPS，不能依赖重定向。
2. 同一 manifest 依次生成，锁最多等待 30 秒；不同 manifest 且独立 session 可并行。
3. session/manifest 使用 `.json`；属于 manifest 的 session 必须通过 manifest/asset_id 编辑，防止绕过资产状态。
4. `parameters` 是请求参数，`actual_dimensions` 是实际宽高；CLI 的 `generated` 不是视觉 QA 通过。主体、文字、构图和尺寸匹配仍由根技能检查并记录。
5. 本地保存失败，使用错误消息里的 `recover --journal 完整路径`，不重复生图。恢复前不要移动目录、改写日志或修改目标文件。日志包含提示词与生成图片，应与其他私有产物一同保管。
6. 已移动的旧版绝对路径会话不会猜测图片位置，使用 `--image 新路径` 显式重新关联；新会话可整体迁移，需保持相对目录结构。
7. 图片发布需要硬链接支持，CLI 在 API 前探测；本机 NTFS 已验证。其他文件系统未实测。不支持时应选择本地支持的输出目录。
8. 若磁盘连恢复日志都无法写入，已返回的 API 结果无法保证持久化，CLI 会明确提示不得自动重复付费请求。恢复日志机制不代表远端 API 支持幂等计费。

原审计“其他静态观察”中的下载重定向逐跳检查、JSON 响应读取阶段的流量上限不属于本次 7 项修复；未声称已完成这些额外加固。

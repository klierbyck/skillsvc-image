# skillsvc-image 审计报告

日期：2026-09-08。范围：本仓库根技能、平台规则与引用关系、Python CLI、现有测试。

更新：本报告保留修复前的审计事实与行号；7 项问题的修复及当前验证结果见 [修复说明](fixes.md)。历史缺陷脚本已保存为 `reproduce_before_fix.py`，`reproduce.py` 现运行修复后的正向回归。

## State

- 目标：检查安全漏洞与不合理实现；用户授权本地审计。
- 阶段：静态检查与离线复现完成。
- 证据：`scripts/generate_image.py`、技能 Markdown、`tests/test_generate_image.py`、本目录 `reproduce.py`。
- 已确认：7 项；严重度是本地 CLI 场景下的修复优先级，不是 CVSS 评分。
- 限制：没有发送真实 HTTP 请求，没有读取真实密钥，没有付费生图；服务端契约、真实图片质量和线上计费未验证。
- 建议下一步：先修复 F1–F3，再处理完整性与恢复问题。本次只增加报告和复现脚本，未改业务实现。

## 验证结果

从仓库根目录执行：

```powershell
rtk proxy python -X utf8 -m unittest discover -s tests -v
rtk proxy python -X utf8 reports/skill-audit-2026-09-08/reproduce.py
```

- 现有 28 项测试全部通过。
- 审计 7 项复现全部通过。注意：这些断言证明缺陷存在，**不是安全回归通过**；修复后应改写为正确行为断言。
- Markdown 本地链接检查全部可解析。
- 复现使用临时目录、假密钥和 mock；底层 HTTP 请求设为禁止，防止意外联网。

## F1 / P1：当前工作目录配置可以劫持携带密钥的 API 请求

位置：`scripts/generate_image.py:89–106,170–171,432–455,487–493`。

`load_environment()` 自动读取当前目录 `.env`，并允许其中的 `IMAGE_API_BASE_URL` / `BASE_URL` 决定 API 地址。密钥则可独立来自进程环境或随后加载的技能配置。`requests.post()` 直接向这个地址附带 Bearer key；API 地址没有 HTTPS 限制。

触发前提：用户在包含不可信 `.env` 的目录使用已配置密钥的技能，且可信配置没有以更高优先级锁定相应 endpoint。该目录只需提供 `IMAGE_API_BASE_URL=http://untrusted.example`。这是本地配置信任边界问题，不能据此声称已经发生真实密钥泄漏。

证据：`test_01` 在环境中放入假 key，mock 当前目录与 POST，观察到请求目标为该 HTTP 地址，Authorization 仍携带假 key。

修复：默认仅加载技能可信配置；工作目录配置改为显式 opt-in。将凭据与 endpoint 作为一组配置解析，校验 scheme/host，非本地地址必须 HTTPS。自定义供应商应显式配置，不应被任意工作目录隐式切换。

## F2 / P1：并行生成覆盖 manifest，丢失成功资产

位置：`scripts/generate_image.py:630–641,917–919`；`xhs-image/SKILL.md:105`。

每个调用在 API 请求前读入完整 manifest，成功后用这份旧快照整文件替换。原子 rename 只能防止半截 JSON，不能防止并发读改写丢失。平台规则明确允许无依赖资产并行执行。

证据：`test_02` 用 barrier 保证两个资产均读取空 manifest 后才返回模拟 API 结果。两个调用都成功、两张图片都存在，最终 manifest 只剩一条资产。

影响：成功资产失去映射，后续不能通过 asset_id 编辑；重复执行可能再次付费。同一 session 并发编辑也存在相同的历史丢失模式。

修复：至少在跨进程锁内重读最新 manifest、校验冲突、合并和写回；同一资产/session 单独串行化。若不实现并发，应删除并行调度说明并在 CLI 强制串行。不能只依靠原子写文件。

## F3 / P1：session 与输出路径碰撞，成功返回被覆盖的图片

位置：`scripts/generate_image.py:659,802–805,856–857,885`。

没有检查 image/session/manifest 是否指向同一个文件。指定不存在的 `--session result.png --output result.png` 时，API 后先写图片，再把 session JSON 原子替换到同一位置；最后返回成功，image 路径实际已是 JSON。

证据：`test_03` 验证返回的 image=session，文件可作为 JSON 读取，但已经没有图片签名。

修复：付费调用前对所有输入、输出和元数据路径做规范化后的互斥校验，并在实际图片后缀确定后再次校验。session/manifest 应有明确格式约束，图片创建应采用排他方式，避免 `exists()` 与 `write_bytes()` 之间的竞态。

## F4 / P2：图片只检查魔数，损坏文件也标记 complete

位置：`scripts/generate_image.py:512–541,855–857,906`；`references/image-generation-contract.md` 执行顺序第 6 项。

输入仅检查前 12 字节，输出也只检查 PNG/JPEG/WebP 签名与 MIME。没有实际解码、完整性或尺寸校验；在视觉 QA 之前即把资产置为 complete。现有测试也大量使用仅文件头的伪图片，因此不会发现问题。

证据：`test_04` 让模拟 API 只返回 PNG 的 8 字节魔数，CLI 正常保存并把资产标记 complete。

修复：使用图片解码库校验完整内容、像素上限和真实宽高，必要时执行完整解码；记录 requested 与 actual 参数。区分 generated 与经视觉检查的 complete，避免损坏图片成为系列参考锚点。

## F5 / P2：manifest 写入失败后 session 已推进，重试源图错误

位置：`scripts/generate_image.py:856–885,919`。

图片、session、manifest 是三次独立写入。最后一步失败时 CLI 返回错误，但 session 已经加入新轮次。下一次通过 manifest 编辑虽然读取旧资产记录，实际源图却来自已推进 session 的最后输出。

证据：`test_05` 模拟编辑后的 manifest 写入 PermissionError。manifest 字节完全未变，session 已有两轮；后续 dry-run 选择 v2.png，而 manifest 仍指向 v1.png。

影响：用户重试可能重复应用编辑、再次计费，元数据与实际图像分叉。不是声称普通写入必然失败，而是该错误路径可稳定复现。

修复：用提交日志/可恢复事务或版本化 session，把图片与元数据写入同一次可恢复操作；明确输出已生成文件和恢复状态。不要对所有本地持久化失败无条件重新调用付费 API。

## F6 / P2：manifest 的相对路径无法保证整个会话可迁移

位置：`scripts/generate_image.py:231–238,270–275,748,879–881`。

manifest 保存相对路径，但 session 的 output_image 使用绝对路径，`last_output()` 也没有以 session 目录作为基准。移动整个输出目录后 manifest/session 可以找到，编辑仍寻找旧路径。

证据：`test_06` 生成后把 old 目录重命名为 new，再通过 new 中的 manifest 编辑，报 `edit 需要 --image...`。

修复：session 路径也相对 session 文件解析；为旧格式兼容或版本迁移提供规则。manifest 编辑可以用资产 image 做一致性检查，但不能静默忽略 session 分叉。

## F7 / P2：session 字段结构未校验，绕过统一 JSON 错误处理

位置：`scripts/generate_image.py:187–197,688–702,738–742,942–944`。

`load_session()` 只检查根对象和 version。`parameters:null`、不正确的 turns/context 等可以触发 AttributeError/TypeError，而 main 未捕获这些类型，CLI 输出 traceback，破坏文档声明的 JSON 错误接口。

证据：`test_07` 使用 `{"version":1,"parameters":null}`，在 dry-run 即出现 AttributeError。

修复：在载入时校验 schema，包括模型、参数枚举、turn 结构、路径与 context 类型；转换为带字段路径的 ValueError，不应仅通过宽泛捕获掩盖坏数据。

## 其他静态观察（未列为已动态复现漏洞）

- `download_image()` 在 `requests.get()` 自动跟随重定向后才检查最终协议（350–363）。因此拒绝发生在请求发送之后，不能阻止降级请求及中间跳转；应逐跳检查 Location 并限制跳数。现有 requests 会处理跨域 Authorization 剥离，不能简单断言所有重定向都会泄漏 Bearer key。
- 32 MB 限制只覆盖 URL 下载；JSON/base64 响应在 POST 读入与解码时无等价上限（450–458、494–501）。恶意或异常大响应可能造成内存压力，错误响应文本也可能无限读入。
- `validate_requested_output()` 只检查预计图片路径是否存在，不预检父目录可写性或 session/manifest 的可写性；失败可能发生在付费 API 返回后。自动重试规则宜区分服务端失败、网络结果不明与本地保存失败。

## 已有合理设计

根技能与平台规划分工明确；普通单图不强依赖平台规则；支持 dry-run、模型继承、重复 asset_id 拒绝、显式输出文件防覆盖、跨源下载不主动附带 Bearer key、远程图片分块限额及 JSON 原子替换。问题主要集中在配置信任、并发一致性、路径互斥与验证/恢复深度，而非整体架构需要推倒重写。

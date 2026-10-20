# Bilibili 采集器卡在字幕阶段时的本地恢复

适用：单视频字幕步骤停滞，或字幕接口要求登录，但公开权限与完整媒体仍可验证。目标是复用已取得的身份、元数据和可选社交数据，补齐媒体与带时间戳 ASR；不必先采集评论、弹幕，也不因字幕鉴权失败就认定公开视频不可获取。所有产物路径使用当前任务的 scratch 目录，不沿用旧脚本硬编码的系统临时目录。

## 恢复顺序

1. **先检查公开权限与标称时长**
   - 调用 Bilibili view API，记录 `bvid`、`cid`、`duration`、`rights`、`is_upower_exclusive/is_upower_preview`。
   - 付费/充电专属或预览态应转为 `auth_required`，不能把预览当完整视频。

2. **不要重跑已成功步骤**
   - 保留已有弹幕、评论 JSON。
   - 采集日志停在字幕阶段且没有结束标记，按“字幕步骤失败”处理；沉默或无 `RESULT_JSON` 不算成功。

3. **用 PlayURL 补媒体**
   - 以 `bvid + cid` 请求 DASH PlayURL，选择一个音频 representation。
   - 立即用带 `User-Agent` 与视频 `Referer` 的 `curl -L --fail` 下载签名 URL；不要把签名 URL写入报告。

4. **做媒体完整性门**
   - 用 `ffprobe` 读取实际音频时长。
   - 与 view API `duration` 比较；误差必须不超过 `max(5s, 2%)`。
   - 通过后才允许 ASR；失败时标记 `truncated_media`，禁止正式 Writer。

5. **本地 MLX ASR 要保存 segments，不只保存纯文本**
   - 使用已缓存的 `mlx-community/whisper-large-v3-turbo` 或显式配置模型。
   - 直接保存完整 ASR JSON，并从 `segments[].start/text` 生成 `[MM:SS] 文本`，避免默认 helper 只落纯文本而丢时间戳。
   - 专名、人名、机构名须结合外部来源校正；不能把校正后的文本冒充官方字幕。
   - 按实际口语设置 ASR 语言，不按中文标题或“双语”标签推断。英文原声配中文字幕仍须用 `en`；把中文硬编码进转录命令会误导识别。
   - 若依赖缺失，或导入栈混入另一 Python 版本的 site-packages，使用隔离执行环境，并清除该进程继承的 `PYTHONPATH`，避免继续加载宿主依赖。只调整本次命令，不修改全局 Python 配置。先验证音频与模型路径；`AUDIO`、`MODEL`、`ASR_JSON` 均传入本次任务的实际路径，`ASR_LANGUAGE` 传入确认的口语语言代码（如 `en` 或 `zh`）：

     ```bash
     env -u PYTHONPATH uv run --python 3.12 --with mlx-whisper python -c 'import json,os,pathlib,mlx_whisper; r=mlx_whisper.transcribe(os.environ["AUDIO"],path_or_hf_repo=os.environ["MODEL"],language=os.environ["ASR_LANGUAGE"],verbose=False); pathlib.Path(os.environ["ASR_JSON"]).write_text(json.dumps(r,ensure_ascii=False),encoding="utf-8")'
     ```

   - 从保存的 `segments` 生成带时间戳文本，再核对最后分段与媒体时长。保留原始 JSON；纯文本 helper 成功不代表时间锚已保存。

6. **重新组成 evidence bundle**
   - 保留原始 ASR JSON 不变，另建契约视图；先检查非空文本、有限且非负的 start、end 不早于 start，以及转录覆盖范围。
   - 契约视图可剔除空文本段。若孤立分段仅有轻微 end < start 且契约允许未知结束时间，可将该段 end 设为 null，保留 start/text，并记录处理数量；不要把 end 伪造为 start，也不要修改原始证据。若倒置广泛出现、start 本身异常或覆盖不完整，应调查或重转录，不能靠批量置空绕过完整性门。
   - 调用 `validate_bundle()` 与 `is_publishable()`，确认通过后才进入 Writer；有文本并不等于契约有效。
   - 记录：标称时长、实际时长、差值、ASR provider/model、原始与契约 segment 数、空段剔除数、未知 end 数、文本字符数、弹幕/评论采样范围。
   - 临时媒体、ASR JSON、转录和日志留在临时工作区；Vault 只写一份正式稿。

## 质量与事实核查提醒

- 政治人物死亡、医学死因、竞选资金与私生活传闻必须分层：已确认 / 初步结论 / 部分可追 / 未证实传闻 / 作者推断。
- “心脏骤停”通常是急救状态，不自动等于基础死因。
- 竞选资金必须区分候选人委员会收款、PAC/个人捐款、独立支出、行业分类，不能写成“某组织或企业直接给了总额”。
- 社交平台复读与高赞只能说明传播和受众情绪，不能验证敏感私生活。

## 验证

先按入口技能选择布局，再执行对应验收；恢复音频不要求退回固定章节。

- 固定章节稿：依次运行 `python3 scripts/verify_report.py /path/to/report.md --mode <selected-mode> --claim-first` 与 `python3 scripts/verify_publishable_report.py /path/to/report.md`。使用实际选定的模式，分别检查 verdict 与失败项，不能只看最后一条命令的退出码。
- `editorial` 稿：执行 `references/interview-editorial-workflow.md` 的原命题与正文双向核对、来源审查及语义验收；旧固定章节门不适用，不报告为通过。
- 两种布局都要通读实际成稿，检查骨架残留、长转录倾倒、事实层级混写、时间锚及双链。仅用音频时，把账单、界面和配置描述归于作者口述，不冒充画面核验。
- 按 Vault 当前写入闸保存一份笔记；文章完成不等于已经晋升 core。末尾修正后重跑受影响检查，最后执行 `qmd update && qmd embed` 并查询标题验证检索。
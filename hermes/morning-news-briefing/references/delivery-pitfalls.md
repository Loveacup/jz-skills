# 交付陷阱

日期 2026-06-03 · 关联：morning-news-briefing

## MEDIA 路径不一致

**症状**：agent 引用 `output/morning-news-{date}-mobile.pdf`，但 render 脚本写在工作区根目录。gateway 报 `Skipping unsafe MEDIA directive path`。

**根因**：SKILL.md 规定 output/ 子目录，但 render_pdfs.py 写 `{base}-mobile.pdf`（工作区根）。

**修复**：render 脚本统一写 `output/` 子目录：
```python
os.makedirs(os.path.join(out_dir, "output"), exist_ok=True)
output_path = os.path.join(out_dir, "output", f"morning-news-{date_str}-mobile.pdf")
```

## TTS 落点错误

**症状**：TTS 输出在 `~/.hermes/audio_cache/tts_{timestamp}.mp3`，而非 `workspace/output/morning-news-{date}.mp3`。

**根因**：`text_to_speech` 工具默认输出到 audio_cache，未指定显式路径。

**修复**：在 text_to_speech 调用中指定 `output_path` 参数指向 workspace/output/。

## 两版 PDF 同时发送

send_message 的 MEDIA 标签对 >2MB 的 PDF 投递不稳定。解决方案：发送时带简短文字 + 单文件 MEDIA 标签，桌面同步备份。

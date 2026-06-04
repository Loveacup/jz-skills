#!/usr/bin/env python3
"""Verify diary files comply with diary-format.md v3.x structural checklist.

Usage:
    python3 verify_diary_compliance.py                 # 校验整个日记目录
    python3 verify_diary_compliance.py <file.md>       # 校验单个文件
    python3 verify_diary_compliance.py <dir>           # 校验指定目录
    python3 verify_diary_compliance.py --quiet ...     # 只打印失败项

Default dir: ~/Documents/Obsidian/AlexCai/50-Self/01_日记/

v2.2 (2026-06-05) — v3.6.0: #6 改为 find()-based fail-loud（格式漂移/半角?/不加粗 不再静默放过；旧 regex m=None 时 fail-open）。
v2.1 (2026-06-04) — v3.5.2: 三问答案深度校验（禁止空洞占位符）。
v2.0 (2026-06-01) — 从"标题存在性扫描"升级为"结构深度校验"。
2026-06 全月重写事故暴露:旧版只查 section 标题在不在,而真正的翻车点
(三问缩写、CC 未按三组拆、治理段缺 info callout、底部段落拍扁、折叠 callout)
旧版一个都查不出。本版按 diary-format.md 逐项加硬校验,且修复旧版"传单文件
即 NotADirectoryError" 的 bug。

退出码: 0 = 全部合规, 1 = 有文件不合规。
"""

import os
import re
import sys

DEFAULT_DIR = os.path.expanduser("~/Documents/Obsidian/AlexCai/50-Self/01_日记")

# ───────── A. 必备 section(标题存在性)─────────
REQUIRED = [
    ("frontmatter",   r"^---\s*\ncreated:"),
    ("abstract 速览", r"\[!abstract\]"),
    ("🎯 每日总结",   r"^## 🎯 每日总结"),
    ("🌤️ 概览",       r"^## 🌤️ 概览"),
    ("⏰ 时间线",      r"^## ⏰ 时间线"),
    ("🤖 AI工作记录", r"^## 🤖 AI助手工作记录"),
    ("info 数据概览", r"\[!info\]"),
    ("📚 知识库",     r"^## 📚 知识库"),
    ("📅 日历事件",   r"^## 📅 日历"),
    ("🏠 个人生活",   r"^## 🏠 个人生活"),
    ("✅ 待办",       r"^## ✅ 待办"),
    ("📝 临时笔记",   r"^## 📝 临时笔记"),
    ("tip 页脚",      r"\[!tip\] 💡 提示"),
]

# ───────── C. 禁止项(出现即 FAIL)─────────
FORBIDDEN = [
    ("折叠 callout (用了 [!xxx]-)", r"\[![a-zA-Z]+\]-"),
    ("🦞 误用 (=OpenClaw 非 CC)",   r"🦞"),
]


def check_required(content):
    return [name for name, pat in REQUIRED
            if not re.search(pat, content, re.MULTILINE)]


def check_forbidden(content):
    return [name for name, pat in FORBIDDEN
            if re.search(pat, content, re.MULTILINE)]


def check_structural(content):
    """B. 深度结构校验 —— 针对 2026-06 翻车的 6 个真问题。条件化,避免误报。"""
    issues = []

    # 1) 三问必须三条齐全(翻车点:三问缩成一句)
    three_q = [
        "今天我做了什么",   # Q1
        "明天我可以构建",   # Q2
        "我可以从过去淘汰",  # Q3
    ]
    missing_q = [q for q in three_q if q not in content]
    if missing_q:
        issues.append(f"三问不全(缺: {'/'.join(missing_q)})")

    # 2) abstract 速览四要素(天气/日历/会话/知识库)
    m = re.search(r"\[!abstract\].*?(?=\n##|\n---|\Z)", content, re.DOTALL)
    if m:
        block = m.group(0)
        if "🌤️" not in block and "天气" not in block:
            issues.append("速览缺天气")
        if "📅" not in block:
            issues.append("速览缺日历")
        if "会话" not in block:
            issues.append("速览缺会话统计")
        if "📚" not in block and "知识库" not in block:
            issues.append("速览缺知识库统计")

    # 无数据/低数据日的合理省略标记 —— 命中则跳过该段的强校验,避免误伤
    NO_DATA = ("当日无", "无会话", "无使用", "无 CC", "无 Claude", "无 agent", "[!note]", "[!NOTE]")

    def _block(header_pat):
        """取该体系标题到下一个 ###/## 之间的文本块。"""
        sm = re.search(header_pat, content, re.MULTILINE)
        if not sm:
            return None
        rest = content[sm.start():]
        nxt = re.search(r"\n###?\s", rest[3:])
        return rest[:nxt.start() + 3] if nxt else rest

    def _bullets(block):
        return sum(1 for ln in block.splitlines() if ln.lstrip().startswith("- "))

    # 3) 体系段(🐴/🏛️/💻)若有实质内容则须带 info 数据概览;无数据日合理省略
    #    (翻车点:治理/CC 段有内容却缺 info callout。但无会话日只写 [!note] 是对的,不罚。)
    for label, pat in [("🐴 助理", r"^### 🐴 助理"),
                       ("🏛️ 治理", r"^### 🏛️ 治理"),
                       ("💻 CC",   r"^### 💻 Claude Code")]:
        block = _block(pat)
        if block is None:
            continue
        if any(m in block for m in NO_DATA):   # 无数据日:合理省略,跳过
            continue
        if _bullets(block) < 3:                 # 内容很少:不强求 info
            continue
        if "[!info]" not in block:
            issues.append(f"{label}段缺 info 数据概览")

    # 4) CC 内容多却平铺无分组 = 真翻车点。
    #    🔴 不强制三组齐全 —— 某组(如 agent_team)当天为 0 时合理省略该子标题。
    #    只在"CC 段内容较多(≥6 条) 却完全没有 #### 子标题"时判失败。
    cc = _block(r"^### 💻 Claude Code")
    if cc and not any(m in cc for m in NO_DATA) and _bullets(cc) >= 6:
        if not re.search(r"^#### ", cc, re.MULTILINE):
            issues.append("CC 内容较多但未分组(应分 🤝协作/💻独立/🤖程序,按当天有数据的组展示)")

    # 5) 底部三段不可拍扁:个人生活/待办/临时笔记之间须有 --- 分隔
    #    (翻车点:底部段落挤在一起没分隔线)
    anchors = ["## 🏠 个人生活", "## ✅ 待办", "## 📝 临时笔记"]
    pos = [content.find(a) for a in anchors]
    if all(p >= 0 for p in pos) and pos == sorted(pos):
        for a, b, label in [(pos[0], pos[1], "个人生活↔待办"),
                            (pos[1], pos[2], "待办↔临时笔记")]:
            if not re.search(r"^---\s*$", content[a:b], re.MULTILINE):
                issues.append(f"底部段落拍扁({label} 间缺 --- 分隔)")

    # 6) 🔴 v3.6.0: 三问答案 fail-loud（find()-based）。旧 regex 当格式漂移（半角?、不加粗）时
    #    m=None → 静默放行 = fail-open。改为 find() 定位问句 → 提取答案 → 不得缺失/占位/<20字。
    q_stems = [
        ("**今天我做了什么推动进展的事情？**", "Q1"),
        ("**明天我可以构建什么未来的事情？**", "Q2"),
        ("**我可以从过去淘汰什么流程？**",    "Q3"),
    ]
    placeholders = {'(无)', '(待补充)', '(待定)', '无', 'N/A', '...', '—'}
    for stem, label in q_stems:
        qpos = content.find(stem)
        if qpos < 0:
            issues.append(f"三问{label}缺失(找不到问句)")
            continue
        rest = content[qpos + len(stem):]
        # 截到下一问句 / 空行 / --- / ## 标题
        cut = len(rest)
        for nstem, _ in q_stems:
            npos = rest.find(nstem)
            if npos >= 0:
                cut = min(cut, npos)
        mb = re.search(r"\n\s*\n", rest)
        if mb:
            cut = min(cut, mb.start())
        md = re.search(r"\n---", rest)
        if md:
            cut = min(cut, md.start())
        answer_clean = re.sub(r'[*_~`#>|\[\]]', '', rest[:cut]).strip()
        if answer_clean in placeholders or len(answer_clean) < 20:
            issues.append(f"三问{label}空洞(答案缺失/占位/<20字: '{answer_clean[:30]}')")

    return issues


def check_file(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    problems = []
    problems += [f"缺 {n}" for n in check_required(content)]
    problems += [f"禁用 {n}" for n in check_forbidden(content)]
    problems += check_structural(content)
    return problems


def is_consolidation(name):
    return "~" in name or "时期" in name or "合并" in name


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    quiet = "--quiet" in sys.argv
    target = os.path.expanduser(args[0]) if args else DEFAULT_DIR

    if os.path.isfile(target):
        files = [target]
    elif os.path.isdir(target):
        files = [os.path.join(target, f) for f in sorted(os.listdir(target))
                 if re.match(r"^\d{4}-\d{2}-\d{2}.*\.md$", f)]
    else:
        print(f"路径不存在: {target}")
        sys.exit(2)

    if not files:
        print("未找到日记文件。")
        sys.exit(0)

    failed = total = 0
    for path in files:
        name = os.path.basename(path)
        if is_consolidation(name):
            if not quiet:
                print(f"  {name:<36} 📦 跳过(合并/时期笔记)")
            continue
        total += 1
        problems = check_file(path)
        if problems:
            failed += 1
            print(f"❌ {name}")
            for p in problems:
                print(f"      - {p}")
        elif not quiet:
            print(f"✅ {name}")

    print(f"\n{total - failed}/{total} 篇日记合规")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

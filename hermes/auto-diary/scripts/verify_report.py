#!/usr/bin/env python3
"""Verify 周/月/年报 comply with their format spec (structural check).

Usage:
    python3 verify_report.py <file.md>          # 按文件名自动判类型
    python3 verify_report.py <file.md> --type monthly|yearly|weekly
    python3 verify_report.py <dir>              # 校验目录下所有报告

类型按文件名判定:
    YYYY年报.md        → yearly
    YYYY-MM月报.md     → monthly
    YYYY-Www周报.md    → weekly

设计原则(承接 verify_diary_compliance.py v2.0 的教训):
  宽松、只查关键结构锚点,避免过严导致 cron "重写也过不了" 的死循环。
  周报兼容历史老格式(无 abstract callout)。

退出码: 0 = 合规, 1 = 不合规, 2 = 路径/类型错误。
"""

import os
import re
import sys

# 每种类型的必备结构锚点(正则,MULTILINE)。宽松:只查骨架。
SPECS = {
    "weekly": {
        "label": "周报",
        "required": [
            ("frontmatter",   r"^---\s*\n"),
            ("type 字段",     r"^type:\s*周报"),
            ("标题",          r"^#\s*周报"),
            ("时间范围",      r"时间范围|至"),
            ("行动项",        r"行动项|待处理|待办"),
            ("数据统计",      r"数据统计|统计"),
            ("日记链接",      r"\[\[.*\d{4}-\d{2}-\d{2}"),
        ],
    },
    "monthly": {
        "label": "月报",
        "required": [
            ("frontmatter",   r"^---\s*\n"),
            ("type 字段",     r"^type:\s*月报"),
            ("标题",          r"^#\s*月报"),
            ("abstract 速览", r"\[!abstract\]"),
            ("🎯 本月主线",   r"^##\s*🎯\s*本月主线"),
            ("📈 月度脉络",   r"^##\s*📈\s*月度脉络"),
            ("📊 数据统计",   r"^##\s*📊\s*数据统计"),
            ("💡 下月重点",   r"^##\s*💡\s*下月重点"),
            ("周报链接",      r"\[\[.*周报|\(无周报\)|无周报"),
        ],
    },
    "yearly": {
        "label": "年报",
        "required": [
            ("frontmatter",   r"^---\s*\n"),
            ("type 字段",     r"^type:\s*年报"),
            ("标题",          r"^#\s*年报"),
            ("abstract 速览", r"\[!abstract\]"),
            ("🎯 年度主线",   r"^##\s*🎯\s*年度主线"),
            ("📈 年度脉络",   r"^##\s*📈\s*年度脉络"),
            ("📊 年度数据",   r"^##\s*📊\s*年度数据"),
            ("💡 来年展望",   r"^##\s*💡\s*来年展望"),
            ("月报链接",      r"\[\[.*月报|\(无月报"),
        ],
    },
}

# 通用禁止项
FORBIDDEN = [
    ("折叠 callout ([!xxx]-)", r"\[![a-zA-Z]+\]-"),
    ("🦞 误用 (=OpenClaw)",    r"🦞"),
]


def detect_type(name):
    if re.search(r"\d{4}年报", name):
        return "yearly"
    if re.search(r"\d{4}-\d{2}月报", name):
        return "monthly"
    if "月报" in name:
        return "monthly"
    if re.search(r"\d{4}-W\d{2}", name) or "周报" in name:
        return "weekly"
    return None


def check_file(path, rtype=None):
    name = os.path.basename(path)
    rtype = rtype or detect_type(name)
    if rtype not in SPECS:
        return rtype, [f"无法判定报告类型(文件名: {name})"]
    with open(path, encoding="utf-8") as f:
        content = f.read()
    problems = []
    for label, pat in SPECS[rtype]["required"]:
        if not re.search(pat, content, re.MULTILINE):
            problems.append(f"缺 {label}")
    for label, pat in FORBIDDEN:
        if re.search(pat, content, re.MULTILINE):
            problems.append(f"禁用 {label}")
    return rtype, problems


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    rtype_override = None
    if "--type" in sys.argv:
        i = sys.argv.index("--type")
        if i + 1 < len(sys.argv):
            rtype_override = sys.argv[i + 1]
    if not args:
        print("用法: verify_report.py <file.md|dir> [--type weekly|monthly|yearly]")
        sys.exit(2)

    target = os.path.expanduser(args[0])
    if os.path.isfile(target):
        files = [target]
    elif os.path.isdir(target):
        files = [os.path.join(target, f) for f in sorted(os.listdir(target))
                 if f.endswith(".md") and detect_type(f)]
    else:
        print(f"路径不存在: {target}")
        sys.exit(2)

    if not files:
        print("未找到报告文件。")
        sys.exit(0)

    failed = 0
    for path in files:
        rtype, problems = check_file(path, rtype_override)
        name = os.path.basename(path)
        label = SPECS.get(rtype, {}).get("label", "?")
        if problems:
            failed += 1
            print(f"❌ {name} [{label}]")
            for p in problems:
                print(f"      - {p}")
        else:
            print(f"✅ {name} [{label}]")

    print(f"\n{len(files) - failed}/{len(files)} 份报告合规")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

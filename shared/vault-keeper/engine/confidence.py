"""复合置信度（**非 AI 自评**）。

confidence = 0.35·源数量信号 + 0.20·信息密度 + 0.20·连接度 + 0.25·AI自评
- AI 自评只占一票（权重 0.25），从 frontmatter `_ai_self` 取（缺省 0.6）。
- 任一冲突 → 触底 0.0 → 绕过矩阵，强制进矛盾裁决。
- **保真信号**（无源外推检测，agent 判断）通过 conflict=True 复用触底通道，见 references/fidelity.md。
权重是起始值，由 sampling.py 的错误率反馈校准（改权重=改逻辑=skill git PR）。
"""
import re

import common  # noqa: F401  (保持与其它引擎模块一致的依赖入口)


def compute(fm, body, conflict=False, cfg=None):
    if conflict:
        return 0.0
    n_src = len(fm.get("sources") or [])
    score = 0.35 if n_src >= 2 else (0.15 if n_src == 1 else 0.0)   # 源数量
    score += 0.20 if len(body) > 400 else 0.10                       # 信息密度
    score += 0.20 * min(len(re.findall(r"\[\[", body)) / 5, 1)       # 连接度
    score += 0.25 * float(fm.get("_ai_self", 0.6))                   # AI 自评（一票）
    return round(min(score, 1.0), 2)


if __name__ == "__main__":
    import sys
    fm, body = common.load(sys.argv[1])
    print(compute(fm, body, conflict=bool(fm.get("contradictions"))))

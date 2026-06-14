"""解析 vault 的 GOVERNANCE.md 阈值块。**不硬编码**——改阈值=编辑 vault（R3）。

GOVERNANCE.md 的「阈值表」节由 key: value 行组成，本模块抓取为 dict。
缺文件或缺项时退回 DEFAULTS。
"""
import os
import re

import common

DEFAULTS = dict(
    promote_conf_low=0.6,       # 低于此 → 退回加工
    promote_conf_high=0.85,     # 高于此 → R2 也可自动晋升
    sample_rate_R1=0.15,        # R1 自动晋升后置抽样率（地板 0.05）
    sample_rate_R2=0.40,        # R2 自动带抽样率
    hub_inlink_threshold=8,     # 入链 ≥ 此值视为枢纽页 → R2
    dedup_overlap_threshold=0.85,
    min_links=3,                # 晋升硬门槛：双链下限
    min_sources=1,              # 晋升硬门槛：sources 下限
    stale_days=180,             # Lint：陈旧阈值
)

_NUM = re.compile(r"^(\w[\w_]*):\s*([\d.]+)\s*$", re.M)


def load():
    cfg = dict(DEFAULTS)
    path = common.vault_path("GOVERNANCE.md")
    if os.path.exists(path):
        txt = open(path, encoding="utf-8").read()
        for k, v in _NUM.findall(txt):
            if k in cfg:
                cfg[k] = float(v) if "." in v else int(v)
    return cfg


if __name__ == "__main__":
    import json
    print(json.dumps(load(), ensure_ascii=False, indent=2))

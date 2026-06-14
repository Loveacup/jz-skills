"""抽样 + 自校准控制环（🟡）。

从 PIPELINE_LOG 取近 N 天自动晋升页，按风险分层抽样 → 88-审计/sampling-*.md 供人 spot-check。
calibrate()：错误率>10% 收紧抽样率，<2% 放松（地板 0.05）。
注：抽样率写在 vault GOVERNANCE.md（改=R3）；本模块只按当前率抽样并给出建议调整。
用法：python3 sampling.py [--days 7]
"""
import os
import re
import random
import argparse
import datetime

import common
import config as C

_ROW = re.compile(r"^\[(\d{4}-\d{2}-\d{2})[^\]]*\][^\n]*?promote\s+(\S+)[^\n]*?risk=(R\d)", re.M)


def recent_promoted(days=7):
    path = common.vault_path("PIPELINE_LOG.md")
    if not os.path.exists(path):
        return []
    txt = open(path, encoding="utf-8").read()
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    return [(d, obj, rk) for d, obj, rk in _ROW.findall(txt) if d >= cutoff]


def calibrate(error_rate, rate, floor=0.05):
    """返回建议的新抽样率（不直接写 GOVERNANCE——改率=R3，由人确认）。"""
    if error_rate > 0.10:
        return min(round(rate * 1.5, 3), 1.0)
    if error_rate < 0.02:
        return max(round(rate * 0.8, 3), floor)
    return rate


def run(days=7, seed=20260614):
    cfg = C.load()
    rnd = random.Random(seed)            # 固定种子保证可复现
    rows = recent_promoted(days)
    rate = {"R1": cfg["sample_rate_R1"], "R2": cfg["sample_rate_R2"]}
    selected = []
    for rk in ("R1", "R2"):
        pool = [r for r in rows if r[2] == rk]
        k = max(1, round(len(pool) * rate[rk])) if pool else 0
        selected += rnd.sample(pool, min(k, len(pool)))

    out = common.vault_path(common.AUDIT, f"sampling-{datetime.date.today()}.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"# 抽样审核 {datetime.date.today()}（近 {days} 天）\n\n")
        f.write(f"> 抽样率 R1={rate['R1']} R2={rate['R2']}。"
                f"审完在下方记缺陷数，运行 calibrate 给出 GOVERNANCE 调整建议。\n\n")
        for d, obj, rk in selected:
            f.write(f"- [ ] {rk} `{obj}`（晋升于 {d}）— 缺陷? ___\n")
    print(f"抽样 {len(selected)}/{len(rows)} → {out}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    a = ap.parse_args()
    run(a.days)

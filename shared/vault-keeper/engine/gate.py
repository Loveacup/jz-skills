"""晋升闸（不变量②「不丢溯源」）。

两层，顺序不可反：
  第一层 硬门槛（确定性 pass/fail）：溯源/双链/必填字段/无断链 —— 任一不过即打回。
  第二层 风险×置信矩阵 → 自动晋升 / 进人工队列 / 退回 / 进矛盾裁决。

退出码：0=自动晋升  10=进人工队列(R2中置信/R3)  20=退回加工  30=进矛盾裁决
用法：python3 gate.py <01-Staging/页.md> [--to 30-Resources/10_AI知识] [--inlinks N]
"""
import sys
import argparse

import common
import config as C
import confidence as CF
import risk as RK


def hard_gates(fm, body, cfg):
    r = []
    if len(fm.get("sources") or []) < cfg["min_sources"]:
        r.append("缺 sources（溯源不变量）")
    if len(common.wikilinks(body)) < cfg["min_links"]:
        r.append(f"双链 < {cfg['min_links']}")
    for k in ("lifecycle_state", "status", "type", "created"):
        if k not in fm:
            r.append(f"缺字段 {k}")
    titles = common.all_titles()
    for link in set(common.wikilinks(body)):
        if link not in titles:
            r.append(f"断链 [[{link}]]")
    return r


def route(rk, conf, cfg):
    if conf < cfg["promote_conf_low"]:
        return 20                                  # 退回加工
    if rk == "R3":
        return 10                                  # 人工
    if rk == "R2" and conf < cfg["promote_conf_high"]:
        return 10                                  # 人工
    return 0                                        # 自动晋升


def run(path, target_dir="30-Resources", inlinks=0):
    cfg = C.load()
    fm, body = common.load(path)
    conflict = bool(fm.get("contradictions"))

    reasons = hard_gates(fm, body, cfg)
    if reasons:
        print("⛔ 硬门槛未过:", "; ".join(reasons))
        return 20

    conf = CF.compute(fm, body, conflict, cfg)
    rk = RK.classify(fm, target_dir, inlinks, cfg)
    code = 30 if conflict else route(rk, conf, cfg)
    verdict = {0: "自动晋升", 10: "进人工队列", 20: "退回加工", 30: "进矛盾裁决"}[code]
    print(f"risk={rk} confidence={conf} → {verdict}（退出码 {code}）")
    return code


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("page")
    ap.add_argument("--to", default="30-Resources")
    ap.add_argument("--inlinks", type=int, default=0)
    a = ap.parse_args()
    sys.exit(run(a.page, a.to, a.inlinks))

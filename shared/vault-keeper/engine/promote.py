"""执行晋升（gate 退出码 0 后调用）：移入 core 区 + 翻 lifecycle_state + 写日志。

写入闸约束：只有本模块（gate 通过后）能置 lifecycle_state=core，且同次必写 PIPELINE_LOG promote。
用法：python3 promote.py <01-Staging/页.md> --to 30-Resources/10_AI知识 [--conf 0.91 --risk R2]
"""
import os
import shutil
import argparse
import datetime

import common
import log as L


def promote(path, to_dir, cli="cc", conf=None, risk=None):
    fm, body = common.load(path)
    fm["lifecycle_state"] = "core"
    if conf is not None:
        fm["confidence"] = conf
    if risk:
        fm["risk"] = risk
    fm.pop("_ai_self", None)                                  # 内部信号不入正本
    fm["modified"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    name = os.path.basename(path)
    dest = common.vault_path(to_dir, name)
    common.dump(path, fm, body)                               # 先写状态
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.move(path, dest)                                   # 再移入 core
    L.append("promote", name[:-3], cli=cli, state="core", conf=conf, risk=risk)
    print("promoted →", dest)
    return dest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("page")
    ap.add_argument("--to", required=True)
    ap.add_argument("--conf", type=float)
    ap.add_argument("--risk")
    a = ap.parse_args()
    promote(a.page, a.to, conf=a.conf, risk=a.risk)

"""core 内风险定级 R1 / R2。

R2 中风险原则：*一处错会向外传播（被多页/未来工作依赖），但仍可改。* 任一触发即 R2：
  1) 晋升常青  2) 改写已有权威 claim  3) 丢信息合并
  4) 枢纽页(入链≥hub)  5) 元知识区(20_Obsidian方法论·02-Plan&CQI)  6) 项目交付区(10-Projects)
R3（对外发布/改治理规则）不在页级定级里，由人工红线把守（见 SKILL.md）。
其余 = R1。
"""
META_ZONES = ["20-Areas/20_Obsidian方法论", "02-Plan&CQI"]


def classify(fm, target_dir, inlinks=0, cfg=None):
    cfg = cfg or {}
    hub = cfg.get("hub_inlink_threshold", 8)
    if fm.get("status") == "常青":                       # 1
        return "R2"
    if fm.get("_authoritative_change"):                  # 2
        return "R2"
    if fm.get("_lossy_merge"):                            # 3
        return "R2"
    if any(z in target_dir for z in META_ZONES):         # 5
        return "R2"
    if target_dir.startswith("10-Projects"):             # 6
        return "R2"
    if inlinks >= hub:                                   # 4
        return "R2"
    return "R1"


if __name__ == "__main__":
    import sys
    import common
    import config as C
    fm, _ = common.load(sys.argv[1])
    target = sys.argv[2] if len(sys.argv) > 2 else "30-Resources"
    inl = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    print(classify(fm, target, inl, C.load()))

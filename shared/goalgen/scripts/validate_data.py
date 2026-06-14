#!/usr/bin/env python3
"""goalgen 数据层校验器（S0.2 的 SPEC/契约）。
契约见 Obsidian 方法论 02(15字段+cross_cli_drivers+execution_options) / 04(19字段+role_bindings+gate_modes) / gate-policy / 25检查点。
退出码 0 = 全通过(GREEN)；非 0 = 失败(RED)，逐项打印。"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
errors = []
def err(m): errors.append(m)
def load(rel):
    p = os.path.join(DATA, rel)
    if not os.path.exists(p): err(f"缺文件: data/{rel}"); return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception as e:
        err(f"data/{rel} 非合法 JSON: {e}"); return None

# ---- 1. cli-registry.json: 15 字段 + cross_cli_drivers + execution_options ----
FIELDS15 = ["identity","launch_method","comm_channel","auth","roles_assumable","nesting_capability",
            "skill_invocation","memory_isolation","injectable_params","intervention_tier",
            "termination_and_escalation","verification_ability","side_effects_and_publish_power",
            "capability_contract_semantics","execution_options"]
SEED_CLIS = {"codex","hermes-default","hermes-regent","claudecode"}
reg = load("cli-registry.json")
if reg is not None:
    cards = reg.get("clis") if isinstance(reg, dict) else reg
    if not isinstance(cards, list): err("cli-registry.json: 顶层须含 clis 列表")
    else:
        ids = set()
        for c in cards:
            cid = (c.get("identity") or {}).get("id", "?")
            ids.add(cid)
            miss = [f for f in FIELDS15 if f not in c]
            if miss: err(f"registry[{cid}] 缺字段: {miss}")
            si = c.get("skill_invocation", {})
            if "cross_cli_drivers" not in si: err(f"registry[{cid}].skill_invocation 缺 cross_cli_drivers")
            eo = c.get("execution_options", {})
            for k in ("models","effort_levels","work_modes"):
                if k not in eo: err(f"registry[{cid}].execution_options 缺 {k}")
        if not SEED_CLIS.issubset(ids): err(f"registry 缺种子 CLI: {SEED_CLIS - ids}")

# ---- 2. goal-schema.json: 19 字段 + role_bindings + gate_modes + schema_version ----
F19 = ["task_id","from","to","type","objective","scope","inputs","context_refs","constraints",
       "acceptance_criteria","timeout","budget","allowed_tools","required_output_format",
       "required_output_destination","required_output_artifacts","roadmap_node","escalation","forbidden"]
gs = load("goal-schema.json")
if gs is not None:
    props = gs.get("properties", {})
    miss = [f for f in F19 if f not in props]
    if miss: err(f"goal-schema 缺 19 字段中的: {miss}")
    for extra in ("role_bindings","gate_modes","schema_version"):
        if extra not in props: err(f"goal-schema 缺顶层 {extra}")
    ac = props.get("acceptance_criteria", {})
    acprops = (ac.get("items", {}) or {}).get("properties", {})
    for tri in ("criterion","verifier","threshold"):
        if tri not in acprops: err(f"goal-schema.acceptance_criteria.items 缺三元组 {tri}")

# ---- 3. pillars-checklist.json: 25 检查点(5维×5), 安全红线唯一硬阻断 ----
pc = load("pillars-checklist.json")
if pc is not None:
    dims = pc.get("dimensions", [])
    if len(dims) != 5: err(f"checklist 维度数={len(dims)}，应=5")
    total = sum(len(d.get("checks", [])) for d in dims)
    if total != 25: err(f"checklist 检查点总数={total}，应=25")
    hard = [d for d in dims if d.get("hard_block")]
    if len(hard) != 1: err(f"checklist 硬阻断维度数={len(hard)}，应唯一(安全红线)")
    elif "安全" not in hard[0].get("name",""): err(f"唯一硬阻断维度应为安全红线，实为 {hard[0].get('name')}")
    for d in dims:
        for ck in d.get("checks", []):
            if not ck.get("pillar"): err(f"checklist 维度[{d.get('name')}] 有检查点未挂承重墙")

# ---- 4. gate-policy.json: gate_default + 6 类门 map + 风险→强度映射 + 不可逆门最强档 ----
GATES = {"binding","audit","termination","escalation","publish","install"}
gp = load("gate-policy.json")
if gp is not None:
    if gp.get("gate_default") not in ("human","auto","hybrid"): err("gate-policy.gate_default 须∈{human,auto,hybrid}")
    gm = gp.get("per_gate", {})
    if not GATES.issubset(gm.keys()): err(f"gate-policy.per_gate 缺门类型: {GATES - set(gm.keys())}")
    strat = gp.get("risk_strength", {})
    for tier in ("routine","high_risk"):
        if tier not in strat: err(f"gate-policy.risk_strength 缺 {tier}")
    irr = gp.get("irreversible_controls", {})
    for ctrl in ("strength","audit_trail","single_publisher_separation","block_on_uncertainty"):
        if ctrl not in irr: err(f"gate-policy.irreversible_controls 缺 {ctrl}")
    if irr.get("strength") != "n-vote-multi-lens": err("不可逆门 strength 应=n-vote-multi-lens(最强档)")

# ---- 5. topology-templates ----
for t in ("星型.md","单CLI-STDD流水线.md"):
    p = os.path.join(DATA, "topology-templates", t)
    if not os.path.exists(p): err(f"缺拓扑模板: data/topology-templates/{t}")
    else:
        body = open(p, encoding="utf-8").read()
        if "role_bindings" not in body: err(f"{t} 缺 role_bindings 占位")
        if "acceptance_criteria" not in body and "验收" not in body: err(f"{t} 缺验收占位")

# ---- 汇总 ----
if errors:
    print(f"RED — {len(errors)} 项不通过:")
    for e in errors: print(f"  ✗ {e}")
    sys.exit(1)
print("GREEN — 数据层全部通过：cli-registry(15字段+cross_cli_drivers+execution_options) / goal-schema(19字段+role_bindings+gate_modes) / pillars-checklist(25检查点,安全红线唯一硬阻断) / gate-policy(6类门+风险分档+不可逆最强档) / 2 拓扑模板")
sys.exit(0)

#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────
# required-actions-validate.py —— call-omp `required_actions` 契约校验器
#
# 【契约唯一真源】枚举/上限一律从 contracts/required-actions.schema.json 派生，
#                本脚本不另行硬编码，schema 改则行为改。纯 stdlib，无第三方依赖。
#
# 输入（二选一）：
#   --json <string>   直接给一段 JSON 文本
#   --file <path>     从文件读 JSON
#   --schema <path>   （可选）覆盖默认 schema 路径（默认：../contracts 同级契约文件）
#
# 输出： 单行 JSON 对象 {"ok":bool,"reason":"..."}
# 退出码： 0 合法 · 1 不合法（含精确 reason）· 3 参数错误 / schema 加载失败
# ─────────────────────────────────────────────────────────────────
import argparse
import json
import os
import sys


def _die_args(reason):
    sys.stdout.write(json.dumps({"ok": False, "reason": reason}, ensure_ascii=False) + "\n")
    sys.exit(3)


def _emit(ok, reason):
    sys.stdout.write(json.dumps({"ok": bool(ok), "reason": reason}, ensure_ascii=False) + "\n")
    sys.exit(0 if ok else 1)


def _is_int(x):
    # JSON true/false 在 Python 是 bool（int 子类），须显式排除，否则会被当整数上限
    return isinstance(x, int) and not isinstance(x, bool)


def _check_len_constraints(node, name):
    for key in ("minLength", "maxLength"):
        if key in node:
            v = node[key]
            if not _is_int(v) or v < 0:
                _die_args("schema %s.%s 须为非负整数" % (name, key))


def load_schema(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            schema = json.load(fh)
    except FileNotFoundError:
        _die_args("schema 文件不存在: %s" % path)
    except (OSError, ValueError) as exc:
        _die_args("schema 加载失败: %s" % exc)
    # 严格结构自检：凡后续会被解引用的节点，此处逐一验型，
    # 任何结构不足一律 → 单行 JSON + 退出 3（绝不放行到 validate 触发 AttributeError/traceback）。
    if not isinstance(schema, dict) or schema.get("type") != "array":
        _die_args("schema 顶层 type 须为 array")
    if "maxItems" in schema and (not _is_int(schema["maxItems"]) or schema["maxItems"] < 0):
        _die_args("schema maxItems 须为非负整数")
    if "uniqueItems" in schema and not isinstance(schema["uniqueItems"], bool):
        _die_args("schema uniqueItems 须为布尔")
    items = schema.get("items")
    if not isinstance(items, dict) or items.get("type") != "object":
        _die_args("schema items 须为 type=object 的对象")
    if "additionalProperties" in items and not isinstance(items["additionalProperties"], bool):
        _die_args("schema items.additionalProperties 须为布尔")
    required = items.get("required", [])
    if not isinstance(required, list) or any(not isinstance(k, str) for k in required):
        _die_args("schema items.required 须为字符串数组")
    props = items.get("properties")
    if not isinstance(props, dict) or "kind" not in props or "reason" not in props:
        _die_args("schema items.properties 缺 kind/reason")
    # kind：type=string + 非空且元素均为非空字符串的 enum
    kind = props["kind"]
    if not isinstance(kind, dict) or kind.get("type") != "string":
        _die_args("schema kind.type 须为 string")
    kinds = kind.get("enum")
    if not isinstance(kinds, list) or not kinds or any((not isinstance(k, str) or k == "") for k in kinds):
        _die_args("schema kind.enum 须为非空的、元素均为非空字符串的数组")
    # reason：type=string + 长度上下限（若存在）须非负整数
    reason = props["reason"]
    if not isinstance(reason, dict) or reason.get("type") != "string":
        _die_args("schema reason.type 须为 string")
    _check_len_constraints(reason, "reason")
    # targets（可选）：type=array + item 数上下限须非负整数 + items.type=string + 其长度限同上
    tgt = props.get("targets")
    if tgt is not None:
        if not isinstance(tgt, dict) or tgt.get("type") != "array":
            _die_args("schema targets.type 须为 array")
        for key in ("minItems", "maxItems"):
            if key in tgt and (not _is_int(tgt[key]) or tgt[key] < 0):
                _die_args("schema targets.%s 须为非负整数" % key)
        t_item = tgt.get("items")
        if not isinstance(t_item, dict) or t_item.get("type") != "string":
            _die_args("schema targets.items.type 须为 string")
        _check_len_constraints(t_item, "targets.items")
    return schema


def _str_constraints(node):
    return node.get("minLength"), node.get("maxLength")


def validate(value, schema):
    """按 schema 派生的约束逐层校验，返回 (ok, reason)。"""
    items = schema["items"]
    props = items["properties"]
    required = items.get("required", [])
    allow_extra = items.get("additionalProperties", True)
    max_items = schema.get("maxItems")
    unique = schema.get("uniqueItems", False)

    kinds = props["kind"]["enum"]
    r_min, r_max = _str_constraints(props["reason"])
    tgt = props.get("targets", {})
    t_min_items = tgt.get("minItems")
    t_max_items = tgt.get("maxItems")
    t_item = tgt.get("items", {})
    ti_min, ti_max = _str_constraints(t_item)

    # 顶层：数组
    if not isinstance(value, list):
        return False, "顶层须为数组"
    if max_items is not None and len(value) > max_items:
        return False, "动作数 %d 超过上限 %d" % (len(value), max_items)

    seen = []
    for i, action in enumerate(value):
        loc = "第%d个动作" % (i + 1)
        if not isinstance(action, dict):
            return False, "%s 须为对象" % loc
        # 未知键
        if allow_extra is False:
            extra = [k for k in action if k not in props]
            if extra:
                return False, "%s 含未知键: %s" % (loc, ", ".join(sorted(extra)))
        # 必填键
        for key in required:
            if key not in action:
                return False, "%s 缺必填键: %s" % (loc, key)
        # kind
        kind = action.get("kind")
        if not isinstance(kind, str) or kind not in kinds:
            return False, "%s kind=%r 非法（须为 %s 之一）" % (loc, kind, "/".join(kinds))
        # reason
        reason = action.get("reason")
        if not isinstance(reason, str):
            return False, "%s reason 须为字符串" % loc
        if r_min is not None and len(reason) < r_min:
            return False, "%s reason 为空（须非空）" % loc
        if r_max is not None and len(reason) > r_max:
            return False, "%s reason 长度 %d 超过上限 %d" % (loc, len(reason), r_max)
        # targets（可选）
        if "targets" in action:
            targets = action["targets"]
            if not isinstance(targets, list):
                return False, "%s targets 须为数组" % loc
            if t_min_items is not None and len(targets) < t_min_items:
                return False, "%s targets 至少 %d 个" % (loc, t_min_items)
            if t_max_items is not None and len(targets) > t_max_items:
                return False, "%s targets 数 %d 超过上限 %d" % (loc, len(targets), t_max_items)
            for j, t in enumerate(targets):
                if not isinstance(t, str):
                    return False, "%s targets[%d] 须为字符串" % (loc, j)
                if ti_min is not None and len(t) < ti_min:
                    return False, "%s targets[%d] 为空（须非空）" % (loc, j)
                if ti_max is not None and len(t) > ti_max:
                    return False, "%s targets[%d] 长度 %d 超过上限 %d" % (loc, j, len(t), ti_max)
        # 去重（保序）：整对象重复即拒
        if unique:
            norm = json.dumps(action, sort_keys=True, ensure_ascii=False)
            if norm in seen:
                return False, "%s 与在先动作完全重复（不允许重复动作对象）" % loc
            seen.append(norm)

    return True, "required_actions 合法（%d 个动作）" % len(value)


class _JsonArgParser(argparse.ArgumentParser):
    """接管 argparse 的错误路径：缺参/非法参不再往 stderr 打 usage，
    而是走 _die_args 输出单行 {ok:false,reason} 到 stdout 并退出 3。"""

    def error(self, message):  # noqa: D401 - argparse hook
        _die_args("参数错误: %s" % message)

    def exit(self, status=0, message=None):
        # -h/--help 已把帮助打到 stdout 后走 status=0，放行；其余非零一律归 3 + JSON
        if status == 0 and message is None:
            sys.exit(0)
        _die_args(message.strip() if message else "参数错误")


def main():
    parser = _JsonArgParser(add_help=True, description="校验 call-omp required_actions 契约")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--json", dest="json_text", help="直接给一段 JSON 文本")
    src.add_argument("--file", dest="file_path", help="从文件读 JSON")
    here = os.path.dirname(os.path.abspath(__file__))
    default_schema = os.path.join(here, "..", "contracts", "required-actions.schema.json")
    parser.add_argument("--schema", dest="schema_path", default=default_schema,
                        help="覆盖默认 schema 路径")
    args = parser.parse_args()

    schema = load_schema(args.schema_path)

    if args.json_text is not None:
        raw = args.json_text
    else:
        try:
            with open(args.file_path, "r", encoding="utf-8") as fh:
                raw = fh.read()
        except (OSError, ValueError) as exc:
            _die_args("读取 --file 失败: %s" % exc)

    try:
        value = json.loads(raw)
    except ValueError as exc:
        _emit(False, "输入非合法 JSON: %s" % exc)

    ok, reason = validate(value, schema)
    _emit(ok, reason)


if __name__ == "__main__":
    main()

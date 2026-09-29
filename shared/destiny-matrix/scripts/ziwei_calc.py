#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""使用统一 time_context 计算紫微斗数三合派盘。

以本地视太阳日期/时辰为输入；所有调用显式传入 analysis_as_of。
闰月保留中分法与 fix_leap=False 两套算法结果，不使用人生事件择优。
"""
import sys
import json
from datetime import datetime

try:
    import iztro_py
    from iztro_py.i18n.locales.zh_CN import translations as ZH_CN
    _IZTRO_IMPORT_ERROR = None
except ImportError as exc:
    iztro_py = None
    ZH_CN = {}
    _IZTRO_IMPORT_ERROR = exc


# ============================================================
# i18n 翻译表
# ============================================================

def _build_lookup():
    flat = {}
    for k, v in ZH_CN.items():
        if isinstance(v, dict):
            for sub_k, sub_v in v.items():
                if isinstance(sub_v, dict):
                    for ssk, ssv in sub_v.items():
                        flat[ssk] = ssv
                else:
                    flat[sub_k] = sub_v
        else:
            flat[k] = v
    flat['changshengChang'] = '长生'
    flat['siChang'] = '死'
    flat['jueChang'] = '绝'
    flat['xishenJiang'] = '息神'
    flat['tianyue2'] = '天月'
    return flat


LOOKUP = _build_lookup()


def L(s):
    if not s or not isinstance(s, str):
        return s
    return LOOKUP.get(s, s)


def localize_star(star):
    return {
        '名称': L(star.name),
        '亮度': star.brightness or '',
        '四化': star.mutagen or '',
        '类型': star.type,
    }






# ============================================================
# v3 · 闰月检测
# ============================================================

def detect_leap_month(lunar):
    raw_month = lunar.getMonth()
    return {
        "is_leap": raw_month < 0,
        "lunar_year": lunar.getYear(),
        "lunar_month": abs(raw_month),
        "lunar_day": lunar.getDay(),
        "lunar_month_chinese": lunar.getMonthInChinese(),
    }


# ============================================================
# 核心排盘
# ============================================================

def _build_chart(lunar, hour_idx, gender_zh, as_of, *, fix_leap=True):
    raw_month = lunar.getMonth()
    lunar_text = f"{lunar.getYear()}-{abs(raw_month)}-{lunar.getDay()}"
    astrolabe = iztro_py.by_lunar(
        lunar_text, hour_idx, gender_zh,
        is_leap_month=raw_month < 0, fix_leap=fix_leap, language="zh-CN",
    )
    base = {
        "公历日期": astrolabe.solar_date, "农历日期": astrolabe.lunar_date,
        "四柱": astrolabe.chinese_date, "出生时辰": astrolabe.time,
        "时辰范围": astrolabe.time_range, "太阳星座": astrolabe.sign,
        "生肖": astrolabe.zodiac,
        "命宫地支": L(astrolabe.earthly_branch_of_soul_palace),
        "身宫地支": L(astrolabe.earthly_branch_of_body_palace),
        "命主": L(astrolabe.soul), "身主": L(astrolabe.body),
        "五行局": astrolabe.five_elements_class,
    }
    palaces = []
    for palace in astrolabe.palaces:
        item = {
            "宫位": L(palace.name), "地支": L(palace.earthly_branch),
            "天干": L(palace.heavenly_stem), "是否身宫": palace.is_body_palace,
            "是否来因宫": palace.is_original_palace,
            "主星": [localize_star(star) for star in palace.major_stars],
            "辅星": [localize_star(star) for star in palace.minor_stars],
            "杂耀": [localize_star(star) for star in palace.adjective_stars],
            "长生十二神": L(palace.changsheng12) if palace.changsheng12 else "",
            "博士十二神": L(palace.boshi12) if palace.boshi12 else "",
            "将前十二神": L(palace.jiangqian12) if palace.jiangqian12 else "",
            "岁前十二神": L(palace.suiqian12) if palace.suiqian12 else "",
            "小限年龄": palace.ages,
        }
        if palace.decadal:
            item["大限"] = {
                "范围": palace.decadal.range,
                "天干": L(palace.decadal.heavenly_stem),
                "地支": L(palace.decadal.earthly_branch),
            }
        palaces.append(item)

    horoscope = astrolabe.horoscope(as_of)
    def horo_to_dict(item):
        if item is None:
            return None
        raw = item.model_dump() if hasattr(item, "model_dump") else dict(item)
        result = {}
        for key, value in raw.items():
            if value is None:
                continue
            if key == "name":
                result["名称"] = value
            elif key == "index":
                result["宫位序号"] = value
            elif key == "heavenly_stem":
                result["天干"] = L(value)
            elif key == "earthly_branch":
                result["地支"] = L(value)
            elif key == "palace_names":
                result["宫位排列"] = [L(name) for name in value]
            elif key == "mutagen":
                result["四化"] = [L(star) for star in value]
            elif key == "range":
                result["年龄范围"] = value
            elif key == "stars" and value:
                result["流耀"] = [
                    [L(star.get("name", "")) if isinstance(star, dict)
                     else L(getattr(star, "name", str(star))) for star in cell]
                    for cell in value
                ]
        return result
    horoscope_data = {
        "查询日期": as_of, "虚岁": horoscope.nominal_age,
        "实岁": horoscope.age if isinstance(horoscope.age, int) else None,
        "当前大限": horo_to_dict(horoscope.decadal),
        "当前流年": horo_to_dict(horoscope.yearly),
        "当前流月": horo_to_dict(horoscope.monthly),
        "当前流日": horo_to_dict(horoscope.daily),
    }
    return {"基础信息": base, "十二宫": palaces, "运限": horoscope_data}


def calc_ziwei(time_context, calculation_sex=None, analysis_as_of=None):
    from _common import CalcError, InputError
    if iztro_py is None:
        raise CalcError("missing_dependency", "ziwei", str(_IZTRO_IMPORT_ERROR))
    if calculation_sex not in {"m", "f"}:
        return {
            "status": "missing_input", "data": None, "candidates": [],
            "limitations": ["紫微排盘所需 calculation_sex 未提供；不默认性别"],
        }
    if time_context.get("precision") != "minute":
        if not analysis_as_of:
            raise InputError("missing_analysis_as_of", "analysis_as_of",
                             "horoscope 必须接收固定 analysis_as_of")
        from _common import candidate_contexts
        groups = {}
        for row in candidate_contexts(time_context):
            result = calc_ziwei(row["time_context"], calculation_sex, analysis_as_of)
            data = result.get("data")
            if not isinstance(data, dict):
                continue
            identity = json.dumps(data, ensure_ascii=False, sort_keys=True, default=str)
            candidate = groups.setdefault(identity, {
                "data": data, "validity": [], "limitations": [],
            })
            validity = row["validity"]
            if (candidate["validity"] and "start_utc" in validity
                    and candidate["validity"][-1].get("end_utc") == validity["start_utc"]):
                candidate["validity"][-1]["end_utc"] = validity["end_utc"]
            else:
                candidate["validity"].append(validity)
        return {
            "status": "partial", "data": None,
            "candidates": list(groups.values()),
            "limitations": ["非精确时刻；按地方视太阳日/时辰边界保留不同紫微盘候选"],
        }
    if not analysis_as_of:
        from _common import InputError
        raise InputError("missing_analysis_as_of", "analysis_as_of",
                         "horoscope 必须接收固定 analysis_as_of")
    try:
        as_of_date = datetime.strptime(analysis_as_of, "%Y-%m-%d").date()
    except ValueError as exc:
        from _common import InputError
        raise InputError("invalid_analysis_as_of", "analysis_as_of",
                         "analysis_as_of 必须为 YYYY-MM-DD") from exc
    solar_dt = datetime.fromisoformat(time_context["local_apparent_datetime"])
    source_subject = time_context.get("input", {}).get("subject", {})
    lunar_input = source_subject.get("lunar_date")
    if lunar_input is not None:
        from _common import lunar_date_to_lunar
        lunar, _ = lunar_date_to_lunar(lunar_input)
        lunar_source = "直接使用 intake 原农历年月日与闰月标记"
    else:
        from _common import local_solar_to_lunar
        solar = local_solar_to_lunar(solar_dt)
        lunar = solar.getLunar()
        lunar_source = "本地视太阳公历经JD适配至 lunar-python 混合历"
    hour_idx = __import__("_common").hour_to_idx(solar_dt.hour, solar_dt.minute)
    gender_zh = "男" if calculation_sex == "m" else "女"
    main_chart = _build_chart(lunar, hour_idx, gender_zh, as_of_date.isoformat(),
                              fix_leap=True)
    main_chart["排盘算法"] = f"iztro-py by_lunar；{lunar_source}；fix_leap=True"
    leap = detect_leap_month(lunar)
    if leap["is_leap"]:
        alternative = _build_chart(lunar, hour_idx, gender_zh,
                                   as_of_date.isoformat(), fix_leap=False)
        alternative["排盘算法"] = "iztro-py by_lunar；is_leap_month=True；fix_leap=False"
        main_chart["闰月候选"] = {
            "状态": f"闰{leap['lunar_month']}月 {leap['lunar_month_chinese']}",
            "中分法": main_chart.copy(),
            "闰月独立算法": alternative,
            "说明": "两个算法并列呈现；不依据历史事件择优",
        }
    return {"status": "ok", "data": main_chart, "candidates": [],
            "limitations": []}


# ============================================================
# CLI
# ============================================================

def parse_args(argv):
    from _common import InputError
    result = {"intake": None, "subject": "primary"}
    i = 0
    while i < len(argv):
        key, sep, value = argv[i].partition("=")
        if key not in {"--intake", "--subject"}:
            raise InputError("unknown_argument", key, f"未知参数: {argv[i]}")
        if not sep:
            i += 1
            value = argv[i] if i < len(argv) else None
        if key == "--intake":
            if not value:
                raise InputError("missing_argument", key, "--intake 需要文件路径")
            result["intake"] = value
        elif value in {"primary", "partner"}:
            result["subject"] = value
        else:
            raise InputError("invalid_argument", key, "subject 必须为 primary 或 partner")
        i += 1
    if not result["intake"]:
        raise InputError("missing_argument", "--intake", "必须提供 --intake")
    return result


def main():
    from _common import InputError, normalize_birth_time
    try:
        args = parse_args(sys.argv[1:])
        with open(args["intake"], encoding="utf-8") as stream:
            intake = json.load(stream)
        if args["subject"] == "primary":
            subject, time_input = intake.get("subject"), intake.get("time_input")
        else:
            partner = intake.get("synastry", {}).get("partner")
            subject = partner.get("subject") if isinstance(partner, dict) else None
            time_input = partner.get("time_input") if isinstance(partner, dict) else None
        if not isinstance(subject, dict) or not isinstance(time_input, dict):
            raise InputError("missing_subject", args["subject"], "intake 缺少 subject/time_input")
        context = normalize_birth_time(subject, time_input, as_of=intake.get("analysis_as_of"))
        print(json.dumps(calc_ziwei(context, subject.get("calculation_sex"),
                                    intake.get("analysis_as_of")),
                         ensure_ascii=False, default=str))
    except Exception as exc:
        from _common import CalcError
        code = 2 if isinstance(exc, (InputError, FileNotFoundError, json.JSONDecodeError)) else 1
        print(json.dumps({"status": "error", "errors": [{
            "code": getattr(exc, "code", "calculation_error"),
            "path": getattr(exc, "path", ""),
            "message": getattr(exc, "message", str(exc)),
        }]}, ensure_ascii=False))
        print(f"ziwei_calc: {exc}", file=sys.stderr)
        sys.exit(code)


if __name__ == "__main__":
    main()


if __name__ == '__main__':
    main()

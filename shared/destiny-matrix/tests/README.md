# destiny-matrix v5 测试说明

本目录的永久测试分两类：

- `test_time_pipeline.py`、`test_calculator_boundaries.py` 使用可核查的时区、历法、节气与子时行为锚点；农历输入保留闰月标记并经 lunar-python 混合历法/JD 转换。
- `run_regression.py` 仅将历史公开命例作为旧输入管线样本，检查新 `chart_bundle` 契约与 cast/astro 参数传递；`CONTRACT_OK` **不证明出生资料、命理解读或预测准确**。1582 年以前的太阳历记录必须明确公历/儒略历；来源为农历时按其原农历字段转换，出生资料仍维持原有未核状态。

## 运行

```bash
"$DM_PY" -m unittest discover -s tests -p 'test_time_pipeline.py' -v
"$DM_PY" -m unittest discover -s tests -p 'test_calculator_boundaries.py' -v
"$DM_PY" tests/run_regression.py
"$DM_PY" scripts/cast_chart.py 1990-07-15 12:00 m Chicago --lat=41.88 --lon=-87.63 --tz=-5
```

不要以同一个 astro 实现的直调对照称为独立引擎核验。`run_regression.py` 的锚点若恢复使用，必须逐项附真实来源与定位、计算方法、依赖版本和容差；缺字段或来源未核验时以配置错误退出，不根据当前实现生成 expected。`nullable_anchors` 只用于有依据记录的公开史料争议，不屏蔽计算、依赖或子进程错误。

## 独立数值来源

- 香港天文台《2024 年公历与农历日期对照表》原页记录 2024-02-04 立春 16:27（UTC+08:00，分钟精度）：<https://www.hko.gov.hk/tc/gts/astron2024/files/2024cal02.pdf>。
- 香港天文台节气资料页记录 2026-02-04 立春 04:02（UTC+08:00，分钟精度）：<https://www.hko.gov.hk/tc/gts/astronomy/Solar_Term.htm>。
- 香港天文台 2023 年公历与农历日期对照表记录 2023-03-22 为闰二月初一：<https://www.hko.gov.hk/tc/gts/time/calendar/text/files/T2023c.txt>；用于检验农历转换，不验证任何个案来源。
- 子时换日测试采用执行方案已记录的 lunar-python 1.4.8 探针：2000-01-01 23:30，`setSect(2)` 为戊午日/甲子时，`setSect(1)` 为己未日/甲子时；测试只锁定该明确 API 行为，不将其提升为唯一传统流派。
- 芝加哥测试锚点来自执行方案记录的 Swiss Ephemeris 2.10.3.2 探针：1990-07-15 12:00、UTC−05:00、经度 −87.63，UTC=17:00，均时差约 −5.9328927 分钟，地方视太阳时相对钟表时约 −56.4528927 分钟。独立近似公式来源 NOAA《General Solar Position Calculations》：<https://gml.noaa.gov/grad/solcalc/solareqns.PDF>。

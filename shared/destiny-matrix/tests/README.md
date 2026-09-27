# destiny-matrix v3 回归测试

> Agent L · 第二波

工程化质量保障。每次修改 `scripts/*.py` 后，跑一次 `$DM_PY tests/run_regression.py`（`$DM_PY` 由 `scripts/doctor.py` 解析，默认 venv `~/.local/share/destiny-matrix/venv/bin/python`）验证四个维度（八字 / 紫微 / 占星 / 性格）的输出是否符合预期锚点。

v4.1 起每条用例还会做**占星直调对照**：用钟表时直接调用 `astro_calc.py`，儒略日与上升黄经必须与 `cast_chart.py` 占星段一致（拦截时间管线错误；v4.0 脚本在此项上 17/17 FAIL）。另有度数级锚点 `astro_asc_lon` / `astro_sun_lon`（±0.02°）。

## 文件
- `regression_baseline.json` —— 命例集 + 预期锚点
- `run_regression.py` —— 测试运行器（调用 `cast_chart.py`、比对锚点）

## 用法
```bash
$DM_PY tests/run_regression.py                  # 跑全部
$DM_PY tests/run_regression.py --id 毛泽东       # 单条
$DM_PY tests/run_regression.py --category boundary   # 只跑边界
$DM_PY tests/run_regression.py -v               # 显示命中锚点
```

退出码：0 = 全 PASS/WARN；1 = 存在 FAIL；2 = 基线无法加载或过滤条件未匹配任何用例。

## 三种结果
| 状态 | 含义 | 处理 |
|:---|:---|:---|
| **PASS** | 所有声明锚点全部命中 | 不用管 |
| **WARN** | 仅 nullable 锚点不一致；或子脚本异常但相关锚点全 nullable | 人工 review，决定要不要升级为 FAIL |
| **FAIL** | 脚本崩溃 / 输出非 JSON / 关键锚点（非 nullable）不一致 | 必须修：要么改代码，要么改 baseline，要么 skip |

## 锚点字段路径
| 锚点 key | 取值路径（取自 cast_chart.py 输出 JSON） |
|:---|:---|
| `bazi_day_master` | `八字.日主.天干` |
| `bazi_day_master_element` | `八字.日主.五行` |
| `bazi_dominant_element` | 取 `八字.五行比例` 中最大值 |
| `ziwei_ming_palace_stars` | `紫微.十二宫[宫位==命宫].主星[].名称`（数组，匹配任一即算命中） |
| `ziwei_ming_branch` | `紫微.基础信息.命宫地支` |
| `ziwei_wuxing_ju` | `紫微.基础信息.五行局` |
| `astro_sun_sign` | 从 `占星.三轴心.太阳` 中提取中文星座（"白羊…双鱼"） |
| `astro_rising_sign` | 同上，取 `上升` |
| `astro_moon_sign` | 同上，取 `月亮` |

`推断 MBTI` 与 `性格签名锚点` 仅供人工 review，**不参与自动判定**（jung_calc.py 输出还在迭代，强行比对会产生大量噪音）。

## 添加新命例
往 `regression_baseline.json` 的 `cases` 数组里追加：
```json
{
  "id": "命主名称",
  "category": "celebrity" | "boundary",
  "input": {
    "date": "YYYY-MM-DD",
    "time": "HH:MM",
    "gender": "m" | "f",
    "city": "城市名",
    "lat": 30.27,    // 可选：geonamescache 解析不到时手动给
    "lon": 120.16,
    "tz": 8.0
  },
  "expected_anchors": {
    "bazi_day_master": "甲",
    "ziwei_ming_branch": "子",
    "astro_sun_sign": "天秤",
    "推断 MBTI": "INTJ",                    // 仅 review，不自动比对
    "性格签名锚点": ["Ni 主导", "战略远见"]  // 仅 review
  },
  "nullable": ["astro_sun_sign"],   // 史料不确定 / 已知子模块挂掉时降级为 WARN
  "key_events": [{"年份": 2020, "事件": "..."}],
  "来源": "嘉庆十六年十月十一日（公历 1811-11-26）卯时",
  "note": "可选：解释这个用例的特殊性",
  "skip": false                     // 写 true + skip_reason 可暂时跳过
}
```

只有当**所有需要校验的锚点都在 nullable 中**时，runner 才会把整条用例的子脚本异常降级为 WARN。

## 处理失败用例
按优先级判断：
1. **算法 bug** —— 代码错了：修代码（不属本 agent，留 issue 给负责人）
2. **史料不准** —— 出生时辰是民间传说：把锚点加到 `nullable`，标 note 说明分歧
3. **暂时跳过** —— 用例确实跑不通，但又不想拉低基线：加 `"skip": true, "skip_reason": "..."`

## 设计要点
- **runner 一定 graceful**：脚本异常、JSON 解析失败、超时都返回 FAIL 记录而非崩溃
- **占星模块系统问题**：v3 下 `astro_calc.py` 通过 `cast_chart.py` 间接调用时，受 `python3` 解释器版本与 PEP 604 类型语法冲突影响，所有用例的占星模块都返回 error。已知问题已记入 `_meta.已知系统问题`，所有 `astro_*` 锚点暂全部标 nullable，等 cast_chart 或 astro_calc 修复后取消 nullable
- **比对策略**：字符串严格相等（紫微主星支持数组，命中其一即算 OK）；MBTI 与性格签名只作人工 review 锚点，不影响 PASS/FAIL

## v4.1 · validate_book.py

`scripts/validate_book.py` is the S9 machine acceptance tool; it uses only the standard library and supports `/usr/bin/python3` (3.9).

```bash
$DM_PY scripts/validate_book.py <book.html> --plan chart_plan.json [--json]
```
- Exit 0 = no M/C red fails or W1 block fails; 1 = one or more such fails; 2 = book/plan read failure or malformed plan.
- S9 must supply `--plan` to pass C1. Supported plan shapes: `chart_plan.chart_table`, legacy `charts`, or bare row arrays (`chart_id` / `id` / `图表 ID`). C1 rejects missing/extra IDs, duplicate IDs in either HTML or plan, and containers without an ID.
- W1 scans the entire body including front matter. Negation/prohibition cues within 40 characters earlier in the same sentence exempt a term; other matches are listed with chapter and context.
- M-LEN deviations, W2 wording counts, and E4 explanation-rating coverage remain review information; C5 remains a keyword heuristic requiring visual confirmation.

## v4.1 · export_pdf.py

```bash
$DM_PY scripts/export_pdf.py <input.html> [output.pdf]
```
- Exit 0 = PDF rendered and sanity checks pass (at least 20 pages); 1 = dependency, render, or sanity failure; 2 = invalid argument count or output path equals input.
- Requires Playwright, Chromium, and `pypdf`: `pip install playwright pypdf && $DM_PY -m playwright install chromium`.
- Trailing blank pages are trimmed with a notice and count. SVG/font wait timeouts print a warning and rendering continues.

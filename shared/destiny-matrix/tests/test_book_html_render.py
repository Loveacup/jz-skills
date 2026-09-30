import json
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import book_html as bh  # noqa: E402

BUNDLE = ROOT / "tests" / "fixtures" / "chart_bundle.example.json"


class CoreChartRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dims = json.loads(BUNDLE.read_text(encoding="utf-8"))["dimensions"]

    def planets(self, names=("太阳", "月亮", "水星", "木星", "土星")):
        table = self.dims["astrology"]["data"]["十大行星+北交+凯龙+莉莉丝"]
        return [{"名称": n, "黄经": table[n]["黄经"], "逆行": table[n]["逆行"]} for n in names]

    def wheel(self, **overrides):
        data = self.dims["astrology"]["data"]
        args = {"cusps": data["十二宫始黄经"], "asc": data["ASC_MC_原始黄经"]["ASC"],
                "mc": data["ASC_MC_原始黄经"]["MC"], "planets": self.planets(), "aspects": []}
        args.update(overrides)
        return bh.wheel_svg(args["cusps"], args["asc"], args["mc"], args["planets"], args["aspects"])

    def test_pillars_table_marks_day_master_and_month_branch_in_text(self):
        html = bh.pillars_html(self.dims["bazi"]["data"]["四柱"])
        book = bh.BookHTML(html)
        marks = [n.text() for n in book.nodes if n.has_class("pillar-mark")]
        self.assertEqual(marks, ["日主", "月令"])
        heads = [n.text() for n in book.nodes if n.tag == "th" and n.attr("scope") == "col"]
        self.assertEqual(heads, ["柱", "年柱", "月柱", "日柱", "时柱"])
        glyphs = [n.text() for n in book.nodes if n.has_class("glyph")]
        self.assertEqual("".join(glyphs), "己丁壬丙卯丑申午")

    def test_pillars_reject_incomplete_input(self):
        pillars = self.dims["bazi"]["data"]["四柱"]
        with self.assertRaises(bh.RenderError):
            bh.pillars_html(pillars[:3])
        with self.assertRaises(bh.RenderError):
            bh.pillars_html([dict(pillars[0], 天干="")] + pillars[1:])

    def test_ziwei_grid_has_twelve_branches_and_text_labels(self):
        data = self.dims["ziwei"]["data"]
        book = bh.BookHTML(bh.ziwei_grid_html(data["十二宫"], basics=data["基础信息"]))
        cells = [n for n in book.nodes if n.has_class("ziwei-cell") and n.attr("data-branch")]
        self.assertEqual(sorted(n.attr("data-branch") for n in cells), sorted(bh.BRANCHES))
        self.assertEqual(cells[0].attr("data-branch"), data["基础信息"]["命宫地支"])
        ming = [n for n in cells if n.has_class("is-ming")]
        self.assertEqual(len(ming), 1)
        self.assertIn("命宫", ming[0].text())
        self.assertIn("身宫", ming[0].text())
        self.assertFalse(any(bh.is_hidden(n) for n in book.nodes))
        svg = next(n for n in book.nodes if n.tag == "svg")
        ET.fromstring(svg.serialize())
        self.assertIn("对宫为迁移宫", svg.attr("aria-label"))

    def test_ziwei_empty_palace_is_written_out_and_not_filled(self):
        palaces = json.loads(json.dumps(self.dims["ziwei"]["data"]["十二宫"]))
        palaces[0]["主星"] = []
        html = bh.ziwei_grid_html(palaces)
        self.assertEqual(html.count("空宫"), 1)
        with self.assertRaises(bh.RenderError):
            bh.ziwei_grid_html(palaces[:11])

    def test_ziwei_relations(self):
        self.assertEqual(bh.ziwei_relations("未"), {"对宫": "丑", "三合一": "亥", "三合二": "卯"})
        with self.assertRaises(bh.RenderError):
            bh.ziwei_relations("甲")

    def test_wheel_is_valid_svg_with_real_cusps_and_axis(self):
        root = ET.fromstring(self.wheel())
        ns = "{http://www.w3.org/2000/svg}"
        texts = ["".join(t.itertext()) for t in root.iter(ns + "text")]
        for label in ("上升", "天顶", "白羊", "双鱼", "太阳", "12"):
            self.assertIn(label, texts)
        self.assertGreaterEqual(min(int(t.get("font-size")) for t in root.iter(ns + "text")), 14)
        cusps = [l for l in root.iter(ns + "line") if l.get("class") == "wheel-cusp"]
        self.assertEqual(len(cusps), 8)  # four of the twelve Placidus cusps are the axes
        asc_label = next(t for t in root.iter(ns + "text") if "".join(t.itertext()) == "上升")
        self.assertLess(float(asc_label.get("x")), bh.WHEEL_SIZE / 2 - bh.WHEEL_RADII["outer"])

    def test_wheel_draws_only_requested_aspects_and_skips_conjunctions(self):
        aspects = [a for a in self.dims["astrology"]["data"]["主要相位"]
                   if {a["行星A"], a["行星B"]} in ({"太阳", "木星"}, {"太阳", "水星"})]
        svg = self.wheel(aspects=aspects)
        self.assertEqual(svg.count('class="wheel-aspect'), 1)
        self.assertIn("is-tense", svg)
        self.assertIn("stroke-dasharray", svg)
        with self.assertRaises(bh.RenderError):
            self.wheel(aspects=[{"行星A": "太阳", "行星B": "金星", "相位": "四分"}])

    def test_wheel_rejects_equal_or_invalid_cusps(self):
        cusps = list(self.dims["astrology"]["data"]["十二宫始黄经"])
        with self.assertRaises(bh.RenderError):
            self.wheel(cusps=[i * 30.0 for i in range(11)])
        with self.assertRaises(bh.RenderError):
            self.wheel(cusps=cusps[:11] + [cusps[0]])
        with self.assertRaises(bh.RenderError):
            self.wheel(cusps=cusps[:11] + [float("nan")])
        with self.assertRaises(bh.RenderError):
            self.wheel(asc=360.0)

    def test_labels_are_spread_without_reordering(self):
        spread = bh.spread_angles([100.0, 101.0, 102.0, 250.0])
        self.assertEqual(spread[3], 250.0)
        self.assertLess(spread[0], spread[1])
        self.assertLess(spread[1], spread[2])
        for a, b in zip(spread, spread[1:3]):
            self.assertGreaterEqual(b - a, bh.label_gap((a + b) / 2) - 1e-3)
        self.assertGreater(bh.label_gap(90), bh.label_gap(0))
        with self.assertRaises(bh.RenderError):
            bh.spread_angles([float(i) for i in range(40)])

    def test_degree_label_truncates(self):
        self.assertEqual(bh.degree_label(294.29999281304805), "24°17′")
        self.assertEqual(bh.degree_label(59.9999), "29°59′")
        self.assertEqual(bh.degree_label(0.0), "0°00′")

    def test_cli_renders_each_chart_and_reports_missing_data(self):
        script = str(ROOT / "scripts" / "book_html.py")
        for chart, marker in (("pillars", "pillar-chart"), ("ziwei", "ziwei-grid"), ("wheel", "<svg")):
            proc = subprocess.run([sys.executable, script, chart, "--bundle", str(BUNDLE)],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn(marker, proc.stdout)
        proc = subprocess.run([sys.executable, script, "wheel", "--bundle", str(BUNDLE), "--bodies", "凯龙星"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        proc = subprocess.run([sys.executable, script, "wheel", "--bundle", str(BUNDLE), "--aspects", "太阳-金星"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()

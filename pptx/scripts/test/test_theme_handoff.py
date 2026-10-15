"""Themes handed off from a web deck survive editable PowerPoint export."""

import argparse
import contextlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from pptx import Presentation
from pptx.oxml.ns import qn

import deck
import theme


class ThemeHandoffTests(unittest.TestCase):
    def test_web_outline_to_editable_deck(self):
        converter = pathlib.Path(__file__).resolve().parents[3] / "slides/scripts/to-pptx-outline.mjs"
        slides = {
            "cover": '<section class="slide cover" id="cover"><h1 data-edit="title">紹介</h1></section>',
            "comparison": '<section class="slide" id="comparison"><h2 data-edit="title">比較</h2><div class="columns"><div><h3 data-edit="left">以前</h3><ul><li data-edit="before">手動</li></ul></div><div><h3 data-edit="right">現在</h3><ul><li data-edit="after">自動</li></ul></div></div></section>',
            "results": '<section class="slide" id="results"><h2 data-edit="title">結果</h2><figure class="chart"><script type="application/json">{"type":"column","categories":["一月","二月"],"series":[{"name":"売上","values":[2,4]}]}</script></figure></section>',
            "custom": '<section class="slide" id="custom"><h2 data-edit="title">補足</h2><div class="custom"><p data-edit="detail">確認する</p></div></section>',
        }
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "slides").mkdir()
            (root / "lib").mkdir()
            (root / "lib/deck.css").write_text("/* fixture */")
            (root / "lib/deck.js").write_text("/* fixture */")
            for name, html in slides.items():
                (root / f"slides/{name}.html").write_text(html, encoding="utf-8")
            source = {"title": "日本語の紹介", "lang": "ja", "theme": {"mode": "dark", "paper": "#141820", "ink": "#f0f1f2", "accent": "#246080", "accentSoft": "#202f40", "muted": "#a2b3c4", "line": "#354657", "font": "'Noto Serif JP', serif", "chart": ["#be5621"]}, "slides": [{"id": name} for name in slides]}
            (root / "deck.json").write_text(json.dumps(source), encoding="utf-8")
            converted = subprocess.run(["node", str(converter), "."], cwd=root, capture_output=True, text=True)
            self.assertEqual(converted.returncode, 0, converted.stdout + converted.stderr)
            self.assertIn("Page 4 (custom): simplified to bullets", converted.stdout)
            outline = json.loads((root / "outline.json").read_text())
            self.assertEqual([item["layout"] for item in outline["slides"]], ["cover", "two-column", "chart", "bullets"])
            built = subprocess.run([sys.executable, "-B", str(pathlib.Path(deck.__file__).resolve()), "build", "--spec", "outline.json", "--out", "result.pptx"], cwd=root, capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            result = Presentation(root / "result.pptx")
            self.assertEqual(len(result.slides), 4)
            self.assertEqual(str(result.slides[1].background.fill.fore_color.rgb), "141820")
            self.assertEqual(self.find_run(result.slides[1], "比較").font.name, "Noto Serif JP")
            self.assertEqual(str(self.find_run(result.slides[1], "比較").font.color.rgb), "F0F1F2")
            self.assertEqual(self.find_run(result.slides[1], "自動").font.name, "Noto Serif JP")
            self.assertEqual(self.find_run(result.slides[3], "確認する").font.name, "Noto Serif JP")
            chart = next(shape.chart for shape in result.slides[2].shapes if shape.has_chart)
            self.assertEqual(str(chart.series[0].format.fill.fore_color.rgb), "BE5621")

    def build(self, selected_theme=None):
        outline = {"slides": [
            {"layout": "cover", "title": "表紙", "subtitle": "Introduction"},
            {"layout": "section", "title": "概要", "subtitle": "Muted detail"},
            {"layout": "quote", "title": "言葉", "subtitle": "Author"},
            {"layout": "chart", "title": "Results", "chart": {"type": "column", "categories": ["A", "B"], "series": [{"name": "First", "values": [2, 3]}, {"name": "Second", "values": [4, 1]}]}},
        ]}
        if selected_theme is not None:
            outline["theme"] = selected_theme
        with tempfile.TemporaryDirectory() as directory:
            original = os.getcwd()
            try:
                os.chdir(directory)
                pathlib.Path("outline.json").write_text(json.dumps(outline), encoding="utf-8")
                with contextlib.redirect_stdout(io.StringIO()):
                    deck.build(argparse.Namespace(spec="outline.json", out="result.pptx"))
                return Presentation("result.pptx")
            finally:
                os.chdir(original)

    @staticmethod
    def find_run(slide, text):
        return next(run for shape in slide.shapes if shape.has_text_frame
                    for paragraph in shape.text_frame.paragraphs for run in paragraph.runs
                    if run.text == text)

    def test_light_and_dark_match_web_defaults(self):
        for mode, expected in [
            ("light", ["FFFFFF", "0F1115", "5B57EF", "5D6471", "E6E8EC", "EEEDFE"]),
            ("dark", ["111216", "E9EBEF", "8481FF", "8E95A2", "2A2D35", "1F1E3D"]),
        ]:
            with self.subTest(mode=mode):
                selected = theme.validated({"mode": mode})
                self.assertEqual(list(theme.colors(selected).values()), expected)

    def test_custom_colors_palette_and_fonts_survive_file_round_trip(self):
        result = self.build({"mode": "dark", "background": "#141820", "text": "#f0f1f2", "accent": "#246080", "muted": "#a2b3c4", "line": "#354657", "soft": "#202f40", "headingFont": "Noto Serif JP", "bodyFont": "Hiragino Sans", "chart": ["#be5621", "#427852"]})
        self.assertEqual(str(result.slides[1].background.fill.fore_color.rgb), "141820")
        heading = self.find_run(result.slides[1], "概要")
        self.assertEqual(str(heading.font.color.rgb), "F0F1F2")
        self.assertEqual(heading.font.name, "Noto Serif JP")
        body = self.find_run(result.slides[1], "Muted detail")
        self.assertEqual(str(body.font.color.rgb), "A2B3C4")
        self.assertEqual(body.font.name, "Hiragino Sans")
        self.assertEqual(body._r.rPr.find(qn("a:ea")).get("typeface"), "Hiragino Sans")
        rule = next(shape for shape in result.slides[1].shapes if not shape.has_text_frame or not shape.text)
        self.assertEqual(str(rule.fill.fore_color.rgb), "246080")
        chart = next(shape.chart for shape in result.slides[3].shapes if shape.has_chart)
        self.assertEqual([str(series.format.fill.fore_color.rgb) for series in chart.series], ["BE5621", "427852"])
        self.assertEqual(theme.stored(result)["mode"], "dark")

    def test_cover_and_quote_keep_their_background_roles_and_readable_text(self):
        result = self.build({"mode": "dark"})
        self.assertEqual(str(result.slides[0].background.fill.fore_color.rgb), "8481FF")
        self.assertEqual(str(self.find_run(result.slides[0], "表紙").font.color.rgb), "0F1115")
        self.assertEqual(str(result.slides[2].background.fill.fore_color.rgb), "1F1E3D")
        self.assertEqual(str(self.find_run(result.slides[2], "“言葉”").font.color.rgb), "E9EBEF")
        self.assertEqual(str(self.find_run(result.slides[2], "— Author").font.color.rgb), "8E95A2")

    def test_chart_partial_override_matches_web_fallback(self):
        self.assertEqual(theme.palette(theme.validated({"mode": "dark", "chart": ["#123456"]})), ["123456", "0EA5A4", "E0A019", "E5484D", "8E95A2"])
        self.assertEqual(theme.palette(theme.validated({"mode": "dark", "chart": []}))[0], "8481FF")

    def test_edit_preserves_background_roles_and_recolors_muted_text(self):
        result = self.build({"mode": "dark", "chart": ["#123456"]})
        selected = theme.validated({"mode": "light", "accent": "#224466", "muted": "#556677", "chart": ["#775533"]})
        previous = theme.stored(result)
        for slide in result.slides:
            theme.apply(slide, selected, previous)
        theme.remember(result, selected)
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "edited.pptx"
            result.save(path)
            result = Presentation(path)
        self.assertEqual(str(result.slides[0].background.fill.fore_color.rgb), "224466")
        self.assertEqual(str(self.find_run(result.slides[0], "表紙").font.color.rgb), "FFFFFF")
        self.assertEqual(str(result.slides[2].background.fill.fore_color.rgb), "EEEDFE")
        self.assertEqual(str(self.find_run(result.slides[1], "Muted detail").font.color.rgb), "556677")
        chart = next(shape.chart for shape in result.slides[3].shapes if shape.has_chart)
        self.assertEqual(str(chart.series[0].format.fill.fore_color.rgb), "775533")

    def test_old_theme_defaults_remain_compatible(self):
        selected = theme.validated({})
        self.assertEqual(selected, theme.DEFAULT)
        self.assertEqual(theme.colors(selected)["muted"], theme.blend("0F1115", "FFFFFF", 0.35))
        self.assertEqual(theme.palette(selected)[1], theme.blend("5B57EF", "0F1115", 0.35))
        themed = self.build({"background": "#fafafa", "text": "#121314"})
        self.assertEqual(str(self.find_run(themed.slides[0], "表紙").font.color.rgb), "121314")
        result = self.build()
        self.assertIsNone(theme.stored(result))
        self.assertEqual(str(result.slides[0].background.fill.fore_color.rgb), "5B57EF")
        self.assertEqual(str(self.find_run(result.slides[1], "Muted detail").font.color.rgb), "5D6471")

    def test_invalid_theme_extensions_are_rejected(self):
        for value in [{"mode": "blue"}, {"mode": None}, {"muted": "red"}, {"soft": "#fff"}, {"line": 123456}, {"chart": "#123456"}, {"chart": ["12345G"]}, {"chart": ["123456"] * 6}, {"unknown": "value"}]:
            with self.subTest(value=value), self.assertRaises(theme.ThemeError):
                theme.validated(value)


if __name__ == "__main__":
    unittest.main()

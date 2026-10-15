"""Validated deck themes, applied without rebuilding slides or their embedded parts."""

import json
import re

from lxml import etree
from pptx.oxml.ns import qn

NAMESPACE = "https://otohaai.com/pptx/theme/1"
EXTENSION = "{D57AFEAA-91BE-4C71-BB7A-5980DAE80001}"
DEFAULT = {"background": "FFFFFF", "text": "0F1115", "accent": "5B57EF",
           "headingFont": "Helvetica Neue", "bodyFont": "Helvetica Neue", "density": "normal"}
# These faces have safe, explicit East Asian companions. Generic families never query or install fonts.
FONTS = {
    "Helvetica Neue": ("Helvetica Neue", "PingFang SC"),
    "Arial": ("Arial", "PingFang SC"),
    "Aptos": ("Aptos", "Yu Gothic"),
    "Calibri": ("Calibri", "Yu Gothic"),
    "Georgia": ("Georgia", "Songti SC"),
    "Times New Roman": ("Times New Roman", "Songti SC"),
    "Courier New": ("Courier New", "PingFang SC"),
    "PingFang SC": ("PingFang SC", "PingFang SC"),
    "Hiragino Sans": ("Hiragino Sans", "Hiragino Sans"),
    "Yu Gothic": ("Yu Gothic", "Yu Gothic"),
    "Noto Sans CJK SC": ("Noto Sans CJK SC", "Noto Sans CJK SC"),
    "Noto Sans JP": ("Noto Sans JP", "Noto Sans JP"),
    "Noto Serif JP": ("Noto Serif JP", "Noto Serif JP"),
    "sans-serif": ("Arial", "PingFang SC"),
    "serif": ("Georgia", "Songti SC"),
    "monospace": ("Courier New", "PingFang SC"),
}
DENSITY = {"compact": 1.05, "normal": 1.0, "airy": 0.9}
LEGACY = ["5B57EF", "0EA5A4", "E0A019", "E5484D", "8E95A2"]


class ThemeError(ValueError):
    """An invalid theme is rejected before the file is replaced."""


def validated(value):
    if not isinstance(value, dict) or set(value) - set(DEFAULT):
        raise ThemeError("theme must be an object with background, text, accent, headingFont, bodyFont and density only.")
    result = dict(DEFAULT, **value)
    for key in ("background", "text", "accent"):
        color = result[key]
        if not isinstance(color, str) or not re.fullmatch(r"#?[0-9a-fA-F]{6}", color):
            raise ThemeError(f"theme.{key} needs a six-digit hex colour, such as #F7F5EF.")
        result[key] = color.lstrip("#").upper()
    for key in ("headingFont", "bodyFont"):
        if not isinstance(result[key], str) or result[key] not in FONTS:
            raise ThemeError(f"theme.{key} needs a supported font; use sans-serif, serif or monospace as a safe fallback.")
    if not isinstance(result["density"], str) or result["density"] not in DENSITY:
        raise ThemeError("theme.density must be compact, normal or airy.")
    return result


def blend(first, second, weight):
    return "".join(f"{round(int(first[i:i + 2], 16) * (1 - weight) + int(second[i:i + 2], 16) * weight):02X}" for i in (0, 2, 4))


def palette(theme):
    return [theme["accent"], blend(theme["accent"], theme["text"], 0.35),
            blend(theme["accent"], theme["background"], 0.35),
            blend(theme["accent"], theme["text"], 0.6), blend(theme["accent"], theme["background"], 0.6)]


def colors(theme, legacy=False):
    if legacy:
        return {"background": "FFFFFF", "text": "0F1115", "accent": "5B57EF",
                "muted": "5D6471", "line": "E6E8EC", "soft": "EEEDFE"}
    return {**{key: theme[key] for key in ("background", "text", "accent")},
            "muted": blend(theme["text"], theme["background"], 0.35),
            "line": blend(theme["text"], theme["background"], 0.85),
            "soft": blend(theme["background"], theme["accent"], 0.1)}


def stored(deck):
    for extension in deck.part._element.iter(qn("p:ext")):
        if extension.get("uri") == EXTENSION:
            node = extension.find(f"{{{NAMESPACE}}}theme")
            if node is None or not node.text or len(node.text) > 2048:
                raise ThemeError("The saved theme cannot be read; the deck has not been changed.")
            try:
                return validated(json.loads(node.text))
            except (ValueError, TypeError) as error:
                raise ThemeError("The saved theme cannot be read; the deck has not been changed.") from error
    return None


def remember(deck, theme):
    root = deck.part._element
    extensions = root.find(qn("p:extLst"))
    if extensions is None:
        extensions = etree.SubElement(root, qn("p:extLst"))
    for old in list(extensions):
        if old.get("uri") == EXTENSION:
            extensions.remove(old)
    extension = etree.SubElement(extensions, qn("p:ext"), uri=EXTENSION)
    etree.SubElement(extension, f"{{{NAMESPACE}}}theme").text = json.dumps(theme, sort_keys=True)


def apply(slide, theme, previous=None, width=None, height=None):
    """Change DrawingML style and geometry only; relations, data and media are left intact."""
    old = colors(previous or DEFAULT, legacy=previous is None)
    new = colors(theme)
    mapping = {old[key]: new[key] for key in old}
    old_series = palette(previous) if previous else LEGACY
    mapping.update(zip(old_series, palette(theme)))
    ratio = DENSITY[theme["density"]] / DENSITY[(previous or DEFAULT)["density"]]
    from pptx.dml.color import RGBColor
    for color in slide._element.iter(qn("a:srgbClr")):
        if color.get("val") in mapping:
            color.set("val", mapping[color.get("val")])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = RGBColor.from_string(theme["background"])
    # Cover text was white against the old accent; it now uses the regular text colour.
    for shape in slide.shapes:
        if ratio != 1 and width is not None and height is not None:
            shape.left = round(width / 2 + (shape.left - width / 2) * ratio)
            shape.top = round(height / 2 + (shape.top - height / 2) * ratio)
            shape.width = max(1, round(shape.width * ratio))
            shape.height = max(1, round(shape.height * ratio))
        paint_text(shape._element, theme, ratio)
        if shape.has_chart:
            chart = shape.chart
            for color in chart._element.iter(qn("a:srgbClr")):
                if color.get("val") in mapping:
                    color.set("val", mapping[color.get("val")])
            paint_text(chart._element, theme, ratio, chart=True)


def paint_text(root, theme, ratio, chart=False):
    # Groups and tables keep their structures; their text properties are reached through DrawingML.
    for run in root.iter(qn("a:r")):
        if run.find(qn("a:rPr")) is None:
            run.insert(0, etree.Element(qn("a:rPr")))
    for tag in ("a:rPr", "a:defRPr", "a:endParaRPr"):
        for properties in root.iter(qn(tag)):
            heading = not chart and properties.get("b") == "1"
            latin, asian = FONTS[theme["headingFont"] if heading else theme["bodyFont"]]
            for font_tag, face in (("a:latin", latin), ("a:ea", asian), ("a:cs", asian)):
                font = properties.find(qn(font_tag))
                if font is None:
                    font = etree.SubElement(properties, qn(font_tag))
                font.set("typeface", face)
            # Explicit text fill, including inherited/theme colours in decks edited in other apps.
            fill = properties.find(qn("a:solidFill"))
            if fill is None:
                fill = etree.Element(qn("a:solidFill"))
                properties.insert(1 if properties.find(qn("a:ln")) is not None else 0, fill)
            current = fill.find(qn("a:srgbClr"))
            # Keep accent text; otherwise all text gets the selected ink.
            accent = current is not None and current.get("val") == theme["accent"]
            for child in list(fill):
                fill.remove(child)
            etree.SubElement(fill, qn("a:srgbClr"), val=theme["accent"] if accent else theme["text"])
            if properties.get("sz") and ratio != 1:
                properties.set("sz", str(max(100, round(int(properties.get("sz")) * ratio))))
    if ratio != 1:
        for spacing in root.iter(qn("a:spcPts")):
            spacing.set("val", str(round(int(spacing.get("val")) * ratio)))

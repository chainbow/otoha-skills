"""Validated deck themes, applied without rebuilding slides or their embedded parts."""

import json
import re

from lxml import etree
from pptx.oxml.ns import qn

NAMESPACE = "https://otohaai.com/pptx/theme/1"
EXTENSION = "{D57AFEAA-91BE-4C71-BB7A-5980DAE80001}"
DEFAULT = {"background": "FFFFFF", "text": "0F1115", "accent": "5B57EF",
           "headingFont": "Helvetica Neue", "bodyFont": "Helvetica Neue", "density": "normal"}
MODES = {
    "light": {"background": "FFFFFF", "text": "0F1115", "accent": "5B57EF",
              "muted": "5D6471", "line": "E6E8EC", "soft": "EEEDFE"},
    "dark": {"background": "111216", "text": "E9EBEF", "accent": "8481FF",
             "muted": "8E95A2", "line": "2A2D35", "soft": "1F1E3D"},
}
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
    if not isinstance(value, dict) or set(value) - (set(DEFAULT) | {"mode", "muted", "line", "soft", "chart"}):
        raise ThemeError("theme must be an object with mode, background, text, accent, muted, line, soft, chart, headingFont, bodyFont and density only.")
    defaults = DEFAULT
    if "mode" in value:
        if not isinstance(value["mode"], str) or value["mode"] not in MODES:
            raise ThemeError("theme.mode must be light or dark.")
        defaults = dict(DEFAULT, **MODES[value["mode"]])
    result = dict(defaults, **value)
    for key in ("background", "text", "accent", "muted", "line", "soft"):
        if key not in result:
            continue
        color = result[key]
        if not isinstance(color, str) or not re.fullmatch(r"#?[0-9a-fA-F]{6}", color):
            raise ThemeError(f"theme.{key} needs a six-digit hex colour, such as #F7F5EF.")
        result[key] = color.lstrip("#").upper()
    if "chart" in result:
        series = result["chart"]
        if not isinstance(series, list) or len(series) > 5 or any(
                not isinstance(color, str) or not re.fullmatch(r"#?[0-9a-fA-F]{6}", color) for color in series):
            raise ThemeError("theme.chart needs a list of at most five six-digit hex colours.")
        result["chart"] = [color.lstrip("#").upper() for color in series]
    for key in ("headingFont", "bodyFont"):
        if not isinstance(result[key], str) or result[key] not in FONTS:
            raise ThemeError(f"theme.{key} needs a supported font; use sans-serif, serif or monospace as a safe fallback.")
    if not isinstance(result["density"], str) or result["density"] not in DENSITY:
        raise ThemeError("theme.density must be compact, normal or airy.")
    return result


def blend(first, second, weight):
    return "".join(f"{round(int(first[i:i + 2], 16) * (1 - weight) + int(second[i:i + 2], 16) * weight):02X}" for i in (0, 2, 4))


def palette(theme):
    result = ([theme["accent"], *LEGACY[1:]] if "mode" in theme else
              [theme["accent"], blend(theme["accent"], theme["text"], 0.35),
               blend(theme["accent"], theme["background"], 0.35),
               blend(theme["accent"], theme["text"], 0.6), blend(theme["accent"], theme["background"], 0.6)])
    result[:len(theme.get("chart", []))] = theme.get("chart", [])
    return result


def colors(theme, legacy=False):
    if legacy:
        return {"background": "FFFFFF", "text": "0F1115", "accent": "5B57EF",
                "muted": "5D6471", "line": "E6E8EC", "soft": "EEEDFE"}
    return {**{key: theme[key] for key in ("background", "text", "accent")},
            "muted": theme.get("muted", blend(theme["text"], theme["background"], 0.35)),
            "line": theme.get("line", blend(theme["text"], theme["background"], 0.85)),
            "soft": theme.get("soft", blend(theme["background"], theme["accent"], 0.1))}


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
    background_color = next(slide.background._cSld.iter(qn("p:bg")), None)
    background_color = next(background_color.iter(qn("a:srgbClr")), None) if background_color is not None else None
    background_role = next((role for role in ("accent", "soft") if background_color is not None and background_color.get("val") == old[role]), "background")
    mapping = {old[key]: new[key] for key in old}
    old_series = palette(previous) if previous else LEGACY
    series_mapping = dict(zip(old_series, palette(theme)))
    ratio = DENSITY[theme["density"]] / DENSITY[(previous or DEFAULT)["density"]]
    from pptx.dml.color import RGBColor
    for color in slide._element.iter(qn("a:srgbClr")):
        if color.get("val") in mapping:
            color.set("val", mapping[color.get("val")])
    slide.background.fill.solid()
    # Explicit web themes retain the accent cover and soft quote backgrounds.
    background_role = background_role if "mode" in theme else "background"
    slide.background.fill.fore_color.rgb = RGBColor.from_string(new[background_role])
    cover_ink = contrasting_ink(new["accent"]) if background_role == "accent" else None
    for shape in slide.shapes:
        if ratio != 1 and width is not None and height is not None:
            shape.left = round(width / 2 + (shape.left - width / 2) * ratio)
            shape.top = round(height / 2 + (shape.top - height / 2) * ratio)
            shape.width = max(1, round(shape.width * ratio))
            shape.height = max(1, round(shape.height * ratio))
        paint_text(shape._element, theme, ratio, foreground=cover_ink)
        if shape.has_chart:
            chart = shape.chart
            for color in chart._element.iter(qn("a:srgbClr")):
                # Chart series can deliberately use a different first colour from the accent.
                # Keep their mapping separate from title rules, captions and other semantic ink.
                chart_mapping = (series_mapping if any(parent.tag == qn("c:ser") for parent in color.iterancestors())
                                 and color.get("val") in series_mapping else mapping)
                if color.get("val") in chart_mapping:
                    color.set("val", chart_mapping[color.get("val")])
            paint_text(chart._element, theme, ratio, chart=True)


def contrasting_ink(color):
    def linear(channel):
        channel = int(channel, 16) / 255
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
    luminance = sum(weight * linear(color[i:i + 2]) for i, weight in ((0, 0.2126), (2, 0.7152), (4, 0.0722)))
    # Pick the stronger contrast against either white or the default dark ink.
    dark = sum(weight * linear("0F1115"[i:i + 2]) for i, weight in ((0, 0.2126), (2, 0.7152), (4, 0.0722)))
    return "FFFFFF" if 1.05 / (luminance + 0.05) >= (luminance + 0.05) / (dark + 0.05) else "0F1115"


def paint_text(root, theme, ratio, chart=False, foreground=None):
    # Groups and tables keep their structures; their text properties are reached through DrawingML.
    theme_colors = colors(theme)
    text_colors = {theme_colors[key] for key in ("text", "muted", "accent")}
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
            # Preserve semantic ink roles after the colour mapping, including muted captions.
            ink = current.get("val") if current is not None else None
            ink = ink if ink in text_colors else theme["text"]
            for child in list(fill):
                fill.remove(child)
            etree.SubElement(fill, qn("a:srgbClr"), val=foreground or ink)
            if properties.get("sz") and ratio != 1:
                properties.set("sz", str(max(100, round(int(properties.get("sz")) * ratio))))
    if ratio != 1:
        for spacing in root.iter(qn("a:spcPts")):
            spacing.set("val", str(round(int(spacing.get("val")) * ratio)))

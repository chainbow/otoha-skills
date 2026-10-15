"""Builds and edits PowerPoint decks from a JSON outline.

    python scripts/deck.py build   --spec outline.json --out 演示/deck.pptx
    python scripts/deck.py edit    --file 演示/deck.pptx --slide 3 --spec slide.json
    python scripts/deck.py edit    --file 演示/deck.pptx --spec theme.json [--out 演示/styled.pptx]
    python scripts/deck.py outline --file 演示/deck.pptx

Paths are relative to the project folder, where the script runs. `edit` replaces one slide's content
and leaves every other slide exactly as it was, including changes made to them in PowerPoint or Keynote.
A spec containing only theme restyles the whole deck without replacing its contents.
See the skill's SKILL.md for the outline's layouts.
"""

import argparse
import io
import json
import math
import os
import pathlib
import shutil
import subprocess
import sys

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE, MSO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn
from pptx.util import Emu, Pt
from PIL import Image, ImageDraw

import theme as deck_theme

# The look of the app ("精密工作台"): quiet ink on white, one indigo accent.
INK = RGBColor(0x0F, 0x11, 0x15)
MUTED = RGBColor(0x5D, 0x64, 0x71)
LINE = RGBColor(0xE6, 0xE8, 0xEC)
ACCENT = RGBColor(0x5B, 0x57, 0xEF)
ACCENT_SOFT = RGBColor(0xEE, 0xED, 0xFE)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
SERIES = ["5B57EF", "0EA5A4", "E0A019", "E5484D", "8E95A2"]
LATIN_FONT = "Helvetica Neue"
ASIAN_FONT = "PingFang SC"

WIDTH, HEIGHT = Emu(12192000), Emu(6858000)  # 16:9
MARGIN = Emu(685800)  # 0.75 in
CHART_TYPES = {
    "column": XL_CHART_TYPE.COLUMN_CLUSTERED,
    "bar": XL_CHART_TYPE.BAR_CLUSTERED,
    "line": XL_CHART_TYPE.LINE_MARKERS,
    "pie": XL_CHART_TYPE.PIE,
    "stacked": XL_CHART_TYPE.COLUMN_STACKED,
}
LAYOUTS = ("cover", "section", "bullets", "two-column", "stats", "chart", "image", "video", "quote", "closing")
# The app keeps 64 KiB of what a script prints; the outline stays under it.
MAX_OUTPUT = 60_000


class OutlineError(Exception):
    """The outline cannot be made into slides; the message says what to change."""


# MARK: Paths


def inside_project(path: str, must_exist: bool = False) -> pathlib.Path:
    project = pathlib.Path.cwd().resolve()
    candidate = (project / path).resolve()
    if candidate != project and project not in candidate.parents:
        raise OutlineError(f"{path} is not inside the project folder.")
    if must_exist and not candidate.is_file():
        raise OutlineError(f"{path} does not exist.")
    return candidate


def read_json(path: str):
    try:
        return json.loads(inside_project(path, must_exist=True).read_text(encoding="utf-8"))
    except UnicodeDecodeError as error:
        raise OutlineError(f"{path} is not UTF-8 text; save it as UTF-8.") from error
    except json.JSONDecodeError as error:
        raise OutlineError(f"{path} is not valid JSON: {error}") from error


def open_deck(path: str):
    try:
        return Presentation(inside_project(path, must_exist=True))
    except OutlineError:
        raise
    except Exception as error:
        raise OutlineError(f"{path} is not a PowerPoint deck that can be read ({error}).") from error


def replaced(path: pathlib.Path, write):
    """Writes the file beside the old one and swaps it in, so a script stopped mid-save (the app ends
    scripts at their time, memory and write limits) leaves the old file whole. The name has no leading
    dot: the sandbox refuses those."""
    temporary = path.with_name(f"{path.stem}-saving-{os.getpid()}{path.suffix}")
    try:
        write(temporary)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


# MARK: Values


def described(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true or false"
    if isinstance(value, (int, float)):
        return "a number"
    if isinstance(value, str):
        return "text"
    return "a list" if isinstance(value, list) else "an object"


def text(value, where: str) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise OutlineError(f"{where} is text; it was {described(value)}.")
    return str(value)


def texts(value, where: str) -> list:
    if not isinstance(value, list):
        raise OutlineError(f'{where} is a list of texts, like ["…", "…"]; it was {described(value)}.')
    return [text(item, f"{where} item {number}") for number, item in enumerate(value, start=1)]


def fields(value, where: str, example: str = '{"layout": "bullets", "title": "…"}') -> dict:
    if not isinstance(value, dict):
        raise OutlineError(f"{where} is an object with named fields, like {example}; it was {described(value)}.")
    return value


def numbers(value, where: str) -> list:
    if not isinstance(value, list):
        raise OutlineError(f"{where} is a list of numbers; it was {described(value)}.")
    for number, item in enumerate(value, start=1):
        if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item):
            raise OutlineError(f"{where} item {number} is a number, like 3.2; it was {json.dumps(item, ensure_ascii=False)}.")
    return value


# MARK: Text


def style_run(run, size, color=INK, bold=False):
    font = run.font
    font.size = Pt(size)
    font.bold = bold
    font.color.rgb = color
    font.name = LATIN_FONT
    properties = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        element = properties.find(qn(tag))
        if element is None:
            element = properties.makeelement(qn(tag), {})
            properties.append(element)
        element.set("typeface", ASIAN_FONT)


def text_box(slide, left, top, width, height, lines, size, color=INK, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, spacing=1.15):
    box = slide.shapes.add_textbox(left, top, width, height)
    frame = box.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = anchor
    for margin in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(frame, margin, 0)
    for index, line in enumerate(lines if isinstance(lines, list) else [lines]):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.alignment = align
        paragraph.line_spacing = spacing
        run = paragraph.add_run()
        style_run(run, size, color, bold)
        run.text = str(line)
    return box


def bullet_list(slide, left, top, width, height, bullets, size=22):
    box = slide.shapes.add_textbox(left, top, width, height)
    frame = box.text_frame
    frame.word_wrap = True
    for margin in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(frame, margin, 0)
    for index, item in enumerate(bullets):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.space_after = Pt(size * 0.6)
        paragraph.line_spacing = 1.2
        marker = paragraph.add_run()
        style_run(marker, size, ACCENT, True)
        marker.text = "—  "
        run = paragraph.add_run()
        style_run(run, size)
        run.text = str(item)
    return box


def title(slide, text, top=MARGIN):
    text_box(slide, MARGIN, top, WIDTH - 2 * MARGIN, Emu(914400), text, 34, bold=True, anchor=MSO_ANCHOR.BOTTOM)
    rule = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, MARGIN, top + Emu(1005840), Emu(457200), Emu(45720))
    fill(rule, ACCENT)


def fill(shape, color, line=None):
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
    shape.shadow.inherit = False


def background(slide, color):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = color


# MARK: Layouts

BODY_TOP = MARGIN + Emu(1371600)


def video_poster(spec, movie):
    if spec.get("poster") is not None:
        name = text(spec["poster"], "poster")
        path = inside_project(name, must_exist=True)
        try:
            with Image.open(path) as frame:
                width, height = frame.size
                frame.verify()
            return str(path), width / height
        except (OSError, ValueError) as error:
            raise OutlineError(f"{name} is not a poster image a deck can hold; use PNG or JPEG.") from error
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        try:
            result = subprocess.run([ffmpeg, "-nostdin", "-v", "error", "-i", str(movie), "-frames:v", "1", "-vf", "scale=w='min(1280,min(iw*sar,720*dar))':h='ow/dar',setsar=1", "-f", "image2pipe", "-vcodec", "png", "pipe:1"], capture_output=True, timeout=15, check=True)
            image = io.BytesIO(result.stdout)
            with Image.open(image) as frame:
                width, height = frame.size
                frame.verify()
            image.seek(0)
            return image, width / height
        except (OSError, ValueError, subprocess.SubprocessError):
            pass  # A missing decoder or a failed extraction still gets a usable poster.
    ratio = spec.get("aspectRatio", 16 / 9)
    if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or not math.isfinite(ratio) or not 0.01 <= ratio <= 100:
        raise OutlineError("aspectRatio is the video's width divided by height, between 0.01 and 100.")
    width, height = (1280, max(1, round(1280 / ratio))) if ratio >= 1 else (max(1, round(720 * ratio)), 720)
    frame = Image.new("RGB", (width, height), "#EEEDFE")
    draw = ImageDraw.Draw(frame)
    size = min(width, height) / 6
    draw.polygon([(width / 2 - size / 2, height / 2 - size), (width / 2 - size / 2, height / 2 + size), (width / 2 + size, height / 2)], fill="#5B57EF")
    image = io.BytesIO()
    frame.save(image, format="PNG")
    image.seek(0)
    return image, ratio


def draw(slide, spec):
    spec = fields(spec, "a slide")
    layout = spec.get("layout")
    if layout not in LAYOUTS:
        raise OutlineError(f"layout {layout!r} is not one of: {', '.join(LAYOUTS)}.")
    spec = dict(spec, title=text(spec.get("title", ""), "title"))
    if not spec["title"].strip():
        raise OutlineError(f"a {layout} slide needs a title.")
    for name in ("subtitle", "caption", "notes"):
        if spec.get(name) is not None:
            spec[name] = text(spec[name], name)
    body_width = WIDTH - 2 * MARGIN
    body_height = HEIGHT - BODY_TOP - MARGIN
    if layout in ("cover", "closing", "section"):
        background(slide, ACCENT if layout == "cover" else WHITE)
        on_accent = layout == "cover"
        size = 54 if layout != "section" else 44
        text_box(slide, MARGIN, Emu(2194560), body_width, Emu(1371600), spec["title"], size, WHITE if on_accent else INK, True, anchor=MSO_ANCHOR.BOTTOM)
        if not on_accent:
            rule = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, MARGIN, Emu(3749040), Emu(914400), Emu(64008))
            fill(rule, ACCENT)
        if spec.get("subtitle"):
            text_box(slide, MARGIN, Emu(3749040 if on_accent else 4023360), body_width, Emu(914400), spec["subtitle"], 24, ACCENT_SOFT if on_accent else MUTED)
    elif layout == "bullets":
        title(slide, spec["title"])
        bullets = texts(spec.get("bullets", []), "bullets")
        if not bullets:
            raise OutlineError("a bullets slide needs bullets.")
        bullet_list(slide, MARGIN, BODY_TOP, body_width, body_height, bullets, 26 if len(bullets) <= 3 else 22)
    elif layout == "two-column":
        title(slide, spec["title"])
        gap = Emu(457200)
        column = int((body_width - gap) / 2)
        for index, side in enumerate(("left", "right")):
            part = fields(spec.get(side) or {}, side, '{"heading": "…", "bullets": ["…"]}')
            left = MARGIN + index * (column + gap)
            card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, BODY_TOP, column, body_height)
            card.adjustments[0] = 0.04
            fill(card, ACCENT_SOFT if index == 1 else WHITE, None if index == 1 else LINE)
            inner = Emu(365760)
            text_box(slide, left + inner, BODY_TOP + inner, column - 2 * inner, Emu(548640), text(part.get("heading", ""), f"{side} heading"), 24, ACCENT if index == 1 else INK, True)
            bullet_list(slide, left + inner, BODY_TOP + inner + Emu(731520), column - 2 * inner, body_height - 2 * inner - Emu(731520), texts(part.get("bullets", []), f"{side} bullets"), 20)
    elif layout == "stats":
        title(slide, spec["title"])
        if not isinstance(spec.get("stats"), list):
            raise OutlineError(f'stats is a list like [{{"value": "0.3 秒", "label": "唤醒"}}]; it was {described(spec.get("stats"))}.')
        stats = [fields(stat, f"stats item {number}", '{"value": "0.3 秒", "label": "唤醒"}') for number, stat in enumerate(spec["stats"], start=1)]
        if not 1 <= len(stats) <= 4:
            raise OutlineError("a stats slide needs 1 to 4 stats.")
        gap = Emu(365760)
        width = int((body_width - gap * (len(stats) - 1)) / len(stats))
        for index, stat in enumerate(stats):
            left = MARGIN + index * (width + gap)
            card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, BODY_TOP + Emu(457200), width, Emu(2743200))
            card.adjustments[0] = 0.06
            fill(card, ACCENT_SOFT)
            text_box(slide, left, BODY_TOP + Emu(914400), width, Emu(1097280), text(stat.get("value", ""), f"stat {index + 1} value"), 48, ACCENT, True, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
            text_box(slide, left, BODY_TOP + Emu(2103120), width, Emu(640080), text(stat.get("label", ""), f"stat {index + 1} label"), 20, MUTED, align=PP_ALIGN.CENTER)
    elif layout == "chart":
        title(slide, spec["title"])
        chart_spec = fields(spec.get("chart") or {}, "chart", '{"type": "column", "categories": ["…"], "series": [{"name": "…", "values": [1]}]}')
        kind = CHART_TYPES.get(chart_spec.get("type"))
        if kind is None:
            raise OutlineError(f"chart type {chart_spec.get('type')!r} is not one of: {', '.join(CHART_TYPES)}.")
        categories = texts(chart_spec.get("categories", []), "chart categories")
        if not isinstance(chart_spec.get("series"), list):
            raise OutlineError(f'chart series is a list like [{{"name": "预约", "values": [3.2, 5.8]}}]; it was {described(chart_spec.get("series"))}.')
        series = [fields(item, f"series {number}", '{"name": "预约", "values": [3.2, 5.8]}') for number, item in enumerate(chart_spec["series"], start=1)]
        values = [numbers(item.get("values"), f"series {number} values") for number, item in enumerate(series, start=1)]
        if not categories or not series or any(len(row) != len(categories) for row in values):
            raise OutlineError("a chart needs categories, and series whose values match them one for one.")
        data = CategoryChartData()
        data.categories = categories
        for number, (item, row) in enumerate(zip(series, values), start=1):
            data.add_series(text(item.get("name", ""), f"series {number} name"), row)
        caption = spec.get("caption")
        height = body_height - (Emu(548640) if caption else 0)
        chart = slide.shapes.add_chart(kind, MARGIN, BODY_TOP, body_width, height, data).chart
        style_chart(chart, kind, len(series))
        if caption:
            text_box(slide, MARGIN, BODY_TOP + height + Emu(91440), body_width, Emu(457200), caption, 16, MUTED)
    elif layout in ("image", "video"):
        title(slide, spec["title"])
        caption = spec.get("caption")
        height = body_height - (Emu(548640) if caption else 0)
        if layout == "video":
            name = text(spec.get("video", ""), "video")
            movie = inside_project(name, must_exist=True)
            if movie.suffix.lower() != ".mp4":
                raise OutlineError(f"{name} is not an MP4; export the video as MP4.")
            poster, ratio = video_poster(spec, movie)
            try:
                picture = slide.shapes.add_movie(str(movie), MARGIN, BODY_TOP, round(ratio * 1_000_000), 1_000_000, poster_frame_image=poster, mime_type="video/mp4")
            except (OSError, ValueError) as error:
                raise OutlineError(f"{name} or its poster cannot be embedded ({error}).") from error
        else:
            name = text(spec.get("image", ""), "image")
            image = inside_project(name, must_exist=True)
            try:
                picture = slide.shapes.add_picture(str(image), MARGIN, BODY_TOP)
            except (OSError, ValueError) as error:
                raise OutlineError(f"{name} is not a picture a deck can hold; use PNG, JPEG or GIF.") from error
        scale = min(body_width / picture.width, height / picture.height)
        picture.width, picture.height = int(picture.width * scale), int(picture.height * scale)
        picture.left = int(MARGIN + (body_width - picture.width) / 2)
        if caption:
            text_box(slide, MARGIN, BODY_TOP + height + Emu(91440), body_width, Emu(457200), caption, 16, MUTED, align=PP_ALIGN.CENTER)
    elif layout == "quote":
        background(slide, ACCENT_SOFT)
        text_box(slide, MARGIN * 2, Emu(1828800), WIDTH - 4 * MARGIN, Emu(2743200), f"“{spec['title']}”", 40, INK, True, anchor=MSO_ANCHOR.MIDDLE)
        if spec.get("subtitle"):
            text_box(slide, MARGIN * 2, Emu(4754880), WIDTH - 4 * MARGIN, Emu(640080), f"— {spec['subtitle']}", 22, MUTED)
    if spec.get("notes"):
        slide.notes_slide.notes_text_frame.text = spec["notes"]


def style_chart(chart, kind, series_count):
    chart.font.size = Pt(14)
    chart.font.color.rgb = MUTED
    chart.font.name = LATIN_FONT
    chart.has_legend = series_count > 1 or kind == XL_CHART_TYPE.PIE
    if chart.has_legend:
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout = False
    plot = chart.plots[0]
    if kind == XL_CHART_TYPE.PIE:
        for index, point in enumerate(plot.series[0].points):
            point.format.fill.solid()
            point.format.fill.fore_color.rgb = RGBColor.from_string(SERIES[index % len(SERIES)])
        return
    plot.has_data_labels = series_count == 1
    if plot.has_data_labels:
        plot.data_labels.font.size = Pt(14)
        plot.data_labels.font.color.rgb = INK
    for index, series in enumerate(plot.series):
        color = RGBColor.from_string(SERIES[index % len(SERIES)])
        if kind == XL_CHART_TYPE.LINE_MARKERS:
            series.format.line.color.rgb = color
            series.format.line.width = Pt(3)
            series.marker.format.fill.solid()
            series.marker.format.fill.fore_color.rgb = color
        else:
            series.format.fill.solid()
            series.format.fill.fore_color.rgb = color
    chart.value_axis.has_major_gridlines = True
    chart.value_axis.major_gridlines.format.line.color.rgb = LINE
    chart.value_axis.format.line.fill.background()
    chart.category_axis.format.line.color.rgb = LINE


# MARK: Commands


def saved(deck, path):
    """Saves the deck with its notes master listed in the presentation, as the format requires. The
    library leaves it out, and Quick Look, Finder's preview, then never finishes drawing the deck."""
    presentation = deck.part._element
    relation = next((rel for rel in deck.part.rels.values() if rel.reltype == RT.NOTES_MASTER), None)
    if relation is not None and presentation.find(qn("p:notesMasterIdLst")) is None:
        listed = parse_xml(f'<p:notesMasterIdLst {nsdecls("p", "r")}><p:notesMasterId r:id="{relation.rId}"/></p:notesMasterIdLst>')
        presentation.find(qn("p:sldMasterIdLst")).addnext(listed)
    replaced(path, deck.save)


def new_slide(deck):
    blank = next((layout for layout in deck.slide_layouts if layout.name == "Blank"), deck.slide_layouts[6])
    return deck.slides.add_slide(blank)


def build(arguments):
    outline = read_json(arguments.spec)
    slides = outline.get("slides") if isinstance(outline, dict) else None
    if not isinstance(slides, list) or not slides:
        raise OutlineError('the outline needs "slides", a list of slides.')
    theme = deck_theme.validated(outline["theme"]) if "theme" in outline else None
    out = inside_project(arguments.out)
    if out.suffix.lower() != ".pptx":
        raise OutlineError("--out must end in .pptx.")
    deck = Presentation()
    deck.slide_width, deck.slide_height = WIDTH, HEIGHT
    if outline.get("title"):
        deck.core_properties.title = str(outline["title"])
    for index, spec in enumerate(slides, start=1):
        try:
            draw(new_slide(deck), spec)
        except (OutlineError, TypeError, ValueError, KeyError, AttributeError) as error:
            raise OutlineError(f"slide {index}: {error}") from error
    if theme is not None:
        for slide in deck.slides:
            deck_theme.apply(slide, theme, width=deck.slide_width, height=deck.slide_height)
        deck_theme.remember(deck, theme)
    out.parent.mkdir(parents=True, exist_ok=True)
    saved(deck, out)
    print(json.dumps({"file": arguments.out, "slides": len(slides)}, ensure_ascii=False))


def clear(slide):
    """Removes a slide's shapes, and the charts and pictures they bring, so nothing is left over."""
    tree = slide.shapes._spTree
    for shape in list(slide.shapes):
        for element in shape._element.iter():
            for attribute in (qn("r:id"), qn("r:embed"), qn("r:link")):
                relation = element.get(attribute)
                if relation and relation in slide.part.rels:
                    slide.part.drop_rel(relation)
        tree.remove(shape._element)
    # Playback timing refers to the removed shape IDs, which the next layout may reuse.
    timing = slide._element.find(qn("p:timing"))
    if timing is not None:
        slide._element.remove(timing)


def edit(arguments):
    path = inside_project(arguments.file, must_exist=True)
    out = inside_project(arguments.out) if arguments.out else path
    if out.suffix.lower() != ".pptx":
        raise OutlineError("--out must end in .pptx.")
    spec = fields(read_json(arguments.spec), "edit spec")
    theme = deck_theme.validated(spec["theme"]) if "theme" in spec else None
    if "slides" in spec:
        raise OutlineError("--spec for edit is one slide or a theme, not an outline.")
    if arguments.slide is None and (theme is None or set(spec) != {"theme"}):
        raise OutlineError("edit needs --slide for replacement content, or a spec containing only theme for the whole deck.")
    deck = open_deck(arguments.file)
    previous = deck_theme.stored(deck)
    if arguments.slide is not None:
        if not 1 <= arguments.slide <= len(deck.slides):
            raise OutlineError(f"the deck has slides 1 to {len(deck.slides)}; there is no slide {arguments.slide}.")
        slide = deck.slides[arguments.slide - 1]
        clear(slide)
        background(slide, WHITE)
        if slide.has_notes_slide:
            slide.notes_slide.notes_text_frame.text = ""
        try:
            draw(slide, spec)
        except (OutlineError, TypeError, ValueError, KeyError, AttributeError) as error:
            raise OutlineError(f"slide {arguments.slide}: {error}") from error
        if theme is None and previous is not None:
            deck_theme.apply(slide, previous, width=deck.slide_width, height=deck.slide_height)
    if theme is not None:
        for number, slide in enumerate(deck.slides, start=1):
            old = None if number == arguments.slide else previous
            deck_theme.apply(slide, theme, old, deck.slide_width, deck.slide_height)
        deck_theme.remember(deck, theme)
    out.parent.mkdir(parents=True, exist_ok=True)
    saved(deck, out)
    print(json.dumps({"file": arguments.out or arguments.file, **({"slide": arguments.slide} if arguments.slide is not None else {"themedSlides": len(deck.slides)})}, ensure_ascii=False))


def shape_texts(shapes):
    """The text a slide shows, in order: text boxes, the text inside groups, and tables a row a line."""
    for shape in shapes:
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from shape_texts(shape.shapes)
        elif shape.has_table:
            for row in shape.table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                if any(cells):
                    yield " | ".join(cells)
        elif shape.has_text_frame and shape.text_frame.text.strip():
            yield shape.text_frame.text.strip()


def outline(arguments):
    deck = open_deck(arguments.file)
    slides = []
    for number, slide in enumerate(deck.slides, start=1):
        found = list(shape_texts(slide.shapes))
        entry = {"slide": number, "title": found[0] if found else "", "text": found[1:]}
        chart = next((shape.chart for shape in slide.shapes if shape.has_chart), None)
        if chart is not None:
            entry["chart"] = {
                "categories": [str(category) for category in chart.plots[0].categories],
                "series": [{"name": series.name, "values": list(series.values)} for series in chart.series],
            }
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame.text:
            entry["notes"] = slide.notes_slide.notes_text_frame.text
        slides.append(entry)
    result = {"file": arguments.file, "slides": slides}
    while len(json.dumps(result, ensure_ascii=False).encode()) > MAX_OUTPUT and len(result["slides"]) > 1:
        result = {"file": arguments.file, "slides": result["slides"][:-1], "truncated": f"slides {len(result['slides'])} to {len(slides)} left out: too long to show at once"}
    print(json.dumps(result, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    built = commands.add_parser("build")
    built.add_argument("--spec", required=True)
    built.add_argument("--out", required=True)
    edited = commands.add_parser("edit")
    edited.add_argument("--file", required=True)
    edited.add_argument("--slide", type=int)
    edited.add_argument("--spec", required=True)
    edited.add_argument("--out")
    read = commands.add_parser("outline")
    read.add_argument("--file", required=True)
    arguments = parser.parse_args()
    try:
        {"build": build, "edit": edit, "outline": outline}[arguments.command](arguments)
    except (OutlineError, deck_theme.ThemeError) as error:
        print(f"deck.py: {error}", file=sys.stderr)
        sys.exit(2)
    except (TypeError, ValueError, KeyError, AttributeError, OSError) as error:
        print(f"deck.py: {type(error).__name__}: {error}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

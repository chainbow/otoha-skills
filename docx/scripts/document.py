"""Builds Word documents (.docx) from a JSON description, and reads their outline back.

    python scripts/document.py build   --spec doc.json --out 报告/报告.docx
    python scripts/document.py outline --file 报告/报告.docx

Paths are relative to the project folder, where the script runs. See the skill's SKILL.md for the blocks.
"""

import argparse
import json
import math
import os
import pathlib
import sys

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

INK = RGBColor(0x0F, 0x11, 0x15)
MUTED = RGBColor(0x5D, 0x64, 0x71)
ACCENT = RGBColor(0x5B, 0x57, 0xEF)
ACCENT_HEX = "5B57EF"
ACCENT_SOFT = "EEEDFE"
LINE = "D9DCE1"
LATIN_FONT = "Helvetica Neue"
ASIAN_FONT = "PingFang SC"
BLOCKS = ("heading", "paragraph", "bullets", "numbered", "table", "image", "quote", "page-break")


class DocumentError(Exception):
    """The description cannot be made into a document; the message says what to change."""


def inside_project(path: str, must_exist: bool = False) -> pathlib.Path:
    project = pathlib.Path.cwd().resolve()
    candidate = (project / path).resolve()
    if candidate != project and project not in candidate.parents:
        raise DocumentError(f"{path} is not inside the project folder.")
    if must_exist and not candidate.is_file():
        raise DocumentError(f"{path} does not exist.")
    return candidate


def read_json(path: str):
    try:
        return json.loads(inside_project(path, must_exist=True).read_text(encoding="utf-8"))
    except UnicodeDecodeError as error:
        raise DocumentError(f"{path} is not UTF-8 text; save it as UTF-8.") from error
    except json.JSONDecodeError as error:
        raise DocumentError(f"{path} is not valid JSON: {error}") from error


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
        raise DocumentError(f"{where} is text; it was {described(value)}.")
    return str(value)


def texts(value, where: str) -> list:
    if not isinstance(value, list):
        raise DocumentError(f'{where} is a list of texts, like ["…", "…"]; it was {described(value)}.')
    return [text(item, f"{where} item {number}") for number, item in enumerate(value, start=1)]


def set_fonts(style, size=None, color=None, bold=None):
    font = style.font
    font.name = LATIN_FONT
    if size:
        font.size = Pt(size)
    if color is not None:
        font.color.rgb = color
    if bold is not None:
        font.bold = bold
    properties = style.element.get_or_add_rPr()
    fonts = properties.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        properties.append(fonts)
    fonts.set(qn("w:eastAsia"), ASIAN_FONT)
    fonts.set(qn("w:ascii"), LATIN_FONT)
    fonts.set(qn("w:hAnsi"), LATIN_FONT)


def styled(document):
    """The look of the app: quiet ink, indigo headings, generous spacing."""
    styles = document.styles
    set_fonts(styles["Normal"], 11, INK)
    styles["Normal"].paragraph_format.space_after = Pt(8)
    styles["Normal"].paragraph_format.line_spacing = 1.4
    set_fonts(styles["Title"], 26, INK, True)
    rule = styles["Title"].element.pPr.find(qn("w:pBdr")).find(qn("w:bottom"))
    rule.set(qn("w:color"), ACCENT_HEX)
    rule.attrib.pop(qn("w:themeColor"), None)
    set_fonts(styles["Subtitle"], 14, MUTED, False)
    for level, size in ((1, 18), (2, 14), (3, 12)):
        style = styles[f"Heading {level}"]
        set_fonts(style, size, ACCENT if level == 1 else INK, True)
        style.paragraph_format.space_before = Pt(18 if level == 1 else 12)
        style.paragraph_format.space_after = Pt(6)
    set_fonts(styles["Quote"], 12, MUTED, False)


def element(tag, **attributes):
    made = OxmlElement(tag)
    for name, value in attributes.items():
        made.set(qn(f"w:{name}"), value)
    return made


def drawn(table):
    """Lines, full width and a repeating header written into the table itself: Word, Pages and
    Quick Look all draw it the same, where a named table style is ignored by some of them."""
    properties = table._tbl.tblPr
    width = properties.find(qn("w:tblW"))
    width.set(qn("w:type"), "pct")
    width.set(qn("w:w"), "5000")
    borders = element("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        borders.append(element(f"w:{edge}", val="single", sz="4", space="0", color=LINE))
    margins = element("w:tblCellMar")
    for edge, size in (("top", "70"), ("left", "110"), ("bottom", "70"), ("right", "110")):
        margins.append(element(f"w:{edge}", w=size, type="dxa"))
    # The schema's order: tblW, jc, tblBorders, …, tblCellMar, tblLook.
    look = properties.find(qn("w:tblLook"))
    if look is not None:
        look.addprevious(borders)
        look.addprevious(margins)
    else:
        properties.append(borders)
        properties.append(margins)
    table.rows[0]._tr.get_or_add_trPr().append(element("w:tblHeader"))
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.line_spacing = 1.15


def shade(cell, color):
    properties = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:color"), "auto")
    shading.set(qn("w:fill"), color)
    properties.append(shading)


def add_block(document, block):
    if not isinstance(block, dict):
        raise DocumentError(f'a block is an object with named fields, like {{"type": "paragraph", "text": "…"}}; it was {described(block)}.')
    kind = block.get("type")
    if kind not in BLOCKS:
        raise DocumentError(f"type {kind!r} is not one of: {', '.join(BLOCKS)}.")
    if kind == "heading":
        level = block.get("level", 1)
        if isinstance(level, bool) or level not in (1, 2, 3):
            raise DocumentError("a heading's level is 1, 2 or 3.")
        document.add_heading(text(block.get("text", ""), "text"), level=level)
    elif kind == "paragraph":
        document.add_paragraph(text(block.get("text", ""), "text"))
    elif kind in ("bullets", "numbered"):
        items = texts(block.get("items", []), "items")
        if not items:
            raise DocumentError("a list needs items.")
        for item in items:
            document.add_paragraph(item, style="List Bullet" if kind == "bullets" else "List Number")
    elif kind == "table":
        header = texts(block.get("header", []), "header")
        if not isinstance(block.get("rows", []), list):
            raise DocumentError(f"rows is a list of rows, each a list of cells; it was {described(block.get('rows'))}.")
        rows = [texts(row, f"row {number}") for number, row in enumerate(block.get("rows", []), start=1)]
        if not header or any(len(row) != len(header) for row in rows):
            raise DocumentError("a table needs a header, and rows with one cell per column.")
        table = document.add_table(rows=1 + len(rows), cols=len(header))
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for column, value in enumerate(header):
            cell = table.rows[0].cells[column]
            cell.text = value
            shade(cell, ACCENT_SOFT)
            for run in cell.paragraphs[0].runs:
                run.font.bold = True
        for number, row in enumerate(rows, start=1):
            for column, value in enumerate(row):
                table.rows[number].cells[column].text = value
        drawn(table)
        document.add_paragraph()
    elif kind == "image":
        name = text(block.get("path", ""), "path")
        path = inside_project(name, must_exist=True)
        width = block.get("width_cm", 15)
        if isinstance(width, bool) or not isinstance(width, (int, float)) or not math.isfinite(width) or not 1 <= width <= 16:
            raise DocumentError(f"width_cm is a number of centimetres from 1 to 16; it was {json.dumps(width, ensure_ascii=False)}.")
        try:
            document.add_picture(str(path), width=Cm(width))
        except Exception as error:
            raise DocumentError(f"{name} is not a picture a document can hold; use PNG, JPEG or GIF.") from error
        if block.get("caption"):
            caption = document.add_paragraph(text(block["caption"], "caption"))
            caption.runs[0].font.color.rgb = MUTED
            caption.runs[0].font.size = Pt(10)
    elif kind == "quote":
        document.add_paragraph(text(block.get("text", ""), "text"), style="Quote")
    elif kind == "page-break":
        document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def build(arguments):
    spec = read_json(arguments.spec)
    if not isinstance(spec, dict) or not isinstance(spec.get("blocks"), list):
        raise DocumentError("the description needs a list of blocks.")
    out = inside_project(arguments.out)
    if out.suffix.lower() != ".docx":
        raise DocumentError("--out must end in .docx.")
    document = docx.Document()
    styled(document)
    for section in document.sections:
        section.page_width, section.page_height = Cm(21.0), Cm(29.7)
        section.left_margin = section.right_margin = Cm(2.5)
        section.top_margin = section.bottom_margin = Cm(2.2)
    if spec.get("title"):
        document.add_paragraph(text(spec["title"], "title"), style="Title")
        document.core_properties.title = text(spec["title"], "title")
    if spec.get("subtitle"):
        document.add_paragraph(text(spec["subtitle"], "subtitle"), style="Subtitle")
    for index, block in enumerate(spec["blocks"], start=1):
        try:
            add_block(document, block)
        except (DocumentError, TypeError, ValueError, KeyError, AttributeError) as error:
            raise DocumentError(f"block {index}: {error}") from error
    out.parent.mkdir(parents=True, exist_ok=True)
    replaced(out, document.save)
    print(json.dumps({"file": arguments.out, "blocks": len(spec["blocks"])}, ensure_ascii=False))


def outline(arguments):
    path = inside_project(arguments.file, must_exist=True)
    try:
        document = docx.Document(path)
    except Exception as error:
        raise DocumentError(f"{arguments.file} is not a Word document that can be read ({error}).") from error
    headings = []
    words = 0
    for paragraph in document.paragraphs:
        words += len(paragraph.text)
        if paragraph.style.name.startswith("Heading"):
            level = paragraph.style.name.split()[-1]
            headings.append({"level": int(level) if level.isdigit() else 1, "text": paragraph.text})
    print(json.dumps({"file": arguments.file, "title": document.core_properties.title, "headings": headings, "tables": len(document.tables), "characters": words}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    built = commands.add_parser("build")
    built.add_argument("--spec", required=True)
    built.add_argument("--out", required=True)
    read = commands.add_parser("outline")
    read.add_argument("--file", required=True)
    arguments = parser.parse_args()
    try:
        {"build": build, "outline": outline}[arguments.command](arguments)
    except DocumentError as error:
        print(f"document.py: {error}", file=sys.stderr)
        sys.exit(2)
    except (TypeError, ValueError, KeyError, AttributeError, OSError) as error:
        print(f"document.py: {type(error).__name__}: {error}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

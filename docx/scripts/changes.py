"""Changes the formatting of an existing Word document from a list of changes, and reads its formatting back.

Used by document.py's `change` and `inspect` commands; see the skill's SKILL.md for the changes.
Everything a change does not name is left as it was.
"""

import copy
import re

from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.table import Table


class ChangeError(Exception):
    """A change cannot be made; the message says what to change."""


# MARK: Sizes and lengths

# Chinese named font sizes in points (号数).
NAMED_SIZES = {
    "初号": 42, "小初": 36, "一号": 26, "小一": 24, "二号": 22, "小二": 18, "三号": 16, "小三": 15,
    "四号": 14, "小四": 12, "五号": 10.5, "小五": 9, "六号": 7.5, "小六": 6.5, "七号": 5.5, "八号": 5,
}
NUMBER = r"(-?\d+(?:\.\d+)?)"
UNITS = {"pt": 20, "磅": 20, "point": 20, "points": 20, "cm": 566.929, "厘米": 566.929, "mm": 56.6929, "毫米": 56.6929,
         "in": 1440, "inch": 1440, "inches": 1440, "英寸": 1440, "twip": 1, "twips": 1}
CHARS = ("字符", "字", "char", "chars", "character", "characters")
LINES = ("行", "line", "lines")


def font_size(value, where):
    """Points, from 12, "12pt", "12磅" or a named size such as "小四"."""
    if isinstance(value, str) and value.strip() in NAMED_SIZES:
        return NAMED_SIZES[value.strip()]
    points = value
    if isinstance(value, str):
        found = re.fullmatch(rf"\s*{NUMBER}\s*(pt|磅|point|points)?\s*", value)
        points = float(found.group(1)) if found else None
    if isinstance(points, bool) or not isinstance(points, (int, float)) or not 1 <= points <= 1638:
        names = "、".join(NAMED_SIZES)
        raise ChangeError(f"size is points (12, \"10.5pt\") or a named size ({names}); it was {value!r}.")
    return points


def measure(value, where, chars=False, lines=False):
    """("twips", n), ("chars", n) or ("lines", n). A bare number is points."""
    if isinstance(value, bool):
        raise ChangeError(f"{where} is a length like \"2cm\", \"12pt\" or 12 (points); it was {value!r}.")
    if isinstance(value, (int, float)):
        return "twips", round(value * 20)
    if isinstance(value, str):
        found = re.fullmatch(rf"\s*{NUMBER}\s*([^\d\s]*)\s*", value)
        if found:
            number, unit = float(found.group(1)), found.group(2).lower()
            if unit in ("", *UNITS):
                return "twips", round(number * UNITS.get(unit, 20))
            if chars and unit in CHARS:
                return "chars", number
            if lines and unit in LINES:
                return "lines", number
    extra = (', "2字符" (characters)' if chars else "") + (', "0.5行" (lines)' if lines else "")
    raise ChangeError(f"{where} is a length like \"2cm\", \"12pt\" or 12 (points){extra}; it was {value!r}.")


def twips(value, where):
    return measure(value, where)[1]


def flag(value, where):
    if not isinstance(value, bool):
        raise ChangeError(f"{where} is true or false; it was {value!r}.")
    return value


def colour(value, where):
    if not isinstance(value, str) or not re.fullmatch(r"#?[0-9A-Fa-f]{6}", value.strip()):
        raise ChangeError(f"{where} is a colour of six hexadecimal digits, like \"#FF0000\"; it was {value!r}.")
    return value.strip().lstrip("#").upper()


def known(spec, allowed, where):
    if not isinstance(spec, dict):
        raise ChangeError(f"{where} is an object with named fields; it was {type(spec).__name__}.")
    unknown = [key for key in spec if key not in allowed]
    if unknown:
        raise ChangeError(f"{where} has {', '.join(map(repr, unknown))}, which is not one of: {', '.join(allowed)}.")
    return spec


# MARK: Elements in schema order

RPR_ORDER = ("rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike", "outline", "shadow",
             "emboss", "imprint", "noProof", "snapToGrid", "vanish", "webHidden", "color", "spacing", "w", "kern",
             "position", "sz", "szCs", "highlight", "u", "effect", "bdr", "shd", "fitText", "vertAlign", "rtl", "cs",
             "em", "lang", "eastAsianLayout", "specVanish", "oMath")
PPR_ORDER = ("pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr",
             "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap",
             "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd", "snapToGrid",
             "spacing", "ind", "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc", "textDirection",
             "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr", "pPrChange")
STYLE_ORDER = ("name", "aliases", "basedOn", "next", "link", "autoRedefine", "hidden", "uiPriority", "semiHidden",
               "unhideWhenUsed", "qFormat", "locked", "personal", "personalCompose", "personalReply", "rsid", "pPr",
               "rPr", "tblPr", "trPr", "tcPr", "tblStylePr")
TBLPR_ORDER = ("tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize", "tblStyleColBandSize", "tblW",
               "jc", "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook")
TCPR_ORDER = ("cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders", "shd", "noWrap", "tcMar",
              "textDirection", "tcFitText", "vAlign", "hideMark")
TRPR_ORDER = ("cnfStyle", "divId", "gridBefore", "gridAfter", "wBefore", "wAfter", "cantSplit", "trHeight",
              "tblHeader", "tblCellSpacing", "jc", "hidden")
SECT_ORDER = ("headerReference", "footerReference", "footnotePr", "endnotePr", "type", "pgSz", "pgMar", "paperSrc",
              "pgBorders", "lnNumType", "pgNumType", "cols", "formProt", "vAlign", "noEndnote", "titlePg",
              "textDirection", "bidi", "rtlGutter", "docGrid", "printerSettings", "sectPrChange")
BORDER_ORDER = ("top", "left", "start", "bottom", "right", "end", "insideH", "insideV", "tl2br", "tr2bl", "between", "bar")


def ensure(parent, name, order):
    """The child w:<name> of parent, added in the place the schema wants it when missing."""
    tag = qn(f"w:{name}")
    found = parent.find(tag)
    if found is not None:
        return found
    made = OxmlElement(f"w:{name}")
    position = order.index(name)
    for later in order[position + 1:]:
        sibling = parent.find(qn(f"w:{later}"))
        if sibling is not None:
            sibling.addprevious(made)
            return made
    parent.append(made)
    return made


def drop(parent, *names):
    for name in names:
        for found in parent.findall(qn(f"w:{name}")):
            parent.remove(found)


def put(element, **attributes):
    for name, value in attributes.items():
        key = qn(f"w:{name}")
        if value is None:
            element.attrib.pop(key, None)
        else:
            element.set(key, str(value))
    return element


def ensure_rpr(holder):
    """w:rPr of a run, a paragraph mark (in w:pPr) or a style."""
    tag = holder.tag.split("}")[1]
    order = {"r": ("rPr", "t"), "pPr": PPR_ORDER, "style": STYLE_ORDER}[tag]
    if tag == "r":
        found = holder.find(qn("w:rPr"))
        if found is None:
            found = OxmlElement("w:rPr")
            holder.insert(0, found)
        return found
    return ensure(holder, "rPr", order)


def ensure_ppr(holder):
    tag = holder.tag.split("}")[1]
    if tag == "p":
        found = holder.find(qn("w:pPr"))
        if found is None:
            found = OxmlElement("w:pPr")
            holder.insert(0, found)
        return found
    return ensure(holder, "pPr", STYLE_ORDER)


# MARK: Fonts

FONT_FIELDS = ("name", "latin", "eastAsia", "size", "bold", "italic", "underline", "strike", "color", "highlight", "verticalAlign")
UNDERLINES = ("single", "double", "thick", "dotted", "dash", "wave", "words", "none")
HIGHLIGHTS = ("yellow", "green", "cyan", "magenta", "blue", "red", "darkBlue", "darkCyan", "darkGreen", "darkMagenta",
              "darkRed", "darkYellow", "darkGray", "lightGray", "black", "white", "none")


def checked_font(spec, where):
    spec = known(spec, FONT_FIELDS, where)
    font = dict(spec)
    for name in ("name", "latin", "eastAsia"):
        if name in font and (not isinstance(font[name], str) or not font[name].strip()):
            raise ChangeError(f"{where} {name} is a font's name, like \"宋体\" or \"Times New Roman\".")
    if "size" in font:
        font["size"] = font_size(font["size"], where)
    for name in ("bold", "italic", "strike"):
        if name in font:
            flag(font[name], f"{where} {name}")
    if "underline" in font:
        value = font["underline"]
        font["underline"] = ("single" if value else "none") if isinstance(value, bool) else value
        if font["underline"] not in UNDERLINES:
            raise ChangeError(f"{where} underline is true, false or one of: {', '.join(UNDERLINES)}.")
    if "color" in font:
        font["color"] = colour(font["color"], f"{where} color")
    if "highlight" in font and font["highlight"] not in HIGHLIGHTS:
        raise ChangeError(f"{where} highlight is one of: {', '.join(HIGHLIGHTS)}.")
    if "verticalAlign" in font and font["verticalAlign"] not in ("superscript", "subscript", "baseline"):
        raise ChangeError(f"{where} verticalAlign is superscript, subscript or baseline.")
    return font


def apply_font(rpr, font):
    """Direct font properties on a w:rPr. Naming a font also removes the theme font that would win over it."""
    names = {}
    if "name" in font:
        names.update(ascii=font["name"], hAnsi=font["name"], eastAsia=font["name"], cs=font["name"])
    if "latin" in font:
        names.update(ascii=font["latin"], hAnsi=font["latin"], cs=font["latin"])
    if "eastAsia" in font:
        names["eastAsia"] = font["eastAsia"]
    if names:
        fonts = ensure(rpr, "rFonts", RPR_ORDER)
        for slot, value in names.items():
            fonts.set(qn(f"w:{slot}"), value)
            fonts.attrib.pop(qn(f"w:{'cstheme' if slot == 'cs' else slot + 'Theme'}"), None)
    if "size" in font:
        half_points = round(font["size"] * 2)
        put(ensure(rpr, "sz", RPR_ORDER), val=half_points)
        put(ensure(rpr, "szCs", RPR_ORDER), val=half_points)
    for name, tags in (("bold", ("b", "bCs")), ("italic", ("i", "iCs")), ("strike", ("strike",))):
        if name in font:
            for tag in tags:
                put(ensure(rpr, tag, RPR_ORDER), val=None if font[name] else "0")
    if "underline" in font:
        put(ensure(rpr, "u", RPR_ORDER), val=font["underline"])
    if "color" in font:
        color = put(ensure(rpr, "color", RPR_ORDER), val=font["color"])
        for theme in ("themeColor", "themeTint", "themeShade"):
            color.attrib.pop(qn(f"w:{theme}"), None)
    if "highlight" in font:
        if font["highlight"] == "none":
            drop(rpr, "highlight")
        else:
            put(ensure(rpr, "highlight", RPR_ORDER), val=font["highlight"])
    if "verticalAlign" in font:
        put(ensure(rpr, "vertAlign", RPR_ORDER), val=font["verticalAlign"])


# MARK: Paragraph formatting

PARAGRAPH_FIELDS = ("style", "align", "leftIndent", "rightIndent", "firstLineIndent", "hangingIndent", "lineSpacing",
                    "spaceBefore", "spaceAfter", "keepWithNext", "keepTogether", "pageBreakBefore", "widowControl",
                    "outlineLevel")
ALIGNMENTS = {"left": "left", "center": "center", "centre": "center", "right": "right", "justify": "both",
              "both": "both", "distribute": "distribute"}


def checked_paragraph(spec, where):
    spec = known(spec, PARAGRAPH_FIELDS, where)
    if "align" in spec and spec["align"] not in ALIGNMENTS:
        raise ChangeError(f"{where} align is one of: {', '.join(ALIGNMENTS)}.")
    for name in ("leftIndent", "rightIndent", "firstLineIndent", "hangingIndent"):
        if name in spec:
            measure(spec[name], f"{where} {name}", chars=True)
    for name in ("spaceBefore", "spaceAfter"):
        if name in spec:
            measure(spec[name], f"{where} {name}", lines=True)
    if "lineSpacing" in spec:
        line_spacing(spec["lineSpacing"], f"{where} lineSpacing")
    for name in ("keepWithNext", "keepTogether", "pageBreakBefore", "widowControl"):
        if name in spec:
            flag(spec[name], f"{where} {name}")
    level = spec.get("outlineLevel")
    if "outlineLevel" in spec and (isinstance(level, bool) or level not in range(1, 10) and level != "body"):
        raise ChangeError(f"{where} outlineLevel is 1 to 9, or \"body\".")
    return spec


def line_spacing(value, where):
    """(line, lineRule): 1.5 is one and a half lines; "20pt" exactly; {"atLeast": "12pt"}; {"multiple": 2}."""
    if isinstance(value, dict) and len(value) == 1:
        (kind, amount), = value.items()
        if kind == "multiple":
            return line_spacing(amount, where)
        if kind in ("exactly", "atLeast"):
            return twips(amount, where), "exact" if kind == "exactly" else "atLeast"
    if isinstance(value, str):
        found = re.fullmatch(rf"\s*{NUMBER}\s*(倍|x|×|lines?)\s*", value)
        if found:
            value = float(found.group(1))
    if isinstance(value, (int, float)) and not isinstance(value, bool) and 0.25 <= value <= 10:
        return round(value * 240), "auto"
    if isinstance(value, str):
        try:
            return twips(value, where), "exact"
        except ChangeError:
            pass
    raise ChangeError(f"{where} is a multiple (1.5), exact points (\"20pt\"), {{\"atLeast\": \"12pt\"}} or {{\"exactly\": \"20pt\"}}; it was {value!r}.")


def apply_indent(ind, side, value, where, size_points):
    kind, amount = measure(value, where, chars=True)
    plain, chars = {"left": ("left", "leftChars"), "right": ("right", "rightChars"),
                    "firstLine": ("firstLine", "firstLineChars"), "hanging": ("hanging", "hangingChars")}[side]
    if kind == "chars":
        put(ind, **{chars: round(amount * 100), plain: round(amount * size_points * 20)})
    else:
        put(ind, **{plain: amount, chars: None})
    if side in ("left", "right"):
        twin = "start" if side == "left" else "end"
        put(ind, **{twin: None, f"{twin}Chars": None})
    else:
        other = ("hanging", "hangingChars") if side == "firstLine" else ("firstLine", "firstLineChars")
        put(ind, **dict.fromkeys(other))


def apply_paragraph(ppr, spec, document, size_points, set_style=True):
    if "style" in spec and set_style:
        style = find_style(document, spec["style"], "paragraph style")
        put(ensure(ppr, "pStyle", PPR_ORDER), val=style.style_id)
    if "align" in spec:
        put(ensure(ppr, "jc", PPR_ORDER), val=ALIGNMENTS[spec["align"]])
    for name, side in (("leftIndent", "left"), ("rightIndent", "right"), ("firstLineIndent", "firstLine"), ("hangingIndent", "hanging")):
        if name in spec:
            apply_indent(ensure(ppr, "ind", PPR_ORDER), side, spec[name], name, size_points)
    if "lineSpacing" in spec:
        line, rule = line_spacing(spec["lineSpacing"], "lineSpacing")
        put(ensure(ppr, "spacing", PPR_ORDER), line=line, lineRule=rule)
    for name, side in (("spaceBefore", "before"), ("spaceAfter", "after")):
        if name in spec:
            kind, amount = measure(spec[name], name, lines=True)
            spacing = ensure(ppr, "spacing", PPR_ORDER)
            put(spacing, **{f"{side}Autospacing": None})
            if kind == "lines":
                put(spacing, **{f"{side}Lines": round(amount * 100), side: round(amount * line_pitch(document))})
            else:
                put(spacing, **{side: amount, f"{side}Lines": None})
    for name, tag in (("keepWithNext", "keepNext"), ("keepTogether", "keepLines"), ("pageBreakBefore", "pageBreakBefore"), ("widowControl", "widowControl")):
        if name in spec:
            put(ensure(ppr, tag, PPR_ORDER), val=None if spec[name] else "0")
    if "outlineLevel" in spec:
        put(ensure(ppr, "outlineLvl", PPR_ORDER), val=9 if spec["outlineLevel"] == "body" else spec["outlineLevel"] - 1)


def line_pitch(document):
    grid = document.sections[0]._sectPr.find(qn("w:docGrid"))
    pitch = grid.get(qn("w:linePitch")) if grid is not None else None
    return int(pitch) if pitch and pitch.isdigit() else 312


# MARK: Styles

STYLE_ALIASES = {"正文": "normal", "標準": "normal", "标题": "title", "副标题": "subtitle", "表格网格": "tablegrid",
                 "网格型": "tablegrid", "页眉": "header", "页脚": "footer", "题注": "caption", "目录标题": "tocheading"}


def style_key(name):
    key = re.sub(r"\s+", "", str(name)).lower()
    found = re.fullmatch(r"(?:标题|見出し|heading)(\d)", key)
    if found:
        return f"heading{found.group(1)}"
    found = re.fullmatch(r"(?:目录|toc)(\d)", key)
    if found:
        return f"toc{found.group(1)}"
    return STYLE_ALIASES.get(key, key)


def find_style(document, name, where, create=None):
    if not isinstance(name, str) or not name.strip():
        raise ChangeError(f"{where} is a style's name, like \"Heading 1\" or \"正文\".")
    wanted = style_key(name)
    for style in document.styles:
        if wanted in (style_key(style.name or ""), style_key(style.style_id or "")):
            return style
    if create is not None:
        style = document.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        if create.get("basedOn"):
            style.base_style = find_style(document, create["basedOn"], "basedOn")
        return style
    names = sorted({style.name for style in document.styles if style.type == WD_STYLE_TYPE.PARAGRAPH and style.name})
    raise ChangeError(f"there is no style {name!r}; the document's paragraph styles are: {', '.join(names)}. Add \"create\": {{\"basedOn\": \"Normal\"}} to make it.")


# MARK: Where paragraphs are

SCOPES = ("document", "body", "tables", "headers", "footers", "textboxes", "everywhere")


def own_paragraph(element):
    parent = element.getparent()
    while parent is not None and parent.tag != qn("w:p"):
        parent = parent.getparent()
    return parent


def inside(element, tag):
    parent = element.getparent()
    while parent is not None:
        if parent.tag == qn(tag):
            return parent
        parent = parent.getparent()
    return None


def numbered_paragraphs(document):
    """The body's paragraphs in reading order, those in tables included, text boxes left out; with the
    number of the table each is in."""
    body = document.element.body
    tables = [table for table in body.iter(qn("w:tbl")) if inside(table, "w:txbxContent") is None]
    numbers = {id(table): number for number, table in enumerate(tables, start=1)}
    found = []
    for paragraph in body.iter(qn("w:p")):
        if inside(paragraph, "w:txbxContent") is not None:
            continue
        table = inside(paragraph, "w:tbl")
        found.append((paragraph, numbers[id(table)] if table is not None else None))
    return found


def header_footer_parts(document, kind):
    reltype = RT.HEADER if kind == "headers" else RT.FOOTER
    return [rel.target_part for rel in document.part.rels.values() if rel.reltype == reltype]


def textbox_paragraphs(roots):
    for root in roots:
        for box in root.iter(qn("w:txbxContent")):
            yield from box.iter(qn("w:p"))


def numbers_of(value, where, top=None):
    """1-based numbers from 3, [1, 4], "2-5" or ["1-3", 8]."""
    items = value if isinstance(value, list) else [value]
    numbers = []
    for item in items:
        if isinstance(item, int) and not isinstance(item, bool) and item >= 1:
            numbers.append(item)
        elif isinstance(item, str) and re.fullmatch(r"\s*\d+\s*-\s*\d+\s*", item):
            first, last = (int(part) for part in item.split("-"))
            numbers.extend(range(first, last + 1))
        elif isinstance(item, str) and item.strip().isdigit():
            numbers.append(int(item))
        else:
            raise ChangeError(f"{where} is a number from 1, a list like [1, 4], or a range like \"2-5\"; it was {value!r}.")
    if top is not None and any(n > top for n in numbers):
        raise ChangeError(f"{where} goes past {top}, the last there is.")
    return numbers


WHERE_FIELDS = ("in", "paragraphs", "style", "contains", "startsWith", "regex", "table")


def selected(document, where, label):
    """The paragraphs a change's "where" picks."""
    where = known(where, WHERE_FIELDS, label)
    scope = where.get("in", "document")
    if scope not in SCOPES:
        raise ChangeError(f"{label} in is one of: {', '.join(SCOPES)}.")
    numbered = numbered_paragraphs(document)
    if scope in ("headers", "footers", "textboxes", "everywhere") and "paragraphs" in where:
        raise ChangeError(f"{label} paragraphs numbers count the document's own paragraphs; use it without in {scope!r}.")
    candidates = []
    if scope in ("document", "everywhere"):
        candidates = [p for p, _ in numbered]
    elif scope == "body":
        candidates = [p for p, table in numbered if table is None]
    elif scope == "tables":
        candidates = [p for p, table in numbered if table is not None]
    if scope in ("headers", "everywhere"):
        candidates += [p for part in header_footer_parts(document, "headers") for p in part.element.iter(qn("w:p")) if inside(p, "w:txbxContent") is None]
    if scope in ("footers", "everywhere"):
        candidates += [p for part in header_footer_parts(document, "footers") for p in part.element.iter(qn("w:p")) if inside(p, "w:txbxContent") is None]
    if scope in ("textboxes", "everywhere"):
        roots = [document.element.body] + [part.element for kind in ("headers", "footers") for part in header_footer_parts(document, kind)]
        candidates += list(textbox_paragraphs(roots))
    if "paragraphs" in where and where["paragraphs"] != "all":
        wanted = set(numbers_of(where["paragraphs"], f"{label} paragraphs", len(numbered)))
        chosen = {id(p) for number, (p, _) in enumerate(numbered, start=1) if number in wanted}
        candidates = [p for p in candidates if id(p) in chosen]
    if "table" in where:
        tables = set(numbers_of(where["table"], f"{label} table"))
        in_tables = {id(p) for p, table in numbered if table in tables}
        candidates = [p for p in candidates if id(p) in in_tables]
    if "style" in where:
        names = where["style"] if isinstance(where["style"], list) else [where["style"]]
        ids = {find_style(document, name, f"{label} style").style_id for name in names}
        default = document.styles.default(WD_STYLE_TYPE.PARAGRAPH)
        candidates = [p for p in candidates if paragraph_style_id(p, default) in ids]
    for name in ("contains", "startsWith", "regex"):
        if name in where and (not isinstance(where[name], str) or not where[name]):
            raise ChangeError(f"{label} {name} is text.")
    if "contains" in where:
        candidates = [p for p in candidates if where["contains"] in paragraph_text(p)]
    if "startsWith" in where:
        candidates = [p for p in candidates if paragraph_text(p).lstrip().startswith(where["startsWith"])]
    if "regex" in where:
        try:
            pattern = re.compile(where["regex"])
        except re.error as error:
            raise ChangeError(f"{label} regex is not a pattern that can be used ({error}).") from error
        candidates = [p for p in candidates if pattern.search(paragraph_text(p))]
    return candidates


def paragraph_style_id(paragraph, default):
    ppr = paragraph.find(qn("w:pPr"))
    style = ppr.find(qn("w:pStyle")) if ppr is not None else None
    if style is not None:
        return style.get(qn("w:val"))
    return default.style_id if default is not None else None


def own_runs(paragraph):
    """A paragraph's runs, those inside links, tracked insertions and fields included; not those of text boxes
    or other paragraphs inside it."""
    return [run for run in paragraph.iter(qn("w:r")) if own_paragraph(run) is paragraph]


def run_text(run):
    parts = []
    for child in run:
        if child.tag == qn("w:t"):
            parts.append(child.text or "")
        elif child.tag == qn("w:tab"):
            parts.append("\t")
        elif child.tag in (qn("w:br"), qn("w:cr")):
            parts.append("\n")
    return "".join(parts)


def paragraph_text(paragraph):
    return "".join(run_text(run) for run in own_runs(paragraph))


def runs_for(paragraph, only):
    """The runs holding `only`, split at its edges so nothing beside it is touched; all runs when only is None."""
    runs = own_runs(paragraph)
    if only is None:
        return runs
    text = "".join(run_text(run) for run in runs)
    spans = [(m.start(), m.end()) for m in re.finditer(re.escape(only), text)]
    if not spans:
        return []
    chosen = []
    offset = 0
    for run in runs:
        length = len(run_text(run))
        start, end = offset, offset + length
        offset = end
        cuts = sorted({max(start, min(end, edge)) for span in spans for edge in span} | {start, end})
        pieces = [(a, b) for a, b in zip(cuts, cuts[1:]) if b > a]
        inside_match = [any(s <= a and b <= e for s, e in spans) for a, b in pieces]
        if not any(inside_match):
            continue
        simple = all(child.tag in (qn("w:rPr"), qn("w:t")) for child in run)
        if all(inside_match) or not simple:
            chosen.append(run)
            continue
        whole = run_text(run)
        made = []
        for (a, b), wanted in zip(pieces, inside_match):
            piece = copy.deepcopy(run)
            for t in piece.findall(qn("w:t")):
                piece.remove(t)
            t = OxmlElement("w:t")
            t.text = whole[a - start:b - start]
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            piece.append(t)
            made.append(piece)
            if wanted:
                chosen.append(piece)
        for piece in made:
            run.addprevious(piece)
        run.getparent().remove(run)
    return chosen


def size_of(document, paragraph, font):
    """The points a paragraph's text is set in, for indents counted in characters."""
    if "size" in font:
        return font["size"]
    for run in own_runs(paragraph):
        size = run.find(f"{qn('w:rPr')}/{qn('w:sz')}")
        if size is not None:
            return int(size.get(qn("w:val"))) / 2
    default = document.styles.default(WD_STYLE_TYPE.PARAGRAPH)
    return resolved_style_value(document, paragraph_style_id(paragraph, default), "size") or 10.5


# MARK: Tables

TABLE_FIELDS = ("table", "borders", "width", "columnWidths", "align", "rowHeight", "headerRepeat", "merge", "cells", "autofit")
CELL_FIELDS = ("rows", "columns", "font", "paragraph", "shading", "verticalAlign", "borders")
EDGES = ("top", "bottom", "left", "right", "insideH", "insideV")
BORDER_STYLES = ("single", "double", "thick", "dotted", "dashed", "dotDash", "wave", "none", "nil")


def table_elements(document):
    body = document.element.body
    return [table for table in body.iter(qn("w:tbl")) if inside(table, "w:txbxContent") is None]


def border(value, where, size="0.5pt", color="000000"):
    """(style, eighths of a point, colour) from "none", "1.5pt" or {"style": "single", "size": "1.5pt", "color": "000000"}."""
    if value in (None, False, "none", "nil"):
        return ("nil", None, None)
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        value = {"size": value}
    if value is True:
        value = {}
    value = known(value, ("style", "size", "color"), where)
    style = value.get("style", "single")
    if style not in BORDER_STYLES:
        raise ChangeError(f"{where} style is one of: {', '.join(BORDER_STYLES)}.")
    eighths = round(twips(value.get("size", size), f"{where} size") / 20 * 8)
    return (style, max(2, min(96, eighths)), colour(value.get("color", color), f"{where} color"))


def write_border(holder, edge, spec):
    style, size, color = spec
    element = ensure(holder, edge, BORDER_ORDER)
    element.attrib.clear()
    put(element, val=style, sz=size, space=None if style == "nil" else 0, color=color)


def table_borders(table, value, where):
    """Table-wide lines. Lines set on single cells before are cleared, so these show everywhere."""
    if isinstance(value, str):
        value = {"preset": value}
    value = known(value, ("preset", "size", "innerSize", "color", *EDGES, "headerBottom"), where)
    preset = value.get("preset")
    size, inner, color = value.get("size"), value.get("innerSize"), value.get("color", "000000")
    plan = {}
    header_bottom = value.get("headerBottom")
    if preset == "three-line":
        plan = dict.fromkeys(EDGES, None)
        plan["top"] = plan["bottom"] = {"size": size or "1.5pt", "color": color}
        header_bottom = header_bottom or {"size": inner or "0.75pt", "color": color}
    elif preset in ("all", "grid"):
        plan = {edge: {"size": size or "0.5pt", "color": color} for edge in EDGES}
    elif preset == "outer":
        plan = {edge: ({"size": size or "0.5pt", "color": color} if edge in ("top", "bottom", "left", "right") else None) for edge in EDGES}
    elif preset == "inner":
        plan = {edge: ({"size": inner or size or "0.5pt", "color": color} if edge.startswith("inside") else None) for edge in EDGES}
    elif preset == "none":
        plan = dict.fromkeys(EDGES, None)
    elif preset is not None:
        raise ChangeError(f"{where} preset is one of: three-line, all, outer, inner, none.")
    for edge in EDGES:
        if edge in value:
            plan[edge] = value[edge]
    properties = table.tblPr
    lines = ensure(properties, "tblBorders", TBLPR_ORDER)
    for edge, spec in plan.items():
        write_border(lines, edge, border(spec, f"{where} {edge}"))
    for cell in table.iter(qn("w:tc")):
        tcpr = cell.find(qn("w:tcPr"))
        if tcpr is not None:
            drop(tcpr, "tcBorders")
    if header_bottom is not None:
        for cell in table.tr_lst[0].tc_lst:
            write_border(ensure(cell.get_or_add_tcPr(), "tcBorders", TCPR_ORDER), "bottom", border(header_bottom, f"{where} headerBottom"))


def grid_cells(table):
    """(row number, first and last grid column, w:tc) for every cell, 1-based."""
    for row_number, row in enumerate(table.tr_lst, start=1):
        trpr = row.find(qn("w:trPr"))
        before = trpr.find(qn("w:gridBefore")) if trpr is not None else None
        column = 1 + (int(before.get(qn("w:val"))) if before is not None else 0)
        for cell in row.tc_lst:
            span = cell.grid_span
            yield row_number, column, column + span - 1, cell
            column += span


def change_table(document, table_element, spec, where):
    table = Table(table_element, document._body)
    properties = table_element.tblPr
    if "borders" in spec:
        table_borders(table_element, spec["borders"], f"{where} borders")
    if "width" in spec:
        width = ensure(properties, "tblW", TBLPR_ORDER)
        value = spec["width"]
        if value == "auto":
            put(width, type="auto", w=0)
        elif isinstance(value, str) and value.strip().endswith("%"):
            put(width, type="pct", w=round(float(value.strip()[:-1]) * 50))
        else:
            put(width, type="dxa", w=twips(value, f"{where} width"))
    if "columnWidths" in spec:
        widths = spec["columnWidths"]
        columns = table_element.tblGrid.findall(qn("w:gridCol"))
        if not isinstance(widths, list) or len(widths) != len(columns):
            raise ChangeError(f"{where} columnWidths lists one width per column; the table has {len(columns)} columns.")
        widths = [twips(value, f"{where} columnWidths") for value in widths]
        for column, value in zip(columns, widths):
            put(column, w=value)
        for _, first, last, cell in grid_cells(table_element):
            tcw = ensure(cell.get_or_add_tcPr(), "tcW", TCPR_ORDER)
            put(tcw, type="dxa", w=sum(widths[first - 1:last]))
        put(ensure(properties, "tblLayout", TBLPR_ORDER), type="fixed")
    if "autofit" in spec:
        put(ensure(properties, "tblLayout", TBLPR_ORDER), type="autofit" if flag(spec["autofit"], f"{where} autofit") else "fixed")
    if "align" in spec:
        if spec["align"] not in ("left", "center", "right"):
            raise ChangeError(f"{where} align is left, center or right.")
        put(ensure(properties, "jc", TBLPR_ORDER), val=spec["align"])
    if "rowHeight" in spec:
        value = spec["rowHeight"]
        value = value if isinstance(value, dict) else {"height": value}
        value = known(value, ("height", "rule", "rows"), f"{where} rowHeight")
        rule = value.get("rule", "atLeast")
        if rule not in ("atLeast", "exact"):
            raise ChangeError(f"{where} rowHeight rule is atLeast or exact.")
        rows = set(numbers_of(value["rows"], f"{where} rowHeight rows", len(table_element.tr_lst))) if value.get("rows", "all") != "all" else None
        for number, row in enumerate(table_element.tr_lst, start=1):
            if rows is None or number in rows:
                put(ensure(row.get_or_add_trPr(), "trHeight", TRPR_ORDER), val=twips(value.get("height"), f"{where} rowHeight"), hRule=rule)
    if "headerRepeat" in spec:
        value = spec["headerRepeat"]
        count = (1 if value else 0) if isinstance(value, bool) else value
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ChangeError(f"{where} headerRepeat is true, false or a number of rows.")
        for number, row in enumerate(table_element.tr_lst, start=1):
            if number <= count:
                ensure(row.get_or_add_trPr(), "tblHeader", TRPR_ORDER)
            elif row.find(qn("w:trPr")) is not None:
                drop(row.trPr, "tblHeader")
    if "cells" in spec:
        groups = spec["cells"] if isinstance(spec["cells"], list) else [spec["cells"]]
        for number, group in enumerate(groups, start=1):
            change_cells(document, table_element, group, f"{where} cells {number}")
    if "merge" in spec:
        merges = spec["merge"]
        if not isinstance(merges, list):
            raise ChangeError(f'{where} merge is a list like [{{"from": [1, 1], "to": [1, 3]}}].')
        for number, merge in enumerate(merges, start=1):
            merge = known(merge, ("from", "to"), f"{where} merge {number}")
            corners = [merge.get("from"), merge.get("to")]
            if not all(isinstance(c, list) and len(c) == 2 and all(isinstance(x, int) and x >= 1 for x in c) for c in corners):
                raise ChangeError(f'{where} merge {number} is {{"from": [row, column], "to": [row, column]}}, counted from 1.')
            try:
                table.cell(corners[0][0] - 1, corners[0][1] - 1).merge(table.cell(corners[1][0] - 1, corners[1][1] - 1))
            except IndexError as error:
                raise ChangeError(f"{where} merge {number} names a cell outside the table.") from error
            except Exception as error:
                raise ChangeError(f"{where} merge {number} cannot be made ({error}).") from error


def change_cells(document, table_element, group, where):
    group = known(group, CELL_FIELDS, where)
    font = checked_font(group["font"], f"{where} font") if "font" in group else None
    paragraph = checked_paragraph(group["paragraph"], f"{where} paragraph") if "paragraph" in group else None
    total_rows = len(table_element.tr_lst)
    rows = group.get("rows", "all")
    rows = set(range(1, total_rows + 1)) if rows == "all" else {1} if rows == "header" else set(numbers_of(rows, f"{where} rows", total_rows))
    columns = group.get("columns", "all")
    columns = None if columns == "all" else set(numbers_of(columns, f"{where} columns"))
    for row, first, last, cell in grid_cells(table_element):
        if row not in rows or (columns is not None and not columns & set(range(first, last + 1))):
            continue
        tcpr = cell.get_or_add_tcPr()
        if "shading" in group:
            shade = ensure(tcpr, "shd", TCPR_ORDER)
            shade.attrib.clear()
            put(shade, val="clear", color="auto", fill=colour(group["shading"], f"{where} shading"))
        if "verticalAlign" in group:
            if group["verticalAlign"] not in ("top", "center", "bottom"):
                raise ChangeError(f"{where} verticalAlign is top, center or bottom.")
            put(ensure(tcpr, "vAlign", TCPR_ORDER), val=group["verticalAlign"])
        if "borders" in group:
            lines = known(group["borders"], ("top", "bottom", "left", "right"), f"{where} borders")
            holder = ensure(tcpr, "tcBorders", TCPR_ORDER)
            for edge, value in lines.items():
                write_border(holder, edge, border(value, f"{where} borders {edge}"))
        for p in cell.iter(qn("w:p")):
            format_paragraph(document, p, font, paragraph, None)


# MARK: Sections, headers and footers

PAGE_SIZES = {"A3": (29.7, 42.0), "A4": (21.0, 29.7), "A5": (14.8, 21.0), "B5": (17.6, 25.0), "JIS B5": (18.2, 25.7),
              "16K": (18.4, 26.0), "LETTER": (21.59, 27.94), "LEGAL": (21.59, 35.56)}
PAGE_FIELDS = ("size", "orientation", "margins", "pageNumbers", "differentFirstPage", "differentOddEven", "columns", "verticalAlign")
NUMBER_FORMATS = ("decimal", "upperRoman", "lowerRoman", "upperLetter", "lowerLetter", "chineseCounting",
                  "chineseCountingThousand", "decimalFullWidth", "ideographTraditional", "numberInDash")


def sections_of(document, value, where):
    if value in (None, "all"):
        return list(document.sections)
    numbers = numbers_of(value, f"{where} sections", len(document.sections))
    return [document.sections[n - 1] for n in numbers]


def change_page(document, spec, sections, where):
    spec = known(spec, PAGE_FIELDS, where)
    for section in sections:
        if "size" in spec:
            size = spec["size"]
            if isinstance(size, str) and size.strip().upper() in PAGE_SIZES:
                width, height = (round(cm * 566.929) for cm in PAGE_SIZES[size.strip().upper()])
            elif isinstance(size, dict) and set(size) == {"width", "height"}:
                width, height = twips(size["width"], f"{where} size width"), twips(size["height"], f"{where} size height")
            else:
                raise ChangeError(f"{where} size is one of {', '.join(PAGE_SIZES)}, or {{\"width\": \"21cm\", \"height\": \"29.7cm\"}}.")
            if isinstance(size, str) and section.orientation == WD_ORIENT.LANDSCAPE:
                width, height = height, width
            section.page_width, section.page_height = width * 635, height * 635
        if "orientation" in spec:
            wanted = spec["orientation"]
            if wanted not in ("portrait", "landscape"):
                raise ChangeError(f"{where} orientation is portrait or landscape.")
            width, height = section.page_width, section.page_height
            if (wanted == "landscape") != (width > height):
                section.page_width, section.page_height = height, width
            section.orientation = WD_ORIENT.LANDSCAPE if wanted == "landscape" else WD_ORIENT.PORTRAIT
        if "margins" in spec:
            margins = known(spec["margins"], ("top", "bottom", "left", "right", "header", "footer", "gutter"), f"{where} margins")
            for name, value in margins.items():
                attribute = {"top": "top_margin", "bottom": "bottom_margin", "left": "left_margin", "right": "right_margin",
                             "header": "header_distance", "footer": "footer_distance", "gutter": "gutter"}[name]
                setattr(section, attribute, twips(value, f"{where} margins {name}") * 635)
        sect = section._sectPr
        if "pageNumbers" in spec:
            numbers = known(spec["pageNumbers"], ("start", "format", "continue"), f"{where} pageNumbers")
            element = ensure(sect, "pgNumType", SECT_ORDER)
            if "start" in numbers:
                start = numbers["start"]
                if isinstance(start, bool) or not isinstance(start, int) or start < 0:
                    raise ChangeError(f"{where} pageNumbers start is a whole number.")
                put(element, start=start)
            if numbers.get("continue"):
                put(element, start=None)
            if "format" in numbers:
                if numbers["format"] not in NUMBER_FORMATS:
                    raise ChangeError(f"{where} pageNumbers format is one of: {', '.join(NUMBER_FORMATS)}.")
                put(element, fmt=numbers["format"])
        if "differentFirstPage" in spec:
            section.different_first_page_header_footer = flag(spec["differentFirstPage"], f"{where} differentFirstPage")
        if "columns" in spec:
            count = spec["columns"]
            if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 10:
                raise ChangeError(f"{where} columns is a number of text columns from 1 to 10.")
            put(ensure(sect, "cols", SECT_ORDER), num=count, space=425)
        if "verticalAlign" in spec:
            if spec["verticalAlign"] not in ("top", "center", "bottom", "both"):
                raise ChangeError(f"{where} verticalAlign is top, center, bottom or both.")
            put(ensure(sect, "vAlign", SECT_ORDER), val=spec["verticalAlign"])
    if "differentOddEven" in spec:
        document.settings.odd_and_even_pages_header_footer = flag(spec["differentOddEven"], f"{where} differentOddEven")


FIELD = re.compile(r"\{(PAGE|NUMPAGES|SECTIONPAGES)\}")
HEADER_FIELDS = ("text", "align", "font", "paragraph", "line", "pages", "sections")


def field_runs(paragraph, instruction):
    def run_with(child):
        run = OxmlElement("w:r")
        run.append(child)
        paragraph.append(run)
    begin = OxmlElement("w:fldChar")
    put(begin, fldCharType="begin")
    run_with(begin)
    code = OxmlElement("w:instrText")
    code.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    code.text = f" {instruction} "
    run_with(code)
    separate = OxmlElement("w:fldChar")
    put(separate, fldCharType="separate")
    run_with(separate)
    shown = OxmlElement("w:t")
    shown.text = "1"
    run_with(shown)
    end = OxmlElement("w:fldChar")
    put(end, fldCharType="end")
    run_with(end)


def text_runs(paragraph, text):
    """Runs for text, where {PAGE}, {NUMPAGES} and {SECTIONPAGES} become fields Word fills in."""
    position = 0
    for match in FIELD.finditer(text):
        if match.start() > position:
            plain_run(paragraph, text[position:match.start()])
        field_runs(paragraph, match.group(1))
        position = match.end()
    if position < len(text):
        plain_run(paragraph, text[position:])


def plain_run(paragraph, text):
    run = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = text
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    run.append(t)
    paragraph.append(run)


def change_header_footer(document, kind, spec, where):
    spec = known(spec, HEADER_FIELDS, where)
    text = spec.get("text", "")
    if not isinstance(text, str):
        raise ChangeError(f"{where} text is text; {{PAGE}} and {{NUMPAGES}} become the page number and the page count.")
    pages = spec.get("pages", "default")
    if pages not in ("default", "first", "even"):
        raise ChangeError(f"{where} pages is default, first or even.")
    font = checked_font(spec["font"], f"{where} font") if "font" in spec else None
    paragraph_spec = checked_paragraph(spec.get("paragraph", {}), f"{where} paragraph")
    if "align" in spec:
        paragraph_spec = dict(paragraph_spec, align=spec["align"])
        checked_paragraph(paragraph_spec, where)
    chosen = sections_of(document, spec.get("sections"), where)
    for number, section in enumerate(chosen):
        attribute = {"default": kind, "first": f"first_page_{kind}", "even": f"even_page_{kind}"}[pages]
        if pages == "first":
            section.different_first_page_header_footer = True
        if pages == "even":
            document.settings.odd_and_even_pages_header_footer = True
        part = getattr(section, attribute)
        if spec.get("sections") in (None, "all") and number > 0 and part.is_linked_to_previous:
            continue  # It shows the previous section's, which has just been set.
        part.is_linked_to_previous = False
        holder = part._element
        for child in list(holder):
            if child.tag in (qn("w:p"), qn("w:tbl")):
                holder.remove(child)
        for line in text.split("\n"):
            paragraph = OxmlElement("w:p")
            holder.append(paragraph)
            ppr = ensure_ppr(paragraph)
            put(ensure(ppr, "pStyle", PPR_ORDER), val=find_style(document, "Header" if kind == "header" else "Footer", where, create={}).style_id)
            text_runs(paragraph, line)
            border_line = spec.get("line")
            if border_line is not None:
                lines = ensure(ppr, "pBdr", PPR_ORDER)
                edge = "bottom" if kind == "header" else "top"
                drop(lines, edge)
                if border_line:
                    write_border(lines, edge, border(border_line, f"{where} line", size="0.75pt"))
            format_paragraph(document, paragraph, font, paragraph_spec, None)


# MARK: Inserting breaks and a table of contents


def insert_page_break(document, paragraphs, side, where):
    for paragraph in paragraphs:
        target = paragraph
        if side == "before":
            target = paragraph.getprevious()
            while target is not None and target.tag != qn("w:p"):
                target = target.getprevious() if target.tag not in (qn("w:tbl"),) else None
            if target is None:
                put(ensure(ensure_ppr(paragraph), "pageBreakBefore", PPR_ORDER), val=None)
                continue
        run = OxmlElement("w:r")
        brk = OxmlElement("w:br")
        put(brk, type="page")
        run.append(brk)
        target.append(run)


SECTION_STARTS = {"nextPage": WD_SECTION.NEW_PAGE, "continuous": WD_SECTION.CONTINUOUS, "oddPage": WD_SECTION.ODD_PAGE, "evenPage": WD_SECTION.EVEN_PAGE}


def insert_section_break(document, paragraphs, start, where):
    """Ends a section after each paragraph. The new section after it starts as `start` and shows the same
    headers and footers until a change gives it its own."""
    if start not in SECTION_STARTS:
        raise ChangeError(f"{where} start is one of: {', '.join(SECTION_STARTS)}.")
    body = document.element.body
    for paragraph in paragraphs:
        if inside(paragraph, "w:tbl") is not None or paragraph.getparent() is not body:
            raise ChangeError(f"{where}: a section can end only after a paragraph of the body, not inside a table.")
        ppr = ensure_ppr(paragraph)
        if ppr.find(qn("w:sectPr")) is not None:
            continue
        following = next((p.find(f"{qn('w:pPr')}/{qn('w:sectPr')}") for p in paragraph.itersiblings(qn("w:p")) if p.find(f"{qn('w:pPr')}/{qn('w:sectPr')}") is not None), None)
        later = following if following is not None else body.find(qn("w:sectPr"))
        ended = copy.deepcopy(later)
        ensure(ppr, "sectPr", PPR_ORDER).getparent().replace(ppr.find(qn("w:sectPr")), ended)
        # The later section keeps showing the same headers by following the one before it.
        drop(later, "headerReference", "footerReference")
        drop(later, "titlePg")
        put(ensure(later, "type", SECT_ORDER), val={"nextPage": "nextPage", "continuous": "continuous", "oddPage": "oddPage", "evenPage": "evenPage"}[start])


def insert_toc(document, paragraphs, spec, where):
    levels = spec.get("levels", "1-3")
    if not isinstance(levels, str) or not re.fullmatch(r"[1-9]-[1-9]", levels):
        raise ChangeError(f"{where} levels is a range of heading levels like \"1-3\".")
    title = spec.get("title")
    placeholder = spec.get("placeholder", "")
    for name, value in (("title", title), ("placeholder", placeholder)):
        if value is not None and not isinstance(value, str):
            raise ChangeError(f"{where} {name} is text.")
    target = paragraphs[0]
    if title:
        heading = OxmlElement("w:p")
        target.addprevious(heading)
        style = next((s for s in document.styles if style_key(s.name or "") == "tocheading"), None)
        ppr = ensure_ppr(heading)
        if style is not None:
            put(ensure(ppr, "pStyle", PPR_ORDER), val=style.style_id)
        else:
            put(ensure(ppr, "jc", PPR_ORDER), val="center")
        plain_run(heading, title)
    field = OxmlElement("w:p")
    target.addprevious(field)
    begin = OxmlElement("w:r")
    char = OxmlElement("w:fldChar")
    put(char, fldCharType="begin", dirty="true")
    begin.append(char)
    field.append(begin)
    code = OxmlElement("w:r")
    instruction = OxmlElement("w:instrText")
    instruction.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    instruction.text = f' TOC \\o "{levels}" \\h \\z \\u '
    code.append(instruction)
    field.append(code)
    for kind in ("separate", "end"):
        if kind == "end" and placeholder:
            plain_run(field, placeholder)
        run = OxmlElement("w:r")
        char = OxmlElement("w:fldChar")
        put(char, fldCharType=kind)
        run.append(char)
        field.append(run)
    if spec.get("pageBreakAfter"):
        run = OxmlElement("w:r")
        brk = OxmlElement("w:br")
        put(brk, type="page")
        run.append(brk)
        field.append(run)
    # Word fills the contents in when the file opens.
    settings = document.settings.element
    update = settings.find(qn("w:updateFields"))
    if update is None:
        update = OxmlElement("w:updateFields")
        settings.append(update)
    put(update, val="true")


# MARK: Applying the changes

CHANGE_KINDS = ("where", "style", "table", "page", "header", "footer", "insert")


def format_paragraph(document, paragraph, font, paragraph_spec, only):
    if font:
        for run in runs_for(paragraph, only):
            apply_font(ensure_rpr(run), font)
        if only is None:
            apply_font(ensure(ensure_ppr(paragraph), "rPr", PPR_ORDER), font)
    if paragraph_spec:
        apply_paragraph(ensure_ppr(paragraph), paragraph_spec, document, size_of(document, paragraph, font or {}))


def apply(document, changes):
    """Applies each change in order and returns what each one touched."""
    if not isinstance(changes, list) or not changes:
        raise ChangeError('the spec needs "changes", a list of changes like [{"where": {"style": "Normal"}, "font": {"size": "小四"}}].')
    done = []
    for number, change in enumerate(changes, start=1):
        where = f"change {number}"
        try:
            done.append(apply_one(document, change, where))
        except ChangeError as error:
            message = str(error)
            raise ChangeError(message if message.startswith(where) else f"{where}: {message}") from error
    return done


def apply_one(document, change, where):
    if not isinstance(change, dict):
        raise ChangeError(f"{where} is an object; it was {type(change).__name__}.")
    kinds = [kind for kind in CHANGE_KINDS if kind in change]
    if len(kinds) != 1:
        raise ChangeError(f"{where} names one of: {', '.join(CHANGE_KINDS)}; it named {', '.join(kinds) or 'none'}.")
    kind = kinds[0]
    if kind == "where":
        known(change, ("where", "only", "font", "paragraph"), where)
        if "font" not in change and "paragraph" not in change:
            raise ChangeError(f"{where} needs font or paragraph, what to change.")
        font = checked_font(change["font"], f"{where} font") if "font" in change else None
        paragraph_spec = checked_paragraph(change["paragraph"], f"{where} paragraph") if "paragraph" in change else None
        only = change.get("only")
        if only is not None and (not isinstance(only, str) or not only):
            raise ChangeError(f"{where} only is the text inside the paragraphs to change.")
        paragraphs = selected(document, change["where"], f"{where} where")
        if only is not None:
            paragraphs = [p for p in paragraphs if only in paragraph_text(p)]
        if not paragraphs:
            raise ChangeError(f"{where} matched no paragraphs; read them with inspect and adjust where.")
        for paragraph in paragraphs:
            format_paragraph(document, paragraph, font, paragraph_spec, only)
        return {"change": where, "paragraphs": len(paragraphs)}
    if kind == "style":
        known(change, ("style", "font", "paragraph", "create"), where)
        create = change.get("create")
        if create is not None:
            create = known(create if isinstance(create, dict) else {}, ("basedOn",), f"{where} create")
        style = find_style(document, change["style"], f"{where} style", create)
        font = checked_font(change["font"], f"{where} font") if "font" in change else None
        paragraph_spec = checked_paragraph(change["paragraph"], f"{where} paragraph") if "paragraph" in change else None
        if font:
            apply_font(ensure_rpr(style.element), font)
        if paragraph_spec:
            if "style" in paragraph_spec:
                raise ChangeError(f"{where} paragraph cannot name a style inside a style change.")
            size = font.get("size") if font else None
            apply_paragraph(ensure_ppr(style.element), paragraph_spec, document, size or resolved_style_value(document, style.style_id, "size") or 10.5)
        return {"change": where, "style": style.name}
    if kind == "table":
        known(change, TABLE_FIELDS, where)
        tables = table_elements(document)
        chosen = tables if change["table"] == "all" else None
        if chosen is None:
            numbers = numbers_of(change["table"], f"{where} table")
            if any(n > len(tables) for n in numbers):
                raise ChangeError(f"{where}: there is no table {max(numbers)}; the document has {len(tables)} tables.")
            chosen = [tables[n - 1] for n in numbers]
        if not chosen:
            raise ChangeError(f"{where}: the document has no tables.")
        for number, table in enumerate(chosen, start=1):
            change_table(document, table, change, f"{where} table {number}")
        return {"change": where, "tables": len(chosen)}
    if kind == "page":
        known(change, ("page", "sections"), where)
        sections = sections_of(document, change.get("sections"), where)
        change_page(document, change["page"], sections, f"{where} page")
        return {"change": where, "sections": len(sections)}
    if kind in ("header", "footer"):
        known(change, (kind,), where)
        change_header_footer(document, kind, change[kind], f"{where} {kind}")
        return {"change": where, kind: True}
    known(change, ("insert", "before", "after", "start", "levels", "title", "placeholder", "pageBreakAfter"), where)
    what = change["insert"]
    sides = [side for side in ("before", "after") if side in change]
    if what not in ("page-break", "section-break", "toc") or len(sides) != 1:
        raise ChangeError(f"{where} insert is page-break, section-break or toc, with before or after naming where.")
    side = sides[0]
    paragraphs = selected(document, change[side], f"{where} {side}")
    if not paragraphs:
        raise ChangeError(f"{where} {side} matched no paragraphs; read them with inspect and adjust it.")
    if what == "page-break":
        insert_page_break(document, paragraphs, side, where)
    elif what == "section-break":
        if side == "before":
            paragraphs = [p.getprevious() for p in paragraphs]
            if any(p is None or p.tag != qn("w:p") for p in paragraphs):
                raise ChangeError(f"{where}: a section break goes after a paragraph; use after.")
        insert_section_break(document, paragraphs, change.get("start", "nextPage"), where)
    else:
        if side == "after":
            following = paragraphs[0].getnext()
            if following is None or following.tag != qn("w:p"):
                raise ChangeError(f"{where}: put the contents before a paragraph.")
            paragraphs = [following]
        insert_toc(document, paragraphs, change, where)
    return {"change": where, "inserted": what, "places": len(paragraphs)}


# MARK: Reading formatting back


def theme_fonts(document):
    """Theme font slots (minorEastAsia, majorHAnsi, …) and the faces they stand for."""
    found = {}
    theme = next((rel.target_part for rel in document.part.rels.values() if rel.reltype == RT.THEME), None)
    if theme is None:
        return found
    try:
        root = parse_xml(theme.blob)
    except Exception:  # A damaged theme only means its fonts cannot be named.
        return found
    a = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    for kind in ("major", "minor"):
        fonts = root.find(f".//{a}{kind}Font")
        if fonts is None:
            continue
        latin = fonts.find(f"{a}latin")
        east = fonts.find(f"{a}ea")
        hans = next((f.get("typeface") for f in fonts.findall(f"{a}font") if f.get("script") == "Hans"), None)
        latin_face = latin.get("typeface") if latin is not None else ""
        east_face = (east.get("typeface") if east is not None else "") or hans or ""
        found[f"{kind}HAnsi"] = found[f"{kind}Ascii"] = latin_face
        found[f"{kind}EastAsia"] = east_face
        found[f"{kind}Bidi"] = latin_face
    return found


def rpr_values(rpr, themes):
    """Font values set directly in one w:rPr."""
    values = {}
    if rpr is None:
        return values
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is not None:
        for slot, name in (("ascii", "latin"), ("eastAsia", "eastAsia")):
            theme = fonts.get(qn(f"w:{slot}Theme"))
            if theme:
                values[name] = f"theme {theme}" + (f" ({themes[theme]})" if themes.get(theme) else "")
            elif fonts.get(qn(f"w:{slot}")):
                values[name] = fonts.get(qn(f"w:{slot}"))
    size = rpr.find(qn("w:sz"))
    if size is not None:
        values["size"] = int(size.get(qn("w:val"))) / 2
    for name, tag in (("bold", "b"), ("italic", "i"), ("strike", "strike")):
        element = rpr.find(qn(f"w:{tag}"))
        if element is not None:
            values[name] = element.get(qn("w:val")) not in ("0", "false", "off")
    underline = rpr.find(qn("w:u"))
    if underline is not None:
        values["underline"] = underline.get(qn("w:val"))
    color = rpr.find(qn("w:color"))
    if color is not None and color.get(qn("w:val")) not in (None, "auto"):
        values["color"] = color.get(qn("w:val"))
    highlight = rpr.find(qn("w:highlight"))
    if highlight is not None:
        values["highlight"] = highlight.get(qn("w:val"))
    return values


def style_chain(document, style_id):
    styles = document.styles.element
    seen = []
    while style_id and style_id not in seen:
        seen.append(style_id)
        element = next((s for s in styles.findall(qn("w:style")) if s.get(qn("w:styleId")) == style_id), None)
        if element is None:
            break
        yield element
        based = element.find(qn("w:basedOn"))
        style_id = based.get(qn("w:val")) if based is not None else None


def resolved_style_value(document, style_id, name, themes=None):
    themes = themes if themes is not None else theme_fonts(document)
    for element in style_chain(document, style_id):
        values = rpr_values(element.find(qn("w:rPr")), themes)
        if name in values:
            return values[name]
    defaults = document.styles.element.find(f"{qn('w:docDefaults')}/{qn('w:rPrDefault')}/{qn('w:rPr')}")
    return rpr_values(defaults, themes).get(name)


def resolved(document, paragraph, run, themes, default_style):
    """What a run shows: its own values, else its paragraph style's, else the document's defaults."""
    own = rpr_values(run.find(qn("w:rPr")), themes)
    style_id = paragraph_style_id(paragraph, default_style)
    values = {}
    for name in ("latin", "eastAsia", "size", "bold", "italic", "underline", "color"):
        value = own.get(name)
        if value is None:
            value = resolved_style_value(document, style_id, name, themes)
        if value is None and name == "size":
            value = 10
        if value is not None and value is not False:
            values[name] = value
    return values


def length_text(twips_value):
    return f"{round(int(twips_value) / 566.929, 2)}cm"


def paragraph_format(document, paragraph):
    """Direct paragraph formatting, in the change spec's own words."""
    shown = {}
    ppr = paragraph.find(qn("w:pPr"))
    if ppr is None:
        return shown
    jc = ppr.find(qn("w:jc"))
    if jc is not None:
        shown["align"] = {v: k for k, v in ALIGNMENTS.items() if k not in ("centre", "both")}.get(jc.get(qn("w:val")), jc.get(qn("w:val")))
    ind = ppr.find(qn("w:ind"))
    if ind is not None:
        for name, plain in (("leftIndent", "left"), ("rightIndent", "right"), ("firstLineIndent", "firstLine"), ("hangingIndent", "hanging")):
            chars = ind.get(qn(f"w:{plain}Chars"))
            value = ind.get(qn(f"w:{plain}")) or ind.get(qn(f"w:{ {'left': 'start', 'right': 'end'}.get(plain, plain) }"))
            if chars and chars != "0":
                shown[name] = f"{int(chars) / 100:g}字符"
            elif value and value != "0":
                shown[name] = length_text(value)
    spacing = ppr.find(qn("w:spacing"))
    if spacing is not None:
        line, rule = spacing.get(qn("w:line")), spacing.get(qn("w:lineRule")) or "auto"
        if line:
            shown["lineSpacing"] = round(int(line) / 240, 2) if rule == "auto" else ({"exactly": f"{int(line) / 20:g}pt"} if rule == "exact" else {"atLeast": f"{int(line) / 20:g}pt"})
        for name, side in (("spaceBefore", "before"), ("spaceAfter", "after")):
            lines = spacing.get(qn(f"w:{side}Lines"))
            value = spacing.get(qn(f"w:{side}"))
            if lines:
                shown[name] = f"{int(lines) / 100:g}行"
            elif value:
                shown[name] = f"{int(value) / 20:g}pt"
    for name, tag in (("keepWithNext", "keepNext"), ("keepTogether", "keepLines"), ("pageBreakBefore", "pageBreakBefore")):
        element = ppr.find(qn(f"w:{tag}"))
        if element is not None and element.get(qn("w:val")) not in ("0", "false"):
            shown[name] = True
    if ppr.find(qn("w:sectPr")) is not None:
        shown["sectionEndsHere"] = True
    return shown


def header_footer_text(part):
    """A header's or footer's text, with its fields shown as {PAGE}, {NUMPAGES} and so on."""
    lines = []
    for paragraph in part.element.iter(qn("w:p")):
        line = []
        state = None  # None, "code" or "result" of a field
        for run in own_runs(paragraph):
            char = run.find(qn("w:fldChar"))
            if char is not None:
                state = {"begin": "code", "separate": "result", "end": None}.get(char.get(qn("w:fldCharType")), state)
                continue
            code = run.find(qn("w:instrText"))
            if code is not None:
                words = (code.text or "").split()
                line.append(f"{{{words[0]}}}" if words else "")
            elif state != "result":
                line.append(run_text(run))
        for simple in paragraph.iter(qn("w:fldSimple")):
            words = (simple.get(qn("w:instr")) or "").split()
            line.append(f"{{{words[0]}}}" if words else "")
        lines.append("".join(line))
    return "\n".join(lines)


def section_report(document, section, number):
    sect = section._sectPr
    report = {"section": number, "page": {
        "width": length_text(section.page_width / 635),
        "height": length_text(section.page_height / 635),
        "orientation": "landscape" if section.orientation == WD_ORIENT.LANDSCAPE else "portrait",
        "margins": {name: length_text(getattr(section, attribute) / 635) for name, attribute in (
            ("top", "top_margin"), ("bottom", "bottom_margin"), ("left", "left_margin"), ("right", "right_margin"),
            ("header", "header_distance"), ("footer", "footer_distance")) if getattr(section, attribute) is not None}}}
    start = sect.find(qn("w:type"))
    report["start"] = start.get(qn("w:val")) if start is not None else "nextPage"
    numbers = sect.find(qn("w:pgNumType"))
    if numbers is not None:
        report["pageNumbers"] = {k: v for k, v in (("start", numbers.get(qn("w:start"))), ("format", numbers.get(qn("w:fmt")))) if v}
    if sect.find(qn("w:titlePg")) is not None:
        report["differentFirstPage"] = True
    for kind in ("header", "footer"):
        for pages, attribute in (("default", kind), ("first", f"first_page_{kind}"), ("even", f"even_page_{kind}")):
            part = getattr(section, attribute)
            if number > 1 and part.is_linked_to_previous:
                if pages == "default":
                    report[kind] = "same as the previous section"
                continue
            if part._has_definition:
                text = header_footer_text(part.part)
                report[kind if pages == "default" else f"{pages}Page{kind.title()}"] = text
    return report


def border_report(holder):
    if holder is None:
        return None
    return {child.tag.split("}")[1]: (child.get(qn("w:val")) if child.get(qn("w:val")) in ("nil", "none") else
            f"{child.get(qn('w:val'))} {int(child.get(qn('w:sz')) or 0) / 8:g}pt") for child in holder}


def table_report(table, number):
    rows = table.tr_lst
    columns = table.tblGrid.findall(qn("w:gridCol")) if table.tblGrid is not None else []
    report = {"table": number, "rows": len(rows), "columns": len(columns),
              "columnWidths": [length_text(c.get(qn("w:w")) or 0) for c in columns]}
    properties = table.tblPr
    width = properties.find(qn("w:tblW"))
    if width is not None:
        kind, value = width.get(qn("w:type")), width.get(qn("w:w")) or "0"
        report["width"] = f"{int(value) / 50:g}%" if kind == "pct" else (length_text(value) if kind == "dxa" else "auto")
    jc = properties.find(qn("w:jc"))
    if jc is not None:
        report["align"] = jc.get(qn("w:val"))
    style = properties.find(qn("w:tblStyle"))
    if style is not None:
        report["style"] = style.get(qn("w:val"))
    report["borders"] = border_report(properties.find(qn("w:tblBorders")))
    merged = []
    cell_borders = []
    for row, first, last, cell in grid_cells(table):
        if last > first:
            merged.append({"row": row, "columns": f"{first}-{last}"})
        tcpr = cell.find(qn("w:tcPr"))
        if tcpr is not None and tcpr.find(qn("w:vMerge")) is not None:
            merged.append({"row": row, "column": first, "vertical": tcpr.find(qn("w:vMerge")).get(qn("w:val")) or "continue"})
        if tcpr is not None and tcpr.find(qn("w:tcBorders")) is not None:
            cell_borders.append({"row": row, "column": first, **border_report(tcpr.find(qn("w:tcBorders")))})
    if merged:
        report["merged"] = merged
    if cell_borders:
        report["cellBorders"] = cell_borders[:40]
    header_rows = sum(1 for row in rows if row.find(qn("w:trPr")) is not None and row.trPr.find(qn("w:tblHeader")) is not None)
    if header_rows:
        report["headerRepeat"] = header_rows
    return report


def inspect(document, first=None, last=None, preview=60):
    """The document's formatting: sections, tables, every numbered paragraph with what its runs show, and a
    tally of the text formats used, so a check can find text whose font or size differs from the rest."""
    themes = theme_fonts(document)
    default_style = document.styles.default(WD_STYLE_TYPE.PARAGRAPH)
    names = {s.style_id: s.name for s in document.styles}
    paragraphs = []
    tally = {}
    for number, (paragraph, table) in enumerate(numbered_paragraphs(document), start=1):
        style_id = paragraph_style_id(paragraph, default_style)
        runs = []
        for run in own_runs(paragraph):
            text = run_text(run)
            if not text.strip():
                continue
            values = resolved(document, paragraph, run, themes, default_style)
            key = (names.get(style_id, style_id), values.get("eastAsia"), values.get("latin"), values.get("size"), bool(values.get("bold")))
            entry = tally.setdefault(key, {"chars": 0, "paragraphs": []})
            entry["chars"] += len(text)
            if number not in entry["paragraphs"] and len(entry["paragraphs"]) < 12:
                entry["paragraphs"].append(number)
            if runs and {k: v for k, v in runs[-1].items() if k != "text"} == values:
                runs[-1]["text"] += text
            else:
                runs.append({"text": text, **values})
        if (first is not None and number < first) or (last is not None and number > last):
            continue
        text = paragraph_text(paragraph)
        entry = {"n": number, "style": names.get(style_id, style_id), "text": text if len(text) <= preview else text[:preview] + "…"}
        if table is not None:
            entry["table"] = table
        entry.update(paragraph_format(document, paragraph))
        for run in runs:
            if len(run["text"]) > 24:
                run["text"] = run["text"][:24] + "…"
        if runs:
            entry["runs"] = runs
        paragraphs.append(entry)
    formats = [{"style": k[0], "eastAsia": k[1], "latin": k[2], "size": k[3], "bold": k[4], **v} for k, v in tally.items()]
    formats.sort(key=lambda f: -f["chars"])
    used = {s for s in (p["style"] for p in paragraphs)} | {f["style"] for f in formats}
    styles = {}
    for style in document.styles:
        if style.name in used and style.type == WD_STYLE_TYPE.PARAGRAPH:
            values = {name: resolved_style_value(document, style.style_id, name, themes) for name in ("latin", "eastAsia", "size", "bold")}
            values = {k: v for k, v in values.items() if v is not None}
            values.update(paragraph_format(document, style.element))
            styles[style.name] = values
    return {
        "sections": [section_report(document, section, number) for number, section in enumerate(document.sections, start=1)],
        "styles": styles,
        "tables": [table_report(table, number) for number, table in enumerate(table_elements(document), start=1)],
        "textFormats": formats,
        "paragraphs": paragraphs,
    }

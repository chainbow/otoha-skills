"""Changes an existing PowerPoint deck from a list of changes: text formatting, position, links, animations,
media with its start, slide transitions and slide order; and reads all of that back.

Used by deck.py's `change` and `inspect` commands; see the skill's SKILL.md for the changes. Everything a
change does not name, other slides, layouts and masters included, is left as it was.
"""

import copy
import io
import json
import re
import shutil
import subprocess
import wave

from PIL import Image, ImageDraw
from pptx.media import Video
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn
from pptx.oxml.xmlchemy import OxmlElement
from pptx.shapes.group import GroupShape
from pptx.text.text import _Paragraph
from pptx.util import Emu, Pt


class ChangeError(Exception):
    """A change cannot be made; the message says what to change."""


P14 = "http://schemas.microsoft.com/office/powerpoint/2010/main"
MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"

# MARK: Values

NAMED_SIZES = {
    "初号": 42, "小初": 36, "一号": 26, "小一": 24, "二号": 22, "小二": 18, "三号": 16, "小三": 15,
    "四号": 14, "小四": 12, "五号": 10.5, "小五": 9, "六号": 7.5, "小六": 6.5, "七号": 5.5, "八号": 5,
}
NUMBER = r"(-?\d+(?:\.\d+)?)"
EMU_PER = {"": 12700, "pt": 12700, "磅": 12700, "cm": 360000, "厘米": 360000, "mm": 36000, "毫米": 36000,
           "in": 914400, "inch": 914400, "英寸": 914400, "emu": 1}


def font_size(value, where):
    if isinstance(value, str) and value.strip() in NAMED_SIZES:
        return NAMED_SIZES[value.strip()]
    points = value
    if isinstance(value, str):
        found = re.fullmatch(rf"\s*{NUMBER}\s*(pt|磅)?\s*", value)
        points = float(found.group(1)) if found else None
    if isinstance(points, bool) or not isinstance(points, (int, float)) or not 1 <= points <= 4000:
        raise ChangeError(f"{where} size is points (24, \"18pt\") or a named size ({'、'.join(NAMED_SIZES)}); it was {value!r}.")
    return points


def length(value, where):
    """EMU from "2cm", "1in", "12pt" or 12 (points)."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return Emu(round(value * 12700))
    if isinstance(value, str):
        found = re.fullmatch(rf"\s*{NUMBER}\s*([a-zA-Z磅厘米毫英寸]*)\s*", value)
        if found and found.group(2).lower() in EMU_PER:
            return Emu(round(float(found.group(1)) * EMU_PER[found.group(2).lower()]))
    raise ChangeError(f"{where} is a length like \"2cm\", \"1in\" or 12 (points); it was {value!r}.")


def seconds(value, where, low=0.0, high=3600.0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
        raise ChangeError(f"{where} is a number of seconds from {low:g} to {high:g}; it was {value!r}.")
    return round(value * 1000)


def flag(value, where):
    if not isinstance(value, bool):
        raise ChangeError(f"{where} is true or false; it was {value!r}.")
    return value


def colour(value, where):
    if not isinstance(value, str) or not re.fullmatch(r"#?[0-9A-Fa-f]{6}", value.strip()):
        raise ChangeError(f"{where} is a colour of six hexadecimal digits, like \"#C00000\"; it was {value!r}.")
    return value.strip().lstrip("#").upper()


def known(spec, allowed, where):
    if not isinstance(spec, dict):
        raise ChangeError(f"{where} is an object with named fields; it was {type(spec).__name__}.")
    unknown = [key for key in spec if key not in allowed]
    if unknown:
        raise ChangeError(f"{where} has {', '.join(map(repr, unknown))}, which is not one of: {', '.join(allowed)}.")
    return spec


def numbers_of(value, where, top):
    items = value if isinstance(value, list) else [value]
    found = []
    for item in items:
        if isinstance(item, int) and not isinstance(item, bool) and item >= 1:
            found.append(item)
        elif isinstance(item, str) and re.fullmatch(r"\s*\d+\s*-\s*\d+\s*", item):
            first, last = (int(part) for part in item.split("-"))
            found.extend(range(first, last + 1))
        else:
            raise ChangeError(f"{where} is a number from 1, a list like [1, 4], a range like \"2-5\", or \"all\"; it was {value!r}.")
    for number in found:
        if number > top:
            raise ChangeError(f"{where}: the deck has slides 1 to {top}; there is no slide {number}.")
    return found


# MARK: Text

RPR_ORDER = ("ln", "noFill", "solidFill", "gradFill", "blipFill", "pattFill", "grpFill", "effectLst", "effectDag",
             "highlight", "uLnTx", "uLn", "uFillTx", "uFill", "latin", "ea", "cs", "sym", "hlinkClick",
             "hlinkMouseOver", "rtl", "extLst")
FILLS = ("noFill", "solidFill", "gradFill", "blipFill", "pattFill", "grpFill")
FONT_FIELDS = ("name", "latin", "eastAsia", "size", "bold", "italic", "underline", "strike", "color")
UNDERLINES = {"single": "sng", "double": "dbl", "thick": "heavy", "dotted": "dotted", "dash": "dash", "wave": "wavy", "none": "none"}
PARAGRAPH_FIELDS = ("align", "lineSpacing", "spaceBefore", "spaceAfter")
ALIGNMENTS = {"left": "l", "center": "ctr", "centre": "ctr", "right": "r", "justify": "just", "distribute": "dist"}


def ensure(parent, name, order):
    tag = qn(f"a:{name}")
    found = parent.find(tag)
    if found is not None:
        return found
    made = OxmlElement(f"a:{name}")
    for later in order[order.index(name) + 1:]:
        sibling = parent.find(qn(f"a:{later}"))
        if sibling is not None:
            sibling.addprevious(made)
            return made
    parent.append(made)
    return made


def checked_font(spec, where):
    font = dict(known(spec, FONT_FIELDS, where))
    for name in ("name", "latin", "eastAsia"):
        if name in font and (not isinstance(font[name], str) or not font[name].strip()):
            raise ChangeError(f"{where} {name} is a font's name, like \"黑体\" or \"Arial\".")
    if "size" in font:
        font["size"] = font_size(font["size"], where)
    for name in ("bold", "italic", "strike"):
        if name in font:
            flag(font[name], f"{where} {name}")
    if "underline" in font:
        value = font["underline"]
        value = ("single" if value else "none") if isinstance(value, bool) else value
        if value not in UNDERLINES:
            raise ChangeError(f"{where} underline is true, false or one of: {', '.join(UNDERLINES)}.")
        font["underline"] = UNDERLINES[value]
    if "color" in font:
        font["color"] = colour(font["color"], f"{where} color")
    return font


def apply_font(rpr, font):
    faces = {}
    if "name" in font:
        faces.update(latin=font["name"], ea=font["name"], cs=font["name"])
    if "latin" in font:
        faces.update(latin=font["latin"], cs=font["latin"])
    if "eastAsia" in font:
        faces["ea"] = font["eastAsia"]
    for slot, face in faces.items():
        element = ensure(rpr, slot, RPR_ORDER)
        element.attrib.clear()
        element.set("typeface", face)
    if "size" in font:
        rpr.set("sz", str(round(font["size"] * 100)))
    for name, attribute in (("bold", "b"), ("italic", "i")):
        if name in font:
            rpr.set(attribute, "1" if font[name] else "0")
    if "strike" in font:
        rpr.set("strike", "sngStrike" if font["strike"] else "noStrike")
    if "underline" in font:
        rpr.set("u", font["underline"])
    if "color" in font:
        for fill in FILLS:
            for found in rpr.findall(qn(f"a:{fill}")):
                rpr.remove(found)
        fill = ensure(rpr, "solidFill", RPR_ORDER)
        colour_element = OxmlElement("a:srgbClr")
        colour_element.set("val", font["color"])
        fill.append(colour_element)


def line_spacing(paragraph, value, where):
    if isinstance(value, (int, float)) and not isinstance(value, bool) and 0.25 <= value <= 10:
        paragraph.line_spacing = float(value)
    elif isinstance(value, dict) and set(value) == {"exactly"}:
        paragraph.line_spacing = Pt(length(value["exactly"], where) / 12700)
    elif isinstance(value, str):
        paragraph.line_spacing = Pt(length(value, where) / 12700)
    else:
        raise ChangeError(f"{where} is a multiple (1.5) or exact points (\"28pt\"); it was {value!r}.")


def checked_paragraph(spec, where):
    spec = known(spec, PARAGRAPH_FIELDS, where)
    if "align" in spec and spec["align"] not in ALIGNMENTS:
        raise ChangeError(f"{where} align is one of: {', '.join(ALIGNMENTS)}.")
    return spec


def apply_paragraph(p, spec, shape, where):
    paragraph = _Paragraph(p, shape)
    if "align" in spec:
        p.get_or_add_pPr().set("algn", ALIGNMENTS[spec["align"]])
    if "lineSpacing" in spec:
        line_spacing(paragraph, spec["lineSpacing"], f"{where} lineSpacing")
    for name, attribute in (("spaceBefore", "space_before"), ("spaceAfter", "space_after")):
        if name in spec:
            setattr(paragraph, attribute, Pt(length(spec[name], f"{where} {name}") / 12700))


def text_paragraphs(element):
    """Every a:p of a shape's text, table cells' included."""
    return list(element.iter(qn("a:p")))


def text_runs(p):
    return [child for child in p if child.tag in (qn("a:r"), qn("a:fld"))]


def run_text(run):
    t = run.find(qn("a:t"))
    return t.text or "" if t is not None else ""


def runs_for(p, only):
    """The runs of a paragraph holding `only`, split at its edges; all runs when only is None."""
    runs = text_runs(p)
    if only is None:
        return runs
    text = "".join(run_text(r) for r in runs)
    spans = [(m.start(), m.end()) for m in re.finditer(re.escape(only), text)]
    chosen = []
    offset = 0
    for run in runs:
        start, end = offset, offset + len(run_text(run))
        offset = end
        cuts = sorted({max(start, min(end, edge)) for span in spans for edge in span} | {start, end})
        pieces = [(a, b) for a, b in zip(cuts, cuts[1:]) if b > a]
        inside = [any(s <= a and b <= e for s, e in spans) for a, b in pieces]
        if not any(inside):
            continue
        if all(inside) or run.tag != qn("a:r"):
            chosen.append(run)
            continue
        whole = run_text(run)
        for (a, b), wanted in zip(pieces, inside):
            piece = copy.deepcopy(run)
            piece.find(qn("a:t")).text = whole[a - start:b - start]
            run.addprevious(piece)
            if wanted:
                chosen.append(piece)
        run.getparent().remove(run)
    return chosen


def rpr_of(run):
    return run.get_or_add_rPr()


# MARK: Finding slides and shapes

PLACEHOLDERS = {"title": ("title", "ctrTitle"), "subtitle": ("subTitle",), "body": ("body", "obj"),
                "date": ("dt",), "footer": ("ftr",), "slide-number": ("sldNum",), "picture": ("pic",),
                "chart": ("chart",), "table": ("tbl",)}


def slides_of(deck, value, where):
    if value == "all":
        return list(deck.slides)
    return [deck.slides[n - 1] for n in numbers_of(value, f"{where} slide", len(deck.slides))]


def all_shapes(shapes):
    for shape in shapes:
        yield shape
        if isinstance(shape, GroupShape):
            yield from all_shapes(shape.shapes)


def placeholder_type(shape):
    ph = shape._element.find(f".//{qn('p:nvPr')}/{qn('p:ph')}")
    if ph is None:
        return None
    return ph.get("type", "obj")


def shape_text(shape):
    return "".join(t.text or "" for t in shape._element.iter(qn("a:t")))


def shapes_of(slide, value, where):
    shapes = list(slide.shapes)
    if value == "all":
        return [s for s in all_shapes(shapes)]
    if isinstance(value, int) and not isinstance(value, bool):
        if not 1 <= value <= len(shapes):
            raise ChangeError(f"{where}: the slide has shapes 1 to {len(shapes)}; there is no shape {value}.")
        return [shapes[value - 1]]
    if isinstance(value, str):
        value = {"name": value}
    value = known(value, ("name", "id", "contains", "placeholder"), where)
    found = list(all_shapes(shapes))
    if "name" in value:
        found = [s for s in found if s.name == value["name"]]
    if "id" in value:
        found = [s for s in found if s.shape_id == value["id"]]
    if "contains" in value:
        found = [s for s in found if isinstance(value["contains"], str) and value["contains"] in shape_text(s)]
    if "placeholder" in value:
        kinds = PLACEHOLDERS.get(value["placeholder"])
        if kinds is None:
            raise ChangeError(f"{where} placeholder is one of: {', '.join(PLACEHOLDERS)}.")
        found = [s for s in found if placeholder_type(s) in kinds]
    if not found:
        raise ChangeError(f"{where}: no shape on the slide is {json.dumps(value, ensure_ascii=False)}; read the slide with inspect.")
    return found


# MARK: Links

ACTIONS = {"next": "nextslide", "previous": "previousslide", "first": "firstslide", "last": "lastslide", "end": "endshow"}


def link_element(deck, slide, target, where):
    """A new a:hlinkClick for {"url"}, {"slide"} or {"action"}; None to remove a link."""
    if target in (None, "none"):
        return None
    target = known(target, ("url", "slide", "action"), where)
    if len(target) != 1:
        raise ChangeError(f'{where} is one of {{"url": "https://…"}}, {{"slide": 3}} or {{"action": "next"}}.')
    link = OxmlElement("a:hlinkClick")
    if "url" in target:
        url = target["url"]
        if not isinstance(url, str) or not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", url.strip()):
            raise ChangeError(f"{where} url is a full address like https://example.com; it was {url!r}.")
        link.set(qn("r:id"), slide.part.relate_to(url.strip(), RT.HYPERLINK, is_external=True))
    elif "slide" in target:
        number = target["slide"]
        if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= len(deck.slides):
            raise ChangeError(f"{where}: the deck has slides 1 to {len(deck.slides)}; there is no slide {number}.")
        link.set(qn("r:id"), slide.part.relate_to(deck.slides[number - 1].part, RT.SLIDE))
        link.set("action", "ppaction://hlinksldjump")
    else:
        if target["action"] not in ACTIONS:
            raise ChangeError(f"{where} action is one of: {', '.join(ACTIONS)}.")
        link.set(qn("r:id"), "")
        link.set("action", f"ppaction://hlinkshowjump?jump={ACTIONS[target['action']]}")
    return link


def set_run_link(rpr, link):
    for found in rpr.findall(qn("a:hlinkClick")):
        rpr.remove(found)
    if link is not None:
        ensure(rpr, "hlinkClick", RPR_ORDER).getparent().replace(rpr.find(qn("a:hlinkClick")), link)


def set_shape_link(shape, link):
    properties = shape._element.find(f"./*[1]/{qn('p:cNvPr')}")
    for found in properties.findall(qn("a:hlinkClick")):
        properties.remove(found)
    if link is not None:
        properties.insert(0, link)


# MARK: Transitions

TRANSITIONS = ("fade", "push", "wipe", "split", "cover", "pull", "cut", "dissolve", "zoom", "random", "wheel",
               "circle", "blinds", "checker", "randomBar", "strips", "wedge", "diamond", "plus", "newsflash", "comb")
# Where the new slide comes from, as PowerPoint's effect options name it, and the way it moves.
FROM = {"right": "l", "from-right": "l", "left": "r", "from-left": "r", "bottom": "u", "from-bottom": "u", "top": "d", "from-top": "d"}


def remove_transition(sld):
    for child in list(sld):
        if child.tag == qn("p:transition") or (child.tag == f"{{{MC}}}AlternateContent" and child.find(f".//{qn('p:transition')}") is not None):
            sld.remove(child)


def set_transition(slide, spec, where):
    sld = slide._element
    if spec in (None, "none"):
        remove_transition(sld)
        return
    spec = known(spec, ("type", "direction", "duration", "advanceOnClick", "advanceAfter"), where)
    kind = spec.get("type", "fade")
    if kind not in TRANSITIONS:
        raise ChangeError(f"{where} type is one of: {', '.join(TRANSITIONS)}.")
    attributes = {}
    if "direction" in spec:
        if kind not in ("push", "wipe", "cover", "pull"):
            raise ChangeError(f"{where} direction applies to push, wipe, cover and pull.")
        if spec["direction"] not in FROM:
            raise ChangeError(f"{where} direction is where the slide comes from: left, right, top or bottom.")
        attributes["dir"] = FROM[spec["direction"]]
    duration = seconds(spec.get("duration", 0.7), f"{where} duration", 0.01, 60)
    speed = "fast" if duration <= 500 else "med" if duration <= 750 else "slow"
    timing = f' advClick="{"1" if flag(spec.get("advanceOnClick", True), f"{where} advanceOnClick") else "0"}"'
    if "advanceAfter" in spec:
        timing += f' advTm="{seconds(spec["advanceAfter"], f"{where} advanceAfter")}"'
    effect = f"<p:{kind}" + "".join(f' {k}="{v}"' for k, v in attributes.items()) + "/>"
    xml = (f'<mc:AlternateContent xmlns:mc="{MC}" {nsdecls("p")}>'
           f'<mc:Choice xmlns:p14="{P14}" Requires="p14"><p:transition spd="{speed}" p14:dur="{duration}"{timing}>{effect}</p:transition></mc:Choice>'
           f'<mc:Fallback><p:transition spd="{speed}"{timing}>{effect}</p:transition></mc:Fallback></mc:AlternateContent>')
    remove_transition(sld)
    element = parse_xml(xml)
    later = sld.find(qn("p:timing"))
    if later is None:
        later = sld.find(qn("p:extLst"))
    if later is not None:
        later.addprevious(element)
    else:
        sld.append(element)


# MARK: Animations

STARTS = {"click": "clickEffect", "with-previous": "withEffect", "after-previous": "afterEffect", "auto": "afterEffect"}
DIRECTIONS = {"top": 1, "from-top": 1, "right": 2, "from-right": 2, "bottom": 4, "from-bottom": 4, "left": 8, "from-left": 8}
WIPES = {1: "wipe(down)", 2: "wipe(left)", 4: "wipe(up)", 8: "wipe(right)"}
FLY_FROM = {1: ("#ppt_x", "0-#ppt_h/2"), 2: ("1+#ppt_w/2", "#ppt_y"), 4: ("#ppt_x", "1+#ppt_h/2"), 8: ("0-#ppt_w/2", "#ppt_y")}
FLY_TO = {1: ("ppt_x", "0-ppt_h/2"), 2: ("1+ppt_w/2", "ppt_y"), 4: ("ppt_x", "1+ppt_h/2"), 8: ("0-ppt_w/2", "ppt_y")}
# (type, effect): (presetClass, presetID, default seconds, takes a direction)
EFFECTS = {
    ("entrance", "appear"): ("entr", 1, 0, False),
    ("entrance", "fade"): ("entr", 10, 0.5, False),
    ("entrance", "fly-in"): ("entr", 2, 0.5, True),
    ("entrance", "wipe"): ("entr", 22, 0.5, True),
    ("entrance", "zoom"): ("entr", 53, 0.5, False),
    ("emphasis", "spin"): ("emph", 8, 2, False),
    ("emphasis", "grow"): ("emph", 6, 2, False),
    ("exit", "disappear"): ("exit", 1, 0, False),
    ("exit", "fade"): ("exit", 10, 0.5, False),
    ("exit", "fly-out"): ("exit", 2, 0.5, True),
    ("exit", "wipe"): ("exit", 22, 0.5, True),
    ("exit", "zoom"): ("exit", 53, 0.5, False),
}
NAMES = {(cls, pid): name for (_, name), (cls, pid, _, _) in EFFECTS.items()}
TYPES = {"entr": "entrance", "emph": "emphasis", "exit": "exit", "mediacall": "media"}
ANIMATION_FIELDS = ("type", "effect", "start", "delay", "duration", "direction", "repeat", "scale")


class Ids:
    """Unique p:cTn numbers for a slide."""

    def __init__(self, sld):
        self.sld = sld
        self.last = 0

    def __call__(self):
        # The tree is read again each time: the timing root may have been added since.
        found = [int(v) for v in self.sld.xpath(".//p:timing//p:cTn/@id") if v.isdigit()]
        self.last = max([self.last, *found]) + 1
        return self.last


def target(spid):
    return f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl>'


def visibility(ids, spid, value, at):
    return (f'<p:set><p:cBhvr><p:cTn id="{ids()}" dur="1" fill="hold"><p:stCondLst><p:cond delay="{at}"/></p:stCondLst></p:cTn>'
            f'{target(spid)}<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr>'
            f'<p:to><p:strVal val="{value}"/></p:to></p:set>')


def motion(ids, spid, attribute, start, end, duration):
    return (f'<p:anim calcmode="lin" valueType="num"><p:cBhvr additive="base"><p:cTn id="{ids()}" dur="{duration}" fill="hold"/>'
            f'{target(spid)}<p:attrNameLst><p:attrName>{attribute}</p:attrName></p:attrNameLst></p:cBhvr>'
            f'<p:tavLst><p:tav tm="0"><p:val><p:strVal val="{start}"/></p:val></p:tav>'
            f'<p:tav tm="100000"><p:val><p:strVal val="{end}"/></p:val></p:tav></p:tavLst></p:anim>')


def filtered(ids, spid, way, name, duration):
    return f'<p:animEffect transition="{way}" filter="{name}"><p:cBhvr><p:cTn id="{ids()}" dur="{duration}"/>{target(spid)}</p:cBhvr></p:animEffect>'


def behaviours(ids, spid, cls, pid, subtype, duration, scale):
    """The XML that makes one preset effect happen."""
    show, hide = cls == "entr", cls == "exit"
    parts = [visibility(ids, spid, "visible", 0)] if show else []
    if pid == 10 and cls != "emph":
        parts.append(filtered(ids, spid, "in" if show else "out", "fade", duration))
    elif pid == 22:
        parts.append(filtered(ids, spid, "in" if show else "out", WIPES[subtype], duration))
    elif pid == 2:
        (x0, y0), (x1, y1) = (FLY_FROM[subtype], ("#ppt_x", "#ppt_y")) if show else (("ppt_x", "ppt_y"), FLY_TO[subtype])
        parts += [motion(ids, spid, "ppt_x", x0, x1, duration), motion(ids, spid, "ppt_y", y0, y1, duration)]
    elif pid == 53:
        if show:
            parts += [motion(ids, spid, "ppt_w", "0", "#ppt_w", duration), motion(ids, spid, "ppt_h", "0", "#ppt_h", duration)]
        else:
            parts += [motion(ids, spid, "ppt_w", "ppt_w", "0", duration), motion(ids, spid, "ppt_h", "ppt_h", "0", duration)]
        parts.append(filtered(ids, spid, "in" if show else "out", "fade", duration))
    elif cls == "emph" and pid == 8:
        parts.append(f'<p:animRot by="21600000"><p:cBhvr><p:cTn id="{ids()}" dur="{duration}" fill="hold"/>{target(spid)}'
                     f'<p:attrNameLst><p:attrName>r</p:attrName></p:attrNameLst></p:cBhvr></p:animRot>')
    elif cls == "emph" and pid == 6:
        parts.append(f'<p:animScale><p:cBhvr><p:cTn id="{ids()}" dur="{duration}" fill="hold"/>{target(spid)}</p:cBhvr>'
                     f'<p:by x="{scale}" y="{scale}"/></p:animScale>')
    if hide:
        parts.append(visibility(ids, spid, "hidden", max(0, duration - 1)))
    return "".join(parts)


def main_sequence(slide, ids):
    """The slide's click sequence (p:cTn nodeType="mainSeq"), made when missing."""
    sld = slide._element
    found = sld.xpath("./p:timing/p:tnLst/p:par/p:cTn/p:childTnLst/p:seq/p:cTn[@nodeType='mainSeq']")
    if found:
        return found[0]
    root = sld.get_or_add_childTnLst()
    sequence = parse_xml(
        f'<p:seq {nsdecls("p")} concurrent="1" nextAc="seek"><p:cTn id="{ids()}" dur="indefinite" nodeType="mainSeq"><p:childTnLst/></p:cTn>'
        '<p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
        '<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq>')
    root.insert(0, sequence)
    return sequence.find(qn("p:cTn"))


def delay_of(ctn):
    conditions = ctn.find(qn("p:stCondLst"))
    first = conditions[0] if conditions is not None and len(conditions) else None
    value = first.get("delay") if first is not None else "0"
    return int(value) if value and value.isdigit() else 0


def effect_length(ctn):
    """How long an effect runs, from its own timing: the longest of its parts, times its repeats."""
    longest = 0
    for part in ctn.iter(qn("p:cTn")):
        if part is ctn:
            continue
        duration = part.get("dur", "0")
        if duration.isdigit():
            longest = max(longest, delay_of(part) + int(duration))
    repeat = ctn.get("repeatCount", "1000")
    return longest * (int(repeat) / 1000 if repeat.isdigit() else 1)


def step_end(step):
    ctn = step.find(qn("p:cTn"))
    effects = [par.find(qn("p:cTn")) for par in ctn.find(qn("p:childTnLst"))]
    return delay_of(ctn) + max((delay_of(e) + effect_length(e) for e in effects), default=0)


def new_par(ids, conditions):
    return parse_xml(f'<p:par {nsdecls("p")}><p:cTn id="{ids()}" fill="hold"><p:stCondLst>{conditions}</p:stCondLst><p:childTnLst/></p:cTn></p:par>')


def place_effect(slide, ids, start, effect_xml):
    """Puts an effect into the click sequence: a new click, with the previous effect, or after it."""
    sequence = main_sequence(slide, ids)
    groups = sequence.find(qn("p:childTnLst"))
    if start == "clickEffect" or not len(groups):
        first = not len(groups) and start != "clickEffect"
        extra = f'<p:cond evt="onBegin" delay="0"><p:tn val="{sequence.get("id")}"/></p:cond>' if first else ""
        group = new_par(ids, f'<p:cond delay="indefinite"/>{extra}')
        groups.append(group)
        step = new_par(ids, '<p:cond delay="0"/>')
        group.find(qn("p:cTn")).find(qn("p:childTnLst")).append(step)
    else:
        group = groups[-1]
        steps = group.find(qn("p:cTn")).find(qn("p:childTnLst"))
        if start == "withEffect" and len(steps):
            step = steps[-1]
        else:
            begins = step_end(steps[-1]) if len(steps) else 0
            step = new_par(ids, f'<p:cond delay="{round(begins)}"/>')
            steps.append(step)
    step.find(qn("p:cTn")).find(qn("p:childTnLst")).append(parse_xml(effect_xml))


def build_list(slide, spid):
    """Text shapes animated by the sequence are listed in p:bldLst, as PowerPoint expects."""
    timing = slide._element.find(qn("p:timing"))
    builds = timing.find(qn("p:bldLst"))
    if builds is None:
        builds = OxmlElement("p:bldLst")
        timing.find(qn("p:tnLst")).addnext(builds)
    if not any(b.get("spid") == str(spid) for b in builds):
        made = OxmlElement("p:bldP")
        made.set("spid", str(spid))
        made.set("grpId", "0")
        made.set("animBg", "1")
        builds.append(made)


def checked_animation(spec, where):
    spec = known(spec, ANIMATION_FIELDS, where)
    kind = spec.get("type", "entrance")
    effect = spec.get("effect")
    if (kind, effect) not in EFFECTS:
        choices = "; ".join(f"{t}: " + ", ".join(e for k, e in EFFECTS if k == t) for t in ("entrance", "emphasis", "exit"))
        raise ChangeError(f"{where}: {kind!r} effect {effect!r} is not one of — {choices}.")
    cls, pid, default, directed = EFFECTS[(kind, effect)]
    start = spec.get("start", "click")
    if start not in STARTS:
        raise ChangeError(f"{where} start is one of: {', '.join(STARTS)}.")
    subtype = 0
    if directed:
        direction = spec.get("direction", "bottom")
        if direction not in DIRECTIONS:
            raise ChangeError(f"{where} direction is where it comes from (or goes to, for exits): left, right, top or bottom.")
        subtype = DIRECTIONS[direction]
    elif "direction" in spec:
        raise ChangeError(f"{where} direction applies only to fly-in, fly-out and wipe.")
    elif pid == 53:
        subtype = 16
    duration = seconds(spec.get("duration", default), f"{where} duration", 0, 600) or 1
    repeat = spec.get("repeat", 1)
    if isinstance(repeat, bool) or not isinstance(repeat, (int, float)) or not 1 <= repeat <= 100:
        raise ChangeError(f"{where} repeat is how many times it plays, from 1 to 100.")
    scale = spec.get("scale", 1.5)
    if isinstance(scale, bool) or not isinstance(scale, (int, float)) or not 0.1 <= scale <= 10:
        raise ChangeError(f"{where} scale is how much grow makes the shape bigger, like 1.5.")
    return {"cls": cls, "pid": pid, "subtype": subtype, "start": STARTS[start], "delay": seconds(spec.get("delay", 0), f"{where} delay"),
            "duration": duration, "repeat": round(repeat * 1000), "scale": round(scale * 100000)}


def animate(slide, shape, spec):
    ids = Ids(slide._element)
    spid = shape.shape_id
    main_sequence(slide, ids)
    group = ' grpId="0"'
    repeat = f' repeatCount="{spec["repeat"]}"' if spec["repeat"] != 1000 else ""
    inner = behaviours(ids, spid, spec["cls"], spec["pid"], spec["subtype"], spec["duration"], spec["scale"])
    xml = (f'<p:par {nsdecls("p")}><p:cTn id="{ids()}" presetID="{spec["pid"]}" presetClass="{spec["cls"]}" presetSubtype="{spec["subtype"]}"'
           f' fill="hold"{group} nodeType="{spec["start"]}"{repeat}><p:stCondLst><p:cond delay="{spec["delay"]}"/></p:stCondLst>'
           f'<p:childTnLst>{inner}</p:childTnLst></p:cTn></p:par>')
    place_effect(slide, ids, spec["start"], xml)
    if shape._element.tag == qn("p:sp"):
        build_list(slide, spid)


def clear_animations(slide):
    timing = slide._element.find(qn("p:timing"))
    if timing is None:
        return
    for sequence in timing.xpath("./p:tnLst/p:par/p:cTn/p:childTnLst/p:seq[p:cTn/@nodeType='mainSeq']"):
        sequence.getparent().remove(sequence)
    builds = timing.find(qn("p:bldLst"))
    if builds is not None:
        timing.remove(builds)


# MARK: Media

AUDIO = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4", ".aac": "audio/aac", ".wma": "audio/x-ms-wma"}
VIDEO = {".mp4": "video/mp4", ".m4v": "video/mp4", ".mov": "video/quicktime", ".wmv": "video/x-ms-wmv", ".avi": "video/x-msvideo"}
MEDIA_FIELDS = ("insert", "slide", "path", "poster", "position", "start", "delay", "loop", "acrossSlides", "hidden", "aspectRatio")
MEDIA_STARTS = ("click", "auto", "with-previous", "after-previous", "on-media-click")


def media_length(path):
    """Milliseconds the media plays, when it can be told; 1 otherwise, so what follows is not held up."""
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path)) as sound:
                return max(1, round(sound.getnframes() / sound.getframerate() * 1000))
        except (wave.Error, EOFError, OSError, ZeroDivisionError):
            pass
    # ffmpeg, which the deck's video posters already use, names the length when it reads the file.
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        try:
            result = subprocess.run([ffmpeg, "-nostdin", "-hide_banner", "-i", str(path)], capture_output=True, text=True, timeout=15)
            found = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
            if found:
                hours, minutes, secs = int(found.group(1)), int(found.group(2)), float(found.group(3))
                return max(1, round((hours * 3600 + minutes * 60 + secs) * 1000))
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    return 1


def speaker_icon():
    image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.polygon([(40, 96), (96, 96), (160, 40), (160, 216), (96, 160), (40, 160)], fill="#5D6471")
    for radius in (40, 72):
        draw.arc([160 - radius, 128 - radius, 160 + radius, 128 + radius], -50, 50, fill="#5D6471", width=14)
    data = io.BytesIO()
    image.save(data, format="PNG")
    data.seek(0)
    return data


def add_audio(slide, path, mime, left, top, width, height):
    media = Video.from_path_or_file_like(str(path), mime)
    media_part = slide.part._package.get_or_add_media_part(media)
    media_rid = slide.part.relate_to(media_part, RT.MEDIA)
    audio_rid = slide.part.relate_to(media_part, RT.AUDIO)
    _, icon_rid = slide.part.get_or_add_image_part(speaker_icon())
    tree = slide.shapes._spTree
    spid = slide.shapes._next_shape_id
    picture = parse_xml(
        f'<p:pic {nsdecls("a", "p", "r")}><p:nvPicPr><p:cNvPr id="{spid}" name="{path.stem}"><a:hlinkClick r:id="" action="ppaction://media"/></p:cNvPr>'
        '<p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr>'
        f'<p:nvPr><a:audioFile r:link="{audio_rid}"/><p:extLst><p:ext uri="{{DAA4B4D4-6D71-4841-9C94-3DE7FCFB9230}}">'
        f'<p14:media xmlns:p14="{P14}" r:embed="{media_rid}"/></p:ext></p:extLst></p:nvPr></p:nvPicPr>'
        f'<p:blipFill><a:blip r:embed="{icon_rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
        f'<p:spPr><a:xfrm><a:off x="{left}" y="{top}"/><a:ext cx="{width}" cy="{height}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>')
    tree.append(picture)
    ids = Ids(slide._element)
    root = slide._element.get_or_add_childTnLst()
    root.append(parse_xml(
        f'<p:audio {nsdecls("p")}><p:cMediaNode vol="80000"><p:cTn id="{ids()}" fill="hold" display="0"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst></p:cTn>'
        f'{target(spid)}</p:cMediaNode></p:audio>'))
    return slide.shapes[-1]


def insert_media(deck, slide, spec, where, project_file, poster_for):
    spec = known(spec, MEDIA_FIELDS, where)
    name = spec.get("path")
    if not isinstance(name, str) or not name:
        raise ChangeError(f"{where} path is a sound or video file in the project.")
    path = project_file(name)
    suffix = path.suffix.lower()
    if suffix not in AUDIO and suffix not in VIDEO:
        raise ChangeError(f"{where}: {name} is not a sound ({', '.join(AUDIO)}) or video ({', '.join(VIDEO)}).")
    start = spec.get("start", "on-media-click")
    if start not in MEDIA_STARTS:
        raise ChangeError(f"{where} start is one of: {', '.join(MEDIA_STARTS)}.")
    width, height = deck.slide_width, deck.slide_height
    box = known(spec.get("position", {}), ("left", "top", "width", "height"), f"{where} position")
    if suffix in AUDIO:
        if "poster" in spec:
            raise ChangeError(f"{where} poster is for videos.")
        size = Emu(457200)
        left = length(box["left"], f"{where} left") if "left" in box else width - size - Emu(228600)
        top = length(box["top"], f"{where} top") if "top" in box else height - size - Emu(228600)
        shape = add_audio(slide, path, AUDIO[suffix], left, top,
                          length(box["width"], f"{where} width") if "width" in box else size,
                          length(box["height"], f"{where} height") if "height" in box else size)
        node = next(n for n in slide._element.iter(qn("p:audio")) if n.find(f".//{qn('p:spTgt')}").get("spid") == str(shape.shape_id))
    else:
        if "acrossSlides" in spec:
            raise ChangeError(f"{where} acrossSlides is for sounds.")
        poster, ratio = poster_for(spec, path)
        frame_width = length(box["width"], f"{where} width") if "width" in box else int(width * 0.6)
        frame_height = length(box["height"], f"{where} height") if "height" in box else int(frame_width / ratio)
        left = length(box["left"], f"{where} left") if "left" in box else int((width - frame_width) / 2)
        top = length(box["top"], f"{where} top") if "top" in box else int((height - frame_height) / 2)
        try:
            shape = slide.shapes.add_movie(str(path), left, top, frame_width, frame_height, poster_frame_image=poster, mime_type=VIDEO[suffix])
        except (OSError, ValueError) as error:
            raise ChangeError(f"{where}: {name} or its poster cannot be embedded ({error}).") from error
        node = next(n for n in slide._element.iter(qn("p:video")) if n.find(f".//{qn('p:spTgt')}").get("spid") == str(shape.shape_id))
    media = node.find(qn("p:cMediaNode"))
    if spec.get("loop") is not None and flag(spec["loop"], f"{where} loop"):
        media.find(qn("p:cTn")).set("repeatCount", "indefinite")
    if spec.get("acrossSlides") is not None and flag(spec["acrossSlides"], f"{where} acrossSlides"):
        media.set("numSld", "999")
    if spec.get("hidden") is not None and flag(spec["hidden"], f"{where} hidden"):
        media.set("showWhenStopped", "0")
    if start != "on-media-click":
        ids = Ids(slide._element)
        main_sequence(slide, ids)
        kind = STARTS[start]
        delay = seconds(spec.get("delay", 0), f"{where} delay")
        xml = (f'<p:par {nsdecls("p")}><p:cTn id="{ids()}" presetID="1" presetClass="mediacall" presetSubtype="0" fill="hold" nodeType="{kind}">'
               f'<p:stCondLst><p:cond delay="{delay}"/></p:stCondLst><p:childTnLst><p:cmd type="call" cmd="playFrom(0.0)">'
               f'<p:cBhvr><p:cTn id="{ids()}" dur="{media_length(path)}" fill="hold"/>{target(shape.shape_id)}</p:cBhvr></p:cmd></p:childTnLst></p:cTn></p:par>')
        place_effect(slide, ids, kind, xml)
    elif "delay" in spec:
        raise ChangeError(f"{where} delay needs a start other than on-media-click.")
    return shape


# MARK: Applying the changes

SHAPE_FIELDS = ("slide", "shape", "only", "font", "paragraph", "hyperlink", "on", "animation", "position")


def apply(deck, changes, project_file, poster_for):
    if not isinstance(changes, list) or not changes:
        raise ChangeError('the spec needs "changes", a list of changes like [{"slide": 1, "shape": {"placeholder": "title"}, "font": {"size": 40}}].')
    done = []
    for number, change in enumerate(changes, start=1):
        where = f"change {number}"
        try:
            done.append(apply_one(deck, change, where, project_file, poster_for))
        except ChangeError as error:
            message = str(error)
            raise ChangeError(message if message.startswith(where) else f"{where}: {message}") from error
    return done


def apply_one(deck, change, where, project_file, poster_for):
    if not isinstance(change, dict):
        raise ChangeError(f"{where} is an object; it was {type(change).__name__}.")
    if "move" in change:
        known(change, ("move", "to"), where)
        listed = deck.slides._sldIdLst
        count = len(listed)
        source, = numbers_of(change["move"], f"{where} move", count)
        destination, = numbers_of(change.get("to"), f"{where} to", count)
        element = listed[source - 1]
        listed.remove(element)
        listed.insert(destination - 1, element)
        return {"change": where, "moved": source, "to": destination}
    if "slide" not in change:
        raise ChangeError(f"{where} needs slide, the slide number (or \"all\"), or move.")
    slides = slides_of(deck, change["slide"], where)
    if "insert" in change:
        if change["insert"] != "media":
            raise ChangeError(f"{where} insert is media.")
        for slide in slides:
            insert_media(deck, slide, change, where, project_file, poster_for)
        return {"change": where, "inserted": "media", "slides": len(slides)}
    if "transition" in change:
        known(change, ("slide", "transition"), where)
        for slide in slides:
            set_transition(slide, change["transition"], f"{where} transition")
        return {"change": where, "transitions": len(slides)}
    if "animations" in change:
        known(change, ("slide", "animations"), where)
        if change["animations"] != "clear":
            raise ChangeError(f"{where} animations is \"clear\"; add effects with a shape's animation.")
        for slide in slides:
            clear_animations(slide)
        return {"change": where, "cleared": len(slides)}
    known(change, SHAPE_FIELDS, where)
    if "shape" not in change:
        raise ChangeError(f"{where} needs shape: its number from inspect, its name, or {{\"placeholder\": \"title\"}} or {{\"contains\": \"…\"}}.")
    if not any(key in change for key in ("font", "paragraph", "hyperlink", "animation", "position")):
        raise ChangeError(f"{where} needs font, paragraph, hyperlink, animation or position, what to change.")
    font = checked_font(change["font"], f"{where} font") if "font" in change else None
    paragraph = checked_paragraph(change["paragraph"], f"{where} paragraph") if "paragraph" in change else None
    animations = change.get("animation")
    if animations is not None:
        animations = [checked_animation(a, f"{where} animation") for a in (animations if isinstance(animations, list) else [animations])]
    only = change.get("only")
    if only is not None and (not isinstance(only, str) or not only):
        raise ChangeError(f"{where} only is the text inside the shape to change.")
    on = change.get("on", "auto")
    if on not in ("auto", "text", "shape"):
        raise ChangeError(f"{where} on is text or shape: where a link goes.")
    touched = 0
    for slide in slides:
        shapes = shapes_of(slide, change["shape"], f"{where} shape")
        if only is not None:
            shapes = [s for s in shapes if only in shape_text(s)]
            if not shapes:
                raise ChangeError(f"{where}: no chosen shape on slide {deck.slides.index(slide) + 1} holds {only!r}.")
        for shape in shapes:
            touched += 1
            paragraphs = text_paragraphs(shape._element)
            if font:
                for p in paragraphs:
                    for run in runs_for(p, only):
                        apply_font(rpr_of(run), font)
                    end = p.find(qn("a:endParaRPr"))
                    if only is None and end is not None:
                        apply_font(end, font)
            if paragraph:
                for p in paragraphs:
                    if only is None or only in "".join(run_text(r) for r in text_runs(p)):
                        apply_paragraph(p, paragraph, shape, f"{where} paragraph")
            if "hyperlink" in change:
                use_text = on == "text" or (on == "auto" and (only is not None or shape_text(shape).strip()))
                if use_text:
                    runs = [run for p in paragraphs for run in runs_for(p, only)]
                    if not runs:
                        raise ChangeError(f"{where}: the shape has no text to link; use \"on\": \"shape\".")
                    for run in runs:
                        set_run_link(rpr_of(run), link_element(deck, slide, change["hyperlink"], f"{where} hyperlink"))
                else:
                    set_shape_link(shape, link_element(deck, slide, change["hyperlink"], f"{where} hyperlink"))
            if "position" in change:
                box = known(change["position"], ("left", "top", "width", "height"), f"{where} position")
                for name, value in box.items():
                    setattr(shape, name, length(value, f"{where} position {name}"))
            for animation in animations or []:
                animate(slide, shape, animation)
    return {"change": where, "shapes": touched}


# MARK: Reading back


def cm(emu):
    return f"{round(int(emu) / 360000, 2)}cm" if emu is not None else None


def link_report(deck, slide, link):
    action = link.get("action") or ""
    rid = link.get(qn("r:id"))
    if action == "ppaction://hlinksldjump" and rid:
        part = slide.part.related_part(rid)
        number = next((n for n, s in enumerate(deck.slides, start=1) if s.part is part), None)
        return {"slide": number}
    if action.startswith("ppaction://hlinkshowjump?jump="):
        jump = action.split("=", 1)[1]
        return {"action": next((k for k, v in ACTIONS.items() if v == jump), jump)}
    if action == "ppaction://media":
        return None
    if rid:
        rel = slide.part.rels.get(rid) if hasattr(slide.part.rels, "get") else slide.part.rels[rid]
        if rel is not None and rel.is_external:
            return {"url": rel.target_ref}
    return {"action": action} if action else None


def run_font(rpr):
    if rpr is None:
        return {}
    values = {}
    for slot, name in (("latin", "latin"), ("ea", "eastAsia")):
        element = rpr.find(qn(f"a:{slot}"))
        if element is not None:
            values[name] = element.get("typeface")
    if rpr.get("sz"):
        values["size"] = int(rpr.get("sz")) / 100
    for attribute, name in (("b", "bold"), ("i", "italic")):
        if rpr.get(attribute) is not None:
            values[name] = rpr.get(attribute) in ("1", "true")
    if rpr.get("u") and rpr.get("u") != "none":
        values["underline"] = rpr.get("u")
    colour_element = rpr.find(f"{qn('a:solidFill')}/{qn('a:srgbClr')}")
    if colour_element is not None:
        values["color"] = colour_element.get("val")
    return values


def shape_kind(shape):
    element = shape._element
    if element.find(f".//{qn('a:audioFile')}") is not None:
        return "audio"
    if element.find(f".//{qn('a:videoFile')}") is not None:
        return "video"
    if isinstance(shape, GroupShape):
        return "group"
    if getattr(shape, "has_table", False) and shape.has_table:
        return "table"
    if getattr(shape, "has_chart", False) and shape.has_chart:
        return "chart"
    if element.tag == qn("p:pic"):
        return "picture"
    return "text" if shape_text(shape).strip() else "shape"


def shape_report(deck, slide, shape, number):
    report = {"n": number, "id": shape.shape_id, "name": shape.name, "kind": shape_kind(shape)}
    placeholder = placeholder_type(shape)
    if placeholder:
        report["placeholder"] = next((k for k, v in PLACEHOLDERS.items() if placeholder in v), placeholder)
    for name in ("left", "top", "width", "height"):
        value = getattr(shape, name, None)
        if value is not None:
            report[name] = cm(value)
    text = shape_text(shape)
    if text.strip():
        report["text"] = text if len(text) <= 80 else text[:80] + "…"
    fonts, links = [], []
    for p in text_paragraphs(shape._element):
        for run in text_runs(p):
            rpr = run.find(qn("a:rPr"))
            values = run_font(rpr)
            if values and values not in fonts and len(fonts) < 8:
                fonts.append(values)
            link = rpr.find(qn("a:hlinkClick")) if rpr is not None else None
            if link is not None:
                shown = link_report(deck, slide, link)
                if shown:
                    if links and links[-1].get("_p") is p and {k: v for k, v in links[-1].items() if k not in ("text", "_p")} == shown:
                        links[-1]["text"] += run_text(run)
                    else:
                        links.append({"text": run_text(run), **shown, "_p": p})
    if fonts:
        report["fonts"] = fonts
    if links:
        report["links"] = [{k: v for k, v in link.items() if k != "_p"} for link in links]
    click = shape._element.find(f"./*[1]/{qn('p:cNvPr')}/{qn('a:hlinkClick')}")
    if click is not None:
        shown = link_report(deck, slide, click)
        if shown:
            report["click"] = shown
    return report


def transition_report(sld):
    transition = sld.find(f"{{{MC}}}AlternateContent/{{{MC}}}Choice/{qn('p:transition')}")
    if transition is None:
        transition = sld.find(qn("p:transition"))
    if transition is None:
        return None
    effect = next((child for child in transition if isinstance(child.tag, str)), None)
    report = {"type": effect.tag.split("}")[1] if effect is not None else "none"}
    if effect is not None and effect.get("dir"):
        report["direction"] = next((k for k, v in FROM.items() if v == effect.get("dir") and not k.startswith("from")), effect.get("dir"))
    duration = transition.get(f"{{{P14}}}dur")
    report["duration"] = int(duration) / 1000 if duration else {"fast": 0.5, "med": 0.75, "slow": 1.0}.get(transition.get("spd", "med"))
    report["advanceOnClick"] = transition.get("advClick", "1") != "0"
    if transition.get("advTm"):
        report["advanceAfter"] = int(transition.get("advTm")) / 1000
    return report


def animation_report(slide, names):
    found = []
    for ctn in slide._element.xpath("./p:timing/p:tnLst/p:par/p:cTn/p:childTnLst/p:seq/p:cTn[@nodeType='mainSeq']//p:cTn[@presetClass]"):
        cls, pid = ctn.get("presetClass"), int(ctn.get("presetID", "0"))
        spid = int(next(ctn.iter(qn("p:spTgt"))).get("spid"))
        start = {v: k for k, v in STARTS.items() if k != "auto"}.get(ctn.get("nodeType"), ctn.get("nodeType"))
        effect = "play" if cls == "mediacall" else NAMES.get((cls, pid), f"preset {pid}")
        entry = {"order": len(found) + 1, "shape": names.get(spid, spid), "type": TYPES.get(cls, cls), "effect": effect, "start": start,
                 "delay": delay_of(ctn) / 1000, "duration": effect_length(ctn) / 1000}
        if ctn.get("presetSubtype") and cls != "mediacall" and pid in (2, 22):
            entry["direction"] = next((k for k, v in DIRECTIONS.items() if v == int(ctn.get("presetSubtype")) and not k.startswith("from")), None)
        found.append(entry)
    return found


def media_report(slide, names):
    found = []
    for kind in ("audio", "video"):
        for node in slide._element.iter(qn(f"p:{kind}")):
            media = node.find(qn("p:cMediaNode"))
            spid = int(media.find(f".//{qn('p:spTgt')}").get("spid"))
            entry = {"shape": names.get(spid, spid), "kind": kind}
            if media.find(qn("p:cTn")).get("repeatCount") == "indefinite":
                entry["loop"] = True
            if media.get("numSld"):
                entry["acrossSlides"] = True
            if media.get("showWhenStopped") == "0":
                entry["hidden"] = True
            found.append(entry)
    return found


def inspect(deck, only_slide=None):
    slides = []
    for number, slide in enumerate(deck.slides, start=1):
        if only_slide is not None and number != only_slide:
            continue
        shapes = list(slide.shapes)
        names = {s.shape_id: f"{n} {s.name}" for n, s in enumerate(shapes, start=1)}
        entry = {"slide": number, "layout": slide.slide_layout.name,
                 "shapes": [shape_report(deck, slide, shape, n) for n, shape in enumerate(shapes, start=1)]}
        transition = transition_report(slide._element)
        if transition:
            entry["transition"] = transition
        animations = animation_report(slide, names)
        if animations:
            entry["animations"] = animations
        media = media_report(slide, names)
        if media:
            entry["media"] = media
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame.text:
            entry["notes"] = slide.notes_slide.notes_text_frame.text[:200]
        slides.append(entry)
    return {"slideSize": {"width": cm(deck.slide_width), "height": cm(deck.slide_height)}, "slides": slides}

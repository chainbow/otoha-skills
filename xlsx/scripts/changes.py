"""Changes an existing Excel workbook from a list of changes, keeping what it already holds, and reads its
formatting back.

Used by workbook.py's `change` and `inspect` commands; see the skill's SKILL.md for the changes.
"""

import copy
import datetime
import importlib.util
import re
import zipfile

from openpyxl.chart import AreaChart, BarChart, LineChart, PieChart, Reference, ScatterChart, Series
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule, DataBarRule, FormulaRule, Rule
from openpyxl.formula.translate import Translator
from openpyxl.styles import Border, Font, PatternFill, Protection, Side
from openpyxl.styles.differential import DifferentialStyle
from openpyxl.utils import get_column_letter
from openpyxl.utils.cell import column_index_from_string, coordinate_from_string, range_boundaries
from openpyxl.worksheet.protection import SheetProtection


class ChangeError(Exception):
    """A change cannot be made; the message says what to change."""


NAMED_SIZES = {
    "初号": 42, "小初": 36, "一号": 26, "小一": 24, "二号": 22, "小二": 18, "三号": 16, "小三": 15,
    "四号": 14, "小四": 12, "五号": 10.5, "小五": 9, "六号": 7.5, "小六": 6.5, "七号": 5.5, "八号": 5,
}
FORMATS = {"text": "@", "number": "#,##0.00", "integer": "#,##0", "percent": "0.0%", "currency": "¥#,##0.00", "date": "yyyy-mm-dd"}
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?)?")

# What openpyxl does not carry over when it saves, found by the parts of the file that hold it.
LOSSES = (
    ("macros (VBA)", lambda names, sheets: any(n.endswith("vbaProject.bin") for n in names)),
    ("slicers and timelines", lambda names, sheets: any(n.startswith(("xl/slicers/", "xl/timelines/", "xl/slicerCaches/")) for n in names)),
    ("form controls and ActiveX controls", lambda names, sheets: any(n.startswith(("xl/ctrlProps/", "xl/activeX/")) for n in names)),
    ("threaded comments (replies)", lambda names, sheets: any(n.startswith("xl/threadedComments/") for n in names)),
    ("sparklines", lambda names, sheets: "sparklineGroup" in sheets),
    ("newer conditional formats and validations (Excel 2010 extensions)", lambda names, sheets: "x14:conditionalFormatting" in sheets or "x14:dataValidation" in sheets),
    ("pictures (the image library is not available)", lambda names, sheets: any(n.startswith("xl/media/") for n in names) and importlib.util.find_spec("PIL") is None),
)


def losses(path):
    """What saving this file with openpyxl would drop."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        sheets = "".join(archive.read(n).decode("utf-8", "replace") for n in names if n.startswith("xl/worksheets/") and n.endswith(".xml"))
    return [label for label, found in LOSSES if found(names, sheets)]


# MARK: Values


def known(spec, allowed, where):
    if not isinstance(spec, dict):
        raise ChangeError(f"{where} is an object with named fields; it was {type(spec).__name__}.")
    unknown = [key for key in spec if key not in allowed]
    if unknown:
        raise ChangeError(f"{where} has {', '.join(map(repr, unknown))}, which is not one of: {', '.join(allowed)}.")
    return spec


def colour(value, where):
    if not isinstance(value, str) or not re.fullmatch(r"#?[0-9A-Fa-f]{6}", value.strip()):
        raise ChangeError(f"{where} is a colour of six hexadecimal digits, like \"#4472C4\"; it was {value!r}.")
    return "FF" + value.strip().lstrip("#").upper()


def flag(value, where):
    if not isinstance(value, bool):
        raise ChangeError(f"{where} is true or false; it was {value!r}.")
    return value


def font_size(value, where):
    if isinstance(value, str) and value.strip() in NAMED_SIZES:
        return NAMED_SIZES[value.strip()]
    points = value
    if isinstance(value, str):
        found = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(pt|磅)?\s*", value)
        points = float(found.group(1)) if found else None
    if isinstance(points, bool) or not isinstance(points, (int, float)) or not 1 <= points <= 409:
        raise ChangeError(f"{where} size is points (11, \"12pt\") or a named size ({'、'.join(NAMED_SIZES)}); it was {value!r}.")
    return points


def cell_range(sheet, value, where):
    """(min_col, min_row, max_col, max_row) of "A1", "B2:D9", "B:D" or "2:5"."""
    if not isinstance(value, str) or not value.strip():
        raise ChangeError(f"{where} is a range like \"A1:D9\".")
    try:
        bounds = range_boundaries(value.strip().replace("$", ""))
    except (ValueError, TypeError) as error:
        raise ChangeError(f"{where} {value!r} is not a range like \"A1:D9\".") from error
    min_col, min_row, max_col, max_row = bounds
    if None in (min_col, min_row, max_col, max_row):
        min_col, max_col = min_col or 1, max_col or sheet.max_column
        min_row, max_row = min_row or 1, max_row or sheet.max_row
    return min_col, min_row, max_col, max_row


def cells_in(sheet, value, where):
    min_col, min_row, max_col, max_row = cell_range(sheet, value, where)
    if (max_col - min_col + 1) * (max_row - min_row + 1) > 1_000_000:
        raise ChangeError(f"{where} {value!r} is more than a million cells; name the used part.")
    for row in sheet.iter_rows(min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col):
        yield from row


def put_value(cell, value, where):
    """Text stays text even when it starts with "="; only {"formula": "…"} is a formula."""
    if isinstance(value, dict):
        formula = value.get("formula")
        if set(value) != {"formula"} or not isinstance(formula, str) or not formula.strip():
            raise ChangeError(f'{where}: a cell is text, a number, true or false, null, a date "2026-10-28", or {{"formula": "=SUM(B2:B4)"}}.')
        cell.value = formula if formula.startswith("=") else f"={formula}"
        return
    if isinstance(value, list):
        raise ChangeError(f"{where}: a cell holds one value; it was a list.")
    if isinstance(value, str) and ISO_DATE.fullmatch(value.strip()) and cell.is_date:
        cell.value = datetime.datetime.fromisoformat(value.strip())
        return
    cell.value = value
    if isinstance(value, str):
        cell.data_type = "s"


# MARK: Styles

FONT_FIELDS = ("name", "size", "bold", "italic", "underline", "strike", "color")
ALIGN_FIELDS = ("horizontal", "vertical", "wrap", "indent", "rotation", "shrink")
HORIZONTAL = ("general", "left", "center", "right", "fill", "justify", "centerContinuous", "distributed")
VERTICAL = ("top", "center", "bottom", "justify", "distributed")
BORDER_STYLES = ("thin", "medium", "thick", "dashed", "dotted", "double", "hair", "mediumDashed", "dashDot", "none")


def font_changes(spec, where):
    spec = known(spec, FONT_FIELDS, where)
    found = {}
    if "name" in spec:
        if not isinstance(spec["name"], str) or not spec["name"].strip():
            raise ChangeError(f"{where} name is a font's name, like \"宋体\" or \"Calibri\".")
        found["name"] = spec["name"]
    if "size" in spec:
        found["size"] = font_size(spec["size"], where)
    for name, attribute in (("bold", "bold"), ("italic", "italic"), ("strike", "strike")):
        if name in spec:
            found[attribute] = flag(spec[name], f"{where} {name}")
    if "underline" in spec:
        value = spec["underline"]
        value = ("single" if value else None) if isinstance(value, bool) else value
        if value not in (None, "single", "double", "singleAccounting", "doubleAccounting"):
            raise ChangeError(f"{where} underline is true, false, single or double.")
        found["underline"] = value
    if "color" in spec:
        found["color"] = colour(spec["color"], f"{where} color")
    return found


def with_font(old, changes):
    font = copy.copy(old)
    for name, value in changes.items():
        setattr(font, name, value)
    return font


def alignment_changes(spec, where):
    spec = known(spec, ALIGN_FIELDS, where)
    found = {}
    if "horizontal" in spec:
        if spec["horizontal"] not in HORIZONTAL:
            raise ChangeError(f"{where} horizontal is one of: {', '.join(HORIZONTAL)}.")
        found["horizontal"] = spec["horizontal"]
    if "vertical" in spec:
        if spec["vertical"] not in VERTICAL:
            raise ChangeError(f"{where} vertical is one of: {', '.join(VERTICAL)}.")
        found["vertical"] = spec["vertical"]
    if "wrap" in spec:
        found["wrap_text"] = flag(spec["wrap"], f"{where} wrap")
    if "shrink" in spec:
        found["shrink_to_fit"] = flag(spec["shrink"], f"{where} shrink")
    for name, attribute, top in (("indent", "indent", 250), ("rotation", "text_rotation", 180)):
        if name in spec:
            if isinstance(spec[name], bool) or not isinstance(spec[name], int) or not 0 <= spec[name] <= top:
                raise ChangeError(f"{where} {name} is a whole number from 0 to {top}.")
            found[attribute] = spec[name]
    return found


def border_plan(spec, where):
    """(style, colour, edges) from "thin" or {"style": "thin", "color": "000000", "edges": "all" | "outline" | [...]}."""
    if isinstance(spec, str):
        spec = {"style": spec}
    spec = known(spec, ("style", "color", "edges"), where)
    style = spec.get("style", "thin")
    if style not in BORDER_STYLES:
        raise ChangeError(f"{where} style is one of: {', '.join(BORDER_STYLES)}.")
    edges = spec.get("edges", "all")
    allowed = ("left", "right", "top", "bottom")
    if edges not in ("all", "outline", "inside") and not (isinstance(edges, list) and all(e in allowed for e in edges)):
        raise ChangeError(f"{where} edges is all, outline, inside, or a list of {', '.join(allowed)}.")
    return None if style == "none" else style, colour(spec.get("color", "000000"), f"{where} color"), edges


def apply_borders(sheet, value, plan):
    style, color, edges = plan
    min_col, min_row, max_col, max_row = value
    side = Side(style=style, color=color if style else None)
    for row in sheet.iter_rows(min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col):
        for cell in row:
            sides = {}
            for edge, outer in (("left", cell.column == min_col), ("right", cell.column == max_col), ("top", cell.row == min_row), ("bottom", cell.row == max_row)):
                wanted = (edges == "all" or (edges == "outline" and outer) or (edges == "inside" and not outer) or (isinstance(edges, list) and edge in edges and outer))
                if wanted:
                    sides[edge] = side
            if sides:
                old = cell.border
                cell.border = Border(left=sides.get("left", old.left), right=sides.get("right", old.right), top=sides.get("top", old.top),
                                     bottom=sides.get("bottom", old.bottom), diagonal=old.diagonal, diagonal_direction=old.diagonal_direction)


def number_format(value, where):
    if not isinstance(value, str) or not value.strip():
        raise ChangeError(f"{where} numberFormat is an Excel number format such as \"0.00%\", or one of: {', '.join(FORMATS)}.")
    return FORMATS.get(value, value)


# MARK: Conditional formats

OPERATORS = ("greaterThan", "lessThan", "between", "notBetween", "equal", "notEqual", "greaterThanOrEqual", "lessThanOrEqual")
RULES = OPERATORS + ("formula", "colorScale", "dataBar", "top", "bottom", "duplicate", "unique", "containsText")


def style_of(spec, where):
    font = Font(**font_changes(spec["font"], f"{where} font")) if "font" in spec else None
    fill = None
    if "fill" in spec:
        rgb = colour(spec["fill"], f"{where} fill")
        fill = PatternFill(start_color=rgb, end_color=rgb, fill_type="solid")
    return font, fill


def formula_value(value):
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    return text[1:] if text.startswith("=") else f'"{text}"' if not re.fullmatch(r"\$?[A-Z]{1,3}\$?\d+", text) else text


def conditional_rule(spec, where):
    rule = spec.get("rule")
    if rule not in RULES:
        raise ChangeError(f"{where} rule {rule!r} is not one of: {', '.join(RULES)}.")
    font, fill = style_of(spec, where)
    if rule in OPERATORS:
        values = spec.get("values", [spec["value"]] if "value" in spec else None)
        needed = 2 if rule in ("between", "notBetween") else 1
        if not isinstance(values, list) or len(values) != needed:
            raise ChangeError(f"{where}: {rule} needs {'values, two of them' if needed == 2 else 'value'}.")
        return CellIsRule(operator=rule, formula=[formula_value(v) for v in values], font=font, fill=fill)
    if rule == "formula":
        formula = spec.get("formula")
        if not isinstance(formula, str) or not formula.strip():
            raise ChangeError(f"{where} formula is the test for the range's first cell, like \"$B2>30\".")
        return FormulaRule(formula=[formula.lstrip("=")], font=font, fill=fill)
    if rule == "colorScale":
        colours = spec.get("colors", ["#F8696B", "#FFEB84", "#63BE7B"])
        if not isinstance(colours, list) or len(colours) not in (2, 3):
            raise ChangeError(f"{where} colors lists two or three colours, lowest first.")
        colours = [colour(c, f"{where} colors") for c in colours]
        if len(colours) == 2:
            return ColorScaleRule(start_type="min", start_color=colours[0], end_type="max", end_color=colours[1])
        return ColorScaleRule(start_type="min", start_color=colours[0], mid_type="percentile", mid_value=50, mid_color=colours[1], end_type="max", end_color=colours[2])
    if rule == "dataBar":
        return DataBarRule(start_type="min", end_type="max", color=colour(spec.get("color", "#638EC6"), f"{where} color"))
    style = DifferentialStyle(font=font, fill=fill)
    if rule in ("top", "bottom"):
        rank = spec.get("rank", 10)
        if isinstance(rank, bool) or not isinstance(rank, int) or not 1 <= rank <= 1000:
            raise ChangeError(f"{where} rank is a whole number from 1 to 1000.")
        return Rule(type="top10", rank=rank, percent=bool(spec.get("percent", False)), bottom=rule == "bottom", dxf=style)
    if rule in ("duplicate", "unique"):
        return Rule(type="duplicateValues" if rule == "duplicate" else "uniqueValues", dxf=style)
    text = spec.get("text")
    if not isinstance(text, str) or not text:
        raise ChangeError(f"{where} text is what the cells contain.")
    first = spec["range"].split(":")[0].replace("$", "")
    escaped = text.replace('"', '""')
    return Rule(type="containsText", operator="containsText", text=text, formula=[f'NOT(ISERROR(SEARCH("{escaped}",{first})))'], dxf=style)


# MARK: Charts

CHARTS = {"column": BarChart, "bar": BarChart, "line": LineChart, "pie": PieChart, "area": AreaChart, "scatter": ScatterChart}
CHART_FIELDS = ("type", "data", "categories", "title", "at", "width", "height", "xTitle", "yTitle", "titlesFromData", "stacked", "legend")


def add_chart(sheet, spec, where):
    spec = known(spec, CHART_FIELDS, where)
    kind = spec.get("type", "column")
    if kind not in CHARTS:
        raise ChangeError(f"{where} type {kind!r} is not one of: {', '.join(CHARTS)}.")
    chart = CHARTS[kind]()
    if kind in ("column", "bar"):
        chart.type = "col" if kind == "column" else "bar"
        if spec.get("stacked"):
            chart.grouping, chart.overlap = "stacked", 100
    min_col, min_row, max_col, max_row = cell_range(sheet, spec.get("data"), f"{where} data")
    titles = spec.get("titlesFromData", True)
    if kind == "scatter":
        if "categories" not in spec:
            raise ChangeError(f"{where}: a scatter chart needs categories, the range of x values.")
        x_col, x_min, _, x_max = cell_range(sheet, spec["categories"], f"{where} categories")
        xs = Reference(sheet, min_col=x_col, min_row=x_min, max_row=x_max)
        for column in range(min_col, max_col + 1):
            values = Reference(sheet, min_col=column, min_row=min_row, max_row=max_row)
            chart.series.append(Series(values, xs, title_from_data=titles))
    else:
        chart.add_data(Reference(sheet, min_col=min_col, min_row=min_row, max_col=max_col, max_row=max_row), titles_from_data=titles)
        if "categories" in spec:
            c_col, c_min, c_max_col, c_max = cell_range(sheet, spec["categories"], f"{where} categories")
            chart.set_categories(Reference(sheet, min_col=c_col, min_row=c_min, max_col=c_max_col, max_row=c_max))
    if spec.get("title"):
        chart.title = str(spec["title"])
    if kind != "pie":
        if spec.get("xTitle"):
            chart.x_axis.title = str(spec["xTitle"])
        if spec.get("yTitle"):
            chart.y_axis.title = str(spec["yTitle"])
    if spec.get("legend") is False:
        chart.legend = None
    for name, default in (("width", 16), ("height", 9)):
        value = spec.get(name, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 2 <= value <= 60:
            raise ChangeError(f"{where} {name} is centimetres from 2 to 60.")
        setattr(chart, name, value)
    anchor = spec.get("at", f"{get_column_letter(sheet.max_column + 2)}2")
    try:
        coordinate_from_string(anchor)
    except (ValueError, TypeError) as error:
        raise ChangeError(f"{where} at is the cell for the chart's top-left corner, like \"F2\".") from error
    sheet.add_chart(chart, anchor)


# MARK: Applying the changes

RANGE_OPS = ("numberFormat", "font", "fill", "align", "border", "formula", "locked", "hidden")
SHEET_OPS = ("cells", "columnWidths", "rowHeights", "freeze", "conditionalFormat", "chart", "protect", "merge", "unmerge", "autoFilter")
PROTECTIONS = ("selectLockedCells", "selectUnlockedCells", "formatCells", "formatColumns", "formatRows", "insertColumns", "insertRows",
               "insertHyperlinks", "deleteColumns", "deleteRows", "sort", "autoFilter", "pivotTables", "objects", "scenarios")


def columns_of(key, where):
    key = str(key).strip().upper()
    found = re.fullmatch(r"([A-Z]{1,3})(?::([A-Z]{1,3}))?", key)
    if not found:
        raise ChangeError(f"{where} names columns like \"A\" or \"B:D\"; it was {key!r}.")
    first = column_index_from_string(found.group(1))
    last = column_index_from_string(found.group(2) or found.group(1))
    return [get_column_letter(n) for n in range(min(first, last), max(first, last) + 1)]


def rows_of(key, where):
    found = re.fullmatch(r"\s*(\d+)\s*(?:[-:]\s*(\d+))?\s*", str(key))
    if not found:
        raise ChangeError(f"{where} names rows like \"1\" or \"2-5\"; it was {key!r}.")
    first, last = int(found.group(1)), int(found.group(2) or found.group(1))
    return range(min(first, last), max(first, last) + 1)


def display_width(value):
    text = "" if value is None else str(value)
    return sum(2 if ord(char) > 0x2E80 else 1 for char in text)


def apply(book, changes):
    if not isinstance(changes, list) or not changes:
        raise ChangeError('the spec needs "changes", a list of changes like [{"sheet": "Sheet1", "range": "A1:D1", "font": {"bold": true}}].')
    done = []
    for number, change in enumerate(changes, start=1):
        where = f"change {number}"
        try:
            done.append(apply_one(book, change, where))
        except ChangeError as error:
            message = str(error)
            raise ChangeError(message if message.startswith(where) else f"{where}: {message}") from error
    book.calculation.fullCalcOnLoad = True  # Excel works out the formulas again when the file opens.
    return done


def apply_one(book, change, where):
    change = known(change, ("sheet", "range", *RANGE_OPS, *SHEET_OPS), where)
    name = change.get("sheet")
    if name not in book.sheetnames:
        raise ChangeError(f"{where}: there is no sheet {name!r}; the sheets are {', '.join(book.sheetnames)}.")
    sheet = book[name]
    ranged = [op for op in RANGE_OPS if op in change]
    if ranged and "range" not in change:
        raise ChangeError(f"{where}: {', '.join(ranged)} needs range, the cells to change, like \"A1:D1\".")
    if not ranged and not any(op in change for op in SHEET_OPS):
        raise ChangeError(f"{where} names nothing to change.")
    if ranged:
        bounds = cell_range(sheet, change["range"], f"{where} range")
        fmt = number_format(change["numberFormat"], where) if "numberFormat" in change else None
        font = font_changes(change["font"], f"{where} font") if "font" in change else None
        fill = PatternFill("solid", fgColor=colour(change["fill"], f"{where} fill")) if change.get("fill") not in (None, "none") else None
        alignment = alignment_changes(change["align"], f"{where} align") if "align" in change else None
        formula = change.get("formula")
        if formula is not None and (not isinstance(formula, str) or not formula.startswith("=")):
            raise ChangeError(f"{where} formula is the first cell's formula, like \"=B2*C2\"; the rest of the range follows it as Excel's fill does.")
        origin = f"{get_column_letter(bounds[0])}{bounds[1]}"
        for cell in cells_in(sheet, change["range"], f"{where} range"):
            if fmt is not None:
                cell.number_format = fmt
            if font:
                cell.font = with_font(cell.font, font)
            if fill is not None:
                cell.fill = fill
            elif change.get("fill") == "none":
                cell.fill = PatternFill(fill_type=None)
            if alignment:
                old = copy.copy(cell.alignment)
                for key, value in alignment.items():
                    setattr(old, key, value)
                cell.alignment = old
            if formula is not None:
                cell.value = Translator(formula, origin=origin).translate_formula(cell.coordinate)
            if "locked" in change or "hidden" in change:
                cell.protection = Protection(locked=flag(change.get("locked", cell.protection.locked), f"{where} locked"),
                                             hidden=flag(change.get("hidden", cell.protection.hidden), f"{where} hidden"))
        if "border" in change:
            apply_borders(sheet, bounds, border_plan(change["border"], f"{where} border"))
    if "cells" in change:
        values = change["cells"]
        if not isinstance(values, dict) or not values:
            raise ChangeError(f'{where} cells is an object like {{"E1": "税额", "E6": {{"formula": "=SUM(E2:E5)"}}}}.')
        for coordinate, value in values.items():
            try:
                coordinate_from_string(coordinate)
            except (ValueError, TypeError) as error:
                raise ChangeError(f"{where} cells: {coordinate!r} is not a cell like \"E1\".") from error
            put_value(sheet[coordinate], value, f"{where} cell {coordinate}")
    if "columnWidths" in change:
        widths = change["columnWidths"]
        if not isinstance(widths, dict):
            raise ChangeError(f'{where} columnWidths is an object like {{"A": 14, "B:D": 12}} (characters), or "auto" for a width.')
        for key, value in widths.items():
            for letter in columns_of(key, f"{where} columnWidths"):
                if value == "auto":
                    longest = max((display_width(c.value) for c in sheet[letter]), default=8)
                    value_used = min(80, max(6, longest * 1.1 + 2))
                elif isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 255:
                    raise ChangeError(f"{where} columnWidths {key} is a width in characters from 0 to 255, or \"auto\".")
                else:
                    value_used = value
                sheet.column_dimensions[letter].width = value_used
    if "rowHeights" in change:
        heights = change["rowHeights"]
        if not isinstance(heights, dict):
            raise ChangeError(f'{where} rowHeights is an object like {{"1": 24, "2-10": 18}} (points).')
        for key, value in heights.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 409:
                raise ChangeError(f"{where} rowHeights {key} is a height in points from 0 to 409.")
            for row in rows_of(key, f"{where} rowHeights"):
                sheet.row_dimensions[row].height = value
    if "freeze" in change:
        value = change["freeze"]
        if value in (None, False):
            sheet.freeze_panes = None
        else:
            try:
                coordinate_from_string(value)
            except (ValueError, TypeError) as error:
                raise ChangeError(f"{where} freeze is the first cell that scrolls, like \"B2\" (row 1 and column A stay), or null.") from error
            sheet.freeze_panes = value
    if "conditionalFormat" in change:
        rules = change["conditionalFormat"] if isinstance(change["conditionalFormat"], list) else [change["conditionalFormat"]]
        for number, spec in enumerate(rules, start=1):
            label = f"{where} conditionalFormat {number}"
            spec = known(spec, ("range", "rule", "value", "values", "formula", "fill", "font", "colors", "color", "rank", "percent", "text"), label)
            cell_range(sheet, spec.get("range"), f"{label} range")
            sheet.conditional_formatting.add(spec["range"], conditional_rule(spec, label))
    if "chart" in change:
        add_chart(sheet, change["chart"], f"{where} chart")
    if "protect" in change:
        value = change["protect"]
        if value is False:
            sheet.protection = SheetProtection()
        else:
            value = known(value if isinstance(value, dict) else {}, ("password", "allow"), f"{where} protect")
            allow = value.get("allow", [])
            if not isinstance(allow, list) or any(a not in PROTECTIONS for a in allow):
                raise ChangeError(f"{where} protect allow lists what people may still do: {', '.join(PROTECTIONS)}.")
            sheet.protection.sheet = True
            if value.get("password"):
                sheet.protection.password = str(value["password"])
            for name in PROTECTIONS:
                if name in allow:
                    setattr(sheet.protection, name, False)
    for op, method in (("unmerge", sheet.unmerge_cells), ("merge", sheet.merge_cells)):
        if op in change:
            for value in change[op] if isinstance(change[op], list) else [change[op]]:
                cell_range(sheet, value, f"{where} {op}")
                try:
                    method(value)
                except (ValueError, KeyError) as error:
                    raise ChangeError(f"{where} {op} {value!r} cannot be done ({error}).") from error
    if "autoFilter" in change:
        value = change["autoFilter"]
        if value in (None, False):
            sheet.auto_filter.ref = None
        else:
            cell_range(sheet, value, f"{where} autoFilter")
            sheet.auto_filter.ref = value
    return {"change": where, "sheet": name}


# MARK: Reading back


def rgb(value):
    if value is None or not isinstance(getattr(value, "rgb", None), str):
        return None
    return value.rgb[-6:]


def cell_report(cell):
    report = {"cell": cell.coordinate, "value": cell.value if isinstance(cell.value, (int, float, str, bool)) or cell.value is None else str(cell.value)}
    if isinstance(report["value"], str) and len(report["value"]) > 200:
        report["value"] = report["value"][:200] + "…"
    if cell.number_format != "General":
        report["numberFormat"] = cell.number_format
    font = cell.font
    shown = {k: v for k, v in (("name", font.name), ("size", font.size), ("bold", font.bold or None), ("italic", font.italic or None),
                               ("underline", font.underline), ("color", rgb(font.color))) if v is not None}
    if shown and shown != {"name": "Calibri", "size": 11.0}:
        report["font"] = shown
    if cell.fill is not None and cell.fill.fill_type == "solid":
        report["fill"] = rgb(cell.fill.fgColor)
    align = cell.alignment
    shown = {k: v for k, v in (("horizontal", align.horizontal), ("vertical", align.vertical), ("wrap", align.wrap_text or None)) if v}
    if shown:
        report["align"] = shown
    borders = {
        edge: side.style
        for edge in ("left", "right", "top", "bottom")
        if (side := getattr(cell.border, edge)) is not None and side.style
    }
    if borders:
        report["border"] = borders
    if cell.protection.locked is False:
        report["locked"] = False
    return report


def chart_report(chart):
    kind = ("column" if chart.type == "col" else "bar") if chart.tagname == "barChart" else chart.tagname.replace("Chart", "")
    title = None
    if chart.title is not None and chart.title.tx is not None and chart.title.tx.rich is not None:
        title = "".join(run.t for p in chart.title.tx.rich.p for run in (p.r or []))
    marker = getattr(chart.anchor, "_from", None)
    return {"type": kind, "title": title, "at": f"{get_column_letter(marker.col + 1)}{marker.row + 1}" if marker is not None else None,
            "series": [s.val.numRef.f for s in chart.series if s.val is not None and s.val.numRef is not None]}


def inspect(book, path, only_sheet=None, area=None, limit_rows=40):
    sheets = []
    for sheet in book.worksheets:
        if only_sheet is not None and sheet.title != only_sheet:
            continue
        entry = {"name": sheet.title, "used": sheet.dimensions, "freeze": sheet.freeze_panes}
        widths = {letter: dim.width for letter, dim in sheet.column_dimensions.items() if dim.customWidth and dim.width}
        if widths:
            entry["columnWidths"] = widths
        heights = {str(row): dim.height for row, dim in sheet.row_dimensions.items() if dim.height}
        if heights:
            entry["rowHeights"] = dict(list(heights.items())[:60])
        if sheet.merged_cells.ranges:
            entry["merged"] = [str(r) for r in sheet.merged_cells.ranges][:100]
        if sheet.auto_filter.ref:
            entry["autoFilter"] = sheet.auto_filter.ref
        if sheet.protection.sheet:
            entry["protection"] = {"protected": True, "password": bool(sheet.protection.password),
                                   "allowed": [name for name in PROTECTIONS if getattr(sheet.protection, name) is False]}
        formats = []
        for group in sheet.conditional_formatting:
            for rule in group.rules:
                shown = {"range": str(group.sqref), "type": rule.type}
                if rule.operator:
                    shown["operator"] = rule.operator
                if rule.formula:
                    shown["formula"] = list(rule.formula)
                if rule.dxf is not None and rule.dxf.fill is not None:
                    shown["fill"] = rgb(rule.dxf.fill.fgColor) or rgb(rule.dxf.fill.bgColor)
                formats.append(shown)
        if formats:
            entry["conditionalFormats"] = formats
        if sheet._charts:
            entry["charts"] = [chart_report(chart) for chart in sheet._charts]
        if sheet.data_validations.dataValidation:
            entry["validations"] = [{"range": str(v.sqref), "type": v.type, "formula1": v.formula1} for v in sheet.data_validations.dataValidation][:40]
        if area is not None:
            min_col, min_row, max_col, max_row = cell_range(sheet, area, "--range")
        else:
            min_col, min_row, max_col, max_row = 1, 1, min(sheet.max_column, 26), min(sheet.max_row, limit_rows)
        entry["cells"] = [cell_report(cell) for row in sheet.iter_rows(min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col)
                          for cell in row if cell.value is not None or cell.has_style]
        sheets.append(entry)
    return {"sheets": sheets, "names": list(book.defined_names), "wouldBeLostOnSave": losses(path)}

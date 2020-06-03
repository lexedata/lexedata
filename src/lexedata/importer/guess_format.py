import os
import re
import sys
import tty
import shutil
import termios
import argparse
import readline
import typing as t
import unicodedata
from pathlib import Path

import openpyxl

if os.name == 'nt':
    def clear():
        os.system('cls')
else:
    def clear():
        os.system('clear')

def select_sheet(wb: openpyxl.Workbook) -> openpyxl.worksheet.worksheet.Worksheet:
    sheets = wb.sheetnames
    if len(sheets) == 1:
        return wb.active
    for i, name in enumerate(sheets, 1):
        print(f"{i: 3d}) {name:}")
    sheet = input("Pick a sheet to work with (default: 0) >")

    for i, name in enumerate(sheets, 1):
        if str(i) == sheet.strip() or name.strip().startswith(sheet.strip()):
            return wb[name]
    else:
        print("That was incomprehensible. Press Ctrl+C to exit.")
        return select_sheet(wb)


def to_width(s: str, target_width: int):
    """Pad or trim a string to target width

    Width is in terms of monospaced spacing glyphs, not in terms of characters,
    to be used in tabular console views.

    >>> to_width("t", 3)
    't  '
    >>> to_width("test", 3)
    'te…'
    >>> to_width("txt", 3)
    'txt'
    >>> to_width("dolﬁns", 5)
    'dolf…'
    >>> to_width("error", 0)
    Traceback (most recent call last):
    ...
    ValueError: Target width must be positive

    """
    if target_width < 1:
        raise ValueError("Target width must be positive")
    s = unicodedata.normalize('NFKD', s)
    if width(s) <= target_width:
        return s + ' ' * (target_width - width(s))
    while width(s) > target_width - 1:
        s = s[:-1]
    if width(s) < target_width - 1:
        return s + '…' + ' ' * (target_width - width(s) - 1)
    else:
        return s + '…'


def width(value: t.Optional[str]) -> int:
    """Compute the decomposed width of a string

    Width is in terms of monospaced spacing glyphs, not in terms of characters,
    to be used in tabular console views. This function applies the NFKD first,
    so ligatures will be unpacked.

    >>> width("t")
    1
    >>> width("ê")
    1
    >>> width("ﬁ")
    2
    >>> width("eǩe")
    3
    >>> width("全角")
    4
    """
    s: str = unicodedata.normalize('NFKD', value or '')
    # There might be CJK characters of double width, or things like that?
    # That's why we use the sum construction, which can be extended to such
    # cases.
    return sum((unicodedata.category(c) not in {'Mn', 'Cf', 'Cc'}) +
               (unicodedata.east_asian_width(c) in {'W', 'F'})
               for c in s)


WHITESPACE = r"\s*"


def to_regex(pattern: str) -> re.Pattern:
    r"""
    >>> l = to_regex("Language")
    >>> l.fullmatch("Maweti-Guarani ").groupdict()
    {'language': 'Maweti-Guarani'}

    >>> n = to_regex("Name (Abbreviation): Curator")
    >>> n.fullmatch("German (deu): MBO").groupdict()
    {'name': 'German', 'abbreviation': 'deu', 'curator': 'MBO'}
    >>> n.fullmatch("German  (deu):MBO	").groupdict()
    {'name': 'German', 'abbreviation': 'deu', 'curator': 'MBO'}
    """
    elements = re.compile(r"(\w+)").split(pattern)
    for i in range(0, len(elements), 2):
        elements[i] = WHITESPACE.join(
            re.escape(s)
            for s in [''] + elements[i].split() + [''])
        if elements[i] == WHITESPACE * 2:
            elements[i] = WHITESPACE
    for i in range(1, len(elements), 2):
        this = elements[i].lower()
        elements[i] = f"(?P<{this:}>.*?)"
    return re.compile(''.join(elements), re.IGNORECASE)


def pretty(ws: openpyxl.worksheet.worksheet.Worksheet,
           col_widths: t.List[int],
           top: int, left: int,
           tty_rows: int = 20) -> None:
    for r, row in enumerate(
            ws.iter_rows(max_row=min(tty_rows - 2, ws.max_row),
                         max_col=len(col_widths))):
        c1, c2 = col_widths[:left - 1], col_widths[left - 1:]
        if r + 1 == top:
            print('┿'.join(['━' * c for c in c1]),
                  '┿'.join(['━' * c for c in c2]),
                  sep='╋')
        print('│'.join(to_width(c.value or '', l) for c, l in zip(row, c1)),
              '│'.join(to_width(c.value or '', l) for c, l in zip(row[left - 1:], c2)),
              sep='┃')


CELL = re.compile(
    r"""
    ((target\W)?cell\W)?  # Maybe the user thought that was part of the syntax
    \W*                   # There may be leading whitespace
    \$?                   # The cell reference may be absolute
    (?P<col>[a-z]{1,3})   # The column has at most three letters
    \$?                   # The cell reference may be absolute
    (?P<row>[0-9]+)       # The row number
    \W*                   # There may be trailing whitespace
    """,
    re.VERBOSE | re.IGNORECASE)


def understand(c: str, top: int, left: int) -> t.Optional[t.Tuple[int, int]]:
    """Parse user input
    >>> understand("cell c2", 3, 2)
    (2, 3)
    >>> understand("$G$3", 3, 2)
    (3, 7)
    >>> understand("d2", 3, 2)
    (2, 4)
    >>> understand("d", 3, 2)
    (4, 2)
    >>> understand("down", 3, 2)
    (4, 2)
    >>> understand("u l u", 3, 2)
    (1, 1)
    >>> understand("[u]p", 3, 2)
    (2, 2)
    """
    if re.fullmatch(r"\W*", c):
        return None
    elif CELL.fullmatch(c):
        # User entered target cell coordinates
        groups = CELL.fullmatch(c).groupdict()
        return openpyxl.utils.cell.coordinate_to_tuple(
            groups["col"].upper() + groups["row"])
    elif re.fullmatch("[^a-z]*u[^a-z]*p?[^a-z]*", c):
        return (top - 1, left)
    elif re.fullmatch("[^a-z]*l[^a-z]*(eft)?[^a-z]*", c):
        return (top, left - 1)
    elif re.fullmatch("[^a-z]*d[^a-z]*(own)?[^a-z]*", c):
        return (top + 1, left)
    elif re.fullmatch("[^a-z]*r[^a-z]*(ight)?[^a-z]*", c):
        return (top, left + 1)
    elif re.fullmatch("[^a-z]*([uldr][^a-z]*)+", c):
        return (top + c.count("d") - c.count("u"),
                left + c.count("r") - c.count("l"))
    elif not re.fullmatch("[^a-z]*[h].*", c, re.IGNORECASE):
        print("Command not understood.")
    print("""Enter (ie. type and then press 'Enter') one of the following:
  • The Excel coordinates (eg. 'C2' or 'G3') of the top left cell of your data.
  • A single direction string ('up', 'left', 'down', or 'right') to shift the
    boundary between headers and data by one cell in that direction.
  • A sequence of one or more direction abbreviations ('u', 'drr') to shift
    the boundary by that.
  • 'H' or 'help' or anything starting with 'h' to display this help.
  • Nothing, just press 'Enter', to accept the current boundary.""")
    return understand(input(">"), top, left)


FAV_SEP = '[,:;–]|\n|--'
SEP_RE = re.compile(FAV_SEP)
SEP_C_RE = re.compile(f"({FAV_SEP:})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a custom lexical dataset parser and dataset metadata for a particular dataset")
    parser.add_argument("excel", type=Path, help="The Excel file to inspect")
    args = parser.parse_args()

    wb = openpyxl.load_workbook(filename=args.excel)

    ws = select_sheet(wb)

    tty_columns, tty_rows = shutil.get_terminal_size()
    running = 0
    col_widths: t.List[int] = []
    for col in ws.iter_cols():
        w = min(15, max(len(c.value or '') for c in col))
        running += w + len("│")
        col_widths.append(w)
        if running >= tty_columns:
            overshoot = running - tty_columns
            col_widths[-1] -= overshoot
            break

    # Guess top and left of data
    if ws.freeze_panes:
        top, left = openpyxl.utils.cell.coordinate_to_tuple(ws.freeze_panes)
    # There can be more guessers here
    else:
        top, left = (2, 2)

    while True:
        clear()
        pretty(ws, col_widths, top, left, tty_rows)
        c = input("Enter a target cell or a direction (up/down/left/right) to move the data boundary. Enter [h]elp for more info. Press [Enter] to confirm. >")
        tl = understand(c, top, left)
        if tl is None:
            break
        top, left = tl

    mcl = 0
    for col in ws.iter_cols(min_col=left, max_row=top - 1):
        content_length = sum(
            len(cell.value or '') +
            ((len(SEP_RE.split(cell.comment.content)) * 8 + 8)
             if cell.comment else 0)
            for cell in col)
        if content_length > mcl:
            long_col = col
            mcl = content_length

    # FIXME: What comes now should be encapsulated in functions, so the same
    # kind of thing can be re-used for concepts and also tested in small units.
    clear()
    i = 0
    print("Your most verbose language metadata, with all potential cells and comments, looks like this:")
    for cell in long_col:
        value = cell.value or ''
        cell_content = '[{:}]'.format("\n     ".join(value.split("\n")))
        i += 1
        print(f"{i:2d}:", cell_content)
        cell_comment = cell.comment.content if cell.comment else ''
        cell_comment = ''.join((to_width(c, 15) if width(c) > 15 else c)
                               for c in SEP_C_RE.split(cell_comment))
        cell_comment = '({:})'.format(
            '\n     '.join(l for l in cell_comment.split("\n")))
        i += 1
        print(f"{i:2d}:", cell_comment)
    print("What should these items be mapped to? Enter column names like 'Name' to map objects to.")
    print("For help: http://git.io/lexedata-g")

    language_properties = {"Name": "cldf_name",
                           "Description": "cldf_description",
                           "Comment": "cldf_comment",
                           "ISO639P3code": "cldf_comment",
                           "Glottocode": "cldf_glottocode",
                           "Macroarea": "cldf_macroarea",
                           "Latitude": "cldf_latitude",
                           "Longitude": "cldf_longitude"}

    def completer(properties):
        def complete(text, state):
            for cmd in properties:
                if cmd.startswith(text):
                    if not state:
                        return cmd
                    else:
                        state -= 1
        return complete

    readline.set_completer(completer(language_properties))
    readline.parse_and_bind("tab: complete")
    cell_parsers: t.List[re.Pattern] = []
    for j in range(1, i + 1):
        pattern = input(f"{j:2d} > ")
        if not pattern.strip():
            pattern = ".*"
        # FIXME: This is a bad heuristic to distinguish regexes from raw
        # patterns.
        if "(?P<" in pattern or "*" in pattern:
            # Pattern is a regex
            pattern = pattern.lower().replace("(?p", "(?P")
        else:
            # Pattern is a naïve string pattern
            pattern = to_regex(pattern).pattern
        # FIXME: Compile, unwrap, re-compile seems cumbersome, but how else can
        # we rename those groups to the CLDF names?
        for readable, cldf in language_properties.items():
            r = readable.lower()
            pattern = pattern.replace(f"(?P<{r:}>", f"(?P<{cldf:}>")
            pattern = pattern.replace(f"(?P={r:})", f"(?P={cldf:})")
        regex = re.compile(pattern, re.IGNORECASE)
        cell_parsers.append(regex)
    cell_regexes = [x for x in cell_parsers[::2]]
    comment_regexes = [x for x in cell_parsers[1::2]]


    # TODO: This for loop should be used to provide a language_from_column
    # method for an ExcelParser subclass.
    for col in ws.iter_cols(min_col=left, max_row=top - 1):
        try:
            d: t.Dict[str, str] = {}
            for cell, cell_regex, comment_regex in zip(col, cell_regexes, comment_regexes):
                if cell.value:
                    # FIXME: If a property appears twice, currently the later
                    # appearance overwrites the earlier one. Merge wiser.
                    d.update(cell_regex.fullmatch(cell.value).groupdict())
                if cell.comment:
                    # FIXME: If a property appears twice, currently the later
                    # appearance overwrites the earlier one. Merge wiser.
                    d.update(comment_regex.fullmatch(cell.comment.content).groupdict())
            print(d)
        except AttributeError:
            print(f"Failed to parse {cell.coordinate} using your supplied pattern ({cell_regex.pattern:}), please check manually.")

    # TODO: The groups encountered here should become CLDF columns of the language.

    # For debugging:
    return locals()

if __name__ == "__main__":
    globals().update(main())


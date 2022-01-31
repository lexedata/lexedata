"""Import data in the "interleaved" format from an Excel spreadsheet.

Here, every even row contains cells with forms (cells may contain
multiple forms), while every odd row contains the associated cognate codes (a one-to-one relationship between forms and codes is expected).
Forms and cognate codes are separated by commas (",") and semi-colons (";"). Any other information existing in the cell will be parsed as
part of the form or the cognate code.
"""
import re
import os
import csv
import logging
import typing as t
from pathlib import Path

import openpyxl

from lexedata import cli, util, types
from lexedata.util.excel import clean_cell_value


def import_interleaved(
    ws: openpyxl.worksheet.worksheet.Worksheet,
    logger: logging.Logger = cli.logger,
    ids: t.Optional[t.Set[types.Cognateset_ID]] = None,
) -> t.Iterable[
    t.Tuple[
        types.Form_ID,
        types.Language_ID,
        types.Parameter_ID,
        str,
        None,
        types.Cognateset_ID,
    ]
]:
    if ids is None:
        ids = set()

    comma_or_semicolon = re.compile("[,;]\\W*")

    concepts = []
    for concept_metadata in ws.iter_cols(min_col=1, max_col=1, min_row=2):
        for entry, cogset in zip(concept_metadata[::2], concept_metadata[1::2]):
            try:
                concepts.append(clean_cell_value(entry))
            except AttributeError:
                break

    for language in cli.tq(
        ws.iter_cols(min_col=2), task="Parsing cells", total=ws.max_column
    ):
        language_name = clean_cell_value(language[0])
        for c, (entry, cogset) in enumerate(zip(language[1::2], language[2::2])):
            if not entry.value:
                if cogset.value:
                    logger.warning(
                        f"Cell {entry.coordinate} was empty, but cognatesets {cogset.value} were given in {cogset.coordinate}."
                    )
                continue
            bracket_level = 0
            i = 0
            f = clean_cell_value(entry)
            forms = []

            try:
                len(f)
            except TypeError:
                cli.Exit.INVALID_INPUT(
                    "I expected one or more forms (so, text) in cell {}, but found {}. Do you have more than one header row?".format(
                        entry.coordinate, f
                    )
                )

            while i < len(f):
                match = comma_or_semicolon.match(f[i:])
                if f[i] == "(":
                    bracket_level += 1
                    i += 1
                    continue
                elif f[i] == ")":
                    bracket_level -= 1
                    i += 1
                    continue
                elif bracket_level:
                    i += 1
                    continue
                elif match:
                    forms.append(f[:i].strip())
                    i += match.span()[1]
                    f = f[i:]
                    i = 0
                else:
                    i += 1

            forms.append(f.strip())

            if isinstance(clean_cell_value(cogset), int):
                cogsets = [str(clean_cell_value(cogset))]
            else:
                cogset = clean_cell_value(cogset)
                cogsets = comma_or_semicolon.split(cogset.strip())

            if len(cogsets) == 1 or len(cogsets) == len(forms):
                True
            else:
                logger.warning(
                    "{:}: Forms ({:}) did not match cognates ({:})".format(
                        entry.coordinate, ", ".join(forms), ", ".join(cogsets)
                    )
                )
            for form, cogset in zip(forms, cogsets + [None]):
                if form == "?" or cogset == "?":
                    continue
                base_id = util.string_to_id(f"{language_name}_{concepts[c]}")
                id = base_id
                synonym = 1
                while id in ids:
                    synonym += 1
                    id = f"{base_id}_s{synonym:d}"
                yield (id, language_name, concepts[c], form, None, cogset)
                ids.add(id)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "excel", type=Path, help="The Excel file to parse", metavar="EXCEL"
    )
    parser.add_argument(
        "--sheets",
        metavar="SHEET",
        nargs="+",
        default=[],
        help="Excel sheet name(s) to import (default: all sheets)",
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path(os.getcwd()),
        help="Path to directory where forms.csv is to be created (default: current working directory)",
    )
    cli.add_log_controls(parser)
    args = parser.parse_args()
    logger = cli.setup_logging(args)

    ws = openpyxl.load_workbook(args.excel)

    w = csv.writer(
        open(Path(args.directory) / "forms.csv", "w", newline="", encoding="utf-8")
    )
    w.writerow(
        ["ID", "Language_ID", "Parameter_ID", "Form", "Comment", "Cognateset_ID"]
    )

    if not args.sheets:
        args.sheets = [sheet for sheet in ws.sheetnames]

    ids: t.Set[str] = set()
    for sheetname in args.sheets:
        sheet = ws[sheetname]
        for row in import_interleaved(sheet, logger=logger, ids=ids):
            w.writerow(row)

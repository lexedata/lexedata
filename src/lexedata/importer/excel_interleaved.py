"""Import some Bantu data

This script is a very rough sketch for importing yet another shape of data.
Here, every even column contains cells with forms (some cells containing
multiple forms), while the odd columns contain the associated cognate codes
(generally in the same order).

"""
import re
import os
import csv
import logging
import typing as t
from pathlib import Path

import openpyxl

import lexedata.cli as cli
import lexedata.util as util


def import_interleaved(
    ws: openpyxl.worksheet.worksheet.Worksheet,
    logger: logging.Logger = cli.logger,
    ids: t.Set[str] = set(),
) -> list:
    comma_or_semicolon = re.compile("[,;]\\W*")

    concepts = []
    for concept_metadata in ws.iter_cols(min_col=1, max_col=1, min_row=2):
        for entry, cogset in zip(concept_metadata[::2], concept_metadata[1::2]):
            try:
                concepts.append(entry.value.strip())
            except AttributeError:
                break

    for language in ws.iter_cols(min_col=2):
        language_name = language[0].value
        for c, (entry, cogset) in enumerate(zip(language[1::2], language[2::2])):
            if not entry.value:
                if cogset.value:
                    logger.warning(
                        f"Cell {entry.coordinate} was empty, but cognatesets {cogset.value} were given in {cogset.coordinate}."
                    )
                continue
            bracket_level = 0
            i = 0
            f = entry.value.strip()
            forms = []
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

            if type(cogset.value) == float:
                cogsets = [str(int(cogset.value))]
            else:
                if isinstance(cogset.value, int):
                    cogset = str(cogset.value)
                else:
                    cogset = cogset.value
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
                base_id = util.string_to_id(f"{language_name}_{concepts[c]}")
                id = base_id
                synonym = 1
                while id in ids:
                    synonym += 1
                    id = f"{base_id}_s{synonym:d}"
                yield [id, language_name, concepts[c], form, None, cogset]
                ids.add(id)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("excel", type=Path, help="The Excel file to parse")
    parser.add_argument(
        "--sheet", action="append", default=[], help="Excel sheet name(s) to import"
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path(os.getcwd()),
        help="Path to directory where forms.csv is created (default: current working directory)",
    )
    cli.add_log_controls(parser)
    args = parser.parse_args()
    logger = cli.setup_logging(args)

    ws = openpyxl.load_workbook(args.excel)

    w = csv.writer(open(Path(args.directory) / "forms.csv", "w", encoding="utf-8"))
    w.writerow(
        ["ID", "Language_ID", "Parameter_ID", "Form", "Comment", "Cognateset_ID"]
    )

    if not args.sheet:
        args.sheet = ws.get_sheet_names()

    ids: t.Set[str] = set()
    for sheetname in args.sheet:
        sheet = ws[sheetname]
        for row in import_interleaved(sheet, logger=logger, ids=ids):
            w.writerow(row)

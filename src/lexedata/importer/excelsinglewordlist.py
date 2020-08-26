import csv
import logging
import unicodedata
import typing as t

import openpyxl


def normalize_header(row: t.Iterable[openpyxl.cell.Cell], running_id: bool = False) -> t.Iterable[str]:
    header = [unicodedata.normalize('NFKD', (n.value or '').strip()) or
              f'c{c:}'
              for c, n in enumerate(row)]
    header = [h.replace(" ", "_") for h in header]
    header = [h.replace("(", "") for h in header]
    header = [h.replace(")", "") for h in header]
    header.append("Language")
    if args.add_running_id:
        header.append("ID")
    return header

def cell_value(cell):
    if cell.value is None:
        return ''
    v = unicodedata.normalize('NFKD', (str(cell.value) or '').strip())
    if type(v) == float:
        if v == int(v):
            return int(v)
        return v
    if type(v) == int:
        return v
    try:
        return v.replace("\n", ";\t")
    except TypeError:
        return str(v)

def import_language(
        sheet: openpyxl.worksheet.worksheet.Worksheet,
        writer: csv.DictWriter,
        concept_property_columns: t.Iterable[str],
        running_id: t.Optional[int] = 1) -> int:
    """

    Return
    ======

    int: the number of forms imported
    """
    language = sheet.title
    fn: t.Iterable[str]
    empty_cols: t.Set[int] = set()
    for i, col in enumerate(sheet.iter_cols()):
        column = [str(unicodedata.normalize('NFKD', (str(c.value) or '').strip())).strip() or None for c in col]
        if not any(column[1:]):
            empty_cols.add(i)

    for i, row in enumerate(sheet.iter_rows()):
        if i == 0:
            header = normalize_header(row)
            diff1 = (set(writer.fieldnames) | set(concept_property_columns)) - {
                h for c, h in enumerate(header) if c not in empty_cols}
            diff2 = {h for c, h in enumerate(header) if c not in empty_cols} - set(
                writer.fieldnames) - set(concept_property_columns)
            if diff1 or diff2:
                logging.warning(
                    "Headers mismatch in sheet %s: expected %s but found %s",
                    language,
                    diff1,
                    diff2)
        data = {
            k: cell_value(cell)
            for k, (c, cell) in zip(header, enumerate(row))
            if c not in empty_cols
            if k in writer.fieldnames
        }
        if "Language" in writer.fieldnames:
            data["Language"] = language
        if running_id is not None:
            data['ID'] = i + running_id
        for c in concept_property_columns:
            try:
                del data[c]
            except KeyError:
                pass
        writer.writerow(data)
    return i + 1


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Parse Excel file into CSV")
    parser.add_argument(
        "excel", type=openpyxl.load_workbook,
        help="The Excel file to parse")
    parser.add_argument(
        "concept_column", help="Title of the column linking rows to concepts")
    parser.add_argument(
        "--concept-property", action="append", default=[],
        help="Additional columns titles that describe concept properties, not form properties"
    )
    parser.add_argument(
        "csv", nargs="?", default="forms.csv", type=argparse.FileType('w'),
        help="Output CSV file")
    parser.add_argument(
        "--sheet", type=str, action="append",
        help="Sheets to parse (default: all)")
    parser.add_argument(
        "--exclude-sheet", "-x", type=str, action="append", default=[],
        help="Sheets not to parse")
    parser.add_argument(
        "--add-running-id", action="store_true", default=False,
        help="Add an automatic integer 'ID' column")
    args = parser.parse_args()
    if not args.sheet:
        args.sheet = [sheet for sheet in args.excel.sheetnames
                      if sheet not in args.exclude_sheet]
        logging.warn("No sheets specified. Parsing sheets: %s", args.sheet)
    first_sheet = args.excel[args.sheet[0]]
    empty_cols: t.Set[int] = set()
    for i, col in enumerate(first_sheet.iter_cols()):
        column = [
            unicodedata.normalize('NFKD', (str(c.value) or '').strip())
            for c in col]
        if not any(column[1:]):
            empty_cols.add(i)

    header = normalize_header(
        r for c, r in enumerate(next(first_sheet.iter_rows(1, 1))) if c not in empty_cols)
    header = [h for h in header if h not in args.concept_property]
    d = csv.DictWriter(
        args.csv,
        header)
    d.writeheader()
    r = 1
    for sheet in args.sheet:
        logging.info("Parsing sheet %s", sheet)
        r += import_language(
            args.excel[sheet], writer=d,
            concept_property_columns=args.concept_property,
            running_id=r if args.add_running_id else None)

    concept_header = [args.concept_column] + args.concept_property
    d = csv.DictWriter(
        open('concepts.csv', 'w'),
        concept_header)
    d.writeheader()
    for sheet in args.sheet:
        logging.info("Parsing sheet %s", sheet)
        import_language(
            args.excel[sheet], writer=d,
            concept_property_columns=[h for h in header if h != args.concept_column],
            running_id=False)

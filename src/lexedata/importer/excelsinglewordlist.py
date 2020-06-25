import csv
import logging
import typing as t

import openpyxl

def import_language(
        sheet: openpyxl.worksheet.worksheet.Worksheet,
        writer: csv.DictWriter) -> None:
    language = sheet.title
    fn: t.Iterable[str]
    empty_cols: t.Set[int] = set()
    for i, col in enumerate(sheet.iter_cols()):
        column = [str(c.value).strip() if c.value is not None else None for c in col]
        if not any(column[1:]):
            empty_cols.add(i)

    for i, row in enumerate(sheet.iter_rows()):
        if i == 0:
            header = [
                n.value or f'c{c:}'
                for c, n in enumerate(row)
                if c not in empty_cols]
            diff1 = (set(writer.fieldnames) - {"Language"}) - set(header)
            diff2 = set(header) - (set(writer.fieldnames) - {"Language"})
            if diff1 or diff2:
                logging.warning(
                    "Headers mismatch in sheet %s: expected %s but found %s",
                    language,
                    diff1,
                    diff2)
        data = {
            k: (int(cell.value)
                if int(cell.value) == cell.value
                else cell.value)
            if type(cell.value) == float
            else cell.value
            for k, (c, cell) in zip(header, enumerate(row))
            if c not in empty_cols
            if k in writer.fieldnames}
        data["Language"] = language
        writer.writerow(data)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Parse Excel file into CSV")
    parser.add_argument(
        "excel", type=openpyxl.load_workbook,
        help="The Excel file to parse")
    parser.add_argument(
        "csv", nargs="?", default="forms.csv", type=argparse.FileType('w'),
        help="Output CSV file")
    parser.add_argument(
        "--sheet", type=str, action="append",
        help="Sheets to parse (default: all)")
    parser.add_argument(
        "--exclude-sheet", "-x", type=str, action="append", default=[],
        help="Sheets not to parse")
    args = parser.parse_args()
    if not args.sheet:
        args.sheet = [sheet for sheet in args.excel.sheetnames
                      if sheet not in args.exclude_sheet]
        logging.warn("No sheets specified. Parsing sheets: %s", args.sheet)
    first_sheet = args.excel[args.sheet[0]]
    empty_cols: t.Set[int] = set()
    for i, col in enumerate(first_sheet.iter_cols()):
        column = [str(c.value).strip() if c.value is not None else None for c in col]
        if not any(column[1:]):
            empty_cols.add(i)
    header = [n.value or f'c{c:}'
              for c, n in enumerate(next(first_sheet.iter_rows(1, 1)))
              if c not in empty_cols]
    header.insert(0, "Language")
    d = csv.DictWriter(
        args.csv,
        header)
    d.writeheader()
    for sheet in args.sheet:
        logging.info("Parsing sheet %s", sheet)
        import_language(
            args.excel[sheet],
            d)

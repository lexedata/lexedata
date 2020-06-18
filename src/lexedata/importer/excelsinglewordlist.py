import csv
import logging
import typing as t

import openpyxl

def import_language(
        sheet: openpyxl.worksheet.worksheet.Worksheet,
        writer: csv.DictWriter) -> None:
    language = sheet.title
    fn: t.Iterable[str]
    for i, row in enumerate(sheet.iter_rows()):
        if i == 0:
            header = [
                n.value or f'c{c:}'
                for c, n in enumerate(row)]
            diff1 = (set(writer.fieldnames) - {"Language"}) - set(header)
            diff2 = set(header) - (set(writer.fieldnames) - {"Language"})
            if diff1 or diff2:
                logging.warning(
                    "Headers mismatch in sheet %s: %s vs. %s",
                    language,
                    diff1,
                    diff2)
        data = {
            k: (int(r.value)
                if int(r.value) == r.value
                else r.value)
            if type(r.value) == float
            else r.value
            for k, r in zip(header, row)
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
    header = [n.value or f'c{c:}'
              for c, n in enumerate(next(first_sheet.iter_rows(1, 1)))]
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

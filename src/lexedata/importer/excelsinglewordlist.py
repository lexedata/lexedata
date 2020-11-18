import csv
import logging
import unicodedata
import typing as t

import openpyxl
import pycldf


from lexedata.importer.fromexcel import DB
from lexedata.types import (
    Object,
    Language,
    RowObject,
    Form,
    Concept,
)

# TODO: Remark for Gereon: On purpose, I chose not to append new concepts and forms to the csv-files.
# I  thought, it is rather redundant to initiate the DB and then not really use it.
# Also, I thought that we need to ensure in any case that the different IDs match,
# so this ist best done by using the DB and its create unique id function...

def normalize_header(
    row: t.Iterable[openpyxl.cell.Cell], add_running_id: bool = False
) -> t.Iterable[str]:
    header = [
        unicodedata.normalize("NFKD", (n.value or "").strip()) or f"c{c:}"
        for c, n in enumerate(row)
    ]
    header = [h.replace(" ", "_") for h in header]
    header = [h.replace("(", "") for h in header]
    header = [h.replace(")", "") for h in header]
    header.append("Language")
    if add_running_id:
        header.append("ID")
    return header


def cell_value(cell):
    if cell.value is None:
        return ""
    v = unicodedata.normalize("NFKD", (str(cell.value) or "").strip())
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
    dataset_header: t.Iterable[str],
    concept_property_columns: t.Iterable[str],
    running_id: t.Optional[int] = 1,
) -> int:
    """

    Return
    ======

    int: the number of forms imported
    """
    language = sheet.title
    fn: t.Iterable[str]
    empty_cols: t.Set[int] = set()
    for i, col in enumerate(sheet.iter_cols()):
        column = [
            str(unicodedata.normalize("NFKD", (str(c.value) or "").strip())).strip()
            or None
            for c in col
        ]
        if not any(column[1:]):
            empty_cols.add(i)

    for i, row in enumerate(sheet.iter_rows()):
        if i == 0:
            header = normalize_header(row)
            diff1 = (set(writer.fieldnames) | set(concept_property_columns)) - {
                h for c, h in enumerate(header) if c not in empty_cols
            }
            diff2 = (
                {h for c, h in enumerate(header) if c not in empty_cols}
                - set(writer.fieldnames)
                - set(concept_property_columns)
            )
            if diff1 or diff2:
                logging.warning(
                    "Headers mismatch in sheet %s: expected %s but found %s",
                    language,
                    diff1,
                    diff2,
                )
        data = {
            k: cell_value(cell)
            for k, (c, cell) in zip(header, enumerate(row))
            if c not in empty_cols
            if k in writer.fieldnames
        }
        if "Language" in writer.fieldnames:
            data["Language"] = language
        if running_id is not None:
            data["ID"] = i + running_id
        for c in concept_property_columns:
            try:
                del data[c]
            except KeyError:
                pass
        writer.writerow(data)
    return i + 1


def read_single_excel_sheet(
        existing_dataset: pycldf.Dataset,
        sheet: openpyxl.worksheet.worksheet.Worksheet,
        concept_property_columns: t.Iterable[str]):
    parser = DB(existing_dataset)
    parser.cache_dataset()
    # prepare Headers
    # get header from cldfdataset.[table_type].tableSchema.columndict()
    form_header = parser.dataset["FormTable"].tableSchema.columndict()
    concept_header = parser.dataset["ParameterTable"].tableSchema.columndict()
    dataset_header = form_header + concept_header
    sheet_form_header, sheet_concept_header = get_headers_from_excel(sheet, concept_property)
    sheet_header = sheet_form_header + sheet_concept_header
    match_for_forms = form_header & sheet_form_header
    match_for_concepts = concept_header & sheet_concept_header

    # read new data from sheet
    new_data = import_language_from_sheet(
        sheet, sheet_header=sheet_header,
        dataset_header=dataset_header,
        concept_property_columns=concept_property_columns
    )
    language = new_data.keys()[0]
    new_data = new_data[language]

    # compare headers from sheet and headers from data set
    diff_form = set(sheet_form_header) - set(form_header)
    if diff_form:
        logging.warning(
            "Form headers mismatch in sheet %s: expected %s but found %s",
            language,
            form_header,
            sheet_form_header,
        )
    diff_concept = set(sheet_concept_header) - set(concept_header)
    if diff_concept:
        logging.warning(
            "Concept headers mismatch in sheet %s: expected %s but found %s",
            language,
            concept_header,
            sheet_concept_header,
        )

    # check for existing concept and forms by matching with intersection of data set and sheet header
    c_l_name = parser.dataset["LanguageTable", "name"].name
    c_l_id = parser.dataset["LanguageTable", "id"].name
    language = {c_l_name: language }
    language_candidates = parser.find_db_candidates(language, [c_l_name])
    if language_candidates:
        for language_id in language_candidates:
            language [c_l_id] = language_id
            break
    else:
        language = Language({
            c_l_id: language[c_l_name],
            c_l_name: language[c_l_name],
        })
        parser.make_id_unique(language)
        parser.insert_into_db(language)
    # TODO: shall new properties be added, although they were not present in the table so far?
    c_c_id = parser.dataset["ParameterTable", "id"].name
    c_f_id = parser.dataset["FormTable", "id"].name
    for form, concept in new_data:
        concept_candidates = parser.find_db_candidates(concept, match_for_concepts)
        if concept_candidates:
            for concept_id in concept_candidates:
                concept[c_c_id] = concept_id
                break
        else:
            # TODO: How to know where to derive a concept id from?
            concept[c_c_id] = concept.values()[0]
            concept = Concept(**concept)
            parser.make_id_unique(concept)
            parser.insert_into_db(concept)
        form_candidates = parser.find_db_candidates(form, match_for_forms)
        if form_candidates:
            for form_id in form_candidates:
                form[c_f_id] = form_id
                # or to copy existing form form = parser.cache["FormTable"][form_id]
                break
        else:
            form[c_f_id] = form.values()[0]
            form = Form(**form)
            parser.make_id_unique(form)
            parser.insert_into_db(form)

    # write to cldf
    parser.write_dataset_from_cache()


def import_language_from_sheet(
    sheet: openpyxl.worksheet.worksheet.Worksheet,
    sheet_header: t.Iterable[str],
    dataset_header: t.Iterable[str],
    concept_property_columns: t.Iterable[str],
    running_id: t.Optional[int] = 1,
) -> t.Dict[str, t.List[t.Tuple[t.Dict[str, str], t.Dict[str, str]]]]:
    language = sheet.title
    new_data = {language: []}
    # find empty columns in this sheet
    empty_cols: t.Set[int] = set()
    for i, col in enumerate(sheet.iter_cols()):
        column = [
            str(unicodedata.normalize("NFKD", (str(c.value) or "").strip())).strip()
            or None
            for c in col
        ]
        if not any(column[1:]):
            empty_cols.add(i)
    # skip first row
    row_iter = sheet.iter_rows()
    next(row_iter)
    # compare header of this sheet to format of given data set
    # process row
    for i, row in enumerate(row_iter):
        data = {
            k: cell_value(cell)
            for k, (c, cell) in zip(sheet_header, enumerate(row))
            if c not in empty_cols
            if k in dataset_header
        }
        if "Language" in dataset_header:
            data["Language"] = language
        if running_id is not None:
            data["ID"] = i + running_id
        concept = dict()
        for c in concept_property_columns:
            try:
                concept[c] = data[c]
                del data[c]
            except KeyError:
                pass
        new_data[language].append((data, concept))
    return new_data


def get_headers_from_excel(sheet: openpyxl.workbook.Sheet, concept_property)->t.Tuple[t.List[str]]:
    empty_cols: t.Set[int] = set()
    for i, col in enumerate(sheet.iter_cols()):
        column = [
            unicodedata.normalize("NFKD", (str(c.value) or "").strip()) for c in col
        ]
        if not any(column[1:]):
            empty_cols.add(i)

    header = normalize_header(
        r
        for c, r in enumerate(next(sheet.iter_rows(1, 1)))
        if c not in empty_cols
    )
    header = [h for h in header if h not in concept_property]
    return header, concept_property

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Parse Excel file into CSV")
    parser.add_argument(
        "excel", type=openpyxl.load_workbook, help="The Excel file to parse"
    )
    parser.add_argument(
        "concept_column", help="Title of the column linking rows to concepts"
    )
    parser.add_argument(
        "--concept-property",
        action="append",
        default=[],
        help="Additional columns titles that describe concept properties, not form properties",
    )
    parser.add_argument(
        "csv",
        nargs="?",
        default="forms.csv",
        type=argparse.FileType("w"),
        help="Output CSV file",
    )
    parser.add_argument(
        "--sheet", type=str, action="append", help="Sheets to parse (default: all)"
    )
    parser.add_argument(
        "--exclude-sheet",
        "-x",
        type=str,
        action="append",
        default=[],
        help="Sheets not to parse",
    )
    parser.add_argument(
        "--add-running-id",
        action="store_true",
        default=False,
        help="Add an automatic integer 'ID' column",
    )
    args = parser.parse_args()
    if not args.sheet:
        args.sheet = [
            sheet for sheet in args.excel.sheetnames if sheet not in args.exclude_sheet
        ]
        logging.warning("No sheets specified. Parsing sheets: %s", args.sheet)
    first_sheet = args.excel[args.sheet[0]]
    empty_cols: t.Set[int] = set()
    for i, col in enumerate(first_sheet.iter_cols()):
        column = [
            unicodedata.normalize("NFKD", (str(c.value) or "").strip()) for c in col
        ]
        if not any(column[1:]):
            empty_cols.add(i)

    header = normalize_header(
        r
        for c, r in enumerate(next(first_sheet.iter_rows(1, 1)))
        if c not in empty_cols
    )
    header = [h for h in header if h not in args.concept_property]
    d = csv.DictWriter(args.csv, header)
    d.writeheader()
    r = 1
    for sheet in args.sheet:
        logging.info("Parsing sheet %s", sheet)
        r += import_language(
            args.excel[sheet],
            writer=d,
            concept_property_columns=args.concept_property,
            running_id=r if args.add_running_id else None,
        )

    concept_header = [args.concept_column] + args.concept_property
    d = csv.DictWriter(open("concepts.csv", "w"), concept_header)
    d.writeheader()
    for sheet in args.sheet:
        logging.info("Parsing sheet %s", sheet)
        import_language(
            args.excel[sheet],
            writer=d,
            concept_property_columns=[h for h in header if h != args.concept_column],
            running_id=False,
        )

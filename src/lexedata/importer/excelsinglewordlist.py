import logging
import unicodedata
import typing as t

import openpyxl
import pycldf

from lexedata.util import string_to_id
from lexedata.importer.fromexcel import DB
from lexedata.types import (
    Language,
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


# TODO: replace this function with a serious way of getting an id candidate
def return_first_not_none_or_id(mydict: t.Dict[str, str]) -> str:
    try:
        return mydict["ID"]
    except KeyError:
        for k, v in mydict.items():
            if v:
                return v


def read_single_excel_sheet(
    existing_dataset: pycldf.Dataset,
    sheet: openpyxl.worksheet.worksheet.Worksheet,
    concept_property_columns: t.Iterable[str],
    running_id: t.Optional[int] = False,
):
    parser = DB(existing_dataset)
    parser.cache_dataset()
    # required cldf fields
    c_l_name = parser.dataset["LanguageTable", "name"].name
    c_l_id = parser.dataset["LanguageTable", "id"].name
    c_c_id = parser.dataset["ParameterTable", "id"].name
    c_c_name = parser.dataset["ParameterTable", "name"].name
    c_f_id = parser.dataset["FormTable", "id"].name
    c_f_language = parser.dataset["FormTable", "languageReference"].name
    # prepare Headers
    # get header from cldfdataset.[table_type].tableSchema.columndict columndict is property of TableSchema
    form_header = list(parser.dataset["FormTable"].tableSchema.columndict.keys())
    concept_header = list(
        parser.dataset["ParameterTable"].tableSchema.columndict.keys()
    )
    dataset_header = form_header + concept_header
    sheet_header, sheet_form_header, sheet_concept_header = get_headers_from_excel(
        sheet, args.concept_property
    )
    # Language_id is added to form
    form_header.append(c_f_language)
    match_for_forms = list(set(form_header) & set(sheet_form_header))
    match_for_concepts = list(set(concept_header) & set(sheet_concept_header))
    # read new data from sheet
    new_data = import_language_from_sheet(
        sheet,
        sheet_header=sheet_header,
        dataset_header=dataset_header,
        concept_property_columns=concept_property_columns,
        running_id=running_id,
    )
    language = list(new_data.keys())[0]
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
    language = Language({c_l_name: language})
    language_candidates = parser.find_db_candidates(language, [c_l_name])
    if language_candidates:
        for language_id in language_candidates:
            language[c_l_id] = language_id
            break
    else:
        language = Language(
            {
                c_l_id: string_to_id(language[c_l_name]),
                c_l_name: language[c_l_name],
            }
        )
        parser.make_id_unique(language)
        parser.insert_into_db(language)
    # TODO: shall new properties be added, although they were not present in the table so far?
    for form, concept in new_data:
        concept = Concept(**concept)
        concept_candidates = parser.find_db_candidates(concept, match_for_concepts)
        if concept_candidates:
            for concept_id in concept_candidates:
                concept[c_c_id] = concept_id
                concept[c_c_name] = parser.cache["ParameterTable"][concept_id][c_c_name]
                break
        else:
            # TODO: How to know where to derive a concept id from?
            concept[c_c_id] = string_to_id(return_first_not_none_or_id(concept))
            concept[c_c_name] = return_first_not_none_or_id(concept)
            parser.make_id_unique(concept)
            parser.insert_into_db(concept)
        # add language id, look for candidates
        form[c_f_language] = language[c_l_id]
        form = Form(**form)
        form_candidates = parser.find_db_candidates(form, match_for_forms)
        if form_candidates:
            for form_id in form_candidates:
                form[c_f_id] = form_id
                # or to copy existing form form = parser.cache["FormTable"][form_id]
                break
        else:
            form[c_f_id] = f"{language[c_l_id]}_{concept[c_c_id]}"
            parser.make_id_unique(form)
            parser.insert_into_db(form)
        parser.associate(form[c_f_id], concept)
    # write to cldf
    parser.write_dataset_from_cache()


def get_headers_from_excel(
    sheet: openpyxl.worksheet.worksheet.Worksheet, concept_property
) -> t.Tuple[t.List[str], t.List[str], t.List[str]]:
    empty_cols: t.Set[int] = set()
    for i, col in enumerate(sheet.iter_cols()):
        column = [
            str(unicodedata.normalize("NFKD", (str(e)).strip())).strip()
            for e in [c.value or "" for c in col]
        ]
        if not any(column[1:]):
            empty_cols.add(i)

    header = normalize_header(r for c, r in enumerate(next(sheet.iter_rows(1, 1))))
    form_header = []
    concept_header = []
    for h in header:
        if h in concept_property:
            concept_header.append(h)
        elif h not in empty_cols:
            form_header.append(h)

    return list(header), form_header, concept_property


def import_language_from_sheet(
    sheet: openpyxl.worksheet.worksheet.Worksheet,
    sheet_header: t.Iterable[str],
    dataset_header: t.Iterable[str],
    concept_property_columns: t.Iterable[str],
    running_id: t.Optional[int] = False,
) -> t.Dict[str, t.List[t.Tuple[t.Dict[str, str], t.Dict[str, str]]]]:
    language = sheet.title
    new_data = {language: []}
    # find empty columns in this sheet
    empty_cols: t.Set[int] = set()
    for i, col in enumerate(sheet.iter_cols()):
        column = [
            str(unicodedata.normalize("NFKD", (str(e)).strip())).strip()
            for e in [c.value or "" for c in col]
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
        # value is a required field of form, containing the content in its original form
        data[dataset["FormTable", "value"].name] = " ".join(
            [str(e) for e in [c.value or "" for c in row]]
        )
        if "Language" in dataset_header:
            data["Language"] = language
        if running_id:
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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Parse Excel file into CSV")
    parser.add_argument(
        "excel", type=openpyxl.load_workbook, help="The Excel file to parse"
    )
    parser.add_argument("metadata", help="Title of the column linking rows to concepts")
    parser.add_argument(
        "--concept-property",
        action="append",
        type=str,
        default=[],
        help="Additional columns titles that describe concept properties, not form properties",
    )
    parser.add_argument(
        "--sheet", type=str, action="append", help="Sheets to parse (default: all)"
    )
    parser.add_argument(
        "--exclude-sheet",
        "-x",
        type=lambda s: s.split(","),
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
    for sheet in args.sheet:
        dataset = pycldf.Dataset.from_metadata(args.metadata)
        read_single_excel_sheet(
            dataset,
            args.excel[sheet],
            args.concept_property,
            running_id=args.add_running_id,
        )

import sys
import unicodedata
import typing as t
import logging

import openpyxl
import pycldf

from lexedata.util import string_to_id
from lexedata.importer.fromexcel import DB
from lexedata.types import (
    Language,
    Form,
    Concept,
)

logger = logging.getLogger(__file__)

# TODO: Remark for Gereon: On purpose, I chose not to append new concepts and forms to the csv-files.
# I  thought, it is rather redundant to initiate the DB and then not really use it.
# Also, I thought that we need to ensure in any case that the different IDs match,
# so this ist best done by using the DB and its create unique id function...


def normalize_header(
    row: t.Iterable[openpyxl.cell.Cell], add_running_id: bool = False
) -> t.Iterable[str]:
    header = [
        unicodedata.normalize("NFKD", (n.value or "").strip()) or ""
        for c, n in enumerate(row)
    ]
    header = [h.replace(" ", "_") for h in header]
    header = [h.replace("(", "") for h in header]
    header = [h.replace(")", "") for h in header]
    while "" in header:
        header.remove("")
    if add_running_id:
        header.append("ID")
    return header


def get_headers_from_excel(
        sheet: openpyxl.worksheet.worksheet.Worksheet,
        row_property: t.Iterable[str] = []
) -> t.Tuple[t.List[str], t.List[str]]:

    header = normalize_header(r for c, r in enumerate(next(sheet.iter_rows(1, 1))))
    form_header = []
    for h in header:
        if h not in row_property:
            form_header.append(h)

    return list(header), form_header


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


def import_language_from_sheet(
    sheet: openpyxl.worksheet.worksheet.Worksheet,
    sheet_header: t.Iterable[str],
    row_property_columns: t.Iterable[str],
    running_id: t.Optional[int] = False,
) -> t.Dict[str, t.List[t.Tuple[t.Dict[str, str], t.Dict[str, str]]]]:
    language = sheet.title
    new_data = {language: []}
    # skip first row
    row_iter = sheet.iter_rows()
    next(row_iter)
    # compare header of this sheet to format of given data set
    # process row
    for i, row in enumerate(row_iter):
        data = {
            k: cell.value
            for k, (c, cell) in zip(sheet_header, enumerate(row))
        }
        # internal value will be handed over to cldf value
        data["internal_value"] = " ".join(
            [str(e) for e in [c.value or "" for j, c in enumerate(row)]]
        )
        if running_id:
            data["ID"] = i + running_id
        row_object = dict()
        for c in row_property_columns:
            try:
                row_object[c] = data[c]
                del data[c]
            except KeyError:
                pass
        new_data[language].append((data, row_object))
    return new_data


def read_single_excel_sheet(
    existing_dataset: pycldf.Dataset,
    sheet: openpyxl.worksheet.worksheet.Worksheet,
    match_form: t.List[str],
    concept_property: t.Iterable[str],
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
    c_f_form = parser.dataset["FormTable", "form"].name
    c_f_value = parser.dataset["FormTable", "value"].name
    if not match_form:
        match_form = [c_f_form, c_f_language]
    # TODO: set here concept_property and match for concept if not provided
    # header from data set
    form_header = list(parser.dataset["FormTable"].tableSchema.columndict.keys())
    # header from sheet
    sheet_header, sheet_form_header = get_headers_from_excel(
        sheet, concept_property
    )
    # read new data from sheet
    new_data = import_language_from_sheet(
        sheet,
        sheet_header=sheet_header,
        row_property_columns=concept_property,
        running_id=running_id,
    )
    language = list(new_data.keys())[0]
    new_data = new_data[language]
    # compare headers from sheet and headers from data set
    # if sheet_form_header contains properties not in form header of data set, exit script
    diff_form = set(sheet_form_header) - set(form_header)
    if diff_form:
        logging.warning(
            "Form headers mismatch in sheet %s: expected %s but found %s.\n"
            "The import of the excel file was aborted to preserve integrity of the cldf data set",
            language,
            form_header,
            sheet_form_header,
        )
        sys.exit()
    # add status column to parameterTable if doesn't exist
    try:
        parser.dataset["ParameterTable", "Status"].name
    except KeyError:
        parser.dataset.add_columns("ParameterTable", "Status")
    # check for existing concept and forms by matching with intersection of data set and sheet header
    language = Language({c_l_name: language})
    language_candidates = parser.find_db_candidates(language, [c_l_name])
    if language_candidates:
        for language_id in language_candidates:
            language[c_l_id] = language_id
            logger.warning(f"Language {language[c_l_name]} is already in the data set")
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

    for form, concept in new_data:
        concept = Concept({
            c_c_id: string_to_id(concept[concept_property[0]]),
            c_c_name: concept[concept_property[0]]
        })
        concept_candidates = parser.find_db_candidates(concept, [c_c_name])
        if concept_candidates:
            for concept_id in concept_candidates:
                concept[c_c_id] = concept_id
                concept[c_c_name] = parser.cache["ParameterTable"][concept_id][c_c_name]
                # TODO check here whether concept was linked to form '?'
                break
        else:
            concept[c_c_id] = string_to_id(concept[c_c_name])
            concept["Status"] = "auto from new forms"
            parser.make_id_unique(concept)
            parser.insert_into_db(concept)

        # add or overwrite required properties if not present
        form[c_f_language] = language[c_l_id]
        if c_f_value not in form:
            form[c_f_value] = form["internal_value"]
            del form["internal_value"]
        else:
            del form["internal_value"]
        form = Form(**form)
        form_candidates = parser.find_db_candidates(form, match_form)
        # for partial matching
        # candidates = [candidate for candidate, properties in self.cache[object.__table__].items() if
        #                        any(properties[p] == object[p] for p in properties)]
        if form_candidates:
            for form_id in form_candidates:
                form[c_f_id] = form_id
                logger.warning(
                    f"Form {form[c_f_id]} for language {language[c_l_id]} was"
                    f" already in data set for concepts "
                    f"{parser.cache['FormTable'][form_id][parser.dataset['FormTable', 'parameterReference'].name]}."
                    f" We added additional concept {concept[c_c_id]} (polysemy)."
                    f" If you want these to be  considered different forms, create a new row "
                    f"for form {form[c_f_id]}_2 in"
                    f" forms.csv and delete concept "
                    f"{parser.cache['FormTable'][form_id][parser.dataset['FormTable', 'parameterReference'].name]}"
                    f" from form {form[c_f_id]}_1."
                )
                # or to copy existing form form = parser.cache["FormTable"][form_id]
                break
        else:
            if c_f_id not in form:
                # TODO: maybe check for type of form id column
                form[c_f_id] = f"{language[c_l_id]}_{concept[c_c_id]}"
            parser.make_id_unique(form)
            parser.insert_into_db(form)
        parser.associate(form[c_f_id], concept)
    # write to cldf
    parser.write_dataset_from_cache()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Parse Excel file into CSV")
    parser.add_argument(
        "excel",
        type=openpyxl.load_workbook,
        help="The Excel file to parse"
    )
    parser.add_argument(
        "metadata",
        help="Title of the column linking rows to concepts"
    )
    parser.add_argument(
        "--concept-property",
        type=str,
        help="Additional columns titles that describe concept properties, not form properties",
    )
    parser.add_argument(
        "--match-form",
        nargs="*",
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
        type=str,
        nargs="*",
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
    concept_property = [args.concept_property]
    for sheet in args.sheet:
        dataset = pycldf.Dataset.from_metadata(args.metadata)
        read_single_excel_sheet(
            dataset,
            args.excel[sheet],
            args.match_form,
            concept_property,
            running_id=args.add_running_id,
        )

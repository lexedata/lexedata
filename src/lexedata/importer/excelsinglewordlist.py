import sys
import logging
import unicodedata
import typing as t
from pathlib import Path

import openpyxl
import pycldf

from lexedata.util import string_to_id
from lexedata.importer.fromexcel import DB
from lexedata.types import Form

logger = logging.getLogger(__file__)


class KeyKeyDict:
    def __getitem__(self, key):
        return key


def normalize_header(row: t.Iterable[openpyxl.cell.Cell]) -> t.Iterable[str]:
    header = [unicodedata.normalize("NFKC", (n.value or "").strip()) for n in row]
    header = [h.replace(" ", "_") for h in header]
    header = [h.replace("(", "") for h in header]
    header = [h.replace(")", "") for h in header]

    return header


def get_headers_from_excel(
    sheet: openpyxl.worksheet.worksheet.Worksheet,
) -> t.Iterable[str]:
    return normalize_header(r for c, r in enumerate(next(sheet.iter_rows(1, 1))))


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


def import_data_from_sheet(
    sheet,
    sheet_header,
    implicit: t.Mapping[t.Literal["languageReference", "id", "value"], str] = {},
    entries_to_concepts: t.Mapping[str, str] = KeyKeyDict(),
    concept_column: t.Tuple[str, str] = ("Concept_ID", "Concept_ID"),
) -> t.Iterable[Form]:
    row_iter = sheet.iter_rows()

    # TODO?: compare header of this sheet to format of given data set process
    # row. Maybe unnecessary.
    header = next(row_iter)

    for row in row_iter:
        data = Form({k: cell_value(cell) for k, cell in zip(sheet_header, row)})
        if "value" in implicit:
            data[implicit["value"]] = "\t".join(map(str, data.values()))
        try:
            concept_entry = data.pop(concept_column[1])
            data[concept_column[0]] = entries_to_concepts[concept_entry]
        except KeyError:
            logger.warning(
                f"Concept {concept_entry} was not found. Please add it to the concepts table manually."
            )
            data[concept_column[0]] = concept_entry
        if "id" in implicit:
            data[implicit["id"]] = None
        if "languageReference" in implicit:
            data[implicit["languageReference"]] = sheet.title
        yield data


def read_single_excel_sheet(
    dataset: pycldf.Dataset,
    sheet: openpyxl.worksheet.worksheet.Worksheet,
    match_form: t.Optional[t.List[str]] = None,
    entries_to_concepts: t.Mapping[str, str] = KeyKeyDict(),
    concept_column: t.Optional[str] = None,
):
    concept_columns: t.Tuple[str, str]
    if concept_column is None:
        concept_columns = (
            dataset["FormTable", "parameterReference"].name,
            dataset["FormTable", "parameterReference"].name,
        )
    else:
        concept_columns = (
            dataset["FormTable", "parameterReference"].name,
            concept_column,
        )

    db = DB(dataset)
    db.cache_dataset()
    # required cldf fields
    c_f_id = db.dataset["FormTable", "id"].name
    c_f_language = db.dataset["FormTable", "languageReference"].name
    c_f_form = db.dataset["FormTable", "form"].name
    c_f_value = db.dataset["FormTable", "value"].name
    c_f_concept = db.dataset["FormTable", "parameterReference"].name
    if not match_form:
        match_form = [c_f_form, c_f_language]
    if not db.dataset["FormTable", c_f_concept].separator:
        match_form.append(c_f_concept)

    sheet_header = get_headers_from_excel(sheet)
    form_header = list(db.dataset["FormTable"].tableSchema.columndict.keys())

    # These columns don't need to be given, we can infer them from the sheet title and from the other data:
    implicit: t.Dict[t.Literal["languageReference", "id", "value"], str] = {}
    if c_f_language not in sheet_header:
        implicit["languageReference"] = c_f_language
    if c_f_id not in sheet_header:
        implicit["id"] = c_f_id
    if c_f_value not in sheet_header:
        implicit["value"] = c_f_value

    assert set(sheet_header) - {concept_column} - set(implicit.values()) == set(
        form_header
    ) - {c_f_concept} - set(
        implicit.values()
    ), f"The column headers in your Excel file sheet {sheet.title} ({sheet_header}) do not match the column headers from the database ({form_header})."

    # read new data from sheet
    for form in import_data_from_sheet(
        sheet,
        sheet_header=sheet_header,
        implicit=implicit,
        entries_to_concepts=entries_to_concepts,
        concept_column=concept_columns,
    ):
        for item, value in form.items():
            sep = db.dataset["FormTable", item].separator
            if sep is None:
                continue
            form[item] = value.split(sep)
        form_candidates = db.find_db_candidates(form, match_form)
        for form_id in form_candidates:
            logger.info(f"Form {form[c_f_value]} was already in data set.")

            if db.dataset["FormTable", c_f_concept].separator:
                if form[c_f_concept] not in db.cache[form_id][c_f_concept]:
                    db.cache[form_id][c_f_concept].append().form[c_f_concept]
                    logger.info(
                        f"Existing form {form_id} was added to concept form[c_f_concept]."
                    )
            break
        else:
            if "id" in implicit:
                # TODO: check for type of form id column
                form[c_f_id] = string_to_id(f"{form[c_f_language]}_{form[c_f_concept]}")
            db.make_id_unique(form)
            db.insert_into_db(form)
    # write to cldf
    db.write_dataset_from_cache()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Parse Excel file into CSV")
    parser.add_argument(
        "excel", type=openpyxl.load_workbook, help="The Excel file to parse"
    )
    parser.add_argument(
        "--metadata", type=Path, default="", help="Path to the metadata file"
    )
    parser.add_argument(
        "--concept-name",
        type=str,
        help="Column to interpret as concept names (default: assume the #parameterReference column, usually named 'Concept_ID' or similar, matches the IDs of the concept. Use this switch if you have concept Names in the wordlist instead.)",
    )
    parser.add_argument(
        "--sheet", type=str, action="append", help="Sheets to parse (default: all)"
    )
    parser.add_argument(
        "--match-form",
        type=str,
        nargs="*",
        default=[],
        help="Columns to match forms by",
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
    # initiate data set from meta data or csv depending on command line arguments
    if args.metadata:
        if args.metadata.name == "forms.csv":
            dataset = pycldf.Dataset.from_data(args.metadata)
        else:
            dataset = pycldf.Dataset.from_metadata(args.metadata)

    try:
        cid = dataset["ParameterTable", "id"].name
        if args.concept_name is None:
            concepts = {c[cid]: c[cid] for c in dataset["ParameterTable"]}
            concept_column = dataset["FormTable", "parameterReference"].name
        else:
            name = dataset["ParameterTable", "name"].name
            concepts = {c[name]: c[cid] for c in dataset["ParameterTable"]}
            concept_column = args.concept_name
    except KeyError:
        concepts = KeyKeyDict()
        concept_column = dataset["FormTable", "parameterReference"].name

    # import all selected sheets
    for sheet in args.sheet:
        read_single_excel_sheet(
            dataset=dataset,
            sheet=args.excel[sheet],
            match_form=args.match_form,
            entries_to_concepts=concepts,
            concept_column=concept_column,
        )

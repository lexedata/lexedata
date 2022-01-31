import typing as t
from pathlib import Path
from collections import defaultdict
from tabulate import tabulate

import attr
import openpyxl
import pycldf

from lexedata.util import (
    string_to_id,
    normalize_string,
)
from lexedata.util.excel import (
    clean_cell_value,
    normalize_header,
)
from lexedata.importer.excel_matrix import DB
from lexedata.types import Form, KeyKeyDict
from lexedata.edit.add_status_column import add_status_column_to_table
import lexedata.cli as cli


try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal


@attr.s(auto_attribs=True)
class ImportLanguageReport:
    is_new_language: bool = False
    new: int = 0
    existing: int = 0
    skipped: int = 0
    concepts: int = 0

    def __iadd__(self, other: "ImportLanguageReport"):
        self.is_new_language |= other.is_new_language
        self.skipped += other.skipped
        self.new += other.new
        self.existing += other.existing
        self.concepts += other.concepts
        return self

    def __call__(self, name: str) -> t.Tuple[str, int, int, int, int]:
        return (
            ("(new) " if self.is_new_language else "") + name,
            self.new,
            self.existing,
            self.skipped,
            self.concepts,
        )


def get_headers_from_excel(
    sheet: openpyxl.worksheet.worksheet.Worksheet,
) -> t.Iterable[str]:
    return normalize_header(r for c, r in enumerate(next(sheet.iter_rows(1, 1))))


def import_data_from_sheet(
    sheet,
    sheet_header,
    language_id: str,
    implicit: t.Mapping[Literal["languageReference", "id", "value"], str] = {},
    concept_column: t.Tuple[str, str] = ("Concept_ID", "Concept_ID"),
) -> t.Iterable[Form]:
    row_iter = sheet.iter_rows()

    # TODO?: compare header of this sheet to format of given dataset process
    # row. Maybe unnecessary. In any case, do not complain about the unused
    # variable.
    header = next(row_iter)  # noqa: F841

    assert (
        concept_column[1] in sheet_header
    ), f"Could not find concept column {concept_column[1]} in your excel sheet {sheet.title}."

    for row in row_iter:
        data = Form({k: clean_cell_value(cell) for k, cell in zip(sheet_header, row)})
        if "?" in data.values():
            continue
        if "value" in implicit:
            data[implicit["value"]] = "\t".join(map(str, data.values()))
        concept_entry = data.pop(concept_column[1])
        data[concept_column[0]] = concept_entry
        if "id" in implicit:
            data[implicit["id"]] = None
        if "languageReference" in implicit:
            data[implicit["languageReference"]] = language_id
        yield data


def read_single_excel_sheet(
    dataset: pycldf.Dataset,
    sheet: openpyxl.worksheet.worksheet.Worksheet,
    logger: cli.logging.Logger = cli.logger,
    match_form: t.Optional[t.List[str]] = None,
    entries_to_concepts: t.Mapping[str, str] = KeyKeyDict(),
    concept_column: t.Optional[str] = None,
    ignore_missing: bool = False,
    ignore_superfluous: bool = False,
    status_update: t.Optional[str] = None,
) -> t.Mapping[str, ImportLanguageReport]:
    report: t.Dict[str, ImportLanguageReport] = defaultdict(ImportLanguageReport)

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
    # required cldf fields of a form
    c_f_id = db.dataset["FormTable", "id"].name
    c_f_language = db.dataset["FormTable", "languageReference"].name
    c_f_form = db.dataset["FormTable", "form"].name
    c_f_value = db.dataset["FormTable", "value"].name
    c_f_concept = db.dataset["FormTable", "parameterReference"].name
    if not match_form:
        match_form = [c_f_form, c_f_language]
    if not db.dataset["FormTable", c_f_concept].separator:
        logger.warning(
            "Your metadata does not allow polysemous forms. According to your specifications, "
            "identical forms with different concepts will always be considered homophones, not a single "
            "polysemous form. To include polysemous forms, add a separator to your FormTable #parameterReference "
            "in the Metadata.json To find potential polysemies, run lexedata.report.list_homophones."
        )
        match_form.append(c_f_concept)
    else:
        if c_f_concept in match_form:
            logger.info(
                "Matching by concept enabled: To find potential polysemies, run lexedata.report.list_homophones."
            )

    sheet_header = get_headers_from_excel(sheet)
    form_header = list(db.dataset["FormTable"].tableSchema.columndict.keys())

    # These columns don't need to be given, we can infer them from the sheet title and from the other data:
    implicit: t.Dict[Literal["languageReference", "id", "value"], str] = {}
    if c_f_language not in sheet_header:
        implicit["languageReference"] = c_f_language
    if c_f_id not in sheet_header:
        implicit["id"] = c_f_id
    if c_f_value not in sheet_header:
        implicit["value"] = c_f_value

    found_columns = set(sheet_header) - {concept_column} - set(implicit.values())
    expected_columns = set(form_header) - {c_f_concept} - set(implicit.values())
    if not found_columns >= expected_columns:
        if ignore_missing:
            logger.info(
                f"Your Excel sheet {sheet.title} is missing columns {expected_columns - found_columns}. "
                f"For the newly imported forms, these columns will be left empty in the dataset."
            )
        else:
            raise ValueError(
                f"Your Excel sheet {sheet.title} is missing columns {expected_columns - found_columns}. "
                f"Clean up your data, or use --ignore-missing-excel-columns to import anyway and leave these "
                f"columns empty in the dataset for the newly imported forms."
            )
    if not found_columns <= expected_columns:
        if ignore_superfluous:
            logger.info(
                f"Your Excel sheet {sheet.title} contained unexpected columns "
                f"{found_columns - expected_columns}. These columns will be ignored."
            )
        else:
            raise ValueError(
                f"Your Excel sheet {sheet.title} contained unexpected columns "
                f"{found_columns - expected_columns}. Clean up your data, or use "
                f"--ignore-superfluous-excel-columns to import the data anyway and ignore these columns."
            )
    # check if language exist
    c_l_name = db.dataset["LanguageTable", "name"].name
    c_l_id = db.dataset["LanguageTable", "id"].name
    language_name_to_language_id = {
        row[c_l_name]: row[c_l_id] for row in db.cache["LanguageTable"].values()
    }
    language_name = normalize_string(sheet.title)
    if language_name in language_name_to_language_id:
        language_id = language_name_to_language_id[language_name]
        report[language_id].is_new_language = False
    else:
        language_id = language_name
        report[language_id].is_new_language = True

    # read new data from sheet
    for form in cli.tq(
        import_data_from_sheet(
            sheet,
            sheet_header=sheet_header,
            implicit=implicit,
            language_id=language_id,
            concept_column=concept_columns,
        ),
        task=f"Parsing cells of sheet {sheet.title}",
        total=sheet.max_row,
    ):
        # if concept not in dataset, don't add form
        try:
            concept_entry = form[c_f_concept]
            entries_to_concepts[concept_entry]
        except KeyError:
            logger.warning(
                f"Concept {concept_entry} was not found. Please add it to the concepts.csv file manually. "
                f"The corresponding form was ignored and not added to the dataset."
            )
            report[language_id].skipped += 1
            continue
        # else, look for candidates, link to existing form or add new form
        for item, value in form.items():
            try:
                sep = db.dataset["FormTable", item].separator
            except KeyError:
                continue
            if sep is None:
                continue
            form[item] = value.split(sep)
        form_candidates = db.find_db_candidates(form, match_form)
        if form_candidates:
            new_concept_added = False
            for form_id in form_candidates:
                logger.info(f"Form {form[c_f_value]} was already in dataset.")

                if db.dataset["FormTable", c_f_concept].separator:
                    for new_concept in form[c_f_concept]:
                        if (
                            new_concept
                            not in db.cache["FormTable"][form_id][c_f_concept]
                        ):
                            db.cache["FormTable"][form_id][c_f_concept].append(
                                new_concept
                            )
                            logger.info(
                                f"New form-concept association: Concept {form[c_f_concept]} was added to existing form "
                                f"{form_id}. If this was not intended "
                                f"(because it is a homophonous form, not a polysemy), "
                                f"you need to manually remove that concept from the old form in forms.csv "
                                f"and create a separate new form. If you want to treat identical forms "
                                f"as homophones in general, add  "
                                f"--match-forms={' '.join(match_form)}, "
                                f"{db.dataset['FormTable', 'parameterReference']} "
                                f"when you run this script."
                            )
                            new_concept_added = True
                break

            if new_concept_added:
                report[language_id].concepts += 1
            else:
                report[language_id].existing += 1
        else:
            # we land here after the break and keep adding existing forms to the dataset just with integer in id +1
            form[c_f_language] = language_id
            if "id" in implicit:
                # TODO: check for type of form id column
                form_concept = form[c_f_concept]
                concept_reference = (
                    form_concept[0] if isinstance(form_concept, list) else form_concept
                )
                form[c_f_id] = string_to_id(f"{form[c_f_language]}_{concept_reference}")
            db.make_id_unique(form)
            if status_update:
                form["Status_Column"] = status_update
            db.insert_into_db(form)
            report[language_id].new += 1
    # write to cldf
    db.write_dataset_from_cache()
    return report


def add_single_languages(
    metadata: Path,
    sheets: t.Iterable[openpyxl.worksheet.worksheet.Worksheet],
    match_form: t.Optional[t.List[str]],
    concept_name: t.Optional[str],
    ignore_missing: bool,
    ignore_superfluous: bool,
    status_update: t.Optional[str],
    logger: cli.logging.Logger,
) -> t.Mapping[str, ImportLanguageReport]:
    if status_update == "None":
        status_update = None
    # initiate dataset from meta data or csv depending on command line arguments
    if metadata:
        if metadata.name == "forms.csv":
            dataset = pycldf.Dataset.from_data(metadata)
        else:
            dataset = pycldf.Dataset.from_metadata(metadata)

    concepts: t.Mapping[str, str]
    try:
        cid = dataset["ParameterTable", "id"].name
        if concept_name is None:
            concepts = {c[cid]: c[cid] for c in dataset["ParameterTable"]}
            concept_column = dataset["FormTable", "parameterReference"].name
        else:
            name = dataset["ParameterTable", "name"].name
            concepts = {c[name]: c[cid] for c in dataset["ParameterTable"]}
            concept_column = concept_name
    except (KeyError, FileNotFoundError) as err:
        if isinstance(err, KeyError):
            logger.warning(
                "Did not find a well-formed ParameterTable. Importing all forms independent of concept"
            )
        elif isinstance(err, FileNotFoundError):
            logger.warning(
                f"Did not find {dataset['ParameterTable'].url.string}. "
                f"Importing all forms independent of concept"
            )
        concepts = KeyKeyDict()
        if concept_name:
            concept_column = concept_name
        else:
            concept_column = dataset["FormTable", "parameterReference"].name
    # add Status_Column if not existing and status_update given
    if status_update:
        add_status_column_to_table(dataset=dataset, table_name="FormTable")
    report: t.Dict[str, ImportLanguageReport] = defaultdict(ImportLanguageReport)
    # import all selected sheets
    for sheet in sheets:
        for lang, subreport in read_single_excel_sheet(
            dataset=dataset,
            sheet=sheet,
            logger=logger,
            match_form=match_form,
            entries_to_concepts=concepts,
            concept_column=concept_column,
            ignore_missing=ignore_missing,
            ignore_superfluous=ignore_superfluous,
            status_update=status_update,
        ).items():
            report[lang] += subreport
    return report


if __name__ == "__main__":
    parser = cli.parser(
        description="Import forms and associated metadata from an excel file to a cldf dataset."
    )
    parser.add_argument(
        "excel",
        type=openpyxl.load_workbook,
        help="The Excel file to parse",
        metavar="EXCEL",
    )
    parser.add_argument(
        "--concept-name",
        type=str,
        help="Column to interpret as concept names "
        "By default, it is assumed that the #parameterReference column, usually named 'Concept_ID' "
        "or similar, matches the IDs of the concept. Use this "
        "switch if instead of concept IDs you have concept Names in the excel file instead.",
        metavar="COLUMN",
    )
    parser.add_argument(
        "--sheets",
        type=str,
        nargs="+",
        metavar="SHEET_NAME",
        help="Sheets to parse. (default: all sheets)",
    )
    parser.add_argument(
        "--match-form",
        "-f",
        type=str,
        nargs="+",
        default=[],
        metavar="COLUMN_NAME",
        help="Forms are considered identical if all columns passed to -f/--match-form are identical",
    )
    parser.add_argument(
        "--ignore-superfluous-columns",
        "-s",
        action="store_true",
        default=False,
        help="Ignore columns in the Excel table which are not in the dataset",
    )
    parser.add_argument(
        "--ignore-missing-columns",
        "-m",
        action="store_true",
        default=False,
        help="Ignore columns missing from the Excel table compared to the dataset",
    )
    parser.add_argument(
        "--exclude-sheet",
        "-x",
        type=str,
        nargs="*",
        default=[],
        metavar="SHEET_NAME",
        help="Sheets not to parse. Does not affect sheets explicitly added using --sheet.",
    )
    parser.add_argument(
        "--status-update",
        type=str,
        default="new import",
        help="Text written to Status_Column. Set to 'None' for no status update. "
        "(default: new import)",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        default=False,
        help="Prints report of newly added forms",
    )

    args = parser.parse_args()
    logger = cli.setup_logging(args)

    if not args.sheets:
        sheets = [
            sheet for sheet in args.excel if sheet.title not in args.exclude_sheet
        ]
        logger.info("No sheets specified explicitly. Parsing sheets: %s", args.sheets)
    else:
        sheets = [args.excel[s] for s in args.sheets]

    report = add_single_languages(
        metadata=args.metadata,
        sheets=sheets,
        match_form=args.match_form,
        concept_name=args.concept_name,
        ignore_missing=args.ignore_missing_excel_columns,
        ignore_superfluous=args.ignore_superfluous_excel_columns,
        status_update=args.status_update,
        logger=logger,
    )
    if args.report:
        report_data = [report(language) for language, report in report.items()]
        print(
            tabulate(
                report_data,
                headers=[
                    "LanguageID",
                    "New forms",
                    "Existing forms",
                    "Skipped forms",
                    "New concept reference",
                ],
                tablefmt="orgtbl",
            )
        )

# -*- coding: utf-8 -*-
import csv
import typing as t
from pathlib import Path

import pycldf

from lexedata.exporter.cognates import BaseExcelWriter
from lexedata import cli, types


class MatrixExcelWriter(BaseExcelWriter):
    """Class logic for Excel matrix export."""

    row_table = "ParameterTable"

    def __init__(
        self,
        dataset: pycldf.Dataset,
        database_url: t.Optional[str] = None,
    ):
        super().__init__(dataset=dataset, database_url=database_url)

    def set_header(self):
        try:
            c_id = self.dataset["ParameterTable", "id"].name
            self.header = [(c_id, "ID")]
        except KeyError:
            c_id = self.dataset["FormTable", "parameterReference"].name
            self.header = [(c_id, "ID")]
        try:
            c_name = self.dataset["ParameterTable", "name"].name
            self.header.append((c_name, "Name"))
        except KeyError:
            pass

        try:
            c_concepticon = self.dataset["ParameterTable", "name"].name
            self.header.append((c_concepticon, "Concepticon"))
        except KeyError:
            pass

    def collect_forms_by_row(self) -> t.Mapping[types.Parameter_ID, t.List[types.Form]]:
        all_forms: t.MutableMapping[
            types.Parameter_ID, t.List[types.Form]
        ] = t.DefaultDict(list)
        c_f_row_reference = self.dataset["FormTable", "parameterReference"].name
        for row in self.dataset["FormTable"]:
            all_forms[row[c_f_row_reference]].append(row)
        return all_forms

    def form_to_cell_value(self, form: types.Form) -> str:
        # TODO: Placeholder, use proper structure here.
        return form["Unified_Form"]

    def collect_rows(self):
        return list(self.dataset["ParameterTable"])

    def after_filling(self):
        pass


if __name__ == "__main__":
    parser = cli.parser(description="Create an Excel matrix view from a CLDF dataset")
    parser.add_argument(
        "excel",
        type=Path,
        help="File path for the generated cognate excel file.",
    )
    parser.add_argument(
        "--concept-list",
        type=Path,
        help="Output only the concepts listed in this file. I assume that CONCEPT_LIST is a CSV file, and the first comma-separated column contains the ID.",
    )
    parser.add_argument(
        "--sort-languages-by",
        help="The name of a column in the LanguageTable to sort languages by in the output",
    )
    parser.add_argument(
        "--url-template",
        type=str,
        default="https://example.org/lexicon/{:}",
        help="A template string for URLs pointing to individual forms. For example, to"
        " point to lexibank, you would use https://lexibank.clld.org/values/{:}."
        " (default: https://example.org/lexicon/{:})",
    )
    args = parser.parse_args()
    logger = cli.setup_logging(args)

    concept_list = None
    if args.concept_list:
        if not args.concept_list.exists():
            logger.critical("Concept list file %s not found.", args.concept_list)
            cli.Exit.FILE_NOT_FOUND()
        concept_list = []
        for c, concept in enumerate(csv.reader(args.concept_list.open())):
            first_column = concept[0]
            if c == 0:
                logger.info(
                    "Reading concept IDs from column with header %s", first_column
                )
            else:
                concept_list.append(first_column)

    E = MatrixExcelWriter(
        pycldf.Wordlist.from_metadata(args.metadata),
        database_url=args.url_template,
    )
    E.create_excel(
        args.excel,
        language_order=args.sort_languages_by,
        rows=concept_list,
    )

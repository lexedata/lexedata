# -*- coding: utf-8 -*-
import re
import typing as t
from pathlib import Path

import pycldf
import openpyxl as op

from lexedata.exporter.cognates import BaseExcelWriter
from lexedata import cli, types, util


class MatrixExcelWriter(BaseExcelWriter):
    """Class logic for Excel matrix export."""

    row_table = "ParameterTable"

    def __init__(
        self,
        dataset: pycldf.Dataset,
        database_url: t.Optional[str] = None,
        logger: cli.logging.Logger = cli.logger,
    ):
        super().__init__(dataset=dataset, database_url=database_url, logger=logger)

    def set_header(self):
        self.header = [("id", "ID")]
        self.header.append(("name", "Name"))

        try:
            self.dataset["ParameterTable", "concepticonReference"].name
            self.header.append(("concepticonReference", "Concepticon"))
        except KeyError:
            pass

    def collect_forms_by_row(self) -> t.Mapping[types.Parameter_ID, t.List[types.Form]]:
        all_forms: t.MutableMapping[
            types.Parameter_ID, t.List[types.Form]
        ] = t.DefaultDict(list)
        for form in util.cache_table(self.dataset).values():
            for row in util.ensure_list(form["parameterReference"]):
                all_forms[row].append(form)
        return all_forms

    def form_to_cell_value(self, form: types.Form) -> str:
        # TODO: Placeholder, use proper structure here.
        return form["form"]

    def after_filling(self, row_index: int):
        pass

    def write_row_header(self, cogset, row):
        try:
            c_comment = self.dataset["ParameterTable", "comment"].name
        except (KeyError):
            c_comment = None
        for col, (db_name, header) in enumerate(self.header, 1):
            if db_name == "":
                continue
            column = self.dataset[self.row_table, db_name]
            if column.separator is None:
                value = cogset[db_name]
            else:
                value = column.separator.join([str(v) for v in cogset[db_name]])
            cell = self.ws.cell(row=row, column=col, value=value)
            # Transfer the cognateset comment to the first Excel cell.
            if c_comment and col == 1 and cogset.get(c_comment):
                cell.comment = op.comments.Comment(
                    re.sub(f"-?{__package__}", "", cogset[c_comment] or "").strip(),
                    "lexedata.exporter",
                )


if __name__ == "__main__":
    parser = cli.parser(description="Create an Excel matrix view from a CLDF dataset")
    parser.add_argument(
        "excel",
        type=Path,
        help="File path for the generated cognate excel file.",
    )
    parser.add_argument(
        "--concepts",
        action=cli.ListOrFromFile,
        help="Concepts to output.",
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

    E = MatrixExcelWriter(
        pycldf.Wordlist.from_metadata(args.metadata),
        database_url=args.url_template,
        logger=logger,
    )
    E.create_excel(
        args.excel,
        language_order=args.sort_languages_by,
        rows=args.concepts,
    )
    E.wb.save(
        filename=args.excel,
    )

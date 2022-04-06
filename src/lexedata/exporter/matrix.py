# -*- coding: utf-8 -*-
import re
import typing as t
import urllib
from pathlib import Path

import openpyxl as op
import pycldf

from lexedata import cli, types, util
from lexedata.exporter.cognates import BaseExcelWriter


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

    def set_header(self, dataset):
        self.header = [("id", "ID")]
        self.header.append(("name", "Name"))

        try:
            dataset["ParameterTable", "concepticonReference"].name
            self.header.append(("concepticonReference", "Concepticon"))
        except KeyError:
            pass

    def form_to_cell_value(self, form: types.Form) -> str:
        # TODO: Placeholder, use proper structure here.
        return form["form"]

    def write_row_header(self, cogset, row):
        for col, (db_name, header) in enumerate(self.header, 1):
            if db_name == "":
                continue
            try:
                value = self.separators[db_name].join([str(v) for v in cogset[db_name]])
            except KeyError:
                # No separator
                value = cogset.get(db_name, "")
            cell = self.ws.cell(row=row, column=col, value=value)
            # Transfer the cognateset comment to the first Excel cell.
            if col == 1 and cogset.get("comment"):
                cell.comment = op.comments.Comment(
                    re.sub(f"-?{__package__}", "", cogset["comment"] or "").strip(),
                    "lexedata.exporter",
                )

    def create_formcell(self, form: types.Form, column: int, row: int) -> None:
        """Fill the given cell with the form's data.

        In the cell described by ws, column, row, dump the data for the form:
        Write into the the form data, and supply a comment from the judgement
        if there is one.

        """
        form, metadata = form
        cell_value = self.form_to_cell_value(form)
        form_cell = self.ws.cell(row=row, column=column, value=cell_value)
        comment = form.pop("comment", None)
        if comment:
            form_cell.comment = op.comments.Comment(comment, __package__)
        if self.URL_BASE:
            link = self.URL_BASE.format(urllib.parse.quote(form["id"]))
            form_cell.hyperlink = link


if __name__ == "__main__":
    parser = cli.parser(
        __package__ + "." + Path(__file__).stem,
        description="Create an Excel matrix view from a CLDF dataset",
    )
    parser.add_argument(
        "excel",
        type=Path,
        help="File path for the generated cognate excel file.",
    )
    parser.add_argument(
        "--concepts",
        action=cli.SetOrFromFile,
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

    dataset = (pycldf.Wordlist.from_metadata(args.metadata),)
    E = MatrixExcelWriter(
        dataset,
        database_url=args.url_template,
        logger=logger,
    )
    forms = util.cache_table(dataset)
    languages = sorted(
        util.cache_table(dataset, "LanguageTable").values(), key=lambda x: x["name"]
    )
    judgements = [
        {"formReference": f["id"], "cognatesetReference": parameter}
        for f in forms.values()
        for parameter in util.ensure_list(f["parameterReference"])
    ]
    parameters = util.cache_table(dataset, "ParameterTable").values()
    E.create_excel(
        rows=parameters, judgements=judgements, forms=forms, languages=languages
    )
    E.wb.save(
        filename=args.excel,
    )

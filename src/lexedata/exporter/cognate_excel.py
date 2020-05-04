# -*- coding: utf-8 -*-
import urllib.parse
from pathlib import Path
from typing import Dict, DefaultDict, List

import sqlalchemy
import openpyxl as op

from lexedata.importer.objects import Form, CogSet, Language
from lexedata.importer.database import create_db_session
from lexedata.importer.exceptions import CellParsingError

WARNING = "\u26A0"

# ----------- Remark: Indices in excel are always 1-based. -----------


class ExcelWriter():
    """Class logic for cognateset Excel export."""
    def __init__(self):
        self.URL_BASE = "https://example.org/{:s}"

    def create_excel(
            self,
            out: Path,
            db_session: sqlalchemy.orm.session.Session) -> None:
        """Convert the CLDF behind db_session into an Excel cognate view

        The Excel file has columns "CogSet", "Tags", and then one column per
        language.

        The rows contain cognate data. If a language has multiple reflexes in
        the same cognateset, these appear in different cells, one below the
        other.

        Parameters
        ==========
        out: The path of the Excel file to be written.
        db_session: An SQLAlchemy database session connecting to a standardized
            CLDF dataset.

        """
        # TODO: Check whether openpyxl.worksheet._write_only.WriteOnlyWorksheet
        # will be useful:
        # https://openpyxl.readthedocs.io/en/stable/optimized.html#write-only-mode
        wb = op.Workbook()
        ws: op.worksheet.worksheet.Worksheet = wb.active

        languages = db_session.query(Language).all()

        # Define the columns
        header = ["CogSet", "Tags"]
        lan_dict = dict()
        for col, lan in enumerate(languages, 3):
            # Excel indices are 1-based, not zero-based, so 3 is column C, as
            # intended.
            lan_dict[lan.id] = col
            header.append(lan.name)

        ws.append(header)

        # Iterate over all cognate sets, and prepare the rows.
        # Again, row_index 2 is indeed row 2, because indices are 1-based.
        row_index = 2
        for cogset in db_session.query(CogSet):
            # Create cell for cogset in column A
            cogset_cell = ws.cell(row=row_index, column=1, value=cogset.id)
            # Transfer the cognateset comment to the Excel cell comment.
            if cogset.description != "":
                cogset_cell.comment = op.comments.Comment(
                    cogset.description, __package__)

            # Put the cognateset's tags in column B.
            ws.cell(row=row_index, column=2, value=cogset.set)

            new_row_index = self.create_formcells_for_cogset(
                cogset, ws, row_index, lan_dict)
            assert new_row_index > row_index, ("""
            There can, by the data model, be cognate sets with no judgements,
            but create_formcells_for_cogset did not increase the row index.""")
            row_index = new_row_index
        wb.save(filename=out)

    def create_formcells_for_cogset(
            self,
            cogset: CogSet,
            ws: op.worksheet.worksheet.Worksheet,
            row_index: int,
            # FIXME: That's not just a str, it's a Language_ID, but String()
            # alias Language.id.type is not a Type, according to `typing`.
            language_columns: Dict[str, int]) -> int:
        """Writes all forms for given cognate set to Excel.

        Take all forms for a given cognate set as given by the database, create
        a hyperlink cell for each form, and write those into rows starting at
        row_index.

        Return the row number of the first empty row after this cognate set,
        which can then be filled by the following cognate set.

        """
        # skip this row, if no judgements given
        if not cogset.judgements:
            row_index += 1
            return row_index

        # Read the forms from the database and group them by language
        forms = DefaultDict[int, List[Form]](list)
        for judgement in cogset.judgements:
            form: Form = judgement.form
            comment: str = judgement.procedural_comment
            forms[language_columns[form.language]].append((form, comment))
        # maximum of rows to be added
        maximum_cogset = max([len(c) for c in forms.values()])
        for column, cells in forms.items():
            for row, form in enumerate(cells, row_index):
                self.create_formcell(form, comment, ws, column, row)
        # increase row_index and return
        row_index += maximum_cogset
        return row_index

    def create_formcell(
            self,
            form: Form,
            procedural_comment: str,
            ws: op.worksheet.worksheet.Worksheet,
            column: int,
            row: int) -> None:
        """Fill the given cell with the form's data.

        In the cell described by ws, column, row, dump the data for the form:
        Write into the the form data, and supply a comment from the judgement
        if there is one.

        """
        cell_value = self.form_to_cell_value(form)
        form_cell = ws.cell(row=row, column=column, value=cell_value)
        if procedural_comment:
            comment = procedural_comment
            form_cell.comment = op.comments.Comment(comment, __package__)
        link = self.URL_BASE.format(urllib.parse.quote(form.id))
        print(cell_value, link)
        form_cell.hyperlink = link

    def form_to_cell_value(self, form: Form) -> str:
        """Build a string describing the form itself

        Provide the best transcription and all translations of the form strung
        together.

        """
        transcription = self.get_best_transcription(form)
        suffix = ""
        translations = []

        # iterate over corresponding concepts
        for form_to_concept in form.concepts:
            if form_to_concept.procedural_comment:
                suffix = f" {WARNING:}"
            translations.append(form_to_concept.concept.english)

        return "{:} ‘{:}’{:}".format(
            transcription, ", ".join(translations), suffix)

    def get_best_transcription(self, form):
        if form.phonemic:
            return form.phonemic
        elif form.phonetic:
            return form.phonetic
        elif form.orthographic:
            return form.orthographic
        else:
            ValueError(f"Form {form:} has no transcriptions.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Create an Excel cognate view from a CLDF dataset")
    parser.add_argument("sqlite", help="SQlite input")
    parser.add_argument("excel", help="Excel output file path")
    args = parser.parse_args()
    E = ExcelWriter()
    E.create_excel(args.excel, create_db_session(args.sqlite))

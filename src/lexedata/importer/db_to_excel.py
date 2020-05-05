# -*- coding: utf-8 -*-
from typing import Dict
from pathlib import Path
from collections import defaultdict, OrderedDict

import sqlalchemy
import openpyxl as op
import unidecode as uni

from lexedata.importer.objects import Form, CogSet, Language
from lexedata.importer.database import create_db_session
from lexedata.importer.exceptions import CellParsingError

WARNING = "\u26A0"
URL_BASE = r"https://myhost.com"

# ----------- Remark: Indices in excel are always 1-based. -----------


def create_excel(out: Path, db_session: sqlalchemy.orm.session.Session) -> None:
    """Convert the CLDF behind db_session into an Excel cognate view

    The Excel file has columns "CogSet", "Tags", and then one column per
    language.

    The rows contain cognate data. If a language has multiple reflexes in the
    same cognateset, these appear in different cells, one below the other.

    Parameters
    ==========
    out: The path of the Excel file to be written.
    db_session: A SQLAlchemy database session connecting to a standardized CLDF
        dataset.

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

        new_row_index = create_formcells_for_cogset(
            cogset, ws, row_index, lan_dict)
        assert new_row_index > row_index, ("""
        There can, by the data model, be cognate sets with no judgements, but
        create_formcells_for_cogset did not increase the row index.""")
        row_index = new_row_index
    wb.save(filename=out)


def create_formcells_for_cogset(
        cogset: CogSet,
        ws: op.worksheet.worksheet.Worksheet,
        row_index: int,
        language_columns: Dict[str, int]) -> int:
    """Writes all forms for given cognate set to Excel.

    Take all forms for a given cognate set as given by the database, create a
    hyperlink cell for each form, and write those into rows starting at
    row_index.

    Return the row number of the first empty row after this cognate set, which
    can then be filled by the following cognate set.

    """
    # skip this row, if no judgements given
    if not cogset.judgements:
        row_index += 1
        return row_index

    # get sorted version of judgements for this cogset, language with maximum of forms first
    row_dict = defaultdict(list)
    for judgement in cogset.judgements:
        row_dict[judgement.language_id].append(judgement)
    ordered_dict = OrderedDict(sorted(row_dict.items(), key=lambda t: len(t[1]), reverse=True))
    # maximum of rows to be added
    maximum_cogset = len(ordered_dict[next(iter(ordered_dict.keys()))])
    for i in range(maximum_cogset):
        this_row = row_index + i
        for k, v in list(ordered_dict.items()):
            this_judgement = v.pop(0)
            # if it was last form, remove this language from dict
            if len(v) == 0:
                del ordered_dict[k]
            # create cell for this judgement
            create_formcell(this_judgement, ws, this_row, lan_dict[k])
    # increase row_index and return
    row_index += (maximum_cogset)
    return row_index


def create_formcell(judgement, ws, row, col):
    "Creates formcell for judgment in ws at row, col. With Return None"
    form = judgement.form
    cell_value = form_to_cell_value(form)
    form_cell = ws.cell(row=row, column=col, value=cell_value)
    if judgement.procedural_comment != "":
        comment = judgement.procedural_comment
        form_cell.comment = op.comments.Comment(comment, "lexicaldata")
    my_formid = uni.unidecode(form.id)  # no illegal characters in URL
    link = "{}/{}".format(URL_BASE, form.id)
    print(cell_value)
    form_cell.hyperlink = link


def form_to_cell_value(form):
    "returns cell value of formcell: best transcription +  all translations"
    transcription = get_best_transcription(form)
    mywarning = ""
    translations = []

    # iterate over corresponding concepts
    for form_to_concept in form.toconcepts:
        if form_to_concept.procedural_comment != "":
            mywarning = WARNING
        translations.append(form_to_concept.concept.english)
    translations = " ".join(translations)

    return " ".join([transcription, translations, mywarning])


def get_best_transcription(form):
    if form.phonemic != "":
        return form.phonemic
    elif form.phonetic != "":
        return form.phonetic
    elif form.orthographic != "":
        return form.orthographic
    else:
        CellParsingError("empty values ''", form.id)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Create an Excel cognate view from a CLDF dataset")
    parser.add_argument("excel", help="Excel output file path")
    parser.add_argument("sqlite", help="SQlite input")
    args = parser.parse_args()
    create_excel(args.excel, create_db_session(args.sqlite))

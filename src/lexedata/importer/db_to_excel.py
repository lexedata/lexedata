# -*- coding: utf-8 -*-

import openpyxl as op

from lexedata.importer.objects import Form, CogSet, Language
from lexedata.importer.database import DATABASE_ORIGIN, connect_db
from lexedata.importer.exceptions import CellParsingError

WARNING = "\u26A0"
URL_BASE = ""


def create_excel(out, db_path=DATABASE_ORIGIN):
    wb = op.Workbook()
    ws = wb.active

    session = connect_db(location=db_path)
    languages = session.query(Language).all()

    header = ["Cogset", "Tags"]
    # mapping language.id : excel column
    lan_dict = dict()
    for col, lan in enumerate(languages, 3):
        lan_dict[lan.id] = col
        header.append(lan.name)

    ws.append(tuple(header))

    row_index = 2
    for cogset in session.query(CogSet):
        cogset_cell = ws.Cell(row=row_index, column=1, value=cogset.id)
        if cogset.description != "":
            cogset_cell.comment.text = cogset.description
        tag_cell = ws.Cell(row=row_index, column=2, value=cogset.set)


def render_judgement_for_cogset(cogset, ws, row_index, lan_dict):
    for judgement in cogset.judgements:
        # TODO check if multiple judgments for a languag for given cogset -> modify row_index
        pass


def create_formcell(form, judgement, ws, row, col):
    cellvalue = form_to_cell_value(form)
    formcell = ws.Cell(row=row, column=col, value=cellvalue)
    comment = judgement.procedural_commen
    formcell.comment.text = comment
    link = "{}/{}".format(URL_BASE, form.id)
    formcell.hyperlink(link)


def form_to_cell_value(form):
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
    session = connect_db()
    for cogset in session.query(CogSet).all():
        print(cogset)
        print(cogset.judgements)
        input()


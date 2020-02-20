# -*- coding: utf-8 -*-
import openpyxl as op
import csv
import re
from collections import defaultdict
import argparse
import pycldf
import attr

from .exceptions import *
from .cellparser import CellParser
from .database import create_db_session, as_declarative, DatabaseObjectWithUniqueStringID, sa
from .objects import Language, Form, Concept, FormConceptAssociation

#replacing none values with ''
replace_none = lambda x: "" if x == None else x

#lambda function for getting comment of excel cell if comment given
replace_none_comment = lambda x: x.content if x  else ""
comment_getter = lambda x: replace_none_comment(x.comment)

# replacing none values with ''
replace_none = lambda x: "" if x == None else x

# lambda function for getting comment of excel cell if comment given
replace_none_comment = lambda x: x.content if x else ""
comment_getter = lambda x: replace_none_comment(x.comment)

# functions for bracket checking
one_bracket = lambda opening, closing, str, nr: str[0] == opening and str[-1] == closing and \
                                                (str.count(opening) == str.count(closing) == nr)
comment_bracket = lambda str: str.count("(") == str.count(")")

# header for files
header_forms = ["form_id", "language_id",
                "phonemic", "phonetic", "orthography", "variants", "source", "form_comment",
                "concept_comment"]

header_concepts = ["concept_id",
                   "set", "english", "english_strict", "spanish", "portuguese", "french", "concept_comment"]

header_languages = ["language_id",
                    "language_name", "curator", "language_comment"]


# header_form_concept = ["form_id", "concept_id"]

session = create_db_session()

def row_to_concept(conceptrow):
    # values of cell
    set, english, english_strict, spanish, portugese, french = [cell.value for cell in conceptrow]
    # comment of cell
    concept_comment = comment_getter(conceptrow[1])
    # create id
    concept_id = Concept.register_new_id(Concept.string_to_id(english))
    return Concept(id=concept_id, set=set, english=english,
                   english_strict=english_strict, spanish=spanish,
                   portuguese=portugese, french=french,
                   concept_comment=concept_comment, coordinates="??")


def create_form(form_id, lan_id, con_com, form_com, values, coordinates):
    phonemic, phonetic, ortho, comment, source = values

    variants = []
    phonemic = Form.variants_separator(variants, phonemic)
    phonetic = Form.variants_separator(variants, phonetic)
    ortho = Form.variants_separator(variants, ortho)

    if phonemic != "" and phonemic != "No value":
        if not one_bracket("/", "/", phonemic, 2):
            raise FormCellError(coordinates, phonemic, "phonemic")
        # phonemic = phonemic.strip("/")

    if phonetic != "" and phonetic != "No value":
        if not one_bracket("[", "]", phonetic, 1):
            raise FormCellError(coordinates, phonetic, "phonetic")
        # phonetic = phonetic.strip("[").strip("]")

    if ortho != "" and ortho != "No value":
        if not one_bracket("<", ">", ortho, 1):
            raise FormCellError(coordinates, ortho, "orthographic")
        # ortho = ortho.strip("<").strip(">")

    if comment != "" and comment != "No value":
        if not comment_bracket(comment):
            raise FormCellError(coordinates, comment, "comment")

    # replace source if not given
    source = "{1}" if source == "" else source

    return Form(id=form_id, language_id=lan_id, phonemic=phonemic, phonetic=phonetic, orthographic=ortho,
                    variants=variants, comment=comment, source=source,
                    form_comment=form_com)


def language_from_column(column):
    name, curator = [cell.value for cell in column]
    id = Language.register_new_id(Language.string_to_id(name))
    return Language(id=id, name=name, curator=curator, comments="", coordinates="??")




def main():
    parser = argparse.ArgumentParser(description="Load a Maweti-Guarani-style dataset into CLDF")
    parser.add_argument(
        "path", nargs="?",
        default="./Copy of TG_comparative_lexical_online_MASTER.xlsx",
        help="Path to an Excel file containing the dataset")
    parser.add_argument(
        "output", nargs="?",
        default="./",
        help="Directory to create the output CLDF wordlist in")
    parser.add_argument(
        "--debug-level", type=int, default=0,
        help="Debug level: Higher numbers are less forgiving")
    args = parser.parse_args()

    wb = op.load_workbook(filename=args.path)
    sheets = wb.sheetnames

    iter_forms = wb[sheets[0]].iter_rows(min_row=3, min_col=7, max_col=44)  # iterates over rows with forms

    iter_concept = wb[sheets[0]].iter_rows(min_row=3, max_col=6)  # iterates over rows with concepts

    with open("forms_ms.csv", "w", encoding="utf8", newline="") as formsout, \
            open("concepts_ms.csv", "w", encoding="utf8", newline="") as conceptsout, \
            open("languages_ms.csv", "w", encoding="utf8", newline="") as lanout:

        formscsv = csv.DictWriter(formsout, header_forms, extrasaction="ignore", quotechar='"',
                                  quoting=csv.QUOTE_MINIMAL)
        formscsv.writeheader()

        concsv = csv.DictWriter(conceptsout, header_concepts, extrasaction="ignore", quotechar='"',
                                quoting=csv.QUOTE_MINIMAL)
        concsv.writeheader()

        lancsv = csv.DictWriter(lanout, header_languages, extrasaction="ignore", quotechar='"',
                                quoting=csv.QUOTE_MINIMAL)
        lancsv.writeheader()

        # Collect languages
        languages = {}
        # TODO: The following line contains a magic number, can we just iterate until we are done?
        for lan_col in wb[sheets[0]].iter_cols(min_row=1, max_row=2, min_col=7, max_col=44):
            # iterate over language columns
            lan_cell = Language.from_column(lan_col)
            session.add(lan_cell)

            # Switch to warnings module or something similar for this
            if args.debug_level >= 2:
                lan_cell.warn()
            elif args.debug_level == 1:
                try:
                    lan_cell.warn()
                except LanguageElementError as E:
                    print(E)
                    continue

            languages[lan_cell.name] = lan_cell

            lancsv.writerow(lan_cell)
        session.commit()

        formcells = []
        for row_forms, row_con in zip(iter_forms, iter_concept):

            concept_cell = row_to_concept(row_con)
            con_comment = concept_cell.concept_comment

            concsv.writerow(concept_cell)

            for i, f_cell in enumerate(row_forms):
                if f_cell.value:

                    # you can access the cell's column letter and just add 1
                    this_lan_name = wb[sheets[0]][(f_cell.column_letter + "1")].value
                    this_lan_id = languages[this_lan_name].id
                    f_comment = comment_getter(f_cell)

                    try:

                        for f_ele in CellParser(f_cell):
                            f_ele = [replace_none(e) for e in f_ele]

                            form_id = Form.id_creator(this_lan_id, concept_cell.id)

                            c_form = create_form(
                                form_id = form_id,
                                lan_id = this_lan_id,
                                con_com = con_comment,
                                form_com = f_comment,
                                values = f_ele,
                                coordinates = f_cell.coordinate)
                            formcells.append(c_form)
                            formscsv.writerow(c_form)

                    except CellParsingError as err:
                        print("CellParsingError - somethings quite wrong")
                        print(err.message)
                        input()



                    except FormCellError as err:
                        print(("original cell content: - " + f_cell.value))
                        print(("failed form element: - " + str(f_ele)))
                        print(err)
                        input()

        #################################################
        # create cldf
        dataset = pycldf.Wordlist.in_dir(args.output)

        dataset.add_component("LanguageTable")
        dataset.write(LanguageTable=list(languages.values()), FormTable=formcells)

if False:
    # For debugging purposes:
    import sys
    import importlib
    import lexedata.importer.database
    import lexedata.importer.objects
    __package__ = "lexedata.importer"
    sys.argv = ["x", "../../../Copy of TG_comparative_lexical_online_MASTER.xlsx"]

    importlib.reload(lexedata.importer.database)
    importlib.reload(lexedata.importer.objects)

if __name__ == '__main__':
    main()

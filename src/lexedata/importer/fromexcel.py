# -*- coding: utf-8 -*-
import openpyxl as op
import csv
from pathlib import Path
from objects import *
from cellparser import *



def init_lan(dir_path, lan_iter, lan_dict):
    header_languages = ["ID", "Name", "Curator", "Comment", "iso639p3", "Excel_name"]
    with (dir_path / "lan_init.csv").open("w", encoding="utf8", newline="") as lanout:
        lancsv = csv.DictWriter(lanout, header_languages, extrasaction="ignore", quotechar='"',
                                quoting=csv.QUOTE_MINIMAL)
        lancsv.writeheader()
        for lan_col in lan_iter:
            # iterate over language columns
            lan_cell = Language.from_column(lan_col)
            lan_dict[lan_cell.Excel_name] = lan_cell.ID
            lancsv.writerow(lan_cell)


def init_con_form(dir_path, con_iter, form_iter, lan_dict, wb):

    with (dir_path / "form_init.csv").open( "w", encoding="utf8", newline="") as formsout, \
            (dir_path / "concept_init.csv").open( "w", encoding="utf8", newline="") as conceptsout:

        header_concepts = ["ID",
                           "Set", "English", "English_Strict", "Spanish", "Portuguese", "French"]
        concsv = csv.DictWriter(conceptsout, header_concepts, extrasaction="ignore", quotechar='"',
                                quoting=csv.QUOTE_MINIMAL)
        concsv.writeheader()

        header_forms = ["ID", "Language_ID",
                        "Phonemic", "Phonetic", "Orthographic", "Variants", "Form_Comment", "Source",
                        "Procedural_Comment", "Procedural_Comment_Concept", "Concept_ID"]

        formscsv = csv.DictWriter(formsout, header_forms, extrasaction="ignore", quotechar='"',
                                  quoting=csv.QUOTE_MINIMAL)
        formscsv.writeheader()

        for row_forms, row_con in zip(form_iter, con_iter):

            concept_cell = Concept.from_default_excel(row_con)
            concsv.writerow(concept_cell)

            for f_cell in row_forms:
                if f_cell.value:
                    # get corresponding language_id to column
                    this_lan_id = lan_dict[wb[(f_cell.column_letter + "1")].value]

                    try:
                        for f_ele in CellParser(f_cell):
                            form_cell = Form.create_form(f_ele, this_lan_id, f_cell, concept_cell)
                            formscsv.writerow(form_cell)

                    except CellParsingError as err:
                        print("CellParsingError - somethings quite wrong")
                        print(err.message)
                        #input()

                    except FormCellError as err:
                        print(err)
                        #input()


def initialize_lexical(dir_path, lan_dict,
                       file=r"C:\Users\walter.fuchs\Desktop\outofasia\stuff\TG_comparative_lexical_online_MASTER.xlsx"):

    wb = op.load_workbook(filename=file)
    sheets = wb.sheetnames
    wb = wb[sheets[0]]
    iter_forms = wb.iter_rows(min_row=3, min_col=7, max_col=44)  # iterates over rows with forms
    iter_concept = wb.iter_rows(min_row=3, max_col=6)  # iterates over rows with concepts
    iter_lan = wb.iter_cols(min_row=1, max_row=2, min_col=7, max_col=44)

    init_lan(dir_path, iter_lan, lan_dict)
    init_con_form(dir_path, iter_concept, iter_forms, lan_dict, wb)


def cogset_cognate(dir_path, cogset_iter, cog_iter, lan_dict, wb):
    with (dir_path / "cog_init.csv").open("w", encoding="utf8", newline="") as cogout, \
            (dir_path / "cogset_init.csv").open("w", encoding="utf8", newline="") as cogsetout:

        header_cog = ["ID", "CogSet_ID", "Form_ID",
                      "Cognate_Comment", "Phonemic", "Phonetic", "Orthographic",  "Source"]
        cogcsv = csv.DictWriter(cogout, header_cog, extrasaction="ignore", quotechar='"',
                                quoting=csv.QUOTE_MINIMAL)
        cogcsv.writeheader()

        header_cogset = ["ID", "Set", "Description"]

        cogsetcsv = csv.DictWriter(cogsetout, header_cogset, extrasaction="ignore", quotechar='"',
                                  quoting=csv.QUOTE_MINIMAL)
        cogsetcsv.writeheader()

        for cogset_row, cog_row in zip(cogset_iter, cog_iter):
            if not cogset_row[1].value:
                continue
            if cogset_row[1].value.isupper():
                cogset = CogSet.from_excel(cogset_row)
                cogsetcsv.writerow(cogset)

                for f_cell in cog_row:
                    if f_cell.value:
                        # get corresponding language_id to column
                        #this_lan_id = lan_dict[wb[(f_cell.column_letter + "1")].value]
                        this_lan_id = "not yet"
                        try:
                            for f_ele in CellParser(f_cell):
                                cog = Cognate.from_excel(f_ele, this_lan_id, f_cell, cogset)
                                cogcsv.writerow(cog)

                        except CellParsingError as err:
                            print("CellParsingError - somethings quite wrong")
                            print(err.message)
                            #input()

                        except FormCellError as err:
                            print(err)
                            #input()

            # line not to be processed
            else:
                continue


def initialize_cognate(dir_path, lan_dict,
                 file=r"C:\Users\walter.fuchs\Desktop\outofasia\stuff\Copy of TG_cognates_online_MASTER.xlsx"):
    wb = op.load_workbook(filename=file)
    sheets = wb.sheetnames
    wb = wb[sheets[0]]
    iter_cog = wb.iter_rows(min_row=3, min_col=5, max_col=42)  # iterates over rows with forms
    iter_congset = wb.iter_rows(min_row=3, max_col=4)  # iterates over rows with concepts
    cogset_cognate(dir_path, iter_congset, iter_cog, lan_dict, wb)


def initialize():
    dir_path = Path.cwd() / "initial_data"
    if not dir_path.exists():
        dir_path.mkdir()
    dir_path = Path(dir_path)

    lan_dict = {} # just for getting of language_id
    initialize_lexical(dir_path, lan_dict)
    print("\n\ncognates\n\n")
    initialize_cognate(dir_path, lan_dict)


if __name__ == "__main__":
    initialize()

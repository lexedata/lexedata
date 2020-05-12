# -*- coding: utf-8 -*-
import openpyxl as op
import csv
from pathlib import Path

from lexedata.database.objects import Language, Concept, Form, CogSet, CognateJudgement
from lexedata.database.database import create_db_session
from lexedata.importer.cellparser import CellParser
import lexedata.importer.exceptions as ex

create_db_session()


class ExcelParser:

    def __init__(self,
                 session,
               output=Path("initial_data"),
               lexicon_spreadsheet = "TG_comparative_lexical_online_MASTER.xlsx",
               cognatesets_spreadsheet = "TG_cognates_online_MASTER.xlsx"):
        self.session = session
        self.path = Path(output)
        if not self.path.exists():
            self.path.mkdir()
        self.lan_dict = {}
        self.lexicon_spreadsheet = lexicon_spreadsheet
        self.cognatesets_spreadsheet = cognatesets_spreadsheet
        self.cell_parser = CellParser()
        self.ignore_for_match = [
            "ID",
            "variants",
            "comment",
            "procedural_comment",
            "original",
        ]

    def parse(self):
        self.initialize_lexical()
        self.initialize_cognate()

    def initialize_lexical(self):
        wb = op.load_workbook(filename=self.lexicon_spreadsheet)
        sheets = wb.sheetnames
        wb = wb[sheets[0]]
        iter_forms = wb.iter_rows(min_row=3, min_col=7, max_col=44)  # iterates over rows with forms
        iter_concept = wb.iter_rows(min_row=3, max_col=6)  # iterates over rows with concepts
        iter_lan = wb.iter_cols(min_row=1, max_row=2, min_col=7, max_col=44)

        self.init_lan(iter_lan)
        self.session.commit()
        self.init_con_form(iter_concept, iter_forms)

    def language_from_column(self, column):
        excel_name, curator = [cell.value or "" for cell in column]
        name, comment = "", ""
        return {
            "name": name,
            "curator": curator,
            "comment": comment,
            "raw name": excel_name,
        }

    def concept_from_row(self, row):
        set, english, english_strict, spanish, portuguese, french = [cell.value or "" for cell in row]
        return {
            "set": set,
            "english": english,
            "english_strict": english_strict,
            "spanish": portuguese,
            "french": french,
            "gloss": english,
        }

    def init_lan(self, lan_iter):
        for lan_col in lan_iter:
            # iterate over language columns
            language_properties = self.language_from_column(lan_col)
            raw_name = language_properties.pop("raw name")
            id = Language.register_new_id(raw_name)
            if not raw_name or not id:
                print(f"Language {language_properties:} could not be created")
                continue
            if not language_properties["name"]:
                language_properties["name"] = raw_name

            language = Language(id=id, **language_properties)
            self.session.add(language)
            self.lan_dict[lan_col[0].column] = language

    def get_cell_comment(self, cell):
        return cell.comment.content if cell.comment else ""

    def init_con_form(self, con_iter, form_iter):
        with (self.path / "form_init.csv").open("w", encoding="utf8", newline="") as formsout, \
                (self.path / "concept_init.csv").open("w", encoding="utf8", newline="") as conceptsout:

            for row_forms, row_con in zip(form_iter, con_iter):
                concept_properties = self.concept_from_row(row_con)
                concept_id = Concept.register_new_id(concept_properties.pop("gloss"))
                comment = self.get_cell_comment(row_con[0])
                concept = Concept(id=concept_id, comment=comment, **concept_properties)

                for f_cell in row_forms:
                    if f_cell.value:
                        # get corresponding language_id to column
                        this_lan = self.lan_dict[f_cell.column]

                        for f_ele in self.cell_parser.parse(f_cell):
                            form_cell = self.form_from_cell(f_ele, this_lan, f_cell)
                            form = self.session.query(Form).filter(
                                Form.language==this_lan,
                                *[getattr(Form, key)==value
                                    for key, value in form_cell.items()
                                    if not key in self.ignore_for_match
                                ]).one_or_none()
                            if form is None:
                                form_id = Form.register_new_id("{:}_{:}".format(this_lan.id, concept.id))
                                form = Form(id=form_id, cell=f_cell.coordinate, **form_cell)
                                self.session.add(form)
                            else:
                                for key, value in form_cell.items():
                                    # FIXME: Maybe test `if value`? – discuss
                                    if key in self.ignore_for_match:
                                        if getattr(form, key)!=value:
                                            print(
                                                "{:s}{:d}:".format(f_cell.column_letter, f_cell.row),
                                                "Property {:s} of form defined here was '{:}', which "
                                                "did not match '{:}' specified earlier for the same form in {:s}. "
                                                "I kept the original {:s}.".format(
                                                    key, value, getattr(form, key), form.cell, key))
                            form.concepts.append(concept)
                            self.session.commit()

    def form_from_cell(self, f_ele, lan, form_cell):
        phonemic, phonetic, ortho, comment, source, _ = f_ele

        # replace source if not given
        source_id = "{:s}_{:}".format(lan.id, (source if source else "{1}").strip())

        return {
            "language": lan,
            "phonemic": phonemic,
            "phonetic": phonetic,
            "orthographic": ortho,
            "comment": comment,
            # FIXME: We need to create those source objects so we can refer to them
            # "sources": [source_id],
            "procedural_comment": self.get_cell_comment(form_cell),
        }

    def cogset_from_row(self, cog_row):
        values = [cell.value or "" for cell in cog_row]
        return {"ID": values[1],
                "properties": values[0],
                "comment": self.get_cell_comment(cog_row[1])}

    def cogset_cognate(self, cogset_iter, cog_iter):

        for cogset_row, row_forms in zip(cogset_iter, cog_iter):
            if not cogset_row[1].value:
                continue
            elif cogset_row[1].value.isupper():
                properties = self.cogset_from_row(cogset_row)
                id = CogSet.register_new_id(properties.pop("ID", ""))
                cogset = CogSet(id=id, **properties)

                for f_cell in row_forms:
                    if f_cell.value:
                        # get corresponding language_id to column
                        this_lan = self.lan_dict[f_cell.column]

                        try:
                            for f_ele in self.cell_parser.parse(f_cell):
                                form_cell = self.form_from_cell(f_ele, this_lan, f_cell)
                                # FIXME: Replace this by [look up existing form, otherwise create form]
                                form = self.session.query(Form).filter(
                                    Form.language==this_lan,
                                    *[getattr(Form, key)==value
                                      for key, value in form_cell.items()
                                      if not key in self.ignore_for_match
                                    ]).one_or_none()
                                if form is None:
                                    raise ex.CognateCellError(
                                        "Found form {:}:{:} in cognate table that is not in lexicon.".format(
                                            this_lan.id, f_ele), f_cell)
                                judgement = self.session.query(CognateJudgement).filter(
                                    CognateJudgement.form==form,
                                    CognateJudgement.cognateset==cogset).one_or_none()
                                if judgement is None:
                                    id = CognateJudgement.register_new_id(form.id)
                                    judgement = CognateJudgement(id=id, form=form, cognateset=cogset)
                                    self.session.add(judgement)
                                else:
                                    print("Duplicate cognate judgement found in cell {:}. "
                                          "(How even is that possible?)".format(f_cell.coordinate))
                        except (ex.CellParsingError, ex.CognateCellError) as e:
                            print("{:s}{:d}:".format(f_cell.column_letter, f_cell.row), e)
                            continue
                    self.session.commit()
            else:
                continue

    def initialize_cognate(self):
        wb = op.load_workbook(filename=self.cognatesets_spreadsheet)
        try:
            for sheet in wb.sheetnames:
                print("\nParsing sheet '{:s}'".format(sheet))
                ws = wb[sheet]
                iter_cog = ws.iter_rows(min_row=3, min_col=5, max_col=42)  # iterates over rows with forms
                iter_congset = ws.iter_rows(min_row=3, max_col=4)  # iterates over rows with concepts
                self.cogset_cognate(iter_congset, iter_cog)
        except KeyError:
            pass


if __name__ == "__main__":
    import argparse
    import pycldf
    parser = argparse.ArgumentParser(description="Load a Maweti-Guarani-style dataset into CLDF")
    parser.add_argument(
        "lexicon", nargs="?",
        default="TG_comparative_lexical_online_MASTER.xlsx",
        help="Path to an Excel file containing the dataset")
    parser.add_argument(
        "cogsets", nargs="?",
        default="TG_cognates_online_MASTER.xlsx",
        help="Path to an Excel file containing cogsets and cognatejudgements")
    parser.add_argument(
        "--db", nargs="?",
        default="sqlite:///",
        help="Where to store the temp DB")
    parser.add_argument(
        "--metadeta", nargs="?",
        default="Wordlist-metadata.json",
        help="Path to the metadata.json")
    parser.add_argument(
        "output", nargs="?",
        default="from_excel/",
        help="Directory to create the output CLDF wordlist in")
    parser.add_argument(
        "--debug-level", type=int, default=0,
        help="Debug level: Higher numbers are less forgiving")
    args = parser.parse_args()

    # The Intermediate Storage, in a in-memory DB
    session = create_db_session(args.db)

    ExcelParser(session, output=args.output, lexicon_spreadsheet=args.lexicon, cognatesets_spreadsheet=args.cogsets).parse()
    session.commit()
    session.close()

    if args.db.startswith("sqlite:///"):
        db_path = args.db[len("sqlite:///"):]
        if db_path == '':
            db_path = ':memory:'

    dataset = pycldf.Wordlist.from_metadata(
        args.metadeta,
    )
    db = pycldf.db.Database(dataset, fname=args.db)

    db.to_cldf(args.output)

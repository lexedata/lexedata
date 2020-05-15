# -*- coding: utf-8 -*-
from typing import Optional, Tuple

import openpyxl as op
import csv
from pathlib import Path

from lexedata.database.objects import Language, Concept, Form, CogSet, CognateJudgement, Source, Reference
from lexedata.database.database import create_db_session
from lexedata.importer.cellparser import CellParser
import lexedata.importer.exceptions as ex


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
            "id",
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

    def find_form(self, properties):
        ...

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
                            form_query = self.session.query(Form).filter(
                                Form.language == this_lan,
                                Form.sources.contains(
                                    form_cell["sources"][0]),
                                *[getattr(Form, key) == value
                                  for key, value in form_cell.items()
                                  if type(value) != tuple
                                  if key not in self.ignore_for_match
                                ])
                            form = form_query.one_or_none()
                            if form is None:
                                form_id = Form.register_new_id("{:}_{:}".format(this_lan.id, concept.id))
                                source, context = form_cell.pop("sources")
                                form = Form(id=form_id,
                                            cell=f_cell.coordinate,
                                            sources=[source],
                                            **form_cell)
                                self.session.add(form)
                                if context:
                                    assoc = self.session.query(Reference).filter(
                                        Reference.form==form.id,
                                        Reference.source==source.id).one()
                                    assoc.context = context
                            else:
                                for key, value in form_cell.items():
                                    try:
                                        old_value = getattr(form, key) or ''
                                    except AttributeError:
                                        continue
                                    if value and key in self.ignore_for_match:
                                        # FIXME: Maybe test `if value`? – discuss
                                        if value.lstrip("(").rstrip(")") not in old_value:
                                            new_value = f"{value:}; {old_value:}".strip().strip(";").strip()
                                            print(f"{f_cell.coordinate}: Property {key:} of form defined here was '{value:}', which was not part of '{old_value:}' specified earlier for the same form in {form.cell}. I combined those values to '{new_value:}'.".replace("\n", "\t"))
                                            setattr(form, key, new_value)
                            form.concepts.append(concept)
                            self.session.commit()

    def source_from_source_string(
            self,
            language: Language,
            source_string: str) -> Tuple[Source, Optional[str]]:
        # Source number {1} is not always specified
        if not source_string or not source_string.strip():
            source_string = "{1}"

        context: Optional[str]
        if ":" in source_string:
            source_string, context = source_string.split(":", maxsplit=1)
            assert context.endswith("}")
            source_string += "}"
            context = context[:-1].strip()
        else:
            context = None

        source_id = Source.string_to_id(f"{language.id:}_s{source_string}")
        source = self.session.query(Source).filter(
            Source.id == source_id).one_or_none()
        if source is None:
            source = Source(id=source_id)
            self.session.add(source)
        return source, context

    def form_from_cell(self, f_ele, lan, form_cell):
        phonemic, phonetic, ortho, comment, source, _ = f_ele

        source, context = self.source_from_source_string(lan, source)

        return {
            "language": lan,
            "phonemic": phonemic,
            "phonetic": phonetic,
            "orthographic": ortho,
            "comment": None if comment is None else comment.strip(),
            "sources": (source, context),
            "procedural_comment": self.get_cell_comment(form_cell).strip(),
            "original": Form.string_to_id(f"{phonemic:}{phonetic:}{ortho:}")
        }

    def cogset_from_row(self, cog_row):
        values = [cell.value or "" for cell in cog_row]
        return {"id": values[1],
                "properties": values[0],
                "comment": self.get_cell_comment(cog_row[1])}

    def cogset_cognate(self, cogset_iter, cog_iter):
        for cogset_row, row_forms in zip(cogset_iter, cog_iter):
            if not cogset_row[1].value:
                continue
            elif cogset_row[1].value.isupper():
                properties = self.cogset_from_row(cogset_row)
                id = CogSet.register_new_id(properties.pop("id", ""))
                cogset = CogSet(id=id, **properties)

                for f_cell in row_forms:
                    try:
                        this_lan = self.lan_dict[f_cell.column]
                    except KeyError:
                        continue

                    if f_cell.value:
                        # get corresponding language_id to column

                        try:
                            for f_ele in self.cell_parser.parse(f_cell):
                                form_cell = self.form_from_cell(f_ele, this_lan, f_cell)
                                form_query = self.session.query(Form).filter(
                                    Form.language == this_lan,
                                    *[getattr(Form, key) == value
                                      for key, value in form_cell.items()
                                      if type(value) != tuple
                                      if key not in self.ignore_for_match
                                    ])
                                forms = form_query.all()

                                if not forms:
                                    similar_forms = self.session.query(Form).filter(
                                        Form.language == this_lan,
                                        Form.original.contains(Form.string_to_id(form_cell["phonemic"])),
                                        Form.original.contains(Form.string_to_id(form_cell["phonetic"])),
                                        Form.original.contains(Form.string_to_id(form_cell["orthographic"])),
                                    ).all()
                                    raise ex.CognateCellError(
                                        f"Found form {this_lan.id:}:{f_ele:} in cognate table that is not in lexicon. Stripping special characters, did you mean one of {similar_forms:}?", f_cell.coordinate)
                                source, context = form_cell["sources"]
                                for form in forms:
                                    if source in form.sources:
                                        break
                                else:
                                    source_ids = [s.id for s in form.sources]
                                    print(f"{f_cell.column_letter}{f_cell.row}: [W] Form was given with source {form_cell['sources'][0].id}, but closest match (form.cldf_id) has different sources {source_ids:}. I assume that's a mistake and I'll add that closest match to the current cognate set.")

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
                            print("{:s}{:d}: [E]".format(f_cell.column_letter, f_cell.row), e)
                            continue
                    self.session.commit()
            else:
                continue

    def initialize_cognate(self):
        wb = op.load_workbook(filename=self.cognatesets_spreadsheet)
        for sheet in wb.sheetnames:
            print("\nParsing sheet '{:s}'".format(sheet))
            ws = wb[sheet]
            iter_cog = ws.iter_rows(min_row=3, min_col=5, max_col=42)  # iterates over rows with forms
            iter_congset = ws.iter_rows(min_row=3, max_col=4)  # iterates over rows with concepts
            self.cogset_cognate(iter_congset, iter_cog)


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
        "--metadata", nargs="?",
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

    # The Intermediate Storage, in a in-memory DB (unless specified otherwise)
    session = create_db_session(args.db)

    ExcelParser(session, output=args.output, lexicon_spreadsheet=args.lexicon, cognatesets_spreadsheet=args.cogsets).parse()
    session.commit()
    session.close()

    if args.db.startswith("sqlite:///"):
        db_path = args.db[len("sqlite:///"):]
        if db_path == '':
            db_path = ':memory:'

    dataset = pycldf.Wordlist.from_metadata(
        args.metadata,
    )
    db = pycldf.db.Database(dataset, fname=db_path)

    db.to_cldf(args.output)

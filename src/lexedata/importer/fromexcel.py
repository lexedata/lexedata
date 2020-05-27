# -*- coding: utf-8 -*-

import csv
import typing as t
from pathlib import Path

import pycldf
import openpyxl as op
import sqlalchemy as sa
from sqlalchemy.ext.automap import automap_base

from lexedata.database.database import create_db_session, new_id, string_to_id
from lexedata.importer.cellparser import CellParserLexical
import lexedata.importer.exceptions as ex
import lexedata.cldf.db as db

CLDFObject = t.Any


def name_of_object_in_table(base, tablename, table):
    """Give the name of objects in the table.

    >>> Dummy = None
    >>> name_of_object_in_table(Dummy, "FormTable", Dummy)
    'Form'
    >>> name_of_object_in_table(Dummy, "objectTable", Dummy)
    'Object'
    """
    s = str(tablename)
    if s.lower().endswith("table"):
        s = s[:-len("table")]
    return s[0].upper() + s[1:]


def name_of_object_in_table_relation(base, local_cls, referred_cls, constraint):
    """Give the name of objects in the table.

    >>> Dummy = None
    >>> name_of_object_in_table_relation(Dummy, Dummy, ExcelParser, Dummy)
    'excelparser'
    >>> class FormTable_SourceTable__cldf_source:
    ...   pass
    >>> name_of_object_in_table_relation(Dummy, Dummy, FormTable_SourceTable__cldf_source, Dummy)
    'cldf_source'
    """
    return referred_cls.__name__.split("__")[-1].lower()


def name_of_objects_in_table_relation(base, local_cls, referred_cls, constraint):
    """Give the name of objects in the table.

    >>> Dummy = None
    >>> name_of_objects_in_table_relation(Dummy, Dummy, ExcelParser, Dummy)
    'excelparsers'
    >>> class FormTable_SourceTable__cldf_source:
    ...   pass
    >>> name_of_objects_in_table_relation(Dummy, Dummy, FormTable_SourceTable__cldf_source, Dummy)
    'cldf_sources'
    """
    return referred_cls.__name__.split("__")[-1].lower() + "s"


class ExcelParser:
    def __init__(
            self,
            output=Path("initial_data/cldf-metadata.json"),
            lexicon_spreadsheet="TG_comparative_lexical_online_MASTER.xlsx",
            cognatesets_spreadsheet="TG_cognates_online_MASTER.xlsx"):
        dataset = pycldf.Dataset.from_metadata(output)
        database = db.Database(dataset)
        database.write()
        connection = database.connection()
        def creator():
            return connection
        Base = automap_base()
        engine = sa.create_engine("sqlite:///:memory:", creator=creator)
        Base.prepare(engine, reflect=True,
                     classname_for_table=name_of_object_in_table,
                     name_for_scalar_relationship=name_of_object_in_table_relation,
                     name_for_collection_relationship=name_of_objects_in_table_relation)
        self.session = sa.orm.Session(engine)

        print(dir(Base.classes))
        self.Form = Base.classes.Form
        self.Language = Base.classes.Language
        self.Concept = Base.classes.Parameter
        self.Source = Base.classes.Source
        self.Reference = Base.classes.FormTable_SourceTable__cldf_source

        self.path = Path(output)
        if not self.path.exists():
            self.path.mkdir()
        self.lan_dict = {}
        self.lexicon_spreadsheet = lexicon_spreadsheet
        self.cognatesets_spreadsheet = cognatesets_spreadsheet
        self.cell_parser = CellParserLexical()
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
        data = [cell.value or "" for cell in column[:2]]
        comment = self.get_cell_comment(column[0])
        return {
            "cldf_name": data[0],
            "Curator": data[1],
            "cldf_comment": comment
        }

    def concept_from_row(self, row):
        set, english, english_strict, spanish, portuguese, french = [cell.value or "" for cell in row]
        comment = self.get_cell_comment(row[0])
        return {
            # "set": set,
            # "english": english,
            # "english_strict": english_strict,
            # "spanish": portuguese,
            # "french": french,
            "cldf_name": english,
            "cldf_comment": comment
        }

    def init_lan(self, lan_iter):
        for lan_col in lan_iter:
            # iterate over language columns
            language_properties = self.language_from_column(lan_col)
            id = new_id(language_properties["cldf_name"], self.Language, self.session)
            language = self.Language(cldf_id=id, **language_properties)
            self.session.add(language)
            self.lan_dict[lan_col[0].column] = language

    @staticmethod
    def get_cell_comment(cell):
        return cell.comment.content if cell.comment else ""

    def find_form(self, properties):
        ...

    def init_con_form(self, con_iter, form_iter):
            for row_forms, row_con in zip(form_iter, con_iter):
                concept_properties = self.concept_from_row(row_con)
                concept_id = new_id(concept_properties["cldf_name"], self.Concept, self.session)
                concept = self.Concept(cldf_id=concept_id, **concept_properties)

                for f_cell in row_forms:
                    if f_cell.value:
                        # get corresponding language_id to column
                        this_lan = self.lan_dict[f_cell.column]

                        for f_ele in self.cell_parser.parse(f_cell.value, f_cell.coordinate):
                            form_cell = self.form_from_cell(f_ele, this_lan, f_cell)
                            form_query = self.session.query(self.Form).filter(
                                self.Form.cldf_languageReference == this_lan.cldf_id,
                                # FIXME: self.Form.cldf_source.contains(form_cell["sources"][0]),
                                *[getattr(self.Form, key) == value
                                  for key, value in form_cell.items()
                                  if type(value) != tuple
                                  if key not in self.ignore_for_match
                                ])
                            form = form_query.one_or_none()
                            if form is None:
                                form_id = new_id("{:}_{:}".format(this_lan.cldf_id, concept.cldf_id),
                                                 self.Form, self.session)
                                # source, context = form_cell.pop("sources")
                                form = self.Form(cldf_id=form_id,
                                            # cell=f_cell.coordinate,
                                            # sources=[source],
                                            **form_cell)
                                self.session.add(form)
                                # if context:
                                #     assoc = self.session.query(Reference).filter(
                                #         Reference.form==form.id,
                                #         Reference.source==source.id).one()
                                #     assoc.context = context
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
                            form.parameters.append(concept)
                            self.session.commit()

    def source_from_source_string(
            self,
            source_string: str,
            language: t.Optional[CLDFObject] = None) -> t.Tuple[CLDFObject, t.Optional[str]]:
        context: t.Optional[str]
        if ":" in source_string:
            source_string, context = source_string.split(":", maxsplit=1)
            assert context.endswith("}")
            source_string += "}"
            context = context[:-1].strip()
        else:
            context = None

        if language is None:
            source_id = string_to_id(source_string)
        else:
            source_id = string_to_id(f"{language.cldf_id:}_s{source_string}")

        source = self.session.query(self.Source).filter(
            self.Source.id == source_id).one_or_none()
        if source is None:
            source = self.Source(id=source_id)
            self.session.add(source)
        return source, context

    def form_from_cell(self, f_ele, lan, form_cell):
        phonemic, phonetic, ortho, comment, source, variants = f_ele

        # Source number {1} is not always specified
        if not source or not source.strip():
            source = "{1}"

        source, context = self.source_from_source_string(source, lan)

        return {
            "language": lan,
            "cldf_form": phonemic or "-",
            "cldf_segments": phonetic or "-",
            # "orthographic": ortho,
            # "variants": variants,
            "cldf_comment": None if comment is None else comment.strip(),
            # "cldf_source": (source, context),
            # "procedural_comment": self.get_cell_comment(form_cell).strip(),
            "cldf_value": string_to_id(f"{phonemic:}{phonetic:}{ortho:}")
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
                                form_query = self.session.query(self.Form).filter(
                                    self.Form.cldf_languageReference == this_lan,
                                    *[getattr(self.Form, key) == value
                                      for key, value in form_cell.items()
                                      if type(value) != tuple
                                      if key not in self.ignore_for_match
                                    ])
                                forms = form_query.all()

                                if not forms:
                                    similar_forms = self.session.query(self.Form).filter(
                                        self.Form.cldf_languageReference == this_lan.cldf_id,
                                        Form.original.contains(Form.string_to_id(form_cell["phonemic"])),
                                        Form.original.contains(Form.string_to_id(form_cell["phonetic"])),
                                        Form.original.contains(Form.string_to_id(form_cell["orthographic"])),
                                    ).all()
                                    raise ex.CognateCellError(
                                        f"Found form {this_lan.id:}:{f_ele:} in cognate table that is not in lexicon. Stripping special characters, did you mean one of {similar_forms:}?", f_cell.coordinate)
                                # source, context = form_cell["sources"]
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
                                    print(
                                        f"{f_cell.coordinate:}: [W] "
                                        "Duplicate cognate judgement found for form {form:}. "
                                        "(I assume it is fine, I added it once.)")
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
    else:
        db_path = args.db
    dataset = pycldf.Wordlist.from_metadata(
        args.metadata,
    )
    db = pycldf.db.Database(dataset, fname=db_path)

    db.to_cldf(args.output)

# -*- coding: utf-8 -*-

import csv
import typing as t
from pathlib import Path

import pycldf
import openpyxl as op
import sqlalchemy as sa
from sqlalchemy.ext.automap import automap_base

from lexedata.database.database import create_db_session, new_id, string_to_id
from lexedata.importer.cellparser import CellParserLexical, CellParserCognate, CellParserHyperlink
import lexedata.importer.exceptions as ex
from lexedata.cldf.automapped import SQLAlchemyWordlist, Language, Source, Form, Concept
import lexedata.cldf.db as db

# FIXME: Be more systematic in coordinates: Use ColLetterRowNumber where that
# is easy, (1-based col number, 1-based row number) elsewhere. Currently,
# topleft for example is indeed top-left, so row-column.

class ExcelParser(SQLAlchemyWordlist):
    topleft_lexical = (2, 2)
    topleft_cognate = (2, 2)

    check_for_match = [
        "cldf_id",
    ]

    def __init__(self, output_dataset: pycldf.Dataset) -> None:
        super().__init__(output_dataset)
        self.cell_parser = CellParserLexical()
        self.cognate_cell_parser = CellParserCognate()


        class Sources(t.DefaultDict[str, Source]):
            def __missing__(inner_self, key: str) -> Source:
                source = self.session.query(self.Source).filter(
                    self.Source.id == key).one_or_none()
                if source is None:
                    source = self.Source(id=key, genre='misc',
                                         author='', editor='')
                    self.session.add(source)
                inner_self.__setitem__(key, source)
                return source

        self.sources = Sources()

    def initialize_lexical(
            self,
            sheet: op.worksheet.worksheet.Worksheet
    ) -> None:
        first_row, first_col = self.topleft_lexical
        iter_forms = sheet.iter_rows(min_row=first_row, min_col=first_col)  # iterates over rows with forms
        iter_concept = sheet.iter_rows(min_row=first_row, max_col=first_col - 1)  # iterates over rows with concepts
        iter_lan = sheet.iter_cols(min_row=1, max_row=first_row - 1, min_col=first_col)

        languages_by_column = self.init_lan(iter_lan)
        self.session.commit()
        self.init_con_form(iter_concept, iter_forms, languages_by_column)

    def initialize_cognate(self, sheet: op.worksheet.worksheet.Worksheet):
        first_row, first_col = self.topleft_cognate
        iter_cog = sheet.iter_rows(min_row=first_row, min_col=first_col)  # iterates over rows with forms
        iter_congset = sheet.iter_rows(min_row=first_row, max_col=first_col - 1)  # iterates over rows with concepts
        iter_lan = sheet.iter_cols(min_row=1, max_row=first_row - 1, min_col=first_col)

        # Because people are not machines, the mapping of columns to languages
        # in cognate sheets can be different from the mapping in lexical
        # sheets, and each other
        languages_by_column = self.init_lan(iter_lan, create_if_not_found=False)
        self.cogset_cognate(iter_congset, iter_cog, languages_by_column)

    def language_from_column(self, column):
        data = [cell.value or "" for cell in column[:2]]
        comment = self.get_cell_comment(column[0])
        return {
            "cldf_name": data[0],
            "cldf_comment": comment
        }

    def concept_from_row(self: "ExcelParser", row: t.List[op.cell.Cell]) -> t.Dict[str, t.Any]:
        data = [cell.value or "" for cell in row[:1]]
        comment = self.get_cell_comment(row[0])
        return {
            "cldf_name": data[0],
            "cldf_comment": comment
        }

    def cogset_from_row(self, cog_row):
        data = [cell.value or "" for cell in cog_row[:]]
        return {"cldf_id": data[0],
                "cldf_comment": self.get_cell_comment(cog_row[0])}

    def init_lan(
            self,
            lan_iter: t.Iterable[t.List[op.cell.Cell]],
            create_if_not_found: bool = True,
            subparser: t.Callable[
                ["ExcelParser", t.List[op.cell.Cell]], t.Dict[str, t.Any]
            ] = language_from_column):
        lan_dict: t.Dict[str, Language] = {}

        for lan_col in lan_iter:
            # iterate over language columns
            language_properties = subparser(self, lan_col)
            language = self.session.query(self.Language).filter(
                self.Language.cldf_name == language_properties["cldf_name"]).one_or_none()
            if language is None:
                if create_if_not_found:
                    id = new_id(language_properties["cldf_name"], self.Language, self.session)
                    language = self.Language(cldf_id=id, **language_properties)
                    self.session.add(language)
                else:
                    # TODO: Should we raise an error here or not?
                    continue
            lan_dict[lan_col[0].column] = language

        return lan_dict

    @staticmethod
    def get_cell_comment(cell):
        return cell.comment.content if cell.comment else None

    def create_form_with_sources(
            self, sources: t.List[t.Tuple[Source, str]] = [], **properties) -> Form:
        concept: t.Optional[Concept] = properties.get("parameter") or properties.get("parameters", [None])[0]
        form_id = new_id(
            "{:}_{:}".format(
                properties["language"].cldf_id,
                concept and concept.cldf_id),
            self.Form, self.session)
        form = self.Form(cldf_id=form_id, **properties)
        self.session.add(form)
        for source, context in sources:
            self.session.add(self.Reference(
                form=form,
                source=source,
                context=context))
        self.session.commit()
        return form

    def init_con_form(self, con_iter, form_iter, lan_dict):
        for row_forms, row_con in zip(form_iter, con_iter):
            concept_properties = self.concept_from_row(row_con)
            concept_id = new_id(concept_properties["cldf_name"], self.Concept, self.session)
            concept = self.Concept(cldf_id=concept_id, **concept_properties)

            for f_cell in row_forms:
                # get corresponding language_id to column
                this_lan = lan_dict[f_cell.column]

                for form_cell in self.cell_parser.parse(f_cell, language=this_lan):
                    sources = [(self.sources[k], c or None)
                                for k, c in form_cell.pop("sources", [])]
                    if not hasattr(self.Form, "parameters"):
                        # There is no complex relationship between
                        # forms and concepts. Just add this form here.
                        self.create_form_with_sources(parameter=concept,
                                                        **form_cell)
                        continue

                    # Otherwise, deal with the alternative data model,
                    # where every form can have more than one meaning!
                    form_query = self.session.query(self.Form).filter(
                        self.Form == this_lan,
                        # FIXME: self.Form.cldf_source.contains(form_cell["sources"][0]),
                        *[getattr(self.Form, key) == value
                            for key, value in form_cell.items()
                            if type(value) != tuple
                            if key in self.check_for_match
                        ])
                    form = form_query.one_or_none()
                    if form is None:
                        self.create_form_with_sources(parameters=[concept],
                                                        **form_cell)
                        continue
                    else:
                        for key, value in form_cell.items():
                            try:
                                old_value = getattr(form, key) or ''
                            except AttributeError:
                                continue
                            if value and key not in self.check_for_match:
                                # FIXME: Maybe test `if value`? – discuss
                                if value.lstrip("(").rstrip(")") not in old_value:
                                    new_value = f"{value:}; {old_value:}".strip().strip(";").strip()
                                    print(f"{f_cell.coordinate}: Property {key:} of form defined here was '{value:}', which was not part of '{old_value:}' specified earlier for the same form in {form.cell}. I combined those values to '{new_value:}'.".replace("\n", "\t"))
                                    setattr(form, key, new_value)
                        self.session.commit()

    def cogset_cognate(self, cogset_iter, cog_iter, lan_dict: t.Dict[int, Language]):
        for cogset_row, row_forms in zip(cogset_iter, cog_iter):
            properties = self.cogset_from_row(cogset_row)
            if not properties:
                continue
            cogset_id = new_id(
                properties.pop("cldf_id", properties.get("cldf_name", "")),
                self.CogSet, self.session)

            cogset = self.CogSet(cldf_id=cogset_id, **properties)

            for f_cell in row_forms:
                try:
                    this_lan = lan_dict[f_cell.column]
                except KeyError:
                    continue

                try:
                    for form_cell in self.cognate_cell_parser.parse(f_cell, language=this_lan):
                        sources = [(self.sources[k], c or None)
                                   for k, c in form_cell.pop("sources", [])]
                        form_query = self.session.query(self.Form).filter(
                            self.Form.language == this_lan,
                            *[getattr(self.Form, key) == value
                                for key, value in form_cell.items()
                                if type(value) != tuple
                                if key in self.check_for_match])
                        forms = form_query.all()

                        if not forms:
                            similar_forms = self.session.query(self.Form).filter(
                                self.Form.language == this_lan,
                            ).all()
                            raise ex.CognateCellError(
                                f"Found form {this_lan.cldf_id:}:{form_cell:} in cognate table that is not in lexicon. Stripping special characters, did you mean one of {similar_forms:}?", f_cell.coordinate)
                        # source, context = form_cell["sources"]

                        for form in forms:
                            maybe_sources = {
                                reference.source
                                for reference in self.session.query(self.Reference).filter(self.Reference.form == form)}
                            if {s for s, c in sources} & maybe_sources:
                                # If described form and the form in the
                                # database share a source, assume they are the
                                # same.
                                break
                        else:
                            source_ids = [source.id for source in maybe_sources]
                            print(f"{f_cell.column_letter}{f_cell.row}: [W] Form was given with source {sources}, but closest match (form.cldf_id) has different sources {source_ids:}. I assume that's a mistake and I'll add that closest match to the current cognate set.")

                        judgement = self.session.query(self.Judgement).filter(
                            self.Judgement.form == form,
                            self.Judgement.cognateset == cogset).one_or_none()
                        if judgement is None:
                            id = new_id(form.cldf_id, self.Judgement, self.session)
                            judgement = self.Judgement(cldf_id=id, form=form, cognateset=cogset)
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


class ExcelCognateParser(ExcelParser):
    check_for_match = [
        "sources",
    ]

    def __init__(self, output_dataset: pycldf.Dataset) -> None:
        super().__init__(output_dataset)
        self.cell_parser = None
        self.cognate_cell_parser = CellParserHyperlink()

    def language_from_column(self, column):
        print(column)
        data = [cell.value or "" for cell in column[:1]]
        return {"cldf_name": data[0]}

    def cogset_from_row(self, cog_row):
        print(cog_row)
        values = [cell.value or "" for cell in cog_row[:1]]
        if values[0]:
            self.previous_cogset = {"cldf_id": values[0]}
        return self.previous_cogset

    def concept_from_row(self, row):
        raise NotImplementedError


class MawetiGuaraniExcelParser(ExcelParser):
    topleft_lexical = (3, 7)
    topleft_cognate = (3, 5)

    check_for_match = [
        "cldf_id",
        "variants",
        "comment",
        "procedural_comment",
        "original",
    ]
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
            "set": set,
            "english": english,
            "english_strict": english_strict,
            "spanish": portuguese,
            "french": french,
            "cldf_name": english,
            "cldf_comment": comment
        }

    def cogset_from_row(self, cog_row):
        values = [cell.value or "" for cell in cog_row[:2]]
        return {"cldf_id": values[1],
                "properties": values[0],
                "comment": self.get_cell_comment(cog_row[1])}

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
    excel_parser = ExcelParser(pycldf.Dataset.from_metadata(args.output))

    wb = op.load_workbook(filename=args.lexicon)
    excel_parser.initialize_cognate(wb.worksheets[0])

    wb = op.load_workbook(filename=args.cogsets)
    for sheet in wb.sheetnames:
        print("\nParsing sheet '{:s}'".format(sheet))
        ws = wb[sheet]
        excel_parser.initialize_cognate(ws)

    excel_parser.cldfdatabase.to_cldf(args.output.parent)

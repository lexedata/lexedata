# -*- coding: utf-8 -*-

import csv
import warnings
import typing as t
from pathlib import Path
from tempfile import mkstemp

import pycldf
import openpyxl
import sqlalchemy
import sqlalchemy.ext.automap as automap

from lexedata.database.database import create_db_session, new_id, string_to_id
from lexedata.importer.cellparser import CellParser, CellParserLexical, CellParserCognate, CellParserHyperlink
import lexedata.importer.exceptions as ex
from lexedata.cldf.automapped import SQLAlchemyWordlist, Language, Source, Form, Concept, CogSet
import lexedata.cldf.db as db

# FIXME: Be more systematic in coordinates: Use ColLetterRowNumber where that
# is easy, (1-based row number, 1-based column number) elsewhere. This may be
# counterintuitive, because B1 becomes (1, 2), but it is consistent with
# openpyxl.utils.cell.coordinate_to_tuple and with matrix indexing.


# Adapt warnings – TODO: Probably the `logging` package would be better for
# this job than `warnings`.
def formatwarning(
        message: str, category: t.Type[Warning], filename: str, lineno: int,
        line: t.Optional[str] = None
) -> str:
    # ignore everything except the message
    return str(message) + '\n'


warnings.formatwarning = formatwarning


class ObjectNotFoundWarning(UserWarning):
    pass


class MultipleCandidatesWarning(UserWarning):
    pass


MissingHandler = t.Callable[
    ["ExcelParser", sqlalchemy.ext.automap.AutomapBase, t.Optional[str]],
    bool]


def get_cell_comment(cell: openpyxl.cell.Cell) -> t.Optional[str]:
    return cell.comment.content if cell.comment else None


class ExcelParser(SQLAlchemyWordlist):
    top, left = (2, 2)

    check_for_match = [
        "cldf_id",
    ]

    check_for_row_match = [
        "cldf_name"
    ]

    def __init__(self, output_dataset: pycldf.Dataset, **kwargs) -> None:
        super().__init__(output_dataset, **kwargs)
        self.cell_parser: CellParser = CellParserLexical()

        class Sources(t.DefaultDict[str, Source]):
            def __missing__(inner_self, key: str) -> Source:
                source: t.Optional[Source] = self.session.query(
                    self.Source).filter(self.Source.id == key).one_or_none()
                if source is None:
                    source = self.Source(id=key, genre='misc',
                                         author='', editor='')
                    self.session.add(source)
                inner_self.__setitem__(key, source)
                return source

        self.sources = Sources()

        self.RowObject = self.Concept

    def error(self, db_object: sqlalchemy.ext.automap.AutomapBase,
              cell: t.Optional[str] = None) -> bool:
        try:
            repr = db_object.cldf_name
        except AttributeError:
            try:
                repr = db_object.cldf_id
            except AttributeError:
                repr = repr(db_object)
        raise ObjectNotFoundWarning(
            f"Failed to find object {repr:} in the database")

    def warn(self, db_object: sqlalchemy.ext.automap.AutomapBase,
             cell: t.Optional[str] = None) -> bool:
        try:
            repr = db_object.cldf_name
        except AttributeError:
            try:
                repr = db_object.cldf_id
            except AttributeError:
                repr = repr(db_object)
        warnings.warn(
            f"Failed to find object {repr:} in the database. Skipped.",
            ObjectNotFoundWarning)
        return False

    def warn_and_create(
            self, db_object: sqlalchemy.ext.automap.AutomapBase,
            cell: t.Optional[str] = None) -> bool:
        try:
            repr = db_object.cldf_name
        except AttributeError:
            try:
                repr = db_object.cldf_id
            except AttributeError:
                repr = repr(db_object)
        warnings.warn(
            f"Failed to find object {repr:} in the database. Added.",
            ObjectNotFoundWarning)
        self.session.add(db_object)
        return True

    def create(self, db_object: sqlalchemy.ext.automap.AutomapBase,
               cell: t.Optional[str] = None) -> bool:
        self.session.add(db_object)
        return True

    def ignore(self, db_object: sqlalchemy.ext.automap.AutomapBase,
               cell: t.Optional[str] = None) -> bool:
        return False

    on_language_not_found: MissingHandler = create
    on_row_not_found: MissingHandler = create
    on_form_not_found: MissingHandler = create

    def read(
            self,
            sheet: openpyxl.worksheet.worksheet.Worksheet,
            on_language_not_found: t.Optional[MissingHandler] = None,
            on_row_not_found: t.Optional[MissingHandler] = None,
            on_form_not_found: t.Optional[MissingHandler] = None,
    ) -> None:
        language_not_found: MissingHandler = on_language_not_found or type(
            self).on_language_not_found
        row_not_found: MissingHandler = on_row_not_found or type(
            self).on_row_not_found
        form_not_found: MissingHandler = on_form_not_found or type(
            self).on_form_not_found

        first_row, first_col = self.top, self.left
        iter_forms = sheet.iter_rows(
            min_row=first_row, min_col=first_col)
        iter_rows = sheet.iter_rows(
            min_row=first_row, max_col=first_col - 1)
        iter_lan: t.Iterable[t.List[openpyxl.cell.Cell]] = sheet.iter_cols(
            min_row=1, max_row=first_row - 1, min_col=first_col)

        languages_by_column = self.init_lan(
            iter_lan, if_not_found=language_not_found)
        self.parse_cells(
            iter_rows, iter_forms, languages_by_column,
            row_not_found, form_not_found)

    def language_from_column(
            self, column: t.List[openpyxl.cell.Cell]
    ) -> t.Dict[str, t.Any]:
        data = [(cell.value or '').strip() for cell in column[:self.top - 1]]
        comment = get_cell_comment(column[0])
        return {
            "cldf_name": data[0],
            "cldf_comment": comment
        }

    def properties_from_row(
            self, row: t.List[openpyxl.cell.Cell]
    ) -> t.Dict[str, t.Any]:
        data = [(cell.value or '').strip() for cell in row[:self.left - 1]]
        comment = get_cell_comment(row[0])
        return {
            "cldf_name": data[0],
            "cldf_comment": comment
        }

    def init_lan(
            self,
            lan_iter: t.Iterable[t.List[openpyxl.cell.Cell]],
            if_not_found: MissingHandler,
            subparser: t.Callable[
                ["ExcelParser", t.List[openpyxl.cell.Cell]], t.Dict[str, t.Any]
            ] = language_from_column) -> t.Dict[str, Language]:
        lan_dict: t.Dict[str, Language] = {}

        # iterate over language columns
        for lan_col in lan_iter:
            if not any([(cell.value or '').strip() for cell in lan_col]):
                # Skip empty languages
                continue
            language_properties = subparser(self, lan_col)
            language = self.session.query(self.Language).filter(
                self.Language.cldf_name == language_properties["cldf_name"]
            ).one_or_none()
            if language is None:
                id = new_id(language_properties["cldf_name"], self.Language, self.session)
                language = self.Language(cldf_id=id, **language_properties)
                if_not_found(self, language)
            lan_dict[lan_col[0].column] = language

        return lan_dict

    def create_form_with_sources(
            self: "ExcelParser",
            sources: t.List[t.Tuple[Source, t.Optional[str]]] = [],
            **properties: t.Any) -> Form:
        concept: t.Optional[Concept] = properties.get("parameter") or properties.get("parameters", [None])[0]
        form_id = new_id(
            "{:}_{:}".format(
                properties["language"].cldf_id,
                concept and concept.cldf_id),
            self.Form, self.session)
        form = self.Form(cldf_id=form_id, **properties)
        references = [
            self.Reference(
                form=form,
                source=source,
                context=context)
            for source, context in sources]
        return form, references

    def associate(self, form: Form, row: t.Union[Concept, CogSet]) -> None:
        try:
            form.parameter
            form.parameter = row
        except AttributeError:
            form.parameters.append(row)
        except KeyError:
            # This seems to be how SQLAlchemy signals the wrong object type
            tp = type(row)
            raise TypeError(
                f"Form {form:} expected a concept association, but got {tp:}.")

    def parse_cells(
            self,
            row_iter: t.Iterable[t.List[openpyxl.cell.Cell]],
            form_iter: t.Iterable[t.List[openpyxl.cell.Cell]],
            languages: t.Dict[str, int],
            on_row_not_found: MissingHandler = create,
            on_form_not_found: MissingHandler = create
    ) -> None:
        for row_header, row_forms in zip(row_iter, form_iter):
            # Parse the row header, creating or retrieving the associated row
            # object (i.e. a concept or a cognateset)
            properties = self.properties_from_row(row_header)
            if not properties:
                # Keep the old row_object from the previous line
                pass
            else:
                similar = self.session.query(self.RowObject).filter(
                    *[getattr(self.RowObject, key) == value
                      for key, value in properties.items()
                      if type(value) != tuple
                      if key in self.check_for_row_match]).all()
                if len(similar) == 0:
                    row_id = new_id(
                        properties.pop("cldf_id",
                                       properties.get("cldf_name", "")),
                        self.RowObject, self.session)
                    row_object = self.RowObject(cldf_id=row_id, **properties)
                    if not on_row_not_found(self, row_object):
                        continue
                else:
                    if len(similar) > 1:
                        warnings.warn(
                            f"Found more than one match for {properties:}")
                    row_object = similar[0]

            # Parse the row, cell by cell
            for f_cell in row_forms:
                try:
                    this_lan = languages[f_cell.column]
                except KeyError:
                    continue

                # Parse the cell, which results (potentially) in multiple forms
                for form_cell in self.cell_parser.parse(
                        f_cell, language=this_lan):
                    sources = [(self.sources[k], c or None)
                               for k, c in form_cell.pop("sources", [])]
                    form_query = self.session.query(self.Form).filter(
                        self.Form.language == this_lan,
                        *[getattr(self.Form, key) == value
                          for key, value in form_cell.items()
                          if type(value) != tuple
                          if key in self.check_for_match])
                    forms = form_query.all()
                    if "sources" in self.check_for_match:
                        for c in range(len(forms) - 1, -1, -1):
                            s = set(reference.source for reference in
                                    self.session.query(self.Reference).filter(
                                        self.Reference.form == forms[c]))
                            sources_only = {src[0] for src in sources}
                            if not sources_only & s:
                                warnings.warn("Closest matching form {:} had sources {:} instead of {:}".format(
                                    forms[0].cldf_id,
                                    {src.id for src in s},
                                    {src.id for src in sources_only}))
                                break
                    if len(forms) == 0:
                        form, references = self.create_form_with_sources(
                            sources=sources,
                            **form_cell)
                        if not on_form_not_found(self, form):
                            continue
                        self.session.add_all(references)
                    else:
                        if len(forms) > 1:
                            warnings.warn(
                                f"Found more than one match for {form_cell:}",
                                MultipleCandidatesWarning)
                        form = forms[0]
                        for attr, value in form_cell.items():
                            reference_value = getattr(form, attr, None)
                            if reference_value != value:
                                warnings.warn(f"Reference form property {attr:} was '{reference_value:}', not the '{value:}' specified here.")
                    self.associate(form, row_object)
            self.session.commit()


class ExcelCognateParser(ExcelParser):
    check_for_match = [
        "cldf_id",
    ]

    def __init__(self, output_dataset: pycldf.Dataset, **kwargs) -> None:
        super().__init__(output_dataset, **kwargs)
        self.cell_parser = CellParserHyperlink()
        self.RowObject = self.CogSet

    def properties_from_row(
            self, row: t.List[openpyxl.cell.Cell]
    ) -> t.Dict[str, t.Any]:
        data = [(cell.value or '').strip() for cell in row[:self.left - 1]]
        comment = get_cell_comment(row[0])
        return {
            "cldf_name": data[0],
            "cldf_comment": comment
        }

    on_language_not_found: MissingHandler = ExcelParser.error
    on_row_not_found: MissingHandler = ExcelParser.create
    on_form_not_found: MissingHandler = ExcelParser.warn

    def associate(self, form: Form, row: t.Union[Concept, CogSet]) -> None:
        id = new_id(
            f"{form.cldf_id:}__{row.cldf_id:}",
            self.Judgement, self.session)
        self.session.add(
            self.Judgement(cldf_id=id, form=form, cognateset=row))


class MawetiGuaraniExcelParser(ExcelParser):
    top, left = (3, 7)

    check_for_match = [
        "cldf_form",
        "sources",
        "cldf_value"
    ]

    def language_from_column(self, column: t.List[openpyxl.cell.Cell]) -> t.Dict[str, t.Any]:
        data = [(cell.value or '').strip() for cell in column[:2]]
        comment = get_cell_comment(column[0])
        return {
            "cldf_name": data[0],
            "Curator": data[1],
            "cldf_comment": comment
        }

    def properties_from_row(self, row: t.List[openpyxl.cell.Cell]) -> t.Dict[str, t.Any]:
        set, english, english_strict, spanish, portuguese, french = [(cell.value or '').strip() for cell in row]
        comment = get_cell_comment(row[0])
        return {
            "Set": set,
            "English": english_strict,
            "Spanish": spanish,
            "Portuguese": portuguese,
            "French": french,
            "cldf_name": english,
            "cldf_comment": comment
        }


class MawetiGuaraniExcelCognateParser(
        ExcelCognateParser, MawetiGuaraniExcelParser):
    top, left = (3, 7)

    def __init__(self, output_dataset: pycldf.Dataset, **kwargs) -> None:
        super().__init__(output_dataset, **kwargs)
        self.cell_parser = CellParserCognate()

    def properties_from_row(self, row):
        values = [(cell.value or '').strip() for cell in row[:2]]
        return {
            "cldf_id": values[1],
            "properties": values[0],
            "cldf_comment": get_cell_comment(row[1])
        }


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
        default="",
        help="Where to store the temp from reading the word list")
    parser.add_argument(
        "--metadata", nargs="?", type=Path,
        default="Wordlist-metadata.json",
        help="Path to the metadata.json")
    parser.add_argument(
        "--debug-level", type=int, default=0,
        help="Debug level: Higher numbers are less forgiving")
    args = parser.parse_args()

    if args.db.startswith("sqlite:///"):
        args.db = args.db[len("sqlite:///"):]
    if args.db == ":memory:":
        args.db = ""
    # We have too many difficult database connections in different APIs, we
    # refuse in-memory DBs and use a temporary file instead.
    if args.db == "":
        _, args.db = mkstemp(".sqlite", "lexicaldatabase", text=False)
        Path(args.db).unlink()

    # The Intermediate Storage, in a in-memory DB (unless specified otherwise)
    excel_parser_lexical = MawetiGuaraniExcelParser(
        pycldf.Dataset.from_metadata(args.metadata), fname=args.db)
    wb = openpyxl.load_workbook(filename=args.lexicon)
    excel_parser_lexical.read(wb.worksheets[0])

    excel_parser_lexical.cldfdatabase.to_cldf(args.metadata.parent)

    excel_parser_cognateset = MawetiGuaraniExcelCognateParser(
        pycldf.Dataset.from_metadata(args.metadata), fname=args.db)
    wb = openpyxl.load_workbook(filename=args.cogsets)
    for sheet in wb.sheetnames:
        print("\nParsing sheet '{:s}'".format(sheet))
        ws = wb[sheet]
        excel_parser_cognateset.read(ws)

    excel_parser_cognateset.cldfdatabase.to_cldf(args.metadata.parent)

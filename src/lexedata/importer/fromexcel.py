# -*- coding: utf-8 -*-

import os
import re
import sqlite3
import warnings
import typing as t
from pathlib import Path
from tempfile import mkstemp

import pycldf
import openpyxl
import sqlalchemy
from csvw.db import insert

from lexedata.types import *
import lexedata.importer.cellparser as cell_parsers
from lexedata.importer.cellparser import CellParser, \
    CellParserHyperlink, CellParserLexical, get_cell_comment
from lexedata.cldf.db import Database
import lexedata.error_handling as err

O = t.TypeVar('O', bound=Object)

# Remark: excel uses 1-based indices
def cells_are_empty(cells: t.Iterable[openpyxl.cell.Cell]) -> bool:
    return not any([(cell.value or '').strip() for cell in cells])

# Adapt warnings – TODO: Probably the `logging` package would be better for
# this job than `warnings`.
def formatwarning(
        message: str, category: t.Type[Warning], filename: str, lineno: int,
        line: t.Optional[str] = None
) -> str:
    # ignore everything except the message
    return str(message) + '\n'


warnings.formatwarning = formatwarning


class ExcelParser:

    def __init__(self, output_dataset: pycldf.Dataset,
                 top: int = 2, left: int = 2,
                 check_for_match: t.List[str] = ["cldf_id"],
                 check_for_row_match: t.List[str] = ["cldf_name"]
    ) -> None:
        self.on_language_not_found: err.MissingHandler = err.create
        self.on_row_not_found: err.MissingHandler = err.create
        self.on_form_not_found: err.MissingHandler = err.create

        self.cell_parser: CellParser = CellParserLexical()
        self.top = top
        self.left = left
        self.check_for_match = check_for_match
        self.check_for_row_match = check_for_row_match

        self.cldfdatabase = Database(output_dataset, fname="temp.sqlite")
        self.cldfdatabase.write()

    def language_from_column(
            self, column: t.List[openpyxl.cell.Cell]
    ) -> Language:
        data = [(cell.value or '').strip() for cell in column[:self.top - 1]]
        comment = get_cell_comment(column[0])
        return Language(
            cldf_name = data[0],
            cldf_comment = comment
        )

    def find_db_candidates(
            self, object: O, properties: t.Iterable[str]
    ) -> t.Iterable[str]:
        where_clauses = []
        where_parameters = []
        for property in properties:
            if type(object[property]) == set:
                where_clauses.append("0==0")
            else:
                where_clauses.append("{0} == ?".format(
                    property))
                where_parameters.append(object[property])
        if where_clauses:
            where = "WHERE {}".format(" AND ".join(where_clauses))
        else:
            where = ""
        candidates = self.cldfdatabase.query(
            "SELECT cldf_id, * FROM {0} {1}".format(
                object.__table__, where),
            where_parameters
        )
        return [c[0] for c in candidates]

    def properties_from_row(
            self, row: t.List[openpyxl.cell.Cell]
    ) -> t.Optional[RowObject]:
        data = [(cell.value or '').strip() for cell in row[:self.left - 1]]
        comment = get_cell_comment(row[0])
        return Concept(
            cldf_name = data[0],
            cldf_comment = comment
        )

    def parse_all_languages(self, sheet: openpyxl.worksheet.worksheet.Worksheet) -> t.Dict[str, str]:
        """Parse all language descriptions in the focal sheet.

        Returns
        =======
        languages: A dictionary mapping columns ("B", "C", "D", …) to language IDs
        """
        languages_by_column: t.Dict[str, str] = {}
        # iterate over language columns
        for lan_col in sheet.iter_cols(min_row=1, max_row=self.top - 1, min_col=self.left):
            if cells_are_empty(lan_col):
                # Skip empty languages
                continue
            language = self.language_from_column(lan_col)
            c = self.find_db_candidates(language, ["cldf_name"])
            for language_id in c:
                break
            else:
                if not (self.on_language_not_found(language, lan_col[0]) and
                        self.insert_into_db(language)):
                    continue
                language_id = language["cldf_id"]
            languages_by_column[lan_col[0].column] = language_id

        return languages_by_column

    def create_form_with_sources(
            self,
            form: Form,
            row_object: RowObject,
            sources: t.List[t.Tuple[Source, t.Optional[str]]] = [],) -> None:
        form["cldf_id"] = "{:}_{:}".format(form["cldf_languageReference"],
                             row_object["cldf_id"])
        self.make_id_unique(form)

        self.insert_into_db(form)
        for source, context in sources:
            self.insert_into_db(
                Reference(
                    FormTable_cldf_id=form["cldf_id"],
                    SourceTable_id=source,
                    context=context))

    def associate(self, form_id: str, row: RowObject) -> bool:
        assert row.__table__ == "ParameterTable", "Expected Concept, but got {:}".format(row.__class__)
        print((form_id, row["cldf_id"]))
        with self.cldfdatabase.connection() as conn:
            try:
                insert(conn, self.cldfdatabase.translate,
                       "FormTable_ParameterTable__cldf_parameterReference",
                       ("FormTable_cldf_id", "ParameterTable_cldf_id"),
                       (form_id, row["cldf_id"])
                )
                conn.commit()
            except sqlite3.IntegrityError:
                return False
        return True

    def insert_into_db(self, object: O) -> bool:
        print(object)
        with self.cldfdatabase.connection() as conn:
            insert(conn, self.cldfdatabase.translate,
                   object.__table__,
                   object.keys(),
                   tuple(object.values())
            )
            conn.commit()
        return True

    def make_id_unique(self, object: O) -> str:
        raw_id = object["cldf_id"]
        i = 0
        while self.cldfdatabase.query(
                "SELECT cldf_id FROM {0} WHERE cldf_id == ?".format(
                    object.__table__),
                (object["cldf_id"],)):
            i += 1
            object["cldf_id"] = "{:}_{:d}".format(raw_id, i)
        return object["cldf_id"]

    def parse_cells(self, sheet: openpyxl.worksheet.worksheet.Worksheet) -> None:
        languages = self.parse_all_languages(sheet)
        row_object = None
        for row in sheet.iter_rows(min_row=self.top):
            row_header, row_forms = row[:self.left - 1], row[self.left - 1:]
            # Parse the row header, creating or retrieving the associated row
            # object (i.e. a concept or a cognateset)
            properties = self.properties_from_row(row_header)
            if properties is not None:
                similar = self.find_db_candidates(
                    properties, self.check_for_row_match)
                for row_id in similar:
                    properties["cldf_id"] = row_id
                    break
                else:
                    if self.on_row_not_found(properties, row[0]):
                        properties["cldf_id"] = properties.get("cldf_name", "")
                        self.make_id_unique(properties)
                        self.insert_into_db(properties)
                    else:
                        continue
                row_object = properties

            if row_object is None:
                raise AssertionError("Empty first row: Row had no properties, and there was no previous row to copy")

            # Parse the row, cell by cell
            for cell_with_forms in row_forms:
                try:
                    this_lan = languages[cell_with_forms.column]
                except KeyError:
                    continue

                # Parse the cell, which results (potentially) in multiple forms
                for params in self.cell_parser.parse(
                            cell_with_forms, language=this_lan):
                    form = Form(params)
                    candidate_forms = self.find_db_candidates(
                        form, self.check_for_match)
                    sources = form.pop("sources")
                    for form_id in candidate_forms:
                        break
                    else:
                        if not self.on_form_not_found(form, cell_with_forms):
                            continue
                        self.create_form_with_sources(form, row_object, sources=sources)
                        form_id = form["cldf_id"]
                    self.associate(form_id, row_object)


class ExcelCognateParser(ExcelParser):
    def __init__(self, output_dataset: pycldf.Dataset,
                 top: int = 2, left: int = 2,
                 check_for_match: t.List[str] = ["cldf_id"],
                 check_for_row_match: t.List[str] = ["cldf_name"]
    ) -> None:
        super().__init__(
            output_dataset = output_dataset,
            top = top, left = left,
            check_for_match = check_for_match,
            check_for_row_match = check_for_row_match)
        self.on_language_not_found: err.MissingHandler = err.error
        self.on_row_not_found: err.MissingHandler = err.create
        self.on_form_not_found: err.MissingHandler = err.warn

    def properties_from_row(
            self, row: t.List[openpyxl.cell.Cell]
    ) -> t.Optional[RowObject]:
        data = [(cell.value or '').strip() for cell in row[:self.left - 1]]
        if not data[0]:
            return None
        comment = get_cell_comment(row[0])
        return CogSet(
            cldf_name = data[0],
            cldf_comment = comment
        )

    def associate(self, form_id: str, row: RowObject) -> bool:
        assert row.__table__ == "CognatesetTable", "Expected Concept, but got {:}".format(row.__class__)
        print((form_id, row["cldf_id"]))
        with self.cldfdatabase.connection() as conn:
            try:
                insert(conn, self.cldfdatabase.translate,
                       "CognateTable",
                       ("formReference", "cognatesetReference"),
                       (form_id, row["cldf_id"])
                )
                conn.commit()
            except sqlite3.IntegrityError:
                return False
        return True


def excel_parser_from_dialect(dataset: pycldf.Dataset) -> t.Type[ExcelParser]:
    dialect = argparse.Namespace(
        **dataset.tablegroup.common_props["special:fromexcel"])
    Row = CogSet if dialect.cognates else Concept
    top = len(dialect.lang_cell_regexes) + 1
    left = len(dialect.row_cell_regexes) + 1

    class SpecializedExcelParser(ExcelParser):
        def __init__(self, output_dataset: pycldf.Dataset) -> None:
            super().__init__(
                output_dataset=output_dataset,
                top=top,
                left=left,
                check_for_match=dialect.check_for_match,
                check_for_row_match=dialect.check_for_row_match,
                )
            self.cell_parser = getattr(
                cell_parsers,
                dialect.cell_parser)()

        def language_from_column(self, column: t.List[openpyxl.cell.Cell]) -> Language:
            """Parse the row, according to regexes from the metadata.

            Raises
            ======
            ValueError: When the cell cannot be parsed with the specified regex.

            """
            # FIXME: If a property appears twice, currently the later
            # appearance overwrites the earlier one. Merge wiser.
            d: t.Dict[str, str] = {}
            for cell, cell_regex, comment_regex in zip(column, dialect.lang_cell_regexes, dialect.lang_comment_regexes):
                if cell.value:
                    match = re.fullmatch(cell_regex, cell.value)
                    if match is None:
                        raise ValueError(f"In cell {cell.coordinate}: Expected to encounter match for {cell_regex}, but found {cell.value}")
                    d.update(match.groupdict())
                if cell.comment:
                    match = re.fullmatch(comment_regex, cell.comment.content)
                    if match is None:
                        raise ValueError(f"In cell {cell.coordinate}: Expected to encounter match for {comment_regex}, but found {cell.comment.content}")
                    d.update(match.groupdict())

            if "cldf_id" not in d:
                d["cldf_id"] = string_to_id(d["cldf_name"])
            return Language(d)

        def properties_from_row(self, row: t.List[openpyxl.cell.Cell]) -> Concept:
            """Parse the row, according to regexes from the metadata.

            Raises
            ======
            ValueError: When the cell cannot be parsed with the specified regex.

            """
            # FIXME: If a property appears twice, currently the later
            # appearance overwrites the earlier one. Merge wiser.
            d: t.Dict[str, str] = {}
            for cell, cell_regex, comment_regex in zip(row, dialect.row_cell_regexes, dialect.row_comment_regexes):
                if cell.value:
                    match = re.fullmatch(cell_regex, cell.value)
                    if match is None:
                        raise ValueError(f"In cell {cell.coordinate}: Expected to encounter match for {cell_regex}, but found {cell.value}")
                    d.update(match.groupdict())
                if cell.comment:
                    match = re.fullmatch(comment_regex, cell.comment.content)
                    if match is None:
                        raise ValueError(f"In cell {cell.coordinate}: Expected to encounter match for {comment_regex}, but found {cell.comment.content}")
                    d.update(match.groupdict())
            return Concept(d)
    return SpecializedExcelParser


def load_mg_style_dataset(
        metadata: Path, lexicon: str, cogsets: str, db: str) -> None:
    if db == "":
        open_file, db = mkstemp(".sqlite", "lexicaldatabase", text=False)
        # The CLDF database functionality expects the file to not exist, so
        # delete it again, but keep the filename.
        os.close(open_file)
        Path(db).unlink()
    lexicon_wb = openpyxl.load_workbook(lexicon)

    dataset = pycldf.Dataset.from_metadata(metadata)
    try:
        EP = excel_parser_from_dialect(dataset)
    except KeyError:
        EP = ExcelParser
    # The Intermediate Storage, in a in-memory DB (unless specified otherwise)
    excel_parser_lexical = EP(dataset)

    excel_parser_lexical.parse_cells(lexicon_wb.active)
    excel_parser_lexical.cldfdatabase.to_cldf(metadata.parent, mdname=metadata.name)

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

    load_mg_style_dataset(args.metadata, args.lexicon, args.cogsets, args.db)


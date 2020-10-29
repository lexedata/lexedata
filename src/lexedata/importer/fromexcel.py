# -*- coding: utf-8 -*-

import re
import sqlite3
import argparse
import typing as t
from pathlib import Path
from tempfile import mkdtemp
import logging
from collections import OrderedDict

from tqdm import tqdm

tqdm = lambda x: x

import pycldf
import openpyxl
from csvw.db import insert

from lexedata.types import (
    Object,
    Language,
    RowObject,
    Form,
    Source,
    Concept,
    Reference,
    CogSet,
    Judgement,
)
from lexedata.util import (
    string_to_id,
    clean_cell_value,
    get_cell_comment,
    edit_distance,
)
import lexedata.importer.cellparser as cell_parsers
import lexedata.error_handling as err
from lexedata.cldf.db import Database


O = t.TypeVar("O", bound=Object)

logger = logging.getLogger(__name__)

# NOTE: Excel uses 1-based indices, this shows up in a few places in this file.


def cells_are_empty(cells: t.Iterable[openpyxl.cell.Cell]) -> bool:
    return not any([clean_cell_value(cell) for cell in cells])


class ExcelParser:
    def __init__(
        self,
        output_dataset: pycldf.Dataset,
        db_fname: str,
        top: int = 2,
        cellparser: cell_parsers.NaiveCellParser = cell_parsers.CellParser(),
        row_header: t.List[str] = ["set", "cldf_name", None],
        check_for_match: t.List[str] = ["cldf_id"],
        check_for_row_match: t.List[str] = ["cldf_name"],
        check_for_language_match: t.List[str] = ["cldf_name"],
        on_language_not_found: err.MissingHandler = err.create,
        on_row_not_found: err.MissingHandler = err.create,
        on_form_not_found: err.MissingHandler = err.create,
    ) -> None:
        self.on_language_not_found = on_language_not_found
        self.on_row_not_found = on_row_not_found
        self.on_form_not_found = on_form_not_found
        self.row_header = row_header

        self.cell_parser: cell_parsers.NaiveCellParser = cellparser
        self.top = top
        self.left = len(row_header) + 1
        self.check_for_match = check_for_match
        self.check_for_row_match = check_for_row_match
        self.check_for_language_match = check_for_language_match
        self.init_db(output_dataset, fname=db_fname)

    def init_db(self, output_dataset, fname=None):
        self.cldfdatabase = Database(output_dataset, fname=fname)

    def cache_dataset(self):
        self.cldfdatabase.write_from_tg(_force=True)

    def drop_from_cache(self, table: str):
        assert "`" not in table
        with self.cldfdatabase.connection() as conn:
            conn.execute("DELETE FROM `{:s}`".format(table))
            conn.commit()

    def retrieve(self, table_type: str):
        data = self.cldfdatabase.read()
        items = data[table_type]
        table = self.cldfdatabase.dataset[table_type]
        return [self.cldfdatabase.retranslate(table, item) for item in items]

    # Run `write` for an ExcelParser after __init__, but not for an ExcelCognateParser
    def write(self):
        if Path(self.cldfdatabase.fname).exists():
            raise FileExistsError(
                "The database file {:} exists, but ExcelParser expects "
                "to start from a clean slate."
            )
        self.cldfdatabase.write()

    def language_from_column(self, column: t.List[openpyxl.cell.Cell]) -> Language:
        data = [clean_cell_value(cell) for cell in column[: self.top - 1]]
        comment = get_cell_comment(column[0])
        id = string_to_id(data[0])
        return Language(
            # an id candidate must be provided, which is transformed into a unique id
            cldf_id=id,
            cldf_name=data[0],
            cldf_comment=comment,
        )

    def find_db_candidates(
        self, object: O, properties_for_match: t.Iterable[str]
    ) -> t.Iterable[str]:
        where_clauses = []
        where_parameters = []
        join = ""
        for property in properties_for_match:
            if property not in object:
                continue
            elif property == "cldf_source":
                # Sources are handled specially.
                where_clauses.append(
                    "FormTable_SourceTable__cldf_source.FormTable_cldf_id == ?"
                )
                where_parameters.append(list(object[property])[0][0])
                # TODO: Should we instead match an OR or an AND of all sources?
                # This checks whether the first source matches, which is
                # correct for MG, I think.
                join = "JOIN FormTable_SourceTable__cldf_source ON FormTable_cldf_id == cldf_id"
            elif type(object[property]) not in {float, int, str}:
                raise ValueError(
                    "Cannot find a DB candidate for column {:}: Data type {:} not supported.".format(
                        property, type(object[property])
                    )
                )
            else:
                where_clauses.append("{0} == ?".format(property))
                where_parameters.append(object[property])
        if where_clauses:
            where = "WHERE {}".format(" AND ".join(where_clauses))
        else:
            where = ""
        candidates = self.cldfdatabase.query(
            "SELECT cldf_id, * FROM {0} {2} {1} ".format(object.__table__, where, join),
            where_parameters,
        )
        return [c[0] for c in candidates]

    def properties_from_row(
        self, row: t.List[openpyxl.cell.Cell]
    ) -> t.Optional[RowObject]:
        data = [clean_cell_value(cell) for cell in row[: self.left - 1]]
        properties = dict(zip(self.row_header, data))
        # delete all possible None entries coming from row_header
        while None in properties.keys():
            del properties[None]

        # fetch cell comment
        comment = get_cell_comment(row[0])
        properties["cldf_comment"] = comment

        # cldf_name serves as cldf_id candidate
        properties["cldf_id"] = properties["cldf_name"]

        return Concept(properties)

    def parse_all_languages(
        self, sheet: openpyxl.worksheet.worksheet.Worksheet
    ) -> t.Dict[str, str]:
        """Parse all language descriptions in the focal sheet.

        Returns
        =======
        languages: A dictionary mapping columns ("B", "C", "D", …) to language IDs
        """
        languages_by_column: t.Dict[str, str] = {}
        # iterate over language columns
        for lan_col in tqdm(
            sheet.iter_cols(min_row=1, max_row=self.top - 1, min_col=self.left)
        ):
            if cells_are_empty(lan_col):
                # Skip empty languages
                continue
            language = self.language_from_column(lan_col)
            candidates = self.find_db_candidates(
                language, self.check_for_language_match
            )
            for language_id in candidates:
                break
            else:
                if not (
                    self.on_language_not_found(language, lan_col[0])
                    and self.insert_into_db(language)
                ):
                    continue
                language_id = language["cldf_id"]
            languages_by_column[lan_col[0].column] = language_id

        return languages_by_column

    def create_form_with_sources(
        self,
        form: Form,
        sources: t.List[t.Tuple[Source, t.Optional[str]]] = [],
    ) -> None:
        self.make_id_unique(form)

        self.insert_into_db(form)
        for source, context in sources:
            self.insert_into_db(
                Reference(
                    FormTable_cldf_id=form["cldf_id"],
                    SourceTable_id=source,
                    context=context,
                )
            )

    def associate(
        self, form_id: str, row: RowObject, comment: t.Optional[str] = None
    ) -> bool:
        assert (
            row.__table__ == "ParameterTable"
        ), "Expected Concept, but got {:}".format(row.__class__)
        with self.cldfdatabase.connection() as conn:
            try:
                insert(
                    conn,
                    self.cldfdatabase.translate,
                    "FormTable_ParameterTable__cldf_parameterReference",
                    ("FormTable_cldf_id", "ParameterTable_cldf_id", "context"),
                    (form_id, row["cldf_id"], comment),
                )
                conn.commit()
            except sqlite3.IntegrityError as err:
                logger.error(err)
        return True

    def insert_into_db(self, object: O) -> bool:
        for key, value in object.items():
            if type(value) == list:
                columns = self.cldfdatabase.dataset[
                    object.__table__
                ].tableSchema.columns
                sep = [
                    c.separator
                    for c in columns
                    if self.cldfdatabase.translate(c.name) == key
                ][0]
                # Join values using the separator
                object[key] = sep.join(value)
            elif type(value) == set:
                raise ValueError("Sets should be handled by association tables.")
        with self.cldfdatabase.connection() as conn:
            insert(
                conn,
                self.cldfdatabase.translate,
                object.__table__,
                object.keys(),
                tuple(object.values()),
            )
            # commit to the database
            conn.commit()
        return True

    def make_id_unique(self, object: O) -> str:
        raw_id = object["cldf_id"]
        i = 0
        while self.cldfdatabase.query(
            "SELECT cldf_id FROM {0} WHERE cldf_id == ?".format(object.__table__),
            (object["cldf_id"],),
        ):
            i += 1
            object["cldf_id"] = "{:}_{:d}".format(raw_id, i)
        return object["cldf_id"]

    def parse_cells(self, sheet: openpyxl.worksheet.worksheet.Worksheet) -> None:
        languages = self.parse_all_languages(sheet)
        row_object = None
        for row in tqdm(sheet.iter_rows(min_row=self.top)):
            row_header, row_forms = row[: self.left - 1], row[self.left - 1 :]
            # Parse the row header, creating or retrieving the associated row
            # object (i.e. a concept or a cognateset)
            properties = self.properties_from_row(row_header)
            if properties is not None:
                similar = self.find_db_candidates(properties, self.check_for_row_match)
                for row_id in similar:
                    properties["cldf_id"] = row_id
                    break
                else:
                    if self.on_row_not_found(properties, row[0]):
                        properties["cldf_id"] = string_to_id(
                            properties.get("cldf_name", "")
                        )
                        self.make_id_unique(properties)
                        self.insert_into_db(properties)
                    else:
                        continue
                row_object = properties

            if row_object is None:
                if any(c.value for c in row_forms):
                    raise AssertionError(
                        "Empty first row: Row had no properties, and there was no previous row to copy"
                    )
                else:
                    continue
            # Parse the row, cell by cell
            for cell_with_forms in row_forms:
                try:
                    this_lan = languages[cell_with_forms.column]
                except KeyError:
                    continue

                # Parse the cell, which results (potentially) in multiple forms
                for params in self.cell_parser.parse(
                    cell_with_forms,
                    this_lan,
                    f"{sheet.title}.{cell_with_forms.coordinate}",
                ):
                    # Cellparser adds comment of a excel cell to "Cell_Comment" if given
                    maybe_comment: t.Optional[str] = params.pop("Cell_Comment", None)
                    form = Form(params)
                    # create candidate for form[cldf_id]
                    form["cldf_id"] = "{:}_{:}".format(
                        form["cldf_languageReference"], row_object["cldf_id"]
                    )
                    candidate_forms = self.find_db_candidates(
                        form, self.check_for_match
                    )
                    sources = form.pop("cldf_source", [])
                    if candidate_forms:
                        # if a candidate for form already exists, don't add the form
                        form_id = candidate_forms[0]
                        self.associate(form_id, row_object)
                    else:
                        # no candidates. form is created or not.
                        if self.on_form_not_found(form, cell_with_forms):
                            form["cldf_id"] = "{:}_{:}".format(
                                form["cldf_languageReference"], row_object["cldf_id"]
                            )
                            self.create_form_with_sources(
                                form, sources=sources
                            )
                            form_id = form["cldf_id"]
                            self.associate(form_id, row_object, comment=maybe_comment)
                        else:
                            logger.error(
                                "The missing form was {:} in {:}, given as {:}.".format(
                                    row_object["cldf_id"], this_lan, form["cldf_value"]
                                )
                            )
                            with self.cldfdatabase.connection() as conn:
                                conn.create_function("edit_distance", 2, edit_distance)
                                conn.row_factory = sqlite3.Row
                                data = conn.execute(
                                    """
                                    SELECT
                                        cldf_languageReference as language,
                                        ParameterTable.cldf_name as concept,
                                        cldf_value as original
                                    FROM FormTable
                                        JOIN FormTable_ParameterTable__cldf_parameterReference
                                            ON FormTable_cldf_id == FormTable.cldf_id
                                        JOIN ParameterTable
                                            ON ParameterTable_cldf_id == ParameterTable.cldf_id
                                    WHERE
                                        cldf_languageReference == ? AND
                                        ({:})
                                    ORDER BY
                                        ({:})
                                    LIMIT 3
                                    """.format(
                                        " OR ".join(
                                            [
                                                "edit_distance({:}, ?) < 0.3".format(m)
                                                for m in self.check_for_match
                                                if m
                                                not in {
                                                    "source",
                                                    "cldf_languageReference",
                                                }
                                            ]
                                        ),
                                        " + ".join(
                                            [
                                                "edit_distance({:}, ?)".format(m)
                                                for m in self.check_for_match
                                                if m
                                                not in {
                                                    "source",
                                                    "cldf_languageReference",
                                                }
                                            ]
                                        ),
                                    ),
                                    [this_lan]
                                    + [
                                        form.get(m, "")
                                        for m in self.check_for_match
                                        if m not in {"source", "cldf_languageReference"}
                                    ]
                                    + [
                                        form.get(m, "")
                                        for m in self.check_for_match
                                        if m not in {"source", "cldf_languageReference"}
                                    ],
                                ).fetchall()
                            for row in data:
                                logger.info(f"Did you mean {dict(row)} ?")
                            continue
        self.commit()

    def commit(self):
        with self.cldfdatabase.connection() as conn:
            conn.commit()


class ExcelCognateParser(ExcelParser):
    def __init__(
        self,
        output_dataset: pycldf.Dataset,
        db_fname: str,
        top: int = 3,
        cellparser: cell_parsers.NaiveCellParser = cell_parsers.CellParser(),
        row_header=["set", "cldf_name", None],
        check_for_match: t.List[str] = ["cldf_id"],
        check_for_row_match: t.List[str] = ["cldf_name"],
        check_for_language_match: t.List[str] = ["cldf_name"],
        on_language_not_found: err.MissingHandler = err.error,
        on_row_not_found: err.MissingHandler = err.create,
        on_form_not_found: err.MissingHandler = err.warn,
    ) -> None:
        super().__init__(
            output_dataset=output_dataset,
            db_fname=db_fname,
            top=top,
            cellparser=cellparser,
            check_for_match=check_for_match,
            row_header=row_header,
            check_for_row_match=check_for_row_match,
            check_for_language_match=check_for_language_match,
            on_language_not_found=on_language_not_found,
            on_row_not_found=on_row_not_found,
            on_form_not_found=on_form_not_found,
        )

    def properties_from_row(
        self, row: t.List[openpyxl.cell.Cell]
    ) -> t.Optional[RowObject]:
        # TODO: Ask Gereon: get_cell_comment with unicode normalization or not?
        data = [clean_cell_value(cell) for cell in row[: self.left - 1]]
        properties = dict(zip(self.row_header, data))
        # delete all possible None entries coming from row_header
        while None in properties.keys():
            del properties[None]

        # fetch cell comment
        comment = get_cell_comment(row[0])
        properties["cldf_comment"] = comment

        # cldf_name serves as cldf_id candidate
        properties["cldf_id"] = properties["cldf_id"] or properties["cldf_name"]
        return CogSet(properties)

    def associate(
        self, form_id: str, row: RowObject, comment: t.Optional[str] = None
    ) -> bool:
        assert (
            row.__table__ == "CognatesetTable"
        ), "Expected CognateSet, but got {:}".format(row.__class__)
        row_id = row["cldf_id"]
        judgement = Judgement(
            cldf_id=f"{form_id}-{row_id}",
            cldf_formReference=form_id,
            cldf_cognatesetReference=row_id,
            cldf_comment=comment or "",
        )
        self.make_id_unique(judgement)
        return self.insert_into_db(judgement)


def excel_parser_from_dialect(
    dialect: argparse.Namespace, cognate: bool
) -> t.Type[ExcelParser]:
    if cognate:
        Row = CogSet
        Parser = ExcelCognateParser
    else:
        Row = Concept
        Parser = ExcelParser
    top = len(dialect.lang_cell_regexes) + 1
    # prepare cellparser
    row_header = []
    for row_regex in dialect.row_cell_regexes:
        match = re.fullmatch(row_regex, "", re.DOTALL)
        row_header += list(match.groupdict().keys()) or [None]
    element_semantics = OrderedDict()
    bracket_pairs = OrderedDict()
    for value in dialect.cell_parser["cell_parser_semantics"]:
        name, opening, closing, my_bool = value
        bracket_pairs[opening] = closing
        element_semantics[opening] = (name, my_bool)
    initialized_cell_parser = getattr(cell_parsers, dialect.cell_parser["name"])(
        bracket_pairs=bracket_pairs,
        element_semantics=element_semantics,
        separation_pattern=fr"([{''.join(dialect.cell_parser['form_separator'])}])",
        variant_separator=dialect.cell_parser["variant_separator"],
        add_default_source=dialect.cell_parser.get("add_default_source"),
    )

    class SpecializedExcelParser(Parser):
        def __init__(
            self,
            output_dataset: pycldf.Dataset,
            db_fname: str,
        ) -> None:
            super().__init__(
                output_dataset=output_dataset,
                db_fname=db_fname,
                top=top,
                row_header=row_header,
                cellparser=initialized_cell_parser,
                check_for_match=dialect.check_for_match,
                check_for_row_match=dialect.check_for_row_match,
                check_for_language_match=dialect.check_for_language_match,
            )

        def language_from_column(self, column: t.List[openpyxl.cell.Cell]) -> Language:
            """Parse the row, according to regexes from the metadata.

            Raises
            ======
            ValueError: When the cell cannot be parsed with the specified regex.

            """
            d: t.Dict[str, str] = {}
            for cell, cell_regex, comment_regex in zip(
                column, dialect.lang_cell_regexes, dialect.lang_comment_regexes
            ):
                if cell.value:
                    match = re.fullmatch(cell_regex, cell.value.strip(), re.DOTALL)
                    if match is None:
                        raise ValueError(
                            f"In cell {cell.coordinate}: Expected to encounter match for {cell_regex}, but found {cell.value}"
                        )
                    for k, v in match.groupdict().items():
                        if k in d:
                            d[k] = d[k] + v
                        else:
                            d[k] = v
                if cell.comment:
                    match = re.fullmatch(comment_regex, cell.comment.content, re.DOTALL)
                    if match is None:
                        raise ValueError(
                            f"In cell {cell.coordinate}: Expected to encounter match for {comment_regex}, but found {cell.comment.content}"
                        )
                    for k, v in match.groupdict().items():
                        if k in d:
                            d[k] = d[k] + v
                        else:
                            d[k] = v

            if "cldf_id" not in d:
                d["cldf_id"] = string_to_id(d["cldf_name"])
            return Language(d)

        def properties_from_row(self, row: t.List[openpyxl.cell.Cell]) -> Row:
            """Parse the row, according to regexes from the metadata.

            Raises
            ======
            ValueError: When the cell cannot be parsed with the specified regex.

            """
            d: t.Dict[str, str] = {}
            for cell, cell_regex, comment_regex in zip(
                row, dialect.row_cell_regexes, dialect.row_comment_regexes
            ):
                if cell.value:
                    match = re.fullmatch(cell_regex, cell.value.strip(), re.DOTALL)
                    if match is None:
                        raise ValueError(
                            f"In cell {cell.coordinate}: Expected to encounter match for {cell_regex}"
                            f", but found {cell.value}"
                        )
                    for k, v in match.groupdict().items():
                        if k in d:
                            d[k] = d[k] + v
                        else:
                            d[k] = v
                if cell.comment:
                    match = re.fullmatch(comment_regex, cell.comment.content, re.DOTALL)
                    if match is None:
                        raise ValueError(
                            f"In cell {cell.coordinate}: Expected to encounter match for {comment_regex},"
                            f"but found {cell.comment.content}"
                        )
                    for k, v in match.groupdict().items():
                        if k in d:
                            d[k] = d[k] + v
                        else:
                            d[k] = v

            return Row(d)

    return SpecializedExcelParser


def load_dataset(
    metadata: Path, lexicon: str, db: str, cognate_lexicon: t.Optional[str]
):
    #logging.basicConfig(filename="warnings.log")
    dataset = pycldf.Dataset.from_metadata(metadata)
    dialect = argparse.Namespace(**dataset.tablegroup.common_props["special:fromexcel"])
    if db == "":
        tmpdir = Path(mkdtemp("", "fromexcel"))
        db = tmpdir / "db.sqlite"
    lexicon_wb = openpyxl.load_workbook(lexicon).active
    # load lexical data set
    try:
        EP = excel_parser_from_dialect(dialect, cognate=False)
    except KeyError:
        logger.warning(
            "Dialect not found or dialect was missing a key, falling back to default parser"
        )
        EP = ExcelParser
    # The Intermediate Storage, in a in-memory DB (unless specified otherwise)
    EP = EP(dataset, db_fname=db)
    EP.write()
    EP.parse_cells(lexicon_wb)
    EP.cldfdatabase.to_cldf(metadata.parent, mdname=metadata.name)
    # load cognate data set if provided by metadata
    cognate = True if cognate_lexicon and dialect.cognates else False
    if cognate:
        try:
            EP = excel_parser_from_dialect(
                argparse.Namespace(**dialect.cognates), cognate=cognate
            )
        except KeyError:
            EP = ExcelCognateParser(dataset, db_fname=db)
        EP = EP(dataset, db)
        for sheet in openpyxl.load_workbook(cognate_lexicon).worksheets:
            EP.parse_cells(sheet)
        EP.cldfdatabase.to_cldf(metadata.parent, mdname=metadata.name)


class DB(ExcelParser):
    def init_db(self, output_dataset, fname=None):
        if fname is not None:
            logger.inf0("Warning: dbase fname set, but ignored")
        self.__cache = {}
        self.__dataset = output_dataset

    def cache_dataset(self):
        for table in self.__dataset.tables:
            table_type = table.common_props["dc:conformsTo"].rsplit("#", 1)[1]
            (id,) = table.tableSchema.primaryKey
            self.__cache[table_type] = {row[id]: row for row in table}

    def drop_from_cache(self, table: str):
        self.__cache[table] = {}

    def retrieve(self, table_type: str):
        return self.__cache[table_type].values()

    def write(self):
        self.__cache = {}

    def associate(
        self, form_id: str, row: RowObject, comment: t.Optional[str] = None
    ) -> bool:
        form = self.__cache["FormTable"][form_id]
        if row.__table__ == "CognatesetTable":
            id = self.__dataset["CognatesetTable", "id"].name
            try:
                column = self.__dataset["FormTable", "cognatesetReference"]
            except KeyError:
                judgements = self.__cache["CognateTable"]
                cognateset = row[self.__dataset["CognatesetTable", "id"].name]
                judgement = Judgement(
                    {
                        self.__dataset["CognateTable", "id"].name: "{:}-{:}".format(
                            form_id, cognateset
                        ),
                        self.__dataset["CognateTable", "formReference"].name: form_id,
                        self.__dataset[
                            "CognateTable", "cognatesetReference"
                        ].name: cognateset,
                        self.__dataset["CognateTable", "comment"].name: comment or "",
                    }
                )
                self.make_id_unique(judgement)
                judgements[judgement[id]] = judgement
                return True
        elif row.__table__ == "ParameterTable":
            column = self.__dataset["FormTable", "parameterReference"]
            id = self.__dataset["ParameterTable", "id"].name

        if column.separator is None:
            form_id[column_name] = row[id]
        else:
            form_id.setdefault(column_name).append(row[id])
        return True

    def insert_into_db(self, object: O) -> bool:
        id = self.__dataset[object.__table__, "id"].name
        assert object[id] not in self.__cache[object.__table__]
        self.__cache[object.__table__][object[id]] = object

    def make_id_unique(self, object: O) -> str:
        id = self.__dataset[object.__table__, "id"].name
        raw_id = object[id]
        i = 0
        while object[id] in self.__cache[object.__table__]:
            i += 1
            object[id] = "{:}_{:d}".format(raw_id, i)
        return object[id]

    def find_db_candidates(
        self, object: O, properties_for_match: t.Iterable[str]
    ) -> t.Iterable[str]:
        return [
            candidate
            for candidate, properties in self.__cache[object.__table__].items()
            if all(properties[p] == object[p] for p in properties_for_match)
        ]

    def commit(self):
        pass


if __name__ == "__main__":
    import argparse
    import pycldf

    parser = argparse.ArgumentParser(
        description="Load a Maweti-Guarani-style dataset into CLDF"
    )
    parser.add_argument(
        "lexicon",
        nargs="?",
        default="TG_comparative_lexical_online_MASTER.xlsx",
        help="Path to an Excel file containing the dataset",
    )
    parser.add_argument(
        "--cogsets",
        nargs="?",
        default="",
        help="Path to an Excel file containing cogsets and cognatejudgements",
    )
    parser.add_argument(
        "--db",
        nargs="?",
        default="",
        help="Where to store the temp from reading the word list",
    )
    parser.add_argument(
        "--metadata",
        nargs="?",
        type=Path,
        default="Wordlist-metadata.json",
        help="Path to the metadata.json",
    )
    parser.add_argument(
        "--debug-level",
        type=int,
        default=0,
        help="Debug level: Higher numbers are less forgiving",
    )
    args = parser.parse_args()

    if args.db.startswith("sqlite:///"):
        args.db = args.db[len("sqlite:///"):]
    if args.db == ":memory:":
        args.db = ""

    load_dataset(args.metadata, args.lexicon, args.db, args.cogsets)

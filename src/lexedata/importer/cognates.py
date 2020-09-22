from pathlib import Path
from tempfile import mkdtemp
import typing as t
from lexedata.types import *

import openpyxl
import lexedata.importer.cellparser as cell_parsers
from lexedata.util import string_to_id, clean_cell_value, get_cell_comment
from lexedata.importer.fromexcel import ExcelCognateParser, ExcelParserDictionaryDB


if __name__ == "__main__":
    import argparse
    import pycldf
    parser = argparse.ArgumentParser(description="Load a Maweti-Guarani-style dataset into CLDF")
    parser.add_argument(
        "cogsets", nargs="?",
        default="Cognates.xlsx",
        help="Path to an Excel file containing cogsets and cognatejudgements")
    parser.add_argument(
        "--db", nargs="?",
        default="",
        help="Where to store the temp from reading the word list")
    parser.add_argument(
        "--metadata", nargs="?", type=Path,
        default="Wordlist-metadata.json",
        help="Path to the metadata.json file (default: ./Wordlist-metadata.json)")
    parser.add_argument(
        "--debug-level", type=int, default=0,
        help="Debug level: Higher numbers are less forgiving")
    args = parser.parse_args()

    if args.db.startswith("sqlite:///"):
        args.db = args.db[len("sqlite:///"):]
    if args.db == ":memory:":
        args.db = ""
    # Refuse in-memory DBs and use a temporary file instead. TODO: Actually,
    # now that we have recovered and are back to using only CLDF, we should
    # permit in-memory DBs again, they might be a lot faster on machines where
    # temporary files do not live in RAM.

    db = args.db
    if db == "":
        tmpdir = Path(mkdtemp("", "fromexcel"))
        db = tmpdir / 'db.sqlite'
    ws = openpyxl.load_workbook(args.cogsets).active

    dataset = pycldf.Dataset.from_metadata(args.metadata)

    # TODO the following lines of code would make a good template for the
    # import of cognate sets in fromexcel. Can we write a single function for
    # both use cases?

    try:
        c_comment = dataset["CognatesetTable", "comment"].name
        comment_column = True
    except KeyError:
        c_comment = None
        comment_column = False

    row_header = []
    for header, in ws.iter_cols(
            min_row=1, max_row=1,
            max_col=len(dataset["CognatesetTable"].tableSchema.columns)):
        column_name = header.value
        if column_name is None:
            column_name = dataset["CognatesetTable", "id"].name
        elif column_name == "CogSet":
            column_name = dataset["CognatesetTable", "id"].name
        try:
            column_name = dataset["CognatesetTable", column_name].name
        except KeyError:
            break
        row_header.append(column_name)

    class Parser(ExcelParserDictionaryDB, ExcelCognateParser):
        def language_from_column(
            self, column: t.List[openpyxl.cell.Cell]
        ) -> Language:
            data = [clean_cell_value(cell) for cell in column[:self.top - 1]]
            comment = get_cell_comment(column[0])
            id = string_to_id(data[0])
            return Language({
                # an id candidate must be provided, which is transformed into a unique id
                dataset["LanguageTable", "name"].name: data[0],
            })

        def properties_from_row(
                self, row: t.List[openpyxl.cell.Cell]
        ) -> t.Optional[RowObject]:
            data = [clean_cell_value(cell) for cell in row[:self.left - 1]]
            properties = dict(zip(self.row_header, data))
            if not any(properties.values()):
                return None
            # delete all possible None entries coming from row_header
            while None in properties.keys():
                del properties[None]

            comment = get_cell_comment(row[0])
            # TODO: add comment
            return CogSet(properties)




    excel_parser_cognate = Parser(
        dataset, db,
        top = 2,
        # When the dataset has cognateset comments, that column is not a header
        # column, so this value is one higher than the actual number of header
        # columns, so actually correct for the 1-based indices. When there is
        # no comment column, we need to compensate for the 1-based Excel
        # indices.
        cellparser = cell_parsers.CellParserHyperlink(),
        row_header = row_header,
        check_for_language_match = ["name"],
        check_for_match = ["id"],
        check_for_row_match = ["id"])


    # TODO: This often doesn't work if the dataset is not perfect before this
    # program is called. In particular, it doesn't work if there are errors in
    # the cognate sets or judgements, which will be reset in just a moment. How
    # else should we solve this?
    excel_parser_cognate.cache_dataset()
    excel_parser_cognate.drop_from_cache("CognatesetTable")
    excel_parser_cognate.drop_from_cache("CognateTable")
    excel_parser_cognate.parse_cells(ws)
    for table_type in ["CognateTable", "CognatesetTable"]:
        excel_parser_cognate._ExcelParserDictionaryDB__dataset[table_type].common_props['dc:extent'] = excel_parser_cognate._ExcelParserDictionaryDB__dataset[table_type].write(
            excel_parser_cognate.retrieve(table_type))

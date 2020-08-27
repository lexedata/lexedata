from pathlib import Path
from tempfile import mkdtemp

import openpyxl
import lexedata.importer.cellparser as cell_parsers
from lexedata.importer.fromexcel import ExcelCognateParser


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

    excel_parser_cognate = ExcelCognateParser(
        dataset, db, 2,
        len(dataset["CognatesetTable"].tableSchema.columns) + (
            1 if not comment_column else 0),
        # When the dataset has cognateset comments, that column is not a header
        # column, so this value is one higher than the actual number of header
        # columns, so actually correct for the 1-based indices. When there is
        # no comment column, we need to compensate for the 1-based Excel
        # indices.
        cell_parsers.CellParserHyperlink(),
        check_for_row_match=["cldf_name"])
    # TODO: This often doesn't work if the dataset is not perfect before this
    # program is called. In particular, it doesn't work if there are errors in
    # the cognate sets or judgements, which will be reset in just a moment. How
    # else should we solve this?
    excel_parser_cognate.cldfdatabase.write_from_tg(_force=True)
    with excel_parser_cognate.cldfdatabase.connection() as conn:
        # TODO: Is there a way around throwing away the entire cognateset
        # table?
        conn.execute("DELETE FROM CognatesetTable")
        conn.execute("DELETE FROM CognateTable")
        conn.commit()
    excel_parser_cognate.parse_cells(ws)
    data = excel_parser_cognate.cldfdatabase.read()
    for table_type in ["CognateTable", "CognatesetTable"]:
        items = data[table_type]
        table = excel_parser_cognate.cldfdatabase.dataset[table_type]
        table.common_props['dc:extent'] = table.write(
            [excel_parser_cognate.cldfdatabase.retranslate(table, item)
             for item in items])

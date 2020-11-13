import pytest
import shutil
import tempfile
from pathlib import Path

import pycldf
import openpyxl

import lexedata.importer.fromexcel as f
from lexedata.exporter.cognates import ExcelWriter
import lexedata.importer.cellparser as cell_parsers
from lexedata.importer.cognates import CognateEditParser

# todo: these test must be adapted to new interface of fromexcel.py


@pytest.fixture(
    params=[
        "data/cldf/minimal/cldf-metadata.json",
        "data/cldf/smallmawetiguarani/cldf-metadata.json",
    ]
)
def cldf_wordlist(request):
    return Path(__file__).parent / request.param


def empty_copy_of_cldf_wordlist(cldf_wordlist):
    # Copy the dataset metadata file to a temporary directory.
    original = Path(__file__).parent / cldf_wordlist
    dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    target = dirname / original.name
    shutil.copyfile(original, target)
    # Create empty (because of the empty row list passed) csv files for the
    # dataset, one for each table, with only the appropriate headers in there.
    dataset = pycldf.Dataset.from_metadata(target)
    dataset.write(**{str(table.url): [] for table in dataset.tables})
    # Return the dataset API handle, which knows the metadata and tables.
    return dataset, original


@pytest.fixture
def excel_wordlist():
    return (
        Path(__file__).parent / "data/excel/small.xlsx",
        Path(__file__).parent / "data/excel/small_cog.xlsx",
        empty_copy_of_cldf_wordlist(
            Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
        ),
    )


def copy_to_temp(cldf_wordlist):
    # Copy the dataset to a different temporary location, so that editing the
    # dataset will not change it.
    original = cldf_wordlist
    dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    target = dirname / original.name
    shutil.copyfile(original, target)
    dataset = pycldf.Dataset.from_metadata(target)
    for table in dataset.tables:
        link = Path(str(table.url))
        o = original.parent / link
        t = target.parent / link
        shutil.copyfile(o, t)
    link = dataset.bibpath.name
    o = original.parent / link
    t = target.parent / link
    shutil.copyfile(o, t)
    dataset.sources = pycldf.dataset.Sources.from_file(dataset.bibpath)
    return dataset, target


def test_fromexcel_runs(excel_wordlist):
    lexicon, cogsets, (empty_dataset, original) = excel_wordlist
    f.load_dataset(
        Path(empty_dataset.tablegroup._fname), str(lexicon), "", str(cogsets)
    )


def test_fromexcel_correct(excel_wordlist):
    lexicon, cogsets, (empty_dataset, original_md) = excel_wordlist
    original = pycldf.Wordlist.from_metadata(original_md)
    # TODO: parameterize original, like the other parameters, over possible
    # test datasets.
    f.load_dataset(
        Path(empty_dataset.tablegroup._fname), str(lexicon), "", str(cogsets)
    )
    form_ids_from_excel = {form["ID"] for form in empty_dataset["FormTable"]}
    form_ids_original = {form["ID"] for form in original["FormTable"]}
    cognate_ids_from_excel = {cognate["ID"] for cognate in empty_dataset["CognateTable"]}
    cognate_ids_original = {form["ID"] for form in original["CognateTable"]}
    assert form_ids_original == form_ids_from_excel, "{:} and {:} don't match.".format(
        empty_dataset["FormTable"]._parent._fname.parent
        / str(empty_dataset["FormTable"].url),
        original["FormTable"]._parent._fname.parent
        / str(empty_dataset["FormTable"].url),
    )
    assert cognate_ids_original == cognate_ids_from_excel, "{:} and {:} don't match.".format(
        empty_dataset["CognateTable"]._parent._fname.parent
        / str(empty_dataset["CognateTable"].url),
        original["CognateTable"]._parent._fname.parent
        / str(empty_dataset["CognateTable"].url),
    )


def test_toexcel_runs(cldf_wordlist):
    filled_cldf_wordlist = copy_to_temp(cldf_wordlist)
    writer = ExcelWriter(
        dataset=filled_cldf_wordlist[0],
        database_url=filled_cldf_wordlist[1],
        override_database=True,
    )
    _, out_filename = tempfile.mkstemp(".xlsx", "cognates")
    writer.create_excel(out_filename)


def test_roundtrip(cldf_wordlist):
    filled_cldf_wordlist = copy_to_temp(cldf_wordlist)
    dataset, target = filled_cldf_wordlist
    c_formReference = dataset["CognateTable", "formReference"].name
    c_cogsetReference = dataset["CognateTable", "cognatesetReference"].name
    old_judgements = {
        (row[c_formReference], row[c_cogsetReference])
        for row in dataset["CognateTable"].iterdicts()
    }
    writer = ExcelWriter(dataset)
    _, out_filename = tempfile.mkstemp(".xlsx", "cognates")
    writer.create_excel(out_filename)

    # Reset the existing cognatesets and cognate judgements, to avoid
    # interference with the the data in the Excel file
    dataset["CognateTable"].write([])
    dataset["CognatesetTable"].write([])

    ws_out = openpyxl.load_workbook(out_filename).active

    row_header = []
    for (header,) in ws_out.iter_cols(
        min_row=1,
        max_row=1,
        max_col=len(dataset["CognatesetTable"].tableSchema.columns),
    ):
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

    excel_parser_cognate = CognateEditParser(
        dataset,
        None,
        top=2,
        # When the dataset has cognateset comments, that column is not a header
        # column, so this value is one higher than the actual number of header
        # columns, so actually correct for the 1-based indices. When there is
        # no comment column, we need to compensate for the 1-based Excel
        # indices.
        cellparser=cell_parsers.CellParserHyperlink(dataset),
        row_header=row_header,
        check_for_language_match=[dataset["LanguageTable", "name"].name],
        check_for_match=[dataset["FormTable", "id"].name],
        check_for_row_match=[dataset["CognatesetTable", "id"].name],
    )

    # TODO: This often doesn't work if the dataset is not perfect before this
    # program is called. In particular, it doesn't work if there are errors in
    # the cognate sets or judgements, which will be reset in just a moment. How
    # else should we solve this?
    excel_parser_cognate.db.cache_dataset()
    excel_parser_cognate.db.drop_from_cache("CognatesetTable")
    excel_parser_cognate.db.drop_from_cache("CognateTable")
    excel_parser_cognate.parse_cells(ws_out)
    excel_parser_cognate.db.write_dataset_from_cache(
        ["CognateTable", "CognatesetTable"]
    )

    new_judgements = {
        (row[c_formReference], row[c_cogsetReference])
        for row in dataset["CognateTable"].iterdicts()
    }

    assert new_judgements == old_judgements


def test_cell_comments():
    dataset, _ = copy_to_temp(
        Path(__file__).parent / "data/cldf/minimal/cldf-metadata.json"
    )
    ws_test = openpyxl.load_workbook(
        Path(__file__).parent / "data/excel/judgement_cell_with_note.xlsx"
    ).active

    row_header = []
    for (header,) in ws_test.iter_cols(
        min_row=1,
        max_row=1,
        max_col=len(dataset["CognatesetTable"].tableSchema.columns),
    ):
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

    excel_parser_cognate = CognateEditParser(
        dataset,
        None,
        top=2,
        # When the dataset has cognateset comments, that column is not a header
        # column, so this value is one higher than the actual number of header
        # columns, so actually correct for the 1-based indices. When there is
        # no comment column, we need to compensate for the 1-based Excel
        # indices.
        cellparser=cell_parsers.CellParserHyperlink(dataset),
        row_header=row_header,
        check_for_language_match=[dataset["LanguageTable", "name"].name],
        check_for_match=[dataset["FormTable", "id"].name],
        check_for_row_match=[dataset["CognatesetTable", "id"].name],
    )

    # TODO: This often doesn't work if the dataset is not perfect before this
    # program is called. In particular, it doesn't work if there are errors in
    # the cognate sets or judgements, which will be reset in just a moment. How
    # else should we solve this?
    excel_parser_cognate.db.cache_dataset()
    excel_parser_cognate.db.drop_from_cache("CognatesetTable")
    excel_parser_cognate.db.drop_from_cache("CognateTable")
    excel_parser_cognate.parse_cells(ws_test)

    assert excel_parser_cognate.db.cache["CognateTable"] == {
        "aaa_1209-cogset": {
            "ID": "aaa_1209-cogset",
            "Form_ID": "aaa_1209",
            "Cognateset": "cogset",
            "Comment": "Comment on judgement",
        }
    }
    assert excel_parser_cognate.db.cache["CognatesetTable"] == {
        "cogset": {"Name": "cogset", "Comment": "Cognateset-comment", "ID": "cogset"}
    }

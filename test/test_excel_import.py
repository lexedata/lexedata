import pytest
from pathlib import Path
import argparse

import pycldf
import openpyxl

import lexedata.importer.fromexcel as f
from fixtures import copy_metadata, copy_to_temp


def test_no_wordlist_and_no_cogsets(fs):
    with pytest.raises(argparse.ArgumentError) as err:
        #mock empty json file
        fs.create_file("invented_path", contents="{}")
        f.load_dataset(
            metadata="invented_path",
            lexicon=None,
            cognate_lexicon=None,
        )
    assert (
        str(err.value)
        == "At least one of WORDLIST and COGNATESETS excel files must be specified"
    )


@pytest.fixture
def empty_excel():
    return Path(__file__).parent / "data/cldf/defective_dataset/empty_excel.xlsx""


def test_no_dialect_excel_parser(fs, caplog, empty_excel):
    # ExcelParser
    with pytest.raises(ValueError):
        # mock empty json file
        fs.create_file("invented_path", contents="{}")
        f.load_dataset(
            metadata="invented_path",
            lexicon=empty_excel
            ,
        )
        assert caplog.text.endswith(
            "User-defined format specification in the json-file was missing, falling back to default parser"
        )


def test_no_dialect_excel_cognate_parser(fs, caplog, empty_excel):
    # ExcelCognateParser
    with pytest.raises(ValueError):
        # mock empty json file
        fs.create_file("invented_path", contents="{}")
        f.load_dataset(
            metadata="invented_path",
            lexicon=None,
            cognate_lexicon=empty_excel
        )
        assert caplog.text.endswith(
            "User-defined format specification in the json-file was missing, falling back to default parser"
        )


def test_dialect_missing_key_excel_parser(fs, caplog, empty_excel):
    # ExcelParser
    with pytest.raises(ValueError):
        fs.create_file(
            "invented_path", contents="""{"special:fromexcel": {}}"""
        )
        f.load_dataset("invented_path", lexicon=empty_excel)
    assert caplog.text.endswith(
        "User-defined format specification in the json-file was missing the key lang_cell_regexes, "
        "falling back to default parser\n"
    )


def test_dialect_missing_key_excel_cognate_parser(caplog, empty_excel):
    # CognateExcelParser
    with pytest.raises(ValueError):
        fs.create_file(
            "invented_path", contents="""{"special:fromexcel": {}}"""
        )
        f.load_dataset("invented_path", lexicon=None, cognate_lexicon=empty_excel)
    assert caplog.text.endswith(
        "User-defined format specification in the json-file was missing the key lang_cell_regexes, "
        "falling back to default parser\n"
    )


def test_no_first_row_in_excel(empty_excel):
    original = Path(__file__).parent / "data/cldf/minimal/cldf-metadata.json"
    copy = copy_metadata(original=original)
    with pytest.raises(AssertionError) as err:
        f.load_dataset(
            metadata=copy,
            lexicon=empty_excel
        )
    assert (
        str(err.value) == "Your first data row didn't have a name. "
        "Please check your format specification or ensure the first row has a name."
    )


def test_language_regex_error():
    excel = (
        Path(__file__).parent
        / "data/cldf/defective_dataset/small_defective_no_regexes.xlsx"
    )
    original = Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    copy = copy_metadata(original=original)

    dataset = pycldf.Dataset.from_metadata(copy)
    dialect = argparse.Namespace(**dataset.tablegroup.common_props["special:fromexcel"])
    lexicon_wb = openpyxl.load_workbook(excel).active
    dialect.lang_cell_regexes = [r"(?P<Name>\[.*)", "(?P<Curator>.*)"]
    EP = f.excel_parser_from_dialect(dataset, dialect, cognate=False)
    EP = EP(dataset)

    with pytest.raises(ValueError) as err:
        EP.parse_cells(lexicon_wb)
    assert (
        str(err.value)
        == r"In cell G1: Expected to encounter match for (?P<Name>\[.*), but found no_language"
    )


def test_language_comment_regex_error():
    excel = (
        Path(__file__).parent
        / "data/cldf/defective_dataset/small_defective_no_regexes.xlsx"
    )
    original = Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    copy = copy_metadata(original=original)

    dataset = pycldf.Dataset.from_metadata(copy)
    dialect = argparse.Namespace(**dataset.tablegroup.common_props["special:fromexcel"])
    lexicon_wb = openpyxl.load_workbook(excel).active
    dialect.lang_comment_regexes = [r"\[.*", ".*"]

    EP = f.excel_parser_from_dialect(dataset, dialect, cognate=False)
    EP = EP(dataset)
    with pytest.raises(ValueError) as err:
        EP.parse_cells(lexicon_wb)
    assert (
        str(err.value)
        == r"In cell G1: Expected to encounter match for \[.*, but found no_lan_comment"
    )


def test_properties_regex_error():
    excel = (
        Path(__file__).parent
        / "data/cldf/defective_dataset/small_defective_no_regexes.xlsx"
    )
    original = Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    copy = copy_metadata(original=original)

    dataset = pycldf.Dataset.from_metadata(copy)
    dialect = argparse.Namespace(**dataset.tablegroup.common_props["special:fromexcel"])
    lexicon_wb = openpyxl.load_workbook(excel).active
    dialect.row_cell_regexes = [
        "(?P<set>.*)",
        r"(?P<Name>\[.*)",
        "(?P<English>.*)",
        "(?P<Spanish>.*)",
        "(?P<Portuguese>.*)",
        "(?P<French>.*)",
    ]
    EP = f.excel_parser_from_dialect(dataset, dialect, cognate=False)
    EP = EP(dataset)

    with pytest.raises(ValueError) as err:
        EP.parse_cells(lexicon_wb)
    assert (
        str(err.value)
        == r"In cell B3: Expected to encounter match for (?P<Name>\[.*), but found no_concept_name"
    )


def test_properties_comment_regex_error():
    excel = (
        Path(__file__).parent
        / "data/cldf/defective_dataset/small_defective_no_regexes.xlsx"
    )
    original = Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    copy = copy_metadata(original=original)

    dataset = pycldf.Dataset.from_metadata(copy)
    dialect = argparse.Namespace(**dataset.tablegroup.common_props["special:fromexcel"])
    lexicon_wb = openpyxl.load_workbook(excel).active
    dialect.row_comment_regexes = [".*", r"\[.*", ".*", ".*", ".*", ".*"]
    EP = f.excel_parser_from_dialect(dataset, dialect, cognate=False)
    EP = EP(dataset)
    with pytest.raises(ValueError) as err:
        EP.parse_cells(lexicon_wb)
    assert (
        str(err.value)
        == r"In cell B3: Expected to encounter match for \[.*, but found no_concept_comment"
    )


def test_cognate_parser_language_not_found():
    excel = Path(__file__).parent / "data/excel/minimal_cog.xlsx"
    original = Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    dataset, copy = copy_to_temp(original)
    lexicon_wb = openpyxl.load_workbook(excel).active
    EP = f.ExcelCognateParser(output_dataset=dataset)
    print(dataset["LanguageTable"])
    with pytest.raises(ValueError) as err:
        EP.db.cache_dataset()
        EP.parse_cells(lexicon_wb)
    assert (
        str(err.value)
        == "Failed to find object {'ID': 'autaa', 'Name': 'Autaa', 'Comment': "
        "'fictitious!'} in the database. In cell: D1"
    )

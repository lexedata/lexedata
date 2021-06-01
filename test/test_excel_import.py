import pytest
import shutil
import tempfile
from pathlib import Path
import argparse

import pycldf
import openpyxl

import lexedata.importer.excel_matrix as f
from test_excel_conversion import copy_to_temp


def copy_metadata(original: Path):
    dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    target = dirname / "cldf-metadata.json"
    copy = shutil.copyfile(original, target)
    return copy


# TODO: have a look at this test. just trying to pass codecov
def test_db_chache():
    copy = copy_metadata(
        Path(__file__).parent / "data/cldf/minimal/cldf-metadata.json"
    )
    res = dict()
    dataset = pycldf.Dataset.from_metadata(copy)
    db = f.DB(output_dataset=dataset)
    db.cache_dataset()
    for table in dataset.tables:
        table_type = (
            table.common_props.get("dc:conformsTo", "").rsplit("#", 1)[1] or table.url
        )
        res[table_type] = {}
    assert db.cache == res


def test_no_wordlist_and_no_cogsets():

    with pytest.raises(argparse.ArgumentError) as err:
        f.load_dataset(
            metadata=Path(__file__).parent
            / "data/cldf/defective_dataset/wordlist-metadata_minimal_no_dialect.json",
            lexicon=None,
            cognate_lexicon=None,
        )
    assert (
        str(err.value)
        == "At least one of WORDLIST and COGNATESETS excel files must be specified"
    )


def test_no_dialect_excel_parser(caplog):
    # ExcelParser
    with pytest.raises(ValueError):
        f.load_dataset(
            metadata=Path(__file__).parent
            / "data/cldf/defective_dataset/wordlist-metadata_minimal_no_dialect.json",
            lexicon=Path(__file__).parent
            / "data/cldf/defective_dataset/empty_excel.xlsx",
        )
        assert caplog.text.endswith(
            "User-defined format specification in the json-file was missing, falling back to default parser"
        )


def test_no_dialect_excel_cognate_parser(caplog):
    # ExcelCognateParser
    with pytest.raises(ValueError):
        f.load_dataset(
            metadata=Path(__file__).parent
            / "data/cldf/defective_dataset/wordlist-metadata_minimal_no_dialect.json",
            lexicon=None,
            cognate_lexicon=Path(__file__).parent
            / "data/cldf/defective_dataset/empty_excel.xlsx",
        )
        assert caplog.text.endswith(
            "User-defined format specification in the json-file was missing, falling back to default parser"
        )


def test_dialect_missing_key_excel_parser(caplog):
    excel = Path(__file__).parent / "data/cldf/defective_dataset/empty_excel.xlsx"
    original = (
        Path(__file__).parent
        / "data/cldf/defective_dataset/wordlist-metadata_no_lang_cell_regexes.json"
    )
    copy = copy_metadata(original=original)

    # ExcelParser
    with pytest.raises(ValueError):
        f.load_dataset(copy, lexicon=excel)
    assert caplog.text.endswith(
        "User-defined format specification in the json-file was missing the key lang_cell_regexes, "
        "falling back to default parser\n"
    )


def test_dialect_missing_key_excel_cognate_parser(caplog):
    excel = Path(__file__).parent / "data/cldf/defective_dataset/empty_excel.xlsx"
    original = (
        Path(__file__).parent
        / "data/cldf/defective_dataset/wordlist-metadata_no_lang_cell_regexes.json"
    )
    copy = copy_metadata(original=original)
    # CognateExcelParser
    with pytest.raises(ValueError) as err:
        f.load_dataset(copy, lexicon=None, cognate_lexicon=excel)
    print(err.value)
    assert caplog.text.endswith(
        "User-defined format specification in the json-file was missing the key lang_cell_regexes, "
        "falling back to default parser\n"
    )


def test_no_first_row_in_excel():
    original = Path(__file__).parent / "data/cldf/minimal/cldf-metadata.json"
    copy = copy_metadata(original=original)
    with pytest.raises(AssertionError) as err:
        f.load_dataset(
            metadata=copy,
            lexicon=Path(__file__).parent
            / "data/cldf/defective_dataset/empty_excel.xlsx",
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

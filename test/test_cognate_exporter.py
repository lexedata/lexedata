import re
import logging
from pathlib import Path

import pytest

from lexedata import util
from helper_functions import empty_copy_of_cldf_wordlist, copy_to_temp
from lexedata.util.fs import get_dataset
from lexedata.exporter.cognates import (
    ExcelWriter,
    create_singletons,
    properties_as_key,
    sort_cognatesets,
    cogsets_and_judgements,
)

try:
    from pycldf.dataset import SchemaError
except ImportError:
    # SchemaError was introduced in pycldf 1.24.0
    SchemaError = KeyError


@pytest.fixture
def tiny_dataset():
    ds = util.fs.new_wordlist(
        FormTable=[{"ID": "f1"}],
        CognatesetTable=[
            {"ID": "s1", "Source": "3", "Description": "A"},
            {"ID": "s2", "Source": "3", "Description": "A"},
            {"ID": "s3", "Source": "3", "Description": "A"},
            {"ID": "s4", "Source": "1", "Description": "C"},
            {"ID": "s5", "Source": "1", "Description": "C"},
        ],
        CognateTable=[
            {"ID": f"{i}{n}", "Cognateset_ID": f"s{i}", "Form_ID": "f1"}
            for i in range(1, 6)
            for n in range(i)
        ],
    )
    cognatesets = list(util.cache_table(ds, "CognatesetTable").values())
    judgements = util.cache_table(ds, "CognateTable").values()
    return cognatesets, judgements


def test_sort_cognatesets_1(tiny_dataset):
    cognatesets, judgements = tiny_dataset
    # Without sort-order arguments, sort_cognatesets changes nothing.
    sort_cognatesets(cognatesets, judgements, size=False)
    assert [s["id"] for s in cognatesets] == ["s1", "s2", "s3", "s4", "s5"]


def test_sort_cognatesets_2(tiny_dataset):
    cognatesets, judgements = tiny_dataset
    # Order by group keeps the order within the group the same.
    sort_cognatesets(cognatesets, judgements, "source", size=False)
    assert [s["id"] for s in cognatesets] == ["s4", "s5", "s1", "s2", "s3"]


def test_sort_cognatesets_3(tiny_dataset):
    cognatesets, judgements = tiny_dataset
    # Order by size does just that (biggest first)
    sort_cognatesets(cognatesets, judgements, size=True)
    assert [s["id"] for s in cognatesets] == ["s5", "s4", "s3", "s2", "s1"]


def test_sort_cognatesets_4(tiny_dataset):
    cognatesets, judgements = tiny_dataset
    # Order by group and size has priority on the group
    sort_cognatesets(cognatesets, judgements, "description", size=True)
    assert [s["id"] for s in cognatesets] == ["s3", "s2", "s1", "s5", "s4"]


def test_cogsets_and_judgements():
    dataset = get_dataset(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    cogsets, judgements = cogsets_and_judgements(dataset, None, by_segment=True)
    assert list(cogsets)[0] == {
        "id": "one1",
        "Set": None,
        "comment": None,
        "name": "ONE1",
    }
    assert list(cogsets)[-1] == {
        "id": "five5",
        "Set": None,
        "comment": None,
        "name": "FIVE5",
    }
    assert len(cogsets) == 10
    assert list(judgements)[0] == {
        "id": "paraguayan_guarani_one-one1",
        "formReference": "paraguayan_guarani_one",
        "comment": None,
        "segmentSlice": ["1:5"],
        "alignment": ["p", "e", "t", "e", "ĩ", "-", "-"],
        "cognatesetReference": "one1",
    }
    assert list(judgements)[-1] == {
        "id": "kaiwa_five-five5",
        "formReference": "kaiwa_five",
        "comment": None,
        "segmentSlice": ["1:7"],
        "alignment": ["t", "e", "ʔ", "i", "o", "w", "aa"],
        "cognatesetReference": "five5",
    }
    assert len(judgements) == 17


def test_cogsets_and_judgements_with_singletons():
    dataset = get_dataset(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    cogsets, judgements = cogsets_and_judgements(dataset, "NEW", by_segment=True)
    assert list(cogsets)[0] == {
        "id": "one1",
        "Set": None,
        "comment": None,
        "name": "ONE1",
    }
    assert list(cogsets)[-1] == {
        "Set": None,
        "id": "X_paraguayan_guarani_five_1",
        "comment": None,
        "name": "five",
    }
    assert len(cogsets) == 14
    assert list(judgements)[0] == {
        "id": "paraguayan_guarani_one-one1",
        "formReference": "paraguayan_guarani_one",
        "comment": None,
        "segmentSlice": ["1:5"],
        "alignment": ["p", "e", "t", "e", "ĩ", "-", "-"],
        "cognatesetReference": "one1",
    }
    assert list(judgements)[-1] == {
        "id": "X_paraguayan_guarani_five_1",
        "formReference": "paraguayan_guarani_five",
        "comment": None,
        "segmentSlice": ["1:2"],
        "alignment": ["p", "o"],
        "cognatesetReference": "X_paraguayan_guarani_five_1",
    }
    assert len(judgements) == 21


def test_adding_singleton_cognatesets(caplog):
    dataset = get_dataset(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    with caplog.at_level(logging.WARNING):
        excel_writer = ExcelWriter(
            dataset=dataset,
        )
        cogsets, judgements = create_singletons(
            dataset,
            status="NEW",
            by_segment=False,
        )
        properties_as_key(cogsets, dataset["CognatesetTable"].tableSchema.columns)
        properties_as_key(judgements, dataset["CognateTable"].tableSchema.columns)
        forms = util.cache_table(dataset)
        languages = util.cache_table(dataset, "LanguageTable").values()
        excel_writer.create_excel(
            rows=cogsets, judgements=judgements, forms=forms, languages=languages
        )
    assert re.search("No Status_Column", caplog.text)

    # load central concepts from output
    cogset_index = 0
    for row in excel_writer.ws.iter_rows(min_row=1, max_row=1):
        for cell in row:
            if cell.value == "CogSet":
                cogset_index = cell.column - 1
    # when accessing the row as a tuple the index is not 1-based as for excel sheets
    cogset_ids = [
        row[cogset_index].value for row in excel_writer.ws.iter_rows(min_row=2)
    ]
    assert cogset_ids == [
        "one1",
        "one1",
        "one2",
        "one6",
        "two1",
        "three1",
        "two8",
        "three9",
        "four1",
        "four8",
        "five5",
        "X_old_paraguayan_guarani_two_1",
        "X_paraguayan_guarani_five_1",
    ]


def test_adding_singleton_cognatesets_with_status(caplog):
    dataset = get_dataset(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    dataset.add_columns("CognatesetTable", "Status_Column")
    with caplog.at_level(logging.WARNING):
        excel_writer = ExcelWriter(dataset=dataset)
        cogsets, judgements = create_singletons(
            dataset,
            status="NEW",
            by_segment=True,
        )
        properties_as_key(cogsets, dataset["CognatesetTable"].tableSchema.columns)
        properties_as_key(judgements, dataset["CognateTable"].tableSchema.columns)
        forms = util.cache_table(dataset)
        languages = util.cache_table(dataset, "LanguageTable").values()
        excel_writer.create_excel(
            rows=cogsets, judgements=judgements, forms=forms, languages=languages
        )
    assert re.search("no Status_Column to write", caplog.text) is None

    cogset_index = 0
    for row in excel_writer.ws.iter_rows(min_row=1, max_row=1):
        for cell in row:
            if cell.value == "Status_Column":
                cogset_index = cell.column - 1
    # when accessing the row as a tuple the index is not 1-based as for excel sheets
    status = [row[cogset_index].value for row in excel_writer.ws.iter_rows(min_row=2)]
    assert status == [
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        "NEW",
        "NEW",
        "NEW",
        "NEW",
    ]


def test_no_cognateset_table(caplog):
    dataset, _ = empty_copy_of_cldf_wordlist(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    dataset.remove_table("CognatesetTable")
    # TODO: SystemExit or dataset error?
    with pytest.raises((SystemExit, SchemaError)) as exc_info:
        ExcelWriter(
            dataset=dataset,
        )
    if exc_info.type == SystemExit:
        assert "presupposes a separate CognatesetTable" in caplog.text
        assert "lexedata.edit.add_table" in caplog.text


def test_no_cognate_table(caplog):
    dataset, _ = empty_copy_of_cldf_wordlist(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    dataset.remove_table("CognateTable")
    with pytest.raises(SystemExit):
        ExcelWriter(
            dataset=dataset,
        )
    assert "presupposes a separate CognateTable" in caplog.text
    assert "lexedata.edit.add_cognate_table" in caplog.text


@pytest.mark.filterwarnings("ignore:Unspecified column")
def test_no_comment_column():
    dataset, _ = copy_to_temp(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    dataset.remove_columns("FormTable", "comment")
    writer = ExcelWriter(
        dataset=dataset,
    )
    forms = util.cache_table(dataset).values()
    for form in forms:
        assert writer.form_to_cell_value(form).strip() == "{ e t a k ɾ ã } ‘one, one’"
        break


def test_missing_required_column():
    dataset, _ = copy_to_temp(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    dataset.remove_columns("FormTable", "ID")
    # TODO: switch to pycldf.dataset.SchemaError
    with pytest.raises(KeyError):
        excel_writer = ExcelWriter(dataset=dataset)
        forms = util.cache_table(dataset)
        languages = util.cache_table(dataset, "LanguageTable").values()
        judgements = util.cache_table(dataset, "CognateTable")
        cogsets = util.cache_table(dataset, "CognatesetTable")
        excel_writer.create_excel(
            rows=cogsets, judgements=judgements, forms=forms, languages=languages
        )


def test_included_segments(caplog):
    ds = util.fs.new_wordlist(FormTable=[], CognatesetTable=[], CognateTable=[])
    E = ExcelWriter(dataset=ds)
    E.form_to_cell_value({"form": "f", "parameterReference": "c"})
    with caplog.at_level(logging.WARNING):
        cell = E.form_to_cell_value(
            {
                "id": "0",
                "cognateReference": "j",
                "form": "fo",
                "parameterReference": "c",
                "segments": ["f", "o"],
                "segmentSlice": ["3:1"],
            }
        )
        assert cell == "{ f o } ‘c’"

    assert re.search("segment slice '3:1' is invalid", caplog.text) is None

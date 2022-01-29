import logging
from pathlib import Path
import re

from lexedata.edit.add_singleton_cognatesets import (
    create_singletons,
    uncoded_segments,
    uncoded_forms,
)
from lexedata.edit.add_status_column import add_status_column_to_table
from helper_functions import copy_to_temp_no_bib


def test_no_status_column(caplog):
    dataset, _ = copy_to_temp_no_bib(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    caplog.set_level(logging.INFO)
    create_singletons(dataset=dataset)
    assert re.search(r".*No Status_Column.*", caplog.text)


def test_uncoded_segments():
    segments = uncoded_segments(
        {
            "f1": [{}, {}, {"s1"}, {}],
            "f2": [{"s1"}, {"s1"}, {"s1"}, {"s1"}],
            "f3": [{}, {}, {"s1"}, {"s1"}],
            "f4": [{"s1"}, {"s1"}, {"s1"}, {}],
            "f5": [{"s1"}, {}, {"s1"}, {"s1"}],
        }
    )
    assert list(segments) == [
        ("f1", range(0, 2)),
        ("f1", range(3, 4)),
        ("f3", range(0, 2)),
        ("f4", range(3, 4)),
        ("f5", range(1, 2)),
    ]


def test_uncoded_forms():
    segments = list(
        uncoded_forms(
            [
                {"id": "f1", "segments": ["e", "x"]},
                {"id": "f2", "segments": ["t", "e", "s", "t"]},
                {"id": "f3", "segments": ["l", "o", "n", "g", "e", "r"]},
            ],
            {"f2"},
        )
    )
    assert list(segments) == [
        ("f1", range(2)),
        ("f3", range(6)),
    ]


def test_singletons():
    dataset, _ = copy_to_temp_no_bib(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    add_status_column_to_table(dataset=dataset, table_name="CognatesetTable")

    all_cogsets, judgements = create_singletons(
        dataset=dataset, status="automatic singleton"
    )
    c_c_id = dataset["CognateTable", "id"].name
    c_cs_id = dataset["CognatesetTable", "id"].name
    cognates = [c for c in judgements if c[c_c_id].startswith("X")]
    cogsets = [c for c in all_cogsets if c[c_cs_id].startswith("X")]
    assert cognates == [
        {
            "ID": "X_old_paraguayan_guarani_two_1",
            "FIXME_IF_you_set_this_column_name_to_Value_it_messes_up_translations_due_to_conflict": "X_old_paraguayan_guarani_two_1",
            "Form_ID": "old_paraguayan_guarani_two",
            "Segment_Slice": ["1:5"],
            "Alignment": ["p", "a", "t", "h", "á"],
            "Status_Column": "automatic singleton",
        },
        {
            "ID": "X_paraguayan_guarani_five_1",
            "FIXME_IF_you_set_this_column_name_to_Value_it_messes_up_translations_due_to_conflict": "X_paraguayan_guarani_five_1",
            "Form_ID": "paraguayan_guarani_five",
            "Segment_Slice": ["1:2"],
            "Alignment": ["p", "o"],
            "Status_Column": "automatic singleton",
        },
        {
            "ID": "X_ache_five_1",
            "FIXME_IF_you_set_this_column_name_to_Value_it_messes_up_translations_due_to_conflict": "X_ache_five_1",
            "Form_ID": "ache_five",
            "Segment_Slice": ["1:0"],
            "Alignment": [],
            "Status_Column": "automatic singleton",
        },
    ]

    assert cogsets == [
        {
            "ID": "X_old_paraguayan_guarani_two_1",
            "Name": "two",
            "Status_Column": "automatic singleton",
        },
        {
            "ID": "X_paraguayan_guarani_five_1",
            "Name": "five",
            "Status_Column": "automatic singleton",
        },
        {"ID": "X_ache_five_1", "Name": "five", "Status_Column": "automatic singleton"},
    ]

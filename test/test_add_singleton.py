import logging
from pathlib import Path
import re

from lexedata.edit.add_singleton_cognatesets import (
    create_singletons,
    uncoded_segments,
    uncoded_forms,
)
from lexedata import types
from lexedata.util.fs import new_wordlist
from lexedata.report.nonconcatenative_morphemes import segment_to_cognateset
from lexedata.edit.add_status_column import add_status_column_to_table
from helper_functions import copy_to_temp_no_bib


def test_no_status_column(caplog):
    dataset, _ = copy_to_temp_no_bib(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    caplog.set_level(logging.INFO)
    create_singletons(dataset=dataset)
    assert re.search(r".*No Status_Column.*", caplog.text)


def test_segment_to_cognateset_no_slices(caplog):
    ds = new_wordlist(
        FormTable=[
            {
                "ID": "f1",
                "Parameter_ID": "c1",
                "Language_ID": "l1",
                "Form": "f",
                "Segments": ["f"],
            },
            {
                "ID": "f2",
                "Parameter_ID": "c1",
                "Language_ID": "l1",
                "Form": "f",
                "Segments": ["f"],
            },
            {
                "ID": "f3",
                "Parameter_ID": "c1",
                "Language_ID": "l1",
                "Form": "f",
                "Segments": ["f", "i"],
            },
            {
                "ID": "f4",
                "Parameter_ID": "c1",
                "Language_ID": "l1",
                "Form": "f",
                "Segments": ["f", "i"],
            },
        ],
        CognateTable=[],
    )
    ds.remove_columns("CognateTable", "Segment_Slice", "Alignment")
    ds.write(
        CognateTable=[
            {"ID": "j1", "Form_ID": "f1", "Cognateset_ID": "s1"},
            {"ID": "j2", "Form_ID": "f3", "Cognateset_ID": "s1"},
            {
                "ID": "j3",
                "Form_ID": "f4",
                "Cognateset_ID": "s1",
            },
            {"ID": "j4", "Form_ID": "f4", "Cognateset_ID": "s2"},
        ],
    )
    with caplog.at_level(logging.WARNING):
        segments = segment_to_cognateset(ds, types.WorldSet())
    assert segments == {
        "f1": [{"s1"}],
        "f2": [set()],
        "f3": [{"s1"}, {"s1"}],
        "f4": [{"s1", "s2"}, {"s1", "s2"}],
    }


def test_create_singletons_no_slices(caplog):
    ds = new_wordlist(
        FormTable=[
            {
                "ID": "f1",
                "Parameter_ID": "c1",
                "Language_ID": "l1",
                "Form": "f",
                "Segments": ["f"],
            },
            {
                "ID": "f2",
                "Parameter_ID": "c1",
                "Language_ID": "l1",
                "Form": "f",
                "Segments": ["f"],
            },
            {
                "ID": "f3",
                "Parameter_ID": "c1",
                "Language_ID": "l1",
                "Form": "f",
                "Segments": ["f", "i"],
            },
            {
                "ID": "f4",
                "Parameter_ID": "c1",
                "Language_ID": "l1",
                "Form": "f",
                "Segments": ["f", "i"],
            },
        ],
        CognateTable=[],
    )
    ds.remove_columns("CognateTable", "Segment_Slice", "Alignment")
    ds.write(
        CognateTable=[
            {"ID": "j1", "Form_ID": "f1", "Cognateset_ID": "s1"},
            {"ID": "j2", "Form_ID": "f3", "Cognateset_ID": "s1"},
            {
                "ID": "j3",
                "Form_ID": "f4",
                "Cognateset_ID": "s1",
            },
            {"ID": "j4", "Form_ID": "f4", "Cognateset_ID": "s2"},
        ],
    )
    with caplog.at_level(logging.WARNING):
        cogsets, judgements = create_singletons(ds)
    assert judgements == [
        {"ID": "j1", "Form_ID": "f1", "Cognateset_ID": "s1", "Source": []},
        {"ID": "j2", "Form_ID": "f3", "Cognateset_ID": "s1", "Source": []},
        {"ID": "j3", "Form_ID": "f4", "Cognateset_ID": "s1", "Source": []},
        {"ID": "j4", "Form_ID": "f4", "Cognateset_ID": "s2", "Source": []},
        {"ID": "x_f2_1", "Form_ID": "f2", "Cognateset_ID": "x_f2_1", "Source": None},
    ]


def test_segment_to_cognateset(caplog):
    ds = new_wordlist(
        FormTable=[
            {
                "ID": "f1",
                "Parameter_ID": "c1",
                "Language_ID": "l1",
                "Form": "f",
                "Segments": ["f"],
            },
            {
                "ID": "f2",
                "Parameter_ID": "c1",
                "Language_ID": "l1",
                "Form": "f",
                "Segments": ["f"],
            },
            {
                "ID": "f3",
                "Parameter_ID": "c1",
                "Language_ID": "l1",
                "Form": "f",
                "Segments": ["f", "i"],
            },
            {
                "ID": "f4",
                "Parameter_ID": "c1",
                "Language_ID": "l1",
                "Form": "f",
                "Segments": ["t", "e", "s", "t"],
            },
        ],
        CognateTable=[
            {"ID": "j1", "Form_ID": "f1", "Cognateset_ID": "s1", "Segment_Slice": "1"},
            {"ID": "j2", "Form_ID": "f3", "Cognateset_ID": "s1", "Segment_Slice": "2"},
            {
                "ID": "j3",
                "Form_ID": "f4",
                "Cognateset_ID": "s1",
                "Segment_Slice": ["2:3"],
            },
            {"ID": "j4", "Form_ID": "f4", "Cognateset_ID": "s2", "Segment_Slice": "2"},
        ],
    )
    with caplog.at_level(logging.WARNING):
        segments = segment_to_cognateset(ds, types.WorldSet())
    assert segments == {
        "f1": [{"s1"}],
        "f2": [set()],
        "f3": [set(), {"s1"}],
        "f4": [set(), {"s1", "s2"}, {"s1"}, set()],
    }


def test_create_singletons_affix(caplog):
    ds = new_wordlist(
        FormTable=[
            {
                "ID": "f1",
                "Parameter_ID": "c1",
                "Language_ID": "l1",
                "Form": "f",
                "Segments": ["f"],
            },
            {
                "ID": "f2",
                "Parameter_ID": "c1",
                "Language_ID": "l1",
                "Form": "f",
                "Segments": ["f"],
            },
            {
                "ID": "f3",
                "Parameter_ID": "c1",
                "Language_ID": "l1",
                "Form": "f",
                "Segments": ["f", "i"],
            },
            {
                "ID": "f4",
                "Parameter_ID": "c1",
                "Language_ID": "l1",
                "Form": "f",
                "Segments": ["t", "e", "s", "t"],
            },
        ],
        CognateTable=[
            {"ID": "j1", "Form_ID": "f1", "Cognateset_ID": "s1", "Segment_Slice": "1"},
            {"ID": "j2", "Form_ID": "f3", "Cognateset_ID": "s1", "Segment_Slice": "2"},
            {
                "ID": "j3",
                "Form_ID": "f4",
                "Cognateset_ID": "s1",
                "Segment_Slice": ["2:3"],
            },
            {"ID": "j4", "Form_ID": "f4", "Cognateset_ID": "s2", "Segment_Slice": "2"},
        ],
        CognatesetTable=[{"ID": "s1"}, {"ID": "s2"}],
    )
    with caplog.at_level(logging.WARNING):
        cognatesets, judgements = create_singletons(ds)
    assert list(cognatesets) == [
        {"ID": "s1", "Description": None, "Source": []},
        {"ID": "s2", "Description": None, "Source": []},
        {"ID": "x_f2_1", "Description": None, "Source": None},
    ]
    assert judgements == [
        {
            "ID": "j1",
            "Form_ID": "f1",
            "Cognateset_ID": "s1",
            "Segment_Slice": ["1"],
            "Alignment": [],
            "Source": [],
        },
        {
            "ID": "j2",
            "Form_ID": "f3",
            "Cognateset_ID": "s1",
            "Segment_Slice": ["2"],
            "Alignment": [],
            "Source": [],
        },
        {
            "ID": "j3",
            "Form_ID": "f4",
            "Cognateset_ID": "s1",
            "Segment_Slice": ["2:3"],
            "Alignment": [],
            "Source": [],
        },
        {
            "ID": "j4",
            "Form_ID": "f4",
            "Cognateset_ID": "s2",
            "Segment_Slice": ["2"],
            "Alignment": [],
            "Source": [],
        },
        {
            "ID": "x_f2_1",
            "Form_ID": "f2",
            "Cognateset_ID": "x_f2_1",
            "Segment_Slice": ["1:1"],
            "Alignment": ["f"],
            "Source": None,
        },
    ]


def test_create_singletons_affix_by_segment(caplog):
    ds = new_wordlist(
        FormTable=[
            {
                "ID": "f1",
                "Parameter_ID": "c1",
                "Language_ID": "l1",
                "Form": "f",
                "Segments": ["f"],
            },
            {
                "ID": "f2",
                "Parameter_ID": "c1",
                "Language_ID": "l1",
                "Form": "f",
                "Segments": ["f"],
            },
            {
                "ID": "f3",
                "Parameter_ID": "c1",
                "Language_ID": "l1",
                "Form": "f",
                "Segments": ["f", "i"],
            },
            {
                "ID": "f4",
                "Parameter_ID": "c1",
                "Language_ID": "l1",
                "Form": "f",
                "Segments": ["t", "e", "s", "t"],
            },
        ],
        CognateTable=[
            {"ID": "j1", "Form_ID": "f1", "Cognateset_ID": "s1", "Segment_Slice": "1"},
            {"ID": "j2", "Form_ID": "f3", "Cognateset_ID": "s1", "Segment_Slice": "2"},
            {
                "ID": "j3",
                "Form_ID": "f4",
                "Cognateset_ID": "s1",
                "Segment_Slice": ["2:3"],
            },
            {"ID": "j4", "Form_ID": "f4", "Cognateset_ID": "s2", "Segment_Slice": "2"},
        ],
        CognatesetTable=[{"ID": "s1"}, {"ID": "s2"}],
    )
    with caplog.at_level(logging.WARNING):
        cognatesets, judgements = create_singletons(ds, by_segment=True)
    assert list(cognatesets) == [
        {"ID": "s1", "Description": None, "Source": []},
        {"ID": "s2", "Description": None, "Source": []},
        {"ID": "x_f2_1", "Description": None, "Source": None},
        {"ID": "x_f3_1", "Description": None, "Source": None},
        {"ID": "x_f4_1", "Description": None, "Source": None},
        {"ID": "x_f4_2", "Description": None, "Source": None},
    ]
    assert judgements == [
        {
            "ID": "j1",
            "Form_ID": "f1",
            "Cognateset_ID": "s1",
            "Segment_Slice": ["1"],
            "Alignment": [],
            "Source": [],
        },
        {
            "ID": "j2",
            "Form_ID": "f3",
            "Cognateset_ID": "s1",
            "Segment_Slice": ["2"],
            "Alignment": [],
            "Source": [],
        },
        {
            "ID": "j3",
            "Form_ID": "f4",
            "Cognateset_ID": "s1",
            "Segment_Slice": ["2:3"],
            "Alignment": [],
            "Source": [],
        },
        {
            "ID": "j4",
            "Form_ID": "f4",
            "Cognateset_ID": "s2",
            "Segment_Slice": ["2"],
            "Alignment": [],
            "Source": [],
        },
        {
            "ID": "x_f2_1",
            "Form_ID": "f2",
            "Cognateset_ID": "x_f2_1",
            "Segment_Slice": ["1:1"],
            "Alignment": ["f"],
            "Source": None,
        },
        {
            "ID": "x_f3_1",
            "Form_ID": "f3",
            "Cognateset_ID": "x_f3_1",
            "Segment_Slice": ["1:1"],
            "Alignment": ["f"],
            "Source": None,
        },
        {
            "ID": "x_f4_1",
            "Form_ID": "f4",
            "Cognateset_ID": "x_f4_1",
            "Segment_Slice": ["1:1"],
            "Alignment": ["t"],
            "Source": None,
        },
        {
            "ID": "x_f4_2",
            "Form_ID": "f4",
            "Cognateset_ID": "x_f4_2",
            "Segment_Slice": ["4:4"],
            "Alignment": ["t"],
            "Source": None,
        },
    ]


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
                {"id": "na", "form": "-", "segments": []},
                {"id": "missing", "form": "", "segments": []},
                {"id": "f1", "form": "ex", "segments": ["e", "x"]},
                {"id": "f2", "form": "test", "segments": ["t", "e", "s", "t"]},
                {
                    "id": "f3",
                    "form": "longer",
                    "segments": ["l", "o", "n", "g", "e", "r"],
                },
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
    cognates = [c for c in judgements if c[c_c_id].startswith("x")]
    cogsets = [c for c in all_cogsets if c[c_cs_id].startswith("x")]
    assert cognates == [
        {
            "ID": "x_ache_one_1_1",
            "Form_ID": "ache_one_1",
            "Comment": None,
            "Segment_Slice": ["1:6"],
            "Alignment": ["e", "t", "a", "k", "r", "ã"],
            "FIXME_IF_you_set_this_column_name_to_Value_it_messes_up_translations_due_to_conflict": "x_ache_one_1_1",
        },
        {
            "ID": "x_ache_two_1_1",
            "Form_ID": "ache_two_1",
            "Comment": None,
            "Segment_Slice": ["1:4"],
            "Alignment": ["m", "i", "r", "õ"],
            "FIXME_IF_you_set_this_column_name_to_Value_it_messes_up_translations_due_to_conflict": "x_ache_two_1_1",
        },
        {
            "ID": "x_old_paraguayan_guarani_two_1",
            "Form_ID": "old_paraguayan_guarani_two",
            "Comment": None,
            "Segment_Slice": ["1:5"],
            "Alignment": ["p", "a", "t", "h", "á"],
            "FIXME_IF_you_set_this_column_name_to_Value_it_messes_up_translations_due_to_conflict": "x_old_paraguayan_guarani_two_1",
        },
        {
            "ID": "x_ache_three_1_1",
            "Form_ID": "ache_three_1",
            "Comment": None,
            "Segment_Slice": ["1:5"],
            "Alignment": ["b", "u", "ǰ", "a", "¹"],
            "FIXME_IF_you_set_this_column_name_to_Value_it_messes_up_translations_due_to_conflict": "x_ache_three_1_1",
        },
        {
            "ID": "x_paraguayan_guarani_five_1",
            "Form_ID": "paraguayan_guarani_five",
            "Comment": None,
            "Segment_Slice": ["1:2"],
            "Alignment": ["p", "o"],
            "FIXME_IF_you_set_this_column_name_to_Value_it_messes_up_translations_due_to_conflict": "x_paraguayan_guarani_five_1",
        },
        {
            "ID": "x_kaiwa_five_1_1",
            "Form_ID": "kaiwa_five_1",
            "Comment": None,
            "Segment_Slice": ["1:6"],
            "Alignment": ["t", "e", "ɲ", "o", "ʔ", "a"],
            "FIXME_IF_you_set_this_column_name_to_Value_it_messes_up_translations_due_to_conflict": "x_kaiwa_five_1_1",
        },
    ]

    assert cogsets == [
        {
            "ID": "x_ache_one_1_1",
            "Set": None,
            "Comment": None,
            "Name": "one",
            "Status_Column": "automatic singleton",
        },
        {
            "ID": "x_ache_two_1_1",
            "Set": None,
            "Comment": None,
            "Name": "two",
            "Status_Column": "automatic singleton",
        },
        {
            "ID": "x_old_paraguayan_guarani_two_1",
            "Set": None,
            "Comment": None,
            "Name": "two",
            "Status_Column": "automatic singleton",
        },
        {
            "ID": "x_ache_three_1_1",
            "Set": None,
            "Comment": None,
            "Name": "three",
            "Status_Column": "automatic singleton",
        },
        {
            "ID": "x_paraguayan_guarani_five_1",
            "Set": None,
            "Comment": None,
            "Name": "five",
            "Status_Column": "automatic singleton",
        },
        {
            "ID": "x_kaiwa_five_1_1",
            "Set": None,
            "Comment": None,
            "Name": "five",
            "Status_Column": "automatic singleton",
        },
    ]

import logging
import pytest
from lexedata.edit.add_cognate_table import add_cognate_table
from lexedata import util


def test_add_cognate_table_column_manip():
    ds = util.fs.new_wordlist(
        FormTable=[],
    )
    ds.add_columns("FormTable", "cognatesetReference")
    assert add_cognate_table(ds, split=True) == 0
    with pytest.raises(KeyError):
        ds["FormTable", "cognatesetReference"]
    ds["CognateTable", "formReference"]


def test_add_cognate_table_sets_only():
    ds = util.fs.new_wordlist(
        FormTable=[],
    )
    ds.add_columns("FormTable", "cognatesetReference")
    ds.write(
        FormTable=[
            {
                "ID": "l1c1",
                "Language_ID": "l1",
                "Parameter_ID": "c1",
                "Form": "one",
                "Segments": ["w", "a", "n"],
                "cognatesetReference": "s1",
            },
            {
                "ID": "l1c2",
                "Language_ID": "l1",
                "Parameter_ID": "c2",
                "Form": "two",
                "Segments": ["t", "u"],
                "cognatesetReference": "s2",
            },
        ]
    )
    assert add_cognate_table(ds, split=True) == 2
    assert list(ds["CognateTable"]) == [
        {
            "ID": "l1c1-c1_s1",
            "Form_ID": "l1c1",
            "Cognateset_ID": "c1_s1",
            "Segment_Slice": ["1:3"],
            "Alignment": ["w", "a", "n"],
            "Source": [],
        },
        {
            "ID": "l1c2-c2_s2",
            "Form_ID": "l1c2",
            "Cognateset_ID": "c2_s2",
            "Segment_Slice": ["1:2"],
            "Alignment": ["t", "u"],
            "Source": [],
        },
    ]


def test_add_cognate_table_with_slices(caplog):
    ds = util.fs.new_wordlist(
        FormTable=[],
    )
    ds.add_columns("FormTable", "cognatesetReference")
    ds["FormTable", "cognatesetReference"].separator = " "
    ds.add_columns("FormTable", "segmentSlice")
    ds["FormTable", "segmentSlice"].separator = ","
    ds.write(
        FormTable=[
            {
                "ID": "good-form",
                "Language_ID": "l1",
                "Parameter_ID": "c1",
                "Form": "good form",
                "Segments": ["g", "u", "d", "_", "f", "o", "m"],
                "cognatesetReference": ["s1", "s2"],
                "segmentSlice": ["1:3", "5:7"],
            },
            {
                "ID": "bad-form",
                "Language_ID": "l1",
                "Parameter_ID": "c1",
                "Form": "one",
                "Segments": ["w", "a", "+", "n"],
                "cognatesetReference": ["s1"],
                "segmentSlice": ["1:4"],
            },
            {
                "ID": "simple-form",
                "Language_ID": "l1",
                "Parameter_ID": "c2",
                "Form": "two",
                "Segments": ["t", "u"],
                "cognatesetReference": ["s2"],
                "segmentSlice": ["1:2"],
            },
        ]
    )
    with caplog.at_level(logging.WARNING):
        n = add_cognate_table(ds, split=True)
    assert n == 4
    assert list(ds["CognateTable"]) == [
        {
            "ID": "good-form-c1_s1",
            "Form_ID": "good-form",
            "Cognateset_ID": "c1_s1",
            "Segment_Slice": ["1:3"],
            "Alignment": ["g", "u", "d"],
            "Source": [],
        },
        {
            "ID": "good-form-c1_s2",
            "Form_ID": "good-form",
            "Cognateset_ID": "c1_s2",
            "Segment_Slice": ["5:7"],
            "Alignment": ["f", "o", "m"],
            "Source": [],
        },
        {
            "ID": "bad-form-c1_s1",
            "Form_ID": "bad-form",
            "Cognateset_ID": "c1_s1",
            "Segment_Slice": ["1:4"],
            "Alignment": ["w", "a", "+", "n"],
            "Source": [],
        },
        {
            "ID": "simple-form-c2_s2",
            "Form_ID": "simple-form",
            "Cognateset_ID": "c2_s2",
            "Segment_Slice": ["1:2"],
            "Alignment": ["t", "u"],
            "Source": [],
        },
    ]
    assert [f["Segments"] for f in ds["FormTable"]] == [
        ["g", "u", "d", "_", "f", "o", "m"],
        ["w", "a", "+", "n"],
        ["t", "u"],
    ]


def test_add_cognate_table(caplog):
    ds = util.fs.new_wordlist(
        FormTable=[],
    )
    ds.add_columns("FormTable", "cognatesetReference")
    ds["FormTable", "cognatesetReference"].separator = " "
    ds.write(
        FormTable=[
            {
                "ID": "good-form",
                "Language_ID": "l1",
                "Parameter_ID": "c1",
                "Form": "good form",
                "Segments": ["g", "u", "d", "_", "f", "o", "m"],
                "cognatesetReference": ["s1", "s2"],
            },
            {
                "ID": "bad-form",
                "Language_ID": "l1",
                "Parameter_ID": "c1",
                "Form": "one",
                "Segments": ["w", "a", "+", "n"],
                "cognatesetReference": ["s1"],
            },
            {
                "ID": "simple-form",
                "Language_ID": "l1",
                "Parameter_ID": "c2",
                "Form": "two",
                "Segments": ["t", "u"],
                "cognatesetReference": ["s2"],
            },
        ]
    )
    with caplog.at_level(logging.WARNING):
        n = add_cognate_table(ds, split=False)
    assert n == 4
    assert list(ds["CognateTable"]) == [
        {
            "ID": "good-form-s1",
            "Form_ID": "good-form",
            "Cognateset_ID": "s1",
            "Segment_Slice": ["1:3"],
            "Alignment": ["g", "u", "d"],
            "Source": [],
        },
        {
            "ID": "good-form-s2",
            "Form_ID": "good-form",
            "Cognateset_ID": "s2",
            "Segment_Slice": ["4:6"],
            "Alignment": ["f", "o", "m"],
            "Source": [],
        },
        {
            "ID": "bad-form-s1",
            "Form_ID": "bad-form",
            "Cognateset_ID": "s1",
            "Segment_Slice": ["1:3"],
            "Alignment": ["w", "a", "n"],
            "Source": [],
        },
        {
            "ID": "simple-form-s2",
            "Form_ID": "simple-form",
            "Cognateset_ID": "s2",
            "Segment_Slice": ["1:2"],
            "Alignment": ["t", "u"],
            "Source": [],
        },
    ]
    assert [f["Segments"] for f in ds["FormTable"]] == [
        ["g", "u", "d", "f", "o", "m"],
        ["w", "a", "n"],
        ["t", "u"],
    ]

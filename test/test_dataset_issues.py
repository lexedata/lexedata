import re
import logging

from lexedata import util
import lexedata.report.judgements


def test_python_slice_is_wrong(caplog):
    ds = util.fs.new_wordlist(
        FormTable=[
            {
                "ID": "f1",
                "Language_ID": "l1",
                "Parameter_ID": "c1",
                "Form": "test",
                "Segments": ["t", "e", "s", "t"],
            }
        ],
        CognateTable=[
            {
                "ID": "j1",
                "Cognateset_ID": "s1",
                "Form_ID": "f1",
                "Segment_Slice": ["0:4"],
            }
        ],
    )
    with caplog.at_level(logging.WARNING):
        lexedata.report.judgements.check_cognate_table(ds)
    assert re.search("slice .*0:4.* is invalid", caplog.text)


def test_overlong_slice_is_wrong(caplog):
    ds = util.fs.new_wordlist(
        FormTable=[
            {
                "ID": "f1",
                "Language_ID": "l1",
                "Parameter_ID": "c1",
                "Form": "test",
                "Segments": ["t", "e", "s", "t"],
            }
        ],
        CognateTable=[
            {
                "ID": "j1",
                "Cognateset_ID": "s1",
                "Form_ID": "f1",
                "Segment_Slice": ["1:7"],
            }
        ],
    )
    with caplog.at_level(logging.WARNING):
        lexedata.report.judgements.check_cognate_table(ds)
    assert re.search("slice .*1:7.* is invalid", caplog.text)


def test_backward_slice_is_wrong(caplog):
    ds = util.fs.new_wordlist(
        FormTable=[
            {
                "ID": "f1",
                "Language_ID": "l1",
                "Parameter_ID": "c1",
                "Form": "test",
                "Segments": ["t", "e", "s", "t"],
            }
        ],
        CognateTable=[
            {
                "ID": "j1",
                "Cognateset_ID": "s1",
                "Form_ID": "f1",
                "Segment_Slice": ["4:3"],
            }
        ],
    )
    with caplog.at_level(logging.WARNING):
        lexedata.report.judgements.check_cognate_table(ds)
    assert re.search("slice .*4:3.* is invalid", caplog.text)


def test_default_metathesis_is_okay(caplog):
    ds = util.fs.new_wordlist(
        FormTable=[
            {
                "ID": "f1",
                "Language_ID": "l1",
                "Parameter_ID": "c1",
                "Form": "test",
                "Segments": ["t", "e", "s", "t"],
            }
        ],
        CognateTable=[
            {
                "ID": "j1",
                "Cognateset_ID": "s1",
                "Form_ID": "f1",
                "Segment_Slice": ["1", "3", "2", "1"],
                "Alignment": ["t", "s", "e", "t"],
            }
        ],
    )
    with caplog.at_level(logging.WARNING):
        lexedata.report.judgements.check_cognate_table(ds)
    assert not caplog.text


def test_strict_metathesis_is_wrong(caplog):
    ds = util.fs.new_wordlist(
        FormTable=[
            {
                "ID": "f1",
                "Language_ID": "l1",
                "Parameter_ID": "c1",
                "Form": "test",
                "Segments": ["t", "e", "s", "t"],
            }
        ],
        CognateTable=[
            {
                "ID": "j1",
                "Cognateset_ID": "s1",
                "Form_ID": "f1",
                "Segment_Slice": ["1", "3", "2", "4"],
                "Alignment": ["t", "s", "e", "t"],
            }
        ],
    )
    with caplog.at_level(logging.WARNING):
        lexedata.report.judgements.check_cognate_table(ds, strict_concatenative=True)
    assert re.search("non-consecutive", caplog.text)


def test_alignments_must_match_segments(caplog):
    ds = util.fs.new_wordlist(
        FormTable=[
            {
                "ID": "f1",
                "Language_ID": "l1",
                "Parameter_ID": "c1",
                "Form": "test",
                "Segments": ["t", "e", "s", "t"],
            }
        ],
        CognateTable=[
            {
                "ID": "j1",
                "Cognateset_ID": "s1",
                "Form_ID": "f1",
                "Segment_Slice": ["1:4"],
                "Alignment": ["t", "e", "x", "t"],
            }
        ],
    )
    with caplog.at_level(logging.WARNING):
        lexedata.report.judgements.check_cognate_table(ds, strict_concatenative=True)
    assert re.search("segments in form .*t e s t.*alignment.*t e x t", caplog.text)


def test_alignments_must_match_segments_ignore_gaps(caplog):
    ds = util.fs.new_wordlist(
        FormTable=[
            {
                "ID": "f1",
                "Language_ID": "l1",
                "Parameter_ID": "c1",
                "Form": "test",
                "Segments": ["t", "e", "s", "t"],
            }
        ],
        CognateTable=[
            {
                "ID": "j1",
                "Cognateset_ID": "s1",
                "Form_ID": "f1",
                "Segment_Slice": ["1:4"],
                "Alignment": ["t", "e", "s", "-", "t", "-"],
            }
        ],
    )
    with caplog.at_level(logging.WARNING):
        lexedata.report.judgements.check_cognate_table(ds)
    assert not caplog.text


def test_alignments_must_match_length(caplog):
    ds = util.fs.new_wordlist(
        FormTable=[
            {
                "ID": "f1",
                "Language_ID": "l1",
                "Parameter_ID": "c1",
                "Form": "test",
                "Segments": ["t", "e", "s", "t"],
            },
            {
                "ID": "f2",
                "Language_ID": "l1",
                "Parameter_ID": "c1",
                "Form": "test",
                "Segments": ["t", "e", "x", "t"],
            },
        ],
        CognateTable=[
            {
                "ID": "j1",
                "Cognateset_ID": "s1",
                "Form_ID": "f1",
                "Segment_Slice": ["1:4"],
                "Alignment": ["t", "e", "s", "t"],
            },
            {
                "ID": "j2",
                "Cognateset_ID": "s1",
                "Form_ID": "f2",
                "Segment_Slice": ["1:3"],
                "Alignment": ["t", "e", "x"],
            },
        ],
    )
    with caplog.at_level(logging.WARNING):
        lexedata.report.judgements.check_cognate_table(ds)
    assert re.search("length.*3.*other alignments.*length.*4", caplog.text)


def test_missing_forms_not_coded(caplog):
    ds = util.fs.new_wordlist(FormTable=[], CognateTable=[])
    ds["FormTable", "Form"].required = False
    ds.write(
        FormTable=[
            {
                "ID": "f1",
                "Language_ID": "l1",
                "Parameter_ID": "c1",
                "Form": "te-t",
                "Value": "te-t",
                "Segments": ["t", "e", "-", "t"],
            },
            {
                "ID": "f2",
                "Language_ID": "l1",
                "Parameter_ID": "c1",
                "Form": "-",
                "Value": "-",
                "Segments": [],
            },
            {
                "ID": "f3",
                "Language_ID": "l1",
                "Parameter_ID": "c1",
                "Form": None,
                "Value": None,
                "Segments": [],
            },
            {
                "ID": "f4",
                "Language_ID": "l1",
                "Parameter_ID": "c1",
                "Form": "",
                "Value": "",
                "Segments": [],
            },
        ],
        CognateTable=[
            {
                "ID": "j1",
                "Cognateset_ID": "s1",
                "Form_ID": "f1",
            },
            {
                "ID": "j2",
                "Cognateset_ID": "s1",
                "Form_ID": "f2",
            },
            {
                "ID": "j3",
                "Cognateset_ID": "s1",
                "Form_ID": "f3",
            },
            {
                "ID": "j4",
                "Cognateset_ID": "s1",
                "Form_ID": "f4",
            },
        ],
    )
    with caplog.at_level(logging.WARNING):
        lexedata.report.judgements.check_cognate_table(ds)
    assert re.search("NA form .*f2.* in cognate set", caplog.text)
    assert re.search("NA form .*f3.* in cognate set", caplog.text)
    assert re.search("NA form .*f4.* in cognate set", caplog.text)
    assert not re.search("NA form .*f1.* in cognate set", caplog.text)

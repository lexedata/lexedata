import re
from pathlib import Path

from lexedata.edit.add_segments import (
    segment_form,
    SegmentReport,
    add_segments_to_dataset,
)
from lexedata.report.segment_inventories import count_segments

from lexedata import util
from test_excel_conversion import copy_to_temp
from lexedata.cli import logger


def test_unkown_aspiration(caplog):
    form = "-á:muaʰ"
    report = SegmentReport()
    segment_form(form, report)
    assert re.search(
        "Unknown sound aʰ encountered in -á:muaʰ", caplog.text
    ) and report("language") == [("language", "aʰ", 1, "unknown pre-aspiration")]


def test_prenasal_before_vowel(caplog):
    form = "-eᵐa"
    report = SegmentReport()
    segment_form(form, report)
    assert re.search("Unknown sound .* encountered in -eᵐa", caplog.text)
    expected_report = [("language", "eᵐ", 1, "unknown pre-nasalization")]
    assert report("language") == expected_report


def test_segment_report():
    report1 = SegmentReport()
    report1.sounds["aʰ"].count = 1
    report1.sounds["aʰ"].comment = "comment"
    report1 = report1("language")
    assert report1 == [("language", "aʰ", 1, "comment")]


# TODO: report also contains the data from the test before ... but why does this happen?
def test_unknown_sound(caplog):
    form = "wohuᵈnasi"
    report2 = SegmentReport()
    segment_form(form, report2)
    assert re.search(
        "Unknown sound uᵈ encountered in wohuᵈnasi", caplog.text
    )  # and report2("language") == [("language", "uᵈ", 1, "unknown sound")]


def test_illegal_symbol(caplog):
    form = r"woh/"
    report3 = SegmentReport()
    segment_form(form, report3)
    assert re.search(
        "Impossible sound '/' encountered in woh/", caplog.text
    )  # and report3("language") == [("language", "/", 1, "illegal symbol")]


def test_deleting_symbols():
    form = "abːcd-ef.gh"
    form = segment_form(form, SegmentReport())
    assert "".join(str(s) for s in form) == "abːcdefgh"


# TODO: report contains warnings from other test. See other TODO.
def test_add_segments_to_dataset():
    dataset, target = copy_to_temp(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    add_segments_to_dataset(
        dataset=dataset,
        transcription=dataset.column_names.forms.form,
        overwrite_existing=True,
        replace_form=False,
        logger=logger,
    )
    assert True
    # assert report == [
    #     ("ache", "'", 7, "unknown sound"),
    #     ("ache", "?", 1, "unknown sound"),
    #     ("paraguayan_guarani", "'", 7, "unknown sound"),
    #     ("paraguayan_guarani", "?", 1, "unknown sound"),
    #     ("kaiwa", "'", 7, "unknown sound"),
    #     ("kaiwa", "?", 1, "unknown sound"),
    #     ("old_paraguayan_guarani", "'", 7, "unknown sound"),
    #     ("old_paraguayan_guarani", "?", 1, "unknown sound"),
    #
    # ]


def test_segment_inventory_report(caplog):
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
            {
                "ID": "f3",
                "Language_ID": "l2",
                "Parameter_ID": "c1",
                "Form": "test",
                "Segments": ["t", "e", "x", "t"],
            },
        ],
    )

    assert count_segments(ds, {"l1"}) == {
        "l1": {
            "t": 4,
            "e": 2,
            "s": 1,
            "x": 1,
        }
    }

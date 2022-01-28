import re
import math
import tempfile
from pathlib import Path

import pytest

from lexedata.report.coverage import coverage_report, coverage_report_concepts
from lexedata.util.fs import copy_dataset
from lexedata import util


@pytest.fixture(
    params=[
        "data/cldf/smallmawetiguarani/cldf-metadata.json",
    ]
)
def cldf_wordlist(request):
    dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    target = dirname / "cldf-metadata.json"
    return copy_dataset(original=Path(__file__).parent / request.param, target=target)


def test_no_primary_concepts(caplog, cldf_wordlist):
    dataset = cldf_wordlist
    coverage_report(dataset=dataset, min_percentage=0, with_concept=[], missing=False)
    assert re.search(r".*doesn't contain a column 'Primary'.*", caplog.text)


def test_uncoded_coverage_report(cldf_wordlist):
    dataset = cldf_wordlist
    data = coverage_report(
        dataset=dataset,
        min_percentage=0,
        with_concept=[],
        only_coded=False,
    )
    assert data == [
        ["ache", "Aché", 6, 0.6, 1.5],
        ["paraguayan_guarani", "Paraguayan Guaraní", 7, 0.7, 1.0],
        ["old_paraguayan_guarani", "Old Paraguayan Guaraní", 1, 0.1, 1.0],
        ["kaiwa", "Kaiwá", 5, 0.5, 1.0],
    ]


def test_coverage_report(cldf_wordlist):
    dataset = cldf_wordlist
    data = coverage_report(
        dataset=dataset,
        min_percentage=0,
        with_concept=[],
    )
    assert math.isnan(data[2][4])
    data[2][4] = 0
    assert data == [
        ["ache", "Aché", 5, 0.5, 1.6],
        ["paraguayan_guarani", "Paraguayan Guaraní", 5, 0.5, 1.0],
        ["old_paraguayan_guarani", "Old Paraguayan Guaraní", 0, 0.0, 0],
        ["kaiwa", "Kaiwá", 5, 0.5, 1.0],
    ]


def test_coverage_concept_report(cldf_wordlist):
    dataset = cldf_wordlist
    data = coverage_report_concepts(dataset=dataset)
    assert data == [
        ["one", 3],
        ["one_1", 1],
        ["two", 4],
        ["three", 3],
        ["four", 3],
        ["four_1", 1],
        ["five", 3],
        ["hand", 1],
    ]


def test_coverage_report_uncoded(cldf_wordlist):
    dataset = cldf_wordlist
    data = coverage_report(
        dataset=dataset,
        min_percentage=0,
        with_concept=[],
        only_coded=False,
    )
    assert data == [
        ["ache", "Aché", 6, 0.6, 1.5],
        ["paraguayan_guarani", "Paraguayan Guaraní", 7, 0.7, 1.0],
        ["old_paraguayan_guarani", "Old Paraguayan Guaraní", 1, 0.1, 1.0],
        ["kaiwa", "Kaiwá", 5, 0.5, 1.0],
    ]


def test_coverage_report_with_concept_table():
    ds = util.fs.new_wordlist(
        FormTable=[
            {"ID": "f2", "Language_ID": "l1", "Parameter_ID": "c2", "Form": "-"},
            {"ID": "f3", "Language_ID": "l1", "Parameter_ID": "c3", "Form": "form"},
            {"ID": "f4", "Language_ID": "l2", "Parameter_ID": "c1", "Form": "form"},
            {"ID": "f5", "Language_ID": "l2", "Parameter_ID": "c2", "Form": "form"},
            {"ID": "f6", "Language_ID": "l2", "Parameter_ID": "c3", "Form": "form"},
        ],
        ParameterTable=[
            {"ID": "c1"},
            {"ID": "c2"},
            {"ID": "c3"},
            {"ID": "c4"},
        ],
    )
    data = coverage_report(ds, only_coded=False)
    assert data == [["l1", "l1", 2, 0.5, 1.0], ["l2", "l2", 3, 0.75, 1.0]]


def test_coverage_report_with_primary_concepts():
    ds = util.fs.new_wordlist(
        FormTable=[
            {"ID": "f2", "Language_ID": "l1", "Parameter_ID": "c2", "Form": "-"},
            {"ID": "f3", "Language_ID": "l1", "Parameter_ID": "c3", "Form": "form"},
            {"ID": "f4", "Language_ID": "l2", "Parameter_ID": "c1", "Form": "form"},
            {"ID": "f5", "Language_ID": "l2", "Parameter_ID": "c2", "Form": "form"},
            {"ID": "f6", "Language_ID": "l2", "Parameter_ID": "c3", "Form": "form"},
        ],
        ParameterTable=[],
    )
    ds.add_columns("ParameterTable", "Primary")
    ds.write(
        ParameterTable=[
            {"ID": "c1", "Primary": "yes"},
            {"ID": "c2", "Primary": "yes"},
            {"ID": "c3", "Primary": "yes"},
            {"ID": "c4", "Primary": ""},
        ],
    )
    data = coverage_report(ds, only_coded=False)
    assert data == [["l1", "l1", 2, 2.0 / 3.0, 1.0], ["l2", "l2", 3, 1.0, 1.0]]

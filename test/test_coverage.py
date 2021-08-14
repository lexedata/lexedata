from pathlib import Path
import re
import tempfile

import pytest

from lexedata.report.coverage import coverage_report, coverage_report_concepts
from lexedata.util.fs import copy_dataset


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


def test_coverage_report(cldf_wordlist):
    dataset = cldf_wordlist
    data, _ = coverage_report(
        dataset=dataset, min_percentage=0, with_concept=[], missing=False
    )
    assert data == [
        ["ache", "Aché", 6, 0.6, 1.5],
        ["paraguayan_guarani", "Paraguayan Guaraní", 7, 0.7, 1.0],
        ["old_paraguayan_guarani", "Old Paraguayan Guaraní", 1, 0.1, 1.0],
        ["kaiwa", "Kaiwá", 5, 0.5, 1.0],
    ]


def test_coverage_concept_report(cldf_wordlist):
    dataset = cldf_wordlist
    data, _ = coverage_report_concepts(dataset=dataset)
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

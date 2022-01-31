import logging
from pathlib import Path

import pytest
import tempfile

from helper_functions import (
    copy_to_temp,
    copy_to_temp_no_bib,
    copy_to_temp_bad_bib,
)
from lexedata import util
from lexedata.exporter.matrix import MatrixExcelWriter


@pytest.fixture(
    params=[
        "data/cldf/minimal/cldf-metadata.json",
        "data/cldf/smallmawetiguarani/cldf-metadata.json",
    ]
)
def cldf_wordlist(request):
    return Path(__file__).parent / request.param


@pytest.fixture(
    params=[
        copy_to_temp,
        copy_to_temp_no_bib,
        copy_to_temp_bad_bib,
    ]
)
def working_and_nonworking_bibfile(request):
    return request.param


try:
    from pycldf.dataset import SchemaError
except ImportError:
    # SchemaError was introduced in pycldf 1.24.0
    SchemaError = KeyError


def test_toexcel_runs(cldf_wordlist, working_and_nonworking_bibfile):
    dataset, filename = working_and_nonworking_bibfile(cldf_wordlist)
    E = MatrixExcelWriter(
        dataset=dataset,
        database_url=str(filename),
    )
    forms = util.cache_table(dataset)
    languages = sorted(
        util.cache_table(dataset, "LanguageTable").values(), key=lambda x: x["name"]
    )
    judgements = [
        {"formReference": f["id"], "cognatesetReference": parameter}
        for f in forms.values()
        for parameter in util.ensure_list(f["parameterReference"])
    ]
    parameters = util.cache_table(dataset, "ParameterTable").values()
    E.create_excel(
        rows=parameters, judgements=judgements, forms=forms, languages=languages
    )
    _, out_filename = tempfile.mkstemp(".xlsx", "cognates")
    E.wb.save(filename=out_filename)


def test_cell_comments_export():
    dataset, _ = copy_to_temp(
        Path(__file__).parent / "data/cldf/minimal/cldf-metadata.json"
    )
    _, out_filename = tempfile.mkstemp(".xlsx", "cognates")

    E = MatrixExcelWriter(dataset, database_url="https://example.org/lexicon/{:}")
    forms = util.cache_table(dataset)
    languages = sorted(
        util.cache_table(dataset, "LanguageTable").values(), key=lambda x: x["name"]
    )
    judgements = [
        {"formReference": f["id"], "cognatesetReference": parameter}
        for f in forms.values()
        for parameter in util.ensure_list(f["parameterReference"])
    ]
    parameters = util.cache_table(dataset, "ParameterTable").values()
    E.create_excel(
        rows=parameters, judgements=judgements, forms=forms, languages=languages
    )

    for col in E.ws.iter_cols():
        pass
    assert (
        col[-1].comment and col[-1].comment.content
    ), "Last row of last column should contain a form, with a comment attached to it."
    assert (
        col[-1].comment.content == "A Comment!"
    ), "Comment should match the comment from the form table"


def test_toexcel_filtered(cldf_wordlist, working_and_nonworking_bibfile, caplog):
    dataset, url = working_and_nonworking_bibfile(cldf_wordlist)
    writer = MatrixExcelWriter(
        dataset=dataset,
        database_url=str(url),
    )
    E = MatrixExcelWriter(dataset, database_url="https://example.org/lexicon/{:}")
    forms = util.cache_table(dataset)
    languages = sorted(
        util.cache_table(dataset, "LanguageTable").values(), key=lambda x: x["name"]
    )
    judgements = [
        {"formReference": f["id"], "cognatesetReference": parameter}
        for f in forms.values()
        for parameter in util.ensure_list(f["parameterReference"])
    ]
    parameters = [
        c
        for n, c in util.cache_table(dataset, "ParameterTable").items()
        if n == "Woman"
    ]
    with caplog.at_level(logging.WARNING):
        E.create_excel(
            rows=parameters, judgements=judgements, forms=forms, languages=languages
        )
    assert len(list(writer.ws.iter_rows())) in {0, 2}

import re
import logging
from pathlib import Path

import pytest
import tempfile

from helper_functions import (
    copy_to_temp,
    copy_to_temp_no_bib,
    copy_to_temp_bad_bib,
)
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
    filled_cldf_wordlist = working_and_nonworking_bibfile(cldf_wordlist)
    writer = MatrixExcelWriter(
        dataset=filled_cldf_wordlist[0],
        database_url=str(filled_cldf_wordlist[1]),
    )
    writer.create_excel()
    _, out_filename = tempfile.mkstemp(".xlsx", "cognates")
    writer.wb.save(filename=out_filename)


def test_cell_comments_export():
    dataset, _ = copy_to_temp(
        Path(__file__).parent / "data/cldf/minimal/cldf-metadata.json"
    )
    _, out_filename = tempfile.mkstemp(".xlsx", "cognates")

    E = MatrixExcelWriter(dataset, database_url="https://example.org/lexicon/{:}")
    E.set_header()
    E.create_excel(size_sort=False, language_order="Name")

    for col in E.ws.iter_cols():
        pass
    assert (
        col[-1].comment and col[-1].comment.content
    ), "Last row of last column should contain a form, with a comment attached to it."
    assert (
        col[-1].comment.content == "A Comment!"
    ), "Comment should match the comment from the form table"


def test_toexcel_filtered(cldf_wordlist, working_and_nonworking_bibfile, caplog):
    filled_cldf_wordlist = working_and_nonworking_bibfile(cldf_wordlist)
    writer = MatrixExcelWriter(
        dataset=filled_cldf_wordlist[0],
        database_url=str(filled_cldf_wordlist[1]),
    )
    with caplog.at_level(logging.WARNING):
        writer.create_excel(rows=["Woman"])
    assert (len(list(writer.ws.iter_rows())) == 2) or (
        re.search("entries {'Woman'}", caplog.text)
    )

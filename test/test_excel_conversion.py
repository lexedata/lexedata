import pytest
import shutil
import tempfile
from pathlib import Path

import pycldf

from lexedata.importer.fromexcel import ExcelParser, op
from lexedata.exporter.cognate_excel import ExcelWriter


@pytest.fixture
def excel_wordlist():
    return Path(__file__).parent / "data/excel/small.xlsx"


@pytest.fixture(params=[
        "data/cldf/minimal/cldf-metadata.json",
        "data/cldf/smallmawetiguarani/cldf-metadata.json"])
def cldf_wordlist(request):
    return Path(__file__).parent / request.param


@pytest.fixture
def empty_cldf_wordlist(cldf_wordlist):
    original = cldf_wordlist
    dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    target = dirname / original.name
    shutil.copyfile(original, target)
    dataset = pycldf.Dataset.from_metadata(target)
    dataset.write(**{str(table.url): []
                     for table in dataset.tables})
    return dataset


@pytest.fixture
def filled_cldf_wordlist(cldf_wordlist):
    original = cldf_wordlist
    dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    target = dirname / original.name
    shutil.copyfile(original, target)
    dataset = pycldf.Dataset.from_metadata(target)
    for table in dataset.tables:
        link = Path(str(table.url))
        o = original.parent / link
        t = target.parent / link
        shutil.copyfile(o, t)
    link = dataset.bibpath.name
    o = original.parent / link
    t = target.parent / link
    shutil.copyfile(o, t)
    dataset.sources = pycldf.dataset.Sources.from_file(dataset.bibpath)
    return dataset


def test_fromexcel_runs(excel_wordlist, empty_cldf_wordlist):
    parser = ExcelParser(empty_cldf_wordlist)

    wb = op.load_workbook(filename=excel_wordlist)
    parser.initialize_lexical(wb.worksheets[0])

    wb = op.load_workbook(filename=excel_wordlist)
    for sheet in wb.sheetnames:
        ws = wb[sheet]
        parser.initialize_cognate(ws)

    parser.cldfdatabase.to_cldf(empty_cldf_wordlist.directory)


def test_toexcel_runs(filled_cldf_wordlist):
    writer = ExcelWriter(filled_cldf_wordlist)
    _, out_filename = tempfile.mkstemp(".xlsx", "cognates")
    writer.create_excel(out_filename)


def test_roundtrip(filled_cldf_wordlist):
    c_formReference = filled_cldf_wordlist["CognateTable", "formReference"].name
    c_cogsetReference = filled_cldf_wordlist["CognateTable", "cognatesetReference"].name
    old_judgements = {
        (row[c_formReference], row[c_cogsetReference])
        for row in filled_cldf_wordlist["CognateTable"].iterdicts()}
    writer = ExcelWriter(filled_cldf_wordlist)
    _, out_filename = tempfile.mkstemp(".xlsx", "cognates")
    writer.create_excel(out_filename)
    filled_cldf_wordlist["CognateTable"].write([])

    parser = ExcelParser(filled_cldf_wordlist)

    wb = op.load_workbook(filename=out_filename)
    for sheet in wb.sheetnames:
        ws = wb[sheet]
        parser.initialize_cognate(ws)

    # Really? Isn't there a shortcut to do this?
    parser.cldfdatabase.to_cldf(filled_cldf_wordlist.tablegroup._fname.parent)
    new_judgements = {
        (row[c_formReference], row[c_cogsetReference])
        for row in filled_cldf_wordlist["CognateTable"].iterdicts()}

    assert new_judgements == old_judgements

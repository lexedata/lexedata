import pytest
import shutil
import tempfile
from pathlib import Path

import pycldf
import openpyxl

from lexedata.importer.fromexcel import ExcelParser, ExcelCognateParser, MawetiGuaraniExcelParser, MawetiGuaraniExcelCognateParser
from lexedata.exporter.cognate_excel import ExcelWriter


@pytest.fixture
def excel_wordlist():
    return Path(__file__).parent / "data/excel/small.xlsx", Path(__file__).parent / "data/excel/small_cog.xlsx"


@pytest.fixture(params=[
        "data/cldf/minimal/cldf-metadata.json",
        "data/cldf/smallmawetiguarani/cldf-metadata.json"])
def cldf_wordlist(request):
    return Path(__file__).parent / request.param


@pytest.fixture
def empty_cldf_wordlist():
    original = Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    target = dirname / original.name
    shutil.copyfile(original, target)
    dataset = pycldf.Dataset.from_metadata(target)
    # TODO: Gereon can you leave some comment for the interface of pycldf.Dataset?
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
    parser = MawetiGuaraniExcelParser(empty_cldf_wordlist)
    wb = openpyxl.load_workbook(filename=excel_wordlist[0])
    parser.read(wb.worksheets[0])
    parser.cldfdatabase.to_cldf(empty_cldf_wordlist.directory)

    cparser = MawetiGuaraniExcelCognateParser(empty_cldf_wordlist)
    wb = openpyxl.load_workbook(filename=excel_wordlist[1])
    for sheet in wb.sheetnames:
        ws = wb[sheet]
        cparser.read(ws)
    cparser.cldfdatabase.to_cldf(empty_cldf_wordlist.directory)


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

    # Reset the existing cognatesets and cognate judgements, to avoid
    # interference with the the data in the Excel file
    filled_cldf_wordlist["CognateTable"].write([])
    # filled_cldf_wordlist["CognatesetTable"].write([])

    parser = ExcelCognateParser(filled_cldf_wordlist)
    parser.left = len(writer.header) + 1

    wb = openpyxl.load_workbook(filename=out_filename)
    for sheet in wb.sheetnames:
        ws = wb[sheet]
        parser.read(ws)

    # Really? Isn't there a shortcut to do this?
    parser.cldfdatabase.to_cldf(filled_cldf_wordlist.tablegroup._fname.parent)
    new_judgements = {
        (row[c_formReference], row[c_cogsetReference])
        for row in filled_cldf_wordlist["CognateTable"].iterdicts()}

    assert new_judgements == old_judgements

import pytest
import shutil
import tempfile
from pathlib import Path

from lexedata.importer.fromexcel import ExcelParser, op


@pytest.fixture
def excel_wordlist():
    return Path(__file__).parent / "data/excel/small.xlsx"


@pytest.fixture
def cldf_wordlist():
    original = Path(__file__).parent / "data/cldf/cldf-metadata.json"
    dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    target = dirname / original.name
    shutil.copyfile(original, target)
    return target


def test_fromexcel_runs(excel_wordlist, cldf_wordlist):
    parser = ExcelParser(output=cldf_wordlist)

    wb = op.load_workbook(filename=excel_wordlist)
    parser.initialize_cognate(wb.worksheets[0])

    wb = op.load_workbook(filename=excel_wordlist)
    for sheet in wb.sheetnames:
        print("\nParsing sheet '{:s}'".format(sheet))
        ws = wb[sheet]
        parser.initialize_cognate(ws)

    parser.cldfdatabase.to_cldf(cldf_wordlist.parent)

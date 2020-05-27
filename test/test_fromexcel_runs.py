import pytest
import shutil
import tempfile
from pathlib import Path

from lexedata.database.database import create_db_session
from lexedata.importer.fromexcel import ExcelParser


@pytest.fixture
def excel_wordlist():
    return Path(__file__).parent / "data/excel/small.xlsx"


@pytest.fixture
def cldf_wordlist():
    return Path(__file__).parent / "data/cldf/cldf-metadata.json"


def test_fromexcel_runs(excel_wordlist, cldf_wordlist):
    dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    target = dirname / cldf_wordlist.name
    shutil.copyfile(cldf_wordlist, target)

    ExcelParser(
        output=target,
        lexicon_spreadsheet=excel_wordlist,
        # FIXME: Build an actual minimal cognateset spreadsheet
        cognatesets_spreadsheet=excel_wordlist).parse()

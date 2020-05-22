from pathlib import Path
import tempfile

import pytest

from lexedata.database.database import create_db_session
from lexedata.importer.fromexcel import ExcelParser


@pytest.fixture
def excel_wordlist():
    return Path(__file__).parent / "data/excel/small.xlsx"


def test_fromexcel_runs(excel_wordlist):
    # The Intermediate Storage, in a in-memory DB
    session = create_db_session("sqlite:///:memory:")

    ExcelParser(
        session,
        output=tempfile.mkdtemp(),
        lexicon_spreadsheet=excel_wordlist,
        # FIXME: Build an actual minimal cognateset spreadsheet
        cognatesets_spreadsheet=excel_wordlist).parse()
    session.commit()
    session.close()

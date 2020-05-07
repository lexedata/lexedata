import shutil
import tempfile
from pathlib import Path

import pytest

import lexedata

@pytest.fixture
def cldf_wordlist():
    return Path(__file__).parent / "data/cldf/Wordlist-metadata.json"


def test_convert_cldf_to_excel_cognateset_view_and_back(cldf_wordlist):
    """Take a CLDF word list dataset and check the round trip to Excel.

    """
    dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    handle, filename = tempfile.mkstemp(suffix=".xlsx", dir=dirname)
    dataset = lexedata.dataset(cldf_wordlist)
    lexedata.exporter.cognateset_excel(dataset, filename)
    target = dirname / cldf_wordlist.name
    shutil.copyfile(cldf_wordlist, target)
    lexedata.importer.cognateset_excel(filename, target)
    assert (target.with_name("cognatesets.csv").open().read() ==
            cldf_wordlist.with_name("cognatesets.csv").open().read())
    # This should actually inspect the dataset for the CognateTable URL.

    # Should we actually care, as this does now, about the order of cognate
    # judgements in the output CognateTable? Maybe, assuming the IDs were
    # ordered to begin with? Otherwise, that information is not in the
    # Excel.

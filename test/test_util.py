import pytest
import logging
from pathlib import Path

import pycldf

from lexedata.util import normalize_table_name


@pytest.fixture(params=["data/cldf/smallmawetiguarani/cldf-metadata.json"])
def wordlist(request):
    original = Path(__file__).parent / request.param
    dataset = pycldf.Dataset.from_metadata(original)
    return dataset


def test_normal_table_names(wordlist, caplog):
    assert normalize_table_name("FormTable", wordlist) == normalize_table_name(
        "forms.csv", wordlist
    )
    with caplog.at_level(logging.WARNING):
        assert normalize_table_name("NonExistingTable", wordlist) is None
    assert "Could not find table NonExistingTable" in caplog.text

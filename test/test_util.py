import pytest
import logging
from pathlib import Path

import pycldf

from lexedata.util import normalize_table_name, get_foreignkey
from helper_functions import copy_metadata


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


def test_get_foreignkey():
    dataset = pycldf.Dataset.from_metadata(
        copy_metadata(
            original=Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
        )
    )
    foreign_key_parameter = ""
    for foreign_key in dataset["FormTable"].tableSchema.foreignKeys:
        if foreign_key.reference.resource == dataset["ParameterTable"].url:
            foreign_key_parameter = foreign_key.columnReference[0]
    assert foreign_key_parameter == get_foreignkey(
        dataset=dataset,
        table="FormTable",
        other_table="ParameterTable",
    )


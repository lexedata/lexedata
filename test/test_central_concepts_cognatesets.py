from pathlib import Path
import shutil
import tempfile

import pytest
import pycldf

from lexedata.edit.add_central_concepts import (
    add_central_concepts_to_cognateset_table,
)
from lexedata.edit.add_concepticon import create_concepticon_for_concepts


@pytest.fixture(params=["data/cldf/smallmawetiguarani/cldf-metadata.json"])
def copy_wordlist_add_concepticons(request):
    original = Path(__file__).parent / request.param
    dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    target = dirname / original.name
    shutil.copyfile(original, target)
    dataset = pycldf.Dataset.from_metadata(original)
    for table in dataset.tables:
        link = Path(str(table.url))
        o = original.parent / link
        t = target.parent / link
        shutil.copyfile(o, t)
    dataset = pycldf.Dataset.from_metadata(target)
    create_concepticon_for_concepts(
        dataset=dataset,
        language=[],
        overwrite=False,
        concepticon_glosses=False,
        concepticon_definition=False,
        status_update=None,
    )
    return target, dataset


def test_value_error_no_concepticonReferenc_for_concepts():
    with pytest.raises(ValueError):
        add_central_concepts_to_cognateset_table(
            pycldf.Dataset.from_metadata(
                Path(__file__).parent
                / "data/cldf/smallmawetiguarani/cldf-metadata.json"
            ),
            add_column=False,
        )


def test_value_error_no_parameterReference_for_cognateset(
    copy_wordlist_add_concepticons,
):
    target, dataset = copy_wordlist_add_concepticons
    with pytest.raises(ValueError):
        add_central_concepts_to_cognateset_table(dataset, add_column=False)


def test_add_concepts_to_maweti_cognatesets(copy_wordlist_add_concepticons):
    target, dataset = copy_wordlist_add_concepticons
    dataset = add_central_concepts_to_cognateset_table(dataset)
    c_core_concept = dataset["CognatesetTable", "parameterReference"].name
    c_id = dataset["CognatesetTable", "id"].name
    concepts_for_cognatesets = [
        (row[c_core_concept], row[c_id]) for row in dataset["CognatesetTable"]
    ]
    assert all(c[0] in c[1] for c in concepts_for_cognatesets)


def test_central_concept_status_column(copy_wordlist_add_concepticons):
    target, dataset = copy_wordlist_add_concepticons
    dataset = add_central_concepts_to_cognateset_table(
        dataset, status_update="Test_Status"
    )
    assert all(c["Status_Column"] == "Test_Status" for c in dataset["CognatesetTable"])

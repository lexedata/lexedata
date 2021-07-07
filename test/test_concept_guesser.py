from pathlib import Path
import tempfile
import shutil
import pytest
import pycldf
import re

from lexedata.edit.add_central_concepts import (
    add_central_concepts_to_cognateset_table,
)
from lexedata.edit.add_concepticon import create_concepticon_for_concepts


# TODO: Discuss this with Gereon. This fixture seems dangerous as we call a function that we test at another place
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
        status_update=None,
    )
    return target, dataset


def test_value_error_no_concepticon_reference_for_concepts(caplog):
    dataset = pycldf.Dataset.from_metadata(
                Path(__file__).parent
                / "data/cldf/smallmawetiguarani/cldf-metadata.json"
            )
    with pytest.raises(
        ValueError,
    ):
        add_central_concepts_to_cognateset_table(
            dataset=dataset,
            add_column=False,
        )
    assert re.search(r"Dataset .* had no concepticonReference in a ParamterTable.*", caplog.text)


def test_value_error_no_parameter_reference_for_cognateset(
    copy_wordlist_add_concepticons,
):
    target, dataset = copy_wordlist_add_concepticons
    with pytest.raises(
        ValueError,
        match="Dataset .* had no parameterReference column in a CognatesetTable.*"
    ):
        add_central_concepts_to_cognateset_table(dataset, add_column=False)


def test_concepticon_id_of_concepts_correct(copy_wordlist_add_concepticons):
    target, dataset = copy_wordlist_add_concepticons
    c_concepticon = dataset["ParameterTable", "concepticonReference"].name
    concepticon_for_concepts = [
        str(row[c_concepticon]) for row in dataset["ParameterTable"]
    ]
    assert concepticon_for_concepts == [
        "1493",
        "None",
        "1498",
        "None",
        "492",
        "None",
        "1500",
        "None",
        "493",
        "1277",
    ]


def test_add_concepts_to_maweti_cognatesets(copy_wordlist_add_concepticons):
    target, dataset = copy_wordlist_add_concepticons
    dataset = add_central_concepts_to_cognateset_table(dataset)
    c_core_concept = dataset["CognatesetTable", "parameterReference"].name
    c_id = dataset["CognatesetTable", "id"].name
    concepts_for_cognatesets = [
        (row[c_core_concept], row[c_id]) for row in dataset["CognatesetTable"]
    ]
    assert all(c[0] in c[1] for c in concepts_for_cognatesets)

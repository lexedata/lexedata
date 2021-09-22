import re
import shutil
import logging
import tempfile
from pathlib import Path

import pytest
import pycldf
from csvw.metadata import URITemplate

from lexedata.edit.add_central_concepts import (
    add_central_concepts_to_cognateset_table,
)
from lexedata.edit.add_concepticon import (
    create_concepticon_for_concepts,
    add_concepticon_definitions,
    add_concepticon_names,
)
from lexedata.util.fs import copy_dataset


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
        concepticon_definition=False,
        status_update=None,
    )
    return target, dataset


def test_value_error_no_concepticon_reference_for_concepts(caplog):
    dataset = pycldf.Dataset.from_metadata(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    with pytest.raises(
        ValueError,
    ):
        with caplog.at_level(logging.INFO):
            add_central_concepts_to_cognateset_table(
                dataset=dataset,
                add_column=False,
            )
    assert re.search(r"Dataset .* .*", caplog.text)


def test_value_error_no_parameter_reference_for_cognateset(
    copy_wordlist_add_concepticons,
):
    target, dataset = copy_wordlist_add_concepticons
    with pytest.raises(
        ValueError,
        match="Dataset .* had no parameterReference column in a CognatesetTable.*",
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


def test_concepticon_reference_missing(caplog):
    original = Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    target = dirname / original.name
    shutil.copyfile(original, target)
    dataset = pycldf.Dataset.from_metadata(target)
    with caplog.at_level(logging.ERROR):
        add_concepticon_definitions(dataset=dataset)
    assert re.search("no #concepticonReference", caplog.text)


def test_no_concepticon_definition_column_added(caplog):
    original = Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    target = dirname / original.name
    shutil.copyfile(original, target)
    dataset = pycldf.Dataset.from_metadata(target)
    dataset.add_columns("ParameterTable", "Concepticon_ID")
    c = dataset["ParameterTable"].tableSchema.columns[-1]
    c.valueUrl = "http://concepticon.clld.org/parameters/{Concepticon_ID}"
    c.propertyUrl = URITemplate(
        "http://cldf.clld.org/v1.0/terms.rdf#concepticonReference"
    )
    dataset.add_columns("ParameterTable", "Concepticon_Definition")
    dataset.write_metadata()
    dataset.write(ParameterTable=[])
    with caplog.at_level(logging.INFO):
        add_concepticon_definitions(dataset=dataset)
    assert re.search("[oO]verwrit.*existing Concepticon_Definition", caplog.text)


def test_concepticon_definitions(copy_wordlist_add_concepticons):
    target, dataset = copy_wordlist_add_concepticons
    column_name = "Concepticon_Definition"
    add_concepticon_definitions(
        dataset=dataset,
        column_name=column_name,
    )

    concepticon_definitions = [
        str(row[column_name]) for row in dataset["ParameterTable"]
    ]
    assert concepticon_definitions == [
        "The natural number one (1).",
        "None",
        "The natural number two (2).",
        "None",
        "The natural number three (3).",
        "None",
        "The natural number four (4).",
        "None",
        "The natural number five (5).",
        "That part of the fore limb below the forearm or wrist in primates (including humans).",
    ]


def test_add_concepticon_names_missing_column():
    original = Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    target = dirname / original.name
    dataset = copy_dataset(original=original, target=target)
    add_concepticon_names(dataset=dataset)
    try:
        assert dataset["ParameterTable", "Concepticon_Gloss"]
    except KeyError:
        pytest.fail("No column Concepticon_Gloss")

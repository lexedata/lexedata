import re
import logging
from pathlib import Path
import tempfile
import shutil

import pytest
import pycldf
from csvw.metadata import URITemplate

from lexedata.edit.add_central_concepts import (
    add_central_concepts_to_cognateset_table,
)
from lexedata.edit.add_concepticon import (
    create_concepticon_for_concepts,
    add_concepticon_definitions,
)


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

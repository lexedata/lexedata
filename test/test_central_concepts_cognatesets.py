import pytest
import pycldf

from lexedata.edit.add_central_concepts import (
    add_central_concepts_to_cognateset_table,
)


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

from pathlib import Path

import pytest

from lexedata.util.simplify_ids import update_ids, update_integer_ids
from helper_functions import copy_to_temp


@pytest.fixture()
def copy_dataset():
    return copy_to_temp(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )


def test_integer_ids(copy_dataset):
    dataset, _ = copy_dataset

    # shorten form and parameter table
    c_f_concept = dataset.column_names.forms.parameterReference
    c_c_id = dataset.column_names.parameters.id
    concepts = [p for p in dataset["ParameterTable"]][:3]
    concept_ids = {p[c_c_id] for p in concepts}
    forms = []
    for f in dataset["FormTable"]:
        if len(f[c_f_concept]) == 1:
            if f[c_f_concept][0] in concept_ids:
                forms.append(f)
    # set one id of concepts to integer
    # concepts[1][c_c_id] = 1
    dataset.write(ParameterTable=concepts)
    dataset.write(FormTable=forms)

    # update parameter table ids
    update_integer_ids(ds=dataset, table=dataset["ParameterTable"])

    # assert ids and parameterReference in form table changed
    concept_ids = {c[c_c_id] for c in dataset["ParameterTable"]}
    param_refs = []
    for f in dataset["FormTable"]:
        param_refs.extend(f[c_f_concept])
    param_refs = set(param_refs)
    assert {"1", "2", "3"} == concept_ids == param_refs


def test_update_ids(copy_dataset):
    dataset, _ = copy_dataset

    # shorten form and parameter table
    c_f_concept = dataset.column_names.forms.parameterReference
    c_c_id = dataset.column_names.parameters.id
    concepts = [p for p in dataset["ParameterTable"]][:3]
    concept_ids = {p[c_c_id] for p in concepts}
    forms = []
    for f in dataset["FormTable"]:
        if len(f[c_f_concept]) == 1:
            if f[c_f_concept][0] in concept_ids:
                forms.append(f)
    dataset.write(ParameterTable=concepts)
    dataset.write(FormTable=forms)

    mapping = {k[c_c_id]: v for k, v in zip(concepts, iter("abc"))}
    update_ids(ds=dataset, table=dataset["ParameterTable"], mapping=mapping)
    # assert ids and parameterReference in form table changed
    concept_ids = {c[c_c_id] for c in dataset["ParameterTable"]}
    param_refs = []
    for f in dataset["FormTable"]:
        param_refs.extend(f[c_f_concept])
    param_refs = set(param_refs)
    assert {"a", "b", "c"} == concept_ids == param_refs

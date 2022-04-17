from pathlib import Path

import csvw.metadata
import pytest
from lexedata import util
from lexedata.util.simplify_ids import (
    simplify_table_ids_and_references,
    update_ids,
    update_integer_ids,
)

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
    dataset["ParameterTable", "id"].datatype = csvw.metadata.Datatype.fromvalue(
        {"base": "string"}
    )
    update_integer_ids(ds=dataset, table=dataset["ParameterTable"])
    dataset["ParameterTable", "id"].datatype = csvw.metadata.Datatype.fromvalue(
        {"base": "integer"}
    )

    # assert ids and parameterReference in form table changed
    concept_ids = {c[c_c_id] for c in dataset["ParameterTable"]}
    param_refs = []
    for f in dataset["FormTable"]:
        param_refs.extend(f[c_f_concept])
    param_refs = set(param_refs)
    assert {1, 2, 3} == concept_ids == param_refs


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


def test_update_illegal_int_reference_ids():
    dataset = util.fs.new_wordlist(
        FormTable=[
            {"ID": "f1", "Parameter_ID": "illegal", "Language_ID": "l1", "Form": "f"}
        ],
        ParameterTable=[{"ID": "illegal"}],
    )
    dataset.remove_columns("FormTable", "Segments", "Comment", "Source")
    dataset["ParameterTable", "id"].datatype = csvw.metadata.Datatype.fromvalue(
        {"base": "integer"}
    )

    simplify_table_ids_and_references(dataset, dataset["ParameterTable"])
    assert list(dataset["FormTable"]) == [
        {"ID": "f1", "Parameter_ID": 1, "Language_ID": "l1", "Form": "f"}
    ]


def test_update_illegal_str_reference_ids():
    dataset = util.fs.new_wordlist(
        FormTable=[
            {"ID": "f1", "Parameter_ID": "Not Valid", "Language_ID": "l1", "Form": "f"}
        ],
        ParameterTable=[{"ID": "Not Valid"}],
    )
    dataset.remove_columns("FormTable", "Segments", "Comment", "Source")
    dataset["ParameterTable", "id"].datatype = csvw.metadata.Datatype.fromvalue(
        {"base": "string", "format": "[a-z]*"}
    )

    simplify_table_ids_and_references(dataset, dataset["ParameterTable"])
    assert list(dataset["FormTable"]) == [
        {"ID": "f1", "Parameter_ID": "not_valid", "Language_ID": "l1", "Form": "f"}
    ]


def test_transparent_form_ids():
    dataset = util.fs.new_wordlist(
        FormTable=[
            {"ID": "f1", "Parameter_ID": "c1", "Language_ID": "l1", "Form": "f"},
            {"ID": "f2", "Parameter_ID": "c1", "Language_ID": "l1", "Form": "f"},
        ],
    )
    dataset.remove_columns("FormTable", "Segments", "Comment", "Source")

    simplify_table_ids_and_references(dataset, dataset["FormTable"])
    assert list(dataset["FormTable"]) == [
        {"ID": "l1_c1", "Parameter_ID": "c1", "Language_ID": "l1", "Form": "f"},
        {"ID": "l1_c1_x2", "Parameter_ID": "c1", "Language_ID": "l1", "Form": "f"},
    ]

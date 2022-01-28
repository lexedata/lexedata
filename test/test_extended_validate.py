from pathlib import Path
import unicodedata
import re

import pytest


from helper_functions import copy_to_temp
import lexedata.report.extended_cldf_validate as validate


def test_check_foreignkeys_correct():
    dataset, target = copy_to_temp(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    assert validate.check_foreign_keys(dataset=dataset)


@pytest.mark.skip(
    reason="How to change the foreign key of the given dataset in a simple way?"
)
def test_check_foreignkeys_warning(caplog):
    dataset, target = copy_to_temp(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )


@pytest.mark.skip(reason="Resolve TODO in extended_cldf_validate and check test data")
def test_check_unicode_data():
    dataset, target = copy_to_temp(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    assert validate.check_unicode_data(dataset=dataset)


def test_check_unicode_data_warning(caplog):
    dataset, target = copy_to_temp(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    # insert incorrect unicode style
    c_f_form = dataset["FormTable", "form"].name
    forms = [f for f in dataset["FormTable"]]
    form = forms[0]
    form[c_f_form] = "\u0041\u0300"
    forms[0] = form
    dataset.write(FormTable=forms)

    validate.check_unicode_data(dataset=dataset)
    assert re.search(
        unicodedata.normalize(
            "NFC",
            "Value À of row 1 in table forms.csv is not in NFC normalized unicode",
        ),
        unicodedata.normalize("NFC", caplog.text),
    )


def test_check_na_forms():
    dataset, target = copy_to_temp(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    assert validate.check_na_form_has_no_alternative(dataset=dataset)


def test_check_empty_forms_warning(caplog):
    dataset, target = copy_to_temp(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    c_f_form = dataset["FormTable", "form"].name
    c_f_concept = dataset["FormTable", "parameterReference"].name
    forms = [f for f in dataset["FormTable"]]
    form = forms[0]
    form[c_f_form] = ""
    form[c_f_concept] = form[c_f_concept] + ["two"]
    forms[0] = form
    dataset.write(FormTable=forms)
    validate.check_na_form_has_no_alternative(dataset=dataset)
    assert re.search(r"Non empty forms exist for the empty form ache_one", caplog.text)


def test_check_no_separator_in_ids():
    dataset, target = copy_to_temp(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    assert validate.check_no_separator_in_ids(dataset=dataset)


@pytest.mark.skip(reason="not yet finished")
def test_check_no_separator_in_ids_warning(caplog):
    dataset, target = copy_to_temp(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    # c_c_id = dataset["ParameterTable", "id"].name
    # c_f_concept = dataset["FormTable", "parameterReference"].name
    # forms = [f for f in dataset["FormTable"]]
    # form = forms[0]
    # concept_id = form[c_f_concept][0]
    # concepts = {c[c_c_id]: c for c in dataset["ParameterTable"]}
    # concept = [c for c in dataset["ParameterTable"] if c[c_c_id] == concept_id]

import logging
from pathlib import Path
import unicodedata
import re

from helper_functions import copy_to_temp
import lexedata.report.extended_cldf_validate as validate


def test_check_foreignkeys_correct():
    dataset, target = copy_to_temp(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    assert validate.check_foreign_keys(dataset=dataset)


def test_check_foreignkeys_warning_table(caplog):
    pass
    # possible just change the resource of the foreignkey.reference to point to something else than the correct table
    dataset, target = copy_to_temp(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    # parameterReference point to column other than parameterID
    for i, key in enumerate(dataset["FormTable"].tableSchema.foreignKeys):
        if key.reference.resource.__str__() == "concepts.csv":
            key.reference.resource = dataset["CognateTable"]

    validate.check_foreign_keys(dataset=dataset)
    assert re.search(
        r"Foreign key ForeignKey.+is a declared as parameterReference, which should point to ParameterTable but instead points to.+",
        caplog.text,
    )


def test_check_foreignkeys_warning_id(caplog):
    dataset, target = copy_to_temp(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    # parameterReference point to column other than parameterID
    for i, key in enumerate(dataset["FormTable"].tableSchema.foreignKeys):
        if key.reference.resource.__str__() == "concepts.csv":
            key.reference.columnReference = [dataset["ParameterTable", "name"].name]

    validate.check_foreign_keys(dataset=dataset)
    assert re.search(
        r"Foreign key ForeignKey\(columnReference=\['Parameter_ID'],.+columnReference=\['Name']\)\) in table forms.csv does not point to the ID column of another table",
        caplog.text,
    )


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
    form[c_f_form] = "-"
    form[c_f_concept] = form[c_f_concept] + ["two"]
    forms[0] = form
    dataset.write(FormTable=forms)
    validate.check_na_form_has_no_alternative(dataset=dataset)
    assert re.search(r"exist for the NA form ache_one", caplog.text)


def test_check_no_separator_in_ids():
    dataset, target = copy_to_temp(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    assert validate.check_no_separator_in_ids(dataset=dataset)


def test_check_no_separator_in_ids_warning(caplog):
    dataset, target = copy_to_temp(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    c_f_concept = dataset["FormTable", "parameterReference"].name
    dataset["FormTable"].get_column(c_f_concept).separator = "_"
    validate.check_no_separator_in_ids(dataset=dataset)
    assert re.search(
        r"In table concepts.csv, row 8 column ID contains _, which is also the separator of \[\('forms.csv', 'Parameter_ID'\)]",
        caplog.text.split("\n")[-2],
    )


def test_check_judgements():
    dataset, target = copy_to_temp(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    assert validate.check_cognate_table(dataset=dataset)


def test_check_judgements_no_segslice_no_alignment(caplog):
    dataset, target = copy_to_temp(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    dataset.remove_columns("CognateTable", "Segment_Slice", "Alignment")
    with caplog.at_level(logging.INFO):
        assert validate.check_cognate_table(dataset=dataset)
    assert re.search("CognateTable.*no.*segmentSlice", caplog.text)
    assert re.search("CognateTable.*no.*alignment", caplog.text)

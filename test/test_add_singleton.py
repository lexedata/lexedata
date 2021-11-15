import logging
from pathlib import Path
import re

from lexedata.edit.add_singleton_cognatesets import create_singeltons
from lexedata.edit.add_status_column import add_status_column_to_table
from helper_functions import copy_to_temp_no_bib


def test_no_status_column(caplog):
    dataset, _ = copy_to_temp_no_bib(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    caplog.set_level(logging.INFO)
    create_singeltons(dataset=dataset)
    assert re.search(r".*No Status Column.*", caplog.text)


def test_singletons():
    dataset, _ = copy_to_temp_no_bib(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    add_status_column_to_table(dataset=dataset, table_name="CognatesetTable")

    all_cogsets, judgements = create_singeltons(dataset=dataset)
    c_c_id = dataset["CognateTable", "id"].name
    c_cs_id = dataset["CognatesetTable", "id"].name
    cognates = [c for c in judgements if c[c_c_id].startswith("X")]
    cogsets = [c for c in all_cogsets if c[c_cs_id].startswith("X")]
    assert cognates == [
        {
            "ID": "X1_old_paraguayan_guarani",
            "Form_ID": "old_paraguayan_guarani_two",
            "FIXME_IF_you_set_this_column_name_to_Value_it_messes_up_translations_due_to_conflict": "X1_old_paraguayan_guarani",
        },
        {
            "ID": "X2_paraguayan_guarani",
            "Form_ID": "paraguayan_guarani_five",
            "FIXME_IF_you_set_this_column_name_to_Value_it_messes_up_translations_due_to_conflict": "X2_paraguayan_guarani",
        },
        {
            "ID": "X3_ache",
            "Form_ID": "ache_five",
            "FIXME_IF_you_set_this_column_name_to_Value_it_messes_up_translations_due_to_conflict": "X3_ache",
        },
    ] and cogsets == [
        {
            "ID": "X1_old_paraguayan_guarani",
            "Name": "two",
            "Status_Column": "automatic singleton",
        },
        {
            "ID": "X2_paraguayan_guarani",
            "Name": "five",
            "Status_Column": "automatic singleton",
        },
        {"ID": "X3_ache", "Name": "five", "Status_Column": "automatic singleton"},
    ]

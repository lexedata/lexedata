import pytest
import shutil
import tempfile
from pathlib import Path

import pycldf
import openpyxl

from lexedata.importer.excelsinglewordlist import read_single_excel_sheet


def writable_copy_of_cldf_wordlist(cldf_wordlist):
    # Copy the dataset metadata file to a temporary directory.
    original = Path(__file__).parent / cldf_wordlist
    dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    target = dirname / original.name
    shutil.copyfile(original, target)
    # Create empty (because of the empty row list passed) csv files for the
    # dataset, one for each table, with only the appropriate headers in there.
    dataset = pycldf.Dataset.from_metadata(target)
    for table in dataset.tables:
        shutil.copyfile(
            original.parent / str(table.url), target.parent / str(table.url)
        )
    # Return the dataset API handle, which knows the metadata and tables.
    return dataset, original


@pytest.fixture(
    params=[
        (
            "data/cldf/smallmawetiguarani/cldf-metadata.json",
            "data/excel/test_single_excel_maweti.xlsx",
            "English",
        )
    ]
)
def single_import_parameters(request):
    original = Path(__file__).parent / request.param[0]
    dataset, original = writable_copy_of_cldf_wordlist(original)
    excel = Path(__file__).parent / request.param[1]
    concept_name = request.param[2]
    return dataset, original, excel, concept_name


def test_add_forms_maweti(single_import_parameters):
    dataset, original, excel, concept_name = single_import_parameters
    excel = openpyxl.load_workbook(excel)
    c_f_id = dataset["FormTable", "id"].name
    c_c_id = dataset["ParameterTable", "id"].name
    c_c_name = dataset["ParameterTable", "name"].name
    concepts = {c[c_c_name]: c[c_c_id] for c in dataset["ParameterTable"]}
    old_form_ids = {row[c_f_id] for row in dataset["FormTable"]}
    sheet = [sheet for sheet in excel.sheetnames]
    for sheet in sheet:
        read_single_excel_sheet(
            dataset=dataset,
            sheet=excel[sheet],
            entries_to_concepts=concepts,
            concept_column=concept_name,
        )
    new_form_ids = {row[c_f_id] for row in dataset["FormTable"]}
    assert new_form_ids - old_form_ids == {"ache_one_1", "ache_one_2"}

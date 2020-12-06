import pytest
import shutil
import tempfile
from pathlib import Path

import pycldf
import openpyxl

from lexedata.importer.excelsinglewordlist import read_single_excel_sheet


@pytest.fixture
def cldf_wordlist():
    return Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"


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


@pytest.fixture
def concept_name():
    return "English"


def test_add_forms(cldf_wordlist, concept_name):
    dataset, original = writable_copy_of_cldf_wordlist(cldf_wordlist)
    excel = openpyxl.load_workbook(
        Path(__file__).parent / "data/excel/test_single_excel_maweti.xlsx"
    )

    cid = dataset["ParameterTable", "id"].name
    concepts = {c[concept_name]: c[cid] for c in dataset["ParameterTable"]}
    concept_column = concept_name

    sheet = [sheet for sheet in excel.sheetnames]
    for sheet in sheet:
        read_single_excel_sheet(
            dataset=dataset,
            sheet=excel[sheet],
            entries_to_concepts=concepts,
            concept_column=concept_column,
        )

    # TODO: Compare results and expected

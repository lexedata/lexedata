import pytest
import shutil
import tempfile
from pathlib import Path

import pycldf
import openpyxl

from lexedata.importer.excelsinglewordlist import (
    read_single_excel_sheet,
    ImportLanguageReport,
)

from test_form_matcher import MockSingleExcelSheet


def copy_cldf_wordlist_no_bib(cldf_wordlist):
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
    dataset, original = copy_cldf_wordlist_no_bib(original)
    excel = Path(__file__).parent / request.param[1]
    concept_name = request.param[2]
    return dataset, original, excel, concept_name


def test_add_new_forms_maweti(single_import_parameters):
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
    assert new_form_ids - old_form_ids == {"ache_one_1"}


def test_import_error_missing_parameter_column(single_import_parameters):
    dataset, original, excel, concept_name = single_import_parameters
    c_c_id = dataset["ParameterTable", "id"].name
    c_c_name = dataset["ParameterTable", "name"].name
    concepts = {c[c_c_name]: c[c_c_id] for c in dataset["ParameterTable"]}
    sheet = MockSingleExcelSheet(
        [
            [
                "variants",
                "Form",
                "phonemic",
                "orthographic",
                "Segments",
                "procedural_comment",
                "Comment",
                "Source",
                "phonetic",
            ],
            [],
        ]
    )
    with pytest.raises(
        AssertionError, match=f"Could not find concept column {concept_name} in .*"
    ):
        read_single_excel_sheet(
            dataset=dataset,
            sheet=sheet,
            entries_to_concepts=concepts,
            concept_column=concept_name,
        )


def test_missing_columns1(single_import_parameters):
    dataset, original, excel, concept_name = single_import_parameters
    c_c_id = dataset["ParameterTable", "id"].name
    c_c_name = dataset["ParameterTable", "name"].name
    concepts = {c[c_c_name]: c[c_c_id] for c in dataset["ParameterTable"]}
    sheet = MockSingleExcelSheet(
        [
            [
                "variants",
                "Form",
                "Segments",
                "procedural_comment",
                "Comment",
                "Source",
                "phonetic",
                "phonemic",
            ],
            [],
        ]
    )
    with pytest.raises(
        ValueError,
        match="Your Excel sheet MockSingleExcelSheet is missing columns {'orthographic'}. "
        "Clean up your data, or use --ignore-missing-excel-columns to import anyway and "
        "leave these columns empty in the dataset for the newly imported forms.",
    ):
        read_single_excel_sheet(
            dataset=dataset,
            sheet=sheet,
            entries_to_concepts=concepts,
            concept_column=concept_name,
        )


def test_missing_columns2(single_import_parameters, caplog):
    dataset, original, excel, concept_name = single_import_parameters
    c_c_id = dataset["ParameterTable", "id"].name
    c_c_name = dataset["ParameterTable", "name"].name
    concepts = {c[c_c_name]: c[c_c_id] for c in dataset["ParameterTable"]}
    sheet = MockSingleExcelSheet(
        [
            [
                "variants",
                "Form",
                "Segments",
                "procedural_comment",
                "Comment",
                "Source",
                "phonetic",
                "phonemic",
                "superfluous",
                "superfluous2",
            ],
            [],
        ]
    )
    with pytest.raises(ValueError):
        read_single_excel_sheet(
            dataset=dataset,
            sheet=sheet,
            entries_to_concepts=concepts,
            concept_column="English",
            ignore_missing=True,
        )
    assert caplog.text.endswith(
        "Your Excel sheet MockSingleExcelSheet is missing columns "
        "{'orthographic'}. For the newly imported forms, these columns "
        "will be left empty in the dataset.\n"
    )


def test_superfluous_columns1(single_import_parameters):
    dataset, original, excel, concept_name = single_import_parameters
    c_c_id = dataset["ParameterTable", "id"].name
    c_c_name = dataset["ParameterTable", "name"].name
    concepts = {c[c_c_name]: c[c_c_id] for c in dataset["ParameterTable"]}
    sheet = MockSingleExcelSheet(
        [
            [
                "variants",
                "Form",
                "Segments",
                "procedural_comment",
                "Comment",
                "Source",
                "phonetic",
                "phonemic",
                "orthographic",
                "superfluous",
            ],
            [],
        ]
    )
    with pytest.raises(
        ValueError,
        match="Your Excel sheet MockSingleExcelSheet contained unexpected columns {'superfluous'}. "
        "Clean up your data, or use --ignore-superfluous-excel-columns to import the data anyway "
        "and ignore these columns.",
    ):
        read_single_excel_sheet(
            dataset=dataset,
            sheet=sheet,
            entries_to_concepts=concepts,
            concept_column="English",
        )


def test_superfluous_columns2(single_import_parameters, caplog):
    dataset, original, excel, concept_name = single_import_parameters
    c_c_id = dataset["ParameterTable", "id"].name
    c_c_name = dataset["ParameterTable", "name"].name
    concepts = {c[c_c_name]: c[c_c_id] for c in dataset["ParameterTable"]}
    sheet = MockSingleExcelSheet(
        [
            [
                "variants",
                "Form",
                "Segments",
                "procedural_comment",
                "Comment",
                "Source",
                "phonetic",
                "phonemic",
                "orthographic",
                "superfluous",
            ],
            [],
        ]
    )
    with pytest.raises(AssertionError):
        read_single_excel_sheet(
            dataset=dataset,
            sheet=sheet,
            entries_to_concepts=concepts,
            concept_column="English",
            ignore_superfluous=True,
        )
    assert caplog.text.endswith(
        "Your Excel sheet MockSingleExcelSheet contained unexpected columns "
        "{'superfluous'}. These columns will be ignored.\n"
    )


def test_no_concept_separator(single_import_parameters):
    import json

    dataset, original, excel, concept_name = single_import_parameters
    # delete parameterReference separator and store met
    json_file = dataset.tablegroup._fname
    with json_file.open("r+") as metadata_file:
        metadata = json.load(metadata_file)
        # del metadata["tables"][0]["tableSchema"]["columns"][2]["separator"]
        json.dump(metadata, metadata_file)
        # metadata_file.write("\n")
    dataset = pycldf.Dataset.from_metadata(dataset.tablegroup._fname)


#############################
# Test report functionality #
#############################


def test_import_report_new_language(single_import_parameters):
    dataset, original, excel, concept_name = single_import_parameters
    c_c_id = dataset["ParameterTable", "id"].name
    c_c_name = dataset["ParameterTable", "name"].name
    concepts = {c[c_c_name]: c[c_c_id] for c in dataset["ParameterTable"]}
    mocksheet = MockSingleExcelSheet(
        [
            [
                "English",
                "Form",
                "phonemic",
                "orthographic",
                "Segments",
                "procedural_comment",
                "Comment",
                "Source",
                "phonetic",
                "variants",
            ],
            [
                "one",
                "form",
                "phonemic",
                "orthographic",
                "f o r m",
                "-",
                "None",
                "source[10]",
                "phonetic",
                "",
            ],
        ]
    )
    mocksheet.title = "new_language"
    # Import this single form in a new language
    assert read_single_excel_sheet(
        dataset=dataset,
        sheet=mocksheet,
        entries_to_concepts=concepts,
        concept_column=concept_name,
    ) == {
        "new_language": ImportLanguageReport(
            is_new_language=True, new=1, existing=0, skipped=0, concepts=0
        )
    }


def test_import_report_existing_form(single_import_parameters):
    dataset, original, excel, concept_name = single_import_parameters
    c_c_id = dataset["ParameterTable", "id"].name
    c_c_name = dataset["ParameterTable", "name"].name
    concepts = {c[c_c_name]: c[c_c_id] for c in dataset["ParameterTable"]}
    mocksheet = MockSingleExcelSheet(
        [
            [
                "English",
                "Form",
                "phonemic",
                "orthographic",
                "Segments",
                "procedural_comment",
                "Comment",
                "Source",
                "phonetic",
                "variants",
            ],
            [
                "one",
                "form",
                "phonemic",
                "orthographic",
                "f o r m",
                "-",
                "None",
                "source[10]",
                "phonetic",
                "",
            ],
        ]
    )
    mocksheet.title = "new_language"
    # Import this single form in a new language
    read_single_excel_sheet(
        dataset=dataset,
        sheet=mocksheet,
        entries_to_concepts=concepts,
        concept_column=concept_name,
    )
    # Import it again, now both form and language should be existing
    assert read_single_excel_sheet(
        dataset=dataset,
        sheet=mocksheet,
        entries_to_concepts=concepts,
        concept_column=concept_name,
    ) == {
        "new_language": ImportLanguageReport(
            # TODO: Actually, this isn't a new language. The difference between
            # adding forms for a language that is not in the LanguageTable yet,
            # but already has forms in the FormTable, and adding something
            # completely new, is washed out by read_single_language. The
            # interpretation of “Does this language still need to be added to
            # the LanguageTable?” for is_new_language is consistent.
            is_new_language=True,
            new=0,
            existing=1,
            skipped=0,
            concepts=0,
        )
    }


def test_import_report_skipped(single_import_parameters):
    dataset, original, excel, concept_name = single_import_parameters
    c_c_id = dataset["ParameterTable", "id"].name
    c_c_name = dataset["ParameterTable", "name"].name
    concepts = {c[c_c_name]: c[c_c_id] for c in dataset["ParameterTable"]}
    mocksheet = MockSingleExcelSheet(
        [
            [
                "English",
                "Form",
                "phonemic",
                "orthographic",
                "Segments",
                "procedural_comment",
                "Comment",
                "Source",
                "phonetic",
                "variants",
            ],
            [
                "FAKE",
                "form",
                "phonemic",
                "orthographic",
                "f o r m",
                "-",
                "None",
                "source[10]",
                "phonetic",
                "",
            ],
        ]
    )
    mocksheet.title = "new_language"
    assert read_single_excel_sheet(
        dataset=dataset,
        sheet=mocksheet,
        entries_to_concepts=concepts,
        concept_column=concept_name,
    ) == {
        "new_language": ImportLanguageReport(
            # TODO: Actually, this isn't a new language. The difference between
            # adding forms for a language that is not in the LanguageTable yet,
            # but already has forms in the FormTable, and adding something
            # completely new, is washed out by read_single_language. The
            # interpretation of “Does this language still need to be added to
            # the LanguageTable?” for is_new_language is consistent.
            is_new_language=True,
            new=0,
            existing=0,
            skipped=1,
            concepts=0,
        )
    }

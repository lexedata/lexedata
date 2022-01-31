import pytest
import logging
from pathlib import Path
import re

import openpyxl

from lexedata.importer.excel_long_format import (
    read_single_excel_sheet,
    ImportLanguageReport,
    add_single_languages,
)
from mock_excel import MockSingleExcelSheet
from helper_functions import copy_metadata, copy_to_temp_no_bib


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
    dataset, target = copy_to_temp_no_bib(original)
    excel = Path(__file__).parent / request.param[1]
    concept_name = request.param[2]
    return dataset, target, excel, concept_name


def test_concept_file_not_found(caplog):
    from lexedata.cli import logger

    copy = copy_metadata(Path(__file__).parent / "data/cldf/minimal/cldf-metadata.json")
    add_single_languages(
        metadata=copy,
        sheets=[],
        match_form=None,
        concept_name=None,
        ignore_missing=True,
        ignore_superfluous=True,
        status_update=None,
        logger=logger,
    )
    assert re.search(
        r"Did not find concepts\.csv\. Importing all forms independent of concept",
        caplog.text,
    )


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
    dataset, target, excel, concept_name = single_import_parameters
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
    dataset, target, excel, concept_name = single_import_parameters
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
        match=".*sheet MockSingleExcelSheet.*missing col.*{[^a-z]*orthographic[^a-z]*}.*--ignore-missing-excel-columns",
    ):
        read_single_excel_sheet(
            dataset=dataset,
            sheet=sheet,
            entries_to_concepts=concepts,
            concept_column=concept_name,
        )


# TODO: Discuss with Gereon, Test has multiple asserts
def test_missing_columns2(single_import_parameters):
    dataset, target, excel, concept_name = single_import_parameters
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
                "undescribed",
                "superfluous2",
            ],
            [],
        ]
    )
    with pytest.raises(
        ValueError, match=".*sheet MockSingleExcelSheet.*unexpected col.*"
    ) as ex_info:
        read_single_excel_sheet(
            dataset=dataset,
            sheet=sheet,
            entries_to_concepts=concepts,
            concept_column="English",
            ignore_missing=True,
        )
    assert "undescribed" in ex_info.value.args[0]
    assert "superfluous2" in ex_info.value.args[0]
    assert "--ignore-superfluous-excel-columns" in ex_info.value.args[0]


def test_superfluous_columns1(single_import_parameters):
    dataset, target, excel, concept_name = single_import_parameters
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
        match=".* Excel sheet MockSingleExcelSheet contained unexpected columns {'superfluous'}.*"
        ".* use --ignore-superfluous-excel-columns .*",
    ):
        read_single_excel_sheet(
            dataset=dataset,
            sheet=sheet,
            entries_to_concepts=concepts,
            concept_column="English",
        )


def test_missing_concept(single_import_parameters, caplog):
    dataset, target, excel, concept_name = single_import_parameters
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
    concept_column_name = "Concept_Column_Name"
    # AssertionError on concept column not in excel header
    with pytest.raises(AssertionError, match=f".*{concept_column_name}.*"):
        read_single_excel_sheet(
            dataset=dataset,
            sheet=sheet,
            entries_to_concepts=concepts,
            concept_column=concept_column_name,
            ignore_superfluous=True,
        )


def test_superfluous_columns2(single_import_parameters, caplog):
    dataset, target, excel, concept_name = single_import_parameters
    concepts = {"Concept": "c_id_1"}
    sheet = MockSingleExcelSheet(
        [
            [
                "Form",
                "Segments",
                "English",
                "procedural_comment",
                "Comment",
                "Source",
                "phonetic",
                "phonemic",
                "variants",
                "orthographic",
                "superfluous",
            ],
            ["test form", "t e s t", "Concept"],
        ]
    )
    # AssertionError on concept column not in excel header
    with caplog.at_level(logging.INFO):
        read_single_excel_sheet(
            dataset=dataset,
            sheet=sheet,
            entries_to_concepts=concepts,
            concept_column="English",
            ignore_superfluous=True,
        )
    assert re.search(
        r"Excel sheet MockSingleExcelSheet contained unexpected columns {'superfluous'}. These columns will be ignored",
        caplog.text,
    )


# TODO: Discuss. Too manny asserts
def test_no_concept_separator(single_import_parameters, caplog):
    dataset, target, excel, concept_name = single_import_parameters
    dataset["FormTable", "parameterReference"].separator = None
    dataset.write_metadata()

    c_c_id = dataset["ParameterTable", "id"].name
    c_c_name = dataset["ParameterTable", "name"].name
    concepts = {c[c_c_name]: c[c_c_id] for c in dataset["ParameterTable"]}
    sheet = MockSingleExcelSheet(
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
    sheet.title = "new_language"

    # Import this single form in a new language
    assert read_single_excel_sheet(
        dataset=dataset,
        sheet=sheet,
        entries_to_concepts=concepts,
        concept_column=concept_name,
    ) == {
        "new_language": ImportLanguageReport(
            is_new_language=True, new=1, existing=0, skipped=0, concepts=0
        )
    }

    # Import it again, with a new concept
    sheet = MockSingleExcelSheet(
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
                "three",
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
    sheet.title = "new_language"

    # Test new concept was added as new form
    assert read_single_excel_sheet(
        dataset=dataset,
        sheet=sheet,
        entries_to_concepts=concepts,
        concept_column=concept_name,
    ) == {
        "new_language": ImportLanguageReport(
            is_new_language=True, new=1, existing=0, skipped=0, concepts=0
        )
    }
    # Test messages mention the solutions
    print(caplog.text)
    assert re.search(
        r"not.* polysemous forms.*separator.*FormTable.*parameterReference.*json.*lexedata\.report\.list_homophones",
        caplog.text,
    )


def test_concept_separator(single_import_parameters, caplog):
    dataset, target, excel, concept_name = single_import_parameters
    c_f_concept = dataset["FormTable", "parameterReference"].name
    match_form = [c_f_concept]
    concepts = dict()
    sheet = MockSingleExcelSheet(
        [
            [
                "English",
                "Form",
                "Segments",
                "procedural_comment",
                "Comment",
                "Source",
                "phonetic",
                "phonemic",
                "orthographic",
                "variants",
            ],
            [
                "three",
                "form",
                "f o r m",
                "auto-generated",
                "",
                "source[10]",
                "phonetic",
                "phonemic",
                "orthographic",
                "",
            ],
        ]
    )
    # ValueError on missing column
    with caplog.at_level(logging.INFO):
        read_single_excel_sheet(
            dataset=dataset,
            sheet=sheet,
            entries_to_concepts=concepts,
            match_form=match_form,
            concept_column="English",
        )
    assert re.search(
        r"[mM]atch.*concept.*lexedata\.report\.list_homophones", caplog.text
    )


def test_concept_not_found(single_import_parameters, caplog):
    dataset, target, excel, concept_name = single_import_parameters
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
    read_single_excel_sheet(
        dataset=dataset,
        sheet=mocksheet,
        entries_to_concepts=concepts,
        concept_column=concept_name,
    )
    assert re.search(r"Concept FAKE was not found", caplog.text)


def test_form_exists(single_import_parameters, caplog):
    dataset, target, excel, concept_name = single_import_parameters
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
                "two",  # existing concept, but new association
                "e.ta.'kɾã",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ],
        ]
    )
    mocksheet.title = "ache"
    with caplog.at_level(logging.INFO):
        read_single_excel_sheet(
            dataset=dataset,
            sheet=mocksheet,
            entries_to_concepts=concepts,
            concept_column=concept_name,
        )
    assert re.search(
        r"two.*e\.ta\.'kɾã.*was already in dataset",
        caplog.text,
    )


def test_new_concept_association(single_import_parameters, caplog):
    dataset, target, excel, concept_name = single_import_parameters
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
                "two",  # existing concept, but new association
                "e.ta.'kɾã",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ],
        ]
    )
    mocksheet.title = "ache"
    with caplog.at_level(logging.INFO):
        read_single_excel_sheet(
            dataset=dataset,
            sheet=mocksheet,
            entries_to_concepts=concepts,
            concept_column=concept_name,
        )
    # Test new concept association
    assert re.search(
        r"two.*added to.*ache_one",
        caplog.text,
    )


#############################
# Test report functionality #
#############################


def test_import_report_new_language(single_import_parameters):
    dataset, target, excel, concept_name = single_import_parameters
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
    dataset, target, excel, concept_name = single_import_parameters
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
    dataset, target, excel, concept_name = single_import_parameters
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
            is_new_language=True,
            new=0,
            existing=0,
            skipped=1,
            concepts=0,
        )
    }


# TODO: Multiply asserts
def test_import_report_add_concept(single_import_parameters):
    dataset, target, excel, concept_name = single_import_parameters
    c_c_id = dataset["ParameterTable", "id"].name
    c_c_name = dataset["ParameterTable", "name"].name
    concepts = {c[c_c_name]: c[c_c_id] for c in dataset["ParameterTable"]}
    sheet = MockSingleExcelSheet(
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
    sheet.title = "new_language"

    # Import this single form in a new language
    assert read_single_excel_sheet(
        dataset=dataset,
        sheet=sheet,
        entries_to_concepts=concepts,
        concept_column=concept_name,
    ) == {
        "new_language": ImportLanguageReport(
            is_new_language=True, new=1, existing=0, skipped=0, concepts=0
        )
    }

    # Import it again, with a new concept
    sheet = MockSingleExcelSheet(
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
                "three",
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
    sheet.title = "new_language"

    assert read_single_excel_sheet(
        dataset=dataset,
        sheet=sheet,
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
            skipped=0,
            concepts=1,
        )
    }


def test_add_concept_to_existing_form(single_import_parameters):
    dataset, target, excel, concept_name = single_import_parameters
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
                "two",
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
    # Import it again, now both form and language should be existing, but the form has a new concept
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
            skipped=0,
            concepts=1,
        )
    }

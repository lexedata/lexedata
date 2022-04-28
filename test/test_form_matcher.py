import pytest
import argparse
import unicodedata
from pathlib import Path
from tempfile import mkdtemp

import pycldf

from mock_excel import MockSingleExcelSheet
from lexedata.importer.excel_matrix import excel_parser_from_dialect
from lexedata.edit.add_segments import bipa


@pytest.fixture
def minimal_parser_with_dialect():
    tmpdir = Path(mkdtemp("", "fromexcel"))
    forms = tmpdir / "forms.csv"
    with forms.open("w", encoding="utf-8") as f:
        f.write("ID,Form,Language_ID,Parameter_ID")

    dataset = pycldf.Wordlist.from_data(forms)
    dataset["FormTable"].tableSchema.columns.append(
        pycldf.dataset.Column(
            {
                "name": "Value",
                "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#value",
            }
        )
    )
    dataset["FormTable", "parameterReference"].separator = ";"
    dataset.add_component("ParameterTable")
    dataset.add_component("LanguageTable")
    dataset._fname = tmpdir / "Wordlist-metadata.json"
    dataset.write_metadata()
    dataset = pycldf.Wordlist.from_metadata(dataset._fname)

    EP = excel_parser_from_dialect(
        dataset,
        argparse.Namespace(
            lang_cell_regexes=["(?P<Name>.*)"],
            lang_comment_regexes=[".*"],
            row_cell_regexes=["(?P<Name>.*)"],
            row_comment_regexes=[".*"],
            cell_parser={
                "form_separator": ",",
                "variant_separator": "~",
                "name": "CellParser",
                "cell_parser_semantics": [
                    ["<", ">", "Form", True],
                    ["{", "}", "Source", False],
                ],
            },
            check_for_match=["Form"],
            check_for_row_match=["Name"],
            check_for_language_match=["Name"],
        ),
        cognate=False,
    )

    EP = EP(dataset)
    EP.db.write_dataset_from_cache()
    return EP


def test_form_association(minimal_parser_with_dialect):
    lexicon_wb = MockSingleExcelSheet(
        [
            ["", "L1", "L2"],
            ["C1", "<L1C1>{1}", "<L2C1>{1}"],
            ["C2", "<L1C2>{1}", "<L2C2>{1}"],
        ]
    )
    minimal_parser_with_dialect.parse_cells(lexicon_wb)

    assert list(minimal_parser_with_dialect.db.retrieve("FormTable")) == [
        {
            "Language_ID": "l1",
            "Value": "<L1C1>{1}",
            "Form": "L1C1",
            "Source": {"l1_s1"},
            "ID": "l1_c1",
            "Parameter_ID": ["c1"],
        },
        {
            "Language_ID": "l2",
            "Value": "<L2C1>{1}",
            "Form": "L2C1",
            "Source": {"l2_s1"},
            "ID": "l2_c1",
            "Parameter_ID": ["c1"],
        },
        {
            "Language_ID": "l1",
            "Value": "<L1C2>{1}",
            "Form": "L1C2",
            "Source": {"l1_s1"},
            "ID": "l1_c2",
            "Parameter_ID": ["c2"],
        },
        {
            "Language_ID": "l2",
            "Value": "<L2C2>{1}",
            "Form": "L2C2",
            "Source": {"l2_s1"},
            "ID": "l2_c2",
            "Parameter_ID": ["c2"],
        },
    ]


def test_source_context(minimal_parser_with_dialect):
    """Check how the ‘context’ of a source is parsed

    The ‘context’ of a source, ie. its page number etc., should be added to the
    source column in square brackets after the source ID. It should be stripped
    of leading and trailing whitespace.

    """
    lexicon_wb = MockSingleExcelSheet(
        [
            ["", "L1"],
            ["C1", "<L1C1>{1:p. 34 }"],
        ]
    )
    minimal_parser_with_dialect.parse_cells(lexicon_wb)

    forms = list(minimal_parser_with_dialect.db.retrieve("FormTable"))
    assert len(forms) == 1
    assert forms[0] == {
        "Language_ID": "l1",
        "Value": "<L1C1>{1:p. 34 }",
        "Form": "L1C1",
        "Source": {"l1_s1[p. 34]"},
        "ID": "l1_c1",
        "Parameter_ID": ["c1"],
    }


def test_form_association_identical(minimal_parser_with_dialect):
    lexicon_wb = MockSingleExcelSheet(
        [
            ["", "L1", "L2"],
            ["C1", "<L1C1>{1}", "<L2C1>{1}"],
            ["C2", "<L1C1>{1}", "<L2C2>{1}"],
        ]
    )
    minimal_parser_with_dialect.parse_cells(lexicon_wb)

    assert list(minimal_parser_with_dialect.db.retrieve("FormTable")) == [
        {
            "Language_ID": "l1",
            "Value": "<L1C1>{1}",
            "Form": "L1C1",
            "Source": {"l1_s1"},
            "ID": "l1_c1",
            "Parameter_ID": ["c1", "c2"],
        },
        {
            "Language_ID": "l2",
            "Value": "<L2C1>{1}",
            "Form": "L2C1",
            "Source": {"l2_s1"},
            "ID": "l2_c1",
            "Parameter_ID": ["c1"],
        },
        {
            "Language_ID": "l2",
            "Value": "<L2C2>{1}",
            "Form": "L2C2",
            "Source": {"l2_s1"},
            "ID": "l2_c2",
            "Parameter_ID": ["c2"],
        },
    ]


def test_form_association_id_after_normalization(minimal_parser_with_dialect):
    f1 = "\xf1"  # Composed form of ñ
    f2 = "n\u0303"  # Decomposed form of ñ
    assert unicodedata.normalize("NFC", f1) == unicodedata.normalize("NFC", f2)
    lexicon_wb = MockSingleExcelSheet(
        [
            ["", "L1", "L2"],
            ["C1", f"<{f1}>{{1}}", "<L2C1>{1}"],
            ["C2", f"<{f2}>{{1}}", "<L2C2>{1}"],
        ]
    )
    minimal_parser_with_dialect.parse_cells(lexicon_wb)

    complete_forms = minimal_parser_with_dialect.db.retrieve("FormTable")
    forms = [(f["Language_ID"], f["Form"]) for f in complete_forms]

    assert (
        forms.count(("l1", "n\u0303")) + forms.count(("l1", "\xf1")) == 1
    ), """Only one variant, either the composed or the decomposed version, should
          persist. (It should be the NFC one, but that is not a
          guarantee of the code, just an implementation detail.)"""

    assert ["c1", "c2"] in [
        f["Parameter_ID"] for f in complete_forms
    ], "Accordingly, there should be one form both C1 and C2 are linked to."


def test_all_ipa_symbols(minimal_parser_with_dialect):
    lexicon_wb = MockSingleExcelSheet(
        [["", "L1"]] + [[s, f"<{s:}>{{bipa}}"] for s in bipa.sounds.keys()]
    )
    minimal_parser_with_dialect.parse_cells(lexicon_wb)

    complete_forms = minimal_parser_with_dialect.db.retrieve("FormTable")
    forms = {f["Form"] for f in complete_forms}

    assert set(unicodedata.normalize("NFC", f) for f in bipa.sounds.keys()) == set(
        unicodedata.normalize("NFC", f) for f in forms
    ), "Some IPA symbols got lost under import"

import pytest
import argparse
import unicodedata
from pathlib import Path
from tempfile import mkdtemp

import pycldf

from lexedata.importer.fromexcel import excel_parser_from_dialect


class C:
    "A mock cell"

    def __init__(self, value, row, column, comment=None):
        self.value = value or None
        self.comment = None
        self.column = column
        self.row = row

    @property
    def coordinate(self):
        return (self.row, self.column)

    def __repr__(self):
        return repr(self.value)


class MockWorkbook:
    def __init__(self, data):
        self.data = [
            [C(d, i, j) for j, d in enumerate(dr, 1)] for i, dr in enumerate(data, 1)
        ]
        self.title = "MockWorkbook"

    def iter_rows(self, min_row=1, max_row=None, min_col=1, max_col=None):
        if max_row is None:
            max_row = len(self.data)
        if max_col is None:
            max_col = len(self.data[0])
        for row in self.data[min_row - 1 : max_row]:
            yield row[min_col - 1 : max_col]

    def iter_cols(self, min_row=1, max_row=None, min_col=1, max_col=None):
        if max_row is None:
            max_row = len(self.data)
        if max_col is None:
            max_col = len(self.data[0])
        for c, col in enumerate(zip(*self.data[min_row - 1 : max_row])):
            if c < min_col - 1:
                continue
            if c == max_col + 1:
                break
            yield col


@pytest.fixture
def minimal_parser_with_dialect():
    tmpdir = Path(mkdtemp("", "fromexcel"))
    forms = tmpdir / "forms.csv"
    with (forms).open("w") as f:
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
    dataset["FormTable"].tableSchema.columns.append(
        pycldf.dataset.Column({"name": "variants", "separator": ","})
    )
    dataset["FormTable", "parameterReference"].separator = ";"
    dataset.add_component("ParameterTable")
    dataset.add_component("LanguageTable")
    dataset._fname = tmpdir / "Wordlist-metadata.json"
    dataset.write_metadata()
    dataset = pycldf.Wordlist.from_metadata(dataset._fname)

    db = tmpdir / "db.sqlite"

    EP = excel_parser_from_dialect(
        argparse.Namespace(
            lang_cell_regexes=["(?P<Name>.*)"],
            lang_comment_regexes=[".*"],
            row_cell_regexes=["(?P<Name>.*)"],
            row_comment_regexes=[".*"],
            cell_parser={
                "form_separator": ",",
                "variant_separator": "~",
                "name": "MawetiCellParser",
                "cell_parser_semantics": [
                    ["Form", "<", ">", True],
                    ["Source", "{", "}", False],
                ],
            },
            check_for_match=["Form"],
            check_for_row_match=["Name"],
            check_for_language_match=["Name"],
        ),
        cognate=False,
    )

    EP = EP(dataset, db_fname=db)
    EP.db.write_dataset_from_cache()
    return EP


def test_form_association(minimal_parser_with_dialect):
    lexicon_wb = MockWorkbook(
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
            "variants": [],
            "Source": {("l1_s1", None)},
            "ID": "l1_c1",
            "Parameter_ID": ["c1"],
        },
        {
            "Language_ID": "l2",
            "Value": "<L2C1>{1}",
            "Form": "L2C1",
            "variants": [],
            "Source": {("l2_s1", None)},
            "ID": "l2_c1",
            "Parameter_ID": ["c1"],
        },
        {
            "Language_ID": "l1",
            "Value": "<L1C2>{1}",
            "Form": "L1C2",
            "variants": [],
            "Source": {("l1_s1", None)},
            "ID": "l1_c2",
            "Parameter_ID": ["c2"],
        },
        {
            "Language_ID": "l2",
            "Value": "<L2C2>{1}",
            "Form": "L2C2",
            "variants": [],
            "Source": {("l2_s1", None)},
            "ID": "l2_c2",
            "Parameter_ID": ["c2"],
        },
    ]


def test_form_association_identical(minimal_parser_with_dialect):
    lexicon_wb = MockWorkbook(
        [
            ["", "L1", "L2"],
            ["C1", "<L1C1>{1}", "<L2C1>{1}"],
            ["C2", "<L1C1>{1}", "<L2C2>{1}"],
        ]
    )
    minimal_parser_with_dialect.parse_cells(lexicon_wb)

    assert list(minimal_parser_with_dialect.db.retrieve("FormTable")) == [{'Language_ID': 'l1', 'Value': '<L1C1>{1}', 'Form': 'L1C1', 'variants': [], 'Source': {('l1_s1', None)}, 'ID': 'l1_c1', 'Parameter_ID': ['c1', 'c2']}, {'Language_ID': 'l2', 'Value': '<L2C1>{1}', 'Form': 'L2C1', 'variants': [], 'Source': {('l2_s1', None)}, 'ID': 'l2_c1', 'Parameter_ID': ['c1']}, {'Language_ID': 'l2', 'Value': '<L2C2>{1}', 'Form': 'L2C2', 'variants': [], 'Source': {('l2_s1', None)}, 'ID': 'l2_c2', 'Parameter_ID': ['c2']}]


def test_form_association_id_after_normalization(minimal_parser_with_dialect):
    f1 = "\xf1"  # Composed form of ñ
    f2 = "n\u0303"  # Decomposed form of ñ
    assert unicodedata.normalize("NFD", f1) == unicodedata.normalize("NFD", f2)
    lexicon_wb = MockWorkbook(
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

    assert ["c1","c2"] in [f["Parameter_ID"] for f in complete_forms], "Accordingly, there should be one form both C1 and C2 are linked to."

import argparse
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


def test_form_association():
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
            lang_cell_regexes=["(?P<cldf_name>.*)"],
            lang_comment_regexes=[".*"],
            row_cell_regexes=["(?P<cldf_name>.*)"],
            row_comment_regexes=[".*"],
            cell_parser={
                "form_separator": ",",
                "variant_separator": "~",
                "name": "MawetiCellParser",
                "cell_parser_semantics": {
                    "cldf_form": ["<", ">", True],
                    "cldf_source": ["{", "}", False],
                },
            },
            check_for_match=["cldf_form"],
            check_for_row_match=["cldf_name"],
            check_for_language_match=["cldf_name"],
        ),
        cognate=False,
    )

    EP = EP(dataset, db_fname=db)
    EP.write()
    lexicon_wb = MockWorkbook(
        [
            ["", "L1", "L2"],
            ["C1", "<L1C1>{1}", "<L2C1>{1}"],
            ["C2", "<L1C2>{1}", "<L2C2>{1}"],
        ]
    )
    EP.parse_cells(lexicon_wb)

    print(EP.cldfdatabase.query("SELECT cldf_form FROM FormTable"))
    assert set(
        EP.cldfdatabase.query("SELECT cldf_languageReference, cldf_form FROM FormTable")
    ) == {
        ("l1", "L1C1"),
        ("l2", "L2C1"),
        ("l1", "L1C2"),
        ("l2", "L2C2"),
    }

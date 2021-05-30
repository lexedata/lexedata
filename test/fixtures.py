import argparse
import shutil
import tempfile
from pathlib import Path
from tempfile import mkdtemp

import cldfbench
import cldfcatalog

import pycldf
import pytest

from lexedata.importer.excel_matrix import excel_parser_from_dialect


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


class MockSingleExcelSheet:
    def __init__(self, data):
        self.data = [
            [C(d, i, j) for j, d in enumerate(dr, 1)] for i, dr in enumerate(data, 1)
        ]
        self.title = "MockSingleExcelSheet"

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

    @property
    def max_column(self):
        return max(len(r) for r in self.data)

    @property
    def max_row(self):
        return len(self.data)


@pytest.fixture(
    params=[
        "data/cldf/minimal/cldf-metadata.json",
        "data/cldf/smallmawetiguarani/cldf-metadata.json",
    ]
)
def cldf_wordlist(request):
    return Path(__file__).parent / request.param


@pytest.fixture(
    params=[
        (
            "data/excel/small.xlsx",
            "data/excel/small_cog.xlsx",
            "data/cldf/smallmawetiguarani/cldf-metadata.json",
        ),
        (
            "data/excel/minimal.xlsx",
            "data/excel/minimal_cog.xlsx",
            "data/cldf/minimal/cldf-metadata.json",
        ),
    ]
)
def excel_wordlist(request):
    return (
        Path(__file__).parent / request.param[0],
        Path(__file__).parent / request.param[1],
        empty_copy_of_cldf_wordlist(Path(__file__).parent / request.param[2]),
    )


def empty_copy_of_cldf_wordlist(cldf_wordlist):
    # Copy the dataset metadata file to a temporary directory.
    original = Path(__file__).parent / cldf_wordlist
    dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    target = dirname / original.name
    shutil.copyfile(original, target)
    # Create empty (because of the empty row list passed) csv files for the
    # dataset, one for each table, with only the appropriate headers in there.
    dataset = pycldf.Dataset.from_metadata(target)
    dataset.write(**{str(table.url): [] for table in dataset.tables})
    # Return the dataset API handle, which knows the metadata and tables.
    return dataset, original


def copy_to_temp_no_bib(cldf_wordlist):
    """Copy the dataset to a temporary location, then delete the sources file."""
    dataset, target = copy_to_temp(cldf_wordlist)
    dataset.bibpath.unlink()
    return dataset, target


def copy_to_temp(cldf_wordlist):
    """Copy the dataset to a different temporary location, so that editing the dataset will not change it."""
    original = cldf_wordlist
    dataset = pycldf.Dataset.from_metadata(original)
    orig_bibpath = dataset.bibpath

    dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    target = dirname / original.name
    shutil.copyfile(original, target)
    dataset = pycldf.Dataset.from_metadata(target)
    for table in dataset.tables:
        link = Path(str(table.url))
        o = original.parent / link
        t = target.parent / link
        shutil.copyfile(o, t)
    link = dataset.bibpath.name
    o = original.parent / link
    t = target.parent / link
    shutil.copyfile(o, t)
    shutil.copyfile(orig_bibpath, dataset.bibpath)
    return dataset, target


def copy_to_temp_bad_bib(cldf_wordlist):
    """Copy the dataset to a temporary location, then mess with the source file syntax."""
    dataset, target = copy_to_temp(cldf_wordlist)
    with dataset.bibpath.open("a") as bibfile:
        bibfile.write("\n { \n")
    return dataset, target


def copy_metadata(original: Path):
    dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    target = dirname / "cldf-metadata.json"
    copy = shutil.copyfile(original, target)
    return copy


@pytest.fixture
def empty_excel():
    return Path(__file__).parent / "data/cldf/defective_dataset/empty_excel.xlsx"


@pytest.fixture
def bipa():
    clts_path = cldfcatalog.Config.from_file().get_clone("clts")
    clts = cldfbench.catalogs.CLTS(clts_path)
    bipa = clts.api.bipa
    return bipa


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
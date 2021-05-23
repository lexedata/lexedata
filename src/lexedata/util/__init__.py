# -*- coding: utf-8 -*-
import re
import zipfile
import tempfile
import typing as t
from pathlib import Path

import unicodedata
import unidecode as uni
import pycldf
import openpyxl as op
import networkx
from lingpy.compare.strings import ldn_swap

import csvw
from lexedata.cli import tq
from lexedata.enrich.add_free_metadata import add_metadata

from ..types import KeyKeyDict
from . import fs

__all__ = [fs, KeyKeyDict]

ID_FORMAT = re.compile("[a-z0-9_]+")


def ensure_list(maybe_string: t.Union[t.List[str], str, None]) -> t.List[str]:
    if maybe_string is None:
        return []
    elif isinstance(maybe_string, list):
        return maybe_string
    else:
        return [maybe_string]


def cldf_property(url: csvw.metadata.URITemplate) -> t.Optional[str]:
    if url.uri.startswith("http://cldf.clld.org/v1.0/terms.rdf#"):
        # len("http://cldf.clld.org/v1.0/terms.rdf#") == 36
        return url.uri[36:]
    else:
        return None


def string_to_id(string: str) -> str:
    """Generate a useful id string from the string

    >>> string_to_id("trivial")
    'trivial'
    >>> string_to_id("Just 4 non-alphanumerical characters.")
    'just_4_non_alphanumerical_characters'
    >>> string_to_id("Это русский.")
    'eto_russkii'
    >>> string_to_id("该语言有一个音节。")
    'gai_yu_yan_you_yi_ge_yin_jie'
    >>> string_to_id("この言語には音節があります。")
    'konoyan_yu_nihayin_jie_gaarimasu'

    """
    # The Japanese ist actually transcribed incorrectly, because unidecode is
    # (relatively) simple, but that doesn't matter for the approximation of a
    # generic string by a very restricted string.

    # We convert to lower case twice, because it can in principle happen that a
    # character without lowercase equivalent is mapped to an uppercase
    # character by unidecode, and we wouldn't want to lose that.
    return "_".join(ID_FORMAT.findall(uni.unidecode(string.lower()).lower()))


def clean_cell_value(cell: op.cell.cell.Cell):
    if cell.value is None:
        return ""
    if type(cell.value) == float:
        if cell.value == int(cell.value):
            return int(cell.value)
        return cell.value
    v = unicodedata.normalize("NFC", (cell.value or "").strip())
    if type(v) == float:
        if v == int(v):
            return int(v)
        return v
    if type(v) == int:
        return v
    try:
        return v.replace("\n", ";\t")
    except TypeError:
        return str(v)


def normalize_string(text: str):
    return unicodedata.normalize("NFC", text.strip())


def get_cell_comment(cell: op.cell.Cell) -> str:
    raw_comment = cell.comment.text.strip() if cell.comment else ""
    lines = [
        line for line in raw_comment.split("\n") if line.strip() != "-lexedata.exporter"
    ]
    return " ".join(lines)


def normalize_header(row: t.Iterable[op.cell.Cell]) -> t.Iterable[str]:
    header = [unicodedata.normalize("NFKC", (n.value or "").strip()) for n in row]
    header = [h.replace(" ", "_") for h in header]
    header = [h.replace("(", "") for h in header]
    header = [h.replace(")", "") for h in header]

    return header


def get_dataset(fname: Path) -> pycldf.Dataset:
    """Load a CLDF dataset.

    Load the file as `json` CLDF metadata description file, or as metadata-free
    dataset contained in a single csv file.

    The distinction is made depending on the file extension: `.json` files are
    loaded as metadata descriptions, all other files are matched against the
    CLDF module specifications. Directories are checked for the presence of
    any CLDF datasets in undefined order of the dataset types.

    Parameters
    ----------
    fname : str or Path
        Path to a CLDF dataset

    Returns
    -------
    Dataset
    """
    fname = Path(fname)
    if not fname.exists():
        raise FileNotFoundError("{:} does not exist".format(fname))
    if fname.suffix == ".json":
        return pycldf.dataset.Dataset.from_metadata(fname)
    return pycldf.dataset.Dataset.from_data(fname)


def edit_distance(text1: str, text2: str) -> float:
    # We request LingPy as dependency anyway, so use its implementation
    if not text1 and not text2:
        return 0.3
    text1 = uni.unidecode(text1 or "").lower()
    text2 = uni.unidecode(text2 or "").lower()
    length = max(len(text1), len(text2))
    return ldn_swap(text1, text2, normalized=False) / length


def load_clics():
    gml_file = (
        Path(__file__).parent.parent
        / "data/clics-clics3-97832b5/clics3-network.gml.zip"
    )
    if not gml_file.exists():
        import urllib.request

        file_name, headers = urllib.request.urlretrieve(
            "https://zenodo.org/record/3687530/files/clics/clics3-v1.1.zip?download=1"
        )
        zfobj = zipfile.ZipFile(file_name)
        zfobj.extract(
            "clics-clics3-97832b5/clics3-network.gml.zip",
            Path(__file__).parent.parent / "data/",
        )
    gml = zipfile.ZipFile(gml_file).open("graphs/network-3-families.gml", "r")
    return networkx.parse_gml(line.decode("utf-8") for line in gml)


def parse_segment_slices(
    segment_slices: t.Sequence[str], enforce_ordered=False
) -> t.Iterator[int]:
    """Parse a segment slice representation into its component indices

    NOTE: Segment slices are 1-based, inclusive; Python indices are 0-based
    (and we are not working with ranges, but they are also exclusive).

    >>> list(parse_segment_slices(["1:3"]))
    [0, 1, 2]

    >>> list(parse_segment_slices(["1:3", "2:4"]))
    [0, 1, 2, 1, 2, 3]

    >>> list(parse_segment_slices(["1:3", "2:4"], enforce_ordered=True))
    Traceback (most recent call last):
    ...
    ValueError: Segment slices are not ordered as required.

    """
    i = -1  # Set it to the value before the first possible segment slice start
    for startend in segment_slices:
        start, end = startend.split(":")
        start = int(start)
        end = int(end)
        if end < start:
            raise ValueError(f"Segment slice {startend} had start after end.")
        if enforce_ordered and start <= i:
            raise ValueError("Segment slices are not ordered as required.")
        for i in range(start - 1, end):
            yield i


def make_temporary_dataset(form_table):
    directory = Path(tempfile.mkdtemp())
    form_table_file_name = directory / "forms.csv"
    with form_table_file_name.open("w") as form_table_file:
        form_table_file.write(form_table)
    dataset = add_metadata(form_table_file_name)
    dataset.write(directory / "Wordlist-metadata.json")
    return dataset


# TODO: Is this logic sound?
def cache_table(
    dataset,
    table: t.Optional[str] = None,
    columns: t.Optional[t.Mapping[str, str]] = None,
    index_column="id",
) -> t.Mapping[str, t.Mapping[str, t.Any]]:
    """Load a dataset table into memory as a dictionary of dictionaries.

    If the table is unspecified, use the primary table of the dataset.

    If the columns are unspecified, read each row completely, into a dictionary
    indexed by the local CLDF properties of the table.

    Examples
    ========

    >>> ds = make_temporary_dataset('''ID,Language_ID,Parameter_ID,Form,Variants
    ... ache_one,ache,one,"e.ta.'kɾã",~[test phonetic variant]
    ... ''')
    >>> forms = cache_table(ds)
    >>> forms["ache_one"]["languageReference"]
    'ache'
    >>> forms["ache_one"]["form"]
    "e.ta.'kɾã"
    >>> forms["ache_one"]["Variants"]
    ['~[test phonetic variant]']

    We can also use it to look up a specific set of columns, and change the index column.
    This allows us, for example, to get language IDs by name:
    >>> _ = ds.add_component("LanguageTable")
    >>> ds.write(LanguageTable=[
    ...     ['ache', 'Aché', 'South America', -25.59, -56.47, "ache1246", "guq"],
    ...     ['paraguayan_guarani', 'Paraguayan Guaraní', None, None, None, None, None]])
    >>> languages = cache_table(ds, "LanguageTable", {"id": "ID"}, index_column="Name")
    >>> languages == {'Aché': {'id': 'ache'},
    ...               'Paraguayan Guaraní': {'id': 'paraguayan_guarani'}}
    True

    In this case identical values later in the file overwrite earlier ones.

    """
    if table is None:
        table = dataset.primary_table
    assert (
        table
    ), "If your dataset has no primary table, you must specify which table to cache."
    if columns is None:
        columns = {
            (cldf_property(c.propertyUrl) if c.propertyUrl else c.name)
            or c.name: c.name
            for c in dataset[table].tableSchema.columns
        }
    c_id = dataset[table, index_column].name
    return {
        row[c_id]: {prop: row[name] for prop, name in columns.items()}
        for row in tq(
            dataset[table], total=dataset[table].common_props.get("dc:extent")
        )
    }

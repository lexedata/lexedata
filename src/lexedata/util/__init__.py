# -*- coding: utf-8 -*-
import re
import typing as t
import unicodedata
import zipfile

import csvw
import networkx
import pkg_resources
import unidecode as uni
from lexedata.cli import logger, tq
from lingpy.compare.strings import ldn_swap

from ..types import KeyKeyDict
from . import fs

__all__ = ["fs", "KeyKeyDict"]

ID_FORMAT = re.compile("[a-z0-9_]+")

MI = t.TypeVar("MI")


def ensure_list(maybe_string: t.Union[t.List[MI], MI, None]) -> t.List[MI]:
    if maybe_string is None:
        return []
    elif isinstance(maybe_string, list):
        return maybe_string
    else:
        return [maybe_string]


def cldf_property(url: t.Optional[csvw.metadata.URITemplate]) -> t.Optional[str]:
    if url is None:
        return None
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


def normalize_string(text: str):
    return unicodedata.normalize("NFC", text.strip())


def edit_distance(text1: str, text2: str) -> float:
    # We request LingPy as dependency anyway, so use its implementation
    if not text1 and not text2:
        return 0.3
    text1 = uni.unidecode(text1 or "").lower()
    text2 = uni.unidecode(text2 or "").lower()
    length = max(len(text1), len(text2))
    return ldn_swap(text1, text2, normalized=False) / length


def load_clics():
    """Load CLICS as networkx Graph.

    Lexedata packages the CLICS colexification graph in GML format from
    https://zenodo.org/record/3687530/files/clics/clics3-v1.1.zip?download=1

    """
    gml = zipfile.ZipFile(
        pkg_resources.resource_stream("lexedata", "data/clics3-network.gml.zip")
    ).open("graphs/network-3-families.gml", "r")
    return networkx.parse_gml(line.decode("utf-8") for line in gml)


def parse_segment_slices(
    segment_slices: t.Sequence[str], enforce_ordered=False
) -> t.Iterator[int]:
    """Parse a segment slice representation into its component indices

    NOTE: Segment slices are 1-based, inclusive; Python indices are 0-based
    (and we are not working with ranges, but they are also exclusive).

    >>> list(parse_segment_slices(["1:3"]))
    [0, 1, 2]

    >>> list(parse_segment_slices(["1", "2:4"]))
    [0, 1, 2, 3]

    >>> list(parse_segment_slices(["1:3", "2:4"]))
    [0, 1, 2, 1, 2, 3]

    >>> list(parse_segment_slices(["1:3", "2:4"], enforce_ordered=True))
    Traceback (most recent call last):
    ...
    ValueError: Segment slices are not ordered as required.

    """
    i = -1  # Set it to the value before the first possible segment slice start
    for startend in segment_slices:
        try:
            start_str, end_str = startend.split(":")
        except ValueError:
            start_str, end_str = startend, startend
        start = int(start_str)
        end = int(end_str)
        if end < start:
            raise ValueError(f"Segment slice {startend} had start after end.")
        if enforce_ordered and start <= i:
            raise ValueError("Segment slices are not ordered as required.")
        for i in range(start - 1, end):
            yield i


def indices_to_segment_slice(
    indices: t.Iterable[int], enforce_ordered=False
) -> t.Sequence[str]:
    """Turn component indices into a segment slice representation

    This is the inverse of parse_segment_slices.

    NOTE: Segment slices are 1-based, inclusive; Python indices are 0-based
    (and if given as ranges, they are also exclusive).

    >>> indices_to_segment_slice(parse_segment_slices(["1:3"]))
    ['1:3']
    >>> indices_to_segment_slice([0, 1, 2])
    ['1:3']
    >>> indices_to_segment_slice([0, 1, 3])
    ['1:2', '4:4']
    >>> indices_to_segment_slice([0, 1, 2, 0])
    ['1:3', '1:1']
    >>> indices_to_segment_slice([0, 1, 2, 0], enforce_ordered=True)
    Traceback (most recent call last):
    ...
    ValueError: Indices are not ordered as required.
    """
    slices = []
    start_range = 0
    prev = -1
    for i in indices:
        if prev + 1 == i:
            prev = i
            continue
        if i <= prev:
            if enforce_ordered:
                raise ValueError("Indices are not ordered as required.")
        if prev != -1:
            slices.append("{:d}:{:d}".format(start_range + 1, prev + 1))
        start_range = i
        prev = i
    slices.append("{:d}:{:d}".format(start_range + 1, prev + 1))
    return slices


def cache_table(
    dataset,
    table: t.Optional[str] = None,
    columns: t.Optional[t.Mapping[str, str]] = None,
    index_column: str = "id",
    filter: t.Callable[[t.Mapping[str, t.Any]], bool] = lambda e: True,
) -> t.Mapping[str, t.Mapping[str, t.Any]]:
    """Load a dataset table into memory as a dictionary of dictionaries.

    If the table is unspecified, use the primary table of the dataset.

    If the columns are unspecified, read each row completely, into a dictionary
    indexed by the local CLDF properties of the table.

    Examples
    ========

    >>> ds = fs.new_wordlist(FormTable=[{
    ...  "ID": "ache_one",
    ...  "Language_ID": "ache",
    ...  "Parameter_ID": "one",
    ...  "Form": "e.ta.'kɾã",
    ...  "variants": ["~[test phonetic variant]"]
    ... }])
    >>> forms = cache_table(ds)
    >>> forms["ache_one"]["languageReference"]
    'ache'
    >>> forms["ache_one"]["form"]
    "e.ta.'kɾã"
    >>> forms["ache_one"]["variants"]
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
            (cldf_property(c.propertyUrl) if c.propertyUrl else c.name): c.name
            for c in dataset[table].tableSchema.columns
        }
    c_id = dataset[table, index_column].name
    return {
        row[c_id]: {prop: row[name] for prop, name in columns.items()}
        for row in tq(
            dataset[table],
            task=f"Caching table {table}",
            total=dataset[table].common_props.get("dc:extent"),
        )
        if filter(row)
    }


def normalize_table_name(name, dataset, logger=logger):
    try:
        return str(dataset[name].url)
    except KeyError:
        logger.warning("Could not find table {}".format(name))
        return None

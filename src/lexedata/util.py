# -*- coding: utf-8 -*-
import re
import zipfile
import typing as t
from pathlib import Path

import unicodedata
import unidecode as uni
import pycldf
import openpyxl as op
import networkx
from lingpy.compare.strings import ldn_swap

import lexedata.types


invalid_id_elements = re.compile(r"\W+")


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
    # We nee to run this through valid_id_elements twice, because some word
    # characters (eg. Chinese) are unidecoded to contain non-word characters.
    # the japanese ist actually decoded incorrectly
    return invalid_id_elements.sub(
        "_", uni.unidecode(invalid_id_elements.sub("_", string)).lower()
    ).strip("_")


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


def get_cell_comment(cell: op.cell.Cell) -> t.Optional[str]:
    return cell.comment.text.strip() if cell.comment else ""


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
        Path(__file__).parent / "data/clics-clics3-97832b5/clics3-network.gml.zip"
    )
    if not gml_file.exists():
        import urllib.request

        file_name, headers = urllib.request.urlretrieve(
            "https://zenodo.org/record/3687530/files/clics/clics3-v1.1.zip?download=1"
        )
        zfobj = zipfile.ZipFile(file_name)
        zfobj.extract(
            "clics-clics3-97832b5/clics3-network.gml.zip",
            Path(__file__).parent / "data/",
        )
    gml = zipfile.ZipFile(gml_file).open("graphs/network-3-families.gml", "r")
    return networkx.parse_gml(line.decode("utf-8") for line in gml)


def segment_slices_to_segment_list(
    segments: t.Iterable[str], judgement: lexedata.types.Judgement
):
    segment_list = []
    if not judgement.get("Segment_Slice"):
        judgement["Segment_Slice"] = ["0:{:d}".format(len(segments))]
    for startend in judgement["Segment_Slice"]:
        start, end = startend.split(":")
        start = int(start)
        end = int(end)
        segment_list.extend(list(r for r in range(start, end)))
    return segment_list


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs="+", type=Path)
    args = parser.parse_args()
    for file in args.file:
        content = file.open().read()
        file.open("w").write(unicodedata.normalize("NFKD", content))

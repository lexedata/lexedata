import shutil
import tempfile
import typing as t
from pathlib import Path

import pycldf

from lexedata.util.fs import copy_dataset
from lexedata.types import Wordlist


def copy_metadata(original: Path) -> Path:
    dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    target = dirname / "cldf-metadata.json"
    copy = shutil.copyfile(original, target)
    return copy


def empty_copy_of_cldf_wordlist(cldf_wordlist) -> t.Tuple[pycldf.Dataset, Path]:
    # Copy the dataset metadata file to a temporary directory.
    original = Path(__file__).parent / cldf_wordlist
    copy = copy_metadata(original)

    # Create empty (because of the empty row list passed) csv files for the
    # dataset, one for each table, with only the appropriate headers in there.
    dataset = pycldf.Dataset.from_metadata(copy)
    dataset.write(**{str(table.url): [] for table in dataset.tables})
    # Return the dataset API handle, which knows the metadata and tables.
    return dataset, original


def copy_to_temp(cldf_wordlist: Path) -> t.Tuple[Wordlist, Path]:
    """Copy the dataset to a different temporary location.

    Given a dataset, copy it to a temporary location and return the new dataset
    and its path. This enables us to edit a dataset in the file system, without
    changing the original.

    """
    dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    target = dirname / cldf_wordlist.name
    dataset = copy_dataset(cldf_wordlist, target)
    return dataset, target


def copy_to_temp_no_bib(cldf_wordlist):
    """Copy the dataset to a temporary location, then delete the sources file."""
    dataset, target = copy_to_temp(cldf_wordlist)
    dataset.bibpath.unlink()
    return dataset, target


def copy_to_temp_bad_bib(cldf_wordlist):
    """Copy the dataset to a temporary location, then mess with the source file syntax."""
    dataset, target = copy_to_temp(cldf_wordlist)
    with dataset.bibpath.open("a", encoding="utf-8") as bibfile:
        bibfile.write("\n { \n")
    return dataset, target

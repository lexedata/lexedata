import shutil
import tempfile
from pathlib import Path

import pycldf


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

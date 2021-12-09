import csv
import shutil
import tempfile
import typing as t
from pathlib import Path

import pycldf

from lexedata import types
from lexedata.util.add_metadata import add_metadata


def new_wordlist(
    path: t.Optional[Path] = None, **data
) -> types.Wordlist[str, str, str, str, str]:
    """Create a new CLDF wordlist.

    By default, the wordlist is created in a new temporary directory, but you
    can specify a path to create it in.

    To immediately fill some tables, provide keyword arguments. The necessary
    components will be created in default shape, so

    >>> ds = new_wordlist()

    will only have a FormTable

    >>> [table.url.string for table in ds.tables]
    ['forms.csv']

    but it is possible to generate a dataset with more tables from scratch

    >>> ds = new_wordlist(
    ...     FormTable=[],
    ...     LanguageTable=[],
    ...     ParameterTable=[],
    ...     CognatesetTable=[],
    ...     CognateTable=[])
    >>> [table.url.string for table in ds.tables]
    ['forms.csv', 'languages.csv', 'parameters.csv', 'cognatesets.csv', 'cognates.csv']
    >>> sorted(f.name for f in ds.directory.iterdir())
    ['Wordlist-metadata.json', 'cognates.csv', 'cognatesets.csv', 'forms.csv', 'languages.csv', 'parameters.csv']
    """
    if path is None:
        path = Path(tempfile.mkdtemp())

    if data.get("FormTable"):
        forms = data["FormTable"]
        keys: t.List[str] = list(set().union(*forms))
        with (path / "forms.csv").open("w", encoding="utf8") as form_table_file:
            writer = csv.DictWriter(form_table_file, fieldnames=keys)
            writer.writeheader()
            writer.writerows(forms)
        dataset = add_metadata((path / "forms.csv"))
    else:
        dataset = pycldf.Wordlist.from_metadata(path)
    for component in data:
        if component not in dataset:
            dataset.add_component(component)
    dataset.write(**data)
    return dataset


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


def copy_dataset(original: Path, target: Path) -> pycldf.Dataset:
    """Return a copy of the dataset at original.

    Copy the dataset (metadata and relative table URLs) from `original` to
    `target`, and return the new dataset at `target`.

    """
    dataset = pycldf.Dataset.from_metadata(original)
    orig_bibpath = dataset.bibpath
    shutil.copyfile(original, target)

    dataset = pycldf.Dataset.from_metadata(target)
    for table in dataset.tables:
        link = Path(str(table.url))
        olink = original.parent / link
        tlink = target.parent / link
        shutil.copyfile(olink, tlink)
    link = dataset.bibpath.name
    olink = original.parent / link
    tlink = target.parent / link
    shutil.copyfile(olink, tlink)
    shutil.copyfile(orig_bibpath, dataset.bibpath)

    return dataset

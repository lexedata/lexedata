import tempfile
import typing as t
from pathlib import Path

import pycldf


def new_wordlist(path: t.Optional[Path] = None, **data):
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

    """
    if path is None:
        path = Path(tempfile.mkdtemp())
    dataset = pycldf.Wordlist.from_metadata(path)
    for component in data:
        if component not in dataset:
            dataset.add_component(component)
    dataset.write(**data)
    return dataset

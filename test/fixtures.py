import shutil
import tempfile
from pathlib import Path

import pycldf
import pytest


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


def copy_metadata(original: Path):
    dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    target = dirname / "cldf-metadata.json"
    copy = shutil.copyfile(original, target)
    return copy


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

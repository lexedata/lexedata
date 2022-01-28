import logging
import tempfile
import argparse
from lexedata import cli
from lexedata.report.filter import parser as filter_parser


def test_listorfromfile_list():
    parser = argparse.ArgumentParser()
    parser.add_argument("--objects", action=cli.ListOrFromFile, help="Some objects.")
    parser.add_argument("--other", action="store_true", default=False)
    parameters = parser.parse_args(["--objects", "o1", "o2", "o3", "--other"])
    assert parameters.other
    assert parameters.objects == ["o1", "o2", "o3"]


def test_listorfromfile_file():
    parser = argparse.ArgumentParser()
    parser.add_argument("--objects", action=cli.ListOrFromFile, help="Some objects.")
    parser.add_argument("--other", action="store_true", default=False)
    _, fname = tempfile.mkstemp(".csv")
    with open(fname, "w") as file:
        file.write("ID,ignored\no1,yes\no2\no3,")
    parameters = parser.parse_args(["--objects", fname, "--other"])
    assert parameters.other
    assert parameters.objects == ["o1", "o2", "o3"]


def test_filter_parser():
    _, fname = tempfile.mkstemp(".csv")
    parameters = filter_parser().parse_args(
        ["form", "a", "FormTable", "-V", "-o", fname]
    )
    assert parameters.table == "FormTable"
    assert parameters.column == "form"
    assert parameters.filter == "a"
    assert parameters.invert is True
    assert parameters.output_columns == []
    assert parameters.output_file.name == fname


def test_loglevel_parser():
    parameters = filter_parser().parse_args(
        ["form", "-q", "-q", "a", "FormTable", "-v", "-V", "-q"]
    )
    # Optional positional argument ("FormTable") after optional switch ("-q",
    # but also "-V" which uses a builtin action) does not seem to work.
    assert parameters.loglevel == logging.ERROR

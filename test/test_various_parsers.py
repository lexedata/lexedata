import logging
import tempfile
import argparse
from pathlib import Path

from lexedata import cli, types
from lexedata.report.filter import parser as filter_parser
from lexedata.exporter.phylogenetics import (
    CodingProcedure,
    AbsenceHeuristic,
    parser as phylo_parser,
)
from lexedata.exporter.cognates import parser as cex_parser


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


def test_phylo_parser():
    _, fname = tempfile.mkstemp(".csv")
    with open(fname, "w") as file:
        file.write("ID,ignored\nl1,yes\nl2\nl3,")
    _, ofname = tempfile.mkstemp(".csv")
    parameters = phylo_parser().parse_args(
        [
            "-b",
            "-o",
            ofname,
            "--languages",
            fname,
            "--coding",
            "rootpresence",
            "--absence-heuristic",
            "centralconcept",
        ]
    )
    assert parameters.format == "beast"
    assert parameters.output_file.absolute() == Path(ofname).absolute()
    assert parameters.languages == ["l1", "l2", "l3"]
    assert type(parameters.concepts) == types.WorldSet
    assert type(parameters.cognatesets) == types.WorldSet
    assert parameters.coding == CodingProcedure.ROOTPRESENCE
    assert parameters.absence_heuristic == AbsenceHeuristic.CENTRALCONCEPT


def test_cex_parser():
    _, fname = tempfile.mkstemp(".xlsx")
    parameters = cex_parser().parse_args([fname, "--add-singletons"])
    assert parameters.add_singletons_with_status == "automatic singleton"

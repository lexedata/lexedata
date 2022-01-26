import logging
from lexedata.report.filter import parser as filter_parser


def test_filter_parser():
    parameters = filter_parser().parse_args(["form", "a", "FormTable", "-V"])
    assert parameters.table == "FormTable"
    assert parameters.column == "form"
    assert parameters.filter == "a"
    assert parameters.invert is True
    assert parameters.output_columns == []


def test_loglevel_parser():
    parameters = filter_parser().parse_args(
        ["form", "-q", "-q", "a", "FormTable", "-v", "-V", "-q"]
    )
    # Optional positional argument ("FormTable") after optional switch ("-q",
    # but also "-V" which uses a builtin action) does not seem to work.
    assert parameters.loglevel == logging.ERROR

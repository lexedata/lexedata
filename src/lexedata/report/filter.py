"""Filter some table by some column.


Print the partial table to STDOUT or a file, so it can be used as subset-filter
for some other script, and output statistics (how many included, how many
excluded, what proportion, maybe sub-statistics for xxxReference columns, i.e.
by language or by conceptr) to STDERR.

For example, assume you want to filter your FormTable down to those forms that
start with a 'b', except for those forms from Fantastean varieties, which all
have a name containing 'Fantastean'. You can do this using two calls to this
program like this:

python -m lexedata.report.filter Form '^b' FormTable -c ID -c Language_ID |
  python -m lexedata.report.filter -V Language_ID 'Fantastean' -c ID

If you are aware of standard Unix tools, this script is a column-aware, but
otherwise vastly reduced implementation of `grep`.

"""

# TODO: Allow to filter concepts down to primary concepts, and then filter
# forms to those linked to primary concepts: i.e. allow the regex to be derived
# from a list of IDs elsewhere.

import argparse
import re
import sys
import typing as t
from csv import DictReader, DictWriter
from pathlib import Path

import pycldf

import lexedata.cli as cli

R = t.TypeVar("R", bound=t.Dict[str, t.Any])


def filter(
    table: t.Iterable[R],
    column: str,
    filter: re.Pattern,
    invert: bool = False,
    logger: cli.logging.Logger = cli.logger,
) -> t.Iterator[R]:
    """Return all rows matching a filter

    Match the filter regular expression and return all rows in the table where
    the filter matches the column. (Or all where it does not, if invert==True.)

    >>> list(filter([
    ...   {"C": "A"},
    ...   {"C": "An"},
    ...   {"C": "T"},
    ...   {"C": "E"},
    ... ], "C", re.compile("A"), invert=True))
    [{'C': 'T'}, {'C': 'E'}]

    """
    n_row = 0
    n_included = 0
    for row in table:
        n_row += 1
        # TODO: Treat list-valued columns better.
        string = str(row[column])
        row_matches = bool(filter.search(string))
        if row_matches ^ invert:
            n_included += 1
            yield row

    logger.info(
        "Filtered %d rows down to %d (%1.0f%%)",
        n_row,
        n_included,
        n_included / n_row * 100,
    )


def parser():
    parser = cli.parser(
        __package__ + "." + Path(__file__).stem,
        description=__doc__.split("\n\n\n")[0],
        epilog=__doc__.split("\n\n\n")[1],
    )
    parser.add_argument("column", help="The column to filter.", metavar="COLUMN")
    parser.add_argument("filter", help="An expression to filter by.", metavar="FILTER")
    parser.add_argument(
        "table",
        nargs="?",
        help="The table to filter. If you want to filter a CSV table from standard input, leave this argument out.",
        metavar="TABLE",
    )
    parser.add_argument(
        "--invert",
        "-V",
        action="store_true",
        default=False,
        help="Output exactly the NON-matching lines",
    )
    parser.add_argument(
        "--output-columns",
        "-c",
        nargs="+",
        default=[],
        help="Output only columns OUTPUT_COLUMN1,OUTPUT_COLUMN2,OUTPUT_COLUMN3,… in the same order as given.",
    )
    parser.add_argument(
        "--output-file",
        "-o",
        type=argparse.FileType("w"),
        default=sys.stdout,
        help="Write output to file OUTPUT_FILE, instead of to the console as stdout.",
    )

    return parser


if __name__ == "__main__":
    args = parser().parse_args()
    logger = cli.setup_logging(args)

    if not args.table:
        table = DictReader(sys.stdin)
        if not args.output_columns:
            args.output_columns = table.fieldnames
    else:
        table = pycldf.Wordlist.from_metadata(args.metadata)[args.table]

    try:
        w: t.Optional[DictWriter] = None
        for r, row in enumerate(
            filter(table, args.column, re.compile(args.filter), args.invert)
        ):
            if not args.output_columns:
                args.output_columns = row.keys()
            if w is None:
                w = DictWriter(args.output_file, args.output_columns)
                w.writeheader()
            row = {
                key: value for key, value in row.items() if key in args.output_columns
            }
            w.writerow(row)
    except KeyError:
        logger.critical("Column %s not found in table.", args.column)
        cli.Exit.INVALID_COLUMN_NAME()

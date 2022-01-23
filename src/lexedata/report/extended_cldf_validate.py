"""Validate a CLDF wordlist.


This script runs some more validators specific to CLDF Wordlist data sets in
addition to the validation implemented in the `pycldf` core. Some of those
tests are not yet mandated by the CLDF standard, but are assumptions which some
tools (including lexedata) tacitly make, so this validator makes them explicit.


TODO: There may be programmatic ways to fix the issues that this script
reports. Those automatic fixes should be made more obvious.

"""

import pycldf

# from clldutils.misc import log_or_raise

from lexedata import cli
from lexedata.report.judgements import check_cognate_table


def log_or_raise(message: str, log=None):
    logger.warning(message)


def check_segmentslice_separator(dataset: pycldf.Dataset, log=None) -> bool:
    if dataset["FormTable", "segments"].separator != " ":
        log_or_raise(
            'FormTable segment separator must be " " (space) for downstream lexedata tools to work.',
            log=log,
        )
        return False
    return True


def check_id_format(ds: pycldf.Dataset):
    correct = True
    for table in ds.tables:
        # Every table SHOULD have an ID column
        try:
            id_column = ds[table, "id"]
        except KeyError:
            logger.warning("Table %s has no identifier column.", table.url)
            correct = False
            continue

        # All IDs SHOULD be [a-zA-Z0-9_-]+
        datatype = id_column.datatype
        if datatype.base == "string":
            if not datatype.format:
                correct = False
                logger.warning(
                    "Table %s has an unconstrained ID column %s. Consider setting its format to [a-zA-Z0-9_-]+ and/or running `lexedata.edit.simplify_ids`.",
                    table.url,
                    id_column.name,
                )
            else:
                if datatype.format not in {
                    "[a-zA-Z0-9_\\-]+",
                    "[a-zA-Z0-9_-]+",
                    "[a-zA-Z0-9\\-_]+",
                    "[a-z0-9_]+",
                }:
                    logger.warning(
                        "Table %s has a string ID column %s with format %s. I am too dumb to check whether that's a subset of [a-zA-Z0-9_-]+ (which is fine) or not (in which case maybe change it).",
                        table.url,
                        id_column.name,
                        datatype.format,
                    )

        elif datatype.base == "integer":
            logger.info(
                "Table %s has integer ID column %s. This is okay, I hope I will not mess it up.",
                table.url,
                id_column.name,
            )

        # IDs should be primary keys and primary keys IDs (not official part of the CLDF specs)
        if table.tableSchema.primaryKey != [id_column.name]:
            logger.warning(
                "Table %s has ID column %s, but primary key %s",
                table.url,
                id_column.name,
                table.tableSchema.primaryKey,
            )
            correct = False

    return correct


if __name__ == "__main__":
    parser = cli.parser(
        description=__doc__.split("\n\n\n")[0], epilog=__doc__.split("\n\n\n")[1]
    )
    args = parser.parse_args()
    logger = cli.setup_logging(args)

    dataset = pycldf.Dataset.from_metadata(args.metadata)

    dataset.auto_constraints()

    # Assume the dataset is conform with CLDF until proven otherwise.
    correct = True

    # Run basic CLDF validate
    correct &= dataset.validate(log=logger)

    # All IDs should be [a-zA-Z0-9_-]+, and should be primary keys
    correct &= check_id_format(dataset)

    # Check reference properties/foreign keys

    # no ID of a reference that contains separators may contain that separator

    # Check segment slice separator is space
    correct &= check_segmentslice_separator(dataset)

    # Check that the CognateTable makes sense
    correct &= check_cognate_table(dataset)

    #  Empty forms may exist, but only if there is no actual form for the concept and the language, and probably given some other constraints.

    #  All files should be in NFC normalized unicode

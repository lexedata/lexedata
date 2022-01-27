"""Validate a CLDF wordlist.


This script runs some more validators specific to CLDF Wordlist data sets in
addition to the validation implemented in the `pycldf` core. Some of those
tests are not yet mandated by the CLDF standard, but are assumptions which some
tools (including lexedata) tacitly make, so this validator makes them explicit.


TODO: There may be programmatic ways to fix the issues that this script
reports. Those automatic fixes should be made more obvious.

"""

import pycldf
import unicodedata

# from clldutils.misc import log_or_raise

from lexedata import cli
from lexedata.report.judgements import check_cognate_table


def log_or_raise(message, log: cli.logger):
    log.warning(message)


def check_segmentslice_separator(dataset, logger=None) -> bool:
    if dataset["FormTable", "segments"].separator != " ":
        log_or_raise(
            'FormTable segment separator must be " " (space) for downstream lexedata tools to work.',
            log=logger,
        )
        return False
    return True


def check_id_format(ds: pycldf.Dataset):
    correct = True
    for table in dataset.tables:
        # Every table SHOULD have an ID column
        try:
            id_column = dataset[table, "id"]
        except KeyError:
            log_or_raise("Table %s has no identifier column.", logger)
            correct = False
            continue

        # All IDs SHOULD be [a-zA-Z0-9_-]+
        datatype = id_column.datatype
        if datatype.base == "string":
            if not datatype.format:
                correct = False
                log_or_raise(
                    f"Table {table.url} has an unconstrained ID column {id_column.name}. Consider setting "
                    f"its format to [a-zA-Z0-9_-]+ and/or running `lexedata.edit.simplify_ids`.",
                    logger,
                )
            else:
                if datatype.format not in {
                    "[a-zA-Z0-9_\\-]+",
                    "[a-zA-Z0-9_-]+",
                    "[a-zA-Z0-9\\-_]+",
                    "[a-z0-9_]+",
                }:
                    log_or_raise(
                        f"Table {table.url} has a string ID column {id_column.name} with format {datatype.format}. "
                        f"I am too dumb to check whether that's a subset of [a-zA-Z0-9_-]+ (which is fine) "
                        f"or not (in which case maybe change it).",
                        logger,
                    )

        elif datatype.base == "integer":
            logger.info(
                "Table %s has integer ID column %s. This is okay, I hope I will not mess it up.",
                table.url,
                id_column.name,
            )

        # IDs should be primary keys and primary keys IDs (not official part of the CLDF specs)
        if table.tableSchema.primaryKey != [id_column.name]:
            log_or_raise(
                f"Table {table.url} has ID column {id_column.name}, but primary key {table.tableSchema.primaryKey}",
                logger,
            )
            correct = False

    return correct


def check_no_separator_in_ids(dataset: pycldf.Dataset, logger=None) -> bool:
    # check that reference columns that have a separator don't contain the separator inside a string value
    for table in dataset.tables:
        for foreign_key in table.tableSchema.foreignKeys:
            original_column_name = foreign_key.reference.columnReference
            original_column = dataset[foreign_key.reference].get_column(
                original_column_name
            )
            if original_column.separator:
                separator = original_column.separator
                if separator in original_column.datatype.format:
                    continue
                for row in dataset[foreign_key.reference]:
                    try:
                        assert separator not in row[original_column_name]
                    except AssertionError:
                        log_or_raise(
                            message=f"Column {original_column_name} of table "
                            f"{foreign_key.reference.resource.__str__()} "
                            f"contains the separator {separator} of column {foreign_key.columnReference} from "
                            f"table {table.url} in value: {row[original_column_name]}",
                            log=logger,
                        )
                        return False
    return True


def check_unicode_data(dataset: pycldf, unicode_form: str = "NFC", logger=None):
    for table in dataset:
        id = dataset[table, "id"].name
        for row in table:
            for value in row.values():
                if isinstance(value, str):
                    if not unicodedata.is_normalized(unicode_form, value):
                        log_or_raise(
                            message=f"Value {value} of row {row[id]} in table {table.url} is not in "
                            f"{unicode_form} normalized unicode",
                            log=logger,
                        )
                        return False
    return True


def check_foreign_keys(dataset: pycldf.Dataset, logger=None):
    # get all foreign keys for each table
    f_keys = {}
    for table in dataset.tables:
        f_keys[table.url.string] = [
            (f.reference, f.columnReference) for f in table.tableSchema.foreignKeys
        ]

    for table, keys in f_keys.items():
        for key in keys:
            reference, column = key
            # check that foreign key is ID of corresponding table:
            try:
                assert reference.columnReference == "ID"
            except AssertionError:
                log_or_raise(
                    message=f"foreign key {key} in table {table.url.string} "
                    f"does not point to the ID column of another table",
                    log=logger,
                )
                return False
            # check that property url of foreign key column points to correct table
            property_url = (
                dataset[table]
                .get_column(column)
                .propertyUrl.split("#")[1]
                .rstrip("Reference")
            )
            referred_table_name = (
                dataset[reference]
                .common_props["dc:conformsTo"]
                .split("#")[1]
                .rstrip("Table")
            )
            try:
                assert property_url == referred_table_name.lower()
            except AssertionError:
                log_or_raise(
                    message=f"foreign key {key} is a declared as "
                    f"{dataset[table].get_column(column).propertyUrl.split('#')[1]} "
                    f"but does not point to this table, instead points to {referred_table_name}",
                    log=logger,
                )
    return True


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
    correct &= check_foreign_keys(dataset, logger=logger)

    # no ID of a reference that contains separators may contain that separator
    correct &= check_no_separator_in_ids(dataset=dataset, logger=logger)

    # Check segment slice separator is space
    correct &= check_segmentslice_separator(dataset=dataset, logger=logger)

    # Check that the CognateTable makes sense
    correct &= check_cognate_table(dataset=dataset, logger=logger)

    #  Empty forms may exist, but only if there is no actual form for the concept and the language, and probably given some other constraints.

    #  All files should be in NFC normalized unicode
    correct &= check_unicode_data(dataset, unicode_form="NFC", logger=logger)

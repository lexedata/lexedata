"""Validate a CLDF wordlist.


This script runs some more validators specific to CLDF Wordlist datasets in
addition to the validation implemented in the `pycldf` core. Some of those
tests are not yet mandated by the CLDF standard, but are assumptions which some
tools (including lexedata) tacitly make, so this validator makes them explicit.


TODO: There may be programmatic ways to fix the issues that this script
reports. Those automatic fixes should be made more obvious.

"""

import typing as t
import unicodedata
from pathlib import Path

import pycldf

from lexedata import cli, types, util
from lexedata.report.judgements import check_cognate_table

# from clldutils.misc import log_or_raise


def log_or_raise(message, log: cli.logging.Logger = cli.logger):
    log.warning(message)


def check_segmentslice_separator(dataset, logger=None) -> bool:
    if dataset["FormTable", "segments"].separator != " ":
        log_or_raise(
            'FormTable segment separator must be " " (space) for downstream lexedata tools to work.',
            log=logger,
        )
        return False
    return True


def check_id_format(dataset: pycldf.Dataset, logger: cli.logging.Logger = cli.logger):
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


def check_no_separator_in_ids(
    dataset: pycldf.Dataset, logger: cli.logger = cli.logger
) -> bool:
    valid = True
    # Check that reference columns that have a separator don't contain the separator inside a string value
    forbidden_separators: t.MutableMapping[
        str, t.MutableMapping[str, t.MutableMapping[str, t.List[t.Tuple[str, str]]]]
    ] = t.DefaultDict(lambda: t.DefaultDict(lambda: t.DefaultDict(list)))
    for table in dataset.tables:
        for foreign_key in table.tableSchema.foreignKeys:
            try:
                (referencing_column,) = foreign_key.columnReference
                (referenced_column,) = foreign_key.reference.columnReference
            except ValueError:
                # Multi-column foreign key. We *could* check that there's not a
                # reference column hidden in there, but we don't.
                continue

            if table.get_column(referencing_column).separator is None:
                continue

            forbidden_separators[foreign_key.reference.resource.__str__()][
                referenced_column
            ][table.get_column(referencing_column).separator].append(
                (table.url.string, referencing_column)
            )

    for table, targets in forbidden_separators.items():
        for r, row in enumerate(dataset[table], 1):
            for target_column, separators_forbidden_here in targets.items():
                for separator, forbidden_by in separators_forbidden_here.items():
                    if separator in row[target_column]:
                        log_or_raise(
                            f"In table {table}, row {r} column {target_column} contains {separator}, which is also the separator of {forbidden_by}.",
                            log=logger,
                        )
                        valid = False
    return valid


def check_unicode_data(
    dataset: pycldf.Dataset,
    unicode_form: str = "NFC",
    logger: cli.logging.Logger = cli.logger,
) -> bool:
    for table in dataset.tables:
        for r, row in enumerate(table, 1):
            for value in row.values():
                if isinstance(value, str):
                    if not unicodedata.is_normalized(unicode_form, value):
                        log_or_raise(
                            message=f"Value {value} of row {r} in table {table.url} is not in {unicode_form} normalized unicode",
                            log=logger,
                        )
                        return False
    return True


def check_foreign_keys(
    dataset: pycldf.Dataset, logger: cli.logging.Logger = cli.logger
):
    # Get all foreign keys for each table
    valid = True
    for table in dataset.tables:
        for key in table.tableSchema.foreignKeys:
            reference = key.reference
            try:
                (target_column,) = reference.columnReference
            except ValueError:
                # Multi-column foreign key. We *could* check that there's not a
                # reference column hidden in there, but we don't.
                continue
            (column,) = key.columnReference
            # check that property url of foreign key column points to correct table
            column_type = util.cldf_property(
                dataset[table].get_column(column).propertyUrl
            )

            if column_type and pycldf.TERMS[column_type].references:
                target_table = pycldf.TERMS[column_type].references
            else:
                # Not a CLDF reference property. Nothing to check.
                continue

            if dataset[target_table] != dataset[reference.resource]:
                log_or_raise(
                    message=f"Foreign key {key} is a declared as {column_type}, which should point to {target_table} but instead points to {reference}",
                    log=logger,
                )
                valid = False
                continue

            # Check that foreign key is ID of corresponding table
            if reference.columnReference != [
                dataset[key.reference.resource, "id"].name
            ]:
                log_or_raise(
                    message=f"Foreign key {key} in table {table.url.string} "
                    f"does not point to the ID column of another table",
                    log=logger,
                )
                valid = False

    return valid


def check_na_form_has_no_alternative(
    dataset: types.Wordlist[
        types.Language_ID,
        types.Form_ID,
        types.Parameter_ID,
        types.Cognate_ID,
        types.Cognateset_ID,
    ],
    logger: cli.logging.Logger = cli.logger,
):
    valid = True
    c_f_id = dataset["FormTable", "id"].name
    c_f_form = dataset["FormTable", "form"].name
    c_f_concept = dataset["FormTable", "parameterReference"].name
    c_f_language = dataset["FormTable", "languageReference"].name
    forms_by_concepts: t.Dict[types.Parameter_ID, t.Set[types.Form_ID]] = t.DefaultDict(
        set
    )

    for f in dataset["FormTable"]:
        for c in util.ensure_list(f[c_f_concept]):
            forms_by_concepts[c].add(f[c_f_id])
    forms_to_languages = t.DefaultDict(set)
    for f in dataset["FormTable"]:
        forms_to_languages[f[c_f_language]].add(f[c_f_id])
    na_forms = [f for f in dataset["FormTable"] if f[c_f_form] == "-"]
    for form in na_forms:
        for c in util.ensure_list(form[c_f_concept]):
            if forms_by_concepts[c].intersection(
                forms_to_languages[form[c_f_language]]
            ) != {form[c_f_id]}:
                log_or_raise(
                    message=f"Non empty forms exist for the NA form {form[c_f_id]} with identical parameter and language reference",
                    log=logger,
                )
                valid = False
    return valid


if __name__ == "__main__":
    parser = cli.parser(
        __package__ + "." + Path(__file__).stem,
        description=__doc__.split("\n\n\n")[0],
        epilog=__doc__.split("\n\n\n")[1],
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
    correct &= check_id_format(dataset, logger=logger)

    # Check reference properties/foreign keys
    correct &= check_foreign_keys(dataset, logger=logger)

    # no ID of a reference that contains separators may contain that separator
    correct &= check_no_separator_in_ids(dataset=dataset, logger=logger)

    #  All files should be in NFC normalized unicode
    correct &= check_unicode_data(dataset, unicode_form="NFC", logger=logger)

    if dataset.module == "Wordlist":
        # Check segment slice separator is space
        correct &= check_segmentslice_separator(dataset=dataset, logger=logger)

        # Check that the CognateTable makes sense
        correct &= check_cognate_table(dataset=dataset, logger=logger)

        # NA forms may exist, but only if there is no actual form for the
        # concept and the language, and probably given some other constraints.
        correct &= check_na_form_has_no_alternative(dataset=dataset, logger=logger)

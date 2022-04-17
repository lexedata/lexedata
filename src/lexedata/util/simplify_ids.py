import typing as t

import csvw.metadata
import pycldf

from lexedata import cli
from lexedata.util import ID_FORMAT, string_to_id
from lexedata import types
from lexedata.util import cache_table

ID_COMPONENTS: t.Mapping[str, t.Sequence[str]] = {
    "FormTable": ["languageReference", "parameterReference"]
}


def clean_mapping(rows: t.Mapping[str, t.Mapping[str, str]]) -> t.Mapping[str, str]:
    """Create unique normalized IDs.

    >>> clean_mapping({"A": {}, "B": {}})
    {'A': 'a', 'B': 'b'}

    >>> clean_mapping({"A": {}, "a": {}})
    {'A': 'a', 'a': 'a_x2'}
    """
    avoid = {id.lower() for id in rows}

    mapping: t.Dict[str, str] = {}
    for id, row in rows.items():
        i = 1
        if row:
            base = string_to_id("_".join(row.values()))
        else:
            base = string_to_id(id)

        if base in avoid and base not in mapping.values():
            # I kept a spot for you!
            mapping[id] = base
            continue

        # Make sure ID is unique
        tentative_mapping = base
        while tentative_mapping in avoid or tentative_mapping in mapping.values():
            i += 1
            tentative_mapping = "{:}_x{:}".format(base, i)
        mapping[id] = tentative_mapping

    return mapping


def update_integer_ids(
    ds: pycldf.Dataset,
    table: csvw.metadata.Table,
    logger: cli.logging.Logger = cli.logger,
):
    """Update all IDs of the table in the database, also in foreign keys."""
    c_id = table.get_column("http://cldf.clld.org/v1.0/terms.rdf#id")
    max_id = 0
    no_integer_rows: t.Set[str] = set()
    # logger.info("Checking IDs that are already integers…")
    for row in cli.tq(
        ds[table],
        task="Checking IDs that are already integers…",
        total=ds[table].common_props.get("dc:extent"),
    ):
        try:
            max_id = max(int(row[c_id.name]), max_id)
        except ValueError:
            no_integer_rows.add(row[c_id.name])
    logger.info("Adding integer IDs to other rows…")

    mapping: t.Dict[str, int] = dict()
    rows: t.List[t.Dict[str, t.Any]] = []
    for row in cli.tq(
        ds[table],
        task="Updating integer ids",
        total=ds[table].common_props.get("dc:extent"),
    ):
        original = row[c_id.name]
        if row[c_id.name] in no_integer_rows:
            max_id += 1
            row[c_id.name] = max_id
        else:
            row[c_id.name] = int(row[c_id.name])
        mapping[original] = row[c_id.name]
        rows.append(row)
    logger.info(f"Writing {table.url.string} back to file…")
    table.write(rows)

    foreign_keys_to_here = {
        other_table.url.string: {
            foreign_key.columnReference[
                foreign_key.reference.columnReference.index(c_id.name)
            ]
            for foreign_key in other_table.tableSchema.foreignKeys
            if foreign_key.reference.resource == table.url
            if c_id.name in foreign_key.reference.columnReference
        }
        for other_table in ds.tables
    }
    for other_table, columns in foreign_keys_to_here.items():
        if not columns:
            continue
        rows = []
        for row in cli.tq(
            ds[other_table],
            task=f"Applying changed foreign key to {other_table}…",
            total=ds[other_table].common_props.get("dc:extent"),
        ):
            for column in columns:
                # TODO: is this enough to handle columns with a separator? like parameterReference in forms table
                if isinstance(row[column], list):
                    row[column] = [mapping[v] for v in row[column]]
                else:
                    row[column] = mapping[row[column]]
            rows.append(row)

        for column in columns:
            ds[other_table, column].datatype = csvw.metadata.Datatype.fromvalue(
                {"base": "integer"}
            )
        logger.info(f"Writing {other_table} back to file…")

        ds[other_table].write(rows)


def update_ids(
    ds: pycldf.Dataset,
    table: csvw.metadata.Table,
    mapping: t.Mapping[str, str],
    logger: cli.logging.Logger = cli.logger,
):
    """Update all IDs of the table in the database, also in foreign keys, according to mapping."""
    c_id = table.get_column("http://cldf.clld.org/v1.0/terms.rdf#id")
    rows = []
    for row in cli.tq(
        ds[table],
        task=f"Updating ids of {table.url.string}",
        total=ds[table].common_props.get("dc:extent"),
    ):
        row[c_id.name] = mapping.get(row[c_id.name], row[c_id.name])
        rows.append(row)
    logger.info(f"Writing {table.url.string} back to file…")
    table.write(rows)

    c_id.datatype.format = ID_FORMAT.pattern

    foreign_keys_to_here = {
        other_table.url.string: {
            foreign_key.columnReference[
                foreign_key.reference.columnReference.index(c_id.name)
            ]
            for foreign_key in other_table.tableSchema.foreignKeys
            if foreign_key.reference.resource == table.url
            if c_id.name in foreign_key.reference.columnReference
        }
        for other_table in ds.tables
    }

    for other_table, columns in foreign_keys_to_here.items():
        if not columns:
            continue
        for column in columns:
            # Temporarily open up the datatype format, otherwise we may be unable to read.
            ds[other_table, column].datatype = csvw.metadata.Datatype.fromvalue(
                {"base": "string"}
            )
        logger.info(
            f"Applying changed foreign key to columns {columns:} in {other_table:}…"
        )
        rows = []
        for row in cli.tq(
            ds[other_table],
            total=ds[other_table].common_props.get("dc:extent"),
            task="Replacing changed IDs",
        ):
            for column in columns:
                # TODO: is this enough to handle columns with a separator? like parameterReference in forms table
                if isinstance(row[column], list):
                    row[column] = [mapping.get(v, v) for v in row[column]]
                else:
                    row[column] = mapping.get(row[column], row[column])
                rows.append(row)
        logger.info(f"Writing {other_table} back to file…")
        ds[other_table].write(rows)

        for column in columns:
            ds[other_table, column].datatype = c_id.datatype


def simplify_table_ids_and_references(
    ds: types.Wordlist[
        types.Language_ID,
        types.Form_ID,
        types.Parameter_ID,
        types.Cognate_ID,
        types.Cognateset_ID,
    ],
    table: csvw.Table,
    transparent: bool = True,
    logger: cli.logging.Logger = cli.logger,
) -> bool:
    """Simplify the IDs of the given table."""
    ttype = ds.get_tabletype(table)
    c_id = table.get_column("http://cldf.clld.org/v1.0/terms.rdf#id")
    if c_id.datatype.base == "string":
        # Temporarily open up the datatype format, otherwise we may be unable to read
        c_id.datatype.format = None
    elif c_id.datatype.base == "integer":
        # Temporarily open up the datatype format, otherwise we may be unable to read
        c_id.datatype = csvw.metadata.Datatype.fromvalue({"base": "string"})
        update_integer_ids(ds, table)
        c_id.datatype = csvw.metadata.Datatype.fromvalue({"base": "integer"})
        return True
    else:
        logger.warning(
            f"Table {table.uri} had an id column ({c_id.name}) that is neither integer nor string. I did not touch it."
        )
        return False

    if transparent and ttype in ID_COMPONENTS:
        cols = {prop: ds[ttype, prop].name for prop in ID_COMPONENTS[ttype]}
        mapping = clean_mapping(cache_table(ds, ttype, cols))
    else:
        mapping = clean_mapping(cache_table(ds, table.url.string, {}))

    update_ids(ds, table, mapping)
    return True

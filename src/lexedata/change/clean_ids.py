"""Clean up all ID columns in the datasat.

Take every ID column and convert it to either an integer-valued or a restricted-string-valued (only containing a-z, 0-9, or _) column, maintaining uniqueness of IDs, and keeping IDs as they are where they fit the format.

Optionally, create ‘transparent’ IDs, that is alphanumerical IDs which are derived from the characteristic columns of the corresponding table. For example, the ID of a FormTable would be derived from language and concept; for a CognatesetTable from the central concept if there is one.

"""

import typing as t

import pycldf

from lexedata import cli
from lexedata.util import ID_FORMAT, string_to_id


def transparent_form_mapping(forms: t.Iterable) -> t.Mapping[str, str]:
    """Create transparent form IDs."""
    avoid = {row.id.lower() for row in forms if ID_FORMAT.fullmatch(row.id.lower())}

    mapping = {}
    for form in forms:
        i = 1
        base = string_to_id("{:}_{:}".format(form.language, form.concept))

        if base in avoid and base not in mapping:
            # I kept a spot for you!
            mapping[form.id] = base
            continue

        # Make sure ID is unique
        tentative_mapping = base
        while tentative_mapping in avoid or tentative_mapping in mapping:
            i += 1
            tentative_mapping = "{:}_s{:}".format(base, i)
        mapping[form.id] = tentative_mapping

    return mapping


def clean_mapping(ids: t.Set[str]) -> t.Mapping[str, str]:
    """Create unique normalized IDs."""
    avoid = {id.lower() for id in ids}

    mapping = {}
    for id in ids:
        i = 1
        base = string_to_id(id)

        if base in avoid and base not in mapping:
            # I kept a spot for you!
            mapping[id] = base
            continue

        # Make sure ID is unique
        tentative_mapping = base
        while tentative_mapping in avoid or tentative_mapping in mapping:
            i += 1
            tentative_mapping = "{:}_s{:}".format(base, i)
        mapping[id] = tentative_mapping

    return mapping


transparent_mappings = {"FormTable": transparent_form_mapping}

if __name__ == "__main__":
    parser = cli.parser(__doc__)
    parser.add_argument(
        "--transparent",
        action="store_true",
        default=False,
        help="Generate transparent IDs.",
    )
    args = parser.parse_args()
    logger = cli.setup_logging(args)

    ds = pycldf.Wordlist.from_metadata(args.metadata)

    for table in ds.tables:
        ttype = ds.get_tabletype(table)
        c_id = table.get_column("http://cldf.clld.org/v1.0/terms.rdf#id")
        if c_id.datatype.base == "string":
            ...
        elif c_id.datatype.base == "integer":
            continue
        else:
            logger.warning(
                f"Table {table.uri} had an id column ({c_id.name}) that is neither integer nor string. I did not touch it."
            )
            continue

        c_id.datatype.format = ID_FORMAT.pattern

        if args.transparent and ttype in transparent_mappings:
            mapping = transparent_mappings[ttype](ds.objects(ttype))
        else:
            ids = {row[c_id.name] for row in ds[table]}
            mapping = clean_mapping(ids)

        foreign_keys_to_here = {
            (table, foreign_key)
            for table in ds.tables
            for foreign_key in table.tableSchema.foreignKeys
        }
        for table, column in foreign_keys_to_here:
            ...

            c_id.datatype = c_id.datatype

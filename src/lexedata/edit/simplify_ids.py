"""Clean up all ID columns in the dataset.

Take every ID column and convert it to either an integer-valued or a restricted-string-valued (only containing a-z, 0-9, or _) column, maintaining uniqueness of IDs, and keeping IDs as they are where they fit the format.

Optionally, create ‘transparent’ IDs, that is alphanumerical IDs which are derived from the characteristic columns of the corresponding table. For example, the ID of a FormTable would be derived from language and concept; for a CognatesetTable from the central concept if there is one.

"""
from pathlib import Path

import lexedata.cli as cli
import pycldf
from lexedata.util.simplify_ids import simplify_table_ids_and_references

if __name__ == "__main__":
    parser = cli.parser(__package__ + "." + Path(__file__).stem, __doc__)
    parser.add_argument(
        "--transparent",
        action="store_true",
        default=False,
        help="Generate transparent IDs.",
    )
    parser.add_argument(
        "--uppercase",
        action="store_true",
        default=False,
        help="Normalize to uppercase letters, instead of the default lowercase.",
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        help="Only fix the IDs of these tables.",
    )
    args = parser.parse_args()
    logger = cli.setup_logging(args)

    if args.uppercase:
        # TODO: implement this
        raise NotImplementedError

    ds = pycldf.Wordlist.from_metadata(args.metadata)

    if args.tables:
        tables = []
        for table in args.tables:
            try:
                tables.append(ds[table])
            except KeyError:
                cli.Exit.INVALID_TABLE_NAME(f"No table {table} in dataset.")
    else:
        tables = ds.tables

    for table in tables:
        logger.info(f"Handling table {table.url.string}…")
        simplify_table_ids_and_references(ds, table, args.transparent, logger)

    ds.write_metadata()

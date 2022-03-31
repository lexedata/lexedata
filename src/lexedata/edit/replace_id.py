from pathlib import Path

import pycldf

import lexedata.cli as cli
from lexedata.util.simplify_ids import update_ids

if __name__ == "__main__":
    parser = cli.parser(
        __package__ + "." + Path(__file__).stem,
        description="Replace the ID of an object (e.g. a language ID) in the wordlist",
    )
    parser.add_argument(
        "table", type=str, help="The table to apply the replacement to", metavar="TABLE"
    )
    parser.add_argument(
        "original", type=str, help="Original ID to be replaced", metavar="ORIGINAL"
    )
    parser.add_argument(
        "replacement", type=str, help="New ID of ORIGINAL", metavar="REPLACEMENT"
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        default=False,
        help="When the replacement would lead to two IDs being merged, warn, but proceed.",
    )
    args = parser.parse_args()
    logger = cli.setup_logging(args)

    dataset = pycldf.Dataset.from_metadata(args.metadata)
    id_column = dataset[args.table, "id"].name
    ids = {row[id_column] for row in dataset[args.table]}
    if args.original not in ids:
        logger.error(
            "The original ID %s is not an ID in %s.", args.original, args.table
        )
        cli.Exit.INVALID_ID()

    if args.replacement in ids:
        if args.merge:
            logger.info(
                "The replacement ID %s is already an ID in %s. I have been told to merge them.",
                args.replacement,
                args.table,
            )
        else:
            logger.error(
                "The replacement ID %s is already an ID in %s. If you want to force conflation of the two rows in tables that reference this one, use --merge.",
                args.replacement,
                args.table,
            )
            cli.Exit.INVALID_ID()

    update_ids(
        ds=dataset,
        table=dataset[args.table],
        mapping={args.original: args.replacement},
        logger=logger,
    )

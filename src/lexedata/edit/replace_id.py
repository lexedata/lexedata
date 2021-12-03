import pycldf

import lexedata.cli as cli
from lexedata.edit.simplify_ids import update_ids


if __name__ == "__main__":
    parser = cli.parser(
        description="Replace the ID of an object (e.g. a language ID) in the wordlist"
    )
    parser.add_argument("table", type=str, help="The table to apply the replacement to")
    parser.add_argument(
        "original", type=str, help="the original id"
    )
    parser.add_argument("replacement", type=str, help="the replacement id")
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
    if args.replacement in ids and not args.merge:
        logger.error(
            "The replacement ID {args.replacement} is already an ID in {args.table}. If you want to force conflation of the two IDs, use --merge."
        )
        cli.Exit.INVALID_ID()

    ids = dataset

    update_ids(
        ds=dataset,
        table=dataset[args.table],
        mapping={args.original: args.replacement},
        logger=logger,
    )

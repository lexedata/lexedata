from collections import defaultdict
from pathlib import Path

import pycldf

import lexedata.cli as cli
from lexedata.util.simplify_ids import string_to_id, update_ids

if __name__ == "__main__":
    parser = cli.parser(
        __package__ + "." + Path(__file__).stem,
        description="Replace the ID column of a table by some other column",
    )
    parser.add_argument(
        "table", type=str, help="The table to apply the replacement to", metavar="TABLE"
    )
    parser.add_argument(
        "replacement",
        type=str,
        help="Name of the replacement column",
        metavar="REPLACEMENT",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        default=False,
        help="When the replacement would lead to two IDs being merged, warn, but proceed.",
    )
    parser.add_argument(
        "--literally",
        action="store_true",
        default=False,
        help="Use the REPLACEMENT literally, instead of simplifying it. (Run lexedata.edit.simplify_ids if you change your mind later.)",
    )
    args = parser.parse_args()
    logger = cli.setup_logging(args)

    dataset = pycldf.Dataset.from_metadata(args.metadata)
    id_column = dataset[args.table, "id"].name
    new_id_column = dataset[args.table, args.replacement].name

    if args.literally:
        replacement = {
            row[id_column]: row[new_id_column] for row in dataset[args.table]
        }
    else:
        replacement = {
            row[id_column]: string_to_id(str(row[new_id_column]))
            for row in dataset[args.table]
        }

    if len(set(replacement.values())) < len(replacement) and not args.merge:
        flip = defaultdict(set)
        for id, new_id in replacement.items():
            flip[new_id].add(id)
        mergers = [k for k in flip.values() if len(k) > 1]
        logger.error(
            f"The replacement ID column {args.replacement} in {args.table} does not have unique values. "
            f"You are about to merge the following groups of IDs: {mergers}. "
            f"If you want to force conflation of them in tables that reference {args.table}, use --merge."
        )
        cli.Exit.INVALID_ID()

    update_ids(
        ds=dataset,
        table=dataset[args.table],
        mapping=replacement,
        logger=logger,
    )

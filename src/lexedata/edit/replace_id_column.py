import pycldf

import cli
from replace_id import replace_column


if __name__ == "__main__":
    parser = cli.parser(
        description="Replace the ID column of a table by some other column"
    )
    parser.add_argument("table", type=str, help="The table to apply the replacement to")
    parser.add_argument("replacement", type=str, help="Name of the replacement column")
    parser.add_argument(
        "--merge",
        action="store_true",
        default=False,
        help="When the replacement would lead to two IDs being merged, warn, but proceed.",
    )
    parser.add_argument(
        "--status-update",
        type=str,
        default="default",
        help="Text written to Status_Column. Set to 'None' for no status update. "
        "(default: Replaced column {original} by column {replacement}",
    )
    args = parser.parse_args()
    logger = cli.setup_logging(args)

    if args.status_update == "None":
        args.status_update = None
    if args.status_update == "default":
        args.status_update = (
            f"Replaced column {args.original} by column {args.replacement}"
        )

    replace_column(
        dataset=pycldf.Dataset.from_metadata(args.metadata),
        original=args.original,
        replacement=args.replacement,
        column_replace=True,
        smush=args.merge,
        status_update=args.status_update,
        logger=logger,
    )

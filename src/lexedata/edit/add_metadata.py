"""
Adds a metadata.json file automatically starting from a forms.csv file. Lexedata can guess metadata for a number of columns, including, but not limited to, all default CLDF properties (e.g. Language, Form) and CLDF reference properties (e.g. parameterReference). We recommend that you check the metadata file created and adjust if necessary.
"""

from pathlib import Path

from lexedata import cli
from lexedata.util.add_metadata import add_metadata

if __name__ == "__main__":
    parser = cli.parser(__package__ + "." + Path(__file__).stem, __doc__)
    parser.add_argument(
        "--keep-forms",
        action="store_true",
        default=False,
        help="Do not overwrite forms.csv to add new columns, even if that means forms.csv and the metadata do not correspond to each other.",
    )
    args = parser.parse_args()
    logger = cli.setup_logging(args)

    fname = Path("forms.csv")

    ds = add_metadata(fname)

    if args.metadata.exists():
        logger.critical("Metadata file %s already exists!", args.metadata)
        cli.Exit.CLI_ARGUMENT_ERROR()

    ds.write_metadata(args.metadata)

    # TODO: If we can get the need to re-write the FormTable out of the
    # metadata guesser, we can default to not re-writing it and warn if it
    # would be necessary.
    if not args.keep_forms:
        ds.write(FormTable=list(ds["FormTable"]))
        logger.info("FormTable re-written.")

    ds.validate(log=logger)

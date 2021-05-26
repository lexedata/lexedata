"""Make sure every string entry in every table of the dataset uses NFC unicode normalization.

Maybe this should be one of the extended checks, with automatic fixing option, instead?

This funtionality is, without error reporting, in the CLI of lexedata.util
"""

from pathlib import Path
import unicodedata

from lexedata import cli


def normalize(file, original_encoding="utf-8"):
    # TODO: If this ever takes more than a second, add a cli.tq progress bar
    content = file.open(encoding=original_encoding).read()
    file.open("w", encoding=original_encoding).write(unicodedata.normalize("NFC", content))


if __name__ == "__main__":
    parser = cli.parser(__doc__)
    parser.add_argument(
        "file",
        nargs="*",
        type=Path,
        help="The file(s) to re-encode. Default: All table files included by the metadata file, though not the sources.",
    )
    parser.add_argument("--from-encoding", default="utf-8", help="original encoding")
    args = parser.parse_args()
    logger = cli.setup_logging(args)
    if not args.file:
        # TODO: Check CLDF for how to properly get table URLs as path
        args.file = [Path(table.url.string) for table in args.metadata.tables]
    for file in args.file:
        logger.info(f"Normalizing {file}…")
        normalize(file)

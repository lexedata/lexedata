"""Normalize a dataset or file to NFC unicode normalization.


Make sure every string entry in every table of the dataset uses NFC unicode
normalization, or take a list of files that each gets normalized.
"""

import unicodedata
from pathlib import Path
from urllib.parse import urljoin

import pycldf

from lexedata import cli


def n(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def normalize(file, original_encoding="utf-8"):
    # TODO: If this ever takes more than a second, add a cli.tq progress bar
    content = file.open(encoding=original_encoding).read()
    file.open("w", encoding=original_encoding).write(n(content))


if __name__ == "__main__":
    parser = cli.parser(
        __package__ + "." + Path(__file__).stem, __doc__.split("\n\n\n")[1]
    )
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
        args.file = [
            # TODO: Check whether other places using table.url.string might
            # benefit from this construction – or whether they use something
            # better that we should use here. (Link objects, like table.url,
            # have a .resolve() method, but that method is inferior.)
            Path(urljoin(str(args.metadata.absolute()), table.url.string))
            for table in pycldf.Wordlist.from_metadata(args.metadata).tables
        ]
    for file in args.file:
        logger.info(f"Normalizing {file}…")
        normalize(file)

"""Starting with a forms.csv, add metadata for all columns we know about.
"""

from pathlib import Path

from lexedata import cli
from lexedata.util.add_metadata import add_metadata

if __name__ == "__main__":
    parser = cli.parser(__doc__)
    args = parser.parse_args()
    logger = cli.setup_logging(args)

    fname = Path("forms.csv")

    ds = add_metadata(fname)

    ds.write_metadata(args.metadata)

    ds.validate(log=logger)

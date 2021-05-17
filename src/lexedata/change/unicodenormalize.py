"""Make sure every string entry in every table of the dataset uses NFC unicode normalization.

Maybe this should be one of the extended checks, with automatic fixing option, instead?

This funtionality is, without error reporting, in the CLI of lexedata.util
"""

from pathlib import Path
import unicodedata

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Recode all data in NFC unicode normalization"
    )
    parser.add_argument("file", nargs="+", type=Path)
    args = parser.parse_args()
    for file in args.file:
        content = file.open().read()
        file.open("w").write(unicodedata.normalize("NFC", content))

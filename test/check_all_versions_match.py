"""Check that the version string is consistent.

Due to different flavours of metadata, the version string ends up in different
files, none of them can include it from elsewhere. This script checks all known
locations for the version string, lists them, and exits with an error code if
they don't all match.

"""

import sys
import json
import configparser
from pathlib import Path

if __name__ == "__main__":
    root = Path(__file__).absolute().parent.parent

    py = root / "setup.cfg"
    config = configparser.ConfigParser()
    config.read(py)
    py_version = config["metadata"]["version"]
    print(py, py_version)

    zenodo = root / ".zenodo.json"
    zenodo_version = json.load(zenodo.open())["version"]
    print(zenodo, zenodo_version)

    cff = root / "CITATION.cff"
    # Maybe use cffconvert to parse? Or at least YAML?
    _, cff_version = [r for r in cff.open() if r.startswith("version:")][0].split(" ")
    print(cff, cff_version.strip())

    # There is also CodeMeta (https://codemeta.github.io/), which is the
    # solution suggested by JOSS. https://elib.dlr.de/133084/1/1905.08674.pdf
    # suggests converting CFF automatically to CodeMeta.

    docs = root / "docs"
    sys.path.append(str(docs))
    from conf import release

    print(docs / "conf.py", release)

    if not (
        py_version.strip()
        == zenodo_version.strip()
        == cff_version.strip()
        == release.strip()
    ):
        sys.exit(1)

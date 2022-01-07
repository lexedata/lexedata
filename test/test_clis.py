import logging

import pytest

from lexedata import cli


def test_exit(caplog):
    with pytest.raises(SystemExit) as exit:
        with caplog.at_level(logging.ERROR):
            cli.Exit.INVALID_DATASET()
        assert "INVALID_DATASET" in caplog.text
    assert exit.value.code == 8

import sys
import logging
import argparse
import typing as t
from enum import IntEnum
from pathlib import Path

import tqdm

logger = logging.getLogger("lexedata")
logging.basicConfig(level=logging.INFO)


# TODO: Maybe we should have these in cli and consolidate them between
# different CLI scripts? Maybe we can even store the messages there, too, and
# have a unified critical exit interface that needs only the name of the script
# and the exit code and does everything?
class Exit(IntEnum):
    CLI_ARGUMENT_ERROR = 2
    NO_COGNATETABLE = 3
    NO_SEGMENTS = 4
    INVALID_ID = 5
    INVALID_COLUMN_NAME = 6
    INVALID_DATASET = 7

    def __call__(self, message: t.Optional[str] = None):
        if message is None:
            logger.critical(self.name)
        else:
            logger.critical(message)
        sys.exit(self)


def tq(iter, task, logger=logger, total: t.Optional[t.Union[int, float]] = None):
    if logger.getEffectiveLevel() >= logging.INFO:
        # print(task)
        logger.info(task)
        return tqdm.tqdm(iter, total=total)
    else:
        return iter


def add_log_controls(parser: argparse.ArgumentParser):
    logcontrol = parser.add_argument_group("Logging")
    logcontrol.add_argument("--loglevel", type=int, default=logging.INFO)
    logcontrol.add_argument(
        "-q", action="store_const", const=logging.WARNING, dest="loglevel"
    )
    logcontrol.add_argument(
        "-v", action="store_const", const=logging.DEBUG, dest="loglevel"
    )


def setup_logging(args: argparse.Namespace):
    logger.setLevel(args.loglevel)
    return logger


def parser(description: str, **kwargs) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description, **kwargs)
    parser.add_argument(
        "--metadata",
        type=Path,
        default="Wordlist-metadata.json",
        help="Path to the JSON metadata file describing the dataset (default: ./Wordlist-metadata.json)",
    )
    add_log_controls(parser)
    return parser

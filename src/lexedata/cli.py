import sys
import logging
import argparse
import typing as t
from enum import IntEnum
from pathlib import Path

import tqdm

logger = logging.getLogger("lexedata")
logging.basicConfig(level=logging.INFO)


class Exit(IntEnum):
    # TODO: Is there a good way to define, structure and unify these error
    # codes? Currently, we are testing a quite random property
    # (Exit.INVALID_DATASET throws SystemExit with code 8), with some system
    # here maybe testing would be worth it.
    CLI_ARGUMENT_ERROR = 2
    NO_COGNATETABLE = 3
    NO_SEGMENTS = 4
    INVALID_ID = 5
    INVALID_COLUMN_NAME = 6
    INVALID_TABLE_NAME = 7
    INVALID_DATASET = 8
    INVALID_INPUT = 9
    FILE_NOT_FOUND = 10

    def __call__(self, message: t.Optional[str] = None):
        if message is None:
            logger.critical(self.name)
        else:
            logger.critical(message)
        sys.exit(self)


def tq(iter, task, logger=logger, total: t.Optional[t.Union[int, float]] = None):
    if logger.getEffectiveLevel() <= logging.INFO:
        logger.info(task)
        return tqdm.tqdm(iter, total=total)
    else:
        return iter


class ChangeLoglevel(argparse.Action):
    def __init__(self, option_strings, dest, change, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, getattr(namespace, self.dest) + self.change)


def add_log_controls(parser: argparse.ArgumentParser):
    logcontrol = parser.add_argument_group("Logging")
    logcontrol.add_argument("--loglevel", type=int, default=logging.INFO)
    logcontrol.add_argument(
        "-q", action=ChangeLoglevel, change=10, const=logging.WARNING, dest="loglevel"
    )
    logcontrol.add_argument(
        "-v", action=ChangeLoglevel, change=-10, const=logging.DEBUG, dest="loglevel"
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

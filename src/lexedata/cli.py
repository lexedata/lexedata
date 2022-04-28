import argparse
import csv
import enum
import logging
import sys
import typing as t
from enum import IntEnum
from pathlib import Path

import tqdm

from lexedata import types

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
    def __init__(self, option_strings, dest, const, nargs=None, **kwargs):
        if nargs is not None:  # pragma: no cover
            raise ValueError("nargs not allowed")
        self.change = const
        super().__init__(option_strings, dest, nargs=0, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, getattr(namespace, self.dest) + self.change)


class SetOrFromFile(argparse.Action):
    def __init__(
        self,
        option_strings,
        dest,
        nargs="+",
        default=types.WorldSet(),
        help=None,
        autohelp=True,
        metavar=None,
        **kwargs,
    ):
        if nargs != "+":
            if (
                len(option_strings) == 1
                and nargs == "*"
                and not option_strings[0].startswith("-")
            ):
                # Mandatory argument, can be not given as default.
                pass
            else:
                raise ValueError(
                    "Optional SetOrFromFile makes sense only with variable argument count ('+')"
                )

        if metavar is None:
            metavar = option_strings[0].upper()
            if option_strings[0].endswith("s"):
                metavar = metavar[:-1]
            if option_strings[0].startswith("--"):
                metavar = metavar[2:]

        if autohelp:
            help = (
                (help or "")
                + f" Instead of a list of individual {metavar}s on the command line, this argument accepts also the path to a single {metavar}S.CSV file (with header row), containing the relevant IDs in the first column."
            )
            if type(default) == types.WorldSet:
                help += f" (default: All {metavar.lower()}s in the dataset)"
            help = help.strip()

        super().__init__(
            option_strings,
            dest,
            nargs=nargs,
            default=default,
            help=help,
            metavar=metavar,
            **kwargs,
        )

    def __call__(self, parser, namespace, values, option_string=None):
        # This coud be improved if we could defer this until the dataset has
        # been loaded; but that requires major changes to the action reading
        # --metadata.
        if len(values) == 0:
            # Keep default value
            return
        if len(values) == 1:
            path = Path(values[0])
            if path.exists():
                values = set()
                for c, concept in enumerate(csv.reader(path.open(encoding="utf-8"))):
                    first_column = concept[0]
                    if c == 0:
                        # header row
                        logger.info(
                            "Reading concept IDs from column with header %s",
                            first_column,
                        )
                    else:
                        values.add(first_column)
                setattr(namespace, self.dest, values)
                return
            logger.debug(
                "File %s not found, assuming you want a single %s",
                path,
                str(option_string).lstrip("-").rstrip("s"),
            )
            setattr(namespace, self.dest, values)
        else:
            setattr(namespace, self.dest, set(values))


def add_log_controls(parser: argparse.ArgumentParser):
    logcontrol = parser.add_argument_group("Logging")
    logcontrol.add_argument("--loglevel", type=int, default=logging.INFO)
    logcontrol.add_argument("-q", action=ChangeLoglevel, const=10, dest="loglevel")
    logcontrol.add_argument("-v", action=ChangeLoglevel, const=-10, dest="loglevel")


def setup_logging(args: argparse.Namespace):
    logger.setLevel(args.loglevel)
    return logger


def parser(name: str, description: str, **kwargs) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=description, prog=f"python -m {name}", **kwargs
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default="Wordlist-metadata.json",
        help="Path to the JSON metadata file describing the dataset (default: ./Wordlist-metadata.json)",
    )
    add_log_controls(parser)
    return parser


def enum_from_lower(enum: t.Type[enum.Enum]):
    class FromLower(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None, **kwargs):
            enum_item = {
                name.lower(): object for name, object in enum.__members__.items()
            }[values.lower()]
            setattr(namespace, self.dest, enum_item)

    return FromLower

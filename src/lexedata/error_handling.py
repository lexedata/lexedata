# -*- coding: utf-8 -*-
import logging
import typing as t


class ObjectNotFoundWarning(UserWarning):
    pass


class MultipleCandidatesWarning(UserWarning):
    pass


MissingHandler = t.Callable[[t.Dict[str, t.Any], t.Optional[str]], bool]

logger = logging.getLogger(__name__)


def error(db_object: t.Dict[str, t.Any], cell: t.Optional[str] = None) -> bool:
    """Should I add a missing object? No, the object missing is an error.

    Raise an exception (ObjectNotFoundWarning) reporting the missing object and cell.

    Raises
    ======
    ObjectNotFoundWarning

    """
    rep = db_object.get("cldf_name", db_object.get("cldf_id", repr(db_object)))
    raise ObjectNotFoundWarning(f"Failed to find object {rep:} {cell:} in the database")


def warn(db_object: t.Dict[str, t.Any], cell: t.Optional[str] = None) -> bool:
    """Should I add a missing object? No, but inform the user.

    Send a warning (ObjectNotFoundWarning) reporting the missing object and cell.

    Returns
    =======
    False: The object should not be added.

    """
    rep = db_object.get("cldf_name", db_object.get("cldf_id", repr(db_object)))
    logger.warning(
        f"Failed to find object {rep:} in the database. Skipped. In cell: {cell:}.",
        ObjectNotFoundWarning,
    )
    return False


def warn_and_create(
    db_object: t.Dict[str, t.Any], cell: t.Optional[str] = None
) -> bool:
    """Should I add a missing object? Yes, but inform the user.

    Send a warning (ObjectNotFoundWarning) reporting the missing object and
    cell, and give permission to add the object.

    Returns
    =======
    True: The object should be added.

    """
    rep = db_object.get("cldf_name", db_object.get("cldf_id", repr(db_object)))
    logger.warning(
        f"Failed to find object {rep:} in the database. Added. Object of cell: {cell:}",
        ObjectNotFoundWarning,
    )
    return True


def create(db_object: t.Dict[str, t.Any], cell: t.Optional[str] = None) -> bool:
    """Should I add a missing object? Yes, quietly.

    Give permission to add the object.

    Returns
    =======
    True: The object should be added.

    """
    return True


def ignore(db_object: t.Dict[str, t.Any], cell: t.Optional[str] = None) -> bool:
    """Should I add a missing object? No, drop it quietly.

    Returns
    =======
    False: The object should not be added.

    """
    return False

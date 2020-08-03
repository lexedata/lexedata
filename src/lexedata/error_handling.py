# -*- coding: utf-8 -*-
import typing as t

from lexedata.types import *


class Error(Exception):
    """Base class for other exceptions"""
    pass


class AlreadyExistsError(Error):

    def __init__(self, element):
        message = """The Element {} already exists in the table {}
         of the database""".format(element, element. __tablename__)
        self.message = message
        super().__init__(message)


# ------------------------------ Matching Errors ------------------------------
class MatchingError(Error):

    def __init__(self, cog, form, type="None"):
        message = "For {} \n {} match was found \n the match is {}".format(cog, type, form)
        self.message = message
        super().__init__(message)


class PartialMatchError(MatchingError):

    def __init__(self, cog, form, type="Partial"):
        super().__init__(cog, form, type)


class NoSourceMatchError(MatchingError):

    def __init__(self, cog, form, type="No source"):
        super().__init__(cog, form, type)


class MultipleMatchError(MatchingError):

    def __init__(self, cog, form, type="Multiple"):
        super().__init__(cog, form, type)


# ------------------------------ Cell Errors ------------------------------
class CellError(Error):
    """base class for formatting errors inside an element"""

    def __init__(self, values, type, cell):
        message = "In cell {} Value '{}' caused a {} error".format(cell, values, type)
        self.message = message
        super().__init__(message)


class SeparatorCellError(CellError):

    def __init__(self, values, cell):
        type = "Separator contained in form"
        super().__init__(values, type, cell)


class LanguageCellError(CellError):

    def __init__(self, values):
        type = "language"
        super().__init__(values, type, cell)


class FormCellError(CellError):
    # phonemic, phonetic usf.
    def __init__(self, values, type, cell):
        super().__init__(values, type, cell)


class CognateCellError(CellError):

    def __init__(self, values, cell):
        type = "cognate"
        super().__init__(values, type, cell)


class CellParsingError(CellError):

    def __init__(self, values, cell):
        type = "parsing (None can be a problem)"
        super().__init__(values, type, cell)


class IgnoreCellError(CellError):
    "special warning for ignored values"
    def __init__(self, values, cell):
        type = "IGNORE"
        super().__init__(values, type, cell)


class ObjectNotFoundWarning(UserWarning):
    pass


class MultipleCandidatesWarning(UserWarning):
    pass


MissingHandler = t.Callable[[t.Dict[str, t.Any], t.Optional[str]], bool]


def error(db_object: t.Dict[str, t.Any], cell: t.Optional[str] = None) -> bool:
    """Should I add a missing object? No, the object missing is an error.

    Raise an exception (ObjectNotFoundWarning) reporting the missing object and cell.

    Raises
    ======
    ObjectNotFoundWarning

    """
    rep = db_object.get("cldf_name", db_object.get("cldf_id", repr(db_object)))
    raise ObjectNotFoundWarning(
        f"Failed to find object {rep:} {cell:} in the database")


def warn(db_object: t.Dict[str, t.Any], cell: t.Optional[str] = None) -> bool:
    """Should I add a missing object? No, but inform the user.

    Send a warning (ObjectNotFoundWarning) reporting the missing object and cell.

    Returns
    =======
    False: The object should not be added.

    """
    rep = db_object.get("cldf_name", db_object.get("cldf_id", repr(db_object)))
    warnings.warn(
        f"Failed to find object {rep:} in the database. Skipped. In cell: {cell:}.",
        ObjectNotFoundWarning)
    return False


def warn_and_create(db_object: t.Dict[str, t.Any], cell: t.Optional[str] = None) -> bool:
    """Should I add a missing object? Yes, but inform the user.

    Send a warning (ObjectNotFoundWarning) reporting the missing object and
    cell, and give permission to add the object.

    Returns
    =======
    True: The object should be added.

    """
    rep = db_object.get("cldf_name", db_object.get("cldf_id", repr(db_object)))
    warnings.warn(
        f"Failed to find object {rep:}in the database. Added. Object of cell: {cell:}",
        ObjectNotFoundWarning)
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


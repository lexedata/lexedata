# -*- coding: utf-8 -*-


class Error(Exception):
    """Base class for other exceptions"""
    pass

class CellError(Error):
    """base class for formatting errors inside an element"""

    def __init__(self, values, type, cell):
        message = "In cell {} Value '{}' caused a {} error".format(cell, values, type)
        self.message = message
        super().__init__(message)


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
        type = "parsing"
        super().__init__(values, type, cell)


class IgnoreCellError(CellError):

    def __init__(self, values, cell):
        type = "IGNORE"
        super().__init__(values, type, cell)

if __name__ == "__main__":
    pass

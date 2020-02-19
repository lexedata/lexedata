# -*- coding: utf8 -*-


class Error(Exception):
    """Base class for other exceptions"""
    pass


class ConceptIdError(Error):
    """Something went wrong while creating the id of the concept"""
    pass


class LanguageElementError(Error):

    def __init__(self, language):
        message = "\n" + language[1] + " this language cell contains ???"
        self.message = message
        super().__init__(message) #desplay language name causing error


class CellParsingError(Error):

    def __init__(self, cell, comment=""):
        message = "\n" + comment + cell + "\n caused an error in the parser"
        self.message = message
        super().__init__(message)


class CellError(Error):
    """base class for formatting errors inside an element"""

    def __init__(self, coordinates, values, type):
        message = "in cell:{}\nvalues:\n{}caused a {} error".format(coordinates, values, type)
        self.message = message
        message = "\n" + message
        super().__init__(message)


class LanguageCellError(CellError):

    def __init__(self, coordinates, values, type="language"):

        super().__init__(coordinates, values, type)


class FormCellError(CellError):
    # phonemic, phonetic usf.
    def __init__(self, coordinates, values, type):
        super().__init__(coordinates, values, type)


class CognateCellError(CellError):

    def __init__(self, coordinates, values, type="cognate"):
        super().__init__(coordinates, values, type)


class CellParsingError(CellError):

    def __init__(self, coordinates, values, type="parsing"):
        super().__init__(coordinates, values, type)


if __name__ == "__main__":
    pass
# -*- coding: utf-8 -*-
import re

from .exceptions import *

class CellParser():
    """
    Iterator class over all form elements contained in a form cell
    """
    _wrongorder = [] #just for checking correct parsing

    #pattern for splitting form cell into various form elements
    __line_separator = re.compile(r"^(.+[\]\}\>\)/])\s*[,;]\s*([<{/[].+)$")
    # pattern for parsing content of cell
    __cell_value_pattern = re.compile(r"^(/.+?/)?\s?(\[.+?\])?\s?(<.+?>)?\s?(\(.+\))?\s?(\{.+\})?$")
    __special_pattern = [re.compile(e) for e in [r"^.*(/.+/).*$",
                                                r"^.*(\[.+?\]).*$",
                                                r"^.*(<.+?>).*$",
                                                r"^.*(\(.+\)).*$",
                                                r"^.*(\{.+?\}).*$"]
                       ]

    def __init__(self, cell):
        values = cell.value

        elements = CellParser.separator(values)

        if len(elements) == 0: #check that not empty
            raise CellParsingError(values)

        # clean elements list
        elements = [e.rstrip(" ").lstrip(" ") for e in elements]  # no tailing white spaces
        elements[-1] = elements[-1].rstrip("\n").rstrip(",").rstrip(";") #remove possible line break and ending commas

        self._elements = iter(elements)

    @staticmethod
    def separator(values):
        """
        splits a form cell into single form elements
        returns list of form strings
        """
        while CellParser.__line_separator.match(values):
            values = CellParser.__line_separator.sub(r"\1&&\2", values)
        return values.split("&&")

    @staticmethod
    def parsecell(ele, cellsize=5):
        """
        :param ele: is a form string; form string referring to a possibly (semicolon or)comma separated string of a form cell
        :return: list of cellsize containing parsed data of form string
        """
        mymatch = CellParser.__cell_value_pattern.match(ele)

        # check for match
        if mymatch:
            mymatch = list(mymatch.groups())  # tuple of all matches, None if empty
            return mymatch

        #check for exceptions
        else:
            if ele == "...":
                ele = ["No value"] * cellsize
                return ele

            elif len(ele) > 3: #cell not None nor ..., could be in wrong order
                ele= CellParser.wrong_order(ele, cellsize=cellsize)
                return ele

            else: #cell cannot be parsed
                raise CellParsingError(ele)

    @staticmethod
    def wrong_order(formele, cellsize=5):
        # checks if values of cells not in expected order, extract each value
        ele = (formele + ".")[:-1] #force python to hard copy string
        empty_cell = [None] * cellsize
        for i, pat in enumerate(CellParser.__special_pattern):
            mymatch = pat.match(ele)
            if mymatch:
                # delet match in cell
                empty_cell[i] = mymatch.group(1)
                ele = pat.sub("", ele)

        #check that ele was parsed entirely
        #add wrong ordered cell to error messag of CellParser
        #raise error
        ele = ele.strip(" ")
        if not ele == "":

            errmessage = formele +"\n" + str(empty_cell)
            CellParser._wrongorder.append(errmessage)
            raise CellParsingError(errmessage, comment="in wrong order: ")

        return empty_cell

    def __iter__(self):
        return self

    def __next__(self):
        ele = next(self._elements)
        return CellParser.parsecell(ele)

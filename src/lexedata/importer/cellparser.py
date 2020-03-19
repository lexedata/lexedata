# -*- coding: utf-8 -*-
import re

from exceptions import *


# functions for bracket checking
one_bracket = lambda opening, closing, str, nr: str[0] == opening and str[-1] == closing and \
                                                (str.count(opening) == str.count(closing) == nr)
comment_bracket = lambda str: str.count("(") == str.count(")")


class CellParser():
    """
    Iterator class over all form elements contained in a form cell
    """

    #pattern for splitting form cell into various form elements
    form_separator = re.compile(r"""(?<=[}\)>/\]])                # The end of an element of transcription, not consumed
    \s*                 # Any amount of spaces
    [,;]                # Some separator
    \s*               # Any amount of spaces
    (?=[</\[])        # Followed by the beginnig of any transcription, but don't consume that bit""", re.VERBOSE)

    _line_separator = re.compile(r"^(.+[}\]>)/])\s*[,;]\s*([<{/[].+)$")
    # pattern for parsing content of supposedly well formatted cell
    # /./ [.] <.> () {}
    _cell_value_pattern = re.compile(r"^(/.+?/)?\s?(\[.+?])?\s?(<.+?>)?\s?(\(.+\))?\s?({.+})?$")
    _special_pattern = [(re.compile(e), l) for e, l in [(r"^(.*?)(/.+/)(.*)$", "phonemic"),
                                                        (r"^(.*?)(\[.+?\])(.*)$", "phonetic"),
                                                        (r"^(.*?)(<.+?>)(.*)$", "orthographic"),
                                                        (r"^(.*?)(\(.+\))(.*)$", "comment"),
                                                        (r"^(.*?)(\{.+?\})(.*)$", "source")]
                       ]
    _cleaner = re.compile(r"^(.+)#.+?#(.*)$")

    def __init__(self, cell):
        values = cell.value
        self.coordinate = cell.coordinate
        self.set_elements(values)

    def set_elements(self, values):

        #remove #
        while self._cleaner.match(values):
            values = self._cleaner.sub(r"\1\2", values)
        elements = CellParser.separate(values)

        if len(elements) == 0: # check that not empty
            raise CellParsingError(values, self.coordinate)

        # clean elements list
        elements = [e.rstrip(" ").lstrip(" ") for e in elements]  # no tailing white spaces
        elements[-1] = elements[-1].rstrip("\n").rstrip(",").rstrip(";") # remove possible line break and ending commas

        self._elements = iter(elements)

    @classmethod
    def separate(cl, values):
        """Splits the content of a form cell into single form descriptions

        >>> CellParser.separate("<jaoca> (apartar-se, separar-se){2}")
        ['<jaoca> (apartar-se, separar-se){2}']
        >>> CellParser.separate("<eruguasu> (adj); <eniãcũpũ> (good-tasting (sweet honey, hard candy, chocolate candy, water){2}; <beyiruubu tuti> (tasty (re: meat with salt, honey, all good things)){2}; <eniacõ> (tasty (re: eggnog with flavoring)){2}; <eracũpũ> (tasty, good re: taste of honey, smell of flowers)){2}; <eribia tuti> (very tasty){2}; <ericute~ecute> (tasty, good (boiled foods)){2}; <eriya sui tuti> (very tasty, re: fermented fruit){2}; <erochĩpu> (good, tasty (re: tembe, pig meat)){2}; <ichẽẽ> (tasty (taste of roasted meat)){2}")[1]
        '<eniãcũpũ> (good-tasting (sweet honey, hard candy, chocolate candy, water){2}'

        Returns
        =======
        list of form strings
        """
        while cl._line_separator.match(values):
            values = cl._line_separator.sub(r"\1&&\2", values)
        return values.split("&&")

    @classmethod
    def parsecell(cls, ele, coordinates, cellsize=5):
        """
        :param ele: is a form string; form string referring to a possibly (semicolon or)comma separated string of a form cell
        :return: list of cellsize containing parsed data of form string
        """
        mymatch = cls._cell_value_pattern.match(ele)

        # check for match
        if mymatch:
            mymatch = list(mymatch.groups())  # tuple of all matches, None if empty

        # check for exceptions
        else:
            if ele == "...":
                mymatch = ["No value"] * cellsize

            elif len(ele) > 3: # cell not None nor ..., could be in wrong order
                mymatch = CellParser.wrong_order(ele, coordinates, cellsize=cellsize)

            else: # cell cannot be parsed
                raise CellParsingError(ele, coordinates)

        mymatch = [e or '' for e in mymatch]
        phonemic, phonetic, ortho, comment, source = mymatch

        variants = []
        phonemic = cls.variants_separator(variants, phonemic)
        phonetic = cls.variants_separator(variants, phonetic)
        ortho = cls.variants_separator(variants, ortho)
        variants = ",".join(variants)
        if phonemic != "" and phonemic != "No value":
            if not one_bracket("/", "/", phonemic, 2):
                raise FormCellError(phonemic, "phonemic", coordinates)
            # phonemic = phonemic.strip("/")

        if phonetic != "" and phonetic != "No value":
            if not one_bracket("[", "]", phonetic, 1):
                raise FormCellError(phonetic, "phonetic", coordinates)
            # phonetic = phonetic.strip("[").strip("]")

        if ortho != "" and ortho != "No value":
            if not one_bracket("<", ">", ortho, 1):
                raise FormCellError(ortho, "orthographic", coordinates)
            # ortho = ortho.strip("<").strip(">")

        if comment != "" and comment != "No value":
            if not comment_bracket(comment):
                raise FormCellError(comment, "comment", coordinates)

        return [phonemic, phonetic, ortho, comment, source, variants]

    @staticmethod
    def wrong_order(formele, coordinates, cellsize=5):
        """checks if values of cells not in expected order, extract each value"""
        ele = (formele + ".")[:-1] # force python to hard copy string
        d = {"phonemic": None, "phonetic": None, "orthographic": None, "comment": None, "source": None}
        for pat, lable in CellParser._special_pattern:

            mymatch = pat.match(ele)
            if mymatch:
                # delete match in cell
                d[lable] = mymatch.group(2)
                ele = pat.sub(r"\1\3", ele)
        # check that ele was parsed entirely
        # add wrong ordered cell to error message of CellParser
        # raise error
        ele = ele.strip(" ")
        if not ele == "":
            # if just text left and no comment given, put text in comment
            if not re.search(r"[<>/\[\]\{\}]", ele):

                if not d["comment"]:
                    d["comment"] = ( "(" + ele + ")")
                else:
                    d["comment"] = ("(" + d["comment"] + ele + ")")
            else:
                errmessage = "after parsing {}  -  {} was left unparsed".format(formele, ele)
                raise FormCellError(errmessage, "IncompleteParsingError; probably illegal content", coordinates)

        empty_cell = [d["phonemic"], d["phonetic"], d["orthographic"], d["comment"], d["source"]]
        return empty_cell

    def __iter__(self):
        return self

    def __next__(self):
        try:
            ele = next(self._elements)
            ele = CellParser.parsecell(ele, self.coordinate)
            return ele

        except CellParsingError as err:
            print("CellParsingError: " + err.message)
            # input()
            return self.__next__()

        except FormCellError as err:
            print(err)
            # input()
            return self.__next__()

        except IgnoreCellError as err:
            print(err)
            # input()
            return self.__next__()



    @staticmethod
    def variants_scanner(string):
        """copies string, inserting closing brackets if necessary"""
        is_open = False
        closers = {"<": ">", "[": "]", "/": "/"}
        collector = ""
        starter = ""

        for char in string:

            if char in closers and not is_open:
                collector += char
                is_open = True
                starter = char

            elif char == "~":
                if is_open:
                    collector += (closers[starter] + char + starter)
                else:
                    collector += char

            elif char in closers.values():
                collector += char
                is_open = False
                starter = ""

            elif is_open:
                collector += char

        return collector

    @classmethod
    def variants_separator(klasse, variants_list, string):

        if "~" in string:
            # force python to copy string
            text = (string + "&")[:-1]
            text = text.replace(" ", "")
            text = text.replace(",", "")
            text = text.replace(";", "")
            values = klasse.variants_scanner(text)

            values = values.split("~")
            first = values.pop(0)

            # add rest to variants prefixed with ~
            values = [("~" + e) for e in values]
            variants_list += values
            return first

        # inconsistent variants
        elif ("," not in string and ";" not in string) and \
                (string.count("[") >= 2 or string.count("<") >= 2 or string.count("/") > 3):
            string = string.replace(" ", "")
            string = string.replace("><", ">&&<")
            string = string.replace("][", "]&&[")
            string = string.replace("//", "/&&/")

            values = string.split("&&")
            first = values.pop(0)

            # add rest to variants prefixed with %
            values = [("%" + e) for e in values]
            variants_list += values
            return first
        else:
            return string


class CogCellParser(CellParser):

    def __init__(self, cell):
        values = cell.value
        self.coordinate = cell.coordinate

        if values.isupper():
            print(IgnoreCellError(values, self.coordinate))

        self.set_elements(values)


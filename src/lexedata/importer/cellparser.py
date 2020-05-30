# -*- coding: utf-8 -*-
import re
import typing as t
import unicodedata
from typing import Tuple, Optional, Pattern, List, Dict

import openpyxl

from lexedata.importer.exceptions import *
from lexedata.database.database import string_to_id
from lexedata.cldf.automapped import Form

# functions for bracket checking, becoming obsolete with new cellparser
comment_bracket = lambda str: str.count("(") == str.count(")")

# TODO: ask Gereon about escaping
comment_escapes = re.compile(r"&[</\[{].+?(?:\s|.$)")

phonemic_pattern = re.compile(r"""
(?:^| # start of the line or
  (.*?(?<=[^&]))) #capture anything before phonemic, phonemic must not follow a &, i.e. & escapes
  (/[^/]+? #first phonemic element, not greedy,
           # special for phonemic: use [^/] instead of . to ensure correct escaping
  (?<=[^&])/  # applies only to phonemic: closer must not follow &, otherwise &/a/ texttext &/b/ will render / texttext &/
  (?:\s*[~%]\s*/[^/]+?/)*  #non capturing pattern for any repetition of [%~]/..../
)  #capture whole group
(.*)$ #capture the rest""", re.VERBOSE)
phonetic_pattern = re.compile(r"(?:^|(.*?(?<=[^&])))(\[.+?](?:\s*[~%]\s*\[.+?])*)(.*)$")
ortho_pattern = re.compile(r"(?:^|(.*?(?<=[^&])))(<.+?>(?:\s*[~%]\s*<.+?>)*)(.*)$")

source_pattern = re.compile(r"(?:^|(.*?(?<=[^&])))({.+?})(.*)$")  # just one source per form, must not be empty

my_form_pattern = {"phonemic": phonemic_pattern,
                   "phonetic": phonetic_pattern,
                   "orthographic": ortho_pattern,
                   "source": source_pattern}


class AbstractCellParser():
    def parse(self, cell: openpyxl.cell.Cell, **known) -> t.Iterable[Form]:
        raise NotImplementedError

class CellParser(AbstractCellParser):
    illegal_symbols_description = re.compile(r"[</[{]")
    illegal_symbols_transcription = re.compile(r"[;]")
    form_pattern = my_form_pattern
    description_pattern = re.compile(r"^(.*?)(\(.+\))(.*)$")
    separator_pattern = re.compile(r"""
                 (?<=[}\)>/\]])    # The end of an element of transcription, not consumed
                 \s*               # Any amount of spaces
                 [,;]              # Some separator
                 \s*               # Any amount of spaces
                 (?=[</\[])        # Followed by the beginning of any transcription, but don't consume that bit""",
                                    re.VERBOSE)
    ignore_pattern = re.compile(r"^(.+)#.+?#(.*)$")  # anything between # # is replaced by an empty string

    def __init__(
            self,
            illegal_symbols_description: Optional[Pattern] = None,
            illegal_symbols_transcription: Optional[Pattern] = None,
            form_pattern: Optional[Dict[str, Pattern]] = None,
            description_pattern: Optional[Pattern] = None,
            separator_pattern: Optional[Pattern] = None,
            ignore_pattern: Optional[Pattern] = None):
        if separator_pattern is not None:
            self.separator_pattern = separator_pattern
        if illegal_symbols_description is not None:
            self.illegal_symbols_description = illegal_symbols_description
        if illegal_symbols_transcription is not None:
            self.illegal_symbols_transcription = illegal_symbols_transcription
        if form_pattern is not None:
            self.form_pattern = form_pattern
        if description_pattern is not None:
            self.description_pattern = description_pattern
        if ignore_pattern is not None:
            self.ignore_pattern = ignore_pattern

    def separate(self, values):
        values = unicodedata.normalize('NFKC', values)
        if self.separator_pattern:
            elements = self.separator_pattern.split(values)
            # clean elements list
            elements = [e.strip() for e in elements]  # no tailing white spaces
            # remove possible line break and ending commas
            elements[-1] = elements[-1].rstrip("\n").rstrip(",").rstrip(";")
            return elements
        else:
            return values

    @classmethod
    def bracket_checker(cls, opening, closing, string):
        assert len(opening) == len(closing) == 1, "Can only check single-character bracketing"
        b = 0
        for c in string:
            if c == opening:
                b += 1
            if c == closing:
                b -= 1
            if b < 0:
                return False
        return b == 0

    def parse_value(self, values, coordinate):
        raise NotImplementedError

    def source_from_source_string(
            self,
            source_string: str,
            language):
        context: t.Optional[str]
        if ":" in source_string:
            source_string, context = source_string.split(":", maxsplit=1)
            assert context.endswith("}")
            source_string += "}"
            context = context[:-1].strip()
        else:
            context = None

        if language is None:
            source_id = string_to_id(source_string)
        else:
            source_id = string_to_id(f"{language.cldf_id:}_s{source_string}")

        return source_id, context

    def parse(self, cell: openpyxl.cell.Cell, **known):
        if not cell.value:
            return None
        lan = known["language"]
        # replace ignore pattern with empty string
        values = cell.value
        while self.ignore_pattern.match(values):
            values = self.ignore_pattern.sub(r"\1\2", values)

        values = self.separate(cell.value)
        for element in values:
            try:
                element = self.parse_value(element, cell.coordinate)
                # assert no empty element
                if all(ele == "" for ele in element):
                    raise CellParsingError("empty values ''", self.coordinate)

                phonemic, phonetic, ortho, comment, source, variants = element

                # Source number {1} is not always specified
                if not source or not source.strip():
                    source = "{1}"

                source, context = self.source_from_source_string(source, lan)

                yield {
                    "language": lan,
                    "cldf_form": phonemic or "-",
                    # "cldf_segments": phonetic or "-",
                    # "orthographic": ortho,
                    # "variants": variants,
                    "cldf_comment": None if comment is None else comment.strip(),
                    "sources": [(source, context)],
                    # "procedural_comment": self.get_cell_comment(form_cell).strip(),
                    "cldf_value": string_to_id(f"{phonemic:}{phonetic:}{ortho:}")
                }


            # error handling
            except CellParsingError as err:
                print("CellParsingError: " + err.message)
                # input()
                continue

            except FormCellError as err:
                print(err)
                # input()
                continue

            except IgnoreCellError as err:
                print(err)
                # input()
                continue

            except SeparatorCellError as err:
                print(err)
                # input()
                continue


class CellParserLexical(CellParser):
    def parse_value(self, ele, coordinates):
        """
        :param ele: is a form string; form string referring to a possibly (semicolon or)comma separated string of a form cell
        :return: list of cellsize containing parsed data of form string
        """
        if ele == "...":
            return [None] * 6

        else:
            mymatch = self.parse_form(ele, coordinates)

        mymatch = [e or '' for e in mymatch]
        phonemic, phonetic, ortho, description, source = mymatch

        variants = []
        if phonemic:
            phonemic = self.variants_separator(variants, phonemic, coordinates)
        if phonetic:
            phonetic = self.variants_separator(variants, phonetic, coordinates)
        if ortho:
            ortho = self.variants_separator(variants, ortho, coordinates)
        variants = ",".join(variants)

        if phonemic == phonetic == ortho == "":
            ele_dummy = (ele + " ")[:-1]
            while " " in ele_dummy:
                ele_dummy = ele.replace(" ", "")
            if not ele_dummy:
                raise IgnoreCellError("Empty Excel Cell", coordinates)
            else:
                errmessage = """IncompleteParsingError; this excel cell rendered an empty form after parsing\n
                                {}""".format(ele)
                raise CellParsingError(errmessage, coordinates)

        if description:
            if not self.bracket_checker("(", ")", description):
                raise FormCellError(description, "description", coordinates)

        return [phonemic, phonetic, ortho, description, source, variants]

    def parse_form(self, formele, coordinates):
        """checks if values of cells not in expected order, extract each value"""
        ele = (formele + ".")[:-1]  # force python to hard copy string
        # parse transcriptions and fill dictionary d
        d = dict()
        for lable, pat in self.form_pattern.items():
            mymatch = pat.match(ele)
            if mymatch:
                # delete match in cell
                d[lable] = mymatch.group(2)
                ele = pat.sub(r"\1\3", ele)
            else:
                d[lable] = None

        mydescription = ""
        # get all that is left of the string in () and add it to the comment
        while self.description_pattern.match(ele):
            description_candidate = self.description_pattern.match(ele).group(2)
            # no transcription symbols in comment
            if not self.illegal_symbols_description.search(description_candidate):
                mydescription += description_candidate
                ele = self.description_pattern.sub(r"\1\3", ele)
            else:  # check if comment is escaped correctly, if not, raise error

                # replace escaped elements and check for illegal content, if all good, add original_form
                escapes = comment_escapes.findall(description_candidate)
                original_form = description_candidate
                for e in escapes:
                    description_candidate = description_candidate.replace(e, "")
                if not self.illegal_symbols_description.search(description_candidate):
                    mydescription += original_form
                    ele = self.description_pattern.sub(r"\1\3", ele)
                else:  # illegal comment
                    raise FormCellError(description_candidate, "description", coordinates)

        # check that ele was parsed entirely, if not raise parsing error
        ele = ele.strip(" ")
        if not ele == "":
            # if just text left and no comment given, put text in comment
            # more than one token
            if len(ele) >= 1 and (not self.illegal_symbols_description.search(ele)):

                if not mydescription:
                    mydescription = ele
                else:
                    mydescription += ele

            else:
                errmessage = """IncompleteParsingError; probably illegal content\n
                after parsing {}  -  {} was left unparsed""".format(formele, ele)
                raise CellParsingError(errmessage, coordinates)

        # enclose comment if not properly enclosed
        if not self.bracket_checker("(", ")", mydescription):
            mydescription = "(" + mydescription + ")"
        d["description"] = mydescription
        form_cell = [d["phonemic"], d["phonetic"], d["orthographic"], d["description"], d["source"]]
        return form_cell

    @staticmethod
    def variants_scanner(string, symbol):
        """copies string, inserting closing brackets after symbol if necessary"""
        is_open = False
        closers = {"<": ">", "[": "]", "/": "/"}
        collector = ""
        starter = ""

        for char in string:

            if char in closers and not is_open:
                collector += char
                is_open = True
                starter = char

            elif char == symbol:
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

    def variants_separator(self, variants_list, string, coordinate):
        if self.illegal_symbols_transcription.search(string):
            raise SeparatorCellError(string, coordinate)
        # force python to copy string
        text = (string + "&")[:-1]
        while " " in text:
            text = text.replace(" ", "")
        if "~" in string:
            values = self.variants_scanner(text, "~")
            values = values.split("~")
            first = values.pop(0)

            # add rest to variants prefixed with ~
            values = [("~" + e) for e in values]
            variants_list += values
            return first

        # inconsistent variants
        elif "%" in string:
            values = self.variants_scanner(text, "%")
            values = values.split("%")
            first = values.pop(0)

            # add rest to variants prefixed with ~
            values = [("%" + e) for e in values]
            variants_list += values
            return first
        else:
            return string


class CellParserCognate(CellParserLexical):
    def parse_value(self, values, coordinate):
        if values.isupper():
            raise IgnoreCellError(values, coordinate)
        else:
            return super().parse_value(values, coordinate)

class CellParserHyperlink(CellParser):
    def parse(self, cell: openpyxl.cell.Cell, **known) -> t.Iterable[Form]:
        url = cell.hyperlink.target
        yield {"cldf_id": url.split("/")[-1]}

# -*- coding: utf-8 -*-
import re
import typing as t
import unicodedata
from typing import Tuple, Optional, Pattern, List, Dict

import openpyxl

from lexedata.importer.exceptions import *
from lexedata.database.database import string_to_id
from lexedata.cldf.automapped import Form


def get_cell_comment(cell: openpyxl.cell.Cell) -> t.Optional[str]:
    return cell.comment.content.strip() if cell.comment else None


class AbstractCellParser():

    def __init__(
            self,
            separator_pattern: Optional[Pattern] = None,
            ignore_pattern: Optional[Pattern] = None):

        if separator_pattern is not None:
            self.separator_pattern = separator_pattern
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

    def parse_value(self, values, coordinate, language=None):
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

    # def parse(self, cell: openpyxl.cell.Cell, **known) -> t.Iterable[Form]:
    def parse(self, cell, language=None):
        if not cell.value:
            return None
        coordinate = cell.coordinate
        values = cell.value
        # replace ignore pattern with empty string
        while self.ignore_pattern.match(values):
            values = self.ignore_pattern.sub(r"\1\2", values)

        values = self.separate(values)
        for element in values:
            try:
                parsed_dict = self.parse_value(element, coordinate, language)
                # replace None
                for k, v in parsed_dict.items():
                    if v is None:
                        parsed_dict[k] = ""
                yield parsed_dict

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


class CellParser(AbstractCellParser):

    def __init__(
            self,
            form_pattern: Optional[Dict[str, Pattern]] = None,
            description_pattern: Optional[Pattern] = None,
            separator_pattern: Optional[Pattern] = None,
            ignore_pattern: Optional[Pattern] = None,
            illegal_symbols_description: Optional[Pattern] = None,
            illegal_symbols_transcription: Optional[Pattern] = None,
            comment_escapes: Optional[Pattern] = None
            ):

        if illegal_symbols_description is not None:
            self.illegal_symbols_description = illegal_symbols_description
        if illegal_symbols_transcription is not None:
            self.illegal_symbols_transcription = illegal_symbols_transcription
        if form_pattern is not None:
            self.form_pattern = form_pattern
        if description_pattern is not None:
            self.description_pattern = description_pattern
        if comment_escapes is not None:
            self.comment_escapes = comment_escapes
        super().__init__(separator_pattern=separator_pattern, ignore_pattern=ignore_pattern)

    def parse_value(
            self, ele: str, coordinate: str,
            language: t.Optional[str] = None) -> t.Dict[str, t.Any]:
        """Create a dictionary of columns from a form description.

        Extract each value (transcriptions, comments, sources etc.) from a
        string describing a single form.

        >>> c = CellParser()
        >>> c.parse_value(" \t")
        Traceback (most recent call last):
        ...
        IgnoreCellError: n must be exact integer

        """
        # if values is only whitespaces, raise IgnoreError
        if not ele.strip():
            raise IgnoreCellError(ele, coordinate)

        # parse transcriptions and fill dictionary d
        d = {}
        for label, pat in self.form_pattern.items():
            mymatch = pat.match(ele)
            if mymatch:
                # delete match in cell
                d[label] = mymatch.group(2)
                ele = pat.sub(r"\1\3", ele)
            else:
                d[label] = None

        # check for illegal symbols in transcriptions (i.e. form-pattern)
        if self.illegal_symbols_transcription:
            for k, string in d.items():
                if k != "source" and string is not None and self.illegal_symbols_transcription.search(string):
                    raise SeparatorCellError(string, coordinate)
        # if description pattern, add description to output
        if self.description_pattern:
            description = self.extract_description(ele, coordinate)
            d["description"] = description
        return d

    def extract_description(self, text, coordinate):
        description = ""
        # get all that is left of the string according to description pattern
        while self.description_pattern.match(text):
            description_candidate = self.description_pattern.match(text).group(2)

            # no illegal symbols in description pattern given, just replace extracted part
            if self.illegal_symbols_description:
                # check for illegal symbols in description
                if not self.illegal_symbols_description.search(description_candidate):
                    description += description_candidate
                    text = self.description_pattern.sub(r"\1\3", text)
                # check if comment is escaped correctly, if not, raise error
                else:
                    if self.comment_escapes:
                        # replace escaped elements and check for illegal content, if all good, add original_form
                        escapes = comment_escapes.findall(description_candidate)
                        original_form = description_candidate
                        for e in escapes:
                            description_candidate = description_candidate.replace(e, "")
                        if not self.illegal_symbols_description.search(description_candidate):
                            description += original_form
                            text = self.description_pattern.sub(r"\1\3", text)
                        # incorrect escaping and illegal symbol in description
                        else:
                            raise FormCellError(description_candidate, "description (illegal content)", coordinate)
                    # no escape and illegal symbol in description
                    else:
                        raise FormCellError(description_candidate, "description (illegal content)", coordinate)

            else:
                text = self.description_pattern.sub(r"\1\3", text)

        # check that ele was parsed entirely, if not raise parsing error
        text = text.strip(" ")
        if not text == "":
            # if just text left and no comment given, put text in comment
            # more than one token
            if len(text) >= 1 and (not self.illegal_symbols_description.search(text)):

                if not description:
                    description = text
                else:
                    description += text

            else:
                errmessage = """IncompleteParsingError; probably illegal content\n
                           after parsing {}  -  {} was left unparsed""".format(coordinate, text)
                raise CellParsingError(errmessage, coordinate)

        # TODO: opening and closing of bracket_checker is hard coded
        # enclose comment if not properly enclosed
        if not self.bracket_checker("(", ")", description):
            description = "(" + description + ")"
            if not self.bracket_checker("(", ")", description):
                raise FormCellError(description, "description (closing and opening brackets don't match",
                                          coordinate)

        return description


class CellParserLexical(CellParser):

    def __init__(
            self,
            form_pattern: Dict[str, Pattern]=None,
            description_pattern: Optional[Pattern] = None,
            separator_pattern: Optional[Pattern] = None,
            ignore_pattern: Optional[Pattern] = None,
            illegal_symbols_description: Optional[Pattern] = None,
            illegal_symbols_transcription: Optional[Pattern] = None,
            comment_escapes: Optional[Pattern] = None,
            add_default_source: str = "",
            scan_for_variants: bool = False
    ):
        self.scan_for_variants = scan_for_variants
        self.add_default_source = add_default_source
        super().__init__(form_pattern=form_pattern,
                         description_pattern=description_pattern,
                         separator_pattern=separator_pattern,
                         ignore_pattern=ignore_pattern,
                         illegal_symbols_description=illegal_symbols_description,
                         illegal_symbols_transcription=illegal_symbols_transcription,
                         comment_escapes=comment_escapes)

    def parse_value(self, values, coordinate, language=None):
        dictionary = super().parse_value(values, coordinate)

        if self.add_default_source and dictionary["source"] is None:
            dictionary["source"] = self.add_default_source

        if self.scan_for_variants:
            variants = []
            for k, v in dictionary.items():
                if k != "source" and v is not None:
                    dictionary[k] = self.variants_separator(variants, v)

            variants = ",".join(variants)
            dictionary["variants"] = variants

        return dictionary

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

    def variants_separator(self, variants_list, string):
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


class MawetiGuaraniLexicalParser(CellParserLexical):
    def __init__(
            self,
            form_pattern=my_form_pattern,
            description_pattern=re.compile(r"^(.*?)(\(.+\))(.*)$"),
            separator_pattern=re.compile(r"""
                 (?<=[}\)>/\]])    # The end of an element of transcription, not consumed
                 \s*               # Any amount of spaces
                 [,;]              # Some separator
                 \s*               # Any amount of spaces
                 (?=[</\[])        # Followed by the beginning of any transcription, but don't consume that bit""",
                                    re.VERBOSE),
            ignore_pattern=re.compile(r"^(.+)#.+?#(.*)$"),  # anything between # # is replaced by an empty string,
            illegal_symbols_description=re.compile(r"[</[{]"),
            illegal_symbols_transcription=re.compile(r"[;]"),
            comment_escapes=re.compile(r"&[</\[{].+?(?:\s|.$)"),
            add_default_source="{1}",
            scan_for_variants=True
    ):
        super().__init__(form_pattern=form_pattern,
                         description_pattern=description_pattern,
                         separator_pattern=separator_pattern,
                         ignore_pattern=ignore_pattern,
                         illegal_symbols_description=illegal_symbols_description,
                         illegal_symbols_transcription=illegal_symbols_transcription,
                         comment_escapes=comment_escapes,
                         add_default_source=add_default_source,
                         scan_for_variants=scan_for_variants)

    def parse_value(self, values, coordinate, language=None):
        dictionary = super().parse_value(values, coordinate)
        # Add metadata. TODO: Why not in super??
        dictionary["language"] = language
        cldf_value = f"{dictionary['phonemic'] or '-'}_{dictionary['phonetic'] or '-'}_{dictionary['orthographic'] or '-'}"
        dictionary["cldf_value"] = cldf_value

        # Rename some keys
        dictionary["cldf_form"] = dictionary.pop("phonemic", None)
        dictionary["cldf_comment"] = dictionary.pop("description", None)

        # Further transformations
        dictionary["cldf_segments"] = dictionary.pop("phonetic", None)
        # TODO: wrap in CLTS to check. Fall back on other transcriptions??

        source = dictionary.pop("source")  # TODO: Rename upstairs to sources
        if language:
            source, context = self.source_from_source_string(source, language)
            dictionary["sources"] = [(source, context)]

        return dictionary


class MawetiGuaraniCognateParser(MawetiGuaraniLexicalParser):
    def parse_value(self, values, coordinate, language=None):
        if values.isupper():
            raise IgnoreCellError(values, coordinate)
        else:
            return super().parse_value(values, coordinate, language)


class CellParserHyperlink(CellParser):
    def parse(self, cell: openpyxl.cell.Cell, **known) -> t.Iterable[Form]:
        try:
            url = cell.hyperlink.target
            yield {"cldf_id": url.split("/")[-1]}
        except AttributeError:
            pass

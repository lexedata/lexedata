# -*- coding: utf-8 -*-
import pytest

from lexedata.importer.cellparser import NaiveCellParser as AbstractCellParser
from lexedata.error_handling import *


def test_cellparser_error():
    cellparser = AbstractCellParser()
    with pytest.raises(NotImplementedError):
        cellparser.parse_value("dummy", "A1")


def test_cellparserlexical_errors():
    cellparser = MawetiGuaraniLexicalParser()
    # white spaces in excel cell
    with pytest.raises(IgnoreCellError):
        cellparser.parse_value(" ", "A1")

    # separator  in transcription
    with pytest.raises(SeparatorCellError):
        cellparser.parse_value("<tɨ̈nɨmpɨ̈'ä>[tɨ̃nɨ̃mpɨ̃ã; hɨnampɨʔa]", "A1")

    # incomplete parsing due to wrong order of variants
    with pytest.raises(CellParsingError):
        cellparser.parse_value("/ta/ [ta.'ʔa] ['ta] (cabello púbico){4}", "A1")
    # incomplete parsing due to wrong order of variants
    with pytest.raises(CellParsingError):
        cellparser.parse_value("[dʒi'tɨka] {2} ~ [ʒi'tɨka] {2}", "A1")
    # incomplete parsing due to missing separator
    with pytest.raises(CellParsingError):
        cellparser.parse_value(" /a/ [a.'ʔa] (cabello){4} /aʔa/", "A1")
    # incomplete parsing due to unrecognized separation pattern: (description), (description)
    with pytest.raises(CellParsingError):
        cellparser.parse_value("[iɾũndɨ] (H.F.) (parir), (GIVE BIRTH) [mbohaˈpɨ]", "A1")
    # incomplete parsing due to too manny sources
    with pytest.raises(CellParsingError):
        cellparser.parse_value("[dʒi'tɨka] ~ [ʒi'tɨka] {2} {2}", "A1")

    # comment error due to not matching opening and closing brackets
    with pytest.raises(FormCellError):
        cellparser.parse_value("<eniãcũpũ> (good-tasting (sweet honey, hard candy, chocolate candy, water))){2}",
                               "A1")
    # incomplete parsing due to wrong order of variants
    with pytest.raises(CellParsingError):
        cellparser.parse_value("/ta/ [ta.'ʔa] ['ta] (cabello púbico){4}", "A1")
    # incomplete parsing due to wrong order of variants
    with pytest.raises(CellParsingError):
        cellparser.parse_value("[dʒi'tɨka] {2} ~ [ʒi'tɨka] {2}", "A1")
    # incomplete parsing due to missing separator
    with pytest.raises(CellParsingError):
        cellparser.parse_value(" /a/ [a.'ʔa] (cabello){4} /aʔa/", "A1")
    # incomplete parsing due to unrecognized separation pattern: (description), (description)
    with pytest.raises(CellParsingError):
        cellparser.parse_value("[iɾũndɨ] (H.F.) (parir), (GIVE BIRTH) [mbohaˈpɨ]", "A1")
    # incomplete parsing due to too manny sources
    with pytest.raises(CellParsingError):
        cellparser.parse_value("[dʒi'tɨka] ~ [ʒi'tɨka] {2} {2}", "A1")


def test_cellparsercognate_errors():
    cellparser = MawetiGuaraniCognateParser()
    # white spaces in excel cell
    with pytest.raises(IgnoreCellError):
        cellparser.parse_value("DUMMY", "A1")

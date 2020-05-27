# -*- coding: utf-8 -*-
import json
from pathlib import Path
import pytest
from unittest import TestCase, TextTestRunner

import openpyxl as op

from lexedata.importer.cellparser import CellParserLexical, CellParser, CellParserCognate
from lexedata.importer.exceptions import *


def test_cellparser_error():
    cellparser = CellParser()
    with pytest.raises(NotImplementedError):
        cellparser.parse_value("dummy", "A1")


def test_cellparserlexical_errors():
    cellparser = CellParserLexical()
    # white spaces in excel cell
    with pytest.raises(IgnoreCellError):
        cellparser.parse_value(" ", "A1")

    # separator  in transcription
    with pytest.raises(SeparatorCellError):
        cellparser.parse_value("<tɨ̈nɨmpɨ̈'ä>[tɨ̃nɨ̃mpɨ̃ã; hɨnampɨʔa]", "A1")


def more_tests():
    for cell in []:
        for f in CellParser(cell):
            pass

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
        cellparser.parse_value("<eniãcũpũ> (good-tasting (sweet honey, hard candy, chocolate candy, water))){2}", "A1")

    c1 = Tester(
        "<tatatĩ>(humo){Guasch1962:717}, <timbo>(vapor, vaho, humareda, humo){Guasch1962:729};<tĩ> (humo, vapor de agua)$LDM:deleted 'nariz, pico, hocico, punta, and ápica' meanings; source incorrectly merges 'point' and 'smoke' meanings ${Guasch1962:729}")
    c2 = Tester(
        "/pãlĩ/ (de froment = wheat) (NCP: loan from french farine), /pɨlatɨ/ (de mais cru), /kuʔi/ (de mais grillé)")
    c3 = Tester(
        "/pãlĩ/ (de froment = wheat(NCP: loan from french farine), &<dummy>), /pɨlatɨ/ (de mais cru), /kuʔi/ (de mais grillé)")
    c4 = Tester("/popɨãpat/ 'back of elbow' {4}")
    c5 = Tester("<ayu> (nominalized &/afaaa/ version of &/ete/ 'about') {2}")
    for ele in [c1, c2, c3, c4, c5]:
        print(ele.value)
        print("is represented as: ")
        for f in CogCellParser(ele):
            print(f)
        input()


def test_cellparsercognate_errors():
    cellparser = CellParserCognate()
    # white spaces in excel cell
    with pytest.raises(IgnoreCellError):
        cellparser.parse_value("DUMMY", "A1")

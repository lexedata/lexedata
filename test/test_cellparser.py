# -*- coding: utf-8 -*-
import pytest
import unicodedata
import argparse
from pathlib import Path
import json
import tempfile
import shutil

import pycldf


from lexedata.importer import cellparser as c


# test throwing errors with wrong dataset
def test_fields_of_formtable():
    # Copy the dataset metadata file to a temporary directory.
    original = (
        Path(__file__).parent / "data/cldf/defective_dataset/Wordlist-metadata.json"
    )
    dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    target = dirname / original.name
    shutil.copyfile(original, target)
    dataset = pycldf.Dataset.from_metadata(target)
    # missing field #value
    with pytest.raises(ValueError) as err:
        c.NaiveCellParser(dataset=dataset)
    assert (
        str(err.value) == "Your metadata are missing a #value column in FormTable,"
        " which is required by your chosen cell parser NaiveCellParser"
    )
    dataset.add_columns("FormTable", "value")

    # missing field #form
    with pytest.raises(ValueError) as err:
        c.NaiveCellParser(dataset=dataset)
    assert (
        str(err.value) == "Your metadata are missing a #form column in FormTable,"
        " which is required by your chosen cell parser NaiveCellParser"
    )
    dataset.add_columns("FormTable", "form")

    # missing field #languageReference
    with pytest.raises(ValueError) as err:
        c.NaiveCellParser(dataset=dataset)
    assert (
        str(err.value)
        == "Your metadata are missing a #languageReference column in FormTable,"
        " which is required by your chosen cell parser NaiveCellParser"
    )
    dataset.add_columns("FormTable", "languageReference")

    # test required fields of FormTable from CellParser
    # missing field #comment
    with pytest.raises(ValueError) as err:
        c.CellParser(dataset=dataset)
    assert (
        str(err.value) == "Your metadata are missing a #comment column in FormTable,"
        " which is required by your chosen cell parser CellParser"
    )
    dataset.add_columns("FormTable", "comment")

    # missing field #source
    with pytest.raises(ValueError) as err:
        c.CellParser(dataset=dataset)
    assert (
        str(err.value) == "Your metadata are missing a #source column in FormTable,"
        " which is required by your chosen cell parser CellParser"
    )
    dataset.add_columns("FormTable", "source")

    # missing field #variants
    with pytest.raises(ValueError) as err:
        c.CellParser(dataset=dataset)
    assert (
        str(err.value) == "Your metadata are missing a #variants column in FormTable,"
        " which is required by your chosen cell parser CellParser"
    )
    dataset.add_columns("FormTable", "variants")

    # missing transcription element
    with pytest.raises(AssertionError) as err:
        c.CellParser(
            dataset=dataset,
            element_semantics=[
                # ("[", "]", "phonetic", True),
                ("<", ">", "form", False),
                # ("/", "/", "phonemic", True),
                ("(", ")", "comment", False),
                ("{", "}", "source", False),
            ],
        )
    assert str(err.value) == "You must specify an element with transcription semantics"


def n(s: str):
    return unicodedata.normalize("NFKC", s)


@pytest.fixture
def naive_parser():
    dataset = pycldf.Dataset.from_metadata(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    return c.NaiveCellParser(dataset)


def test_cellparser_error(naive_parser):
    assert naive_parser.parse_form("form ", "language") == {
        "Form": "form",
        "Language_ID": "language",
        "Value": "form ",
    }


@pytest.fixture
def parser():
    dataset = pycldf.Dataset.from_metadata(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    return c.CellParser(
        dataset,
        element_semantics=[
            ("/", "/", "phonemic", True),
            ("[", "]", "phonetic", True),
            ("<", ">", "orthographic", True),
            ("{", "}", "source", False),
            ("(", ")", "comment", False),
        ],
    )


def test_source_from_source_string(parser, caplog):
    assert parser.source_from_source_string("{1}", "abui") == "abui_s1"
    assert parser.source_from_source_string("", "abui") == "abui_s"
    assert (
        parser.source_from_source_string("{Gul2020: p. 4}", "abui")
        == "abui_sgul2020[p. 4]"
    )
    # catch warning for misshaped source
    parser.source_from_source_string("{1:", "abui")
    assert (
        caplog.text
        == "WARNING  lexedata.importer.cellparser:cellparser.py:247 In source "
        "{1:: Closing bracket '}' is missing, split into source and "
        "page/context may be wrong\n"
    )


def test_cellparser_separate(parser, caplog):
    assert list(parser.separate("hic, haec, hoc")) == ["hic", "haec", "hoc"]
    assert list(parser.separate("hic (this, also: here); hoc")) == [
        "hic (this, also: here)",
        "hoc",
    ]
    assert list(parser.separate("illic,")) == ["illic"]
    assert list(parser.separate("hic (this, also: here")) == ["hic (this, also: here"]
    # catch logger warning for mismatching delimiters after separation
    assert (
        caplog.text
        == "WARNING  lexedata.importer.cellparser:cellparser.py:307 In values "
        "hic (this, also: here: Encountered mismatched closing delimiters. "
        "Please check that the separation into different forms was correct.\n"
    )


def test_cellparser_separate_1(parser):
    assert list(
        parser.separate("[iɾũndɨ] (H.F.) (parir), (GIVE BIRTH) [mbohaˈpɨ]")
    ) == ["[iɾũndɨ] (H.F.) (parir)", "(GIVE BIRTH) [mbohaˈpɨ]"]


def test_cellparser_separate_2(parser):
    assert len(list(parser.separate("<tɨ̈nɨmpɨ̈'ä>[tɨ̃nɨ̃mpɨ̃ã; hɨnampɨʔa]"))) == 1


def test_cellparser_empty(parser):
    # white spaces in excel cell
    assert parser.parse_form(" ", "language") is None
    assert parser.parse_form(" \t", "abui") is None


def test_cellparser_form_1(parser):
    form = parser.parse_form("<tɨ̈nɨmpɨ̈'ä>[tɨ̃nɨ̃mpɨ̃ã; hɨnampɨʔa]", "l1")
    assert form["Source"] == {"l1_s1"}
    assert n(form["Value"]) == n("<tɨ̈nɨmpɨ̈'ä>[tɨ̃nɨ̃mpɨ̃ã; hɨnampɨʔa]")
    assert n(form["orthographic"]) == n("tɨ̈nɨmpɨ̈'ä")
    assert n(form["phonetic"]) == n("tɨ̃nɨ̃mpɨ̃ã; hɨnampɨʔa")


def test_cellparser_form_2(parser):
    form = parser.parse_form("/ta/ [ta.'ʔa] ['ta] (cabello púbico){4}", "language")
    assert form == {
        "Comment": "cabello púbico",
        "Language_ID": "language",
        "Source": {"language_s4"},
        "Value": "/ta/ [ta.'ʔa] ['ta] (cabello púbico){4}",
        "phonemic": "ta",
        "phonetic": "ta.'ʔa",
        "variants": ["['ta]"],
        "Form": "ta",
    }


def test_cellparser_form_3(parser):
    form = parser.parse_form("[dʒi'tɨka] {2} ~ [ʒi'tɨka] {2}", "language")
    assert form == {
        "Language_ID": "language",
        "Source": {"language_s2"},
        "Value": "[dʒi'tɨka] {2} ~ [ʒi'tɨka] {2}",
        "phonetic": "dʒi'tɨka",
        "variants": ["~[ʒi'tɨka]", "{2}"],
        "Form": "dʒi'tɨka",
    }


def test_cellparser_form_4(parser):
    form = parser.parse_form("[iɾũndɨ] (H.F.) (parir)", "language")
    assert form["Comment"] == "H.F."
    assert form["Source"] == {"language_s1"}
    assert n(form["Value"]) == n("[iɾũndɨ] (H.F.) (parir)")
    assert n(form["phonetic"]) == n("iɾũndɨ")
    assert form["variants"] == ["(parir)"]


def test_cellparser_form_5(parser):
    form = parser.parse_form("(GIVE BIRTH) [mbohaˈpɨ]", "language")
    assert form == {
        "Comment": "GIVE BIRTH",
        "Language_ID": "language",
        "Source": {"language_s1"},
        "Value": "(GIVE BIRTH) [mbohaˈpɨ]",
        "phonetic": "mbohaˈpɨ",
        "Form": "mbohaˈpɨ",
    }


def test_cellparser_form_6(parser):
    form = parser.parse_form("[dʒi'tɨka] ~ [ʒi'tɨka] {2} {2}", "language")
    assert form == {
        "Language_ID": "language",
        "Source": {"language_s2"},
        "Value": "[dʒi'tɨka] ~ [ʒi'tɨka] {2} {2}",
        "phonetic": "dʒi'tɨka",
        "variants": ["~[ʒi'tɨka]", "{2}"],
        "Form": "dʒi'tɨka",
    }


def test_cellparser_form_7(parser):
    # comment error due to not matching opening and closing brackets
    form = parser.parse_form(
        "<eniãcũpũ> (good-tasting (sweet honey, hard candy, chocolate candy, water))){2}",  # noqa: E501
        "language",
    )
    assert (
        form["Comment"]
        == "good-tasting (sweet honey, hard candy, chocolate candy, water)"
    )
    assert form["Language_ID"] == "language"
    assert n(form["Value"]) == n(
        "<eniãcũpũ> (good-tasting (sweet honey, hard candy, chocolate candy, water))){2}",  # noqa: E501
    )
    assert n(form["orthographic"]) == n("eniãcũpũ")
    assert not form.get("phonemic")


def test_cellparser_unexpected_variant(parser, caplog):
    form = parser.parse_form(" /a/ [a.'ʔa] (cabello){4} /aʔa/", "language")
    assert form == {
        "Comment": "cabello",
        "Language_ID": "language",
        "Source": {"language_s4"},
        "Value": " /a/ [a.'ʔa] (cabello){4} /aʔa/",
        "phonemic": "a",
        "phonetic": "a.'ʔa",
        "variants": ["/aʔa/"],
        "Form": "a",
    }
    # catch the logger warning
    assert (
        caplog.text
        == "WARNING  lexedata.importer.cellparser:cellparser.py:392 In form  /a/ [a.'ʔa] (cabello){4} "
        "/aʔa/: Element /aʔa/ was an unexpected variant for phonemic\n"
    )


def test_cellparser_missmatching(parser, caplog):
    parser.parse_form("(GIVE BIRTH) [mbohaˈpɨ", "language")
    assert (
        caplog.text
        == "WARNING  lexedata.importer.cellparser:cellparser.py:360 In form "
        "(GIVE BIRTH) [mbohaˈpɨ: Element [mbohaˈpɨ had mismatching delimiters\n"
    )


def test_cellparser_not_parsable(parser, caplog):
    parser.parse_form("!!", "language")
    assert (
        caplog.text
        == "WARNING  lexedata.importer.cellparser:cellparser.py:375 In form "
           "!!: Element !! could not be parsed, ignored\n"
    )


def test_cellparser_no_real_variant(parser, caplog):
    parser.parse_form(" ~ [ʒi'tɨka] {2} {2}", "language")
    assert (
        caplog.text
        == "WARNING  lexedata.importer.cellparser:cellparser.py:400 In form  ~ [ʒi'tɨka] {2} {2}: "
        "Element [ʒi'tɨka] was supposed to be a variant, but there is no earlier phonetic\n"
    )


@pytest.fixture
def mawetiparser():
    metadata = Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    dataset = pycldf.Dataset.from_metadata(metadata)
    dialect = argparse.Namespace(
        **json.load(metadata.open("r", encoding="utf8"))["special:fromexcel"]
    )
    initialized_cell_parser = getattr(c, dialect.cell_parser["name"])(
        dataset,
        element_semantics=dialect.cell_parser["cell_parser_semantics"],
        separation_pattern=fr"([{''.join(dialect.cell_parser['form_separator'])}])",
        variant_separator=dialect.cell_parser["variant_separator"],
        add_default_source=dialect.cell_parser["add_default_source"],
    )
    return initialized_cell_parser


def test_mawetiparser_no_duplicate_sources(mawetiparser):
    form = mawetiparser.parse_form("[dʒi'tɨka] {2} ~ [ʒi'tɨka] {2}", "language")
    assert form == {
        "Language_ID": "language",
        "Source": {"language_s2"},
        "Value": "[dʒi'tɨka] {2} ~ [ʒi'tɨka] {2}",
        "phonetic": "dʒi'tɨka",
        "variants": ["~[ʒi'tɨka]"],
        "Form": "dʒi'tɨka",
    }


def test_mawetiparser_multiple_comments(mawetiparser):
    form = mawetiparser.parse_form(
        "/etakɾã/ [e.ta.'kɾã] ~[test_variant with various comments] (uno; solo) "
        "(test comment) (test comment 2){4}",
        "language",
    )
    assert form == {
        "Language_ID": "language",
        "Source": {"language_s4"},
        "Value": ""
        "/etakɾã/ [e.ta.'kɾã] ~[test_variant with various comments] (uno; solo) "
        "(test comment) (test comment 2){4}",
        "phonetic": "e.ta.'kɾã",
        "phonemic": "etakɾã",
        "Comment": "uno; solo\ttest comment\ttest comment 2",
        "variants": ["~[test_variant with various comments]"],
        "Form": "e.ta.'kɾã",
    }


def test_mawetiparser_postprocessing(mawetiparser):
    form = {
        "orthographic": "<lexedata % lexidata>",
        "phonemic": "/lεksedata ~ lεksidata/",
        "variants": ["(from lexicon + edit + data)", "(another comment)"],
        "Comment": ""
        "(GAK: We should pick one of those names, I'm 80% sure it should be the first)",
    }
    mawetiparser.postprocess_form(form, "abui1241")
    assert form == {
        "orthographic": "lexedata",
        "phonemic": "lεksedata",
        "variants": ["~/lεksidata/", "%<lexidata>"],
        "Comment": "from lexicon + edit + data\tanother comment",
        "procedural_comment": ""
        "GAK: We should pick one of those names, I'm 80% sure it should be the first",
        "Source": {"abui1241_s1"},
        "Form": "lεksedata",
    }

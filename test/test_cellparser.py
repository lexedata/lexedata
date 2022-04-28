# -*- coding: utf-8 -*-
import pytest
import argparse
from pathlib import Path
import json
import logging
import re

import pycldf


from lexedata.edit.normalize_unicode import n
from lexedata.util import excel as c
from helper_functions import copy_metadata


@pytest.fixture(params=[r"data/cldf/smallmawetiguarani/cldf-metadata.json"])
def no_dialect(request):
    # Copy the dataset metadata file to a temporary directory.
    target = copy_metadata(Path(__file__).parent / request.param)
    with open(target, "r", encoding="utf-8") as file:
        j = json.load(file)
        j["special:fromexcel"] = {}
        j["tables"][0] = {
            "dc:conformsTo": "http://cldf.clld.org/v1.0/terms.rdf#FormTable",
            "dc:extent": 2,
            "tableSchema": {
                "columns": [
                    {
                        "datatype": "string",
                        "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#id",
                        "name": "ID",
                    }
                ],
                "primaryKey": ["ID"],
            },
            "url": "forms.csv",
        }

    with open(target, "w", encoding="utf-8") as file:
        json.dump(j, file, indent=4)
    dataset = pycldf.Dataset.from_metadata(target)
    return dataset


def test_fields_of_formtable_no_value(no_dialect):
    dataset = no_dialect
    # missing field #value
    with pytest.raises(
        ValueError,
        match="Your metadata json file and your cell parser don’t match.*#value column.*",
    ):
        c.NaiveCellParser(dataset=dataset)


def test_fields_of_formtable_no_form(no_dialect):
    dataset = no_dialect
    dataset.add_columns("FormTable", "value")

    # missing field #form
    with pytest.raises(
        ValueError,
        match="Your metadata json file and your cell parser don’t match.*#form column.*",
    ):
        c.NaiveCellParser(dataset=dataset)


def test_fields_of_formtable_no_language_reference(no_dialect):
    dataset = no_dialect
    dataset.add_columns("FormTable", "value")
    dataset.add_columns("FormTable", "form")

    # missing field #languageReference
    with pytest.raises(
        ValueError,
        match="Your metadata json file and your cell parser don’t match.*#languageReference column.*",
    ):
        c.NaiveCellParser(dataset=dataset)


def test_fields_of_formtable_no_comment(no_dialect):
    dataset = no_dialect
    dataset.add_columns("FormTable", "value")
    dataset.add_columns("FormTable", "form")
    dataset.add_columns("FormTable", "languageReference")

    # test required fields of FormTable from CellParser
    # missing field #comment
    with pytest.raises(
        ValueError,
        match="Your metadata json file and your cell parser don’t match.*#comment.*",
    ):
        c.CellParser(dataset=dataset)


def test_fields_of_formtable_no_source(no_dialect):
    dataset = no_dialect
    dataset.add_columns("FormTable", "value")
    dataset.add_columns("FormTable", "form")
    dataset.add_columns("FormTable", "languageReference")
    dataset.add_columns("FormTable", "comment")

    # missing field #source
    with pytest.raises(
        ValueError,
        match="Your metadata json file and your cell parser don’t match.*#source.*",
    ):
        c.CellParser(dataset=dataset)


def test_fields_of_formtable_no_transcription(no_dialect):
    dataset = no_dialect
    dataset.add_columns("FormTable", "value")
    dataset.add_columns("FormTable", "form")
    dataset.add_columns("FormTable", "languageReference")
    dataset.add_columns("FormTable", "comment")
    dataset.add_columns("FormTable", "source")

    # missing transcription element
    with pytest.raises(
        AssertionError,
        match=r"Your metadata json file and your cell parser don’t match.*transcriptions \(at least one of "
        r"'orthographic', 'phonemic', and 'phonetic'\) to derive a #form.*",
    ):
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


@pytest.fixture
def naive_parser():
    dataset = pycldf.Dataset.from_metadata(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    return c.NaiveCellParser(dataset)


def test_cellparser_default(naive_parser):
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


def test_source_from_source_string1(parser):
    assert parser.source_from_source_string("{1}", "abui") == "abui_s1"


def test_source_from_source_string2(parser):
    assert parser.source_from_source_string("", "abui") == "abui_s"


def test_source_from_source_string3(parser):
    assert (
        parser.source_from_source_string("{Gul2020: p. 4}", "abui")
        == "abui_sgul2020[p. 4]"
    )


def test_misshaped_source(parser, caplog):
    # catch warning for misshaped source
    parser.source_from_source_string("{1:", "abui")
    assert re.search("In source {1:: Closing bracket '}' is missing.*", caplog.text)


def test_cellparser_separate_1(parser):
    assert list(
        parser.separate("[iɾũndɨ] (H.F.) (parir), (GIVE BIRTH) [mbohaˈpɨ]")
    ) == ["[iɾũndɨ] (H.F.) (parir)", "(GIVE BIRTH) [mbohaˈpɨ]"]


def test_cellparser_separate_2(parser):
    assert len(list(parser.separate("<tɨ̈nɨmpɨ̈'ä>[tɨ̃nɨ̃mpɨ̃ã; hɨnampɨʔa]"))) == 1


def test_cellparser_separate_3(parser):
    assert list(parser.separate("hic, haec, hoc")) == ["hic", "haec", "hoc"]


def test_cellparser_separate_4(parser):
    assert list(parser.separate("hic (this, also: here); hoc")) == [
        "hic (this, also: here)",
        "hoc",
    ]


def test_cellparser_separate_5(parser):
    assert list(parser.separate("illic,")) == ["illic"]


def test_cellparser_separate_warning(parser, caplog):
    # catch logger warning for mismatching delimiters after separation
    list(parser.separate("hic (this, also: here", "B6: "))
    assert re.search(
        r".*hic \(this, also: here: Encountered mismatched closing delimiters.*",
        caplog.text,
    )


def test_cellparser_empty1(parser):
    # white spaces in excel cell
    assert parser.parse_form(" ", "language") is None


def test_cellparser_empty2(parser):
    assert parser.parse_form(" \t", "abui") is None


def test_cellparser_form_1(parser):
    form = parser.parse_form("<tɨ̈nɨmpɨ̈'ä>[tɨ̃nɨ̃mpɨ̃ã; hɨnampɨʔa]", "l1")
    assert [
        form["Source"],
        n(form["Value"]),
        n(form["orthographic"]),
        n(form["phonetic"]),
    ] == [
        {"l1_s1"},
        n("<tɨ̈nɨmpɨ̈'ä>[tɨ̃nɨ̃mpɨ̃ã; hɨnampɨʔa]"),
        n("tɨ̈nɨmpɨ̈'ä"),
        n("tɨ̃nɨ̃mpɨ̃ã; hɨnampɨʔa"),
    ]
    # assert form["Source"] == {"l1_s1"}
    # assert n(form["Value"]) == n("<tɨ̈nɨmpɨ̈'ä>[tɨ̃nɨ̃mpɨ̃ã; hɨnampɨʔa]")
    # assert n(form["orthographic"]) == n("tɨ̈nɨmpɨ̈'ä")
    # assert n(form["phonetic"]) == n("tɨ̃nɨ̃mpɨ̃ã; hɨnampɨʔa")


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
    assert form == {
        "Comment": "H.F.",
        "Source": {"language_s1"},
        "Value": "[iɾũndɨ] (H.F.) (parir)",
        "phonetic": "iɾũndɨ",
        "variants": ["(parir)"],
        "Form": "iɾũndɨ",
        "Language_ID": "language",
    }


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
    with pytest.raises(ValueError, match="had mismatching delimiters"):
        parser.parse_form(
            "<eniãcũpũ> (good-tasting (sweet honey, hard candy, chocolate candy, water))){2}",  # noqa: E501
            "language",
        )


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
    } and re.search(
        "In form  .* Element /aʔa/ was an unexpected variant for phonemic.*",
        caplog.text,
    )


def test_parser_variant_lands_in_comment(caplog):
    caplog.set_level(logging.INFO)
    dataset = pycldf.Dataset.from_metadata(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    dataset.remove_columns("FormTable", "variants")
    parser = c.CellParser(
        dataset=dataset,
        element_semantics=[
            ("/", "/", "phonemic", True),
            ("[", "]", "phonetic", True),
            ("<", ">", "orthographic", True),
            ("{", "}", "source", False),
            ("(", ")", "comment", False),
        ],
    )
    form = parser.parse_form(" {2} [dʒi'tɨka] ~[ʒi'tɨka] {2}", "language")
    assert re.search(
        "No 'variants' column found .* will be added to #comment.*", caplog.text
    ) and form == {
        "Language_ID": "language",
        "Value": " {2} [dʒi'tɨka] ~[ʒi'tɨka] {2}",
        "phonetic": "dʒi'tɨka",
        "Comment": "~[ʒi'tɨka]\t2",
        "Source": {"language_s2"},
        "Form": "dʒi'tɨka",
    }


def test_cellparser_missmatching(parser):
    with pytest.raises(
        ValueError, match="34: .* [mbohaˈpɨ had mismatching delimiters ]"
    ):
        parser.parse_form("(GIVE BIRTH) [mbohaˈpɨ", "language", cell_identifier="34: ")


def test_cellparser_not_parsable(parser, caplog):
    parser.parse_form("!!", "language", "C3: ")
    assert caplog.text.endswith(
        "C3: In form !!: Element !! could not be parsed, ignored\n"
    )


def test_cellparser_no_real_variant(parser, caplog):
    parser.parse_form(" ~ [ʒi'tɨka] {2} {2}", "language", "A4: ")
    assert caplog.text.endswith(
        "A4: In form  ~ [ʒi'tɨka] {2} {2}: "
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
        separation_pattern=rf"([{''.join(dialect.cell_parser['form_separator'])}])",
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

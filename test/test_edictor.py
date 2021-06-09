import io

import lexedata.importer.edictor as importer
import lexedata.exporter.edictor as exporter  # noqa
import lexedata.util.fs


def test_match_cognatesets_1():
    edictor_style_cognatesets = {1: [("form1", range(4), ["t", "e", "s", "t"])]}
    cldf_style_cognatesets = {"id1": [("form1", range(4), ["t", "e", "s", "t"])]}
    matching = importer.match_cognatesets(
        edictor_style_cognatesets, cldf_style_cognatesets
    )
    assert matching == {1: "id1"}


def test_match_cognatesets_2():
    edictor_style_cognatesets = {
        1: [("form1", range(4), ["t", "e", "s", "t"])],
        2: [("form2", range(4), ["t", "e", "s", "t"])],
    }
    cldf_style_cognatesets = {
        "id1": [("form1", range(4), ["t", "e", "s", "t"])],
        "id2": [("form2", range(4), ["t", "e", "s", "t"])],
    }
    matching = importer.match_cognatesets(
        edictor_style_cognatesets, cldf_style_cognatesets
    )
    assert matching == {1: "id1", 2: "id2"}


def test_write_edictor_empty_dataset():
    dataset = lexedata.util.fs.new_wordlist(FormTable=[])
    file = io.StringIO()
    file.name = "<memory>"
    forms = {}
    judgements_about_form = {}
    cognateset_numbers = {}
    exporter.write_edictor_file(
        dataset, file, forms, judgements_about_form, cognateset_numbers
    )


def test_write_edictor_small_dataset():
    dataset = lexedata.util.fs.new_wordlist(FormTable=[])
    file = io.StringIO()
    file.name = "<memory>"
    forms = {}
    judgements_about_form = {}
    cognateset_numbers = {}
    exporter.write_edictor_file(
        dataset, file, forms, judgements_about_form, cognateset_numbers
    )

import lexedata.importer.edictor as importer
import lexedata.exporter.edictor as exporter  # noqa


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
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
    assert (
        file.getvalue()
        .upper()
        .startswith(
            "ID\tCLDF_ID\tDOCULECT\tCONCEPT\tIPA\tTOKENS\tCOMMENT\tSOURCE\tCOGID\tALIGNMENT"
        )
    )


def test_write_edictor_singleton_dataset():
    forms = {
        "form1": {
            "ID": "form1",
            "Language_ID": "axav1032",
            "Parameter_ID": "one",
            "Form": "the form",
            "Segments": list("ðəfom"),
            "Source": [],
        }
    }
    dataset = lexedata.util.fs.new_wordlist(
        FormTable=forms.values(),
        CognateTable=[
            {
                "ID": "1-1",
                "Form_ID": "form1",
                "Cognateset_ID": "c1",
                "Segment_Slice": "1:1",
                "Alignment": ["ð"],
            }
        ],
    )
    file = io.StringIO()
    file.name = "<memory>"
    judgements_about_form = {"form1": (["ð", "(ə)", "(f)", "(o)", "(m)"], ["c1"])}
    cognateset_numbers = {"c1": 2}
    exporter.write_edictor_file(
        dataset, file, forms, judgements_about_form, cognateset_numbers
    )
    rows = [line.strip().split("\t") for line in file.getvalue().split("\n")[:3]]
    assert rows[2] == [""]
    assert dict(zip(rows[0], rows[1])) == {
        "ID": "1",
        "CONCEPT": "one",
        "DOCULECT": "axav1032",
        "IPA": "the form",
        "CLDF_id": "form1",
        "TOKENS": "ð ə f o m",
        "Source": "",
        "Comment": "",
        "COGID": "2",
        "ALIGNMENT": "ð ( ə f o m )",
    }
    assert "<memory>" in file.getvalue()

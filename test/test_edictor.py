import io
import tempfile
from pathlib import Path

import pycldf

import lexedata.util.fs
from lexedata import util
from lexedata.types import WorldSet
from test_excel_conversion import cldf_wordlist, working_and_nonworking_bibfile  # noqa

import lexedata.importer.edictor as importer
import lexedata.exporter.edictor as exporter


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
    assert set(file.getvalue().split("\n")[0].strip().upper().split("\t")) == {
        "ID",
        "CLDF_ID",
        "DOCULECT",
        "CONCEPT",
        "IPA",
        "TOKENS",
        "COMMENT",
        "SOURCE",
        "COGID",
        "ALIGNMENT",
    }


def test_forms_to_csv():
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
                "Segment_Slice": ["1:1"],
                "Alignment": ["ð"],
            }
        ],
    )
    forms, judgements, cognateset_cache = exporter.forms_to_tsv(
        dataset, languages=["axav1032"], concepts={"one"}, cognatesets=["c1"]
    )
    assert forms == {
        "form1": {
            "languageReference": "axav1032",
            "segments": ["ð", "ə", "f", "o", "m"],
            "form": "the form",
            "parameterReference": "one",
            "source": "",
            "id": "form1",
            "comment": None,
        }
    }

    assert judgements == {
        "form1": (["ð", "+", "(ə)", "(f)", "(o)", "(m)"], ["c1", None])
    }
    assert cognateset_cache == {"c1": 1}


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
                "Segment_Slice": ["1:1"],
                "Alignment": ["ð"],
            }
        ],
    )
    file = io.StringIO()
    file.name = "<memory>"
    judgements_about_form = {"form1": (["ð", "(ə)", "(f)", "(o)", "(m)"], ["c1"])}
    cognateset_numbers = {"c1": 2}
    exporter.write_edictor_file(
        dataset,
        file,
        util.cache_table(dataset),
        judgements_about_form,
        cognateset_numbers,
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
        "source": "",
        "comment": "",
        "COGID": "2",
        "ALIGNMENT": "ð ( ə f o m )",
    }
    assert "<memory>" in file.getvalue()


def test_roundtrip(cldf_wordlist, working_and_nonworking_bibfile):  # noqa
    """Check that a small dataset survives the round trip to edictor"""
    filled_cldf_wordlist = working_and_nonworking_bibfile(cldf_wordlist)
    dataset, target = filled_cldf_wordlist

    # Export to edictor
    forms, judgements_about_form, cognateset_mapping = exporter.forms_to_tsv(
        dataset=dataset,
        languages=WorldSet(),
        concepts=WorldSet(),
        cognatesets=WorldSet(),
    )

    _, f = tempfile.mkstemp(".tsv", "edictor")
    filename = Path(f)

    with filename.open("w", encoding="utf-8") as file:
        exporter.write_edictor_file(
            dataset, file, forms, judgements_about_form, cognateset_mapping
        )

    # Re-import
    new_cogsets, affected_forms = importer.load_forms_from_tsv(
        dataset=dataset,
        input_file=filename,
    )

    importer.edictor_to_cldf(
        dataset=dataset, new_cogsets=new_cogsets, affected_forms=affected_forms
    )

    expected = pycldf.Wordlist.from_metadata(target)
    for table in expected.tables:
        assert list(dataset[table.url]) == list(expected[table.url])

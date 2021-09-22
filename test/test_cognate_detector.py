from lexedata import util
from lexedata.edit.add_segments import add_segments_to_dataset
from lexedata.edit.detect_cognates import filter_function_factory


def test_filter_function_factory():
    ds = util.fs.new_wordlist(FormTable=[])
    add_segments_to_dataset(ds, "Form", overwrite_existing=True, replace_form=True)
    filter = filter_function_factory(ds)

    form = {
        "ID": "1",
        "Language_ID": "language",
        "Parameter_ID": "concept",
        "Form": "-",
        "Segments": [],
    }
    row = {key.lower(): val for key, val in form.items()}
    assert not filter(row)
    assert row == {
        "id": "1",
        "language_id": "language",
        "parameter_id": "concept",
        "form": "-",
        "segments": [],
        "concept": "concept",
        "doculect": "language",
        "tokens": [],
    }

    form = {
        "ID": "1",
        "Language_ID": "language",
        "Parameter_ID": "concept",
        "Form": "f",
        "Segments": ["f"],
    }
    row = {key.lower(): val for key, val in form.items()}
    assert filter(row)
    assert row == {
        "id": "1",
        "language_id": "language",
        "parameter_id": "concept",
        "form": "f",
        "segments": ["f"],
        "concept": "concept",
        "doculect": "language",
        "tokens": ["f"],
    }

    form = {
        "ID": "1",
        "Language_ID": "language",
        "Parameter_ID": "concept",
        "Form": "f a",
        "Segments": ["f", "_", "a"],
    }
    row = {key.lower(): val for key, val in form.items()}
    assert filter(row)
    assert row == {
        "id": "1",
        "language_id": "language",
        "parameter_id": "concept",
        "form": "f a",
        "segments": ["f", "_", "a"],
        "concept": "concept",
        "doculect": "language",
        "tokens": ["f", "+", "a"],
    }

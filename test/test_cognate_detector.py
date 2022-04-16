import lingpy
import pytest
from lexedata import util
from lexedata.edit.add_segments import add_segments_to_dataset
from lexedata.edit.detect_cognates import (
    alignment_functions,
    filter_function_factory,
    get_partial_matrices,
)


@pytest.fixture(params=list(alignment_functions))
def aligment_type(request):
    return request.param


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


def test_partials_compare_lingpy():
    # Test that our method of computing partial matrices matches the one implemented in LingPy.
    lex = lingpy.compare.partial.Partial(
        {
            0: ["doculect", "concept", "tokens"],
            1: ["l1", "c1", list("form")],
            2: ["l2", "c1", list("folm")],
            3: ["l3", "c1", list("furm+forn")],
            4: ["l2", "c1", list("diff't")],
        }
    )
    lex.get_scorer(runs=10000, ratio=(1, 0), threshold=0.7)
    lingpy_matrices = {
        c: matrix
        for c, mapping, matrix in lex._get_partial_matrices(
            method="lexstat",
            mode="global",
            imap_mode=True,
        )
    }
    lexedata_matrices = {
        c: matrix
        for c, mapping, matrix in get_partial_matrices(
            lex,
            ["c1"],
            method="lexstat",
            mode="global",
        )
    }
    assert lingpy_matrices == lexedata_matrices

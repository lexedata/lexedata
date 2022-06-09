import lingpy
import numpy
import pytest
from lexedata import util
from lexedata.edit.add_segments import add_segments_to_dataset
from lexedata.edit.detect_cognates import (
    alignment_functions,
    filter_function_factory,
    get_partial_matrices,
    partial_cluster,
    get_slices,
)


@pytest.fixture(params=list(alignment_functions))
def alignment_type(request):
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


@pytest.fixture
def lex():
    return lingpy.compare.partial.Partial(
        {
            0: ["doculect", "concept", "tokens"],
            1: ["l1", "c1", list("form")],
            2: ["l2", "c1", list("folm")],
            3: ["l3", "c1", list("furm+forn")],
            4: ["l2", "c1", list("diff't")],
            5: ["l1", "c2", list("room")],
            6: ["l2", "c2", list("loom")],
            7: ["l3", "c2", list("ruum+roon")],
            8: ["l2", "c2", list("other")],
            9: ["l1", "c1", list("dorm")],
            10: ["l2", "c1", list("dolm")],
            11: ["l3", "c1", list("durm+dorn")],
            12: ["l2", "c1", list("unrelated")],
        }
    )


def test_partial_matrices_compare_lingpy(lex, alignment_type):
    # Test that our method of computing partial matrices matches the one implemented in LingPy.
    lex.get_scorer(runs=10000, ratio=(1, 0), threshold=0.7)
    lingpy_matrices = {
        c: matrix
        for c, mapping, matrix in lex._get_partial_matrices(
            method="lexstat",
            mode=alignment_type,
            imap_mode=True,
        )
    }
    lexedata_matrices = {
        c: matrix
        for c, mapping, matrix in get_partial_matrices(
            lex,
            ["c1", "c2"],
            method="lexstat",
            mode=alignment_type,
        )
    }
    for concept in set(lingpy_matrices) | set(lexedata_matrices):
        assert numpy.allclose(
            lingpy_matrices[concept], lexedata_matrices[concept], equal_nan=True
        )


def test_partial_cluster_compare_lingpy(lex, alignment_type):
    # Test that our method of computing partial matrices matches the one implemented in LingPy.
    lex.get_scorer(runs=10000, ratio=(1, 0), threshold=0.7)
    lex.partial_cluster(
        method="lexstat",
        mode=alignment_type,
        imap_mode=True,
    )

    lingpy_judgements = {}

    partial_cognate_sets = lex.columns.index("partial_cognate_sets")
    tokens = lex.columns.index("tokens")
    for row_id in lex:
        row = lex[row_id]
        for slice, cognateclass in zip(
            get_slices(row[tokens]), row[partial_cognate_sets]
        ):
            lingpy_judgements[row_id, slice.start, slice.stop] = cognateclass

    judgements = {}
    for form, slice, cognateclass in partial_cluster(
        lex,
        method="lexstat",
        mode=alignment_type,
    ):
        judgements[form, slice.start, slice.stop] = cognateclass

    assert judgements == lingpy_judgements

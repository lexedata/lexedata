import re
from pathlib import Path
from copy import deepcopy

import pytest

from lexedata.edit import merge_homophones
from helper_functions import copy_to_temp

M = merge_homophones.all_mergers


# Test the merging functions


def test_errors(caplog):
    assert merge_homophones.must_be_equal([1, 1]) == 1
    assert merge_homophones.must_be_equal([]) is None
    with pytest.raises(AssertionError):
        merge_homophones.must_be_equal([None, 1])
    with pytest.raises(AssertionError):
        merge_homophones.must_be_equal(["This is a partial string", "partial string"])
    with pytest.raises(AssertionError):
        merge_homophones.must_be_equal([1, 2])

    assert merge_homophones.must_be_equal_or_null([None, 1]) == 1
    assert merge_homophones.must_be_equal_or_null([None, None]) is None
    assert merge_homophones.must_be_equal_or_null([None, 1, None]) == 1

    assert merge_homophones.warn([1, 1]) == 1
    assert merge_homophones.warn([]) is None
    merge_homophones.warn([None, 1], {"id": 1})
    assert re.search(
        r".*The entries \[None, 1], to be merged into 1, were not identical.",
        caplog.text,
    )
    merge_homophones.warn(["This is a partial string", "partial string"], {"id": 2})
    assert re.search(
        r".*The entries \['This is a partial string', 'partial string'], to be merged into 2, were not identical.",
        caplog.text,
    )
    # TODO: TypError, list of list not hashable
    # merge_homophones.warn([[1, 2], [1], [2]], {"id": 3})
    assert re.search(
        r".*The entries \[None, 1], to be merged into 1, were not identical.",
        caplog.text,
    )

    assert merge_homophones.must_be_equal_or_null([None, 1], {"id": 4}) == 1
    assert not re.search(
        r".*The entries \[None, 1], to be merged into 4, were not identical.",
        caplog.text,
    )
    assert merge_homophones.must_be_equal_or_null([None, None], {"id": 5}) is None
    assert not re.search(
        r".*The entries \[None, None], to be merged into 1, were not identical.",
        caplog.text,
    )
    assert merge_homophones.must_be_equal_or_null([None, 1, None], {"id": 6}) == 1
    assert not re.search(
        r".*The entries \[None, 1, None], to be merged into 1, were not identical.",
        caplog.text,
    )


def test_skip(caplog):
    with pytest.raises(merge_homophones.Skip):
        merge_homophones.cancel_and_skip([1, 2])

    # Something like:
    target_form = {"id": 2}
    target_form["id"] = merge_homophones.cancel_and_skip([1, 1], target_form)
    assert target_form == {"id": 1}
    # Of course, this needs another function of merge_homophones around it, but
    # I don't know the call signature of that, and this test is definitely
    # necessary.


def test_concatenations():
    assert merge_homophones.concatenate([["this"], ["text"]]) == ["this", "text"]
    assert merge_homophones.concatenate([["this"], ["text"], ["text"]]) == [
        "this",
        "text",
        "text",
    ]
    assert merge_homophones.concatenate([None, "this", "text"]) == "; this; text"
    assert merge_homophones.concatenate(["this", "text"]) == "this; text"
    assert merge_homophones.concatenate(["this", "", "text"]) == "this; ; text"
    assert merge_homophones.concatenate(["this", None, "text"]) == "this; ; text"
    assert merge_homophones.concatenate([None, "this", "text"]) == "; this; text"
    assert merge_homophones.concatenate([["this"], [], ["text"]]) == ["this", "text"]
    assert merge_homophones.concatenate([["this", "text"], [], ["text"]]) == [
        "this",
        "text",
        "text",
    ]
    with pytest.raises(NotImplementedError):
        assert merge_homophones.concatenate([1, 3])


def test_union():
    assert merge_homophones.union([["this"], ["text"]]) == ["this", "text"]
    assert merge_homophones.union([["this"], ["text"], ["text"]]) == ["this", "text"]
    assert merge_homophones.union([["text"], ["this"], ["text"]]) == ["text", "this"]
    assert merge_homophones.union(["this", "text"]) == "this; text"
    assert merge_homophones.union(["this", "", "text"]) == "this; ; text"
    assert merge_homophones.union(["this", None, "text"]) == "this; ; text"
    assert merge_homophones.union([["this"], [], ["text"]]) == ["this", "text"]
    assert merge_homophones.union([["this", "text"], [], ["text"]]) == ["this", "text"]
    with pytest.raises(NotImplementedError):
        assert merge_homophones.union([1, 3])


# TODO: Some of the merging functions referenced here don't exist anymore or never existed so far
def test_simple():
    assert merge_homophones.first([["this"], ["text"]]) == ["this"]
    assert merge_homophones.first([["this"], ["text"], ["text"]]) == ["this"]
    assert merge_homophones.first(["this", "text"]) == "this"
    assert merge_homophones.first(["this", "", "text"]) == "this"
    assert merge_homophones.first(["this", None, "text"]) == "this"
    assert merge_homophones.first([None, "this", "text"]) is None
    # assert M["first-not-null"]([None, "this", "text"]) == "this"
    assert merge_homophones.first([["this"], [], ["text"]]) == ["this"]
    assert merge_homophones.first([["this", "text"], [], ["text"]]) == [
        "this",
        "text",
    ]
    assert merge_homophones.first([1, 3]) == 1
    # assert M["min"]([1, 3]) == 1
    # assert M["max"]([1, 3]) == 3


def test_constants():
    assert (
        merge_homophones.constant_factory("MERGED: Review necessary")(["this", "text"])
        == "MERGED: Review necessary"
    )


@pytest.mark.skip("No function for parsing merge string.")
def test_parse_merge_string():
    assert merge_homophones.parse_merge_command("Source:SKIP") == {
        "Source": merge_homophones.cancel_and_skip
    }
    already_parsed = {"Source": merge_homophones.cancel_and_skip}
    merge_homophones.parse_merge_command("orthographic:VARIANTS", already_parsed)
    assert already_parsed == {
        "Source": merge_homophones.cancel_and_skip,
        "orthographic": merge_homophones.cancel_and_skip,
    }
    with pytest.raises(ValueError):
        merge_homophones.parse_merge_command("orthographic:VARIANTS", already_parsed)


def test_preprocessing():
    # Create tmp dataset with #parameterReference without separator
    # Run preprocessing function
    # Check that #parameterReference now has a separator
    # Check that there was a warning explaining this change
    # Reload the tmp dataset, see that the separator was indeed written to the metadata
    ...


def test_merge_1():
    dataset, _ = copy_to_temp(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    c_f_id = dataset["FormTable", "id"].name
    first_form = next(dataset["FormTable"].iterdicts())
    first_id = first_form[c_f_id]
    new_first_id = first_form[c_f_id] + "1"
    new_first_form = deepcopy(first_form)
    new_first_form[c_f_id] = new_first_id
    dataset.write(FormTable=[first_form, new_first_form])
    buffer = merge_homophones.merge_forms(
        data=dataset,
        mergers=merge_homophones.default_mergers,
        homophone_groups={first_id: [new_first_id]},
    )
    assert [f[c_f_id] for f in buffer] == [first_form[c_f_id]]
    # Create tmp dataset with two identical forms (apart from ID)
    # run merging function, with these two IDs
    # Check that the result has exactly one form, with the first ID


def test_merge_2():
    dataset, _ = copy_to_temp(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    c_f_id = dataset["FormTable", "id"].name
    forms = [
        {
            "ID": "ache_one",
            "Language_ID": "ache",
            "Parameter_ID": ["one", "one"],
            "Form": "e.ta.'kɾã",
            "orthographic": "",
            "phonemic": "etakɾã",
            "phonetic": "e.ta.'kɾã",
            "variants": ["~1"],
            "Segments": [],
            "Comment": "uno",
            "procedural_comment": "",
            "Value": "value1",
            "Source": ["ache_s4"],
        },
        {
            "ID": "ache_one1",
            "Language_ID": "ache",
            "Parameter_ID": ["one", "one"],
            "Form": "e.ta.'kɾã",
            "orthographic": "etakɾã",
            "phonemic": "",
            "phonetic": "e.ta.'kɾã",
            "variants": ["~2"],
            "Segments": [],
            "Comment": "dos",
            "procedural_comment": "",
            "Value": "value2",
            "Source": ["ache_s5"],
        },
        {
            "ID": "ache_one2",
            "Language_ID": "ache",
            "Parameter_ID": ["one"],
            "Form": "form1",
            "orthographic": "",
            "phonemic": "",
            "phonetic": "",
            "variants": [""],
            "Segments": [],
            "Comment": "",
            "procedural_comment": "",
            "Value": "2",
            "Source": [""],
        },
        {
            "ID": "ache_one3",
            "Language_ID": "ache",
            "Parameter_ID": ["one"],
            "Form": "form2",
            "orthographic": "",
            "phonemic": "",
            "phonetic": "",
            "variants": [""],
            "Segments": [],
            "Comment": "",
            "procedural_comment": "",
            "Value": "3",
            "Source": [""],
        },
    ]
    first_id = forms[0][c_f_id]
    dataset.write(FormTable=forms)
    merger = merge_homophones.default_mergers
    merger["phonemic"] = merge_homophones.first
    merger["orthographic"] = merge_homophones.first
    buffer = [
        e
        for e in merge_homophones.merge_forms(
            data=dataset, mergers=merger, homophone_groups={"ache_one": ["ache_one1"]}
        )
    ]
    assert (
        len(buffer) == 3
        and buffer[0][c_f_id] == first_id
        and buffer[0]["orthographic"] == "etakɾã"
        and buffer[0]["phonemic"] == "etakɾã"
    )
    # Create tmp dataset with four form, two of which have identical #forms,
    # but different transcriptions, one only an orthographic one, the other one
    # only a phonemic one; run merging function, explicitly taking
    # "first-not-null", with the two homophones; Check that the result has three
    # forms, and the homophone has both transcriptions


def test_merge_3():
    dataset, _ = copy_to_temp(
        Path(__file__).parent / "data/cldf/smallmawetiguarani/cldf-metadata.json"
    )
    c_f_id = dataset["FormTable", "id"].name
    forms = [
        {
            "ID": "ache_one",
            "Language_ID": "ache",
            "Parameter_ID": ["one", "one"],
            "Form": "e.ta.'kɾã",
            "orthographic": "",
            "phonemic": "etakɾã",
            "phonetic": "e.ta.'kɾã",
            "variants": ["~1"],
            "Segments": ["a"],
            "Comment": "uno",
            "procedural_comment": "",
            "Value": "value1",
            "Source": ["ache_s4"],
        },
        {
            "ID": "ache_one1",
            "Language_ID": "ache",
            "Parameter_ID": ["one1", "one1"],
            "Form": "e.ta.'kɾã",
            "orthographic": "etakɾã",
            "phonemic": "",
            "phonetic": "e.ta.'kɾã",
            "variants": ["~2"],
            "Segments": ["b"],
            "Comment": "dos",
            "procedural_comment": "",
            "Value": "value2",
            "Source": ["ache_s5"],
        },
        {
            "ID": "ache_one2",
            "Language_ID": "ache",
            "Parameter_ID": ["two1", None],
            "Form": "e.ta.'kɾã",
            "orthographic": "etakɾã",
            "phonemic": "",
            "phonetic": "e.ta.'kɾã",
            "variants": ["~3"],
            "Segments": [None],
            "Comment": "tres",
            "procedural_comment": "",
            "Value": "value3",
            "Source": ["ache_s6"],
        },
        {
            "ID": "ache_one3",
            "Language_ID": "ache",
            "Parameter_ID": ["one"],
            "Form": "form1",
            "orthographic": "",
            "phonemic": "",
            "phonetic": "",
            "variants": [""],
            "Segments": [],
            "Comment": "",
            "procedural_comment": "",
            "Value": "2",
            "Source": [""],
        },
        {
            "ID": "ache_one4",
            "Language_ID": "ache",
            "Parameter_ID": ["one"],
            "Form": "form2",
            "orthographic": "",
            "phonemic": "",
            "phonetic": "",
            "variants": [""],
            "Segments": [],
            "Comment": "",
            "procedural_comment": "",
            "Value": "3",
            "Source": [""],
        },
    ]
    first_id = forms[0][c_f_id]
    dataset.write(FormTable=forms)
    merger = merge_homophones.default_mergers
    merger["phonemic"] = merge_homophones.first
    merger["orthographic"] = merge_homophones.first
    buffer = [
        e
        for e in merge_homophones.merge_forms(
            data=dataset,
            mergers=merger,
            homophone_groups={"ache_one": ["ache_one1", "ache_one2"]},
        )
    ]
    first_form = buffer[0]
    assert (
        len(buffer) == 3
        and first_form[c_f_id] == first_id
        and first_form["Language_ID"] == "ache"
        and first_form["Parameter_ID"] == ["one", "one", "one1", "two1", ""]
        and first_form["orthographic"] == "etakɾã"
        and first_form["phonemic"] == "etakɾã"
        and first_form["variants"] == ["~1", "~2", "~3"]
        and first_form["Source"] == ["ache_s4", "ache_s5", "ache_s6"]
        and first_form["Value"] == "value1; value2; value3"
        and first_form["Comment"] == "uno; dos; tres"
        and first_form["Segments"] == ["a", "b"]
    )
    # Create tmp dataset with four form, two of which have identical #forms,
    # but different transcriptions, one only an orthographic one, the other one
    # only a phonemic one; run merging function, with default merging
    # functions; Check that the result has three forms, and that the two forms
    # got merged as expected. Can also check different more mergable forms here
    # to increase coverage


def test_parse_merge_override():
    assert ("Source", merge_homophones.union) == merge_homophones.parse_merge_override("Source:union")


def test_order_merge():
    """Say, the dataset has forms 1, 2, 3 in that order.
    Someone wrote in their homophones to be merged that 3, 2, 1 shoud be merged.
    Presumably, that means the values in form 3 have precedence, and for concatenate, they should appear in order 3,2,1.
    """


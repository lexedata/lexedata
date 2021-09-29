import re

import pytest

from lexedata.edit import merge_homophones

M = merge_homophones.merging_functions


# Test the merging functions


def test_errors(caplog):
    assert M["error"]([1, 1]) == 1
    assert M["error"]([]) is None
    with pytest.raises(AssertionError):
        M["error"]([None, 1])
    with pytest.raises(AssertionError):
        M["error"](["This is a partial string", "partial string"])
    with pytest.raises(AssertionError):
        M["error"]([[1, 2], [1], [2]])

    assert M["error-not-null"]([None, 1]) == 1
    assert M["error-not-null"]([None, None]) is None
    assert M["error-not-null"]([None, 1, None]) is None

    assert M["warning"]([1, 1]) == 1
    assert M["warning"]([]) is None
    M["warning"]([None, 1], {"id": 1})
    assert re.search("merging homophones into 1", caplog.text)
    M["warning"](["This is a partial string", "partial string"], {"id": 2})
    assert re.search("merging homophones into 2", caplog.text)
    M["warning"]([[1, 2], [1], [2]], {"id": 3})
    assert re.search("merging homophones into 3", caplog.text)

    assert M["error-not-null"]([None, 1], {"id": 4}) == 1
    assert not re.search("merging homophones into 4", caplog.text)
    assert M["error-not-null"]([None, None], {"id": 5}) is None
    assert not re.search("merging homophones into 5", caplog.text)
    assert M["error-not-null"]([None, 1, None], {"id": 6}) is None
    assert not re.search("merging homophones into 6", caplog.text)


def test_skip(caplog):
    with pytest.raises(merge_homophones.Skip):
        M["skip"]([[1, 2], [1], [2]])

    # Something like:
    target_form = {"id": 1}
    M["variants"](["a", "e"], target_form)
    M["skip"]([[1, 2], [1], [2]], target_form)
    assert target_form == {"id": 1}
    # Of course, this needs another function of merge_homophones around it, but
    # I don't know the call signature of that, and this test is definitely
    # necessary.


def test_concatenations():
    assert M["concatenate"]([["this"], ["text"]]) == ["this", "text"]
    assert M["concatenate"]([["this"], ["text"], ["text"]]) == ["this", "text", "text"]
    assert M["concatenate"](["this", "text"]) == "this;text"
    assert M["concatenate"](["this", "", "text"]) == "this;;text"
    assert M["concatenate"](["this", None, "text"]) == "this;;text"
    assert M["concatenate"]([None, "this", "text"]) == ";this;text"
    assert M["concatenate"]([["this"], [], ["text"]]) == ["this", None, "text"]
    assert M["concatenate"]([["this", "text"], [], ["text"]]) == [
        "this",
        "text",
        None,
        "text",
    ]
    with pytest.raises(TypeError):
        assert M["concatenate"]([1, 3])

    assert M["union"]([["this"], ["text"]]) == ["this", "text"]
    assert M["union"]([["this"], ["text"], ["text"]]) == ["this", "text"]
    assert M["union"]([["text"], ["this"], ["text"]]) == ["text", "this"]
    assert M["union"](["this", "text"]) == "this;text"
    assert M["union"](["this", "", "text"]) == "this;text"
    assert M["union"](["this", None, "text"]) == "this;text"
    assert M["concatenate"]([None, "this", "text"]) == "this;text"
    assert M["union"]([["this"], [], ["text"]]) == ["this", "text"]
    assert M["union"]([["this", "text"], [], ["text"]]) == ["this", "text"]
    with pytest.raises(TypeError):
        assert M["union"]([1, 3])


def test_simple():
    assert M["first"]([["this"], ["text"]]) == ["this"]
    assert M["first"]([["this"], ["text"], ["text"]]) == ["this"]
    assert M["first"](["this", "text"]) == "this"
    assert M["first"](["this", "", "text"]) == "this"
    assert M["first"](["this", None, "text"]) == "this"
    assert M["first"]([None, "this", "text"]) is None
    assert M["first-not-null"]([None, "this", "text"]) == "this"
    assert M["first"]([["this"], [], ["text"]]) == ["this"]
    assert M["first"]([["this", "text"], [], ["text"]]) == [
        "this",
        "text",
    ]
    assert M["first"]([1, 3]) == 1
    assert M["min"]([1, 3]) == 1
    assert M["max"]([1, 3]) == 3


def test_constants():
    assert M["status"](["this", "text"]) == "Homophones merged: Review necessary"


def test_parse_merge_string():
    assert merge_homophones.parse_merge_command("Source:SKIP") == {"Source": M["skip"]}
    already_parsed = {"Source": M["skip"]}
    merge_homophones.parse_merge_command("orthographic:VARIANTS", already_parsed)
    assert already_parsed == {"Source": M["skip"], "orthographic": M["skip"]}
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
    # Create tmp dataset with two identical forms (apart from ID)
    # run merging function, with these two IDs
    # Check that the result has exactly one form, with the first ID
    ...


def test_merge_2():
    # Create tmp dataset with four form, two of which have identical #forms,
    # but different transcriptions, one only an orthographic one, the other one
    # only a phonemic one; run merging function, explicitly taking
    # "first-not-null", with the two homophones; Check that the result has three
    # forms, and the homophone has both transcriptions
    ...


def test_merge_3():
    # Create tmp dataset with four form, two of which have identical #forms,
    # but different transcriptions, one only an orthographic one, the other one
    # only a phonemic one; run merging function, with default merging
    # functions; Check that the result has three forms, and that the two forms
    # got merged as expected. Can also check different more mergable forms here
    # to increase coverage
    ...

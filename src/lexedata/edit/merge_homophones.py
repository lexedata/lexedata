"""Read a homophones report (an edited one, most likely) and merge all pairs of form in there.

Different treatment for separated fields, and un-separated fields
Form variants into variants?
Make sure concepts have a separator
What other columns give warnings, what other columns give errors?

*Optionally*, merge cognate sets that get merged by this procedure.
"""

import typing as t

C = t.TypeVar("C")
Merger = t.Callable[[t.Sequence[C], t.Optional[t.Dict[str, t.Any]]], t.Optional[C]]


class Skip(Exception):
    """Skip this merge, leave all forms as expected. This is not an Error!"""


def assert_equal(
    sequence: t.Sequence[C], target: t.Optional[t.Dict[str, t.Any]] = None
) -> t.Optional[C]:
    forms = set(sequence)
    assert len(forms) <= 1
    try:
        return forms.pop()
    except KeyError:
        return None


def assert_equal_ignoring_null(
    sequence: t.Sequence[C], target: t.Optional[t.Dict[str, t.Any]] = None
) -> t.Optional[C]:
    return assert_equal(list(filter(bool, sequence)))


def variants(
    sequence: t.Sequence[C], target: t.Optional[t.Dict[str, t.Any]] = None
) -> t.Optional[C]:
    raise NotImplementedError


def concatenate(
    sequence: t.Sequence[C], target: t.Optional[t.Dict[str, t.Any]] = None
) -> t.Optional[C]:
    raise NotImplementedError


def warn(
    sequence: t.Sequence[C], target: t.Optional[t.Dict[str, t.Any]] = None
) -> t.Optional[C]:
    raise NotImplementedError


def constant_factory(c: C) -> Merger[C]:
    def constant(
        sequence: t.Sequence[C], target: t.Optional[t.Dict[str, t.Any]] = None
    ) -> t.Optional[C]:
        return c

    return constant


merging_functions: t.Dict[str, Merger] = {
    "error": assert_equal,
    "error-not-null": assert_equal_ignoring_null,
}


default_mergers = {
    "form": "error-not-null",
    "language": "error-not-null",
    "source": "union",
}

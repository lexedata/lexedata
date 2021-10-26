"""Read a homophones report (an edited one, most likely) and merge all pairs of form in there.

Different treatment for separated fields, and un-separated fields
Form variants into variants?
Make sure concepts have a separator
What other columns give warnings, what other columns give errors?

*Optionally*, merge cognate sets that get merged by this procedure.
"""
import re
import argparse
import typing as t
from pathlib import Path
from collections import defaultdict
from io import StringIO

import pycldf

import lexedata.cli as cli
from lexedata import types

# The cell value type, which tends to be string, lists of string, or int:
C = t.TypeVar("C")
# A CLDF row, mapping column names to cell values:
MaybeRow = t.Optional[types.Form]
# A function that matches a sequence of cell values to a ‘summary’ Cell value –
# or None. It may modify the row in-place, if given a row:
Merger = t.Callable[[t.Sequence[C], MaybeRow], t.Optional[C]]

# For sequence operations, we treat strings as implicit sequences separated by
# the separator.
SEPARATOR = "; "


def isiterable(object):
    if isinstance(object, str):
        return False
    try:
        _ = iter(object)
    except TypeError:
        return False
    return True


class Skip(Exception):
    """Skip this merge, leave all forms as expected. This is not an Error!"""


def cancel_and_skip(
    sequence: t.Sequence[C],
    target: MaybeRow = None,
) -> t.Optional[C]:
    """If entries differ, do not merge this set of forms

    >>> cancel_and_skip([])

    >>> cancel_and_skip([1, 2])
    Traceback (most recent call last):
    ...
        raise Skip
    lexedata.edit.merge_homophones.Skip

    >>> cancel_and_skip([1, 1])
    1

    """
    forms = set(sequence)
    if not len(forms) <= 1:
        raise Skip
    try:
        return forms.pop()
    except KeyError:
        return None


def must_be_equal(
    sequence: t.Sequence[C],
    target: MaybeRow = None,
) -> t.Optional[C]:
    """
    End with an error if entries are not equal
    >>> must_be_equal([1, 2])
    Traceback (most recent call last):
    ...
    AssertionError: assert 2 <= 1
    ...
    >>> must_be_equal([1, 1])
    1
    >>> must_be_equal([])

    """
    forms = set(sequence)
    assert len(forms) <= 1
    try:
        return forms.pop()
    except KeyError:
        return None


def must_be_equal_or_null(
    sequence: t.Sequence[C],
    target: MaybeRow = None,
) -> t.Optional[C]:
    """
    End with an error if those entries which are present are not equal
    >>> must_be_equal_or_null([1, 2])
    Traceback (most recent call last):
    ...
    AssertionError: assert 2 <= 1
    ...

    >>> must_be_equal_or_null([1, 1])
    1
    >>> must_be_equal_or_null([1, 1, None])
    1
    """
    return must_be_equal(list(filter(bool, sequence)))


def warn(
    sequence: t.Sequence[C],
    target: MaybeRow = None,
) -> t.Optional[C]:
    """Print a warning if entries are not equal, but proceed taking the first one

    >>> warn([1, 2])
    1
    >>> warn([1, 1])
    1
    """
    forms = set(sequence)
    if not len(forms) <= 1:
        cli.logger.warning(
            "The entries {:}, to be merged into {:}, were not identical.".format(
                sequence, target and target.get("id")
            )
        )
    try:
        return sequence[0]
    except IndexError:
        return None


def first(
    sequence: t.Sequence[C],
    target: MaybeRow = None,
) -> t.Optional[C]:
    """
    Take the first entry, no matter whether the others match or not
    >>> first([1, 2])
    1
    >>> first([])

    """
    try:
        return sequence[0]
    except IndexError:
        return None


def transcription(wrapper: str = "{}"):
    """Make a closure that adds variants to a variants column

    >>> row = {"variants": None}
    >>> orthographic = transcription("<{}>")
    >>> orthographic(["a", "a", "an"], row)
    'a'
    >>> row
    {'variants': ['<an>']}

    """

    def first_transcription_remainder_to_variants(
        sequence: t.Sequence[C],
        target: MaybeRow = None,
    ) -> t.Optional[C]:
        all_transcriptions: t.Optional[t.List[C]] = union([[s] for s in sequence])
        if all_transcriptions is None:
            return None
        else:
            if target is not None:
                try:
                    target["variants"] = (target.get("variants") or []) + [
                        wrapper.format(s) for s in all_transcriptions[1:]
                    ]
                except KeyError:
                    pass
            return all_transcriptions[0]

    first_transcription_remainder_to_variants.__name__ = f"transcription({wrapper!r})"
    first_transcription_remainder_to_variants.__doc__ = f"Keep one transcription in this column, add others as {wrapper} to variants".format(
        "form"
    )
    return first_transcription_remainder_to_variants


def concatenate(
    sequence: t.Sequence[C],
    target: MaybeRow = None,
) -> t.Optional[C]:
    """Concatenate all entries, even if they are identical, in the given order

    Strings are concatenated using '; ' as a separator. FOr iterables
    >>> concatenate([[1, 2], [2, 4]])
    [1, 2, 2, 4]
    >>> concatenate([["a", "b"], ["c", "a"]])
    ['a', 'b', 'c', 'a']
    >>> concatenate(["a", "b"])
    'a; b'

    """
    if isinstance(sequence[0], str):
        return SEPARATOR.join(sequence)
    elif isiterable(sequence[0]):
        # Assume list values, and accept the type error if not
        return sum(sequence, [])
    else:
        raise NotImplementedError


def union(
    sequence: t.Sequence[C],
    target: MaybeRow = None,
) -> t.Optional[C]:
    """Concatenate all entries, without duplicates

    Strings are concatenated using '; ' as a separator. FOr iterables
    >>> union([[1, 2], [2, 4]])
    [1, 2, 4]
    >>> union([["a", "b"], ["c", "a"]])
    ['a', 'b', 'c']
    >>> union(["a", "b", "a"])
    'a; b'

    """
    if isinstance(sequence[0], str):
        unique = []
        for entry in sequence:
            for component in entry.split(SEPARATOR):
                if component not in unique:
                    unique.append(component)
        return SEPARATOR.join(unique)
    elif isiterable(sequence[0]):
        # Assume list values, and accept the type error if not
        unique = []
        for entry in sequence:
            for component in entry:
                if component not in unique:
                    unique.append(component)
        return unique
    else:
        raise NotImplementedError


def constant_factory(c: C) -> Merger[C]:
    """
    >>> constant = constant_factory("a")
    >>> constant()
    'a'

    """

    def constant(
        sequence: t.Sequence[C],
        target: MaybeRow = None,
    ) -> t.Optional[C]:
        return c

    constant.__name__ = f"constant({c!r})"
    constant.__doc__ = f"Set the column to {c!r} for the merged form"
    return constant


def default(
    sequence: t.Sequence[C],
    target: MaybeRow = None,
) -> t.Optional[C]:
    """
    Union for sequence-shaped entries (strings, and lists with a separator in the metadata),
    must_be_equal otherwise
    >>> default([1, 2])
    '1'
    >>> default([1, 2], [3, 4]])
    [1, 2, 3, 4]
    """
    if isiterable(sequence[0]):
        return union(sequence, target)
    else:
        return must_be_equal(sequence, target)


default_mergers: t.Mapping[str, Merger] = t.DefaultDict(
    lambda: default,
    {
        "form": must_be_equal,
        "language": must_be_equal,
        "source": union,
        "concept": union,
        "variants": union,
        "source": union,
        "status": constant_factory("MERGED: Review necessary"),
        "orthographic": transcription("<{}>"),
        "phonemic": transcription("/{}/"),
        "phonetic": transcription("[{}]"),
    },
)


def merge_group(
    forms: t.Sequence[types.Form],
    target: types.Form,
    mergers: t.Mapping[str, Merger],
    dataset: types.Wordlist[
        types.Language_ID,
        types.Form_ID,
        types.Parameter_ID,
        types.Cognate_ID,
        types.Cognateset_ID,
    ],
) -> types.Form:
    for column in target:
        _, reference_name = dataset["FormTable", column].propertyUrl.split("#")
        merger = mergers.get(column, mergers.get(reference_name, must_be_equal))
        target[column] = merger([form[column] for form in forms], target)
    return target


def merge_forms(
    data: types.Wordlist[
        types.Language_ID,
        types.Form_ID,
        types.Parameter_ID,
        types.Cognate_ID,
        types.Cognateset_ID,
    ],
    mergers: t.Mapping[str, Merger],
    homophone_groups: t.Mapping[types.Form_ID, t.Sequence[types.Form_ID]],
) -> t.Iterable[types.Form]:
    merge_targets = {
        variant: target
        for target, variants in homophone_groups.items()
        for variant in variants
    }
    c_f_id = data["FormTable", "id"].name

    for form_id in homophone_groups:
        assert merge_targets[form_id] == form_id

    buffer: t.OrderedDict[types.Form_ID, types.Form] = t.OrderedDict()
    unknown = set()
    form: types.Form
    for form in data["FormTable"]:
        id: types.Form_ID = form[c_f_id]
        buffer[id] = form
        if form in merge_targets:
            unknown.add(id)
            target_id = merge_targets[id]
            group = homophone_groups[target_id]
            if all(i in buffer for i in group):
                try:
                    buffer[target_id] = merge_group(
                        [buffer[i] for i in group],
                        buffer[target_id].copy(),  # type: ignore
                        mergers,
                        data,
                    )
                    for i in group:
                        if i != target_id:
                            del buffer[i]
                except Skip:
                    pass
                for i in group:
                    unknown.remove(i)
        for f in buffer:
            if f in unknown:
                break
            yield buffer.pop(f)


def parse_merge_override(string: str) -> t.Tuple[str, Merger]:
    column, merger_name = string.rsplit(":", 1)
    merger_name = merger_name.lower()
    return (column, eval(merger_name.lower()))


def format_mergers(mergers: t.Mapping[str, Merger]) -> str:
    return "\n".join(
        " {col}:{name}".format(col=col, name=function.__name__)
        for col, function in mergers.items()
    )


def parse_homophones_report(
        report: t.TextIO,
) -> t.Mapping[types.Form_ID, t.Sequence[types.Form_ID]]:
    r"""Parse legacy homophones merge instructions

    The format of the input file is the same as the output of the homophones report

    >>> file = StringIO("ache, e.ta.'kɾã: Unknown (but at least one concept not found)\n"
    ... "    ache_one (one, one)\n"
    ... "    ache_two_3 (two, two)\n")
    >>> parse_homophones_report(file)
    defaultdict(<class 'list'>, {'ache_one': ['ache_two_3']})
    """
    homophone_groups: t.Mapping[types.Form_ID, t.List[types.Form_ID]] = defaultdict(list)
    first_id = True
    target_id = ""
    for line in report:
        match = re.match(r"\s+?(\w+?) .*", line)
        if match:
            id = match.group(1)
            if first_id:
                target_id = id
                first_id = False
            else:
                homophone_groups[target_id].append(id)
        else:
            first_id = True
    return homophone_groups


def parse_homophones_old_format(
    report: t.TextIO,
) -> t.Mapping[types.Form_ID, t.Sequence[types.Form_ID]]:
    """Parse legacy homophones merge instructions

    >>> file = StringIO("Unconnected: Matsigenka kis {('ANGRY', '19148'), ('FIGHT (v. Or n.)', '19499'), ('CRITICIZE, SCOLD', '19819')}")
    >>> parse_homophones_old_format(file)
    defaultdict(<class 'list'>, {'19148': ['19499', '19819']})
    """
    homophone_groups: t.Mapping[types.Form_ID, t.List[types.Form_ID]] = defaultdict(list)
    first_id = True
    target_id = ""
    for line in report:
        match = re.findall(r"\('.+?', '(\w+?)'\),? ?", line)
        if match:
            for id in match:
                if first_id:
                    target_id = id
                    first_id = False
                else:
                    homophone_groups[target_id].append(id)
            first_id = True
        else:
            first_id = True
    return homophone_groups


all_mergers: t.Set[Merger] = {default}
all_mergers.update(default_mergers.values())
for name, item in list(vars().items()):
    if callable(item) and hasattr(item, "__annotations__"):
        if set(item.__annotations__) == {"sequence", "target", "return"}:
            # It would be better to check the actual types, instead of the
            # parameter names, but that would need a deeper delve into the
            # typing system.
            all_mergers.add(item)

if __name__ == "__main__":
    parser = cli.parser(
        description="Script for merging homophones.",
        epilog="""The default merging functions are:
{:}

Every other column is merged with `default`.

The following merge functions are predefined, each takes the given entries for one column of the forms to be merged and aggregates them into a single new entry for the merged result form.
{:}
        """.format(
            format_mergers(default_mergers),
            "\n".join(
                sorted(
                    "{}: {}".format(m.__name__, m.__doc__.split("\n")[0])
                    for m in all_mergers
                )
            ),
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "merge_report",
        help="Path pointing to the file containing the merge report generated by report/homophones.py",
        type=Path,
    )
    parser.add_argument(
        "--merge",
        nargs="+",
        default=[],
        type=parse_merge_override,
        metavar="COLUMN:MERGER",
        help="""Override merge defaults using COLUMN:MERGER syntax, eg. --merge Source:cancel_and_skip orthographic:transcription('~<{}>').""",
    )
    args = parser.parse_args()
    dataset = pycldf.Wordlist.from_metadata(args.metadata)

    cli.logger = cli.setup_logging(args)
    mergers = dict(default_mergers)
    for column, merger in args.merge:
        mergers[column] = merger

    # Parse the homophones instructions!
    homophone_groups = parse_homophones_report(args.merge_report.open("r", encoding="utf8"))

    dataset.write(
        FormTable=merge_forms(
            data=pycldf.Dataset.from_metadata(args.metadata),
            mergers=mergers,
            homophone_groups=homophone_groups,
        )
    )

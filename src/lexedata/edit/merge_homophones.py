"""Read a homophones report (an edited one, most likely) and merge all pairs of form in there.

Different treatment for separated fields, and un-separated fields
Form variants into variants?
Make sure concepts have a separator
What other columns give warnings, what other columns give errors?

*Optionally*, merge cognate sets that get merged by this procedure.
"""
import argparse
import typing as t
from pathlib import Path
import re
from collections import defaultdict
import tempfile

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


def skip(
    sequence: t.Sequence[C],
    target: MaybeRow = None,
) -> t.Optional[C]:
    raise Skip


def assert_equal(
    sequence: t.Sequence[C],
    target: MaybeRow = None,
) -> t.Optional[C]:
    forms = set(sequence)
    assert len(forms) <= 1
    try:
        return forms.pop()
    except KeyError:
        return None


def assert_equal_ignoring_null(
    sequence: t.Sequence[C],
    target: MaybeRow = None,
) -> t.Optional[C]:
    return assert_equal(list(filter(bool, sequence)))


def variants_factory(formstring: str="{}"):
    def variants(
        sequence: t.Sequence[C],
        target: t.Optional[t.Dict[str, t.Any]] = None,
        separator: str = ";",
    ) -> t.Optional[C]:
        all_transcriptions = union(sequence=sequence)
        target["variants"] += all_transcriptions[1:]
        return all_transcriptions[0]
    return variants


def warn(
    sequence: t.Sequence[C],
    target: MaybeRow = None,
) -> t.Optional[C]:
    forms = set(sequence)
    if not len(forms) <= 1:
        cli.logger.warning(
            "The entries {:}, to be merged into {:}, were not identical.".format(
                sequence, target and target.get("id")
            )
        )
    try:
        return forms.pop()
    except KeyError:
        return None


def transcription(wrapper: str = "{}"):
    """Make a closure that adds variants to a variants column

    >>> row = {"variants": None}
    >>> orthographic = transcription("<{}>")
    >>> orthographic(["a", "a", "an"], row)
    "a"
    >>> row
    {"variants": ["<an>"]}

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
                        wrapper.format(s) for s, in all_transcriptions[1:]
                    ]
                except KeyError:
                    pass
            return all_transcriptions[0]

    first_transcription_remainder_to_variants.__name__ = f"transcription({wrapper!r})"
    return first_transcription_remainder_to_variants


def concatenate(
    sequence: t.Sequence[C],
    target: MaybeRow = None,
) -> t.Optional[C]:
    if isinstance(sequence[0], str):
        return SEPARATOR.join(sequence)
    elif isiterable(sequence[0]):
        # TODO: I expect this to throw a TypeError
        # Assume list values, and accept the type error if not
        return sum(sequence, start=[])
    else:
        raise NotImplementedError


def union(
    sequence: t.Sequence[C],
    target: MaybeRow = None,
) -> t.Optional[C]:
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
    def constant(
        sequence: t.Sequence[C],
        target: MaybeRow = None,
    ) -> t.Optional[C]:
        return c

    constant.__name__ = f"constant({c!r})"
    return constant


# TODO: Melvin has trouble understanding the terminology here. Why error - > assert_equal?
# TODO: as i understand the meeting agenda, error should throw errors?
merging_functions: t.Dict[str, Merger] = {
    "error": assert_equal,
    "error-not-null": assert_equal_ignoring_null,
    "concatenate": concatenate,
    "union": union,
    "skip": skip,
    "status": constant_factory("Status_Update"),
    "orthographic": variants_factory("<{}>")
}


# default_mergers = {
#     "form": "error-not-null",
#     "language": "error-not-null",
#     "source": "union",
#     "concept": "union",
#     "variants": "union"
# }


def default(
    sequence: t.Sequence[C],
    target: MaybeRow = None,
) -> t.Optional[C]:
    if isiterable(sequence[0]):
        return union(sequence, target)
    else:
        return assert_equal(sequence, target)


default_mergers: t.Mapping[str, Merger] = t.DefaultDict(
    lambda: default,
    {
        "form": assert_equal_ignoring_null,
        "language": assert_equal_ignoring_null,
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
        merger = mergers.get(column, mergers.get(reference_name, assert_equal))
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
    homophone_groups: t.Mapping[types.Form_ID, t.Set[types.Form_ID]],
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


def parse_homophones_report(report: Path)->t.Mapping[types.Form_ID, t.Set[types.Form_ID]]:
    """
    :param report:
    :return:
    >>> dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    >>> file = dirname / "temp_file.txt"
    >>> open_file = file.open("w", encoding="utf8")
    >>> _ = open_file.write("ache, e.ta.'kɾã: Unknown (but at least one concept not found):")
    >>> _ = open_file.write("   ache_two_3, (two, two)")
    >>> _ = open_file.write("   ache_one, (one, one)")
    >>> open_file.close()
    >>> parse_homophones_report(file)
    defaultdict(<class 'set'>, {'19148': {'19819', '19499'}})
    """
    homophone_groups: t.Mapping[types.Form_ID, t.Set[types.Form_ID]] = defaultdict(set)
    with report.open("r", encoding="utf8") as inn:
        first_id = True
        target_id = ""
        for line in inn:
            match = re.match(r"\s+?(\w+?) .*", line)
            if match:
                id = match.group(1)
                if first_id:
                    target_id = id
                    first_id = False
                else:
                    homophone_groups[target_id].add(id)
            else:
                first_id = True
    return homophone_groups


def parse_homophones_old_format(report: Path)->t.Mapping[types.Form_ID, t.Set[types.Form_ID]]:
    """
    :param report:
    :return:
    >>> dirname = Path(tempfile.mkdtemp(prefix="lexedata-test"))
    >>> file = dirname / "temp_file1.txt"
    >>> open_file = file.open("w", encoding="utf8")
    >>> _ = open_file.write("Unconnected: Matsigenka kis {('ANGRY', '19148'), ('FIGHT (v. Or n.)', '19499'), ('CRITICIZE, SCOLD', '19819')}")
    >>> open_file.close()
    >>> parse_homophones_old_format(file)
    defaultdict(<class 'set'>, {'19148': {'19819', '19499'}})
    """
    homophone_groups: t.Mapping[types.Form_ID, t.Set[types.Form_ID]] = defaultdict(set)
    with report.open("r", encoding="utf8") as inn:
        first_id = True
        target_id = ""
        for line in inn:
            match = re.findall(r"\('.+?', '(\w+?)'\),? ?", line)
            if match:
                for id in match:
                    if first_id:
                        target_id = id
                        first_id = False
                    else:
                        homophone_groups[target_id].add(id)
                first_id = True
            else:
                first_id = True
    return homophone_groups


if __name__ == "__main__":
    parser = cli.parser(
        description="Script for merging homophones.",
        epilog="""The default merging functions are: {:} 
        Every other column is merged with `union` if it has list or string values, and with `assert_equal` 
        otherwise.""".format(
            format_mergers(default_mergers)
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
        help="""Override merge defaults using COLUMN_NAME:MERGER syntax, 
        eg. --merge Source:skip orthographic:transcription("~<{{}}>").""",
    )
    args = parser.parse_args()
    dataset = pycldf.Wordlist.from_metadata(args.metadata)

    cli.logger = cli.setup_logging(args)
    mergers = dict(default_mergers)
    for column, merger in args.merge:
        mergers[column] = merger

    # Parse the homophones instructions!
    homophone_groups = parse_homophones_report(args.merge_report)

    dataset.write(
        FormTable=merge_forms(
            data=pycldf.Dataset.from_metadata(args.metadata),
            mergers=mergers,
            homophone_groups=homophone_groups,
        )
    )

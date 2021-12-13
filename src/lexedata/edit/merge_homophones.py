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

import pycldf

from lexedata import cli, util, types

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

    >>> cancel_and_skip([1, 2]) # doctest: +IGNORE_EXCEPTION_DETAIL
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
    >>> must_be_equal([1, 2]) # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    AssertionError: assert 2 <= 1
    >>> must_be_equal([1, 1])
    1
    >>> must_be_equal([])

    """
    try:
        c = sequence[0]
        for other_c in sequence:
            assert c == other_c
    except KeyError:
        return None


def must_be_equal_or_null(
    sequence: t.Sequence[C],
    target: MaybeRow = None,
) -> t.Optional[C]:
    """
    End with an error if those entries which are present are not equal
    >>> must_be_equal_or_null([1, 2]) # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
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

    Strings are concatenated using '; ' as a separator. Other iterables are
    flattened.

    >>> concatenate([[1, 2], [2, 4]])
    [1, 2, 2, 4]
    >>> concatenate([["a", "b"], ["c", "a"]])
    ['a', 'b', 'c', 'a']
    >>> concatenate(["a", "b"])
    'a; b'

    """
    if isinstance(sequence[0], str) or sequence[0] is None:
        unique = [s if s is not None else "" for s in sequence]
        return SEPARATOR.join(unique)
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

    Iterables are flattened. Strings are considered sequences of '; '-separated
    strings and flattened accordingly. Empty values are ignored.

    >>> union([[1, 2], [2, 4]])
    [1, 2, 4]
    >>> union([None, [1], [3]])
    [1, 3]
    >>> union([["a", "b"], ["c", "a"]])
    ['a', 'b', 'c']
    >>> union([None, "a", "b"])
    'a; b'
    >>> union(["a", "b", "a", ""])
    'a; b'
    >>> union(["a", "b", "a", None])
    'a; b'
    >>> union(["a", "b", "a; c", None])
    'a; b'

    """
    if isinstance(sequence[0], str) or sequence[0] is None:
        unique = []

        for entry in sequence:
            if entry is None:
                entry = ""
            for component in entry.split(SEPARATOR):
                if component not in unique:
                    unique.append(component)
        return SEPARATOR.join(unique)
    elif isiterable(sequence[0]):
        # Assume list values, and accept the type error if not
        unique = []
        for entry in sequence:
            for component in entry:
                if component is None:
                    continue
                if component not in unique:
                    unique.append(component)
        return unique
    else:
        raise NotImplementedError


def constant_factory(c: C) -> Merger[C]:
    """Create a merger taht always returns c.

    This is useful eg. for the status column, which needs to be updated when
    forms are merged, to a value that does not depend on the earlier status.

    >>> constant = constant_factory("a")
    >>> constant([None, 'b'])
    'a'
    >>> constant([])
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
    """A default merger.

    Union for sequence-shaped entries (strings, and lists with a separator in
    the metadata), must_be_equal otherwise

    >>> default([1, 2]) # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    AssertionError: ...
    >>> default([[1, 2], [3, 4]])
    [1, 2, 3, 4]
    >>> default(["a; b", "a", "c; b"])
    'a; b; c'

    """
    if isiterable(sequence[0]):
        return union(sequence, target)
    else:
        return must_be_equal(sequence, target)


default_mergers: t.Mapping[str, Merger] = t.DefaultDict(
    lambda: default,
    {
        "Form": must_be_equal,
        "form": must_be_equal,
        "languageReference": must_be_equal,
        "Language_ID": must_be_equal,
        "Source": union,
        "parameterReference": union,
        "Parameter_ID": union,
        "variants": union,
        "Comment": concatenate,
        "Value": concatenate,
        "status": constant_factory("MERGED: Review necessary"),
        "orthographic": transcription("<{}>"),
        "phonemic": transcription("/{}/"),
        "phonetic": transcription("[{}]"),
        "Segments": union,
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
    logger: cli.logging.Logger = cli.logger,
) -> types.Form:
    c_f_id = dataset["FormTable", "id"].name
    for column in target:
        if column == c_f_id:
            continue
        try:
            reference_name = (
                util.cldf_property(dataset["FormTable", column].propertyUrl) or column
            )
            merger = mergers.get(column, mergers.get(reference_name, must_be_equal))
            try:
                merge_result = merger([form[column] for form in forms], target)
            except AssertionError:
                merger_name = merger.__name__
                cli.Exit.INVALID_INPUT(
                    f"Merging forms: {[f[c_f_id] for f in forms]} with target: {target[c_f_id]} on column: {column}\n"
                    f"The merge function {merger_name} requires the input data to be equal. \n"
                    f"Given input: {[form[column] for form in forms]}"
                )
            except NotImplementedError:
                merger_name = merger.__name__
                cli.Exit.INVALID_INPUT(
                    f"Merging forms: {[f[c_f_id] for f in forms]} with target: {target[c_f_id]} \n"
                    f"The merge function {merger_name} is not implemented for type {type(forms[0])}. \n"
                    f"Given input: {[form[column] for form in forms]}"
                )
            # make sure nothing in the target is overwritten with None or empty string
            if (merge_result is None or merge_result == "") and (
                target[column] is not None or target[column] != ""
            ):
                continue
            # don't overwrite target value, but add return value from merging function
            if target[column] is None:
                target[column] = merge_result
            else:
                if (
                    isinstance(target[column], str)
                    and isinstance(merge_result, str)
                    and merge_result != target[column]
                ):
                    target[column] += SEPARATOR + merge_result
                elif target[column] != merge_result:
                    target[column] += merge_result
        except KeyError:
            cli.Exit.INVALID_COLUMN_NAME(f"Column {column} is not in FormTable.")
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
    logger: cli.logging.Logger = cli.logger,
) -> t.Iterable[types.Form]:
    merge_targets = {
        variant: target
        for target, variants in homophone_groups.items()
        for variant in variants
    }
    c_f_id = data["FormTable", "id"].name

    for ids_to_merge in homophone_groups.values():
        for form_id in ids_to_merge:
            assert merge_targets[form_id] in homophone_groups

    buffer: t.Dict[types.Form_ID, types.Form] = {}
    for f in data["FormTable"]:
        buffer[f[c_f_id]] = f

    unknown = set()
    form: types.Form
    for form in cli.tq(
        data["FormTable"],
        task="Going through forms and merging",
        logger=logger,
        total=data["FormTable"].common_props.get("dc:extent"),
    ):
        id: types.Form_ID = form[c_f_id]
        if id in merge_targets:
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
                        logger,
                    )

                    for i in group:
                        if i != target_id:
                            del buffer[i]
                except Skip:
                    logger.info(
                        f"Merging form {id} with forms {[f[c_f_id] for f in group]} was skipped."
                    )
                    pass
                unknown.remove(id)

    for f in buffer:
        if f in unknown:
            break
        yield buffer[f]


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
    >>> from io import StringIO
    >>> file = StringIO("ache, e.ta.'kɾã: Unknown (but at least one concept not found)\n"
    ... "    ache_one (one, one)\n"
    ... "    ache_two_3 (two, two)\n")
    >>> parse_homophones_report(file)
    defaultdict(<class 'list'>, {'ache_one': ['ache_two_3']})
    """
    homophone_groups: t.Mapping[types.Form_ID, t.List[types.Form_ID]] = defaultdict(
        list
    )
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
    >>> from io import StringIO
    >>> file = StringIO("Unconnected: Matsigenka kis {('ANGRY', '19148'), ('FIGHT (v. Or n.)', '19499'), ('CRITICIZE, SCOLD', '19819')}")
    >>> parse_homophones_old_format(file)
    defaultdict(<class 'list'>, {'19148': ['19499', '19819']})
    """
    homophone_groups: t.Mapping[types.Form_ID, t.List[types.Form_ID]] = defaultdict(
        list
    )
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
        "merge_file",
        type=Path,
        help="Path pointing to the file containing the mergers, in the same format as output by report.homophones",
        metavar="MERGE_FILE",
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
    logger = cli.setup_logging(args)

    dataset = pycldf.Wordlist.from_metadata(args.metadata)
    if not dataset["FormTable", "parameterReference"].separator:
        logger.warning(
            "I had to set a separator for your forms' concepts. I set it to ';'."
        )
        dataset["FormTable", "parameterReference"].separator = ";"

    mergers: t.Dict[str, Merger] = dict(default_mergers)
    for column, merger in args.merge:
        # TODO: catch error of unkown merger, and generally treat this better
        mergers[column] = eval(merger)
    logger.debug(
        "The homophones merger was initialized as follows\n Column : merger function\n"
        + "\n".join("{}: {}".format(k, m.__name__) for k, m in mergers.items())
    )
    # Parse the homophones instructions!
    homophone_groups = parse_homophones_report(
        args.merge_file.open("r", encoding="utf8"),
    )
    if homophone_groups == defaultdict(list):
        cli.Exit.INVALID_INPUT(
            f"The provided report {args.report} is empty or does not have the correct format."
        )

    dataset.write(
        FormTable=list(
            merge_forms(
                data=dataset,
                mergers=mergers,
                homophone_groups=homophone_groups,
                logger=logger,
            )
        )
    )

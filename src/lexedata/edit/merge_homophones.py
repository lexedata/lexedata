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


# TODO: For this function to fulfill its purpose we would need to pass it the dataset or the variants key,
# I think it s better to set as a default
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
                target["variants"] = (target.get("variants") or []) + [
                    wrapper.format(s) for s, in all_transcriptions[1:]
                ]
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


def merge_forms(
    dataset: pycldf.Dataset,
    report: Path,
    merger: Merger,
    status_update: str = "MERGED: Review necessary",
) -> None:
    c_f_id = dataset["FormTable", "id"].name
    c_f_form = dataset["FormTable", "form"].name
    c_f_source = dataset["FormTable", "source"].name
    source_separator = dataset["FormTable", "source"].separator
    foreign_key_form_concept = ""
    for foreign_key in dataset["FormTable"].tableSchema.foreignKeys:
        if foreign_key.reference.resource == dataset["ParameterTable"].url:
            foreign_key_form_concept = foreign_key.columnReference[0]
    concept_separator = dataset["FormTable", "parameterReference"].separator
    add_status_column_to_table(dataset=dataset, table_name="FormTable")
    c_f_status = dataset["FormTable", "Status_Column"].name
    try:
        c_f_variant = dataset["FormTable", "variants"].name
    except KeyError:
        c_f_variant = None
    if c_f_variant:
        variant_separator = dataset["FormTable", "variants"].separator
    # check if there are transcription columns
    try:
        dialect = argparse.Namespace(
            **dataset.tablegroup.common_props["special:fromexcel"]
        )
        # TODO: this might be risky, as we have to extract the names of the transcription columns from the dialect. And this involes hard coding some stuff
        transcriptions = []
        for ele in dialect.cell_parser["cell_parser_semantics"]:
            transcriptions.append(ele[2])
        if transcriptions:
            if "source" in transcriptions:
                transcriptions.remove("source")
            if "variants" in transcriptions:
                transcriptions.remove("variants")
            if "form" in transcriptions:
                transcriptions.remove("form")
            if "comment" in transcriptions:
                transcriptions.remove("comment")
    except KeyError:
        transcriptions = None
    all_forms: t.Dict[str, types.Form] = {}
    for f in dataset["FormTable"]:
        all_forms[f[c_f_id]] = f
    # TODO: write function that reads report and returns 'forms_to_merge'
    # key is form id from report that appears first in the dataset
    # Then iterate over all forms, if form id in forms_to_merge
    forms_to_merge: t.Dict[FORMID, t.Set[FORMID]] = []

    # parse csv string back into python objects
    with report.open("r", encoding="utf8") as input:
        reader = DictReader(input)
        for row in reader:
            concept_list = []
            dummy_concept_list = row["Concepts"]
            dummy_concept_list = dummy_concept_list.lstrip("{")
            dummy_concept_list = dummy_concept_list.rstrip("}")
            dummy_concept_list = re.split(r"\),", dummy_concept_list)
            for i in range(len(dummy_concept_list)):
                dummy_concept_list[i] = dummy_concept_list[i].replace("(", "")
                dummy_concept_list[i] = dummy_concept_list[i].replace(")", "")
                if dummy_concept_list[i].startswith(" "):
                    dummy_concept_list[i] = dummy_concept_list[i].lstrip(" ")
            for element in dummy_concept_list:
                elements = element.split(",")
                dummy_elements = []
                for e in elements:
                    if e.startswith(" "):
                        e = e.lstrip(" ")
                    e = e.replace("'", "")
                    dummy_elements.append(e)
                concept_list.append(tuple(dummy_elements))

            for element in concept_list:
                element = list(element)
                form_id = element.pop(-1)
                forms_to_merge[row["Form"]].append(form_id)

    for k, values in forms_to_merge.items():
        first_id = values.pop(0)
        try:
            first_form = all_forms[first_id]
            first_c_form = all_forms[first_id][c_f_form]
        except KeyError:
            cli.Exit.INVALID_ID(
                f"The form id {first_id} from the merge report could not be found in the dataset."
            )
        if c_f_variant:
            first_variants = all_forms[first_id][c_f_variant]
        else:
            first_variants = None
        if isinstance(first_variants, list):
            pass
        else:
            first_variants = [first_variants]

        first_concept = all_forms[first_id][foreign_key_form_concept]
        if isinstance(first_concept, list):
            pass
        else:
            first_concept = [first_concept]

        first_source = all_forms[first_id][c_f_source]
        if isinstance(first_source, list):
            pass
        else:
            first_source = [first_source]

        for id in values:
            try:
                form = all_forms[id]
            except KeyError:
                cli.Exit.INVALID_ID(
                    f"The form id {first_id} from the merge report could not be found in the dataset."
                )
            # merge concepts
            concept = form[foreign_key_form_concept]
            first_concept = merging_functions[merger["concept"]](
                sequence=concept, target=first_concept, separator=concept_separator
            )
            # merge sources
            source = form[c_f_source]
            first_source = merging_functions[merger["source"]](
                sequence=source, target=first_source, separator=source_separator
            )

            # add existing variants to variants
            if c_f_variant:
                first_variants = merging_functions[merger[c_f_variant]](
                    sequence=form[c_f_variant],
                    target=first_variants,
                    separator=variant_separator,
                )

            # add mismatching transcriptions to variants, if transcriptions exists.
            # Default behaviour, add them to variants
            to_add_to_variants = []
            if transcriptions is not None:
                for name in transcriptions:
                    if first_form[name] == form[name]:
                        continue
                    try:
                        if merging_functions[merger[name]].__name__ != "variants":
                            to_add_to_transcription = merging_functions[merger[name]](
                                sequence=form[name],
                                target=first_form[name],
                            )
                            # overwrite this transcription field of the first form
                            all_forms[first_id][name] = to_add_to_transcription
                        else:
                            to_add_to_variants = merging_functions[merger[name]](
                                sequence=form[name],
                                target=to_add_to_variants,
                                separator=variant_separator,
                            )
                    except KeyError:
                        cli.Exit.CLI_ARGUMENT_ERROR(
                            f"No merging function was specified for the transcription {name}. "
                            f"Please choose one using the argument --{name}."
                        )

            if to_add_to_variants:
                first_variants.extend(to_add_to_variants)
            this_c_form = form[c_f_form]
            # delete current form
            del all_forms[id]
            # add mismatching forms to variants
            # TODO: unsure here if I should concatenate different forms or add them to variants
            # TODO: anyhow, this step needs to be performed as a last step because of the continue
            # TODO: besides, the report already assures that the forms are identical...
            if first_c_form == this_c_form:
                continue
            else:
                if c_f_variant is not None:
                    variants.append(this_c_form)

        # write merged form
        all_forms[first_id][foreign_key_form_concept] = first_concept
        all_forms[first_id][c_f_source] = first_source
        if c_f_variant is not None:
            all_forms[first_id][c_f_variant] = first_variants
        if status_update is not None:
            all_forms[first_id][c_f_status] = status_update

    dataset.write(FormTable=all_forms.values())


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


if __name__ == "__main__":
    parser = cli.parser(
        description="Script for merging homophones.",
        epilog="""The default merging functions are:
{:}
Every other column is merged with `union` if it has list or string values, and with `assert_equal` otherwise.""".format(
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
        help="""Override merge defaults using COLUMN_NAME:MERGER syntax, eg. --merge Source:skip orthographic:transcription("~<{{}}>").""",
    )
    args = parser.parse_args()
    dataset = pycldf.Wordlist.from_metadata(args.metadata)

    cli.logger = cli.setup_logging(args)
    mergers = dict(default_mergers)
    for column, merger in args.merge:
        mergers[column] = merger

    # Parse the homophones instructions!
    homophone_groups = ...

    dataset.write(
        FormTable=merge_forms(
            data=pycldf.Dataset.from_metadata(args.metadata),
            mergers=mergers,
            homophone_groups=homophone_groups,
        )
    )

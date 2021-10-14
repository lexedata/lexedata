"""Read a homophones report (an edited one, most likely) and merge all pairs of form in there.

Different treatment for separated fields, and un-separated fields
Form variants into variants?
Make sure concepts have a separator
What other columns give warnings, what other columns give errors?

*Optionally*, merge cognate sets that get merged by this procedure.
"""
from pathlib import Path
import typing as t
from csv import DictReader
from collections import defaultdict
import re
import argparse

import pycldf

import lexedata.cli as cli
from lexedata import types
from lexedata.edit.add_status_column import add_status_column_to_table

# TODO: Melvin does not understand this type annotation. Or better, why use it in such a way?
C = t.TypeVar("C")
MaybeRow = t.Optional[t.Dict[str, t.Any]]
Merger = t.Callable[[t.Sequence[C], MaybeRow], t.Optional[C]]


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
    separator: str = ";",
) -> t.Optional[C]:
    return assert_equal(list(filter(bool, sequence)))


# TODO: For this function to fulfill its purpose we would need to pass it the dataset or the variants key,
# I think it s better to set as a default
def transcription(wrapper: str = "{}"):
    def first_transcription_remainder_to_variants(
        sequence: t.Sequence[C],
        target: MaybeRow = None,
    ) -> t.Optional[C]:
        all_transcriptions = union([[s] for s in sequence])
        target["variants"] = (target.get("variants") or []) + [
            wrapper.format(s) for s, in all_transcriptions[1:]
        ]
        return all_transcriptions[0][0]


def concatenate(
    sequence: t.Sequence[C],
    target: MaybeRow = None,
) -> t.Optional[C]:
    if type(sequence[0]) == str:
        return "; ".join(sequence)
    elif type(sequence[0]) == list:
        return sum(sequence, start=[])
    else:
        raise NotImplementedError


def union(
    sequence: t.Sequence[C],
    target: MaybeRow = None,
) -> t.Optional[C]:
    if type(sequence[0]) == str:
        unique = []
        for x in sequence:
            if x not in unique:
                unique.append(x)
        return "; ".join(unique)
    elif type(sequence[0]) == list:
        # Assume list values, and accept the type error if not
        unique = []
        for xs in sequence:
            for x in xs:
                if x not in unique:
                    unique.append(x)
        return unique
    else:
        raise NotImplementedError


def warn(
    sequence: t.Sequence[C],
    target: t.Optional[t.Dict[str, t.Any]] = None,
    separator: str = ";",
) -> t.Optional[C]:
    if isiterable(target):
        target = target[0]
    if isiterable(sequence):
        sequence = sequence[0]
    assert type(target) == type(sequence), (
        f"Comparing instances of different types:"
        f" {target} type:{type(target)} and {sequence} type: {type(sequence)}"
    )
    if target != sequence:
        cli.logger.warning(
            f"The instance {sequence} was not equal to the instance of the first form {target}. {sequence} was ignored."
        )
    return target


def constant_factory(c: C) -> Merger[C]:
    def constant(
        sequence: t.Sequence[C],
        target: MaybeRow = None,
    ) -> t.Optional[C]:
        return c

    return constant


# TODO: Melvin has trouble understanding the terminology here. Why error - > assert_equal?
# TODO: as i understand the meeting agenda, error should throw errors?
merging_functions: t.Dict[str, Merger] = {
    "error": assert_equal,
    "error-not-null": assert_equal_ignoring_null,
    "concatenate": concatenate,
    "union": union,
    "skip": skip,
}


default_mergers: t.Mapping[str, str] = {
    "form": "error-not-null",
    "language": "error-not-null",
    "source": "union",
    "concept": "union",
    "variants": "union",
}


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
    forms_to_merge: t.DefaultDict[str, t.List] = defaultdict(list)

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
            first_concept = merger["concept"](
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
                    [].append(this_c_form)

        # write merged form
        all_forms[first_id][foreign_key_form_concept] = first_concept
        all_forms[first_id][c_f_source] = first_source
        if c_f_variant is not None:
            all_forms[first_id][c_f_variant] = first_variants
        if status_update is not None:
            all_forms[first_id][c_f_status] = status_update

    dataset.write(FormTable=all_forms.values())


def parse_merge_override(string: str) -> t.Tuple[str, Merger]:
    column, merger_name = string.rsplit(-1, ":")
    merger_name = merger_name.lower()
    return (column, merging_functions[merger_name])


def format_mergers(mergers: t.Dict[str, str]) -> str:
    "\n".join(
        "{col}:{name}".format(col=col, name=name.upper())
        for col, name in mergers.items()
    )


if __name__ == "__main__":

    parser = cli.parser(description="Script for merging homophones.")
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
        help="""Override merge defaults using COLUMN_NAME:MERGER syntax, eg. --merge Source:SKIP orthographic:VARIANTS. The default merging functions are:

        {:}

        The available mergers are {:}""".format(
            format_mergers(default_mergers), [key.upper() for key in merging_functions]
        ),
    )
    # parser.add_argument(
    #     "--source",
    #     type=str,
    #     help="Specify the way to merge sources. (default union)",
    #     choices=["error-not-null", "error", "warn", "union", "concatenate", "skip"],
    #     default="union",
    # )
    # parser.add_argument(
    #     "--variants",
    #     type=str,
    #     help="Specify the way to merge sources. (default union)",
    #     choices=["error-not-null", "error", "warn", "union", "concatenate", "skip"],
    #     default="union",
    # )
    # parser.add_argument(
    #     "--concept",
    #     type=str,
    #     help="Specify the way to merge concepts. (default union)",
    #     choices=["error-not-null", "error", "warn", "union", "concatenate", "skip"],
    #     default="union",
    # )
    # parser.add_argument(
    #     "--orthographic",
    #     type=str,
    #     help="Specify the way to merge orthographic transcriptions",
    #     choices=["error-not-null", "error", "warn", "union", "concatenate", "skip"],
    # )
    # parser.add_argument(
    #     "--phonemic",
    #     type=str,
    #     help="Specify the way to merge phonemic transcriptions",
    #     choices=["error-not-null", "error", "warn", "union", "concatenate", "skip"],
    # )
    # parser.add_argument(
    #     "--phonetic",
    #     type=str,
    #     help="Specify the way to merge phonetic transcriptions",
    #     choices=["error-not-null", "error", "warn", "union", "concatenate", "skip"],
    # )
    parser.add_argument(
        "--status-update",
        type=str,
        default="MERGED: Review necessary",
        help="Text written to Status_Column. Set to 'None' for no status update. "
        "(default: MERGED: Review necessary)",
    )
    args = parser.parse_args()
    logger = cli.setup_logging(args)
    mergers = default_mergers
    for column, merger in args.merge:
        mergers[column] = merger
    if args.status_update == "None":
        args.status_update = None
    merge_forms(
        dataset=pycldf.Dataset.from_metadata(args.metadata),
        report=args.merge_report,
        merger=mergers,
        status_update=args.status_update,
    )

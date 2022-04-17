"""Read a homophones report (an edited one, most likely) and merge all pairs of form in there.

Different treatment for separated fields, and un-separated fields
Form variants into variants?
Make sure concepts have a separator
What other columns give warnings, what other columns give errors?

*Optionally*, merge cognate sets that get merged by this procedure.
"""

import argparse
import typing as t
from collections import defaultdict
from pathlib import Path

import pycldf

from lexedata import cli, types, util
from lexedata.edit.merge_homophones import (
    Merger,
    Skip,
    all_mergers,
    default,
    first,
    format_mergers,
    must_be_equal,
    parse_homophones_report,
    parse_merge_override,
)
from lexedata.util.simplify_ids import update_ids

# TODO: Options given on the command line should have preference over defaults,
# no matter whether they are given in terms of names ("Parameter_ID") or
# property URLs ("parameterReference")
default_mergers: t.Mapping[str, Merger] = t.DefaultDict(
    lambda: default,
    {
        "Name": first,
        "parameterReference": first,
    },
)


def merge_group(
    cogsets: t.Sequence[types.CogSet],
    target: types.CogSet,
    mergers: t.Mapping[str, Merger],
    dataset: types.Wordlist[
        types.Language_ID,
        types.Form_ID,
        types.Parameter_ID,
        types.Cognate_ID,
        types.Cognateset_ID,
    ],
    logger: cli.logging.Logger = cli.logger,
) -> types.CogSet:
    """Merge one group of cognate sets.

    The target is assumed to be already included in the forms.

    """
    c_s_id = dataset["CognatesetTable", "id"].name
    for column in target:
        if column == c_s_id:
            continue
        try:
            reference_name = (
                util.cldf_property(dataset["CognatesetTable", column].propertyUrl)
                or column
            )
            merger = mergers.get(column, mergers.get(reference_name, must_be_equal))
            try:
                merge_result = merger([cogset[column] for cogset in cogsets], target)
            except AssertionError:
                merger_name = merger.__name__
                # We cannot deal with this block, but others may be fine.
                logger.error(
                    f"Merging cognate sets: {[f[c_s_id] for f in cogsets]} with target: {target[c_s_id]} on column: {column}\n"
                    f"The merge function {merger_name} requires the input data to be equal. \n"
                    f"Given input: {[cogset[column] for cogset in cogsets]}"
                )
                raise Skip
            except NotImplementedError:
                merger_name = merger.__name__
                # Other groups will have the same issue.
                cli.Exit.INVALID_INPUT(
                    f"Merging forms: {[f[c_s_id] for f in cogsets]} with target: {target[c_s_id]} \n"
                    f"The merge function {merger_name} is not implemented for type {type(cogsets[0])}. \n"
                    f"Given input: {[cogset[column] for cogset in cogsets]}"
                )
            target[column] = merge_result
        except KeyError:
            cli.Exit.INVALID_COLUMN_NAME(f"Column {column} is not in CognatesetTable.")
    return target


def merge_cogsets(
    data: types.Wordlist[
        types.Language_ID,
        types.Form_ID,
        types.Parameter_ID,
        types.Cognate_ID,
        types.Cognateset_ID,
    ],
    mergers: t.Mapping[str, Merger],
    cogset_groups: t.MutableMapping[
        types.Cognateset_ID, t.Sequence[types.Cognateset_ID]
    ],
    logger: cli.logging.Logger = cli.logger,
) -> t.Iterable[types.CogSet]:
    """Merge cognate sets in a dataset.

    TODO: Construct an example that shows that the order given in
    `cogset_groups` is maintained.

    Side Effects
    ============
    Changes cogset_groups:
        Groups that are skipped are removed

    """
    merge_targets = {
        variant: target
        for target, variants in cogset_groups.items()
        for variant in variants
    }
    for target in cogset_groups:
        assert merge_targets[target] == target

    c_s_id = dataset["CognatesetTable", "id"].name
    buffer: t.Dict[types.Cognateset_ID, types.CogSet] = {}

    unknown = set()
    cogset: types.CogSet
    for cogset in cli.tq(
        data["CognatesetTable"],
        task="Going through cognate sets and merging",
        logger=logger,
        total=data["CognatesetTable"].common_props.get("dc:extent"),
    ):
        id: types.Cognateset_ID = cogset[c_s_id]
        buffer[id] = cogset
        if id in merge_targets:
            unknown.add(id)
            target_id = merge_targets[id]
            group = cogset_groups[target_id]
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
                        f"Merging cognates set {id} with cognate sets {group} was skipped."
                    )
                    del cogset_groups[id]
                    pass
                for i in group:
                    unknown.remove(i)

        for f in list(buffer):
            if f in unknown:
                break
            yield buffer.pop(f)


if __name__ == "__main__":
    parser = cli.parser(
        __package__ + "." + Path(__file__).stem,
        description="Merge script for cognate sets.",
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
        help="Path pointing to the file containing the mergers, in the same format as output by report.nonconcatenative_morphemes",
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

    mergers: t.Dict[str, Merger] = dict(default_mergers)
    for column, merger in args.merge:
        # TODO: catch error of unkown merger, and generally treat this better
        mergers[column] = eval(merger)
    logger.debug(
        "The cognatet set merger was initialized as follows\n Column : merger function\n"
        + "\n".join("{}: {}".format(k, m.__name__) for k, m in mergers.items())
    )
    # Parse the homophones instructions!
    cogset_groups = parse_homophones_report(
        args.merge_file.open("r", encoding="utf8"),
    )
    if cogset_groups == defaultdict(list):
        cli.Exit.INVALID_INPUT(
            f"The provided report {args.merge_file} is empty or does not have the correct format."
        )

    dataset.write(
        CognatesetTable=list(
            merge_cogsets(
                data=dataset,
                mergers=mergers,
                cogset_groups=cogset_groups,
                logger=logger,
            )
        )
    )

    update_ids(
        dataset,
        dataset["CognatesetTable"],
        {
            old: target
            for target, olds in cogset_groups.items()
            for old in olds
            if target != old
        },
    )

    # TODO: merge duplicate judgements in CognateTable
    # TODO: something with alignments

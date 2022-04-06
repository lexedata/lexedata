"""Add trivial cognatesets

Make sure that every segment of every form is in at least one cognateset
(there can be more than one, eg. for nasalization), by creating singleton
cognatesets for streaks of segments not in cognatesets.

"""
import typing as t
from pathlib import Path

import pycldf

from lexedata import cli, types, util
from lexedata.report.nonconcatenative_morphemes import segment_to_cognateset
from lexedata.util import indices_to_segment_slice


def uncoded_segments(
    segment_to_cognateset: t.Mapping[types.Form_ID, t.List[t.Set[types.Cognateset_ID]]],
    logger: cli.logging.Logger = cli.logger,
) -> t.Iterator[t.Tuple[types.Form_ID, range]]:
    """Find the slices of uncoded segments.

    >>> list(uncoded_segments({"f1": [{}, {}, {"s1"}, {}]}))
    [('f1', range(0, 2)), ('f1', range(3, 4))]
    """
    for form, segments in segment_to_cognateset.items():
        if not all(segments):
            first_of_streak = None
            previous = None
            for i, cs in enumerate(segments):
                if cs:
                    continue
                if i - 1 == previous:
                    previous = i
                else:
                    if first_of_streak is not None:
                        yield form, range(first_of_streak, previous + 1)
                    first_of_streak = i
                    previous = i
            yield form, range(first_of_streak, previous + 1)


def uncoded_forms(
    forms: t.Iterable[types.Form], judged: t.Container[types.Form_ID]
) -> t.Iterator[t.Tuple[types.Form_ID, range]]:
    """Find the uncoded forms, and represent them as segment slices.

    >>> list(uncoded_forms([
    ...   {"id": "f1", "form": "ex", "segments": list("ex")},
    ...   {"id": "f2", "form": "test", "segments": list("test")},
    ... ], {"f1"}))
    [('f2', range(0, 4))]

    """
    for form in forms:
        if (
            form["id"] not in judged
            and form["form"]
            and form["form"].strip()
            and form["form"].strip() != "-"
        ):
            yield (form["id"], range(len(form["segments"])))


def create_singletons(
    dataset: types.Wordlist[
        types.Language_ID,
        types.Form_ID,
        types.Parameter_ID,
        types.Cognate_ID,
        types.Cognateset_ID,
    ],
    status: t.Optional[str] = None,
    by_segment: bool = False,
    logger: cli.logging.Logger = cli.logger,
) -> t.Tuple[t.Sequence[types.CogSet], t.Sequence[types.Judgement]]:
    """Create singleton cognate judgements for forms that don't have cognate judgements.

    Depending on by_segment, singletons are created for every range of segments
    that is not in any cognate set yet (True) or just for every form where no
    segment is in any cognate sets (False).

    """
    forms = util.cache_table(dataset)
    c_j_id = dataset["CognateTable", "id"].name
    c_j_cogset = dataset["CognateTable", "cognatesetReference"].name
    c_j_form = dataset["CognateTable", "formReference"].name
    try:
        c_j_segmentslice = dataset["CognateTable", "segmentSlice"].name
    except KeyError:
        c_j_segmentslice = None
    try:
        c_j_alignment = dataset["CognateTable", "alignment"].name
    except KeyError:
        c_j_alignment = None

    if not dataset.get(("CognatesetTable", "Status_Column")):
        logger.warning(
            "No Status_Column in CognatesetTable. I will proceed without. Run `lexedata.edit.add_status_column`` in default mode or with table-names CognatesetTable to add a Status_Column."
        )

    try:
        c_s_id = dataset["CognatesetTable", "id"].name
        all_cognatesets = {s[c_s_id]: s for s in dataset["CognatesetTable"]}
    except KeyError:
        c_s_id = "id"
        c_s_name = "name"
        all_cognatesets = {
            id: types.Judgement({"id": id, "name": id})
            for id in {j[c_j_cogset] for j in dataset["CognateTable"]}
        }
    try:
        c_s_name = dataset["CognatesetTable", "name"].name
    except KeyError:
        c_s_name = c_s_id

    all_judgements = list(dataset["CognateTable"])
    if by_segment:
        judgements = segment_to_cognateset(dataset, types.WorldSet(), logger)
        forms_and_segments = uncoded_segments(judgements, logger)
    else:
        forms_and_segments = uncoded_forms(
            forms.values(), {j[c_j_form] for j in all_judgements}
        )
    for form, slice in forms_and_segments:
        i = 1
        singleton_id = f"X_{form}_{i:d}"
        while singleton_id in all_cognatesets:
            i += 1
            singleton_id = f"X_{form}_{i:d}"
        all_cognatesets[singleton_id] = types.CogSet({})
        properties = {
            c_s_name: util.ensure_list(forms[form]["parameterReference"])[0],
            c_s_id: singleton_id,
            "Status_Column": status,
        }
        try:
            for column in dataset["CognatesetTable"].tableSchema.columns:
                all_cognatesets[singleton_id][column.name] = properties.get(column.name)
        except KeyError:
            pass
        judgement = types.Judgement({})
        properties = {
            c_j_id: singleton_id,
            c_j_cogset: singleton_id,
            c_j_form: form,
            c_j_segmentslice: indices_to_segment_slice(slice),
            c_j_alignment: [forms[form]["segments"][i] for i in slice],
            "Status_Column": status,
        }
        for column in dataset["CognateTable"].tableSchema.columns:
            judgement[column.name] = properties.get(column.name)
        all_judgements.append(judgement)
    return all_cognatesets.values(), all_judgements


if __name__ == "__main__":
    parser = cli.parser(
        __package__ + "." + Path(__file__).stem,
        description="Add singleton cognatesets to a CLDF dataset",
    )
    parser.add_argument(
        "--status",
        default=None,
        metavar="MESSAGE",
        help="For each part of a form that is not cognate coded, a singleton cognateset is created, and its status column (if there is one) is set to MESSAGE.",
    )
    parser.add_argument(
        "--by-segment",
        default=False,
        action="store_true",
        help="Instead of creating singleton cognate sets only for forms that are not cognate coded at all, make sure every contiguous set of segments in every form is in a cognate set.",
    )
    args = parser.parse_args()
    logger = cli.setup_logging(args)

    dataset = pycldf.Wordlist.from_metadata(args.metadata)
    try:
        cogsets = list(dataset["CognatesetTable"])
    except (KeyError):
        cli.Exit.INVALID_DATASET(
            "Dataset has no explicit CognatesetTable. Add one using `lexedata.edit.add_table CognatesetTable`."
        )

    all_cognatesets, all_judgements = create_singletons(
        dataset, status=args.status, by_segment=args.by_segment, logger=logger
    )

    dataset.write(
        CognatesetTable=all_cognatesets,
        CognateTable=all_judgements,
    )

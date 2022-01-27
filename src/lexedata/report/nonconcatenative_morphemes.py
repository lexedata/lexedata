import typing as t

import pycldf
import networkx.algorithms.community

from lexedata import cli, types, util
from lexedata.util import parse_segment_slices, indices_to_segment_slice


def segment_to_cognateset(
    dataset: types.Wordlist[
        types.Language_ID,
        types.Form_ID,
        types.Parameter_ID,
        types.Cognate_ID,
        types.Cognateset_ID,
    ],
    cognatesets: t.Optional[t.Container[types.Cognateset_ID]],
    logger: cli.logging.Logger = cli.logger,
    forms_by_cogset: t.Mapping[types.Cognateset_ID, t.List[t.Sequence[str]]] = {},
) -> t.Set[t.Tuple[types.Cognateset_ID, types.Cognateset_ID]]:
    # required fields
    c_cognate_cognateset = dataset.column_names.cognates.cognatesetReference
    c_form_segments = dataset.column_names.forms.segments
    c_cognate_id = dataset.column_names.cognates.id
    c_cognate_form = dataset.column_names.cognates.formReference
    c_cognate_slice = dataset.column_names.cognates.segmentSlice

    mergers: t.Set[t.Tuple[types.Cognateset_ID, types.Cognateset_ID]] = set()

    forms = util.cache_table(dataset)
    cognateset_cache: t.Container[types.Cognateset_ID]
    if "CognatesetTable" in dataset:
        c_s_id = dataset["CognatesetTable", "id"].name
        cognateset_cache = {
            cognateset[c_s_id]
            for cognateset in dataset["CognatesetTable"]
            if cognatesets is None or cognateset["ID"] in cognatesets
        }
    else:
        if cognatesets is None:
            cognateset_cache = types.WorldSet()
        else:
            cognateset_cache = cognatesets

    which_segment_belongs_to_which_cognateset: t.Dict[
        types.Form_ID, t.List[t.Set[types.Cognateset_ID]]
    ] = {}
    for j in dataset["CognateTable"]:
        if j[c_cognate_form] in forms and j[c_cognate_cognateset] in cognateset_cache:
            form = forms[j[c_cognate_form]]
            if j[c_cognate_form] not in which_segment_belongs_to_which_cognateset:
                which_segment_belongs_to_which_cognateset[j[c_cognate_form]] = [
                    set() for _ in form["segments"]
                ]
            if j.get(c_cognate_slice):
                try:
                    segments_judged = list(parse_segment_slices(j[c_cognate_slice]))
                except ValueError:
                    logger.warning(
                        f"In judgement {j[c_cognate_id]}, segment slice {j[c_cognate_slice]} has start after end."
                    )
                    continue
            else:
                segments_judged = list(range(len(form["segments"])))
            old_s = None
            already: t.MutableMapping[types.Cognateset_ID, t.List[int]] = t.DefaultDict(
                list
            )

            try:
                forms_by_cogset[j[c_cognate_cognateset]].append(
                    [
                        form["segments"][s] if 0 <= s < len(form["segments"]) else ""
                        for s in segments_judged
                    ]
                )
            except KeyError:
                # We are not supposed to add new keys. In this manner, a caller
                # can decide which cognatesets are interesting to them.
                pass

            for s in segments_judged:
                if old_s is not None and old_s + 1 != s:
                    logger.warning(
                        f"In judgement {j[c_cognate_id]}, segment {s+1} follows segment {old_s}, so the morpheme is non-contiguous"
                    )
                try:
                    cognatesets = which_segment_belongs_to_which_cognateset[
                        j[c_cognate_form]
                    ][s]
                except IndexError:
                    logger.warning(
                        f"In judgement {j[c_cognate_id]}, segment slice {j[c_cognate_slice]} points outside valid range 1:{len(form[c_form_segments])}."
                    )
                    continue
                for cs in cognatesets:
                    already[cs].append(s)
                cognatesets.add(j[c_cognate_cognateset])
            for cs, segments in already.items():
                segments_string = ",".join(indices_to_segment_slice(segments))
                logger.warning(
                    f"In judgement {j[c_cognate_id]}, segments {segments_string} are associated with cognate set {j[c_cognate_cognateset]}, but were already in {cs}."
                )
                if len(segments) >= len(segments_judged) / 2:
                    mergers.add((cs, j[c_cognate_cognateset]))

    return mergers


if __name__ == "__main__":
    parser = cli.parser(
        description="List segments that indicate non-concatenative morphology.",
        epilog="If you want a more general report on the cognate judgements, run `lexedata.report.judgements`.",
    )
    parser.add_argument(
        "--cognatesets",
        action=cli.ListOrFromFile,
        help="Only use these cognate sets as indication of overlapping morphemes.",
    )
    args = parser.parse_args()
    logger = cli.setup_logging(args)
    forms_by_cogset = t.DefaultDict(list)
    merge_pairs = segment_to_cognateset(
        dataset=pycldf.Dataset.from_metadata(args.metadata),
        cognatesets=args.cognatesets,
        logger=logger,
        forms_by_cogset=forms_by_cogset,
    )
    graph = networkx.Graph()
    graph.add_edges_from(merge_pairs)
    # Sort to keep order persistent
    for community in sorted(
        networkx.algorithms.community.greedy_modularity_communities(graph),
        key=lambda x: sorted(x),
    ):
        print("Cluster of overlapping cognate sets:")
        for cognateset in sorted(community):
            forms = ["".join(segments) for segments in forms_by_cogset[cognateset]]
            print(f"\t {cognateset} ({forms})")

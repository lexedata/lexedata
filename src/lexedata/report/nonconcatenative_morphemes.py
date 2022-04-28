import itertools
import sys
import typing as t
from pathlib import Path

import networkx.algorithms.community
import pycldf

from lexedata import cli, types, util
from lexedata.util import indices_to_segment_slice, parse_segment_slices


def segment_to_cognateset(
    dataset: types.Wordlist[
        types.Language_ID,
        types.Form_ID,
        types.Parameter_ID,
        types.Cognate_ID,
        types.Cognateset_ID,
    ],
    cognatesets: t.Container[types.Cognateset_ID],
    logger: cli.logging.Logger = cli.logger,
) -> t.Mapping[types.Form_ID, t.List[t.Set[types.Cognateset_ID]]]:
    # required fields
    c_cognate_cognateset = dataset.column_names.cognates.cognatesetReference
    c_cognate_id = dataset.column_names.cognates.id
    c_cognate_form = dataset.column_names.cognates.formReference
    c_cognate_slice = dataset.column_names.cognates.segmentSlice

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

    which_segment_belongs_to_which_cognateset: t.Mapping[
        types.Form_ID, t.List[t.Set[types.Cognateset_ID]]
    ] = {
        f: [set() for _ in form["segments"]]
        for f, form in forms.items()
        if form["form"] and form["form"].strip() and form["form"].strip() != "-"
    }
    for j in dataset["CognateTable"]:
        if j[c_cognate_form] in forms and j[c_cognate_cognateset] in cognateset_cache:
            form = forms[j[c_cognate_form]]
            if j[c_cognate_form] not in which_segment_belongs_to_which_cognateset:
                continue
            if j.get(c_cognate_slice):
                try:
                    segments_judged = list(parse_segment_slices(j[c_cognate_slice]))
                except ValueError:
                    logger.warning(
                        f"In judgement {j[c_cognate_id]}, segment slice {','.join(j[c_cognate_slice])} has start after end."
                    )
                    continue
            else:
                segments_judged = list(range(len(form["segments"])))
            old_s = None

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
                        f"In judgement {j[c_cognate_id]}, segment slice {','.join(j[c_cognate_slice])} points outside valid range 1:{len(form['segments'])}."
                    )
                    continue
                cognatesets.add(j[c_cognate_cognateset])

    return which_segment_belongs_to_which_cognateset


def network_of_overlaps(
    which_segment_belongs_to_which_cognateset: t.Mapping[
        types.Form_ID, t.List[t.Set[types.Cognateset_ID]]
    ],
    forms_cache: t.Optional[t.Mapping[types.Form_ID, types.Form]] = None,
) -> t.Set[t.Tuple[types.Cognateset_ID, types.Cognateset_ID]]:
    mergers: t.Set[t.Tuple[types.Cognateset_ID, types.Cognateset_ID]] = set()

    for form, cogsets in which_segment_belongs_to_which_cognateset.items():
        if [cs for cs in cogsets if len(cs) > 1]:
            logger.warning(
                f"In form {form}, segments are associated with multiple cognate sets."
            )
            for c1, c2 in itertools.combinations(sorted(set.union(*cogsets)), 2):
                s1 = {i for i, cs in enumerate(cogsets) if c1 in cs}
                s2 = {i for i, cs in enumerate(cogsets) if c2 in cs}
                if s1 & s2:
                    as_text = ",".join(indices_to_segment_slice(sorted(s1 & s2)))
                    if forms_cache:
                        as_text = "{} ({})".format(
                            as_text,
                            " ".join(
                                forms_cache.get(form)["segments"][i]
                                for i in sorted(s1 & s2)
                            ),
                        )
                    logger.info(
                        f"In form {form}, segments {as_text} are in both cognate sets {c1} and {c2}."
                    )
                    if len(s1 & s2) >= min(len(s1), len(s2)) / 2:
                        mergers.add((c1, c2))
    return mergers


def cluster_overlaps(
    overlapping_cognatesets: t.Iterable[
        t.Tuple[types.Cognateset_ID, types.Cognateset_ID]
    ],
    out=sys.stdout,
) -> None:
    graph = networkx.Graph()
    graph.add_edges_from(overlapping_cognatesets)
    if graph.nodes():
        communities = [
            community
            for comp in networkx.connected_components(graph)
            for community in networkx.algorithms.community.greedy_modularity_communities(
                graph.subgraph(comp)
            )
        ]
        # Sort to keep order persistent
        for community in sorted(
            communities,
            key=lambda x: sorted(x),
        ):
            print("Cluster of overlapping cognate sets:", file=out)
            for cognateset in sorted(community):
                print(f"\t {cognateset}", file=out)
                # TODO: Generate form segments, if considered informative
                # forms = ["".join(segments) for segments in forms_by_cogset[cognateset]]
                # print(f"\t {cognateset} ({forms})")


if __name__ == "__main__":
    parser = cli.parser(
        __package__ + "." + Path(__file__).stem,
        description="List segments that indicate non-concatenative morphology.",
        epilog="If you want a more general report on the cognate judgements, run `lexedata.report.judgements`.",
    )
    parser.add_argument(
        "--cognatesets",
        action=cli.SetOrFromFile,
        help="Only use these cognate sets as indication of overlapping morphemes.",
    )
    parser.add_argument(
        "--output-file",
        "-o",
        help="Path to output file (default: output to stdout)",
        type=Path,
    )

    args = parser.parse_args()
    logger = cli.setup_logging(args)
    dataset = pycldf.Dataset.from_metadata(args.metadata)
    which_segment_belongs_to_which_cognateset = segment_to_cognateset(
        dataset=dataset,
        cognatesets=args.cognatesets,
        logger=logger,
    )

    out = (
        args.output_file.open("w", encoding="utf-8") if args.output_file else sys.stdout
    )

    cluster_overlaps(
        network_of_overlaps(
            which_segment_belongs_to_which_cognateset,
            forms_cache=util.cache_table(dataset),
        ),
        out,
    )

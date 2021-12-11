import itertools
import typing as t

import pycldf

import lexedata.cli as cli
from lexedata.util import parse_segment_slices, indices_to_segment_slice
from lexedata import types


def segment_to_cognateset(
    dataset: types.Wordlist[
        types.Language_ID,
        types.Form_ID,
        types.Parameter_ID,
        types.Cognate_ID,
        types.Cognateset_ID,
    ],
    cognatesets: t.Optional[t.Iterable[types.Cognateset_ID]],
    logger: cli.logging.Logger = cli.logger,
):
    # required fields
    c_cognate_cognateset = dataset.column_names.cognates.cognatesetReference
    c_form_segments = dataset.column_names.forms.segments
    c_form_id = dataset.column_names.forms.id
    c_cognate_id = dataset.column_names.cognates.id
    c_cognate_form = dataset.column_names.cognates.formReference
    c_cognate_slice = dataset.column_names.cognates.segmentSlice

    forms = {f[c_form_id]: f for f in dataset["FormTable"]}
    cognateset_cache: t.Mapping[t.Optional[types.Cognateset_ID], int]
    if "CognatesetTable" in dataset:
        cognateset_cache = {
            cognateset["ID"]: c
            for c, cognateset in enumerate(dataset["CognatesetTable"], 1)
            if cognatesets is None or cognateset["ID"] in cognatesets
        }
    else:
        if cognatesets is None:
            cognateset_cache = t.DefaultDict(itertools.count().__next__)
        else:
            cognateset_cache = {c: i for i, c in enumerate(cognatesets, 1)}

    cognateset_cache[None] = 0

    which_segment_belongs_to_which_cognateset: t.Dict[
        str, t.List[t.Set[types.Cognateset_ID]]
    ] = {}
    for j in dataset["CognateTable"]:
        if j[c_cognate_form] in forms and cognateset_cache.get(j[c_cognate_cognateset]):
            form = forms[j[c_cognate_form]]
            if j[c_cognate_form] not in which_segment_belongs_to_which_cognateset:
                which_segment_belongs_to_which_cognateset[j[c_cognate_form]] = [
                    set() for _ in form[c_form_segments]
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
                segments_judged = list(range(len(form[c_form_segments])))
            old_s = None
            already: t.MutableMapping[types.Cognateset_ID, t.List[int]] = t.DefaultDict(
                list
            )
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
                    f"In judgement {j[c_cognate_id]}, segments {segments_string} are associated with cognate set {j[c_cognate_cognateset]}, but was already in {cognatesets}."
                )

    return which_segment_belongs_to_which_cognateset


if __name__ == "__main__":
    parser = cli.parser(
        description="List segments that indicate non-concatenative morphology "
    )
    parser.add_argument(
        "--cognatesets",
        type=str,
        nargs="*",
        default=None,
        help="",
    )
    args = parser.parse_args()
    logger = cli.setup_logging(args)
    segment_to_cognateset(
        dataset=pycldf.Dataset.from_metadata(args.metadata),
        cognatesets=args.cognatesets,
        logger=logger,
    )

import typing as t

import pycldf

import lexedata.cli as cli
from lexedata.util import parse_segment_slices


def segment_to_cognateset(
    dataset: pycldf.Dataset,
    cognatesets: t.Optional[t.Iterable],
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
    cognateset_cache: t.Dict[t.Optional[str], int] = {
        cognateset["ID"]: c
        for c, cognateset in enumerate(dataset["CognatesetTable"], 1)
        if cognatesets is None or cognateset["ID"] in cognatesets
    }
    cognateset_cache[None] = 0

    which_segment_belongs_to_which_cognateset: t.Dict[str, t.List[t.Set[str]]] = {}
    for j in dataset["CognateTable"]:
        if j[c_cognate_form] in forms and j[c_cognate_cognateset] in cognateset_cache:
            form = forms[j[c_cognate_form]]
            if j[c_cognate_form] not in which_segment_belongs_to_which_cognateset:
                which_segment_belongs_to_which_cognateset[j[c_cognate_form]] = [
                    set() for _ in form[c_form_segments]
                ]
            try:
                segments_judged = list(parse_segment_slices(j[c_cognate_slice]))
            except ValueError:
                logger.warning(
                    f"In judgement {j[c_cognate_id]}, segment slice {j[c_cognate_slice]} has start after end."
                )
                continue
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
                        f"In judgement {j[c_cognate_id]}, segment slice {j[c_cognate_slice]} points outside valid range 1:{len(form[c_form_segments])}."
                    )
                    continue
                if cognatesets:
                    logger.warning(
                        f"In judgement {j[c_cognate_id]}, segment {s+1} is associated with cognate set {j[c_cognate_cognateset]}, but was already in {cognatesets}."
                    )
                cognatesets.add(j[c_cognate_cognateset])

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

""" Add a CognateTable to the dataset.

If the dataset has a CognateTable, do nothing.
If the dataset has no cognatesetReference column anywhere, add an empty CognateTable.
If the dataset has a cognatesetReference in the FormTable, extract that to a separate cognateTable, also transferring alignments if they exist.
If the dataset has a cognatesetReference anywhere else, admit you don't know what is going on and die.
"""
from pathlib import Path

import pycldf

import typing as t
from lexedata import cli, util
from lexedata.util import cache_table, ensure_list

S = t.TypeVar("S")


def split_at_markers(
    segments: t.Sequence[S], markers: t.Container[S] = {"+", "_"}
) -> t.Tuple[t.Sequence[range], t.Sequence[t.Sequence[S]]]:
    """Split a list of segments at the markers.

    Return the segments without markers, and the sequence of morphemes (groups
    of segments between markers) in terms of indices into the segments result.

    >>> split_at_markers("test")
    [['t', 'e', 's', 't']]
    >>> split_at_markers("test+ing")
    [['t', 'e', 's', 't'], ['i', 'n', 'g']]
    >>> split_at_markers(["th"]+list("is is a test+i")+["ng"]+list(" example"), {" ", "+"})
    [['th', 'i', 's'], ['i', 's'], ['a'], ['t', 'e', 's', 't'], ['i', 'ng'], ['e', 'x', 'a', 'm', 'p', 'l', 'e']]
    """
    split = []
    start = 0
    i = 0
    for i, c in enumerate(segments):
        if c in markers:
            split.append([segments[j] for j in range(start, i)])
            start = i + 1
    split.append([segments[j] for j in range(start, len(segments))])
    return split


def morphemes(
    segments: t.Sequence[S], markers: t.Container[S] = {"+", "_"}
) -> t.Tuple[t.Sequence[range], t.Sequence[t.Sequence[S]]]:
    """Split a list of segments at the markers.

    Return the segments without markers, and the sequence of morphemes (groups
    of segments between markers) in terms of indices into the segments result.

    >>> morphemes("test")
    (['t', 'e', 's', 't'], [range(0, 4)])
    >>> morphemes("test+ing")
    (['t', 'e', 's', 't', 'i', 'n', 'g'], [range(0, 4), range(4, 7)])
    >>> s, r = morphemes(["th"]+list("is is a test+ing example"), {" ", "+"})
    >>> s[:3]
    ['th', 'i', 's']
    >>> r
    [range(0, 3), range(3, 5), range(5, 6), range(6, 10), range(10, 13), range(13, 20)]
    """
    split = split_at_markers(segments, markers)
    segment_slices = []
    segments = []
    start = 0
    for s in split:
        segment_slices.append(range(start, start + len(s)))
        start = start + len(s)
        segments.extend(s)
    return segments, segment_slices


def add_cognate_table(
    dataset: pycldf.Wordlist,
    split: bool = True,
    logger: cli.logging.Logger = cli.logger,
) -> int:
    """Add a cognate (judgment) table.

    split: bool
        Make sure that the same raw cognate code in different concepts gives
        rise to different cognate set ids, because raw cognate codes are not
        globally unique, only within each concept.

    Returns
    =======
    The number of partial cognate judgements in the new cognate table

    """
    if "CognateTable" in dataset:
        return
    dataset.add_component("CognateTable")

    # TODO: Check if that cognatesetReference is already a foreign key to
    # elsewhere (could be a CognatesetTable, could be whatever), because then
    # we need to transfer that knowledge.

    # Load anything that's useful for a cognate set table: Form IDs, segments,
    # segment slices, cognateset references, alignments
    cognate_judgements = []
    forms = cache_table(dataset)
    forms_without_segments = 0
    warned_about_morphemes = False
    warned_about_inconsistent_morphemes = False
    counter = 0
    for f, form in cli.tq(
        forms.items(), task="Extracting cognate judgements from forms…"
    ):
        if form.get("cognatesetReference"):
            if split:
                cogset = [
                    util.string_to_id("{:}-{:}".format(form["parameterReference"], c))
                    for c in ensure_list(form["cognatesetReference"])
                ]
            else:
                cogset = ensure_list(form["cognatesetReference"])
            if form.get("segmentSlice"):
                segment_slice = [
                    list(util.parse_segment_slices([s]))
                    for s in ensure_list(form.get("segmentSlice"))
                ]
            else:
                segment_slice = None
            if not form.get("segments"):
                forms_without_segments += 1
                if forms_without_segments < 5:
                    logger.warning(
                        f"No segments found for form {form['id']} ({form['form']}). Skipping its cognate judgements."
                    )
                continue
            else:
                if segment_slice is None:
                    form["segments"], segment_slice = morphemes(form["segments"])
                else:
                    # If we have got here, we have both segment slices given in
                    # the data and by '+'s in the segments. Check whether they
                    # are the same. But how? Should we assume that
                    # form["segmentSlice"] counts the "+"s or not? The least we
                    # can check is that they at least have the same length.
                    _, segment_slices = morphemes(form["segments"])

                    if not warned_about_morphemes:
                        logger.warning(
                            "You have morphemes with cognate codes specified in two ways: Your form table contains a #segmentSlice column, but also have morphemes separated using '+' in the form's segments. I will take the #segmentSlice value."
                        )
                        warned_about_morphemes = True
                    if not warned_about_inconsistent_morphemes and len(
                        segment_slice
                    ) != len(segment_slices):
                        logger.warning(
                            "You have *incompatible* morphemes between the #segmentSlice column, and the '+'s in the form's segments."
                        )
                        warned_about_inconsistent_morphemes = True
            if "alignment" not in form:
                alignments = [[form["segments"][a] for a in s] for s in segment_slice]
            else:
                alignments = split_at_markers(form["alignment"])

            if len(alignments) == len(cogset) == len(segment_slice):
                for cogset_id, segments, alignment in zip(
                    cogset, segment_slice, alignments
                ):
                    counter += 1
                    cognate_judgements.append(
                        {
                            "ID": f"{form['id']}-{cogset_id}",
                            "Form_ID": form["id"],
                            "Cognateset_ID": cogset_id,
                            "Segment_Slice": util.indices_to_segment_slice(segments),
                            "Alignment": alignment,
                        }
                    )
            elif len(cogset) == 1:
                (cogset_id,) = cogset
                counter += 1
                cognate_judgements.append(
                    {
                        "ID": f"{form['id']}-{cogset_id}",
                        "Form_ID": form["id"],
                        "Cognateset_ID": cogset_id,
                        "Segment_Slice": util.indices_to_segment_slice(
                            [s for r in segment_slice for s in r]
                        ),
                        "Alignment": sum(alignments, start=[]),
                    }
                )
            else:
                logger.warning(
                    f"In form {form['id']}, you had {len(cogset)} cognate judgements, but {len(alignments)} alignments and {len(segment_slice)} different morphemes or segment slices. I don't know how to deal with that discrepancy, so I skipped that form."
                )

    if forms_without_segments >= 5:
        logger.warning(
            "No segments found for %d forms. You can generate segments using `lexedata.edit.segment_using_clts`.",
            forms_without_segments,
        )

    # Delete the cognateset column
    cols = dataset["FormTable"].tableSchema.columns
    remove = {
        dataset["FormTable", c].name
        for c in ["cognatesetReference", "segmentSlice", "alignment"]
        if ("FormTable", c) in dataset
    }

    forms = [
        {
            dataset["FormTable", key].name: value
            for key, value in form.items()
            if key not in ["cognatesetReference", "segmentSlice", "alignment"]
        }
        for form in forms.values()
    ]
    for c in remove:
        ix = cols.index(dataset["FormTable", c])
        del cols[ix]

    dataset.write(FormTable=forms)
    dataset.write(CognateTable=cognate_judgements)

    return counter


if __name__ == "__main__":
    parser = cli.parser(__package__ + "." + Path(__file__).stem, __doc__)
    parser.add_argument(
        "--unique-id",
        choices=["dataset", "concept"],
        default=False,
        help="Are cognateset IDs unique over the whole *dataset* (including, but not limited to, cross-concept cognatesets), or are they unique only *within a concept* (eg. cognateset 1 for concept ‘hand’ is different than cognateset 1 for concept ‘to eat’",
    )
    args = parser.parse_args()
    logger = cli.setup_logging(args)

    split: bool
    if args.unique_id == "dataset":
        split = False
    elif args.unique_id == "concept":
        split = True
    else:
        cli.Exit.CLI_ARGUMENT_ERROR(
            "You must specify whether cognatesets have dataset-wide unique ids or not (--unique-id)"
        )

    dataset = pycldf.Wordlist.from_metadata(args.metadata)
    add_cognate_table(dataset, split=split)

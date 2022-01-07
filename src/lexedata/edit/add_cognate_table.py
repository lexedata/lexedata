""" Add a CognateTable to the dataset.

If the dataset has a CognateTable, do nothing.
If the dataset has no cognatesetReference column anywhere, add an empty CognateTable.
If the dataset has a cognatesetReference in the FormTable, extract that to a separate cognateTable, also transferring alignments if they exist.
If the dataset has a cognatesetReference anywhere else, admit you don't know what is going on and die.
"""

import pycldf


from lexedata.util import cache_table
from lexedata import cli
from lexedata import util


def add_cognate_table(
    dataset: pycldf.Wordlist,
    split: bool = True,
    logger: cli.logging.Logger = cli.logger,
) -> None:
    if "CognateTable" in dataset:
        return
    dataset.add_component("CognateTable")

    # TODO: Check if that cognatesetReference is already a foreign key to
    # elsewhere (could be a CognatesetTable, could be whatever), because then
    # we need to transfer that knowledge.

    # Load anything that's useful for a cognate set table: Form IDs, segments,
    # segment slices, cognateset references, alignments
    columns = {
        "id": dataset["FormTable", "id"].name,
        "concept": dataset["FormTable", "parameterReference"].name,
        "form": dataset["FormTable", "form"].name,
    }
    for property in ["segments", "segmentSlice", "cognatesetReference", "alignment"]:
        try:
            columns[property] = dataset["FormTable", property].name
        except KeyError:
            pass
    cognate_judgements = []
    forms = cache_table(dataset, columns=columns)
    forms_without_segments = 0
    for f, form in cli.tq(
        forms.items(), task="Extracting cognate judgements from forms…"
    ):
        if form.get("cognatesetReference"):
            if split:
                cogset = util.string_to_id(
                    "{:}-{:}".format(form["concept"], form["cognatesetReference"])
                )
            else:
                cogset = form["cognatesetReference"]
            judgement = {
                "ID": f,
                "Form_ID": f,
                "Cognateset_ID": cogset,
            }
            try:
                judgement["Segment_Slice"] = form["segmentSlice"]
            except KeyError:
                try:
                    if not form["segments"]:
                        raise ValueError("No segments")
                    if (
                        "+" in form["segments"]
                        and dataset["FormTable", "cognatesetReference"].separator
                    ):
                        logger.warning(
                            "You seem to have morpheme annotations in your cognates. I will probably mess them up a bit, because I have not been taught properly how to deal with them. Sorry!"
                        )
                    judgement["Segment_Slice"] = [
                        "1:{:d}".format(len(form["segments"]))
                    ]
                except (KeyError, TypeError, ValueError):
                    forms_without_segments += 1
                    if forms_without_segments >= 5:
                        pass
                    else:
                        logger.warning(
                            f"No segments found for form {f} ({form['form']})."
                        )
            # What does an alignment mean without segments or their slices?
            # Doesn't matter, if we were given one, we take it.
            judgement["Alignment"] = form.get("alignment")
            cognate_judgements.append(judgement)

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

    def clean_form(form):
        for c in remove:
            form.pop(c, None)
        return form

    forms = [clean_form(form) for form in dataset["FormTable"]]
    for c in remove:
        ix = cols.index(dataset["FormTable", c])
        del cols[ix]

    dataset.write(FormTable=forms)

    dataset.write(CognateTable=cognate_judgements)


if __name__ == "__main__":
    parser = cli.parser(__doc__)
    parser.add_argument(
        "--unique-id",
        choices=["dataset", "concept"],
        default=False,
        help="Are cognateset IDs unique over the whole *dataset* (including, but not limited to, cross-meaning cognatesets), or are they unique only *within a concept* (eg. cognateset 1 for concept ‘the hand’ has no relation cognateset 1 for concept ‘to eat’",
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
            "You must specify whether cognateset have dataset-wide unique ids or not (--unique-id)"
        )

    dataset = pycldf.Wordlist.from_metadata(args.metadata)
    add_cognate_table(dataset, split=split)

""" Add a CognateTable to the dataset.

If the dataset has a CognateTable, do nothing.
If the dataset has no cognatesetReference column anywhere, add an empty CognateTable.
If the dataset has a cognatesetReference in the FormTable, extract that to a separate cognateTable, also transferring alignments if they exist.
If the dataset has a cognatesetReference anywhere else, admit you don't know what is going on and die.
"""

import pycldf

from lexedata.util import cache_table
import lexedata.cli as cli


def add_explicit_cognateset_table(dataset: pycldf.Wordlist) -> None:
    if dataset["CognatesetTable"]:
        return
    dataset.add_component("CognatesetTable")

    c_cognateset = dataset["CognateTable", "cognatesetReference"].name

    cognatesets = set()
    for judgement in dataset["CognateTable"]:
        cognatesets.add(c_cognateset)

    dataset.write(CognatesetTable=[{"ID": id for id in sorted(cognatesets)}])


def add_cognate_table(dataset: pycldf.Wordlist) -> None:
    if dataset["CognateTable"]:
        return
    dataset.add_component("CognateTable")

    # TODO: Check if that cognatesetReference is already a foreign key
    # elsewhere, because then we need to transfer that knowledge.

    # Load anything that's useful for a cognate set table: Form IDs, segments,
    # segment slices, cognateset references, alignments
    columns = {"id": dataset["FormTable", "id"].name}
    for property in ["segments", "segmentSlice", "cognatesetReference", "alignment"]:
        try:
            columns[property] = dataset["FormTable", property].name
        except KeyError:
            pass
    cognate_judgements = []
    forms = cache_table(dataset, columns)
    for f, form in forms.items():
        if form.get("cognatesetReference"):
            judgement = {
                "ID": f,
                "Form_ID": f,
                "Cognateset_ID": form["cognatesetReference"],
            }
            try:
                judgement["Segment_Slice"] = form["segmentSlice"]
            except KeyError:
                try:
                    judgement["Segment_Slice"] = "1:{:d}".format(len(form["segments"]))
                except KeyError:
                    pass
            # What does an alignment mean without segments or their slices?
            # Doesn't matter, if we were given one, we take it.
            judgement["Alignment"] = form.get("alignment")
            cognate_judgements.append(judgement)

    add_explicit_cognateset_table(dataset)

    # TODO: Delete those moved columns
    dataset.write(CognateTable=cognate_judgements)


if __name__ == "__main__":
    parser = cli.parser(__doc__)
    args = parser.parse_args()

    add_cognate_table(pycldf.Dataset.from_metadata(args.metadata))

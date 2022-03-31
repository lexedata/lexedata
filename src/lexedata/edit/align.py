"""Automatically align morphemes within each cognateset.

If possible, align using existing lexstat scorer.

"""

import typing as t
from pathlib import Path

import pycldf

from lexedata import cli, util
from lexedata.edit.add_status_column import add_status_column_to_table


def align(forms):
    """‘Align’ forms by adding gap characters to the end.

    TODO: This is DUMB. Write a function that does this more sensibly, using
    LexStat scorers where available.

    """
    length = 0
    for (language, segments), metadata in forms:
        length = max(len(segments), length)

    for (language, segments), metadata in forms:
        yield segments + ["-"] * (length - len(segments)), metadata


def aligne_cognate_table(
    dataset: pycldf.Dataset, status_update: t.Optional[str] = None
):
    # add Status_Column if not existing – TODO: make configurable
    if status_update:
        add_status_column_to_table(dataset=dataset, table_name="CognateTable")

    forms = util.cache_table(dataset, "FormTable")

    c_id = dataset["CognateTable", "id"].name
    c_form_id = dataset["CognateTable", "formReference"].name
    c_cognateset_id = dataset["CognateTable", "cognatesetReference"].name
    c_slice = dataset["CognateTable", "segmentSlice"].name
    c_alignment = dataset["CognateTable", "alignment"].name

    cognatesets: t.Dict[str, t.List[t.Tuple[str, str, str, t.List[str]]]] = {}
    judgements: t.Dict[str, t.Dict[str, t.Any]] = {}
    for judgement in cli.tq(
        dataset["CognateTable"],
        task="Aligning the cognate segments",
        total=dataset["CognateTable"].common_props.get("dc:extent"),
    ):
        judgements[judgement[c_id]] = judgement
        form = forms[judgement[c_form_id]]
        morpheme = []
        if not judgement[c_slice]:
            morpheme = form["segments"]
        else:
            morpheme = [
                form["segments"][i]
                for i in util.parse_segment_slices(judgement[c_slice])
            ]
        cognatesets.setdefault(judgement[c_cognateset_id], []).append(
            ((form["languageReference"], morpheme), judgement[c_id])
        )

    for cognateset, morphemes in cognatesets.items():
        for alignment, id in align(morphemes):
            judgements[id][c_alignment] = alignment
            if status_update:
                judgements[id]["Status_Column"] = status_update
    dataset.write(CognateTable=judgements.values())


if __name__ == "__main__":

    parser = cli.parser(__package__ + "." + Path(__file__).stem, description=__doc__)
    parser.add_argument(
        "--status-update",
        type=str,
        default="automatically aligned",
        help="Text written to Status_Column. Set to 'None' for no status update. "
        "(default: automatically aligned)",
    )
    args = parser.parse_args()
    if args.status_update == "None":
        args.status_update = None
    aligne_cognate_table(
        pycldf.Wordlist.from_metadata(args.metadata), args.status_update
    )

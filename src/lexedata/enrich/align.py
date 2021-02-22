"""Automatically align morphemes within each cognateset

If possible, align using existing lexstat scorer.

"""

import typing as t
from pathlib import Path

import pycldf

from lexedata.enrich.add_status_column import add_status_column_to_table


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
    f_id = dataset["FormTable", "id"].name
    f_segments = dataset["FormTable", "segments"].name
    f_language = dataset["FormTable", "languageReference"].name
    # add Status_Column if not existing
    if status_update:
        add_status_column_to_table(dataset=dataset, table_name="CognateTable")

    forms = {}
    for form in dataset["FormTable"]:
        forms[form[f_id]] = form

    c_id = dataset["CognateTable", "id"].name
    c_form_id = dataset["CognateTable", "formReference"].name
    c_cognateset_id = dataset["CognateTable", "cognatesetReference"].name
    # TODO: how dos CognateTable get a segmentSlice column?
    c_slice = dataset["CognateTable", "segmentSlice"].name
    c_alignment = dataset["CognateTable", "alignment"].name

    cognatesets: t.Dict[str, t.List[t.Tuple[str, str, str, t.List[str]]]] = {}
    judgements: t.Dict[str, t.Dict[str, t.Any]] = {}
    for judgement in dataset["CognateTable"]:
        judgements[judgement[c_id]] = judgement
        form = forms[judgement[c_form_id]]
        morpheme = []
        if not judgement[c_slice]:
            morpheme = form[f_segments]
        for s in judgement[c_slice]:
            if ":" in s:
                i_, j_ = s.split(":")
                i, j = int(i_), int(j_)
            else:
                i = int(s)
                j = i + 1
            morpheme.extend(form[f_segments][slice(i, j)])
        cognatesets.setdefault(judgement[c_cognateset_id], []).append(
            ((form[f_language], morpheme), judgement[c_id])
        )

    for cognateset, morphemes in cognatesets.items():
        for alignment, id in align(morphemes):
            judgements[id][c_alignment] = alignment
            if status_update:
                judgement["Status_Column"] = status_update
    dataset["CognateTable"].write(judgements.values())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metadata",
        type=Path,
        default="Wordlist-metadata.json",
        help="Path to the JSON metadata file describing the dataset (default: ./Wordlist-metadata.json)",
    )
    parser.add_argument(
        "--status-update",
        type=str,
        default="Morphemes aligned",
        help="Text written to Status_Column. Set to 'None' for no status update. "
        "(default: Morphemes aligned)",
    )
    args = parser.parse_args()
    if args.status_update == "None":
        args.status_update = None
    aligne_cognate_table(
        pycldf.Wordlist.from_metadata(args.metadata), args.status_update
    )

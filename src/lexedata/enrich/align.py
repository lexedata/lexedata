"""Automatically align morphemes within each cognateset

If possible, align using existing lexstat scorer.

"""

import typing as t
from pathlib import Path

import pycldf


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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metadata",
        nargs="?",
        type=Path,
        default="Wordlist-metadata.json",
        help="Path to the metadata.json",
    )
    args = parser.parse_args()

    dataset = pycldf.Wordlist.from_metadata(args.metadata)

    f_id = dataset["FormTable", "id"].name
    f_segments = dataset["FormTable", "segments"].name
    f_language = dataset["FormTable", "languageReference"].name

    forms = {}
    for form in dataset["FormTable"]:
        forms[form[f_id]] = form

    c_id = dataset["CognateTable", "id"].name
    c_form_id = dataset["CognateTable", "formReference"].name
    c_cognateset_id = dataset["CognateTable", "cognatesetReference"].name
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

    dataset["CognateTable"].write(judgements.values())

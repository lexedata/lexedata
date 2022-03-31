"""Report the segment inventory of each language.


Report the phonemes (or whatever is represented by the #segments column) for
each language, each with frequencies and whether the segments are valid CLTS.
"""

import typing as t
from pathlib import Path

import pycldf
from tabulate import tabulate

from lexedata import cli, types
from lexedata.edit.add_segments import bipa


def count_segments(
    dataset: types.Wordlist[
        types.Language_ID,
        types.Form_ID,
        types.Parameter_ID,
        types.Cognate_ID,
        types.Cognateset_ID,
    ],
    languages: t.Container[types.Language_ID],
):
    c_f_language = dataset["FormTable", "languageReference"].name
    try:
        c_f_segments = dataset["FormTable", "segments"].name
    except KeyError:
        cli.Exit.NO_SEGMENTS(
            """Segment invertories report requires your dataset to have segments in the FormTable.
        Run `lexedata.edit.add_segments` to automatically add segments based on your forms."""
        )
    counter: t.MutableMapping[t.Counter[str]] = t.DefaultDict(t.Counter)
    for form in cli.tq(
        dataset["FormTable"],
        total=dataset["FormTable"].common_props.get("dc:extent"),
        task="Reading all forms",
    ):
        if form[c_f_language] in languages:
            counter[form[c_f_language]].update(form[c_f_segments])
    return counter


def comment_on_sound(sound: str) -> str:
    """Return a comment on the sound, if necessary.

    >>> comment_on_sound("a")
    ''
    >>> comment_on_sound("_")
    'Marker'
    >>> comment_on_sound("(")
    'Invalid BIPA'

    """
    if bipa[sound].type in {"vowel", "consonant", "tone"}:
        return ""
    if bipa[sound].type in {"marker"}:
        return "Marker"
    return "Invalid BIPA"


if __name__ == "__main__":
    parser = cli.parser(
        __package__ + "." + Path(__file__).stem,
        description=__doc__.split("\n\n\n")[0],
        epilog=__doc__.split("\n\n\n")[1],
    )
    parser.add_argument(
        "--languages",
        action=cli.SetOrFromFile,
        help="Restrict the report to these lanugage id(s).",
    )
    args = parser.parse_args()
    logger = cli.setup_logging(args)

    dataset = pycldf.Wordlist.from_metadata(args.metadata)

    counts = count_segments(dataset, args.languages)

    if len(counts) == 1:
        # A single language
        ((language, scounts),) = counts.items()
        print(language)
        print(
            tabulate(
                (
                    (sound, frequency, comment_on_sound(sound))
                    for sound, frequency in scounts.most_common()
                ),
                headers=["Sound", "Occurrences", "Comment"],
                tablefmt="orgtbl",
            )
        )
    else:
        # Extended report
        print(
            tabulate(
                (
                    (
                        language_id if s == 0 else "",
                        sound,
                        frequency,
                        comment_on_sound(sound),
                    )
                    for language_id, scounts in sorted(counts.items())
                    for s, (sound, frequency) in enumerate(scounts.most_common())
                ),
                headers=["Sound", "Occurrences", "Comment"],
                tablefmt="orgtbl",
            )
        )

"""Segment the form.


Take a form, in a phonemic transcription compatible with IPA, and split it into
phonemic segments, which are written back to the Segments column of the
FormTable. Segmentation essentially uses `CLTS`_, including diphthongs and affricates.


For details on the segmentation procedure, see the manual.

.. _CLTS: https://clts.clld.org/parameters
"""

import typing as t
from collections import defaultdict
from pathlib import Path

import attr
import cldfbench
import cldfcatalog
import pycldf
import pyclts
import segments
from csvw.metadata import URITemplate
from tabulate import tabulate

import lexedata.cli as cli

try:
    with cldfcatalog.Catalog.from_config("clts", tag="v2.0.0"):
        clts_path = cldfcatalog.Config.from_file().get_clone("clts")
        clts = cldfbench.catalogs.CLTS(clts_path)
        bipa = clts.api.bipa
except (ValueError, KeyError):  # pragma: no cover
    # Make a temporary clone of CLTS. Mostly useful for ReadTheDocs.
    cli.logging.warning(
        "Failed to read the CLTS catalog. This script cannot be processed without that catalog, so I'm falling back to a manual clone of the repository. Please check your CLDF catalogs using `cldbench catinfo`, and consider installing CLTS using `cldfbench catconfig`."
    )
    import os
    from tempfile import mkdtemp

    clts_path = mkdtemp("clts")
    os.system(
        f"git clone -b v2.0.0 --depth 1 https://github.com/cldf-clts/clts.git '{clts_path}'"
    )
    clts = cldfbench.catalogs.CLTS(clts_path)
    bipa = clts.api.bipa

tokenizer = segments.Tokenizer()


@attr.s(auto_attribs=True)
class ReportEntry:
    count: int = 0
    comment: str = ""


@attr.s(auto_attribs=True)
class SegmentReport:
    sounds: t.MutableMapping[str, ReportEntry] = attr.ib(
        factory=lambda: defaultdict(ReportEntry)
    )

    def __call__(self, name: str) -> t.List[t.Tuple[str, str, int, str]]:
        res = []
        for k, v in self.sounds.items():
            res.append((name, k, v.count, v.comment))
        return res


def cleanup(form: str) -> str:
    """
    >>> cleanup("dummy;form")
    'dummy'
    >>> cleanup("dummy,form")
    'dummy'
    >>> cleanup("(dummy)")
    'dummy'
    >>> cleanup("dummy-form")
    'dummy+form'
    """
    form = form.split(";")[0].strip()
    form = form.split(",")[0].strip()
    form = form.replace("(", "").replace(")", "")
    form = form.replace("-", "+")
    return form


pre_replace = {
    "l̴": str(bipa["voiceless alveolar lateral fricative consonant"]),
    "˺": "̚",
    "ˑ": ".",
    "oː́": str(bipa["long rounded close-mid back with-high_tone vowel"]),
    "\u2184": str(bipa["rounded open-mid back vowel"]),
    # LATIN SMALL LETTER REVERSED C, instead of LATIN SMALL LETTER OPEN O
    "Ɂ": str(bipa["voiceless glottal stop consonant"]),
    # "?": str(bipa["voiceless glottal stop consonant"]),
    # But this could also be marking an unknown sound – maybe the recording is messy
    # "'": "ˈ",
    # But this could also be marking ejective consonants, so don't guess
    "͡ts": str(bipa["voiceless alveolar sibilant affricate consonant"]),
    "ts͡": str(bipa["voiceless alveolar sibilant affricate consonant"]),
    "ts͜": str(bipa["voiceless alveolar sibilant affricate consonant"]),
    "͜ts": str(bipa["voiceless alveolar sibilant affricate consonant"]),
    "tʃ͡": str(bipa["voiceless post-alveolar sibilant affricate consonant"]),
    "͡tʃ": str(bipa["voiceless post-alveolar sibilant affricate consonant"]),
    "t͡ç": str(bipa["voiceless palatal affricate consonan"]),
}


def segment_form(
    formstring: str,
    report: SegmentReport,
    system=bipa,
    split_diphthongs: bool = True,
    context_for_warnings: str = "",
    logger: cli.logging.Logger = cli.logger,
) -> t.Iterable[pyclts.models.Symbol]:
    """Segment the form.

    First, apply some pre-processing replacements. Forms supplied contain all
    sorts of noise and lookalike symbols. This function comes with reasonable
    defaults, but if you encounter other problems, or you actually want to be
    strict about IPA transcriptions, pass a dictionary of your choice as
    `pre_replace`.

    Then, naïvely segment the form using the IPA tokenizer from the `segments`
    package. Check each returned segment to see whether it is valid according
    to CLTS's BIPA, and if not, try to fix some issues (in particular
    pre-aspirated or pre-nasalized consonants showing up as post-aspirated
    resp. post-nasalized vowels, which BIPA does not accept).

    >>> [str(x) for x in segment_form("iɾũndɨ", report=SegmentReport())]
    ['i', 'ɾ', 'ũ', 'n', 'd', 'ɨ']
    >>> [str(x) for x in segment_form("mokõi", report=SegmentReport())]
    ['m', 'o', 'k', 'õ', 'i']
    >>> segment_form("pan̥onoót͡síkoːʔú", report=SegmentReport())  # doctest: +ELLIPSIS
    [<pyclts.models.Consonant: voiceless bilabial stop consonant>, <pyclts.models.Vowel: unrounded open front vowel>, <pyclts.models.Consonant: devoiced voiced alveolar nasal consonant>, <pyclts.models.Vowel: rounded close-mid back vowel>, <pyclts.models.Consonant: voiced alveolar nasal consonant>, <pyclts.models.Vowel: rounded close-mid back vowel>, <pyclts.models.Vowel: rounded close-mid back ... vowel>, <pyclts.models.Consonant: voiceless alveolar sibilant affricate consonant>, <pyclts.models.Vowel: unrounded close front ... vowel>, <pyclts.models.Consonant: voiceless velar stop consonant>, <pyclts.models.Vowel: long rounded close-mid back vowel>, <pyclts.models.Consonant: voiceless glottal stop consonant>, <pyclts.models.Vowel: rounded close back ... vowel>]

    """
    # and with the syllable boundary marker '.', so we wrap it with special cases for those.
    raw_tokens = [
        system[s]
        for s in tokenizer(
            formstring,
            ipa=True,
        ).split()
    ]
    if system != bipa:
        for r in raw_tokens:
            if r.type == "unknownsound":
                logger.warning(
                    f"{context_for_warnings}Unknown sound encountered in {formstring:}"
                )
                report.sounds[str(r)].count += 1
                report.sounds[str(r)].comment = "unknown sound"
    i = len(raw_tokens) - 1
    while i >= 0:
        if split_diphthongs and raw_tokens[i].type == "diphthong":
            raw_tokens[i : i + 1] = [raw_tokens[i].from_sound, raw_tokens[i].to_sound]
            i += 1
            continue
        if raw_tokens[i].type != "unknownsound":
            i -= 1
            continue
        if raw_tokens[i].source == "/":
            report.sounds[str(raw_tokens[i])].count += 1
            report.sounds[str(raw_tokens[i])].comment = "illegal symbol"
            del raw_tokens[i]
            logger.warning(
                f"{context_for_warnings}Impossible sound '/' encountered in {formstring} – "
                f"You cannot use CLTS extended normalization "
                f"with this script. The slash was skipped and not included in the segments."
            )
            i -= 1
            continue
        grapheme = raw_tokens[i].grapheme
        if grapheme in {".", "-"}:
            del raw_tokens[i]
            i -= 1
            continue
        if grapheme == "ː":
            del raw_tokens[i]
            try:
                raw_tokens[i - 1] = bipa["long " + raw_tokens[i - 1].name]
            except TypeError:
                raw_tokens[i - 1].grapheme += "ː"
            i -= 1
            continue
        if grapheme.endswith("ⁿ") or grapheme.endswith("ᵐ") or grapheme.endswith("ᵑ"):
            if (
                i + 1 > len(raw_tokens) - 1
                or not hasattr(raw_tokens[i + 1], "preceding")
                or raw_tokens[i + 1].preceding is not None
            ):
                logger.warning(
                    f"{context_for_warnings}Unknown sound {raw_tokens[i]} encountered in {formstring}"
                )
                report.sounds[str(raw_tokens[i])].count += 1
                report.sounds[str(raw_tokens[i])].comment = "unknown pre-nasalization"
                i -= 1
                continue
            raw_tokens[i + 1] = bipa["pre-nasalized " + raw_tokens[i + 1].name]
            raw_tokens[i] = bipa[grapheme[:-1]]
            continue
        if grapheme.endswith("ʰ"):
            if (
                i + 1 > len(raw_tokens) - 1
                or not hasattr(raw_tokens[i + 1], "preceding")
                or raw_tokens[i + 1].preceding is not None
            ):
                logger.warning(
                    f"{context_for_warnings}Unknown sound {raw_tokens[i]} encountered in {formstring}"
                )
                report.sounds[str(raw_tokens[i])].count += 1
                report.sounds[str(raw_tokens[i])].comment = "unknown pre-aspiration"
                i -= 1
                continue
            raw_tokens[i + 1] = bipa["pre-aspirated " + raw_tokens[i + 1].name]
            raw_tokens[i] = bipa[grapheme[:-1]]
            continue
        logger.warning(
            f"{context_for_warnings}Unknown sound {raw_tokens[i]} encountered in {formstring}"
        )
        report.sounds[str(raw_tokens[i])].count += 1
        report.sounds[str(raw_tokens[i])].comment = "unknown sound"
        i -= 1

    return raw_tokens


def add_segments_to_dataset(
    dataset: pycldf.Dataset,
    transcription: str,
    overwrite_existing: bool,
    replace_form: bool,
    logger: cli.logging.Logger = cli.logger,
):
    if dataset.column_names.forms.segments is None:
        # Create a Segments column in FormTable
        dataset.add_columns("FormTable", "Segments")
        c = dataset["FormTable"].tableSchema.columns[-1]
        c.separator = " "
        c.propertyUrl = URITemplate("http://cldf.clld.org/v1.0/terms.rdf#segments")
        dataset.write_metadata()

    write_back = []
    c_f_segments = dataset["FormTable", "segments"].name
    c_f_id = dataset["FormTable", "id"].name
    c_f_lan = dataset["FormTable", "languageReference"].name
    c_f_form = dataset["FormTable", "form"].name
    # report = t.Dict[str, t.Dict[str, t.Dict[str, str]]] = {}
    report = {f[c_f_lan]: SegmentReport() for f in dataset["FormTable"]}
    for r, row in cli.tq(
        enumerate(dataset["FormTable"], 1),
        task="Writing forms with segments to dataset",
        total=dataset["FormTable"].common_props.get("dc:extent"),
    ):
        if row[c_f_segments] and not overwrite_existing:
            write_back.append(row)
            continue
        else:
            if row[transcription] is None or row[transcription] == "-":
                row[dataset.column_names.forms.segments] = ""
            elif row[transcription]:
                form = row[transcription].strip()
                for wrong, right in pre_replace.items():
                    if wrong in form:
                        report[row[c_f_lan]].sounds[wrong].count += form.count(wrong)
                        report[row[c_f_lan]].sounds[
                            wrong
                        ].comment = f"'{wrong}' replaced by '{right}' in segments"
                        form = form.replace(wrong, right)
                        # also replace symbol in #FormTable *form
                        if replace_form:
                            row[c_f_form] = row[c_f_form].replace(wrong, right)
                            report[row[c_f_lan]].sounds[wrong].comment += " and forms."
                        else:
                            report[row[c_f_lan]].sounds[
                                wrong
                            ].comment += ". Run with `--replace-form` to apply this also to the forms."
                row[dataset.column_names.forms.segments] = segment_form(
                    form,
                    report=report[row[c_f_lan]],
                    context_for_warnings=f"In form {row[c_f_id]} (line {r}): ",
                    logger=logger,
                )
            write_back.append(row)
    dataset.write(FormTable=write_back)
    return report


if __name__ == "__main__":
    parser = cli.parser(
        __package__ + "." + Path(__file__).stem,
        description=__doc__.split("\n\n\n")[0],
        epilog=__doc__.split("\n\n\n")[1],
    )
    parser.add_argument(
        "transcription_column",
        nargs="?",
        default=None,
        help="Column containing the IPA transcriptions. Default: The CLDF #form column",
        metavar="TRANSCRIPTION_COLUMN",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Overwrite #segments values already given in the dataset",
    )

    parser.add_argument(
        "--replace-form",
        action="store_true",
        default=False,
        help="Apply the replacements performed on segments also to #form column of #FormTable",
    )
    args = parser.parse_args()
    logger = cli.setup_logging(args)

    dataset = pycldf.Wordlist.from_metadata(args.metadata)

    if args.transcription_column is None:
        args.transcription_column = dataset.column_names.forms.form
    # add segments to FormTable
    report = add_segments_to_dataset(
        dataset,
        args.transcription_column,
        args.overwrite,
        args.replace_form,
        logger=logger,
    )
    data = []
    for lan, segment_report in report.items():
        data.extend(segment_report(lan))

    print(
        tabulate(
            data,
            headers=["LanguageID", "Sound", "Occurrences", "Comment"],
            tablefmt="orgtbl",
        )
    )

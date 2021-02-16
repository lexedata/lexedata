import logging
import argparse
import typing as t
from pathlib import Path

from csvw.metadata import URITemplate

import pycldf
import pyclts
import segments
import cldfbench
import cldfcatalog

clts_path = cldfcatalog.Config.from_file().get_clone("clts")
clts = cldfbench.catalogs.CLTS(clts_path)
bipa = clts.api.bipa

tokenizer = segments.Tokenizer()


def cleanup(form: str) -> str:
    form = form.split(";")[0].strip()
    form = form.split(",")[0].strip()
    form = form.replace("(", "").replace(")", "")
    form = form.replace("-", "+")
    return form


pre_replace = {
    "l̴": "ɬ",
    ".": ".",
    "˺": "̚",
    "ˑ": ".",
    "oː́": "oó",
    "Ɂ": "ʔ",
    # "?": "ʔ",  # But this could also be marking an unknown sound – maybe the recording is messy
    # "'": "ˈ",  # But this could also be marking ejective consonants, so don't guess
    "͡ts": "t͡s",
    "ts͡": "t͡s",
    "tʃ͡": "t͡ʃ",
    "͡tʃ": "t͡ʃ",
    "t͡ç": "c͡ç",
}


def segment_form(
    formstring: str, system=bipa, pre_replace=pre_replace, split_diphthongs: bool = True
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

    >>> [str(x) for x in segment_form("iɾũndɨ")]
    ['i', 'ɾ', 'ũ', 'n', 'd', 'ɨ']
    >>> [str(x) for x in segment_form("mokõi")]
    ['m', 'o', 'k', 'õ', 'i']
    >>> segment_form("pan̥onoː́t͡síkoːʔú")
    [<pyclts.models.Consonant: voiceless bilabial stop consonant>, <pyclts.models.Vowel: unrounded open front vowel>, <pyclts.models.Consonant: devoiced voiced alveolar nasal consonant>, <pyclts.models.Vowel: rounded close-mid back vowel>, <pyclts.models.Consonant: voiced alveolar nasal consonant>, <pyclts.models.Vowel: rounded close-mid back vowel>, <pyclts.models.Vowel: rounded close-mid back with_high_tone vowel>, <pyclts.models.Consonant: voiceless alveolar sibilant affricate consonant>, <pyclts.models.Vowel: unrounded close front with_high_tone vowel>, <pyclts.models.Consonant: voiceless velar stop consonant>, <pyclts.models.Vowel: long rounded close-mid back vowel>, <pyclts.models.Consonant: voiceless glottal stop consonant>, <pyclts.models.Vowel: rounded close back with_high_tone vowel>]

    """
    # and with the syllable boundary marker '.', so we wrap it with special cases for those.
    for wrong, right in pre_replace.items():
        formstring = formstring.replace(wrong, right)
    raw_tokens = [
        system[s]
        for s in tokenizer(
            formstring,
            ipa=True,
        ).split()
    ]
    if system != bipa:
        if any(r.type == "unknownsound" for r in raw_tokens):
            logging.warning(f"Unknown sound encountered in {formstring:}")
        return raw_tokens
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
            del raw_tokens[i]
            logging.warning(
                "Impossible sound / encountered in {:} – You cannot use CLTS extended normalization with this script. The slash was not taken over into the segments.".format(
                    formstring
                )
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
            if raw_tokens[i + 1].preceding is not None:
                logging.warning(
                    "Unknown sound {:} encountered in {:}".format(
                        raw_tokens[i], formstring
                    )
                )
                i -= 1
                continue
            raw_tokens[i + 1] = bipa["pre-nasalized " + raw_tokens[i + 1].name]
            raw_tokens[i] = bipa[grapheme[:-1]]
            continue
        if grapheme.endswith("ʰ"):
            if raw_tokens[i + 1].preceding is not None:
                logging.warning(
                    "Unknown sound {:} encountered in {:}".format(
                        raw_tokens[i], formstring
                    )
                )
                i -= 1
                continue
            raw_tokens[i + 1] = bipa["pre-aspirated " + raw_tokens[i + 1].name]
            raw_tokens[i] = bipa[grapheme[:-1]]
            continue
        logging.warning(
            "Unknown sound {:} encountered in {:}".format(raw_tokens[i], formstring)
        )
        i -= 1
    return raw_tokens


def add_segments_to_dataset(
    dataset: pycldf.Dataset, transcription: str, overwrite_existing: bool
):
    if dataset.column_names.forms.segments is None:
        # Create a Segments column in FormTable
        dataset.add_columns("FormTable", "Segments")
        c = dataset["FormTable"].tableSchema.columns[-1]
        c.separator = " "
        c.propertyUrl = URITemplate("http://cldf.clld.org/v1.0/terms.rdf#segments")
        dataset.write_metadata()

    write_back = []
    c_f_segments = dataset["FormTable", "Segments"].name
    for row in dataset["FormTable"]:
        if row[c_f_segments] and not overwrite_existing:
            continue
        else:
            if row[transcription]:
                form = row[transcription].strip()
                row[dataset.column_names.forms.segments] = segment_form(form)
            write_back.append(row)
    dataset.write(FormTable=write_back)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--metadata",
        nargs="?",
        type=Path,
        default="Wordlist-metadata.json",
        help="Path to the metadata.json. The metadata file describes the dataset. Default: ./Wordlist-metadata.json. "
        "Segments will be added to the segments column of the formTable of this dataset.",
    )
    parser.add_argument(
        "transcription",
        nargs="?",
        default=None,
        help="Column containing the IPA transcriptions. Default: The CLDF #form column",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Overwrite #segments values already given in the dataset",
    )
    args = parser.parse_args()

    dataset = pycldf.Wordlist.from_metadata(args.metadata)

    if args.transcription is None:
        args.transcription = dataset.column_names.forms.form
    # add segments to FormTable
    add_segments_to_dataset(dataset, args.transcription, args.overwrite)

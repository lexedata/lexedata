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


def segment_form(form: str) -> t.Iterable[pyclts.models.Symbol]:
    if "." in form:
        return [s for f in form.split(".") for s in segment_form(f)]
    segments = [
        bipa[c] for c in tokenizer(bipa.normalize(cleanup(form)), ipa=True).split()
    ]
    for s, segment in enumerate(segments):
        if segment.type == "unknownsound":
            logging.warning(
                "Unknown sound '%s' in form '%s' (segment #%d)", segment, form, s + 1
            )
    segments = [str(s) for s in segments]
    return segments


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Adds #segments to the #formTable and segment column if not existing."
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default="Wordlist-metadata.json",
        help="Path to the JSON metadata file describing the dataset (default: ./Wordlist-metadata.json)",
    )
    parser.add_argument(
        "transcription",
        nargs="?",
        default=None,
        help="Column containing the IPA transcriptions (default: The CLDF #form column)",
    )
    args = parser.parse_args()

    dataset = pycldf.Wordlist.from_metadata(args.wordlist)

    if args.transcription is None:
        args.transcription = dataset.column_names.forms.form

    if dataset.column_names.forms.segments is None:
        # Create a concepticonReference column
        dataset.add_columns("FormTable", "Segments")
        c = dataset["FormTable"].tableSchema.columns[-1]
        c.separator = " "
        c.propertyUrl = URITemplate("http://cldf.clld.org/v1.0/terms.rdf#segments")
        dataset.write_metadata()

    print(dataset.column_names.forms.segments)

    write_back = []
    for row in dataset["FormTable"]:
        if row[args.transcription]:
            form = row[args.transcription].strip()
            if row[dataset.column_names.forms.segments]:
                pass
            else:
                row[dataset.column_names.forms.segments] = segment_form(form)
        write_back.append(row)
    dataset.write(FormTable=write_back)

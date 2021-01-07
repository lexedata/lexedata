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
    """
    :param form:
    :return:
    ----------
    >>> segment_form("iɾũndɨ") == ["i", "ɾ", "ũ", "n", "d", "ɨ"]
    True
    >>> segment_form("mokõi") == ["m", "o", "k", "õ", "i"]
    True
    """
    if "." in form:
        return [s for f in form.split(".") for s in segment_form(f)]
    segments = [
        bipa[c] for c in tokenizer(bipa.normalize(cleanup(form)), ipa=True).split()
    ]
    for s, segment in enumerate(segments):
        if segment.type == "unknownsound":
            logging.warning(
                "Unknown sound '%s' in form '%s' (segment #%d). "
                "Sound was added unchanged to segments.", segment, form, s + 1
            )
    segments = [str(s) for s in segments]
    return segments


def add_segments_to_dataset(dataset: pycldf.Dataset, transcription: str, overwrite_existing: bool):
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
        help="Overwrite segments already given in the dataset",
    )
    args = parser.parse_args()

    dataset = pycldf.Wordlist.from_metadata(args.wordlist)

    if args.transcription is None:
        args.transcription = dataset.column_names.forms.form
    # add segments to FormTable
    add_segments_to_dataset(dataset, args.transcription, args.overwrite_existing)
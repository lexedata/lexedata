"""Similarity code tentative cognates in a word list and align them"""

import csv
import hashlib
import typing as t
from pathlib import Path

import lingpy
import lingpy.compare.partial
import pycldf
import pyclts
import segments

import lexedata.cli as cli
import lexedata.types as types
from lexedata.edit.add_segments import bipa

# TODO maybe the CLTS logic from here and there belongs in util?

tokenizer = segments.Tokenizer()


def sha1(path):
    return hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:12]


def clean_segments(segment_string: t.List[str]) -> t.Iterable[pyclts.models.Symbol]:
    """Reduce the row's segments to not contain empty morphemes.

    This function removes all unknown sound segments (/0/) from the segments
    string it is passed, and removes empty morphemes by collapsing subsequent
    morpheme boundary markers (_#◦+→←) into one.

    >>> segments = "+ _ t a + 0 + a t"
    >>> c = clean_segments(segments)
    >>> [str(s) for s in c]
    ['t', 'a', '+', 'a', 't']

    """
    segments = [bipa[x] for x in segment_string]
    segments.insert(0, bipa["#"])
    segments.append(bipa["#"])
    for s in range(len(segments) - 1, 0, -1):
        if not pyclts.models.is_valid_sound(segments[s - 1], bipa):
            if isinstance(segments[s - 1], pyclts.models.Marker) and isinstance(
                segments[s], pyclts.models.Marker
            ):
                del segments[s - 1]
            if isinstance(segments[s - 1], pyclts.models.UnknownSound):
                del segments[s - 1]
            continue
    return segments[1:-1]


def filter_function_factory(
    dataset: types.Wordlist,
) -> t.Callable[[t.Dict[str, t.Any]], bool]:
    def filter(row: t.Dict[str, t.Any]) -> bool:
        row["tokens"] = [
            str(x)
            for x in clean_segments(row[dataset.column_names.forms.segments.lower()])
        ]
        row["tokens"] = ["+" if x == "_" else x for x in row["tokens"]]
        # TODO: Find the official LingPy way to consider word boundaries to
        # also be morpheme boundaries – just adding them in
        # `partial_cluster(sep=...+'_')` did not work, and why isn't it the
        # default anyway?
        row["doculect"] = row[dataset.column_names.forms.languageReference.lower()]
        row["concept"] = row[dataset.column_names.forms.parameterReference.lower()]
        return row["segments"] and row["concept"]

    return filter


def cognate_code_to_file(
    metadata: Path,
    ratio: float,
    soundclass: str,
    cluster_method: str,
    threshold: float,
    initial_threshold: float,
    gop: float,
    mode: str,
    output_file: Path,
) -> None:
    dataset = pycldf.Wordlist.from_metadata(metadata)
    assert (
        dataset.column_names.forms.segments is not None
    ), "Dataset must have a CLDF #segments column."

    lex = lingpy.compare.partial.Partial.from_cldf(
        metadata,
        filter=filter_function_factory(dataset),
        columns=["doculect", "concept", "tokens"],
        model=lingpy.data.model.Model(soundclass),
        check=True,
    )

    if ratio != 1.5:
        if ratio == float("inf"):
            ratio_pair = (1, 0)
            ratio_str = "-inf"
        if ratio == int(ratio) >= 0:
            r = int(ratio)
            ratio_pair = (r, 1)
            ratio_str = "-{:d}".format(r)
        elif ratio > 0:
            ratio_pair = (ratio, 1)
            ratio_str = "-" + str(ratio)
        else:
            raise ValueError("LexStat ratio must be in [0, ∞]")
    else:
        ratio_pair = (3, 2)
        ratio_str = ""
    if initial_threshold != 0.7:
        ratio_str += "-t{:02d}".format(int(initial_threshold * 100))
    try:
        scorers_etc = lingpy.compare.lexstat.LexStat(
            filename="lexstats-{:}-{:s}{:s}.tsv".format(
                sha1(metadata), soundclass, ratio_str
            )
        )
        lex.scorer = scorers_etc.scorer
        lex.cscorer = scorers_etc.cscorer
        lex.bscorer = scorers_etc.bscorer
    except (OSError, ValueError):
        lex.get_scorer(runs=10000, ratio=ratio_pair, threshold=initial_threshold)
        lex.output(
            "tsv",
            filename="lexstats-{:}-{:s}{:s}".format(
                sha1(metadata), soundclass, ratio_str
            ),
            ignore=[],
        )
    # For some purposes it is useful to have monolithic cognate classes.
    lex.cluster(
        method="lexstat",
        threshold=threshold,
        ref="cogid",
        cluster_method=cluster_method,
        verbose=True,
        override=True,
        gop=gop,
        mode=mode,
    )
    # But actually, in most cases partial cognates are much more useful.
    lex.partial_cluster(
        method="lexstat",
        threshold=threshold,
        cluster_method=cluster_method,
        ref="partialcognateids",
        override=True,
        verbose=True,
        gop=gop,
        mode=mode,
    )
    lex.output("tsv", filename="auto-clusters")
    alm = lingpy.Alignments(lex, ref="partialcognateids", fuzzy=True)
    alm.align(method="progressive")
    alm.output("tsv", filename=str(output_file), ignore="all", prettify=False)

    try:
        dataset.add_component("CognateTable")
    except ValueError:
        ...
    try:
        dataset.add_component("CognatesetTable")
    except ValueError:
        ...

    read_back = csv.DictReader(
        open(str(output_file) + ".tsv", encoding="utf-8"), delimiter="\t"
    )
    cognatesets = {}
    judgements = []
    i = 1
    for line in read_back:
        partial = line["PARTIALCOGNATEIDS"].split()
        alignment = line["ALIGNMENT"].split(" + ")
        slice_start = 0
        for cs, alm in zip(partial, alignment):
            # TODO: @Gereon: is it alright to add the same content to Name and ID?
            cognatesets.setdefault(cs, {"ID": cs, "Name": cs})
            length = len(alm.split())
            judgements.append(
                {
                    "ID": i,
                    "Form_ID": line["ID"],
                    "Cognateset_ID": cs,
                    "Segment_Slice": [
                        "{:d}:{:d}".format(slice_start, slice_start + length)
                    ],
                    "Alignment": alm.split(),
                    "Source": ["LexStat"],
                }
            )
            i += 1
            slice_start += length
    dataset.write(CognatesetTable=cognatesets.values())
    dataset.write(CognateTable=judgements)


if __name__ == "__main__":
    parser = cli.parser(__package__ + "." + Path(__file__).stem, description=__doc__)
    parser.add_argument(
        "--output-file",
        "-o",
        type=Path,
        default="aligned",
        help="Output file to write segmented data to,"
        " without extension .tsv (automatically added) (default: aligned)",
    )
    parser.add_argument(
        "--sound-class",
        default="sca",
        choices=["sca", "dolgo", "asjp", "art"],
        help="Sound class model to use (default: sca)",
    )
    parser.add_argument(
        "--threshold",
        default=0.55,
        type=float,
        help="Cognate clustering threshold value (default: 0.55)",
    )
    parser.add_argument(
        "--clustering-method",
        default="infomap",
        help="Cognate clustering method name. Valid options"
        " are, dependent on your LingPy version, {'upgma',"
        " 'single', 'complete', 'mcl', 'infomap'}."
        " (default: infomap)",
    )
    parser.add_argument(
        "--gop",
        default=-2,
        type=float,
        help="Gap opening penalty for the clustering procedure (default: -2)",
    )
    parser.add_argument(
        "--mode",
        default="overlap",
        choices=["global", "local", "overlap", "dialign"],
        help="Select the mode for the alignment analysis (default: overlap)",
    )
    parser.add_argument(
        "--ratio",
        default=1.5,
        type=float,
        help="Ratio of language-pair specific vs. general"
        " scores in the LexStat algorithm (default: 1.5)",
    )
    parser.add_argument(
        "--initial-threshold",
        default=0.7,
        type=float,
        help="Threshold value for the initial pairs used to"
        " bootstrap the calculation (default: 0.7)",
    )
    args = parser.parse_args()
    cognate_code_to_file(
        metadata=args.metadata,
        ratio=args.ratio,
        cluster_method=args.clustering_method,
        soundclass=args.sound_class,
        mode=args.mode,
        threshold=args.threshold,
        initial_threshold=args.initial_threshold,
        gop=args.gop,
        output_file=args.output_file,
    )

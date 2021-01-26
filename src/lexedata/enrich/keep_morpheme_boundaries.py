from pathlib import Path

import argparse

import csv


def morpheme_boundaries_to_csv(judgements: Path, alignments: Path, output_file: Path):
    cognatesets_new = {}
    for line in csv.DictReader(judgements.open()):
        cognatesets_new.setdefault(line["Cognateset_ID"], set()).add(line["Form_ID"])

    cognatesets_old = {}
    old_judgements = {}
    for line in csv.DictReader(alignments.open()):
        cognatesets_old.setdefault(line["Cognateset_ID"], set()).add(line["Form_ID"])
        old_judgements[line["Form_ID"], line["Cognateset_ID"]] = line

    cognatesets_old_reversed = {
        frozenset(forms): id for id, forms in cognatesets_old.items()
    }

    with judgements.open() as judgements_file:
        judgements = csv.DictReader(judgements_file)
        out = csv.DictWriter(
            output_file.open("w"),
            judgements.fieldnames,
            dialect=judgements.dialect,
        )
        out.writeheader()
        for line in judgements:
            cognates = frozenset(cognatesets_new[line["Cognateset_ID"]])
            if cognates in cognatesets_old_reversed:
                old_line = old_judgements[
                    line["Form_ID"], cognatesets_old_reversed[cognates]
                ]
                line["Alignment"] = old_line["Alignment"]
                line["Segment_Slice"] = old_line["Segment_Slice"]
            else:
                pass
            out.writerow(line)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transfer metadata of existing cognate sets to new cognatesets that may "
        "have different IDs, but the same composition in terms of contained forms."
    )
    parser.add_argument(
        "judgements",
        type=Path,
        help="Path to the csv file containing the cognate judgements",
    )
    parser.add_argument(
        "alignments",
        type=Path,
        help="Path to the file containing the alignments",
    )
    # TODO: set appropriate default
    parser.add_argument(
        "--output-file",
        "-o",
        type=Path,
        default="cognate.csv",
        help="Path to the output file",
    )
    args = parser.parse_args()
    morpheme_boundaries_to_csv(args.judgements, args.alignments, args.output_file)

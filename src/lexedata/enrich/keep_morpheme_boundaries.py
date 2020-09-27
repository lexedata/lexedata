from pathlib import Path

import argparse

import csv

parser = argparse.ArgumentParser(description="Transfer metadata of existing cognate sets to new cognatesets that may have different IDs, but the same composition in terms of contained forms.")
parser.add_argument("judgements", type=Path)
parser.add_argument("alignments", type=Path)
parser.add_argument("out", type=Path)
args = parser.parse_args()

cognatesets_new = {}
for line in csv.DictReader(args.judgements.open()):
    cognatesets_new.setdefault(line["Cognateset_ID"], set()).add(line["Form_ID"])

cognatesets_old = {}
old_judgements = {}
for line in csv.DictReader(args.alignments.open()):
    cognatesets_old.setdefault(line["Cognateset_ID"], set()).add(line["Form_ID"])
    old_judgements[line["Form_ID"], line["Cognateset_ID"]] = line

cognatesets_old_reversed = {
    frozenset(forms): id
    for id, forms in cognatesets_old.items()
}

with args.judgements.open() as judgements_file:
    judgements = csv.DictReader(judgements_file)
    out = csv.DictWriter(args.out.open("w"), judgements.fieldnames, dialect=judgements.dialect)
    out.writeheader()
    for line in judgements:
        cognates = frozenset(cognatesets_new[line["Cognateset_ID"]])
        if cognates in cognatesets_old_reversed:
            old_line = old_judgements[line["Form_ID"], cognatesets_old_reversed[cognates]]
            old_line["ID"] = line["ID"]
            old_line["Cognateset_ID"] = line["Cognateset_ID"]
        else:
            old_line = line
        out.writerow(old_line)



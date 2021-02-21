from pathlib import Path
import csv
from tqdm import tqdm
import collections

import pycldf


def load_forms_from_tsv(dataset: pycldf.Dataset, input_file: Path):
    input = csv.DictReader(
        input_file.open(encoding="utf-8"),
        delimiter="\t",
    )

    c_form_id = dataset["FormTable", "id"].name
    c_form_segments = dataset["FormTable", "segments"].name
    forms = {
        # These days, all dicts are ordered by default. Still, maybe make this explicit.
        form[c_form_id]: form
        for form in dataset["FormTable"]
    }

    edictor_cognatesets = collections.defaultdict(list)

    form_table_upper = {
        column.name.upper(): column.name
        for column in dataset["FormTable"].tableSchema.columns
    }
    form_table_upper.update(
        {
            "DOCULECT": dataset["FormTable", "languageReference"].name,
            "CONCEPT": dataset["FormTable", "parameterReference"].name,
            "IPA": dataset["FormTable", "form"].name,
            "COGID": "cognatesetReference",
            "ALIGNMENT": "alignment",
            "TOKENS": c_form_segments,
            "CLDF_ID": c_form_id,
            "ID": "",
        }
    )
    separators = [None for _ in input.fieldnames]
    for i in range(len(input.fieldnames) - 1, -1, -1):
        lingpy = input.fieldnames[i]
        try:
            input.fieldnames[i] = form_table_upper[lingpy]
        except KeyError:
            pass

        if input.fieldnames[i] == "cognatesetReference":
            separators[i] = " "
        elif input.fieldnames[i] == "alignment":
            separators[i] = " "

        try:
            separators[i] = dataset["FormTable", input.fieldnames[i]].separator
        except KeyError:
            pass

    for line in tqdm(input, total=len(forms)):
        if line[""].startswith("#"):
            # One of Edictor's comment rows, storing settings
            continue

        for (key, value), sep in zip(line.items(), separators):
            if sep is not None:
                if not value:
                    line[key] = []
                else:
                    line[key] = value.split(sep)

        morpheme_boundary = 0
        alignment_morpheme_boundary = 0
        for cognateset in line["cognatesetReference"][:-1]:
            next_morpheme_boundary = line[c_form_segments].index("+", morpheme_boundary)
            del line[c_form_segments][next_morpheme_boundary]
            if line["alignment"]:
                next_alignment_morpheme_boundary = line["alignment"].index(
                    "+", alignment_morpheme_boundary
                )
                alignment = line["alignment"][
                    alignment_morpheme_boundary:next_alignment_morpheme_boundary
                ]
                if line[c_form_segments][morpheme_boundary:next_morpheme_boundary] != [
                    c for c in alignment if c != "-"
                ]:
                    print(
                        "Alignment {:} did not match segments {:}".format(
                            alignment,
                            line[c_form_segments][
                                morpheme_boundary:next_morpheme_boundary
                            ],
                        )
                    )
                alignment_morpheme_boundary = next_alignment_morpheme_boundary + 1
            else:
                alignment = None
            edictor_cognatesets[cognateset].append(
                (line[c_form_id], morpheme_boundary, next_morpheme_boundary, alignment)
            )
            morpheme_boundary = next_morpheme_boundary
        next_morpheme_boundary = len(line[c_form_segments])
        if line["alignment"]:
            next_alignment_morpheme_boundary = len(line["alignment"])
            alignment = line["alignment"][
                alignment_morpheme_boundary:next_alignment_morpheme_boundary
            ]
            if line[c_form_segments][morpheme_boundary:next_morpheme_boundary] != [
                c for c in alignment if c != "-"
            ]:
                print(
                    "Alignment {:} did not match segments {:}".format(
                        alignment,
                        line[c_form_segments][morpheme_boundary:next_morpheme_boundary],
                    )
                )
        else:
            alignment = None
        edictor_cognatesets[line["cognatesetReference"][-1]].append(
            (line[c_form_id], morpheme_boundary, next_morpheme_boundary, alignment)
        )

        forms[line[c_form_id]] = line
    del edictor_cognatesets["0"]

    dataset["FormTable"].write(forms.values())
    return edictor_cognatesets


def match_cognatesets(new_cognatesets, reference_cognatesets):
    new_cognateset_ids = sorted(
        new_cognatesets, key=lambda x: len(new_cognatesets[x]), reverse=True
    )
    matching = {}
    unassigned_reference_cognateset_ids = [
        (len(forms), c) for c, forms in reference_cognatesets.items()
    ]
    unassigned_reference_cognateset_ids.sort(reverse=True)
    cut = 0
    for n in tqdm(new_cognateset_ids):
        new_cognateset = new_cognatesets[n]
        forms = {s[0] for s in new_cognateset}
        best_intersection = 0
        index, best_reference = None, None
        for i, (left, right) in enumerate(
            unassigned_reference_cognateset_ids[cut:], cut
        ):
            if left <= best_intersection:
                break
            if left > 2 * len(forms):
                cut = i
                continue
            reference_cognateset = reference_cognatesets[right]
            intersection = len(forms & {s[0] for s in reference_cognateset})
            if intersection > best_intersection:
                index, best_reference = (i, right)
                best_intersection = intersection
        matching[n] = best_reference
        if index is not None:
            del unassigned_reference_cognateset_ids[index]
    return matching


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Export #FormTable to tsv format for import to edictor"
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default="Wordlist-metadata.json",
        help="Path to the JSON metadata file describing the dataset (default: ./Wordlist-metadata.json)",
    )
    # TODO: set these arguments correctly
    parser.add_argument(
        "--some-switch-on-how-to-merge-cognatesets",
    )
    parser.add_argument(
        "--input-file",
        "-i",
        type=Path,
        default="cognate.tsv",
        help="Path to the input file",
    )
    args = parser.parse_args()
    load_forms_from_tsv(
        dataset=pycldf.Dataset.from_metadata(args.metadata),
        input_file=args.input_file,
    )

if False:
    import os

    os.chdir("/home/gereon/Develop/lexedata/Arawak")
    dataset = pycldf.Wordlist.from_metadata("Wordlist-metadata.json")
    input_file = Path("./from_edictor.tsv")
    new_cogsets = load_forms_from_tsv(dataset, input_file)
    ref_cogsets = {}
    comments = {}
    for j in dataset["CognateTable"]:
        ref_cogsets.setdefault(j["Cognateset_ID"], set()).add((j["Form_ID"],))
        comments[j["Cognateset_ID"], j["Form"]] = j["Comment"]
    matches = match_cognatesets(new_cogsets, ref_cogsets)

    cognate = []
    for cognateset, judgements in new_cogsets.items():
        if matches[cognateset]:
            cognateset = matches[cognateset]
        else:
            cognateset = "+".join(f for f, _, _, _ in judgements)
        for form, start, end, alignment in judgements:
            cognate.append(
                {
                    "ID": f"{form}-{cognateset}",
                    "Form_ID": form,
                    "Cognateset_ID": cognateset,
                    "Segment_Slice": [f"{start}:{end}"],
                    "Alignment": alignment,
                    "Source": ["EDICTOR"],
                    "Comment": comments.get((cognateset, form)),
                }
            )

    cognate.sort(key=lambda j: j["ID"])
    dataset["CognateTable"].write(cognate)

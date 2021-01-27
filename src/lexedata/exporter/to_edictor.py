# Input for edictor is a .tsv file containing the forms
# The first column needs to be 'ID', 1-based integers
# Cognatesets IDs need to be 1-based integers

from pathlib import Path
import csv
import typing as t

import pycldf

from lexedata.types import Form


def prepare_forms(dataset: pycldf.Dataset, languages: t.Iterable[str], cognatesets: t.Iterable[str], output_file: Path):
    # required fields
    c_cognate_cognateset = dataset["CognateTable", "cognatesetReference"].name
    c_cognate_form = dataset["CognateTable", "formReference"].name
    c_form_id = dataset["FormTable", "id"].name
    c_form_language = dataset["FormTable", "languageReference"].name
    c_cogset_id = dataset["CognatesetTable", "id"].name
    cogset_to_id = dict()
    for c, cogset in enumerate(dataset["CognatesetTable"], 1):
        if cogset[c_cogset_id] in cognatesets:
            cogset_to_id[cogset[c_cogset_id]] = c
    # load all cogsets associated with a form
    cogset_by_form_id = dict()
    for j in dataset["CognateTable"]:
        cogset_by_form_id[j[c_cognate_form]] = j[c_cognate_cognateset]
    # load all forms with given languages:
    forms = []
    for form in dataset["FormTable"]:
        if form[c_form_language] in languages:
            forms.append(form)
    # set header for tsv
    tsv_header = list(dataset["FormTable"].tableSchema.columndict.keys())
    # create new field ID or Original_ID if already exists
    if c_form_id == "ID":
        tsv_header.pop(c_form_id)
        tsv_header.insert(0, c_form_id)
        tsv_header.append("Original_ID")
    else:
        tsv_header.insert(0, "ID")
    # add Cognateset ID
    if "Cognateset_ID" not in tsv_header:
        tsv_header.append("Cognateset_ID")
    forms_to_tsv(
        forms=forms,
        tsv_header=tsv_header,
        cogset_by_form_id=cogset_by_form_id,
        cogset_to_id=cogset_to_id,
        output_file=output_file
    )

def forms_to_tsv(
        forms: t.Iterable[Form],
        tsv_header: t.List[str],
        cogset_by_form_id: t.Dict[str: str],
        cogset_to_id: t.Dict[str, int],
        output_file: Path
):
    out = csv.DictWriter(
        output_file,
        fieldnames=tsv_header,
        delimiter="\t",
        newline="",
    )
    out.writeheader()
    for c, form in enumerate(forms, 1):
        # store original form id in other field and get cogset integer id
        if "Original_ID" in tsv_header:
            form["Original_ID"] = form[c_form_id]
            cogset = cogset_by_form_id.get(form["Original_ID"])
        else:
            cogset = cogset_by_form_id.get(form[c_form_id])
        # if there is a cogset, add its integer id. otherwise set id to 0
        if cogset:
            form["Cogset_ID"] = cogset_to_id[cogset]
        else:
            form["Cogset_ID"] = 0
        # add integer form id
        form["ID"] = c

        out.writerow(form)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Export #FormTable to tsv format for import to edictor")
    parser.add_argument(
        "--metadata",
        type=Path,
        default="Wordlist-metadata.json",
        help="Path to the JSON metadata file describing the dataset (default: ./Wordlist-metadata.json)",
    )
    # TODO: set these arguments correctly
    parser.add_argument(
        "--languages",
        type=str,
        nargs="*",
        default=[],
        help="Language references for form selection",
    )
    parser.add_argument(
        "--concepts",
        type=str,
        nargs="*",
        default=[],
        help="",
    )
    parser.add_argument(
        "--cognatesets",
        type=str,
        nargs="*",
        default=[],
        help="",
    )
    parser.add_argument(
        "--output-file",
        "-o",
        type=Path,
        default="cognate.csv",
        help="Path to the output file",
    )
    args = parser.parse_args()
    prepare_forms(
        dataset=pycldf.Dataset.from_metadata(args.metadata),
        languages=args.languages,
        cognatesets=args.cognatesets,
        output_file=args.output_file
    )


# Input for edictor is a .tsv file containing the forms
# The first column needs to be 'ID', 1-based integers
# Cognatesets IDs need to be 1-based integers

from pathlib import Path
import csv
import typing as t

import pycldf

from lexedata.types import Form


def prepare_forms(
    dataset: pycldf.Dataset,
    languages: t.Iterable[str],
    cognatesets: t.Iterable[str],
    output_file: Path,
):
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
    try:
        id_column = tsv_header.index("ID")
        tsv_header[id_column] = "Original_ID"
    except ValueError:
        pass
    # add Cognateset ID
    if "Cognateset_ID" not in tsv_header:
        tsv_header.append("Cognateset_ID")
    forms_to_tsv(
        dataset=dataset,
        forms=forms,
        tsv_header=tsv_header,
        cogset_by_form_id=cogset_by_form_id,
        cogset_to_id=cogset_to_id,
        output_file=output_file,
    )


def forms_to_tsv(
    dataset: pycldf.Dataset,
    forms: t.Iterable[Form],
    tsv_header: t.List[str],
    cogset_by_form_id: t.Dict[str, str],
    cogset_to_id: t.Dict[str, int],
    output_file: Path,
):
    out = csv.DictWriter(
        output_file.open("w"),
        fieldnames=tsv_header,
        delimiter="\t",
    )
    out.writeheader()
    for c, form in enumerate(forms, 1):
        # store original form id in other field and get cogset integer id
        cogset = cogset_by_form_id.get(form[c_form_id])
        if "ID" in form:
            form["Original_ID"] = form.pop("ID")
            cogset = cogset_by_form_id.get(form["Original_ID"])
        else:
            ...
        # if there is a cogset, add its integer id. otherwise set id to 0
        if cogset:
            form["Cogset_ID"] = cogset_to_id[cogset]
        else:
            form["Cogset_ID"] = 0
        # add integer form id
        form["ID"] = c
        # TODO: join the segments by +
        out.writerow(form)


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
        default="cognate.tsv",
        help="Path to the output file",
    )
    args = parser.parse_args()
    prepare_forms(
        dataset=pycldf.Dataset.from_metadata(args.metadata),
        languages=args.languages,
        cognatesets=args.cognatesets,
        output_file=args.output_file,
    )

#### NON-RUNNING EXAMPLE NOTES FOLLOW
"""
FormTable
himmelauge, h i m m e l a u g e
himmelsauge, h i m m e l s a u g e
tão, t ã o
kitab, k i t a b

CognateTable
himmelauge,1:6,HIMMEL
himmelauge,7:10,AUGE
himmelsauge,1:6,HIMMEL
himmelsauge,8:11,AUGE
tão,1:2,TA
tão,2:3,NO
kitab,"1,3,5",KTB
kitab,"2,4",IA

CognatesetTable
HIMMEL,1
AUGE,2
TA,3
NO,4

Edictor
1	himmelsauge	h i m m e l + a u g e	1 2
2	himmelsauge	h i m m e l + s + a u g e	1 0 2
3	tão	t ã + o	3 4
4	kitab	k + i + t + a + b	5 6 5 6 5


which_segment_belongs_to_which_cognateset: Dict[FormID, List[Set[CognatesetID]]] = {}
for j in ds["CognateTable"]:
    if j["Form_ID"] not in which_segment_belongs_to_which_cognateset:
        form = forms[j["Form_ID"]]
        which_segment_belongs_to_which_cognateset[j["Form_ID"]] = [set() for _ in form["Segments"]]

    segments_judged = lexedata.util.parse_segment_slice(j["Segment_Slice"])
    for s in segments_judged:
        which_segment_belongs_to_which_cognateset[j["Form_ID"]][s].add(j["Cognateset_ID"])



{"himmelsauge": [{"HIMMEL"}, {"HIMMEL"}, {"HIMMEL"}, {"HIMMEL"}, {"HIMMEL"}, {"HIMMEL"}, set(), {"AUGE"}, {"AUGE"}, {"AUGE"}, {"AUGE"}]}

all_cognatesets = {cognateset["ID"]: c for c, cognateset in enumerate(ds["CognatesetTable"], 1)}

for form, judgements in which_segment_belongs_to_which_cognateset.items():
    for s, segment_cognatesets in enumerate(judgements):
        if s = 0:
            if not segment_cognatesets:
                out_segments = [forms[form]["Segments"][s]]
                out_cognatesets = [0]
            elif len(segment_cognatesets) >= 1:
                out_segments = [forms[form]["Segments"][s]]
                out_cognatesets = [all_cognatesets[segment_cognatesets.pop()]]
        else:
            if out_cognatesets[-1] in segment_cognatesets:
                pass
            elif out_cognatesets[-1] == 0 and not segment_cognatesets:
                pass
            elif not segment_cognatesets:
                out_segments.append("+")
                out_cognatesets.append(0)
            else:
                out_segments.append("+")
                out_cognatesets.append(all_cognatesets[segment_cognatesets.pop()])
            out_segments.append(forms[form]["Segments"][s])


{"himmelsauge": [1, 1, 1, 1, 1, 1, +, 0, +, 2, 2, 2, 2]}
{"himmelsauge": [h, i, m, m, e, l, +, s, +, a, u, g, e], [1, 0, 2]}
himmelsauge	h i m m e l + s + a u g e	1 0 2
"""

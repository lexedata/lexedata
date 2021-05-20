# Input for edictor is a .tsv file containing the forms
# The first column needs to be 'ID', 1-based integers
# Cognatesets IDs need to be 1-based integers

from pathlib import Path
import csv
import typing as t

import pycldf


import lexedata.cli as cli
from lexedata.util import parse_segment_slices


def rename(form_column, dataset):
    try:
        function = dataset["FormTable", form_column].propertyUrl.expand().split("#")[-1]
    except (KeyError, AttributeError):
        function = form_column
    return {
        "languageReference": "DOCULECT",
        "parameterReference": "CONCEPT",
        "form": "IPA",
        "cognatesetReference": "COGID",
        "alignment": "ALIGNMENT",
        "segments": "TOKENS",
        "id": "CLDF_id",
        "LINGPY_ID": "ID",
        "ID": "CLDF_ID",
    }.get(function, form_column)


class WorldSet:
    def __contains__(self, thing: t.Any):
        return True

    def intersection(self, other: t.Iterable):
        return other


def ensure_list(maybe_string: t.Union[t.List[str], str]) -> t.List[str]:
    if isinstance(maybe_string, list):
        return maybe_string
    else:
        return [maybe_string]


def forms_to_tsv(
    dataset: pycldf.Dataset,
    languages: t.Iterable[str],
    concepts: t.Set[str],
    cognatesets: t.Iterable[str],
    output_file: Path,
    logger: cli.logging.Logger = cli.logger,
):
    # required fields
    c_cognate_cognateset = dataset["CognateTable", "cognatesetReference"].name
    c_cognate_form = dataset["CognateTable", "formReference"].name
    c_form_language = dataset["FormTable", "languageReference"].name
    c_form_concept = dataset["FormTable", "parameterReference"].name
    c_form_id = dataset["FormTable", "id"].name
    c_form_segments = dataset["FormTable", "segments"].name

    # prepare the header for the tsv output
    # the first column must be named ID and contain 1-based integer IDs
    # set header for tsv
    tsv_header = list(dataset["FormTable"].tableSchema.columndict.keys())

    tsv_header.insert(0, "LINGPY_ID")
    tsv_header.append("cognatesetReference")

    delimiters = {
        c.name: c.separator
        for c in dataset["FormTable"].tableSchema.columns
        if c.separator
    }

    # select forms and cognates given restriction of languages and concepts, cognatesets respectively
    forms = {}
    for form in dataset["FormTable"]:
        if form[c_form_language] in languages:
            if concepts.intersection(ensure_list(form[c_form_concept])):
                # Normalize the form:
                # 1. No list-valued entries
                for c, d in delimiters.items():
                    if c == c_form_segments:
                        continue
                    form[c] = d.join(form[c])
                # 2. No tabs, newlines in entries
                for c, v in form.items():
                    if type(v) == str:
                        form[c] = form[c].replace("\t", "!t").replace("\n", "!n")
                forms[form[c_form_id]] = form

    cognateset_cache: t.Dict[t.Optional[str], int] = {
        cognateset["ID"]: c
        for c, cognateset in enumerate(dataset["CognatesetTable"], 1)
        if cognateset["ID"] in cognatesets
    }
    cognateset_cache[None] = 0
    alignments: t.Dict[t.Tuple[str, str], t.List[str]] = {}

    # load all cognates corresponding to those forms
    which_segment_belongs_to_which_cognateset: t.Dict[str, t.List[t.Optional[str]]] = {}
    for j in dataset["CognateTable"]:
        if j[c_cognate_form] in forms and j[c_cognate_cognateset] in cognateset_cache:
            form = forms[j[c_cognate_form]]
            if j[c_cognate_form] not in which_segment_belongs_to_which_cognateset:
                which_segment_belongs_to_which_cognateset[j[c_cognate_form]] = [
                    None for _ in form[c_form_segments]
                ]
            segments_judged = parse_segment_slices(
                segments=form[c_form_segments], judgement=j
            )
            for s in segments_judged:
                if s >= len(
                    which_segment_belongs_to_which_cognateset[j[c_cognate_form]]
                ):
                    logger.warning(
                        f"In judgement {j}, segment slice point outside valid range 0:{len(form[c_form_segments])}."
                    )
                    continue
                elif (
                    s > 0
                    and j[c_cognate_cognateset]
                    != which_segment_belongs_to_which_cognateset[j[c_cognate_form]][
                        s - 1
                    ]
                    and j[c_cognate_cognateset]
                    in which_segment_belongs_to_which_cognateset[j[c_cognate_form]]
                ):
                    raise ValueError(
                        f"In judgement {j}, encountered non-concatenative morphology: Segments of judgement are not contiguous."
                    )

                elif which_segment_belongs_to_which_cognateset[j[c_cognate_form]][s]:
                    raise ValueError(
                        f"In judgement {j}, encountered non-concatenative morphology: Segments overlap with cognate set {which_segment_belongs_to_which_cognateset[j[c_cognate_form]][s]}."
                    )
                else:
                    which_segment_belongs_to_which_cognateset[j[c_cognate_form]][s] = j[
                        c_cognate_cognateset
                    ]
            alignments[j[c_cognate_form], j[c_cognate_cognateset]] = j["Alignment"] or [
                s for i, s in enumerate(form[c_form_segments]) if i in segments_judged
            ]

    # write output to tsv
    out = csv.DictWriter(
        output_file.open("w", encoding="utf-8"),
        fieldnames=tsv_header,
        delimiter="\t",
    )
    out.writerow({column: rename(column, dataset) for column in tsv_header})
    out_cognatesets: t.List[t.Optional[str]]
    for c, (form, judgements) in enumerate(
        which_segment_belongs_to_which_cognateset.items(), 1
    ):
        for s, segment_cognateset in enumerate(judgements):
            if s == 0:
                if segment_cognateset is None:
                    out_segments = [forms[form][c_form_segments][s]]
                    out_alignment = [forms[form][c_form_segments][s]]
                    out_cognatesets = [None]
                else:
                    out_segments = [forms[form][c_form_segments][s]]
                    out_alignment = alignments[form, segment_cognateset]
                    out_cognatesets = [segment_cognateset]
            else:
                if out_cognatesets[-1] == segment_cognateset:
                    pass
                elif out_cognatesets[-1] is None and segment_cognateset is None:
                    out_alignment.append(forms[form][c_form_segments][s])
                    pass
                elif segment_cognateset is None:
                    out_segments.append("+")
                    out_alignment.append("+")
                    out_alignment.append(forms[form][c_form_segments][s])
                    out_cognatesets.append(None)
                else:
                    out_segments.append("+")
                    out_alignment.append("+")
                    out_alignment.extend(alignments[form, segment_cognateset])
                    out_cognatesets.append(segment_cognateset)
                out_segments.append(forms[form][c_form_segments][s])
        if out_segments != [s for s in out_alignment if s != "-"]:
            logger.warning(
                f"In form {form}, alignment {out_alignment} did not match segments {out_segments}!"
            )
        # store original form id in other field and get cogset integer id
        this_form = forms[form]
        this_form["LINGPY_ID"] = c
        # if there is a cogset, add its integer id. otherwise set id to 0
        this_form["cognatesetReference"] = " ".join(
            str(cognateset_cache[e]) for e in out_cognatesets
        )
        this_form["alignment"] = " ".join(out_alignment)
        this_form[c_form_segments] = " ".join(out_segments)

        # add integer form id
        this_form["ID"] = c
        out.writerow(this_form)


if __name__ == "__main__":
    parser = cli.parser(
        description="Export #FormTable to tsv format for import to edictor"
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
    logger = cli.setup_logging(args)
    forms_to_tsv(
        dataset=pycldf.Dataset.from_metadata(args.metadata),
        languages=args.languages or WorldSet(),
        concepts=args.concepts or WorldSet(),
        cognatesets=args.cognatesets or WorldSet(),
        output_file=args.output_file,
        logger=logger,
    )

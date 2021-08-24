"""Export a dataset to Edictor/Lingpy.

Input for edictor is a .tsv file containing the forms. The first column needs
to be 'ID', containing 1-based integers. Cognatesets IDs need to be 1-based
integers.

"""

# TODO: Underscores are treated specially by Edictor in a way we cannot support yet.

import csv
import sys
import itertools
import typing as t
from pathlib import Path

import pycldf


import lexedata.cli as cli
import lexedata.types as types
import lexedata.report.nonconcatenative_morphemes
from lexedata.util import parse_segment_slices, ensure_list


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


def glue_in_alignment(
    global_alignment, cogsets, new_alignment, new_cogset, segments: slice
):
    """Add a partial alignment to a global alignment with gaps

    NOTE: This function does not check for overlapping alignments, it just
    assumes alignments do not overlap!

    >>> alm = "(t) (e) (s) (t)".split()
    >>> cogsets = [None]
    >>> glue_in_alignment(alm, cogsets, list("es-"), 1, slice(1, 3))
    >>> alm
    ['(t)', '+', 'e', 's', '-', '+', '(t)']
    >>> cogsets
    [None, 1, None]
    >>> glue_in_alignment(alm, cogsets, list("-t-"), 2, slice(3, 4))
    >>> alm
    ['(t)', '+', 'e', 's', '-', '+', '-', 't', '-']
    >>> cogsets
    [None, 1, 2]

    This is independent of the order in which alignments are glued in.

    >>> alm = "(t) (e) (s) (t)".split()
    >>> cogsets = [None]
    >>> glue_in_alignment(alm, cogsets, list("-t-"), 2, slice(3, 4))
    >>> alm
    ['(t)', '(e)', '(s)', '+', '-', 't', '-']
    >>> cogsets
    [None, 2]
    >>> glue_in_alignment(alm, cogsets, list("es-"), 1, slice(1, 3))
    >>> alm
    ['(t)', '+', 'e', 's', '-', '+', '-', 't', '-']
    >>> cogsets
    [None, 1, 2]

    Of course, it also works for coplete forms, not just for partial cognate
    judgements.

    >>> alm = "(t) (e) (s) (t)".split()
    >>> cogsets = [None]
    >>> glue_in_alignment(alm, cogsets, list("t-es-t-"), 3, slice(0, 4))
    >>> alm
    ['t', '-', 'e', 's', '-', 't', '-']
    >>> cogsets
    [3]

    """
    first_segment, last_segment = segments.start, segments.stop - 1
    alignment_index, cogsets_index, segment_index = 0, 0, 0

    # Just in case start or end are ouf of bounds:
    first_alignment = 0
    last_alignment = len(global_alignment)

    while alignment_index < len(global_alignment):
        if segment_index == first_segment:
            first_alignment = alignment_index
        if segment_index == last_segment:
            last_alignment = alignment_index
            break

        alignment_index += 1
        if global_alignment[alignment_index] == "+":
            # Segment boundary here, skip, increase the morpheme
            cogsets_index += 1
        elif global_alignment[alignment_index] in {"-", "(", ")"}:
            # Alignment special character, skip
            pass
        else:
            # Some actual segment, step
            segment_index += 1

    global_alignment[first_alignment : last_alignment + 1] = (
        ["+"] + new_alignment + ["+"]
    )
    cogsets.insert(cogsets_index, new_cogset)
    cogsets.insert(cogsets_index, None)

    # Clear up double morpheme boundary markers
    old_a = "+"
    a, s = 0, 0
    while a < len(global_alignment):
        if old_a == "+" and global_alignment[a] == "+":
            del global_alignment[a]
            del cogsets[s]
        else:
            if global_alignment[a] == "+":
                s += 1
            old_a = global_alignment[a]
            a += 1

    if global_alignment[-1] == "+":
        del global_alignment[-1]

    if global_alignment.count("+") == len(cogsets):
        cogsets.append(None)
    if global_alignment.count("+") + 2 == len(cogsets) and not cogsets[-1]:
        del cogsets[-1]


def forms_to_tsv(
    dataset: types.Wordlist[
        types.Language_ID,
        types.Form_ID,
        types.Parameter_ID,
        types.Cognate_ID,
        types.Cognateset_ID,
    ],
    languages: t.Iterable[str],
    concepts: t.Set[str],
    cognatesets: t.Iterable[str],
    logger: cli.logging.Logger = cli.logger,
):
    # required fields
    try:
        c_cognate_cognateset = dataset["CognateTable", "cognatesetReference"].name
        c_cognate_form = dataset["CognateTable", "formReference"].name
        c_cognate_id = dataset["CognateTable", "id"].name
        c_segment_slice = dataset["CognateTable", "segmentSlice"].name
        c_alignment = dataset["CognateTable", "alignment"].name
    except KeyError:
        # TODO: why not use directly: cli.EXIT.NO_COGNATETABLE(message) ?
        logger.critical(
            """Edictor export requires your dataset to have an explicit CognateTable containing the judgements,
            with all of IDs, forms, cognatesets, segment slices and alignments.
            Run `lexedata.edit.construct_cognate_table` if you have cognate sets in your FormTable.
            Run `lexedata.edit.cognate_code_data` if you want to start from automatic cognate detection."""
        )
        sys.exit(cli.Exit.NO_COGNATETABLE)
    c_form_language = dataset["FormTable", "languageReference"].name
    c_form_concept = dataset["FormTable", "parameterReference"].name
    c_form_id = dataset["FormTable", "id"].name
    try:
        c_form_segments = dataset["FormTable", "segments"].name
    except KeyError:
        # TODO: same: why not use cli:Exit....() directly?
        logger.critical(
            """Edictor export requires your dataset to have segments in the FormTable.
        Run `lexedata.edit.add_segments` to automatically add segments based on your forms."""
        )
        # TODO: Exit.NO_SEGMENTS is not an `int`, so the exit code of the
        # python run is actually 1, not 4 as we wanted.
        sys.exit(cli.Exit.NO_SEGMENTS)

    # prepare the header for the tsv output
    # the first column must be named ID and contain 1-based integer IDs
    # set header for tsv
    tsv_header = list(dataset["FormTable"].tableSchema.columndict.keys())

    tsv_header.insert(0, "LINGPY_ID")
    tsv_header.append("cognatesetReference")
    if "alignment" not in tsv_header:
        tsv_header.append("alignment")

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
                    try:
                        form[c] = d.join(form[c])
                    except TypeError:
                        logger.warning(
                            f"No segments found for form {form[c_form_id]}. You can generate segments using `lexedata.edit.add_segments`."
                        )
                # 2. No tabs, newlines in entries
                for c, v in form.items():
                    if type(v) == str:
                        form[c] = form[c].replace("\t", "!t").replace("\n", "!n")
                forms[form[c_form_id]] = form

    cognateset_cache: t.Mapping[t.Optional[str], int]
    if "CognatesetTable" in dataset:
        cognateset_cache = {
            cognateset["ID"]: c
            for c, cognateset in enumerate(dataset["CognatesetTable"], 1)
            if cognateset["ID"] in cognatesets
        }
    else:
        if cognatesets is None:
            cognateset_cache = t.DefaultDict(itertools.count().__next__)
        else:
            cognateset_cache = {c: i for i, c in enumerate(cognatesets, 1)}

    # Warn about unexpected non-concatenative ‘morphemes’
    lexedata.report.nonconcatenative_morphemes.segment_to_cognateset(
        dataset, cognatesets, logger
    )

    judgements_about_form: t.Mapping[
        types.Form_ID, t.Tuple[t.List[str], t.List[int]]
    ] = {
        id: ([f"({s})" for s in form[c_form_segments]], [])
        for id, form in forms.items()
    }
    # Compose all judgements, last-one-rules mode.
    for j in dataset["CognateTable"]:
        if j[c_cognate_form] in forms and cognateset_cache.get(j[c_cognate_cognateset]):
            j[c_alignment] = [s or "" for s in j[c_alignment]]
            try:
                segments_judged = list(
                    parse_segment_slices(
                        segment_slices=j[c_segment_slice], enforce_ordered=False
                    )
                )
            except ValueError:
                logger.warning(
                    f"In judgement {j[c_cognate_id]}: Index error due to bad segment slice. Skipped."
                )
                continue
            global_alignment, cogsets = judgements_about_form[j[c_cognate_form]]
            segment_start, segment_end = min(segments_judged), max(segments_judged) + 1
            try:
                glue_in_alignment(
                    global_alignment,
                    cogsets,
                    j[c_alignment],
                    j[c_cognate_cognateset],
                    slice(segment_start, segment_end),
                )
            except IndexError:
                logger.warning(
                    f"In judgement {j[c_cognate_id]}: Index error due to bad segment slice. Skipped."
                )
                continue

    return forms, judgements_about_form, cognateset_cache


def write_edictor_file(
    dataset: types.Wordlist[
        types.Language_ID,
        types.Form_ID,
        types.Parameter_ID,
        types.Cognate_ID,
        types.Cognateset_ID,
    ],
    file: t.TextIO,
    forms: t.Mapping[types.Form_ID, t.Mapping[str, t.Any]],
    judgements_about_form,
    cognateset_numbers,
):
    """Write the judgements of a dataset to file, in edictor format."""
    c_form_id = dataset["FormTable", "id"].name
    delimiters = {
        c.name: c.separator
        for c in dataset["FormTable"].tableSchema.columns
        if c.separator
    }

    tsv_header = list(dataset["FormTable"].tableSchema.columndict.keys())

    tsv_header.insert(0, "LINGPY_ID")
    tsv_header.append("cognatesetReference")
    tsv_header.append("alignment")

    # write output to tsv
    out = csv.DictWriter(
        file,
        fieldnames=tsv_header,
        delimiter="\t",
    )
    out.writerow({column: rename(column, dataset) for column in tsv_header})
    out_cognatesets: t.List[t.Optional[str]]
    for f, (id, form) in enumerate(forms.items(), 1):
        # store original form id in other field and get cogset integer id
        this_form = dict(form)
        this_form["LINGPY_ID"] = f

        # Normalize the form:
        # 1. No list-valued entries
        for col, d in delimiters.items():
            this_form[col] = d.join(form[col])
        # 2. No tabs, newlines in entries, they make Edictor mad.
        for c, v in form.items():
            if type(v) == str:
                this_form[c] = (
                    form[c].replace("\t", "  ;t  ").replace("\n", "    ;n    ")
                )

        # if there is a cogset, add its integer id. otherwise set id to 0
        judgement = judgements_about_form[this_form[c_form_id]]
        this_form["cognatesetReference"] = " ".join(
            str(cognateset_numbers.get(e, 0)) for e in (judgement[1] or [None])
        )
        this_form["alignment"] = (
            " ".join(judgement[0])
            .replace("(", "( ")
            .replace(")", " )")
            .replace(" ) ( ", " ")
        )

        # add integer form id
        out.writerow(this_form)
    add_edictor_settings(file, dataset)


def add_edictor_settings(file, dataset):
    """Write a block of Edictor setting comments to a file.

    Edictor takes some comments in its TSV files as directives for how it
    should behave. The important settings here are to set the morphology mode
    to ‘partial’ and pass the order of languages and concepts through.
    Everything else is pretty much edictor standard.

    """
    # TODO: We can set the separator here. We could use something except "\t",
    # maybe, but then we would have to clean up that alternative separator in
    # all out outputs.

    try:
        c_language_id = dataset["LanguageTable", "id"].name
        languages = "\n#@sorted_taxa={:s}".format(
            "|".join(lang[c_language_id] for lang in dataset["LanguageTable"])
        )
    except KeyError:
        languages = ""
    try:
        c_concept_id = dataset["ParameterTable", "id"].name
        concepts = "\n#@sorted_concepts={:s}".format(
            "|".join(concept[c_concept_id] for concept in dataset["ParameterTable"])
        )
    # @sorted_concepts={:s}
    except KeyError:
        concepts = ""
    file.write(
        """
#@highlight=TOKENS|ALIGNMENT
#@sampa=IPA|TOKENS
#@css=menu:show|database:hide
#@basics=COGID|CONCEPT|DOCULECT|IPA|TOKENS{:s}{:s}
#@display=filedisplay|partial
#@missing_marker=Ø
#@separator=\t
#@gap_marker=-
#@formatter=false
#@root_formatter=COGID
#@note_formatter=undefined
#@pattern_formatter=undefined
#@publish=undefined
#@_almcol=ALIGNMENT
#@filename={:s}
#@navbar=true
#@_morphology_mode=partial""".format(
            languages,
            concepts,
            file.name,
        )
    )


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
    dataset = pycldf.Dataset.from_metadata(args.metadata)
    forms, judgements_about_form, cognateset_mapping = forms_to_tsv(
        dataset=dataset,
        languages=args.languages or types.WorldSet(),
        concepts=args.concepts or types.WorldSet(),
        cognatesets=args.cognatesets or types.WorldSet(),
        logger=logger,
    )

    with args.output_file.open("w", encoding="utf-8") as file:
        write_edictor_file(
            dataset, file, forms, judgements_about_form, cognateset_mapping
        )

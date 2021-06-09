from pathlib import Path
import csv
from tqdm import tqdm
import collections
import typing as t

import pycldf

import lexedata.cli as cli
import lexedata.types as types


def extract_partial_judgements(
    segments: t.Sequence[str],
    cognatesets: t.Sequence[types.Cognateset_ID],
    global_alignment: t.Sequence[str],
    logger: cli.logging.Logger = cli.logger,
) -> t.Iterator[t.Tuple[range, types.Cognateset_ID, t.Sequence[str]]]:
    """Extract the different partial cognate judgements.

    Segments has no morpheme boundary markers, they are inferred from
    global_alignment. The number of cognatesets and marked segments in
    global_alignment must match.

    >>> next(extract_partial_judgements("t e s t".split(), [3], "t e s t".split()))
    (range(0, 4), 3, ['t', 'e', 's', 't'])

    >>> partial = extract_partial_judgements("t e s t".split(), [0, 1, 2], "( t ) + e - s + - t -".split())
    >>> next(partial)
    (range(1, 3), 1, ['e', '-', 's'])
    >>> next(partial)
    (range(3, 4), 2, ['-', 't', '-'])

    """
    morpheme_boundary = 0
    alignment_morpheme_boundary = 0
    a, s, c = 0, 0, 0

    while a < len(global_alignment):
        if global_alignment[a] == "+":
            if cognatesets[c]:
                yield range(morpheme_boundary, s), cognatesets[c], global_alignment[
                    alignment_morpheme_boundary:a
                ]
            c += 1
            morpheme_boundary = s
            alignment_morpheme_boundary = a + 1
        elif global_alignment[a] in {"-", "(", ")"}:
            pass
        else:
            s += 1
        a += 1
    yield range(morpheme_boundary, s), cognatesets[c], global_alignment[
        alignment_morpheme_boundary:a
    ]


def load_forms_from_tsv(
    dataset: types.Wordlist[
        types.Language_ID,
        types.Form_ID,
        types.Parameter_ID,
        types.Cognate_ID,
        types.Cognateset_ID,
    ],
    input_file: Path,
    logger: cli.logging.Logger = cli.logger,
) -> t.Mapping[str, t.Sequence[t.Tuple[types.Form_ID, range, t.Sequence[str]]]]:
    """

    Side effects
    ============
    This function overwrites dataset's FormTable
    """
    input = csv.DictReader(
        input_file.open(encoding="utf-8"),
        delimiter="\t",
    )

    c_form_id = dataset["FormTable", "id"].name
    c_form_segments = dataset["FormTable", "segments"].name
    # These days, all dicts are ordered by default. Still, better make this explicit.
    forms = collections.OrderedDict(
        (form[c_form_id], form) for form in dataset["FormTable"]
    )

    edictor_cognatesets: t.Dict[
        str, t.List[t.Tuple[types.Form_ID, range, t.Sequence[str]]]
    ] = collections.defaultdict(list)

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
    separators: t.List[t.Optional[str]] = [None for _ in input.fieldnames]
    for i in range(len(input.fieldnames) - 1, -1, -1):
        if i == 0 and input.fieldnames[0] != "ID":
            raise ValueError(
                f"When importing from Edictor, expected the first column to be named 'ID', but found {input.fieldnames['ID']}"
            )

        lingpy = input.fieldnames[i]
        try:
            input.fieldnames[i] = form_table_upper[lingpy.upper()]
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

    logger.info("Importing form rows from edictor…")
    for line in cli.tq(input, total=len(forms)):
        # Column "" is the re-named Lingpy-ID column, so the first one.
        if line[""].startswith("#"):
            # One of Edictor's comment rows, storing settings
            continue

        for (key, value), sep in zip(line.items(), separators):
            if sep is not None:
                if not value:
                    line[key] = []
                else:
                    line[key] = value.split(sep)

        try:
            for segments, cognateset, alignment in extract_partial_judgements(
                line[c_form_segments],
                line["cognatesetReference"],
                line["alignment"],
                logger,
            ):
                edictor_cognatesets[cognateset].append(
                    (line[c_form_id], segments, alignment)
                )
            forms[line[c_form_id]] = line
        except IndexError:
            logger.warning(
                f"In form with Lingpy-ID {line['']}: Cognateset judgements {line['cognatesetReference']} and alignment {line['alignment']} did not match. At least one morpheme skipped."
            )
    edictor_cognatesets.pop("0", None)

    # Deliberately make use of the property of `write` to discard any entries
    # that don't correspond to existing columns. Otherwise, we'd still have to
    # get rid of the alignment, cognatesetReference and Lingpy-ID columns.
    dataset["FormTable"].write(forms.values())
    return edictor_cognatesets


def match_cognatesets(
    new_cognatesets: t.Mapping[
        int, t.Sequence[t.Tuple[types.Form_ID, range, t.Sequence[str]]]
    ],
    reference_cognatesets: t.Mapping[
        types.Cognateset_ID, t.Sequence[t.Tuple[types.Form_ID, range, t.Sequence[str]]]
    ],
) -> t.Mapping[int, t.Optional[types.Cognateset_ID]]:
    new_cognateset_ids = sorted(
        new_cognatesets, key=lambda x: len(new_cognatesets[x]), reverse=True
    )
    matching: t.Dict[int, t.Optional[types.Cognateset_ID]] = {}
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

    parser = cli.parser(
        description="Export #FormTable to tsv format for import to edictor"
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

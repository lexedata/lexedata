import collections
import csv
import typing as t
from pathlib import Path

import pycldf
from tqdm import tqdm

from lexedata import cli, types, util


def extract_partial_judgements(
    segments: t.Sequence[str],
    cognatesets: t.Sequence[int],
    global_alignment: t.Sequence[str],
    logger: cli.logging.Logger = cli.logger,
) -> t.Iterator[t.Tuple[range, int, t.Sequence[str]]]:
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
) -> t.Mapping[int, t.Sequence[t.Tuple[types.Form_ID, range, t.Sequence[str]]]]:
    """

    Side effects
    ============
    This function overwrites dataset's FormTable
    """
    input = csv.DictReader(
        input_file.open(encoding="utf-8"),
        delimiter="\t",
    )

    # These days, all dicts are ordered by default. Still, better make this explicit.
    forms = util.cache_table(dataset)

    edictor_cognatesets: t.Dict[
        int, t.List[t.Tuple[types.Form_ID, range, t.Sequence[str]]]
    ] = collections.defaultdict(list)

    form_table_upper = {
        (util.cldf_property(column.propertyUrl) or column.name).upper(): (
            util.cldf_property(column.propertyUrl) or column.name
        )
        for column in dataset["FormTable"].tableSchema.columns
    }
    form_table_upper.update(
        {
            "DOCULECT": "languageReference",
            "CONCEPT": "parameterReference",
            "IPA": "form",
            "COGID": "cognatesetReference",
            "ALIGNMENT": "alignment",
            "TOKENS": "segments",
            "CLDF_ID": "id",
            "ID": "",
        }
    )
    if "_PARAMETERREFERENCE" in [f.upper() for f in input.fieldnames]:
        form_table_upper["_PARAMETERREFERENCE"] = "parameterReference"
        form_table_upper["CONCEPT"] = ""

    separators: t.MutableMapping[str, t.Optional[str]] = {}
    # TODO: What's the logic behind going backwards through this? We are not modifying fieldnames.
    for i in range(len(input.fieldnames)):
        if i == 0 and input.fieldnames[0] != "ID":
            raise ValueError(
                "When importing from Edictor, expected the first column to be named 'ID', but found %s",
                input.fieldnames["ID"],
            )

        lingpy = input.fieldnames[i]
        try:
            input.fieldnames[i] = form_table_upper[lingpy.upper()]
        except KeyError:
            logger.warning(
                "Your edictor file contained a column %s, which I could not interpret.",
                lingpy,
            )

        if input.fieldnames[i] == "cognatesetReference":
            separators[input.fieldnames[i]] = " "
        elif input.fieldnames[i] == "alignment":
            separators[input.fieldnames[i]] = " "

        try:
            separators[input.fieldnames[i]] = dataset[
                "FormTable", input.fieldnames[i]
            ].separator
        except KeyError:
            pass

    logger.info(
        "The header of your edictor file will be interpreted as %s.", input.fieldnames
    )

    affected_forms: t.Set[types.Form_ID] = set()
    for line in cli.tq(
        input, task="Importing form rows from edictor…", total=len(forms)
    ):
        # Column "" is the re-named Lingpy-ID column, so the first one.
        if not any(line.values()) or line[""].startswith("#"):
            # One of Edictor's comment rows, storing settings
            continue

        for (key, value) in line.items():
            value = value.replace("\\!t", "\t").replace("\\!n", "\n")
            sep = separators[key]
            if sep is not None:
                if not value:
                    line[key] = []
                else:
                    line[key] = value.split(sep)
            else:
                line[key] = value

        affected_forms.add(line["id"])

        try:
            for segments, cognateset, alignment in extract_partial_judgements(
                line["segments"],
                line["cognatesetReference"],
                line["alignment"],
                logger,
            ):
                edictor_cognatesets[cognateset].append(
                    (line["id"], segments, alignment)
                )
            forms[line["id"]] = line
        except IndexError:
            logger.warning(
                f"In form with Lingpy-ID {line['']}: Cognateset judgements {line['cognatesetReference']} and alignment {line['alignment']} did not match. At least one morpheme skipped."
            )
    edictor_cognatesets.pop(0, None)

    columns = {
        (util.cldf_property(column.propertyUrl) or column.name): column.name
        for column in dataset["FormTable"].tableSchema.columns
    }
    # Deliberately make use of the property of `write` to discard any entries
    # that don't correspond to existing columns. Otherwise, we'd still have to
    # get rid of the alignment, cognatesetReference and Lingpy-ID columns.
    dataset["FormTable"].write(
        (
            {
                columns[property]: value
                for property, value in form.items()
                if columns.get(property)
            }
            for form in forms.values()
        )
    )
    return edictor_cognatesets, affected_forms


def match_cognatesets(
    new_cognatesets: t.Mapping[
        int, t.Sequence[t.Tuple[types.Form_ID, range, t.Sequence[str]]]
    ],
    reference_cognatesets: t.Mapping[
        types.Cognateset_ID, t.Sequence[t.Tuple[types.Form_ID, range, t.Sequence[str]]]
    ],
) -> t.Mapping[int, t.Optional[types.Cognateset_ID]]:
    """Match two different cognateset assignments with each other.

    Map the new_cognatesets to the reference_cognatesets by trying to maximize
    the overlap between each new cognateset and the reference cognateset it is
    mapped to.

    So, if two cognatesets got merged, they get mapped to the bigger one:

    >>> match_cognatesets(
    ...   {0: ["a", "b", "c"]},
    ...   {">": ["a", "b"], "<": ["c"]}
    ... )
    {0: '>'}

    If a cognateset got split, it gets mapped to the bigger part and the other
    part becomes a new, unmapped set:

    >>> match_cognatesets(
    ...   {0: ["a", "b"], 1: ["c"]},
    ...   {"Σ": ["a", "b", "c"]}
    ... )
    {0: 'Σ', 1: None}

    If a single form (or a relatively small number) gets moved between
    cognatesets, the mapping is maintained:

    >>> match_cognatesets(
    ...   {0: ["a", "b"], 1: ["c", "d", "e"]},
    ...   {0: ["a", "b", "c"], 1: ["d", "e"]}
    ... ) == {1: 1, 0: 0}
    True

    (As you see, the function is a bit more general than the type signature
    implies.)

    """
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


def edictor_to_cldf(
    dataset: types.Wordlist[
        types.Language_ID,
        types.Form_ID,
        types.Parameter_ID,
        types.Cognate_ID,
        types.Cognateset_ID,
    ],
    new_cogsets: t.Mapping[
        types.Cognateset_ID, t.List[t.Tuple[types.Form_ID, range, t.Sequence[str]]]
    ],
    affected_forms: t.Set[types.Form_ID],
    source: t.List[str] = [],
):
    ref_cogsets: t.MutableMapping[
        types.Cognateset_ID, t.List[t.Tuple[types.Form_ID, range, t.Sequence[str]]]
    ] = t.DefaultDict(list)
    cognate: t.List[types.Judgement] = []
    judgements_lookup: t.MutableMapping[
        types.Form_ID, t.MutableMapping[types.Cognateset_ID, types.Judgement]
    ] = t.DefaultDict(dict)
    for j in util.cache_table(dataset, "CognateTable").values():
        if j["formReference"] in affected_forms:
            ref_cogsets[j["cognatesetReference"]].append(
                (j["formReference"], j["segmentSlice"], j["alignment"])
            )
            judgements_lookup[j["formReference"]][j["cognatesetReference"]] = j
        else:
            cognate.append(j)
    matches = match_cognatesets(new_cogsets, ref_cogsets)

    for cognateset, judgements in new_cogsets.items():
        cognateset = matches[cognateset]
        if cognateset is None:
            cognateset = "_".join(f for f, _, _ in judgements)
        for form, slice, alignment in judgements:
            was: types.Judgement = judgements_lookup.get(form, {}).get(cognateset)
            if was:
                was["segmentSlice"] = util.indices_to_segment_slice(slice)
                was["alignment"] = alignment
                cognate.append(was)
                continue
            judgements_lookup
            cognate.append(
                types.Judgement(
                    {
                        "id": f"{form}-{cognateset}",
                        "formReference": form,
                        "cognatesetReference": cognateset,
                        "alignment": alignment,
                        "segmentSlice": util.indices_to_segment_slice(slice),
                        "source": source,
                        # TODO: Any more parameters? Status update?
                    }
                )
            )

    cognate.sort(key=lambda j: j["id"])
    m = {
        util.cldf_property(c.propertyUrl) or c.name: c.name
        for c in dataset["CognateTable"].tableSchema.columns
    }
    dataset["CognateTable"].write(
        [{m[k]: v for k, v in j.items() if k in m} for j in cognate]
    )
    # TODO: write new sets to cognateset table


if __name__ == "__main__":
    parser = cli.parser(
        __package__ + "." + Path(__file__).stem,
        description="Import the tsv format used by Edictor and Lingpy. Try to only change the subset of forms and cognatesets contained in the TSV, from a partial export.",
    )
    parser.add_argument(
        "--source",
        default=None,
        metavar="MESSAGE",
        # TODO: Source is not really the right place, even though it's used for
        # this in one of our datasets.
        help="Set the source of all new cognate sets and all new cognate judgements to MESSAGE.",
    )

    parser.add_argument(
        "--input-file",
        "-i",
        type=Path,
        default="cognate.tsv",
        help="Path to the input file",
    )
    args = parser.parse_args()
    logger = cli.setup_logging(args)

    dataset = pycldf.Dataset.from_metadata(args.metadata)
    new_cogsets, affected_forms = load_forms_from_tsv(
        dataset=dataset,
        input_file=args.input_file,
    )

    edictor_to_cldf(
        dataset=dataset,
        new_cogsets=new_cogsets,
        affected_forms=affected_forms,
        source=[args.source],
    )

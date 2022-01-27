import enum
import typing as t
from tabulate import tabulate

import pycldf

import lexedata.cli as cli
import lexedata.types as types


class Missing(enum.Enum):
    IGNORE = 0
    COUNT_NORMALLY = 1
    KNOWN = 2


def coverage_report(
    dataset: types.Wordlist[
        types.Language_ID,
        types.Form_ID,
        types.Parameter_ID,
        types.Cognate_ID,
        types.Cognateset_ID,
    ],
    min_percentage: float,
    with_concept: t.Iterable[types.Parameter_ID],
    missing: Missing = Missing.KNOWN,
    only_coded: bool = True,
) -> t.Tuple[t.List[str], t.List[str]]:
    coded: t.Container[types.Form_ID]
    if only_coded:
        coded = set()
        try:
            c_j_form = dataset["CognateTable", "formReference"].name
            form_column_referred_to_by_judgements = ""
            for foreign_key in dataset["CognateTable"].tableSchema.foreignKeys:
                if foreign_key.columnReference == [c_j_form]:
                    (
                        form_column_referred_to_by_judgements,
                    ) = foreign_key.reference.columnReference
            for judgement in dataset["CognateTable"]:
                coded.add(judgement[c_j_form])
        except KeyError:
            logger.warning(
                "You requested that I only count cognate coded forms, but you have no CognateTable containing judgements. Expect an empty report."
            )
    else:
        form_column_referred_to_by_judgements = dataset["FormTable", "id"].name
        coded = types.WorldSet()

    languages = {}
    try:
        c_l_id = dataset["LanguageTable", "id"].name
        c_l_name = dataset["LanguageTable", "name"].name
        for language in dataset["LanguageTable"]:
            languages[language[c_l_id]] = language
    except KeyError:
        pass

    concepts: t.DefaultDict[str, t.Counter[str]] = t.DefaultDict(t.Counter)
    multiple_concepts = bool(dataset["FormTable", "parameterReference"].separator)
    c_concept = dataset["FormTable", "parameterReference"].name
    c_language = dataset["FormTable", "languageReference"].name
    c_form = dataset["FormTable", "form"].name
    for form in dataset["FormTable"]:
        languages.setdefault(form[c_language], {})
        if form[form_column_referred_to_by_judgements] not in coded:
            continue
        if missing == Missing.IGNORE and (not form[c_form] or form[c_form] == "-"):
            continue
        if missing == Missing.KNOWN and not form[c_form]:
            continue
        if multiple_concepts:
            for c in form[c_concept]:
                concepts[form[c_language]][c] += 1
        else:
            concepts[form[c_language]][form[c_concept]] += 1

    # load primary concepts and number of concepts
    c_c_id = dataset["ParameterTable", "id"].name
    try:
        primary_concepts = [
            c[c_c_id] for c in dataset["ParameterTable"] if c["Primary"]
        ]
    except KeyError:
        cli.logger.warning(
            "ParameterTable doesn't contain a column 'Primary'. Primary concepts couldn't be loaded. "
            "Loading all concepts."
        )
        primary_concepts = [c[c_c_id] for c in dataset["ParameterTable"]]

    total_number_concepts = len(list(dataset["ParameterTable"]))

    data_languages = []
    for language, metadata in languages.items():
        conceptlist = concepts[language]
        try:
            synonyms = sum(conceptlist.values()) / len(conceptlist)
        except ZeroDivisionError:
            synonyms = float("nan")

        # percentage of all concepts covered by this language
        conceptlist_percentage = len(conceptlist) / total_number_concepts
        if conceptlist_percentage * 100 < min_percentage:
            continue

        if not all(c in conceptlist for c in with_concept):
            continue

        # count primary concepts
        primary_count = 0
        for c in primary_concepts:
            if c in conceptlist:
                primary_count += 1
        # if args.languages_only:
        #     print(language)
        data_languages.append(
            [
                metadata[c_l_id],
                metadata[c_l_name],
                primary_count,
                conceptlist_percentage,
                synonyms,
            ]
        )
    return data_languages


def coverage_report_concepts(
    dataset: pycldf.Dataset,
):
    # TODO: This assumes the existence of a ParameterTable. The script should
    # still work if none exists. TODO: In addition, we decided to not formalize
    # primary concepts, so this should instead depend on a command line
    # argument, either supplementing or replacing --with-concepts.
    c_c_id = dataset["ParameterTable", "id"].name
    try:
        # Load primary concepts if possible.
        primary_concepts = [
            c[c_c_id] for c in dataset["ParameterTable"] if c["Primary"]
        ]
    except KeyError:
        cli.logger.warning(
            "ParamterTable doesn't contain a column 'Primary'. Primary concepts couldn't be loaded. "
            "Loading all concepts."
        )
        primary_concepts = [c[c_c_id] for c in dataset["ParameterTable"]]
    # get the foreign keys pointing to the required tables
    foreign_key_parameter = ""
    for foreign_key in dataset["FormTable"].tableSchema.foreignKeys:
        if foreign_key.reference.resource == dataset["ParameterTable"].url:
            foreign_key_parameter = foreign_key.columnReference[0]

    foreign_key_language = ""
    for foreign_key in dataset["FormTable"].tableSchema.foreignKeys:
        if foreign_key.reference.resource == dataset["LanguageTable"].url:
            foreign_key_language = foreign_key.columnReference[0]

    multiple_concepts = bool(dataset["FormTable", "parameterReference"].separator)
    c_concept = foreign_key_parameter
    c_language = foreign_key_language
    # for each concept count the languages
    concepts_to_languages: t.DefaultDict[str, t.List[str]] = t.DefaultDict(list)
    for form in dataset["FormTable"]:
        if multiple_concepts:
            language = form[c_language]
            for concept in form[c_concept]:
                if (
                    language not in concepts_to_languages[concept]
                    and concept in primary_concepts
                ):
                    concepts_to_languages[concept].append(language)
        else:
            concept = form[c_concept]
            language = form[c_language]
            if (
                language not in concepts_to_languages[concept]
                and concept in primary_concepts
            ):
                concepts_to_languages[concept].append(language)

    data_concepts = []
    for k, v in concepts_to_languages.items():
        data_concepts.append([k, len(set(v))])

    return data_concepts


if __name__ == "__main__":
    parser = cli.parser(
        description="Summarise coverage, i.e. how many concepts are known for each language."
    )
    # parser.add_argument(
    #     "--min-concepts",
    #     default=0,
    #     type=int,
    #     help="Only include languages with at least M concepts",
    #     metavar="M",
    # )
    parser.add_argument(
        "--min-percentage",
        default=0,
        type=float,
        help="Only include languages with at least M%% concepts",
        metavar="M",
    )
    parser.add_argument(
        "--languages-only",
        "-l",
        action="store_true",
        default=False,
        help="Only list matching languages, don't report statistics",
    )
    parser.add_argument(
        "--with-concepts",
        "-c",
        action=cli.ListOrFromFile,
        metavar="CONCEPT",
        help="Only include languages that have a form for each CONCEPT.",
    )
    parser.add_argument(
        "--concept-report",
        "-r",
        action="store_true",
        default=False,
        help="Output separate report with concepts and the number of languages that attest them",
    )

    parser.add_argument(
        "--coded",
        action="store_true",
        default=False,
        help="Include only forms that are assigned to at least one cognate class",
    )
    parser.add_argument(
        "--missing",
        choices=list(Missing.__members__),
        default="IGNORE",
        help="How to report missing and NA forms, i.e. forms with #form '' or '-'. The following options exist:"
        "IGNORE: ignore all such forms;"
        "COUNT_NORMALLY: count all such forms as if they were normal forms;"
        "KNOWN: count NA forms ('-') as if they were normal forms;",
    )
    args = parser.parse_args()
    logger = cli.setup_logging(args)

    if str(args.metadata).endswith(".json"):
        dataset = pycldf.Wordlist.from_metadata(args.metadata)
    else:
        cli.Exit.INVALID_DATASET(
            "You must specify the path to a valid metadata file (--metadata path/to/Filename-metadata.json)."
        )
    data = coverage_report(
        dataset,
        args.min_percentage,
        args.with_concepts,
        missing=Missing.__members__[args.missing],
        only_coded=args.coded,
    )

    # TODO: consider generic way of writing the header
    if args.languages_only:
        print(*[language[0] for language in data], sep="\n")
    else:
        print(
            tabulate(
                data,
                headers=[
                    "Language_ID",
                    "Language_Name",
                    "Number of primary concepts",
                    "Percentage of total concepts",
                    "Synonyms",
                ],
                stralign="left",
                numalign="right",
            )
        )

        if args.concept_report:
            data = coverage_report_concepts(dataset=dataset)
            print(
                tabulate(
                    data,
                    headers=[
                        "Concept_ID",
                        "Language_Count",
                    ],
                    stralign="left",
                    numalign="right",
                )
            )

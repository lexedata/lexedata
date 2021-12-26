import typing as t
from tabulate import tabulate

import pycldf

import lexedata.cli as cli
import lexedata.types as types
from lexedata.util import get_foreignkey


def coverage_report(
    dataset: pycldf.Dataset,
    min_percentage: float,
    with_concept: t.Iterable,
    missing: bool,
    only_coded: bool = True,
) -> t.Tuple[t.List[str], t.List[str]]:
    if only_coded:
        try:
            c_j_form = dataset["CognateTable", "formReference"].name
            coded = set()
            form_column_referred_to_by_judgements = ""
            for foreign_key in dataset["CognateTable"].tableSchema.foreignKeys:
                if foreign_key.columnReference == [c_j_form]:
                    (
                        form_column_referred_to_by_judgements,
                    ) = foreign_key.reference.columnReference
            for judgement in dataset["CognateTable"]:
                coded.add(judgement[c_j_form])
        except KeyError:
            form_column_referred_to_by_judgements = dataset["FormTable", "id"].name
            coded = {}
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

    # get the foreign keys pointing to the required tables
    foreign_key_parameter = get_foreignkey(dataset=dataset, table="FormTable", other_table="ParameterTable")
    foreign_key_language = get_foreignkey(dataset=dataset, table="FormTable", other_table="LanguageTable")

    concepts: t.DefaultDict[str, t.Counter[str]] = t.DefaultDict(t.Counter)
    multiple_concepts = bool(dataset["FormTable", "parameterReference"].separator)
    c_concept = foreign_key_parameter
    c_language = foreign_key_language
    c_form = dataset["FormTable", "form"].name
    for form in dataset["FormTable"]:
        languages.setdefault(form[c_language], {})
        if form[form_column_referred_to_by_judgements] not in coded:
            continue
        if form[c_form] == "?" and missing:
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

    header_languages = ""
    data_languages = []
    for language, metadata in languages.items():
        conceptlist = concepts[language]
        try:
            synonyms = sum(conceptlist.values()) / len(conceptlist)
        except ZeroDivisionError:
            synonyms = float("nan")
        include = True
        # percentage of all concepts covered by this language
        conceptlist_percentage = len(conceptlist) / total_number_concepts
        if conceptlist_percentage * 100 < min_percentage:
            include = False

        for c in with_concept:
            if c not in conceptlist:
                include = False
        if not include:
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
    return data_languages, header_languages


def coverage_report_concepts(
    dataset: pycldf.Dataset,
):
    # load possible primary concepts
    c_c_id = dataset["ParameterTable", "id"].name
    try:
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
    foreign_key_parameter = get_foreignkey(dataset=dataset, table="FormTable", other_table="ParameterTable")
    foreign_key_language = get_foreignkey(dataset=dataset, table="FormTable", other_table="LanguageTable")

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
    header_concepts = ""

    return data_concepts, header_concepts


if __name__ == "__main__":
    parser = cli.parser(description="Summarise coverage data")
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
        help="Only include languages with at least M% concepts",
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
        "--with-concept",
        "-c",
        action="append",
        default=[],
        type=str,
        help="Only include languages that have a form for CONCEPT",
        metavar="CONCEPT",
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
        action="store_true",
        default=False,
        help="Ignore missing forms, i.e. FormTable entries with CLDF #form '?'",
    )
    args = parser.parse_args()
    logger = cli.setup_logging(args)

    if str(args.metadata).endswith(".json"):
        dataset = pycldf.Wordlist.from_metadata(args.metadata)
    else:
        cli.Exit.INVALID_DATASET(
            "You must specify the path to a valid metadata file (--metadata path/to/Filename-metadata.json)."
        )
    data, header = coverage_report(
        dataset,
        args.min_percentage,
        args.with_concept,
        missing=args.missing,
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
            data, header = coverage_report_concepts(dataset=dataset)
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

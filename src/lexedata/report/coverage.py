import typing as t
from tabulate import tabulate

import pycldf

import lexedata.cli as cli


def coverage_report(
    dataset: pycldf.Dataset,
    min_percentage: float,
    with_concept: t.Iterable,
    missing: bool,
) -> t.Tuple[t.List[str], t.List[str]]:
    languages = {}
    try:
        c_l_id = dataset["LanguageTable", "id"].name
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
        logger.warning(
            "ParamterTable doesn't contain a column 'Primary'. Primary concepts couldn't be loaded. "
            "Loading all concepts."
        )
        primary_concepts = [c[c_c_id] for c in dataset["ParameterTable"]]

    total_number_concepts = len(list(dataset["ParameterTable"]))

    header = ""
    data = []
    for language, metadata in languages.items():

        conceptlist = concepts[language]
        synonyms = sum(conceptlist.values()) / len(conceptlist)
        include = True
        # percentage of all concepts covered by this language
        conceptlist_percentage = len(conceptlist) / total_number_concepts
        if conceptlist_percentage < min_percentage:
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
        data.append(
            [
                metadata[c_l_id],
                metadata["Name"],
                primary_count,
                conceptlist_percentage,
                synonyms,
            ]
        )
    return data, header


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
        type=int,
        help="Only include languages with at least M% concepts",
        metavar="M",
    )
    # parser.add_argument(
    #     "--languages-only",
    #     "-l",
    #     action="store_true",
    #     default=False,
    #     help="Only list matching languages, don't report statistics",
    # )
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
        dataset, args.min_percentage, args.with_concept, args.missing
    )

    # TODO: consider generic way of writing the header
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
            tablefmt="pretty",
        )
    )

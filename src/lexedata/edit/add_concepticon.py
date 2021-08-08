import collections
import typing as t

from csvw.metadata import URITemplate

import pycldf
import cldfcatalog
import cldfbench
from pyconcepticon.glosses import concept_map2

from lexedata.edit.add_status_column import add_status_column_to_table
import lexedata.cli as cli

concepticon_path = cldfcatalog.Config.from_file().get_clone("concepticon")
concepticon = cldfbench.catalogs.Concepticon(concepticon_path)


def equal_separated(option: str) -> t.Tuple[str, str]:
    column, language = option.split("=")
    return column.strip(), language.strip()


def add_concepticon_names(
    dataset: pycldf.Wordlist,
    column_name: str = "Concepticon_Gloss",
):
    # Create a concepticonReference column
    try:
        dataset.add_columns("ParameterTable", column_name)
        dataset.write_metadata()
    except ValueError:
        pass

    write_back = []
    for row in cli.tq(dataset["ParameterTable"], task="Write concepts with concepticon names to dataset"):
        try:
            row[column_name] = concepticon.api.conceptsets[
                row[dataset.column_names.parameters.concepticonReference]
            ].gloss
        except KeyError:
            pass

        write_back.append(row)

    dataset.write(ParameterTable=write_back)


def add_concepticon_references(
    dataset: pycldf.Wordlist,
    gloss_languages: t.Mapping[str, str],
    status_update: t.Optional[str],
    overwrite: bool = False,
) -> None:
    """Guess Concepticon links for a multilingual Concept table.

    Fill the concepticonReference column of the dateset's ParameterTable with
    best guesses for Concepticon IDs, based on gloss columns in different
    languages.

    Parameters
    ==========
    dataset: A pycldf.Wordlist with a concepticonReference column in its
        ParameterTable
    gloss_languages: A mapping from ParameterTable column names to ISO-639-1
        language codes that Concepticon has concept lists for (eg. en, fr, de,
        es, zh, pt)
    status_update: String written to Status_Column of #parameterTable if provided
    overwrite: Overwrite existing Concepticon references

    """
    # TODO: If this function took only dataset["ParameterTable"] and the name
    # of the target column in there as arguments, one could construct examples
    # that just use the Iterable API and therefore look nice as doctests.
    gloss_lists: t.Dict[str, t.List[str]] = {column: [] for column in gloss_languages}

    for row in dataset["ParameterTable"]:
        for column, glosses in gloss_lists.items():
            glosses.append(row[column] or "?")  # Concepticon abhors empty glosses.

    targets = {
        language: concepticon.api._get_map_for_language(language, None)
        for language in gloss_languages.values()
    }

    cmaps: t.List[t.Dict[int, t.Tuple[t.List[int], int]]] = [
        (
            concept_map2(
                glosses,
                [i[1] for i in targets[gloss_languages[column]]],
                similarity_level=2,
                language=gloss_languages[column],
            ),
            # What a horrendous API! Why can't it return glosses or IDs instead
            # of, as it does now, target-indices so I have to schlepp target along
            # with the results?
            targets[gloss_languages[column]],
        )
        for column, glosses in gloss_lists.items()
    ]

    write_back = []
    for i, row in cli.tq(enumerate(dataset["ParameterTable"]), task="Write concepts with concepticon reference to dataset"):
        if overwrite or not row.get(
            dataset.column_names.parameters.concepticonReference
        ):
            matches = [(m.get(i, ([], 10)), t) for m, t in cmaps]
            best_sim = min(x[0][1] for x in matches)
            best_matches = [t[m] for (ms, s), t in matches for m in ms if s <= best_sim]
            c: t.Counter[str] = collections.Counter(id for id, string in best_matches)
            if len(c) > 1:
                print(row, best_sim, c.most_common())
                row[
                    dataset.column_names.parameters.concepticonReference
                ] = c.most_common(1)[0][0]
            elif len(c) < 1:
                print(row)
            else:
                row[
                    dataset.column_names.parameters.concepticonReference
                ] = c.most_common(1)[0][0]
        # add status update if given
        if status_update:
            row["Status_Column"] = status_update
        write_back.append(row)

    dataset.write(ParameterTable=write_back)


def add_concepticon_definitions(
    dataset: pycldf.Dataset,
    column_name: str = "Concepticon_Definition",
    logger: cli.logging.Logger = cli.logger,
) -> None:
    concepticon_ids = dataset.column_names.parameters.concepticonReference
    if concepticon_ids is None:
        logger.error(
            "Your concepts table has no #concepticonReference column, so I cannot add any definitions from Concepticon to it. Try running lexedata.edit.add_conception to have me guess those references."
        )
        return

    # Create a concepticon_definition column
    try:
        dataset["ParameterTable", column_name]
        logger.info(
            "Overwriting existing {:} column in concepts table".format(column_name)
        )
    except KeyError:
        dataset.add_columns("ParameterTable", column_name)
        dataset.write_metadata()
        # Now if this throws an exception, it's an unexpected exception.

    # write concepticon definitions
    write_back = []
    for row in cli.tq(dataset["ParameterTable"], task="Write concepts with concepticon definitions to dataset"):
        try:
            row[column_name] = concepticon.api.conceptsets[
                row[concepticon_ids]
            ].definition
        except KeyError:
            pass
        write_back.append(row)

    dataset.write(ParameterTable=write_back)


def create_concepticon_for_concepts(
    dataset: pycldf.Dataset,
    language: t.Iterable,
    concepticon_glosses: bool,
    concepticon_definition: bool,
    overwrite: bool,
    status_update: t.Optional[str],
):
    # add Status_Column if status update
    if status_update:
        add_status_column_to_table(dataset=dataset, table_name="ParameterTable")
    # add Concepticon_ID column to ParameterTable
    if dataset.column_names.parameters.concepticonReference is None:
        # Create a concepticonReference column
        dataset.add_columns("ParameterTable", "Concepticon_ID")
        c = dataset["ParameterTable"].tableSchema.columns[-1]
        c.valueUrl = "http://concepticon.clld.org/parameters/{Concepticon_ID}"
        c.propertyUrl = URITemplate(
            "http://cldf.clld.org/v1.0/terms.rdf#concepticonReference"
        )
        dataset.write_metadata()
    if not language:
        language = [(dataset.column_names.parameters.id, "en")]

    gloss_languages: t.Dict[str, str] = dict(language)
    add_concepticon_references(
        dataset,
        gloss_languages=gloss_languages,
        status_update=status_update,
        overwrite=overwrite,
    )

    if concepticon_glosses:
        add_concepticon_names(dataset)
    if concepticon_definition:
        add_concepticon_definitions(dataset=dataset)


if __name__ == "__main__":
    parser = cli.parser(description="Adds Concepticon reference to #parameterTable")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Set concepticon reference even if one exists already",
    )
    parser.add_argument(
        "--add-concept-set-names",
        action="store_true",
        default=False,
        help="Add/update a column containing Concepticon's concept set names (glosses)",
    )
    parser.add_argument(
        "--add-definitions",
        action="store_true",
        default=False,
        help="Add/update a column containing Concepticon's concept set definitions, for quick disambiguation",
    )
    parser.add_argument(
        "--gloss-language",
        "-l",
        action="append",
        default=[],
        type=equal_separated,
        help="Maps from column names to language codes, eg. '-l GLOSS=en -l PORTUGUESE=pt'. "
        "If no language mappings are given, try to understand the #id column in English.",
    )
    parser.add_argument(
        "--status-update",
        type=str,
        default="automatic Concepticon link",
        help="Text written to Status_Column. Set to 'None' for no status update. "
        "(default: automatic Concepticon link)",
    )
    args = parser.parse_args()
    if args.status_update == "None":
        args.status_update = None

    create_concepticon_for_concepts(
        dataset=pycldf.Wordlist.from_metadata(args.metadata),
        language=args.language,
        concepticon_glosses=args.concepticon_glosses,
        concepticon_definition=args.concepticon_definition,
        overwrite=args.overwrite,
        status_update=args.status_update,
    )

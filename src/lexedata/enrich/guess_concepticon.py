import argparse
import typing as t
from pathlib import Path

from csvw.metadata import URITemplate

import pycldf
import pyconcepticon
import cldfcatalog
from cldfcatalog import Catalog
import cldfbench
from pyconcepticon.glosses import concept_map, concept_map2

concepticon_path = cldfcatalog.Config.from_file().get_clone('concepticon')
concepticon = cldfbench.catalogs.Concepticon(concepticon_path)

def equal_separated(option: str) -> t.Tuple[str, str]:
    column, language = option.split("=")
    return column.strip(), language.strip()

def add_concepticon_references(
        dataset: pycldf.Wordlist,
        gloss_languages: t.Mapping[str, str]) -> None:
    """Guess Concepticon links for a multilingual Concept table.

    Fill the concepticonReference column of the dateset's ParameterTable with
    best guesses for Concepticon IDs, based on gloss columns in different
    languages.

    Parameters
    ==========
    dataset: A pycldf.Wordlist with a concepticonReference column in its
        ParameterTable
    gloss_lang: A mapping from ParameterTable column names to ISO-639-1
        language codes that Concepticon has concept lists for (eg. en, fr, de,
        es, zh, pt)

    """
    # TODO: If this function took only dataset["ParameterTable"] and the name
    # of the target column in there as arguments, one could construct examples
    # that just use the Iterable API and therefore look nice as doctests.
    gloss_lists: t.Dict[str, t.List[str]] = {column: [] for column in gloss_languages}

    for row in dataset["ParameterTable"]:
        for column, glosses in gloss_lists.items():
            glosses.append(row[column] or '?')  # Concepticon abhors empty glosses.

    targets = {language: concepticon.api._get_map_for_language(language, None)
            for language in gloss_languages.values()}


    cmaps: t.List[t.Dict[int, t.Tuple[t.List[int], int]], ] = [
        (concept_map2(
            glosses,
            [i[1] for i in targets[gloss_languages[column]]],
            similarity_level=2,
            language=gloss_languages[column]),
         # What a horrendous API! Why can't it return glosses or IDs instead
         # of, as it does now, target-indices so I have to schlepp target along
         # with the results?
         targets[gloss_languages[column]])
        for column, glosses in gloss_lists.items()
    ]

    write_back = []
    for i, row in enumerate(dataset["ParameterTable"]):
        matches = [(m.get(i, ([], 10)), t) for m, t in cmaps]
        best_sim = min(x[0][1] for x in matches)
        best_matches = [t[m]
                        for (ms, s), t in matches
                        for m in ms
                        if s <= best_sim]
        c: t.Counter[str] = t.Counter(id for id, string in best_matches)
        if len(c) > 1:
            print(row, best_sim, c.most_common())
            row[dataset.column_names.parameters.concepticonReference] = c.most_common(1)[0][0]
        elif len(c) < 1:
            print(row)
        else:
            row[dataset.column_names.parameters.concepticonReference] = c.most_common(1)[0][0]
        write_back.append(row)

    dataset.write(ParameterTable=write_back)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("wordlist", default="cldf-metadata.json",
                        type=Path, help="The wordlist to add Concepticon links to")
    parser.add_argument("--language", "-l",
                        action="append",
                        default=[],
                        type=equal_separated,
                        help="Maps from column names to language codes, eg. GLOSS=en")
    args = parser.parse_args()

    dataset = pycldf.Wordlist.from_metadata(args.wordlist)

    if dataset.column_names.parameters.concepticonReference is None:
        # Create a concepticonReference column
        dataset.add_columns("ParameterTable", "Concepticon_ID")
        c = dataset["ParameterTable"].tableSchema.columns[-1]
        c.valueUrl = "http://concepticon.clld.org/parameters/{Concepticon_ID}"
        c.propertyUrl = URITemplate("https://cldf.clld.org/v1.0/terms.rdf#concepticonReference")
        dataset.column_names.parameters.concepticonReference = "Concepticon_ID"
        dataset.write_metadata()

        # Reload dataset
        dataset = pycldf.Wordlist.from_metadata(args.wordlist)

    if not args.language:
        args.language = [(dataset.column_names.parameters.id, "en")]

    gloss_languages: t.Dict[str, str] = dict(args.language)

    add_concepticon_references(dataset, gloss_languages)


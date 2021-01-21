import argparse
import typing as t
from pathlib import Path

import pycldf

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarise coverage data")
    parser.add_argument(
        "--min-concepts",
        default=0,
        type=int,
        help="Only include languages with at least M concepts",
        metavar="M",
    )
    parser.add_argument(
        "-l",
        action="store_true",
        default=False,
        help="Only list matching languages, don't report statistics",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default="Wordlist-metadata.json",
        help="Path to the JSON metadata file describing the dataset (default: ./Wordlist-metadata.json)",
    )
    parser.add_argument(
        "--metadata-or-forms",
        type=Path,
        default="forms.csv",
        help="Path to the JSON metadata or forms.csv file, i.e. metadata-free wordlist "
        "(default: ./forms.csv)",
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
        "--missing",
        action="store_true",
        default=False,
        help="Ignore missing forms, i.e. FormTable entries with CLDF #form '?'",
    )
    args = parser.parse_args()

    if args.metadata_or_forms.name == "forms.csv":
        dataset = pycldf.Wordlist.from_data(args.metadata_or_forms)
    else:
        dataset = pycldf.Wordlist.from_metadata(args.metadata)

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
        if form[c_form] == "?" and args.missing:
            continue
        if multiple_concepts:
            for c in form[c_concept]:
                concepts[form[c_language]][c] += 1
        else:
            concepts[form[c_language]][form[c_concept]] += 1

    for language, metadata in languages.items():
        conceptlist = concepts[language]
        synonyms = sum(conceptlist.values()) / len(conceptlist)
        include = True
        if len(conceptlist) < args.min_concepts:
            include = False
        for c in args.with_concept:
            if c not in conceptlist:
                include = False
        if not include:
            continue
        if args.l:
            print(language)
        else:
            print(metadata, len(conceptlist), synonyms)

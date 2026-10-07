# -*- coding: utf-8 -*-
import typing as t
from pathlib import Path
from typing import List, Any, Mapping

import pycldf

from lexedata import cli
from lexedata.util import cache_table, ensure_list


def parser():
    parser = cli.parser(
        __package__ + "." + Path(__file__).stem,
        description="Create a new dataset from an existing dataset, filtering to a subset of languages, concepts and/or cognatesets",
    )
    parser.add_argument(
        # MAKE COMPULSORY!
        "--new-dataset-path",
        type=Path,
        help="The path to put the new dataset into",
    )
    parser.add_argument(
        "--concepts",
        action=cli.SetOrFromFile,
        help="Concepts to include in the new dataset.",
    )
    parser.add_argument(
        "--languages",
        action=cli.SetOrFromFile,
        help="Languages to include in the new dataset.",
    )
    parser.add_argument(
        "--cognatesets",
        action=cli.SetOrFromFile,
        help="Cognatesets to include in the new dataset.",
    )
    parser.add_argument(
        "--keep-unassigned-forms",
        type={"True": True, "False": False}.get,
        choices=("True", "False"),
        default=True,
        help="Should forms not assigned to any cognateset "
        "(or assigned to a cognateset not to be included in the new dataset)"
        "be included in the new dataset? Default = True)",
    )
    return parser


def test_subset():
    ...
    all_forms_by_id: dict[str, dict[str, t.Any]] = {
        "f1": {"ID": "f1", "Language_ID": "abui1241"},
        "f2": {"ID": "f2", "Language_ID": "abui1243"},
    }
    all_forms_by_id["f1"]["Language_ID"] == "abui1241"


def write_changed_dataset_to_new_path(
    dataset: pycldf.Wordlist,
    changed_tables: dict[str, t.Iterable[Mapping[str, t.Any]]],
    new_path: Path,
):
    output_tables: dict[str, t.Iterable[Mapping[str, t.Any]]] = {
        table.url: cache_table(dataset, table.url.string).values()
        for table in dataset.tables
        if not table.common_props.get("dc:conformsTo", "").endswith("FormTable")
        if not table.common_props.get("dc:conformsTo", "").endswith("LanguageTable")
        if not table.common_props.get("dc:conformsTo", "").endswith("ParameterTable")
        if not table.common_props.get("dc:conformsTo", "").endswith("CognatesetTable")
        if not table.common_props.get("dc:conformsTo", "").endswith("CognateTable")
    }

    dataset.tablegroup._fname = new_path / dataset.tablegroup._fname.name
    output_tables.update(changed_tables)

    if dataset.sources and not dataset.properties.get("dc:source"):
        dataset.properties["dc:source"] = "sources.bib"
    dataset.write_sources()

    for table_type, items in output_tables.items():
        table = dataset[table_type]
        table.common_props["dc:extent"] = table.write(items)

    dataset.write_metadata()


if __name__ == "__main__":  # pragma: no cover
    args = parser().parse_args()
    t.cast(Path, args.new_dataset_path).mkdir(exist_ok=False, parents=True)
    logger = cli.setup_logging(args)

    dataset = pycldf.Wordlist.from_metadata(args.metadata)

    if ("LanguageTable", "parameterReference") in dataset:
        cli.Exit.INVALID_DATASET(
            "I cannot deal with a parameterReference (concept) column in your language table."
        )
    if ("ParameterTable", "languageReference") in dataset:
        cli.Exit.INVALID_DATASET(
            "I cannot deal with a languageReference column in your concept table."
        )

    # select languages from languages.
    c_l_id = dataset["LanguageTable", "id"].name
    relevant_language_ids = args.languages
    l_columns = [column.name for column in dataset["LanguageTable"].tableSchema.columns]
    relevant_languages = cache_table(
        dataset,
        "LanguageTable",
        columns=dict(zip(l_columns, l_columns)),
        filter=lambda row: row[c_l_id] in relevant_language_ids,
    )

    # select concepts from parameters.csv
    c_c_id = dataset["ParameterTable", "id"].name
    relevant_concept_ids = args.concepts
    c_columns = [
        column.name for column in dataset["ParameterTable"].tableSchema.columns
    ]
    relevant_concepts = cache_table(
        dataset,
        "ParameterTable",
        columns=dict(zip(c_columns, c_columns)),
        filter=lambda row: row[c_c_id] in relevant_concept_ids,
    )

    # TODO: select cognatesets from table
    try:
        c_s_id = dataset["CognatesetTable", "id"].name
        s_columns = [
            column.name for column in dataset["CognatesetTable"].tableSchema.columns
        ]
        relevant_cognatesets = cache_table(
            dataset,
            "CognatesetTable",
            columns=dict(zip(s_columns, s_columns)),
            filter=lambda row: row[c_s_id] in args.cognatesets,
        )
        print(relevant_cognatesets)
    except KeyError:
        relevant_cognatesets = ...  # Something better, we'll sort this in a moment

    # get the right forms, then look them up in cognates.csv
    #    then pull all referenced cognatesets
    #    get all sources from all files from sources bib.

    columns = [column.name for column in dataset["FormTable"].tableSchema.columns]
    if args.keep_unassigned_forms:
        c_f_lang = dataset["FormTable", "languageReference"].name
        c_f_concept = dataset["FormTable", "parameterReference"].name

        def form_filter(form_row: Mapping[str, t.Any]) -> bool:
            concept = form_row[c_f_concept]
            if isinstance(concept, list):
                concept = [c for c in concept if c in relevant_concept_ids]
                if len(concept) == 0:
                    return False
                form_row[c_f_concept] = concept
            else:
                if concept not in relevant_concept_ids:
                    return False
            return form_row[c_f_lang] in relevant_language_ids

    else:

        def form_filter(form_row: Mapping[str, t.Any]) -> bool:
            raise NotImplementedError
            # filter by judgements in addition to the stuff above!

    relevant_forms = cache_table(
        dataset,
        table="FormTable",
        columns=dict(zip(columns, columns)),
        filter=form_filter,
    )

    try:
        c_j_form = dataset["CognateTable", "formReference"].name
        j_columns = [
            column.name for column in dataset["CognateTable"].tableSchema.columns
        ]
        relevant_judgements = cache_table(
            dataset,
            "CognateTable",
            columns=dict(zip(j_columns, j_columns)),
            filter=lambda row: row[c_j_form] in relevant_forms,
        )
    except KeyError:
        # We don't have a cognate judgement table
        ...

    c_j_cognateset = dataset["CognateTable", "cognatesetReference"].name
    c_f_source = dataset["FormTable", "source"].name

    relevant_cognateset_ids = set()
    for id, row in relevant_judgements.items():
        if row[c_j_cognateset] not in relevant_cognateset_ids:
            relevant_cognateset_ids.add(row[c_j_cognateset])

    s_columns = [
        column.name for column in dataset["CognatesetTable"].tableSchema.columns
    ]
    relevant_cognatesets = cache_table(
        dataset,
        "CognatesetTable",
        columns=dict(zip(s_columns, s_columns)),
        filter=lambda row: row[c_s_id] in relevant_cognateset_ids,
    )

    relevant_source_ids = set()
    for id, row in relevant_forms.items():
        for source_id in ensure_list(row[c_f_source]):
            if source_id not in relevant_source_ids:
                relevant_source_ids.add(source_id)

    new_sources = pycldf.Sources()
    for source in list(dataset.sources):
        source_id = source.id
        if source_id in relevant_source_ids:
            new_sources.add(source)

    # when we want part of the cognatesets:
    # if there are cognatesets listed in the arg, then compare the remaining cognatesets (after any language/concept filtering is done) with the ones to include
    # get list of cognatesets to delete
    # WARNING: a cognateset instructed to include is excluded because of lang/concept choice (give preference to lang/concept choice)
    # delete all judgements that references the cognatesets to delete while keeping a list of all referenced forms
    # delete all forms that are in the list of forms to delete, unless they are referenced in a judgement that is not deleted
    # WARNING: a concept/lang combination is not included because of a cognateset instructed to not include
    # first get a list of cognatesets and then filter the cognates.csv the same way we do for forms
    # adjust some minor stuff in json (only numbers, right?)
    # option to have a plain dataset without cognatesets?
    # option to retain unassigned forms to given cognatesets or not

    new_form_table: List[Mapping[str, Any]] = list(relevant_forms.values())
    new_parameter_table: List[Mapping[str, Any]] = list(relevant_concepts.values())
    new_language_table: List[Mapping[str, Any]] = list(relevant_languages.values())
    new_cognate_table: List[Mapping[str, Any]] = list(relevant_judgements.values())
    new_cognateset_table: List[Mapping[str, Any]] = list(relevant_cognatesets.values())
    # print(new_cognateset_table)
    # up to here the fields id and name are filled in correctly. However they are listed as id and name, rather than ID
    # and Name which are the column names in the dataset. Only the fields BLR Index and BLR Root which are identical in
    # the print command and in the table are filled in correctly.
    write_changed_dataset_to_new_path(
        dataset,
        {
            "FormTable": new_form_table,
            "ParameterTable": new_parameter_table,
            "LanguageTable": new_language_table,
            "CognateTable": new_cognate_table,
            "CognatesetTable": new_cognateset_table,
        },
        new_path=args.new_dataset_path,
    )

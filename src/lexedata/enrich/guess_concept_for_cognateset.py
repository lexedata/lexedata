import argparse
import typing as t
from pathlib import Path
from tqdm import tqdm
from csvw.metadata import URITemplate
import pycldf
import networkx
from lexedata.util import load_clics


def load_concepts_by_form(dataset: pycldf.Dataset) -> t.Dict[str, str]:
    try:
        clics = load_clics()
    except FileNotFoundError:
        clics = None

    if clics and dataset.column_names.parameters.concepticonReference:
        concept_to_concepticon = {
            row[dataset.column_names.parameters.id]: row[
                dataset.column_names.parameters.concepticonReference
            ]
            for row in dataset["ParameterTable"]
        }
        concepticon_to_concept = {
            row[dataset.column_names.parameters.concepticonReference]: row[
                dataset.column_names.parameters.id
            ]
            for row in dataset["ParameterTable"]
        }
        concepticon_concepts_by_form_id: t.Dict[
            t.Hashable, t.List[t.Optional[t.Hashable]]
        ] = {}
        concepts = dataset["FormTable"].get_column(
            dataset.column_names.forms.parameterReference
        )
        multi = bool(concepts.separator)
        for form in tqdm(dataset["FormTable"]):
            if multi:
                concepticon_concepts_by_form_id[form[dataset.column_names.forms.id]] = [
                    concept_to_concepticon.get(c) for c in form[concepts.name]
                ]
            else:
                concepticon_concepts_by_form_id[form[dataset.column_names.forms.id]] = [
                    concept_to_concepticon.get(form[concepts.name])
                ]

        central_concepts = {}
        for form_id, concepts in tqdm(concepticon_concepts_by_form_id.items()):
            centrality = networkx.algorithms.centrality.betweenness_centrality(
                clics.subgraph([c for c in concepts if c])
            )
            central_concepts[form_id] = concepticon_to_concept.get(
                max(centrality or concepts, key=lambda k: centrality.get(k, -1))
            )
        print(central_concepts)
        return central_concepts
    # if no concepticon references are given or clicks is not available
    central_concepts_by_form_id = dict()
    c_f_id = dataset.column_names.forms.id
    c_f_concept = dataset.column_names.forms.parameterReference
    for form in dataset["FormTable"]:
        concept = form.get(c_f_concept, "")
        central_concepts_by_form_id[form[c_f_id]] = (
            concept if type(concept) == str else concept[0]
        )
    return central_concepts_by_form_id


def reshape_dataset(dataset: pycldf.Dataset, add_column: bool = True) -> pycldf.Dataset:

    # check for existing cognateset table
    if dataset.column_names.cognatesets is None:
        # Create a Cognateset Table
        dataset.add_component("CognatesetTable")

    # add a concept column to the cognateset table
    if add_column:
        if dataset.column_names.cognatesets.parameterReference is None:
            dataset.add_columns("CognatesetTable", "Core_Concept_ID")
            c = dataset["CognatesetTable"].tableSchema.columns[-1]
            c.datatype = dataset["ParameterTable", "ID"].datatype
            c.propertyUrl = URITemplate(
                "http://cldf.clld.org/v1.0/terms.rdf#parameterReference"
            )
            fname = dataset.write_metadata()
            # Reload dataset with new column definitions
            dataset = pycldf.Wordlist.from_metadata(fname)
    return dataset


def add_central_concepts_to_cognateset_table(
    dataset: pycldf.Dataset, add_column: bool = True, overwrite_existing: bool = True
) -> pycldf.Dataset:
    central_concept_by_form_id = load_concepts_by_form(dataset)
    dataset = reshape_dataset(dataset, add_column=add_column)
    # Check whether cognate judgements live in the FormTable …
    c_cognateset = dataset.column_names.forms.cognatesetReference
    c_form = dataset.column_names.forms.id
    table = dataset["FormTable"]
    # … or in a separate CognateTable
    if c_cognateset is None:
        c_cognateset = dataset.column_names.cognates.cognatesetReference
        c_form = dataset.column_names.cognates.formReference
        table = dataset["CognateTable"]

    if c_cognateset is None:
        raise ValueError(
            f"Dataset {dataset:} had no cognatesetReference column in a CognateTable"
            " or a FormTable and is thus not compatible with this script."
        )
    c_core_concept = dataset.column_names.cognatesets.parameterReference
    if c_core_concept is None:
        raise ValueError(
            f"Dataset {dataset:} had no parameterReference column in a CognatesetTable"
            " and is thus not compatible with this script."
        )
    # check all cognatesets in table
    write_back = []
    cognatesets = set()
    for row in tqdm(dataset["CognatesetTable"]):
        write_back.append(row)
        cognatesets.add(row[dataset.column_names.cognatesets.id])
    # Load judgements, making sure all cognatesets exist
    for row in tqdm(table):
        if row[c_cognateset] not in cognatesets:
            write_back.append({dataset.column_names.cognatesets.id: row[c_cognateset]})
    dataset.write(CognatesetTable=write_back)
    cognatesets = set()
    for row in tqdm(dataset["CognatesetTable"]):
        cognatesets.add(row[dataset.column_names.cognatesets.id])
    # central concepts by cogset id
    concepts_by_cogset: t.Dict[t.Hashable, t.Hashable] = dict()
    for row in tqdm(table):
        cognateset = row[c_cognateset]
        form = row[c_form]
        concepts_by_cogset[cognateset] = central_concept_by_form_id[form]
    print(concepts_by_cogset)
    # write cognatesets with central concepts
    write_back = []
    for row in tqdm(dataset["CognatesetTable"]):
        if row[dataset.column_names.cognatesets.id] not in concepts_by_cogset:
            print(row)
            write_back.append(row)
            continue
        if row[c_core_concept] and not overwrite_existing:
            write_back.append(row)
            continue
        row[c_core_concept] = concepts_by_cogset[
            row[dataset.column_names.cognatesets.id]
        ]
        write_back.append(row)
    print(write_back)
    dataset.write(CognatesetTable=write_back)
    return dataset


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "wordlist",
        default="cldf-metadata.json",
        type=Path,
        help="The wordlist to add Concepticon links to",
    )
    parser.add_argument(
        "add-column",
        default=False,
        action="store_true",
        help="Activate to add a new column Core_Concept_ID to cognatesetTable",
    )
    parser.add_argument(
        "--overwrite_existing",
        action="store_true",
        default=False,
        help="Activate to overwrite existing Core_Concept_ID of cognatesets",
    )
    args = parser.parse_args()

    dataset = pycldf.Wordlist.from_metadata(args.wordlist)
    dataset = add_central_concepts_to_cognateset_table(
        dataset, add_column=args.add_column, overwrite_existing=args.overwrite_existing
    )

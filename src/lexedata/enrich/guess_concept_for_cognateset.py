import argparse
import typing as t
from pathlib import Path

from tqdm import tqdm

from csvw.metadata import URITemplate

import pycldf
import pyconcepticon
import cldfcatalog
from cldfcatalog import Catalog
import cldfbench
from pyconcepticon.glosses import concept_map, concept_map2

concepticon_path = cldfcatalog.Config.from_file().get_clone('concepticon')
concepticon = cldfbench.catalogs.Concepticon(concepticon_path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("wordlist", default="cldf-metadata.json",
                        type=Path, help="The wordlist to add Concepticon links to")
    parser.add_argument("--no-add-column", default=False, action="store_true",
                        help="Add the column?")
    args = parser.parse_args()

    dataset = pycldf.Wordlist.from_metadata(args.wordlist)

    # Is there a cognateset table?
    if dataset.column_names.cognatesets is None:
        # Create a Cognateset Table
        dataset.add_component("CognatesetTable")

    # May I add a concept column to the cognateset table?
    if not args.no_add_column:
        dataset.add_columns("CognatesetTable", "Core_Concept_ID")
        c = dataset["CognatesetTable"].tableSchema.columns[-1]
        c.datatype = dataset["ParameterTable", "ID"].datatype
        c.propertyUrl = URITemplate("http://cldf.clld.org/v1.0/terms.rdf#parameterReference")
        dataset.write_metadata()

        # Reload dataset with new column definitions
        dataset = pycldf.Wordlist.from_metadata(args.wordlist)

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
            raise ValueError(f"Dataset {dataset:} had no cognatesetReference column in a CognateTable or a FormTable and is thus not compatible with this script.")

    print("Loading cognatesets…")
    cognatesets = set()
    write_back = []
    for row in tqdm(dataset["CognatesetTable"]):
        write_back.append(row)
        cognatesets.add(row[dataset.column_names.cognatesets.id])

    print("Loading judgements, making sure all cognatesets exist…")
    for row in tqdm(table):
        if row[c_cognateset] not in cognatesets:
            write_back.append({dataset.column_names.cognatesets.id: row[c_cognateset]})

    dataset.write(CognatesetTable=write_back)

    concept_to_concepticon = {
        row[dataset.column_names.parameters.id]:
        row[dataset.column_names.parameters.concepticonReference]
        for row in dataset["ParameterTable"]
    }
    concepticon_to_concept = {
        row[dataset.column_names.parameters.concepticonReference]:
        row[dataset.column_names.parameters.id]
        for row in dataset["ParameterTable"]
    }


    concepts = dataset['FormTable'].get_column(dataset.column_names.forms.parameterReference)
    multi = bool(concepts.separator)
    concepts_by_form: t.Dict[t.Hashable, t.List[t.Optional[t.Hashable]]] = {}
    print("Loading form concepts…")
    for form in tqdm(dataset['FormTable']):
        if multi:
            concepts_by_form[form[dataset.column_names.forms.id]] = [
                concept_to_concepticon.get(c)
                for c in form[concepts.name]]
        else:
            concepts_by_form[form[dataset.column_names.forms.id]] = [
                concept_to_concepticon.get(form[concepts.name])]

    concepts_by_cogset: t.DefaultDict[t.Hashable, t.Counter[t.Optional[t.Hashable]]] = t.DefaultDict(t.Counter)
    print("Matching judgements…")
    for row in tqdm(table):
        cognateset = row[c_cognateset]
        form = row[c_form]
        concepts_by_cogset[cognateset].update(concepts_by_form[form])

    import networkx
    clics = networkx.parse_gml(
        (Path(__file__).parent / '../../../network-3-families.gml').open()
    )
    r = {}
    print("Finding central concepts…")
    for cognateset, concepts in tqdm(concepts_by_cogset.items()):
        centrality = networkx.algorithms.centrality.betweenness_centrality(
            clics.subgraph([c for c in concepts if c]))
        r[cognateset] = max(centrality or concepts, key=lambda k: centrality.get(k, -1))

    write_back = []
    c_core_concept = dataset["CognatesetTable", "parameterReference"].name

    print("Setting central concepts…")
    for row in tqdm(dataset["CognatesetTable"]):
        if row[dataset.column_names.cognatesets.id] not in r:
            continue
        row[c_core_concept] = concepticon_to_concept[r[row[dataset.column_names.cognatesets.id]]]
        write_back.append(row)
    dataset.write(CognatesetTable=write_back)


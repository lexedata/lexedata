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

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("wordlist", default="cldf-metadata.json",
                        type=Path, help="The wordlist to add Concepticon links to")
    args = parser.parse_args()

    dataset = pycldf.Wordlist.from_metadata(args.wordlist)

    # Is there a cognateset table?
    if dataset.column_names.cognatesets is None:
        # Create a Cognateset Table
        dataset.add_component("CognatesetTable")
        dataset.add_columns("CognatesetTable", "Core_Concept_ID")
        c = dataset["CognatesetTable"].tableSchema.columns[-1]
        c.propertyUrl = URITemplate("https://cldf.clld.org/v1.0/terms.rdf#parameterReference")
        dataset.column_names.parameters.concepticonReference = "Core_Concept_ID"
        dataset.write_metadata()

        # Reload dataset
        dataset = pycldf.Wordlist.from_metadata(args.wordlist)

    c_cognateset = dataset.column_names.forms.cognatesetReference
    c_form = dataset.column_names.forms.id
    table = dataset["FormTable"]
    if c_cognateset is None:
        c_cognateset = dataset.column_names.cognates.cognatesetReference
        c_form = dataset.column_names.cognates.formReference
        table = dataset["CognateTable"]
    if c_cognateset is None:
            raise ValueError(f"Dataset {dataset:} had no cognatesetReference column in a CognateTable or a FormTable and is thus not compatible with this script.")

    cognatesets = set()
    write_back = []
    for row in dataset["CognatesetTable"]:
        write_back.append(row)
        cognatesets.add(dataset.column_names.cognatesets.id)

    for row in table:
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
    for form in dataset['FormTable']:
        if multi:
            concepts_by_form[form[dataset.column_names.forms.id]] = [
                concept_to_concepticon.get(c)
                for c in form[concepts.name]]
        else:
            concepts_by_form[form[dataset.column_names.forms.id]] = [
                concept_to_concepticon.get(form[concepts.name])]

    concepts_by_cogset: t.DefaultDict[t.Hashable, t.Counter[t.Optional[t.Hashable]]] = t.DefaultDict(t.Counter)
    for row in table:
        cognateset = row[c_cognateset]
        form = row[c_form]
        concepts_by_cogset[cognateset].update(concepts_by_form[form])

    import networkx
    clics = networkx.parse_gml(
        (Path(__file__).parent / '../../../network-3-families.gml').open()
    )
    r = {}
    for cognateset, concepts in concepts_by_cogset.items():
        centrality = networkx.algorithms.centrality.betweenness_centrality(
            clics.subgraph([c for c in concepts if c]))
        r[cognateset] = max(centrality, key=centrality.get)

    write_back = []
    for row in dataset["CognatesetTable"]:
        row["Core_Concept_ID"] = concepticon_to_concept[r[row[dataset.column_names.cognatesets.id]]]
        write_back.append(row)
    dataset.write(CognatesetTable=write_back)


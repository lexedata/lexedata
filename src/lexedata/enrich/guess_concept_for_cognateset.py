import argparse
import typing as t
from pathlib import Path
from tqdm import tqdm

from csvw.metadata import URITemplate
import pycldf
import cldfcatalog
import cldfbench
import networkx

from lexedata.util import load_clics

concepticon_path = cldfcatalog.Config.from_file().get_clone("concepticon")
concepticon = cldfbench.catalogs.Concepticon(concepticon_path)


class ConceptGuesser:
    def __init__(self, dataset: pycldf.Dataset, add_column: bool = True):
        self.dataset = self.reshape_dataset(dataset, add_column=add_column)
        if self.dataset.column_names.parameters.concepticonReference is None:
            raise ValueError(
                f"Dataset {self.dataset:} had no ConcepticonReference column in ParamterTable"
                "and is thus not compatible with ConceptGuesser."
            )
        self.concept_to_concepticon = {
            row[self.dataset.column_names.parameters.id]: row[
                self.dataset.column_names.parameters.concepticonReference
            ]
            for row in self.dataset["ParameterTable"]
        }
        self.concepticon_to_concept = {
            row[self.dataset.column_names.parameters.concepticonReference]: row[
                self.dataset.column_names.parameters.id
            ]
            for row in self.dataset["ParameterTable"]
        }

        self.concepticon_concepts_by_form_id: t.Dict[
            t.Hashable, t.List[t.Optional[t.Hashable]]
        ] = {}
        concepts = dataset["FormTable"].get_column(
            dataset.column_names.forms.parameterReference
        )
        multi = bool(concepts.separator)
        for form in tqdm(self.dataset["FormTable"]):
            if multi:
                self.concepticon_concepts_by_form_id[
                    form[self.dataset.column_names.forms.id]
                ] = [self.concept_to_concepticon.get(c) for c in form[concepts.name]]
            else:
                self.concepticon_concepts_by_form_id[
                    form[self.dataset.column_names.forms.id]
                ] = [self.concept_to_concepticon.get(form[concepts.name])]

        clics = load_clics()
        central_concepts = {}
        for form_id, concepts in tqdm(self.concepticon_concepts_by_form_id.items()):
            centrality = networkx.algorithms.centrality.betweenness_centrality(
                clics.subgraph([c for c in concepts if c])
            )
            central_concepts[form_id] = max(
                centrality or concepts, key=lambda k: centrality.get(k, -1)
            )
        self.central_concepticion_concepts_by_form_id = central_concepts

    @staticmethod
    def reshape_dataset(
        dataset: pycldf.Dataset, add_column: bool = True
    ) -> pycldf.Dataset:

        # Is there a cognateset table?
        if dataset.column_names.cognatesets is None:
            # Create a Cognateset Table
            dataset.add_component("CognatesetTable")

        # May I add a concept column to the cognateset table
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

    def get_central_concept_by_form_id(self, form_id: str):
        try:
            return self.concepticon_to_concept[
                self.central_concepticion_concepts_by_form_id[form_id]
            ]
        except KeyError:
            return None

    def add_central_concepts_to_cognateset_table(self):
        # Check whether cognate judgements live in the FormTable …
        c_cognateset = self.dataset.column_names.forms.cognatesetReference
        c_form = self.dataset.column_names.forms.id
        table = self.dataset["FormTable"]
        # … or in a separate CognateTable
        if c_cognateset is None:
            c_cognateset = self.dataset.column_names.cognates.cognatesetReference
            c_form = self.dataset.column_names.cognates.formReference
            table = self.dataset["CognateTable"]

        if c_cognateset is None:
            raise ValueError(
                f"Dataset {self.dataset:} had no cognatesetReference column in a CognateTable"
                " or a FormTable and is thus not compatible with this script."
            )
        c_core_concept = self.dataset.column_names.cognatesets.parameterReference
        if c_core_concept is None:
            raise ValueError(
                f"Dataset {self.dataset:} had no parameterReference column in a CognatesetTable"
                " and is thus not compatible with this script."
            )
        # check all cognatesets in table
        write_back = []
        cognatesets = set()
        for row in tqdm(self.dataset["CognatesetTable"]):
            write_back.append(row)
            cognatesets.add(row[self.dataset.column_names.cognatesets.id])
        # Load judgements, making sure all cognatesets exist
        for row in tqdm(table):
            if row[c_cognateset] not in cognatesets:
                write_back.append(
                    {self.dataset.column_names.cognatesets.id: row[c_cognateset]}
                )
        self.dataset.write(CognatesetTable=write_back)
        cognatesets = set()
        for row in tqdm(self.dataset["CognatesetTable"]):
            cognatesets.add(row[self.dataset.column_names.cognatesets.id])
        # central concepts by cogset id
        concepts_by_cogset: t.Dict[t.Hashable, t.Hashable] = dict()
        for row in tqdm(table):
            cognateset = row[c_cognateset]
            form = row[c_form]
            concepts_by_cogset[cognateset] = self.get_central_concept_by_form_id(form)
        # write cognatesets with central concepts
        write_back = []
        for row in tqdm(self.dataset["CognatesetTable"]):
            if row[self.dataset.column_names.cognatesets.id] not in concepts_by_cogset:
                continue
            row[c_core_concept] = concepts_by_cogset[
                row[self.dataset.column_names.cognatesets.id]
            ]
            write_back.append(row)
        self.dataset.write(CognatesetTable=write_back)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""
    Writes a concept reference column to #cognatesetTable based on the concepts linked to the cognateset
    through the cognate judgement.
    """)
    parser.add_argument(
        "--metadata",
        type=Path,
        default="Wordlist-metadata.json",
        help="Path to the JSON metadata file describing the dataset (default: ./Wordlist-metadata.json)",
    )
    parser.add_argument(
        "--no-add-column",
        default=False,
        action="store_true",
        help="Adds column 'Core_Concept_ID' to #cognatesetTable",
    )
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
        c.datatype = dataset["ParameterTable", "id"].datatype
        c.propertyUrl = URITemplate(
            "http://cldf.clld.org/v1.0/terms.rdf#parameterReference"
        )
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
        raise ValueError(
            f"Dataset {dataset:} had no cognatesetReference column in a CognateTable"
            " or a FormTable and is thus not compatible with this script."
        )

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

    concepts = dataset["FormTable"].get_column(
        dataset.column_names.forms.parameterReference
    )
    multi = bool(concepts.separator)
    concepts_by_form: t.Dict[t.Hashable, t.List[t.Optional[t.Hashable]]] = {}
    print("Loading form concepts…")
    for form in tqdm(dataset["FormTable"]):
        if multi:
            concepts_by_form[form[dataset.column_names.forms.id]] = [
                concept_to_concepticon.get(c) for c in form[concepts.name]
            ]
        else:
            concepts_by_form[form[dataset.column_names.forms.id]] = [
                concept_to_concepticon.get(form[concepts.name])
            ]

    concepts_by_cogset: t.DefaultDict[
        t.Hashable, t.Counter[t.Optional[t.Hashable]]
    ] = t.DefaultDict(t.Counter)
    print("Matching judgements…")
    for row in tqdm(table):
        cognateset = row[c_cognateset]
        form = row[c_form]
        concepts_by_cogset[cognateset].update(concepts_by_form[form])

    clics = load_clics()
    central_concepts = {}
    print("Finding central concepts…")
    for cognateset, concepts in tqdm(concepts_by_cogset.items()):
        centrality = networkx.algorithms.centrality.betweenness_centrality(
            clics.subgraph([c for c in concepts if c])
        )
        central_concepts[cognateset] = max(
            centrality or concepts, key=lambda k: centrality.get(k, -1)
        )

    write_back = []
    c_core_concept = dataset["CognatesetTable", "parameterReference"].name

    print("Setting central concepts…")
    for row in tqdm(dataset["CognatesetTable"]):
        if row[dataset.column_names.cognatesets.id] not in central_concepts:
            continue
        row[c_core_concept] = concepticon_to_concept[
            central_concepts[row[dataset.column_names.cognatesets.id]]
        ]
        write_back.append(row)
    dataset.write(CognatesetTable=write_back)

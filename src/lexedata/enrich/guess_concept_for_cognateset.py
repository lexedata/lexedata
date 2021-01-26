import typing as t
import collections
from pathlib import Path

from csvw.metadata import URITemplate
import pycldf
import networkx

from lexedata.util import load_clics

FormID = str
ConceptID = str
CognatesetID = str


def tqdm(iter, total=0):
    return iter


def load_concepts_by_form(
    dataset: pycldf.Dataset,
) -> t.Dict[FormID, t.Sequence[ConceptID]]:
    """Look up all concepts for each form, and return them as dictionary."""
    concepts_by_form_id: t.Dict[FormID, t.Sequence[ConceptID]] = {}
    c_f_id = dataset.column_names.forms.id
    c_f_concept = dataset.column_names.forms.parameterReference
    for form in tqdm(
        dataset["FormTable"],
        total=dataset["FormTable"].common_props.get("dc:extent"),
    ):
        concept = form.get(c_f_concept, [])
        concepts_by_form_id[form[c_f_id]] = (
            concept if isinstance(concept, list) else [concept]
        )
    return concepts_by_form_id


def concepts_to_concepticon(dataset: pycldf.Wordlist) -> t.Mapping[ConceptID, int]:
    concept_to_concepticon = {
        row[dataset.column_names.parameters.id]: row.get(
            dataset.column_names.parameters.concepticonReference
        )
        for row in tqdm(
            dataset["ParameterTable"],
            total=dataset["ParameterTable"].common_props.get("dc:extent"),
        )
    }
    return concept_to_concepticon


def central_concept(
    concepts: t.Counter[ConceptID],
    concepts_to_concepticon: t.Mapping[ConceptID, int],
    clics: t.Optional[networkx.Graph],
):
    """Find the most central concept among a weighted set.

    If the concepts are not linked to Concepticon/CLICS, we can only take the
    simple majority among the given concepts.

    >>> concepts = {"woman": 3, "mother": 4, "aunt": 3}
    >>> central_concept(concepts, {}, None)
    'mother'

    However, if the concepts can be linked to the CLICS graph, centrality
    actually can be defined using that graph.

    >>> concepticon_mapping = {"arm": 1673, "five": 493, "hand": 1277, "leaf": 628}
    >>> central_concept(
    ...   collections.Counter(["arm", "hand", "five", "leaf"]),
    ...   concepticon_mapping,
    ...   load_clics()
    ... )
    'hand'

    When counts and concepticon references are both given, the value with the
    maximum product of CLICS centrality and count is returned. If the concepts
    do not form a connected subgraph in CLICS (eg. 'five', 'hand', 'lower arm',
    'palm of hand' – with no attested form meaning 'arm' to link them), only
    centrality within the disjoint subgraphs is considered, so in this example,
    'hand' would be considered the most central concept.

    """
    centralities: t.Mapping[ConceptID, float]
    if clics is None:
        centralities = {}
    else:
        # In the extreme case, there is one concept in CLICS and one concept
        # without CLICS connection. Then there is no path, and the centralities
        # are 0 – including `endpoints=True` in `betweenness_centrality` does
        # not help with that, either.
        centralities = networkx.algorithms.centrality.betweenness_centrality(
            clics.subgraph(
                {str(concepts_to_concepticon.get(c)) for c in concepts} - {"None"}
            )
        )

    def effective_centrality(cc):
        concept, count = cc
        return count * (
            # So, the minimal betwenness centrality is 0. To not give concepts
            # outside CLICS an advantage, we need to assume a centrality of 0
            # when we don't know better – this is consistent with a
            # disconnected graph. To make different counts distinguishable, we
            # then need to 1 to the centrality, otherwise we end up with a lot
            # of concepts of effective count 0.
            centralities.get(str(concepts_to_concepticon.get(concept)), 0)
            + 1
        )

    concept, count = max(concepts.items(), key=effective_centrality)
    return concept


def reshape_dataset(
    dataset: pycldf.Wordlist, add_column: bool = True
) -> pycldf.Dataset:
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


def connected_concepts(
    dataset: pycldf.Wordlist,
) -> t.Mapping[CognatesetID, t.Counter[ConceptID]]:
    """For each cognate set it the data set, check which concepts it is connected to.

    >>>
    """
    concepts_by_form = load_concepts_by_form(dataset)
    cognatesets_to_concepts: t.DefaultDict[
        CognatesetID, t.Sequence[ConceptID]
    ] = t.DefaultDict(list)

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

    for judgement in tqdm(
        table,
        total=table.common_props.get("dc:extent"),
    ):
        cognatesets_to_concepts[judgement[c_cognateset]].extend(
            concepts_by_form[judgement[c_form]]
        )
    return {
        cogset: collections.Counter(concepts)
        for cogset, concepts in cognatesets_to_concepts.items()
    }


def add_central_concepts_to_cognateset_table(
    dataset: pycldf.Dataset,
    add_column: bool = True,
    overwrite_existing: bool = True,
) -> pycldf.Dataset:
    # create mapping cognateset to central concept
    try:
        clics: t.Optional[networkx.Graph] = load_clics()
    except FileNotFoundError:
        clics = None
    concepts_of_cognateset: t.Mapping[
        CognatesetID, t.Counter[ConceptID]
    ] = connected_concepts(dataset)
    central: t.MutableMapping[str, str] = {}
    if clics and dataset.column_names.parameters.concepticonReference:
        concept_to_concepticon = concepts_to_concepticon(dataset)
        for cognateset, concepts in concepts_of_cognateset.items():
            central[cognateset] = central_concept(
                concepts, concept_to_concepticon, clics
            )
    else:
        for cognateset, concepts in concepts_of_cognateset.items():
            central[cognateset] = central_concept(concepts, {}, None)
    dataset = reshape_dataset(dataset, add_column=add_column)
    c_core_concept = dataset.column_names.cognatesets.parameterReference
    if c_core_concept is None:
        raise ValueError(
            f"Dataset {dataset:} had no parameterReference column in a CognatesetTable"
            " and is thus not compatible with this script."
        )

    # write cognatesets with central concepts
    write_back = []
    for row in tqdm(
        dataset["CognatesetTable"],
        total=dataset["CognatesetTable"].common_props.get("dc:extent"),
    ):
        if not overwrite_existing and row[c_core_concept]:
            continue
        row[c_core_concept] = central.get(row[dataset.column_names.cognatesets.id])
        write_back.append(row)
    dataset.write(CognatesetTable=write_back)
    return dataset


if __name__ == "__main__":
    import argparse
    from tqdm import tqdm  # noqa

    parser = argparse.ArgumentParser(
        description="""Add central concepts to cognatesets.

        Write a concept reference column to #CognatesetTable based on the
        concepts linked to the cognateset through the cognate judgement, using
        the central concepts according to CLICS if links to Concepticon are
        available.

        You probably want to run this with `--add-column` (the default) the
        first time you run it, and with `--no-add-column --overwrite-existing`
        after you heavily edited the cognate sets afterwards."""
    )

    parser.add_argument(
        "--metadata",
        type=Path,
        default="Wordlist-metadata.json",
        help="Path to the JSON metadata file describing the dataset (default: ./Wordlist-metadata.json)",
    )
    parser.add_argument(
        "--add-column",
        default=True,
        action="store_true",
        help="Add column 'Core_Concept_ID' as new #parameterReference to #CognatesetTable (default)",
    )
    parser.add_argument(
        "--no-add-column",
        default=False,
        action="store_true",
        help="Do not add a new #parameterReference to #CognatesetTable, but instead use the existing one",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Overwrite #parameterReference values of cognate sets already given in the dataset",
    )
    args = parser.parse_args()
    dataset = pycldf.Wordlist.from_metadata(args.wordlist)

    add_central_concepts_to_cognateset_table(
        dataset,
        add_column=args.add_column,
        overwrite_existing=args.overwrite_existing,
    )

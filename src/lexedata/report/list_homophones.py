"""Generate a report of homophones.

List all groups of homophones in the dataset, together with (if available) the
minimal spanning tree according to clics, in order to identify polysemies vs.
accidental homophones

"""

from lexedata.util import load_clics
import typing as t

import networkx as nx

import pycldf

if __name__ == "__main__":
    dataset = pycldf.Wordlist.from_metadata("Wordlist-metadata.json")

    clics = load_clics()

    c_id = dataset["ParameterTable", "id"].name
    c_concepticon = dataset["ParameterTable", "concepticonReference"].name
    concepticon = {}
    for concept in dataset["ParameterTable"]:
        concepticon[concept[c_id]] = concept[c_concepticon]

    f_id = dataset["FormTable", "id"].name
    f_lang = dataset["FormTable", "languageReference"].name
    f_concept = dataset["FormTable", "parameterReference"].name
    f_form = dataset["FormTable", "form"].name

    homophones: t.DefaultDict[
        str, t.DefaultDict[str, t.Set[t.Tuple[str, str]]]
    ] = t.DefaultDict(lambda: t.DefaultDict(set))

    for form in dataset["FormTable"]:
        homophones[form[f_lang]][form[f_form]].add((form[f_concept], form[f_id]))

    for lang, forms in homophones.items():
        for form, meanings in forms.items():
            if len(meanings) == 1:
                continue
            clics_nodes = [concepticon.get(concept) for concept, form_id in meanings]
            if None in clics_nodes:
                clics_nodes = [c for c in clics_nodes if c]
                x = "(but at least one concept not found)"
            else:
                x = ""
            if len(clics_nodes) <= 1:
                print("Unknown:", lang, form, meanings)
            elif nx.is_connected(clics.subgraph(clics_nodes)):
                print("Connected:", x, lang, form, meanings)
            else:
                print("Unconnected:", x, lang, form, meanings)

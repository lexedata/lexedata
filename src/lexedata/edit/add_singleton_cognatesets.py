"""Add trivial cognatesets

Make sure that every segment of every form is in at least one cognateset
(there can be more than one, eg. for nasalization), by creating singleton
cognatesets for streaks of segments not in cognatesets.

"""
import typing as t
from collections import OrderedDict

import pycldf

# Type aliases, for clarity
CognatesetID = str
FormID = str

def create_singeltons(dataset: pycldf.Dataset):
    # cldf names and foreignkeys
    c_f_id = dataset["FormTable", "id"]
    c_cs_id = dataset["CognatesetTable", "id"].name
    c_cs_name = dataset["CognatesetTable", "name"].name
    foreign_key_form_cogset = ""
    for foreign_key in dataset["FormTable"].tableSchema.foreignKeys:
        if foreign_key.reference.resource == dataset["CognatesetTable"].url:
            foreign_key_form_cogset = foreign_key.columnReference[0]

    foreign_key_cognate_form = ""
    for foreign_key in dataset["CognateTable"].tableSchema.foreignKeys:
        if foreign_key.reference.resource == dataset["FormTable"].url:
            foreign_key_cognate_form = foreign_key.columnReference[0]
    foreign_key_cognate_cogset = ""
    for foreign_key in dataset["CognateTable"].tableSchema.foreignKeys:
        if foreign_key.reference.resource == dataset["CognatesetTable"].url:
            foreign_key_cognate_cogset = foreign_key.columnReference[0]
    # load data
    singleton_forms: t.Dict[FormID, OrderedDict] = {}
    for f in dataset["FormTable"]:
        singleton_forms[f[c_f_id]] = f
    all_judgements: t.Dict[CognatesetID, t.List[types.CogSet]] = {}
    for j in dataset["CognateTable"]:
        all_judgements.setdefault(j[foreign_key_cognate_cogset], []).append(j)
    all_cogsets = [c for c in dataset["CognatesetTable"]]
    for k in all_judgements:
        for j in all_judgements[k]:
            form_id = j[foreign_key_cognate_form]
            try:
                del singleton_forms[form_id]
            except KeyError:
                continue
    # create singletons for remaining forms and add singleton to cogsets
    for i, form_id in enumerate(singleton_forms):
        cogset_id =
        if db_name == c_cogset_id:
            value = f"X{i + 1}_{form[c_language]}"
        elif db_name == c_cogset_name:
            value = concept_id_by_form_id[form_id]
        elif db_name == c_cogset_concept:
            value = concept_id_by_form_id[form_id]
    # replace forms with new singleton cogset id

def
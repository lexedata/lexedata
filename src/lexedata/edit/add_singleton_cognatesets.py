"""Add trivial cognatesets

Make sure that every segment of every form is in at least one cognateset
(there can be more than one, eg. for nasalization), by creating singleton
cognatesets for streaks of segments not in cognatesets.

"""
import typing as t

import pycldf

from lexedata import types
from lexedata import cli

# Type aliases, for clarity
CognatesetID = str
FormID = str
ConceptID = str


def create_singeltons(dataset: pycldf.Dataset, logger: cli.logger = cli.logger):
    # cldf names and foreignkeys
    c_f_id = dataset["FormTable", "id"].name
    c_f_form = dataset["FormTable", "form"].name
    c_cs_id = dataset["CognatesetTable", "id"].name
    c_cs_name = dataset["CognatesetTable", "name"].name
    c_c_id = dataset["CognateTable", "id"].name

    status_column = None
    for column in dataset["CognatesetTable"].tableSchema.columns:
        if column.name == "Status_Column":
            status_column = column.name
    if not status_column:
        logger.warning(
            "No Status Column. Proceeding without Status Column. "
            "Run add_status_column.py in default mode or with table-names CognatesetTable to "
            "add a Status Column."
        )

    foreign_key_form_concept = ""
    for foreign_key in dataset["FormTable"].tableSchema.foreignKeys:
        if foreign_key.reference.resource == dataset["ParameterTable"].url:
            foreign_key_form_concept = foreign_key.columnReference[0]

    foreign_key_form_language = ""
    for foreign_key in dataset["FormTable"].tableSchema.foreignKeys:
        if foreign_key.reference.resource == dataset["LanguageTable"].url:
            foreign_key_form_language = foreign_key.columnReference[0]

    foreign_key_cognate_form = ""
    for foreign_key in dataset["CognateTable"].tableSchema.foreignKeys:
        if foreign_key.reference.resource == dataset["FormTable"].url:
            foreign_key_cognate_form = foreign_key.columnReference[0]

    foreign_key_cognate_cogset = ""
    for foreign_key in dataset["CognateTable"].tableSchema.foreignKeys:
        if foreign_key.reference.resource == dataset["CognatesetTable"].url:
            foreign_key_cognate_cogset = foreign_key.columnReference[0]

    # load data
    singleton_forms: t.Dict[FormID, types.Form] = {}
    for f in dataset["FormTable"]:
        singleton_forms[f[c_f_id]] = f

    all_judgements: t.Dict[CognatesetID, t.List[types.CogSet]] = {}
    for j in dataset["CognateTable"]:
        all_judgements.setdefault(j[foreign_key_cognate_cogset], []).append(j)

    all_cogsets = [c for c in dataset["CognatesetTable"]]

    concept_id_by_form_id: t.Dict[ConceptID, FormID] = {}
    for f in dataset["FormTable"]:
        concept = f[foreign_key_form_concept]
        if isinstance(concept, str):
            concept_id_by_form_id[f[c_f_id]] = concept
        else:
            concept_id_by_form_id[f[c_f_id]] = concept[0]

    # delete forms with cognateset
    for k in all_judgements:
        for j in all_judgements[k]:
            form_id = j[foreign_key_cognate_form]
            try:
                del singleton_forms[form_id]
            except KeyError:
                continue
    del all_judgements
    judgements = [c for c in dataset["CognateTable"]]

    # create singletons for remaining forms and add singleton to cogsets
    for i, form_id in enumerate(singleton_forms):
        if singleton_forms[form_id][c_f_form] is None:
            continue
        cogset = {
            c_cs_id: f"X{i + 1}_{singleton_forms[form_id][foreign_key_form_language]}",
            c_cs_name: concept_id_by_form_id[form_id],
        }
        if status_column:
            cogset[status_column] = "automatic singleton"
        all_cogsets.append(cogset)

        cognate = {
            c_c_id: f"{cogset[c_cs_id]}",
            foreign_key_cognate_form: form_id,
            foreign_key_cognate_cogset: cogset[c_cs_id],
        }
        judgements.append(cognate)
    return all_cogsets, judgements


if __name__ == "__main__":
    parser = cli.parser(description="Create an Excel cognate view from a CLDF dataset")
    args = parser.parse_args()
    logger = cli.setup_logging(args)
    logger.info("Creating Singleton Cognatesets.")
    dataset = pycldf.Dataset.from_metadata(args.metadata)
    all_cogsets, judgements = create_singeltons(dataset=dataset, logger=logger)
    dataset.write(CognatesetTable=all_cogsets, CognateTable=judgements)

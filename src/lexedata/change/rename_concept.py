import pycldf
import argparse
import typing as t

from lexedata.enrich.add_status_column import add_status_column_to_table

def substitute(row, columns, old_value, new_value):
    for column in columns:
        if type(row[column]) == list:
            row[column] = [
                new_value if val == old_value else val for val in row[column]
            ]
        elif type(row[column]) == str:
            row[column] = new_value if row[column] == old_value else row[column]
    return row


def substitute_many(row, columns, old_values_to_new_values):
    for column in columns:
        if type(row[column]) == list:
            row[column] = [
                old_values_to_new_values.get(val, val) for val in row[column]
            ]
        elif type(row[column]) == str:
            row[column] = old_values_to_new_values.get(row[column], row[column])
    return row


def rename(ds, old_values_to_new_values):
    concepts = ds["ParameterTable"]

    for table in ds.tables:
        if table == concepts:
            continue
        _, component = table.common_props["dc:conformsTo"].split("#")
        try:
            c_concept = ds[component, "parameterReference"]
            columns = {c_concept.name}
        except KeyError:
            columns = set()
        for reference in table.tableSchema.foreignKeys:
            if reference.reference.resource.string == concepts.url.string:
                (column,) = reference.columnReference
                columns.add(column)
        if columns:
            print(f"Changing columns {columns:} in {component:}…")
            ds.write(
                **{
                    component: [
                        substitute_many(r, columns, old_values_to_new_values)
                        for r in table
                    ]
                }
            )

def replace_column(
        dataset: pycldf.Dataset,
        original: str,
        replacement: str,
        column_replace: bool,
        smush: bool,
        status_update: t.Optional[str]
) -> None:
    if column_replace:
        concepts = dataset["ParameterTable"]

        assert (
            original == "id"
            or original == dataset["ParameterTable", "id"].name
        ), f"Replacing an entire column is only meaningful when you change the #id column ({dataset['ParameterTable', 'id'].name}) of the ConceptTable."

        c_id = dataset["ParameterTable", original].name
        c_new = dataset["ParameterTable", replacement].name
        mapping = {
            concept[c_id]: concept[c_new] for concept in dataset["ParameterTable"]
        }
        assert smush or len(mapping) == len(
            set(mapping.values())
        ), "Would collapse some concepts that were distinct before! Add '--smush' if that is intended."
        # dataset["ParameterTable"].tableSchema.columns["c_id"]
        rename(dataset, mapping)
    else:
        concepts = dataset["ParameterTable"]

        c_id = dataset["ParameterTable", "id"].name

        print(f"Changing {c_id:} of ParameterTable…")
        dataset.write(
            ParameterTable=[
                substitute_many(r, [c_id], {original: replacement})
                for r in concepts
            ]
        )
        rename(dataset, {original: replacement})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Change the ID of a concept in the wordlist"
    )
    parser.add_argument(
        "original",
        type=str,
        help="Name of the original column to be replaced"
    )
    parser.add_argument(
        "replacement",
        type=str,
        help="Name of the replacement column"
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default="Wordlist-metadata.json",
        help="Path to the JSON metadata file describing the dataset (default: ./Wordlist-metadata.json)",
    )
    parser.add_argument(
        "--column-replace",
        action="store_true",
        default=False
    )
    parser.add_argument(
        "--smush",
        action="store_true",
        default=False
    )



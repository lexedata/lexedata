import pycldf
import argparse


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Change the ID of a concept in the wordlist"
    )
    parser.add_argument("--metadata", default="Wordlist-metadata.json")
    parser.add_argument("original")
    parser.add_argument("replacement")
    parser.add_argument("--column-replace", action="store_true", default=False)
    parser.add_argument("--smush", action="store_true", default=False)
    args = parser.parse_args()

    dataset = pycldf.Wordlist.from_metadata(args.metadata)
    if args.column_replace:
        concepts = dataset["ParameterTable"]

        assert (
            args.original == "id"
            or args.original == dataset["ParameterTable", "id"].name
        ), f"Replacing an entire column is only meaningful when you change the #id column ({dataset['ParameterTable', 'id'].name}) of the ConceptTable."

        c_id = dataset["ParameterTable", args.original].name
        c_new = dataset["ParameterTable", args.replacement].name
        mapping = {
            concept[c_id]: concept[c_new] for concept in dataset["ParameterTable"]
        }
        assert args.smush or len(mapping) == len(
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
                substitute_many(r, [c_id], {args.original: args.replacement})
                for r in concepts
            ]
        )
        rename(dataset, {args.original: args.replacement})

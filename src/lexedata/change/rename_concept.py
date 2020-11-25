import pycldf
import argparse

parser = argparse.ArgumentParser(
    description="Change the ID of a concept in the wordlist"
)
parser.add_argument("--metadata", default="Wordlist-metadata.json")
parser.add_argument("original")
parser.add_argument("replacement")
args = parser.parse_args()

ds = pycldf.Wordlist.from_metadata(args.metadata)
concepts = ds["ParameterTable"]
c_id = ds["ParameterTable", "id"].name


def substitute(row, columns, old_value, new_value):
    for column in columns:
        if type(row[column]) == list:
            row[column] = [
                new_value if val == old_value else val for val in row[column]
            ]
        elif type(row[column]) == str:
            row[column] = new_value if row[column] == old_value else row[column]
    return row


print(f"Changing {c_id:} of ParameterTable…")
ds.write(
    ParameterTable=[
        substitute(r, [c_id], args.original, args.replacement) for r in concepts
    ]
)

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
                    substitute(r, columns, args.original, args.replacement)
                    for r in table
                ]
            }
        )

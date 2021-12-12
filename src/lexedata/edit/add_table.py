"""
Given a table name: Find all the references to that table and create an empty table of that type filled with all those.

Should definitely work for: LanguageTable, CognatesetTable, and ParameterTable (i.e. the table with the concepts).
Warn about `ConceptTable`, but proceed adding a ParameterTable.
Suggest running `lexedata.edit.simplify_ids` if the references we resolve here are not properly ID-shaped.
"""

import pycldf

from lexedata import cli, util


if __name__ == "__main__":
    parser = cli.parser(__doc__)
    parser.add_argument(
        "table",
        help="""The table to add. Examples: LanguageTable, CognatesetTable, or
    ParameterTable (i.e. the table with the concepts), but any CLDF component
    where you have a corresponding reference column should work, so you could
    also use this script to extract a CodeTable from an existing codeReference
    column.""",
        metavar="TABLE",
    )
    args = parser.parse_args()
    logger = cli.setup_logging(args)

    if args.table == "ConceptTable":
        logger.warning(
            "ConceptTable is not a valid table name. I assume you meant ParameterTable, and I will proceed adding that."
        )
        args.table = "ParameterTable"

    if not args.table.endswith("Table"):
        cli.Exit.CLI_ARGUMENT_ERROR(
            f"Your table does not end in 'Table'. Did you mean {args.table:s}Table?"
        )

    ds = pycldf.Wordlist.from_metadata(args.metadata)

    if ds.get(args.table):
        cli.Exit.CLI_ARGUMENT_ERROR(f"Dataset already has a {args.table:s}.")

    try:
        new_table = ds.add_component(args.table)
    except FileNotFoundError:
        cli.Exit.CLI_ARGUMENT_ERROR(
            f"I don't know how to add a {args.table:s}. Is it a well-defined CLDF component, according to https://cldf.clld.org/v1.0/terms.rdf#components ?"
        )

    if "Name" in new_table.tableSchema.columndict:

        def new_row(item):
            return {"ID": item, "Name": item}

    else:

        def new_row(item):
            return {"ID": item}

    reference_properties = {
        property_name
        for property_name, term in pycldf.terms.Terms().properties.items()
        if term.references == args.table
    }

    referenced_items = set()
    for table in ds.tables:
        for column in table.tableSchema.columns:
            if util.cldf_property(column.propertyUrl) in reference_properties:
                referenced_items |= {row[column.name] for row in table}

    logger.info(
        "Found %d different entries for your new %s.", len(referenced_items), args.table
    )

    ds.write(**{args.table: [new_row(item) for item in sorted(referenced_items)]})

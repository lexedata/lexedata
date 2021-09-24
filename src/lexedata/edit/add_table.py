"""
Given a table name: Find all the references to that table and create an empty table of that type filled with all those.

Should definitely work for: LanguageTable, CognatesetTable, and ParameterTable (i.e. the table with the concepts).
Warn about `ConceptTable`, but proceed adding a ParameterTable.
Suggest running `lexedata.edit.simplify_ids` if the references we resolve here are not properly ID-shaped.
"""

from lexedata import cli

if __name__ == "__main__":
    parser = cli.parser(__doc__)
    parser.add_argument(
        "table",
        help="""The table to add. Examples: LanguageTable, CognatesetTable, or
    ParameterTable (i.e. the table with the concepts), but any CLDF component
    where you have a corresponding reference column should work, so you could
    also use this script to extract a CodeTable from an existing codeReference
    column.""",
    )

    raise NotImplementedError

import typing as t

import pycldf
import cldfcatalog
import cldfbench

from lexedata.edit.add_status_column import add_status_column_to_table
import lexedata.cli as cli
concepticon_path = cldfcatalog.Config.from_file().get_clone("concepticon")
concepticon = cldfbench.catalogs.Concepticon(concepticon_path)


def add_concepticon_definitions(
        dataset: pycldf.Dataset,
        column_name: str = "Concepticon_Definition",
        logger: cli.logging = cli.logger,
        status_update: t.Optional[str] = None
):
    # check for existing concepticon reference
    if not dataset.column_names.parameters.concepticonReference:
        logger.warning("This script requires a column ConcepticonReference. Run add_concepticon first")
        raise ValueError

    # Create a concepticon_definition column
    try:
        dataset.add_columns("ParameterTable", column_name)
        dataset.write_metadata()
    except ValueError:
        logger.warning(f"{column_name} could not be added to ParameterTable of {dataset}.")
        raise ValueError

    # add Status_Column if status update
    if status_update:
        add_status_column_to_table(dataset=dataset, table_name="ParameterTable")

    write_back = []
    for row in dataset["ParameterTable"]:
        try:
            row[column_name] = concepticon.api.conceptsets[
                row[dataset.column_names.parameters.concepticonReference]
            ].definition
        except KeyError:
            pass
        # add status update if given
        if status_update:
            row["Status_Column"] = status_update
        write_back.append(row)

    dataset.write(ParameterTable=write_back)


if __name__ == "__main__":
    parser = cli.parser(description="Adds Concepticon reference to #parameterTable")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Set concepticon definition even if one exists already",
    )
    parser.add_argument(
        "--status-update",
        type=str,
        default="automatic Concepticon link",
        help="Text written to Status_Column. Set to 'None' for no status update. "
             "(default: automatic Concepticon link)",
    )
    args = parser.parse_args()
    if args.status_update == "None":
        args.status_update = None

    add_concepticon_definitions(
        dataset=pycldf.Dataset.from_metadata(args.metadata),
        status_update=args.status_update,
    )


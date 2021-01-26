from pathlib import Path
import typing as t

import pycldf


def add_status_column_to_table(dataset: pycldf.Dataset, table_name: str) -> None:
    if "Status_Column" not in dataset[table_name].tableSchema.columndict.keys():
        dataset.add_columns(table_name, "Status_Column")


def status_column_to_table_list(
    dataset: pycldf.Dataset, tables: t.List[str]
) -> pycldf.Dataset:
    for table in tables:
        add_status_column_to_table(dataset, table)
    return dataset


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Add Status_Column to specified tables of the dataset"
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default="Wordlist-metadata.json",
        help="Path to the JSON metadata file describing the dataset (default: ./Wordlist-metadata.json)",
    )
    parser.add_argument(
        "--table-names",
        type=str,
        nargs="*",
        default=[],
        help="Table names where to add Status_Column "
        "(default: FormTable, CognatesetTable, CognateTable, ParameterTable)",
    )
    parser.add_argument(
        "--exclude-tables",
        type=str,
        nargs="*",
        default=[],
        help="Table names to exclude",
    )
    args = parser.parse_args()
    if args.table_names:
        table_names = args.table_names
    else:
        table_names = [
            name
            for name in [
                "FormTable",
                "CognatesetTable",
                "CognateTable",
                "ParameterTable",
            ]
            if name not in args.exclude_tables
        ]
    dataset = pycldf.Dataset.from_metadata(args.metadata)
    status_column_to_table_list(dataset=dataset, tables=table_names)

import typing as t
import sqlalchemy
import sqlalchemy.ext.automap


def name_of_object_in_table(
        base: t.Type[sqlalchemy.ext.automap.AutomapBase],
        tablename: str,
        table: sqlalchemy.schema.Table) -> str:
    """Give the name of objects in the table.

    >>> name_of_object_in_table(..., "FormTable", ...)
    'Form'
    >>> name_of_object_in_table(..., "objectTable", ...)
    'Object'
    """
    if tablename.lower().endswith("table"):
        tablename = tablename[:-len("table")]
    return tablename[0].upper() + tablename[1:]


def name_of_object_in_table_relation(
        base: t.Type[sqlalchemy.ext.automap.AutomapBase],
        local_cls: t.Type[sqlalchemy.ext.automap.AutomapBase],
        referred_cls: t.Type[sqlalchemy.ext.automap.AutomapBase],
        constraint: sqlalchemy.schema.ForeignKeyConstraint) -> str:
    """Give the name of objects in the table.

    >>> class Parser:
    ...   pass
    >>> name_of_object_in_table_relation(..., ..., Parser, ...)
    'parser'
    >>> class FormTable_SourceTable__cldf_source:
    ...   pass
    >>> name_of_object_in_table_relation(..., ..., FormTable_SourceTable__cldf_source, ...)
    'cldf_source'
    """
    return referred_cls.__name__.split("__")[-1].lower()


def name_of_objects_in_table_relation(
        base: t.Type[sqlalchemy.ext.automap.AutomapBase],
        local_cls: t.Type[sqlalchemy.ext.automap.AutomapBase],
        referred_cls: t.Type[sqlalchemy.ext.automap.AutomapBase],
        constraint: sqlalchemy.schema.ForeignKeyConstraint) -> str:
    """Give the name of objects in the table.

    >>> class Parser:
    ...   pass
    >>> name_of_objects_in_table_relation(..., ..., Parser, ...)
    'parsers'
    >>> class FormTable_SourceTable__cldf_source:
    ...   pass
    >>> name_of_objects_in_table_relation(..., ..., FormTable_SourceTable__cldf_source, ...)
    'cldf_sources'
    """
    return referred_cls.__name__.split("__")[-1].lower() + "s"


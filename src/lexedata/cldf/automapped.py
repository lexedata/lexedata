import os
import pycldf
import typing as t
from pathlib import Path
import sqlalchemy
import sqlalchemy.ext.automap

import lexedata.cldf.db as db
from lexedata.database.database import create_db_session


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


A = t.TypeVar("A", bound=sqlalchemy.ext.automap.AutomapBase, covariant=True)
B = t.TypeVar("B", bound=sqlalchemy.ext.automap.AutomapBase, covariant=True)


class Language(sqlalchemy.ext.automap.AutomapBase):
    cldf_id: t.Hashable


L = t.TypeVar("L", bound=Language, covariant=True)


class Concept(sqlalchemy.ext.automap.AutomapBase):
    cldf_id: t.Hashable


C = t.TypeVar("C", bound=Concept, covariant=True)


class Source(sqlalchemy.ext.automap.AutomapBase):
    ...


S = t.TypeVar("S", bound=Source, covariant=True)


class Form(t.Generic[L, C], sqlalchemy.ext.automap.AutomapBase):
    cldf_id: t.Hashable
    language: L

    def __init__(self, cldf_id: t.Hashable, language: L, **kwargs):
        ...


F = t.TypeVar("F", bound=Source, covariant=True)


class CogSet(sqlalchemy.ext.automap.AutomapBase):
    cldf_id: t.Hashable
    ...


X = t.TypeVar("X", bound=Source, covariant=True)


class Association(t.Generic[A, B], sqlalchemy.ext.automap.AutomapBase):
    ...


class Judgement(Association[F, X]):
    ...

class Reference(Association[F, S]):
    ...

class SQLAlchemyWordlist:
    def __init__(
            self,
            dataset: pycldf.Dataset,
            fname: str = None,
            override_database: bool = False,
            override_dataset: bool = False,
            echo=False,
            **kwargs) -> None:
        self.cldfdatabase = db.Database(dataset, fname=fname, **kwargs)
        # if fname given and str, turn into Path()
        if fname and isinstance(fname, str):
            fname = Path(fname)

        if override_database or not fname or os.path.exists(fname):
            self.cldfdatabase.write_from_tg(_force=True)
        # TODO: Ask Gereon about the exact condition here
        # dataset["FormTable"] throws an error, as dataset does not exist
        elif override_dataset or not list(fname.parent.glob("*.csv")):
            dataset.write(**{str(t.url): [] for t in dataset.tables})
        else:
            raise ValueError("Database and data set both exist.")

        connection = self.cldfdatabase.connection()

        def creator():
            return connection

        Base = sqlalchemy.ext.automap.automap_base()

        if fname:
            engine = sqlalchemy.create_engine(f"sqlite:///{fname:}")
        else:
            engine = sqlalchemy.create_engine("sqlite:///:memory:",
                                              creator=creator)
        Base.prepare(engine, reflect=True,
                     classname_for_table=name_of_object_in_table,
                     name_for_scalar_relationship=name_of_object_in_table_relation,
                     name_for_collection_relationship=name_of_objects_in_table_relation)
        # TODO: Ask Gereon about creator function
        self.session = sqlalchemy.orm.Session(engine)

        self.Language: t.Type[Language] = Base.classes.Language
        self.Concept: t.Type[Concept] = Base.classes.Parameter
        self.Source: t.Type[Source] = Base.classes.Source
        self.Form: t.Type[Form[Language, Concept]] = Base.classes.Form
        self.Reference: t.Type[Association[Form, Source]] = Base.classes.FormTable_SourceTable__cldf_source
        self.CogSet: t.Type[CogSet] = Base.classes.Cognateset
        self.Judgement: t.Type[Judgement] = Base.classes.Cognate

# -*- coding: utf-8 -*-

import re
import unidecode as uni

import sqlalchemy as sa
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import sessionmaker

# Initialize the SQL Alchemy
import os

invalid_id_elements = re.compile(r"\W+")


@as_declarative()
class DatabaseObjectWithUniqueStringID:
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = sa.Column(sa.String, primary_key=True)

    @staticmethod
    def string_to_id(string):
        """

        >>> string_to_id("trivial")
        "trivial"
        >>> string_to_id("just 4 non-alphanumerical characters.")
        >>> string_to_id("Это русский.")
        >>> string_to_id("该语言有一个音节。")
        >>> string_to_id("この言語には音節があります。")

        """
        # We nee to run this through valid_id_elements twice, because some word
        # characters (eg. Chinese) are unidecoded to contain non-word characters.
        return invalid_id_elements.sub(
            "_", uni.unidecode(
                invalid_id_elements.sub("_", string)).lower())

    @classmethod
    def register_new_id(cl, id):
        assert id == cl.string_to_id(id)
        try:
            registry = cl.__registry
        except AttributeError:
            registry = set(o.id for o in cl.session.query(cl.id))
        i = 1
        while "{:s}{:d}".format(id, i) in registry:
            i += 1
        unique = "{:s}{:d}".format(id, i)
        registry.add(unique)
        return unique


def create_db_session(location='sqlite:///cldf.sqlite'):
    try:
        os.remove("cldf.sqlite")
    except FileNotFoundError:
        pass
    engine = sa.create_engine(location, echo=False) # Create an SQLite database in this directory
    # use `echo=True` to see the SQL stamenets echoed

    session = sessionmaker(bind=engine)()
    DatabaseObjectWithUniqueStringID.session = session
    DatabaseObjectWithUniqueStringID.metadata.create_all(engine, checkfirst=True)
    return session

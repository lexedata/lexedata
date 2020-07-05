# -*- coding: utf-8 -*-
"""

>>> True
True

"""
import os
import re
from typing import Dict

from pathlib import Path

import unidecode as uni
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import sessionmaker


@declarative_base
class Base(object):
    """Database declarative base class"""
    metadata: Dict


invalid_id_elements = re.compile(r"\W+")


class DatabaseObjectWithUniqueStringID(Base):
    '''An ORM base class for objects with string IDs.

    Define all subclasses, then create a session, then initialize instances.

    >>> class ObjectWithID(DatabaseObjectWithUniqueStringID):
    ...   pass
    >>> session = create_db_session(location='sqlite:///:memory:')
    >>> ObjectWithID(id="this")
    <ObjectWithID(id='this')>
    >>> session.connection().engine.dispose()

    '''
    __abstract__ = True
    session = None # These objects need a database session to look up existing IDs
    id = sa.Column(sa.String, name="cldf_id", primary_key=True)

    def __init__(self, *initial_data, **kwargs):
        for dictionary in initial_data:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])

    def __repr__(self):
        return '<{:}({:})>'.format(
            self.__class__.__name__,
            ', '.join("{:s}={!r:}".format(attr, val)
                      for attr, val in vars(self).items()
                      if not attr.startswith("_")))

    def get(self, property, default=None):
        for ele in dir(self):
            if ele == property:
                return getattr(self, ele)
        return default

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    @staticmethod
    def string_to_id(string):
        """Generate a useful id string from the string

        >>> d = DatabaseObjectWithUniqueStringID
        >>> d.string_to_id("trivial")
        'trivial'
        >>> d.string_to_id("Just 4 non-alphanumerical characters.")
        'just_4_non_alphanumerical_characters'
        >>> d.string_to_id("Это русский.")
        'eto_russkii'
        >>> d.string_to_id("该语言有一个音节。")
        'gai_yu_yan_you_yi_ge_yin_jie'
        >>> d.string_to_id("この言語には音節があります。")
        'konoyan_yu_nihayin_jie_gaarimasu'

        """
        # We nee to run this through valid_id_elements twice, because some word
        # characters (eg. Chinese) are unidecoded to contain non-word characters.
        return invalid_id_elements.sub(
            "_", uni.unidecode(
                invalid_id_elements.sub("_", string)).lower()).strip("_")

    @classmethod
    def register_new_id(cl, string):
        """Turn the current string into a unique id

        Turn the string into a useful id string using string_to_id, then append
        a decimal integer number to that string that is large enough to make
        the id different from all objects added to the database so far.

        >>> class Ex(DatabaseObjectWithUniqueStringID):
        ...   pass
        >>> session = create_db_session(location='sqlite:///:memory:')
        >>> session.add(Ex(id=Ex.register_new_id("unique")))
        >>> session.add(Ex(id=Ex.register_new_id("unique")))
        >>> list(session.query(Ex))
        [<Ex(id='unique')>, <Ex(id='unique_1')>]
        >>> session.connection().engine.dispose()

        """
        id = cl.string_to_id(string)
        i = 0
        candidate = id
        while cl.session.query(cl.id).filter(cl.id == candidate).one_or_none():
            i += 1
            candidate = "{:s}_{:d}".format(id, i)
        return candidate


def string_to_id(string):
    """Generate a useful id string from the string

    >>> string_to_id("trivial")
    'trivial'
    >>> string_to_id("Just 4 non-alphanumerical characters.")
    'just_4_non_alphanumerical_characters'
    >>> string_to_id("Это русский.")
    'eto_russkii'
    >>> string_to_id("该语言有一个音节。")
    'gai_yu_yan_you_yi_ge_yin_jie'
    >>> string_to_id("この言語には音節があります。")
    'konoyan_yu_nihayin_jie_gaarimasu'

    """
    # We nee to run this through valid_id_elements twice, because some word
    # characters (eg. Chinese) are unidecoded to contain non-word characters.
    return invalid_id_elements.sub(
        "_", uni.unidecode(
            invalid_id_elements.sub("_", string)).lower()).strip("_")


def new_id(maybe_not_unique: str, cl, session: sa.engine.Connectable):
    """Turn the current string into a unique id for the table

    Turn the string into a useful id string using string_to_id, then append a
    decimal integer number to that string that is large enough to make the id
    different from all objects added to the database so far.

    >>> session = create_db_session(location='sqlite:///:memory:')

    """
    id = string_to_id(maybe_not_unique)
    i = 0
    candidate = id
    while session.query(cl.cldf_id).filter(cl.cldf_id == candidate).one_or_none():
        i += 1
        candidate = "{:s}_{:d}".format(id, i)
    return candidate


def create_db_session(location=None, echo=False, override=False):
    if Path(location).exists() and override:
        Path(location).unlink()

    if not location:
        location = "sqlite:///:memory:"
    # use `echo=True` to see the SQL stamenets echoed
    # create db path for sql module, and escape \ for windows
    else:
        if not location.startswith("sqlite:///"):
            location = f"sqlite:///{location:}"
        location = location.replace("\\", "\\\\")  # can this cause problems on IOS?
    # Create an SQLite database in this directory. Use `echo=True` to see the SQL statements echoed
    engine = sa.create_engine(location, echo=echo)
    # bind to session
    session = sessionmaker(bind=engine)()
    # pass session to object
    DatabaseObjectWithUniqueStringID.session = session
    # this part is only for creation
    # bind session to object and create tables
    DatabaseObjectWithUniqueStringID.metadata.create_all(engine, checkfirst=True)
    return session

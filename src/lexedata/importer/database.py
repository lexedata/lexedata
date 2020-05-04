# -*- coding: utf-8 -*-
"""

>>> True
True

"""
import os
import re
import attr
from pathlib import Path

import unidecode as uni
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import sessionmaker


@declarative_base
class Base(object):
    """Database declarative base class"""
    pass


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
        'just_4_non_alphanumerical_characters_'
        >>> d.string_to_id("Это русский.")
        'eto_russkii_'
        >>> d.string_to_id("该语言有一个音节。")
        'gai_yu_yan_you_yi_ge_yin_jie__'
        >>> d.string_to_id("この言語には音節があります。")
        'konoyan_yu_nihayin_jie_gaarimasu_'

        """
        # We nee to run this through valid_id_elements twice, because some word
        # characters (eg. Chinese) are unidecoded to contain non-word characters.
        return invalid_id_elements.sub(
            "_", uni.unidecode(
                invalid_id_elements.sub("_", string)).lower()).strip("_")

    # TODO: register_new_id should just query candidate and raise int if already in db, not create ids
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
        [<Ex(id='unique1')>, <Ex(id='unique2')>]
        >>> session.connection().engine.dispose()

        """
        ID = cl.string_to_id(string)
        i = 0
        candidate = ID
        while cl.session.query(cl.id).filter(cl.id == candidate).one_or_none():
            i += 1
            candidate = "{:s}{:d}".format(ID, i)
        return candidate


def create_db_session(location='sqlite:///:memory:', echo=False):
    # FIXME: Give this a parameter to decide whether or not an existing DB should be overwritten
    try:
        os.remove("cldf.sqlite")
    except FileNotFoundError:
        pass
    engine = sa.create_engine(location, echo=False) # Create an SQLite database in this directory
    engine.execute('pragma foreign_keys=ON')
    # use `echo=True` to see the SQL stamenets echoed

    # create db path for sql module, and escape \ for windows
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

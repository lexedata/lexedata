# -*- coding: utf-8 -*-
"""

>>> True
True

"""

import re
import attr
import unidecode as uni

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import sessionmaker

# Initialize the SQL Alchemy
import os

invalid_id_elements = re.compile(r"\W+")

@declarative_base
class Base(object):
    """Database declarative base class"""
    pass

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
    id = sa.Column(sa.String, primary_key=True)

    def __repr__(self):
        return '<{:}({:})>'.format(
            self.__class__.__name__,
            ', '.join("{:s}={!r:}".format(attr, val)
                      for attr, val in vars(self).items()
                      if not attr.startswith("_")))

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    @staticmethod
    def string_to_id(string):
        """Generate a useful ID string from the string

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
                invalid_id_elements.sub("_", string)).lower())

    @classmethod
    def register_new_id(cl, string):
        """Turn the current string into a unique ID

        Turn the string into a useful ID string using string_to_id, then append
        a decimal integer number to that string that is large enough to make
        the ID different from all objects added to the database so far.

        >>> class Ex(DatabaseObjectWithUniqueStringID):
        ...   pass
        >>> session = create_db_session(location='sqlite:///:memory:')
        >>> session.add(Ex(id=Ex.register_new_id("unique")))
        >>> session.add(Ex(id=Ex.register_new_id("unique")))
        >>> list(session.query(Ex))
        [<Ex(id='unique1')>, <Ex(id='unique2')>]
        >>> session.connection().engine.dispose()

        """
        id = cl.string_to_id(string)
        i = 1
        while cl.session.query(cl.id).filter(
                cl.id == "{:s}{:d}".format(id, i)).one_or_none():
            i += 1
        unique = "{:s}{:d}".format(id, i)
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

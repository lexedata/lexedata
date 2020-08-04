import re
import abc
import typing as t
import unidecode as uni


class Object(t.Dict[str, t.Any]):
    @property
    @abc.abstractmethod
    def __table__(self) -> str:
        raise NotImplementedError


class RowObject(Object):
    """A row in a lexical dataset, i.e. a concept or cognateset"""
    pass


class Concept(RowObject):
    @property
    def __table__(self) -> str:
        return "ParameterTable"


class Form(Object):
    @property
    def __table__(self) -> str:
        return "FormTable"


class Language(Object):
    @property
    def __table__(self) -> str:
        return "LanguageTable"


class Source(Object):
    @property
    def __table__(self) -> str:
        return "SourceTable"


class Reference(Object):
    @property
    def __table__(self) -> str:
        return "FormTable_SourceTable__cldf_source"


invalid_id_elements = re.compile(r"\W+")

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

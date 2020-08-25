import typing as t
import abc

class Object(t.Dict[str, t.Any]):
    """Object"""
    @property
    @abc.abstractmethod
    def __table__(self) -> str:
        raise NotImplementedError


class RowObject(Object):
    """A row in a lexical dataset, i.e. a concept or cognateset"""
    pass


class Concept(RowObject):
    """concept"""
    @property
    def __table__(self) -> str:
        return "ParameterTable"


class CogSet(RowObject):
    """cognate set"""
    @property
    def __table__(self) -> str:
        return "CognatesetTable"


class Form(Object):
    """form"""
    @property
    def __table__(self) -> str:
        return "FormTable"


class Language(Object):
    """language"""
    @property
    def __table__(self) -> str:
        return "LanguageTable"


class Source(Object):
    """source"""
    @property
    def __table__(self) -> str:
        return "SourceTable"


class Reference(Object):
    """reference"""
    @property
    def __table__(self) -> str:
        return "FormTable_SourceTable__cldf_source"


class Judgement(RowObject):
    """cognate judgement"""
    @property
    def __table__(self) -> str:
        return "CognateTable"


# TODO: This function is a bit out of place here. Move it somewhere more
# sensible.
import re
import unidecode as uni
invalid_id_elements = re.compile(r"\W+")


def string_to_id(string: str) -> str:
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

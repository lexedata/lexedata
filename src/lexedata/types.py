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

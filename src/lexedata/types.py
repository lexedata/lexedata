import pycldf
import typing as t
import abc


H = t.TypeVar("H", bound=t.Hashable)


class WorldSet(t.Generic[H]):
    def __contains__(self, thing: H):
        return True

    def intersection(
        self, other: t.Union["WorldSet[H]", t.Set[H]]
    ) -> t.Union["WorldSet[H]", t.Set[H]]:
        return other


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


Language_ID = t.TypeVar("Language_ID", bound=t.Hashable)
Form_ID = t.TypeVar("Form_ID", bound=t.Hashable)
Parameter_ID = t.TypeVar("Parameter_ID", bound=t.Hashable)
Cognate_ID = t.TypeVar("Cognate_ID", bound=t.Hashable)
Cognateset_ID = t.TypeVar("Cognateset_ID", bound=t.Hashable)


class Wordlist(
    pycldf.Wordlist,
    t.Generic[Language_ID, Form_ID, Parameter_ID, Cognate_ID, Cognateset_ID],
):
    pass

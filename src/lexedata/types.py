import abc
import typing as t

import pycldf

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

    __table__: str


R = t.TypeVar("R", bound=RowObject)


class Concept(RowObject):
    """concept"""

    __table__ = "ParameterTable"


class CogSet(RowObject):
    """cognate set"""

    __table__ = "CognatesetTable"


class Form(Object):
    """form"""

    __table__ = "FormTable"


class Language(Object):
    """language"""

    __table__ = "LanguageTable"


class Source(Object):
    """source"""

    __table__ = "SourceTable"


class Reference(Object):
    """reference"""

    @property
    def __table__(self) -> str:
        return "FormTable_SourceTable__cldf_source"


class Judgement(RowObject):
    """cognate judgement"""

    __table__ = "CognateTable"


Language_ID = t.TypeVar("Language_ID", bound=t.Union[str, int])
Form_ID = t.TypeVar("Form_ID", bound=t.Union[str, int])
Parameter_ID = t.TypeVar("Parameter_ID", bound=t.Union[str, int])
Cognate_ID = t.TypeVar("Cognate_ID", bound=t.Union[str, int])
Cognateset_ID = t.TypeVar("Cognateset_ID", bound=t.Union[str, int])
Row_ID = t.Union[Cognateset_ID, Parameter_ID]


class Wordlist(
    pycldf.Wordlist,
    t.Generic[Language_ID, Form_ID, Parameter_ID, Cognate_ID, Cognateset_ID],
):
    pass


class KeyKeyDict(t.Mapping[str, str]):
    def __len__(self):
        return 0

    def __iter__(self):
        return ()

    def __getitem__(self, key):
        return key

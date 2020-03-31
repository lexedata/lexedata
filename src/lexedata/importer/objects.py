import re
import attr
from collections import defaultdict

import unidecode as uni
from pycldf.db import BIBTEX_FIELDS

from lexedata.importer.database import Base, DatabaseObjectWithUniqueStringID, sa, create_db_session
from lexedata.importer.exceptions import *

# lambda function for getting comment of excel cell if comment given
comment_getter = lambda x: x.comment.content if x.comment else ""
#functions for bracket checking
one_bracket = lambda opening, closing, str, nr: str[0] == opening and str[-1] == closing and \
                                                (str.count(opening) == str.count(closing) == nr)
comment_bracket = lambda str: str.count("(") == str.count(")")


class Language(DatabaseObjectWithUniqueStringID):
    """Metadata for a language"""
    __tablename__ = "LanguageTable"
    id = sa.Column(sa.String, name="cldf_id", primary_key=True)
    name = sa.Column(sa.String, name="cldf_name")
    glottocode = sa.Column(sa.String, name="cldf_glottocode")
    iso639p3 = sa.Column(sa.String, name="cldf_iso639p3code")
    curator = sa.Column(sa.String, name="Curator")
    comments = sa.Column(sa.String, name="cldf_comment")


class Source(DatabaseObjectWithUniqueStringID):
    __tablename__ = "SourceTable"


# global name space
for source_col in ['genre'] + BIBTEX_FIELDS:
    setattr(Source, source_col, sa.Column(sa.String, name=source_col, default=""))


class Form(DatabaseObjectWithUniqueStringID):
    __tablename__ = "FormTable"
    Language_ID = sa.Column(sa.String, sa.ForeignKey(Language.id), name="cldf_languageReference")
    # FIXME: Use an actual foreign-key relationship here.

    phonemic = sa.Column(sa.String, name="Phonemic_Transcription", index=True)
    phonetic = sa.Column(sa.String, name="cldf_form", index=True)
    orthographic = sa.Column(sa.String, name="Orthographic_Transcription", index=True)
    variants = sa.Column(sa.String, name="Variants_of_Form_given_by_Source")
    original = sa.Column(sa.String, name="cldf_value", index=True)
    form_comment = sa.Column(sa.String, name="cldf_comment")
    sources = sa.orm.relationship(
        "Source",
        secondary="FormTable_SourceTable"
    )
    concepts = sa.orm.relationship(
        "Concept",
        secondary='FormTable_ParameterTable',
        back_populates="forms"
    )

class Concept(DatabaseObjectWithUniqueStringID):
    """
    a concept element consists of 8 fields:
        (concept_id,set,english,english_strict,spanish,portuguese,french,concept_comment)
    sharing concept_id and concept_comment with a form element
    concept_comment refers to te comment of the cell containing the english meaning
    """
    __tablename__ = "ParameterTable"

    english = sa.Column(sa.String, name="cldf_name")
    set = sa.Column(sa.String, name="Set")
    english_strict = sa.Column(sa.String, name="English_Strict")
    spanish = sa.Column(sa.String, name="Spanish")
    french = sa.Column(sa.String, name="French")
    portuguese = sa.Column(sa.String, name="Portuguese")
    concept_comment = sa.Column(sa.String, name="cldf_comment")

    forms = sa.orm.relationship(
        "Form",
        secondary='FormTable_ParameterTable',
        back_populates="concepts"
    )


class FormMeaningAssociation(Base):
    __tablename__ = 'FormTable_ParameterTable'
    form = sa.Column('FormTable_cldf_id',
                     sa.Integer, sa.ForeignKey(Form.id),
                     primary_key=True)
    concept = sa.Column('ParameterTable_cldf_id',
                        sa.Integer, sa.ForeignKey(Concept.id),
                        primary_key=True)
    context = sa.Column('context', sa.String, default="Concept_IDs")


class CogSet(DatabaseObjectWithUniqueStringID):
    __tablename__ = 'CognatesetTable'

    id = sa.Column(sa.String, name="cldf_id", primary_key=True)
    set = sa.Column(sa.String, name="Set")
    description = sa.Column(sa.String, name="cldf_description") # meaning comment of excel sheet
    # judgements may contain various CognateJudgement
    judgements = sa.orm.relationship("CognateJudgement", back_populates="cogset")

    @classmethod
    def from_excel(cls, cog_row):
        values = [cell.value or "" for cell in cog_row]
        return cls(id=values[1], set=values[0], description=comment_getter(cog_row[1]))


class CognateJudgement(DatabaseObjectWithUniqueStringID):
    __tablename__ = 'CognateTable'

    id = sa.Column(sa.String, name="cldf_id", primary_key=True)
    cogset_id = sa.Column(sa.String, sa.ForeignKey('CognatesetTable.cldf_id'), name="cldf_cognatesetReference")
    form_id = sa.Column(sa.String, sa.ForeignKey('FormTable.cldf_id'), name="cldf_formReference")
    language_id = sa.Column(sa.String, sa.ForeignKey('LanguageTable.cldf_id'), name="cldf_languageReference")
    cognate_comment = sa.Column(sa.String, name="cognate_comment")
    procedural_comment = sa.Column(sa.String, name="comment")
    # relations to one Cogset, one Form, one Language
    cogset = sa.orm.relationship("CogSet", back_populates="judgements")
    form = sa.orm.relationship("Form", back_populates="judgements")
    language = sa.orm.relationship("Language", back_populates="judgements")

    @classmethod
    def from_cognate_and_form(cls, cognate, form):
        id = cognate.id + "_" + form.id
        return cls(id=id, cogset_id=cognate.cog_set_id, form_id=form.id, language_id=cognate.language_id,
                   cognate_comment=cognate.cognate_comment, procedural_comment=cognate.procedural_comment)


@attr.s
class Cognate:

    id = attr.ib()
    language_id = attr.ib()
    cog_set_id = attr.ib()
    cognate_comment = attr.ib()
    phonemic = attr.ib()
    phonetic = attr.ib()
    orthographic = attr.ib()
    source = attr.ib()
    procedural_comment = attr.ib()

    __cog_counter = defaultdict(int)

    @classmethod
    def create_id(cls, cogset_id):
        cls.__cog_counter[cogset_id]+=1
        return cogset_id + "_" + str(cls.__cog_counter[cogset_id])

    @classmethod
    def from_excel(cls, f_ele, lan_id, cog_cell, cogset):

        phonemic, phonetic, ortho, comment, source, variants = f_ele
        cogset_id = cogset.id
        id = cls.create_id(cogset_id)
        pro_com = comment_getter(cog_cell)
        source = lan_id + ("{1}" if source == "" else source).strip()
        return cls(id=id, language_id=lan_id, cog_set_id=cogset_id, cognate_comment=comment,
                   phonemic=phonemic, phonetic=phonetic, orthographic=ortho, source=source, procedural_comment=pro_com)


form_sources = sa.Table(
    'FormTable_SourceTable', Base.metadata,
    sa.Column('FormTable_cldf_id', sa.String, sa.ForeignKey(Form.id)),
    sa.Column('SourceTable_id', sa.String, sa.ForeignKey(Source.id)),
    sa.Column('context', sa.String),
)

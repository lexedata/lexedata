import re
import attr
from collections import defaultdict
from pycldf.db import BIBTEX_FIELDS

from lexedata.importer.database import create_db_session, Base, DatabaseObjectWithUniqueStringID, sa

class Language(DatabaseObjectWithUniqueStringID):
    """Metadata for a language"""
    __tablename__ = "LanguageTable"
    name = sa.Column(sa.String, name="cldf_name")
    glottocode = sa.Column(sa.String, name="cldf_glottocode")
    iso639p3 = sa.Column(sa.String, name="cldf_iso639p3code")
    curator = sa.Column(sa.String, name="Curator")
    comment = sa.Column(sa.String, name="cldf_comment")


class Source(DatabaseObjectWithUniqueStringID):
    __tablename__ = "SourceTable"


# global name space
for source_col in ['genre'] + BIBTEX_FIELDS:
    setattr(Source, source_col, sa.Column(sa.String, name=source_col, default=""))


class Form(DatabaseObjectWithUniqueStringID):
    __tablename__ = "FormTable"
    Language_ID = sa.Column(sa.String, sa.ForeignKey(Language.id), name="cldf_languageReference")
    language = sa.orm.relationship(Language)

    phonemic = sa.Column(sa.String, name="Phonemic_Transcription", index=True)
    phonetic = sa.Column(sa.String, name="cldf_form", index=True)
    orthographic = sa.Column(sa.String, name="Orthographic_Transcription", index=True)
    variants = sa.Column(sa.String, name="Variants_of_Form_given_by_Source")
    original = sa.Column(sa.String, name="cldf_value", index=True)
    comment = sa.Column(sa.String, name="cldf_comment")
    procedural_comment = sa.Column(sa.String, name="procedural_comment")
    sources = sa.orm.relationship(
        Source,
        secondary="FormTable_SourceTable"
    )
    concepts = sa.orm.relationship(
        "Concept", # will be parsed to the class once it is defined
        secondary='FormTable_ParameterTable',
        back_populates="forms"
    )
    cognatesets = sa.orm.relationship(
        "CogSet",
        secondary="CognateTable",
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
    comment = sa.Column(sa.String, name="cldf_comment")

    forms = sa.orm.relationship(
        Form,
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


form_sources = sa.Table(
    'FormTable_SourceTable', Base.metadata,
    sa.Column('FormTable_cldf_id', sa.String, sa.ForeignKey(Form.id)),
    sa.Column('SourceTable_id', sa.String, sa.ForeignKey(Source.id)),
    sa.Column('context', sa.String),
)

class CogSet(DatabaseObjectWithUniqueStringID):
    """
    A cognateset, which has an ID, an optional reference form, and an optional comment
    """
    __tablename__ = 'CognatesetTable'

    reference_form_id = sa.Column('cldf_formReference',
                     sa.Integer, sa.ForeignKey(Form.ID),
                     primary_key=True)
    reference_form = sa.orm.relationship(Form)
    comment = sa.Column(sa.String, name="cldf_comment")
    properties = sa.Column(sa.String, name="properties")

    forms = sa.orm.relationship(
        Form,
        secondary='CognateTable',
        back_populates="cognatesets"
    )

class CognateJudgement(Base):
    __tablename__ = 'CognateTable'

    form_id = sa.Column('FormTable_cldf_id',
                     sa.Integer, sa.ForeignKey(Form.ID),
                     primary_key=True)
    form = sa.orm.relationship(Form)
    cognateset_id = sa.Column('CognatesetTable_cldf_id',
                        sa.Integer, sa.ForeignKey(CogSet.ID),
                        primary_key=True)
    cognateset = sa.orm.relationship(CogSet)
    context = sa.Column('context', sa.String, default="Concept_IDs")
    comment = sa.Column(sa.String, name="cldf_comment")


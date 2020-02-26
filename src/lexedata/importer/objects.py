import re
from collections import defaultdict

from database import create_db_session, Base, DatabaseObjectWithUniqueStringID, sa

class Language(DatabaseObjectWithUniqueStringID):
    """Metadata for a language"""
    __tablename__ = "LanguageTable"
    ID = sa.Column(sa.String, name="cldf_id", primary_key=True)
    name = sa.Column(sa.String, name="cldf_name")
    curator = sa.Column(sa.String, name="Curator")
    comments = sa.Column(sa.String, name="cldf_comment")
    iso639p3 = sa.Column(sa.String, name="cldf_iso639p3code")

#what is this?
from pycldf.db import BIBTEX_FIELDS

class Source(DatabaseObjectWithUniqueStringID):
    __tablename__ = "SourceTable"
    ID = sa.Column(sa.String, name="id", primary_key=True)
for source_col in ['genre'] + BIBTEX_FIELDS:
    setattr(Source, source_col, sa.Column(sa.String, name=source_col, default=""))


class Form(DatabaseObjectWithUniqueStringID):
    __tablename__ = "FormTable"
    ID = sa.Column(sa.String, name="cldf_id", primary_key=True)
    Language_ID = sa.Column(sa.String, name="cldf_languageReference")
    # FIXME: Use an actual foreign-key relationship here.

    phonemic = sa.Column(sa.String, name="Phonemic_Transcription")
    phonetic = sa.Column(sa.String, name="cldf_form")
    orthographic = sa.Column(sa.String, name="Orthographic_Transcription")
    variants = sa.Column(sa.String, name="Variants_of_Form_given_by_Source")
    sources = sa.orm.relationship(
        "Source",
        secondary="FormTable_SourceTable"
    )
    concepts = sa.orm.relationship(
        "Concept",
        secondary='FormTable_ParameterTable',
        back_populates="forms"
    )


    @staticmethod
    def variants_scanner(string):
        """copies string, inserting closing brackets if necessary"""
        is_open = False
        closers = {"<": ">", "[": "]", "/": "/"}
        collector = ""
        starter = ""

        for char in string:

            if char in closers and not is_open:
                collector += char
                is_open = True
                starter = char

            elif char == "~":
                if is_open:
                    collector += (closers[starter] + char + starter)
                else:
                    collector += char

            elif char in closers.values():
                collector += char
                is_open = False
                starter = ""

            elif is_open:
                collector += char

        return collector

    @classmethod
    def variants_separator(klasse, variants_list, string):
        if "~" in string:
            # force python to copy string
            text = (string + "&")[:-1]
            text = text.replace(" ", "")
            text = text.replace(",", "")
            text = text.replace(";", "")
            values = klasse.variants_scanner(text)

            values = values.split("~")
            first = values.pop(0)

            #add rest to variants prefixed with ~
            values = [("~"+e) for e in values]
            variants_list += values
            return first
        else:
            return string

    __form_counter = defaultdict(int)

    @classmethod
    def id_creator(klasse, lan_id, con_id):
        return klasse.string_to_id("{:s}_{:s}_".format(lan_id, con_id))



class Concept(DatabaseObjectWithUniqueStringID):
    """
    a concept element consists of 8 fields:
        (concept_id,set,english,english_strict,spanish,portuguese,french,concept_comment)
    sharing concept_id and concept_comment with a form element
    concept_comment refers to te comment of the cell containing the english meaning
    """
    __tablename__ = "ParameterTable"

    ID = sa.Column(sa.String, name="cldf_id", primary_key=True)
    set = sa.Column(sa.String, name="Set")
    english = sa.Column(sa.String, name="cldf_name")
    english_strict = sa.Column(sa.String, name="English_Strict")
    spanish = sa.Column(sa.String, name="Spanish")
    portuguese = sa.Column(sa.String, name="Portuguese")
    french = sa.Column(sa.String, name="French")
    concept_comment = sa.Column(sa.String, name="cldf_comment")

    forms = sa.orm.relationship(
        "Form",
        secondary='FormTable_ParameterTable',
        back_populates="concepts"
    )



class FormMeaningAssociation(Base):
    __tablename__ = 'FormTable_ParameterTable' # no such table....
    # Actually pycldf looks for 'forms.csv_concepts.csv', there could probably
    # be a translation in pycldf to tie it to the 'conformsTo' objects.
    # Previous line kept for posterity.

    # gereon, why are ids here integers?
    # why parameter names context and internal/procedural_comment?
    form = sa.Column('forms.csv_ID',
                     sa.Integer, sa.ForeignKey(Form.ID), primary_key=True)
    concept = sa.Column('concepts.csv_ID',
                        sa.Integer, sa.ForeignKey(Concept.ID), primary_key=True)
    context = sa.Column('context', sa.String)
    procedural_comment = sa.Column('Internal_Comment', sa.String)

# why here no indent?
form_sources = sa.Table(
    'FormTable_SourceTable', Base.metadata,
    sa.Column('FormTable_cldf_id', sa.String, sa.ForeignKey(Form.ID)),
    sa.Column('SourceTable_id', sa.String, sa.ForeignKey(Source.ID)),
    sa.Column('context', sa.String),
)

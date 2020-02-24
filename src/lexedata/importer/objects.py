import re
from collections import defaultdict

from .database import create_db_session, Base, DatabaseObjectWithUniqueStringID, sa

class Language(DatabaseObjectWithUniqueStringID):
    """Metadata for a language"""
    name = sa.Column(sa.String)
    curator = sa.Column(sa.String)
    comments = sa.Column(sa.String)
    iso639p3 = sa.Column(sa.String)


class Source(DatabaseObjectWithUniqueStringID):
    ...

class Form(DatabaseObjectWithUniqueStringID):
    ID = sa.Column(sa.String, name="FormTable_cldf_id", primary_key=True)
    Language_ID = sa.Column(sa.String, name="FormTable_cldf_languageReference")
    # FIXME: Use an actual foreign-key relationship here.

    phonemic = sa.Column(sa.String)
    phonetic = sa.Column(sa.String)
    orthographic = sa.Column(sa.String)
    variants = sa.Column(sa.String)
    sources = sa.orm.relationship(
        "Source",
        secondary="FormTable_SourceTable"
    )
    concepts = sa.orm.relationship(
        "Concept",
        secondary='formmeaning',
        back_populates="forms"
    )

    __variants_corrector = re.compile(r"^([</\[])(.+[^>/\]])$")
    __variants_splitter = re.compile(r"^(.+?)\s?~\s?([</\[].+)$")

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
            variants_list += values
            return first
        else:
            return string

    __form_counter = defaultdict(int)

    @classmethod
    def id_creator(klasse, lan_id, con_id):
        return klasse.string_to_id("{:s}_{:s}_".format(lan_id, con_id))

    def get(self, property, default=None):
        if property == "form_id" or property == "ID":
            return self.ID
        elif property == "language_id" or property == "Language_ID":
            return self.language_id
        elif property == "phonemic":
            return self.phonemic
        elif property == "phonetic":
            return self.phonetic
        elif property == "orthographic":
            return self.orthographic
        elif property == "source":
            return self.source
        elif property == "comment":
            return self.comment
        elif property == "form_comment":
            return self.form_comment
        elif property == "variants":
            return self.variants
        return default


class Concept(DatabaseObjectWithUniqueStringID):
    """
    a concept element consists of 8 fields:
        (concept_id,set,english,english_strict,spanish,portuguese,french,concept_comment)
    sharing concept_id and concept_comment with a form element
    concept_comment refers to te comment of the cell containing the english meaning
    """
    set = sa.Column(sa.String)
    english = sa.Column(sa.String)
    english_strict = sa.Column(sa.String)
    spanish = sa.Column(sa.String)
    portuguese = sa.Column(sa.String)
    french = sa.Column(sa.String)
    concept_comment = sa.Column(sa.String)

    forms = sa.orm.relationship(
        "Form",
        secondary='formmeaning',
        back_populates="concepts"
    )

    def get(self, property, default=None):
        if property == "concept_id":
            return self.ID
        elif property == "set":
            return self.set
        elif property == "english":
            return self.english
        elif property == "english_strict":
            return self.english_strict
        elif property == "spanish":
            return self.spanish
        elif property == "portuguese":
            return self.portuguese
        elif property == "french":
            return self.french
        return default


class FormMeaningAssociation(Base):
    __tablename__ = 'formmeaning'
    form = sa.Column('FormTable_cldf_formReference',
                     sa.Integer, sa.ForeignKey(Form.ID), primary_key=True)
    concept = sa.Column('ConceptTable_cldf_parameterReference',
                        sa.Integer, sa.ForeignKey(Concept.ID), primary_key=True)
    comment = sa.Column('Comment', sa.String)
    procedural_comment = sa.Column('Internal_Comment', sa.String)

form_sources = sa.Table('FormTable_SourceTable', Base.metadata,
    sa.Column('FormTable_cldf_id', sa.Integer, sa.ForeignKey(Form.ID)),
    sa.Column('SourceTable_id', sa.Integer, sa.ForeignKey(Source.ID))
)

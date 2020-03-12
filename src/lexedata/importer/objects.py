import re
import attr
from collections import defaultdict
import unidecode as uni
from database import create_db_session, DatabaseObjectWithUniqueStringID, sa
from exceptions import *
# lambda function for getting comment of excel cell if comment given
comment_getter = lambda x: x.comment.content if x.comment else ""
#functions for bracket checking
one_bracket = lambda opening, closing, str, nr: str[0] == opening and str[-1] == closing and \
                                                (str.count(opening) == str.count(closing) == nr)
comment_bracket = lambda str: str.count("(") == str.count(")")

class Language(DatabaseObjectWithUniqueStringID):
    """Metadata for a language"""
    __tablename__ = "LanguageTable"
    ID = sa.Column(sa.String, name="cldf_id", primary_key=True)
    Name = sa.Column(sa.String, name="cldf_name")
    Curator = sa.Column(sa.String, name="Curator")
    Comment = sa.Column(sa.String, name="cldf_comment")
    iso639p3 = sa.Column(sa.String, name="cldf_iso639p3code")
    Excel_name = attr.ib()

    forms = sa.orm.relationship("Form", back_populates="language_ids")

    @classmethod
    def from_column(k, column):
        excel_name, curator = [cell.value or "" for cell in column]
        id = k.create_id_from_string(excel_name)
        name, comment = "", ""
        return k(ID=id, Name=name, Curator=curator, Comment=comment, Excel_name=excel_name)

    # id creation encapuslated
    __valid = re.compile(r"\W+")
    _languagedict = defaultdict(int)

    @classmethod
    def create_id_from_string(k, string):
        string = uni.unidecode(k.__valid.sub("_", string)).lower()
        # take only parts longer than 3
        string = "_".join([ele for ele in string.split("_") if len(ele) > 3])
        k._languagedict[string] += 1
        string += str(k._languagedict[string])
        return string

    # pycldf.Dataset.write assumes a `get` method to access attributes, so we
    # can make `LanguageCell` outputtable to CLDF by providing such a method,
    # mapping attributes to CLDF column names


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
    Language_ID = sa.Column(sa.String, sa.ForeignKey('LanguageTable.cldf_id'), name="cldf_languageReference")

    Phonemic = sa.Column(sa.String, name="Phonemic_Transcription")
    Phonetic = sa.Column(sa.String, name="cldf_form")
    Orthographic = sa.Column(sa.String, name="Orthographic_Transcription")
    Variants = sa.Column(sa.String, name="Variants_of_Form_given_by_Source") #does it need this column name?

   # sources_gereon = sa.orm.relationship(
    #    "Source",
    #    secondary="FormTable_SourceTable"
    #)
    #concepts = sa.orm.relationship(
    #    "Concept",
    #    secondary='FormTable_ParameterTable',
    #    back_populates="forms"
    #)

    #melvin
    Form_Comment = attr.ib()
    Source = attr.ib()
    Concept_ID = attr.ib()
    Procedural_Comment = attr.ib()
    Procedural_Comment_Concept = attr.ib()

    language_ids = sa.orm.relationship("Language", back_populates="forms")
    toconcepts = sa.orm.relationship("FormToConcept", back_populates="fromforms")

    __form_id_counter = defaultdict(int)

    @classmethod
    def id_creator(cls, lan_id, con_id):
        candidate = "_".join([lan_id, con_id])
        cls.__form_id_counter[candidate] += 1
        candidate += ("_" + str(cls.__form_id_counter[candidate]))
        return candidate

    @classmethod
    def create_form(cls, f_ele, lan_id, form_cell, concept):

        phonemic, phonetic, ortho, comment, source, variants = f_ele

        form_id = cls.id_creator(lan_id, concept.ID)
        # replace source if not given
        source_id = lan_id + ("{1}" if source == "" else source).strip()

        return cls(ID=form_id, Language_ID=lan_id, Phonemic=phonemic, Phonetic=phonetic, Orthographic=ortho,
                   Variants=variants, Form_Comment=comment, Source=source_id, Procedural_Comment=comment_getter(form_cell),
                   Procedural_Comment_Concept=concept.Concept_Comment,  Concept_ID=concept.ID)


class Concept(DatabaseObjectWithUniqueStringID):
    """
    a concept element consists of 8 fields:
        (concept_id,set,english,english_strict,spanish,portuguese,french,concept_comment)
    sharing concept_id and concept_comment with a form element
    concept_comment refers to te comment of the cell containing the english meaning
    """
    __tablename__ = "ParameterTable"

    ID = sa.Column(sa.String, name="cldf_id", primary_key=True)
    Set = sa.Column(sa.String, name="Set")
    English = sa.Column(sa.String, name="cldf_name")
    English_Strict = sa.Column(sa.String, name="English_Strict")
    Spanish = sa.Column(sa.String, name="Spanish")
    Portuguese = sa.Column(sa.String, name="Portuguese")
    French = sa.Column(sa.String, name="French")
    Concept_comment = attr.ib()

    toforms = sa.orm.relationship("FormToConcept", back_populates="fromconcepts")

    @classmethod
    def from_default_excel(cls, conceptrow):
        # values of cell
        set, english, english_strict, spanish, portuguese, french = [cell.value or "" for cell in conceptrow]
        concept_id = cls.create_id(english)
        comment = comment_getter(conceptrow[1])
        return cls(ID=concept_id, Set=set, English=english, English_Strict=english_strict, Spanish=spanish,
                   Portuguese=portuguese, French=french, Concept_Comment=comment)

    # protected static class variable for creating unique ids, regex-pattern
    _conceptdict = defaultdict(int)
    __id_pattern = re.compile(r"^(.+?)(?:[,\(\@](?:.+)?|)$")
    @staticmethod
    def create_id(meaning):
        """
        creates unique id out of given english meaning
        :param meaning: str
        :return: unique id (str)
        """
        mymatch = Concept.__id_pattern.match(meaning)
        if mymatch:
            mymatch = mymatch.group(1)
            mymatch = mymatch.replace(" ", "")
            Concept._conceptdict[mymatch] += 1
            mymatch += str(Concept._conceptdict[mymatch])
            return mymatch
        else:
            raise ConceptIdError


class FormToConcept(DatabaseObjectWithUniqueStringID):
    __tablename__ = 'FormTable_ParameterTable'

    ID = sa.Column(sa.String, name="cldf_id", primary_key=True)
    Form_ID = sa.Column(sa.String, sa.ForeignKey('FormTable.cldf_id'), name="cldf_?")
    Concept_ID = sa.Column(sa.String, sa.ForeignKey('ParameterTable.cldf_id'), name="cldf_?!")
    Form_Comment = sa.Column(sa.String, name="cldf_??")
    Procedural_Comment = sa.Column(sa.String, name="cldf_???")
    Procedural_Comment_Concept = sa.Column(sa.String, name="cldf_????")

    fromconcepts = sa.orm.relationship("Concept", back_populates="toforms")
    fromforms = sa.orm.relationship("Form", back_populates="toconcepts")


    @classmethod
    def from_form(cls, form):
        id = form.ID + "c"
        return cls(ID=id, Form_ID=form.ID, Concept_ID=form.Concept_ID,
                   Form_Comment=form.Form_Comment, Procedural_Comment=form.Procedural_Comment,
                   Procedural_Comment_Concept=form.Procedural_Comment_Concept)


class CogSet(DatabaseObjectWithUniqueStringID):
    __tablename__ = 'CognatesetTable'

    ID = sa.Column(sa.String, name="cldf_id", primary_key=True)
    Set = sa.Column(sa.String, name="Set")
    Description = sa.Column(sa.String, name="cldf_description") # meaning comment of excel sheet

    @classmethod
    def from_excel(cls, cog_row):
        values = [cell.value or "" for cell in cog_row]
        return cls(ID=values[1], Set=values[0], Description=comment_getter(cog_row[1]))


class Cognate(DatabaseObjectWithUniqueStringID):
    __tablename__ = 'CognateTable'

    ID = sa.Column(sa.String, name="cldf_id", primary_key=True)
    Language_Id = sa.Column(sa.String, name="Language_ID")
    CogSet_ID = sa.Column(sa.String, name="cldf_cognatesetReference")
    Form_ID = sa.Column(sa.String, name="cldf_formReference")
    Cognate_Comment = sa.Column(sa.String, name="Cognate_Comment")
    Phonemic = sa.Column(sa.String, name="Phonemic")
    Phonetic = sa.Column(sa.String, name="Phonetic")
    Orthographic = sa.Column(sa.String, name="Orthographic")
    Source = attr.ib()

    __cog_counter = defaultdict(int)

    @classmethod
    def create_id(cls, cogset_id):
        cls.__cog_counter[cogset_id]+=1
        return cogset_id + "_" + str(cls.__cog_counter[cogset_id])

    @classmethod
    def from_excel(cls, f_ele, lan_id, cog_cell, cogset):

        phonemic, phonetic, ortho, comment, source, variants = f_ele
        cogset_id = cogset.ID
        id = cls.create_id(cogset_id)
        form_id = ""
        cog_com = comment_getter(cog_cell)
        return cls(ID=id, Language_id=lan_id, CogSet_ID=cogset_id, Form_Id=form_id, Cognate_Comment=cog_com,
                   Phonemic=phonemic, Phonetic=phonetic, Orthographic=ortho, Source=source)

    # ________________________________________________________________________
    #gereon

class FormMeaningAssociation(DatabaseObjectWithUniqueStringID):
    __tablename__ = 'FormTable_ParameterTable2' # no such table....
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
#form_sources = sa.Table(
#    'FormTable_SourceTable', Base.metadata,
#    sa.Column('FormTable_cldf_id', sa.String, sa.sa.ForeignKey(Form.ID)),
#    sa.Column('SourceTable_id', sa.String, sa.sa.ForeignKey(Source.ID)),
#    sa.Column('context', sa.String),
#)

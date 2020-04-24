import re
import attr
from collections import defaultdict

import unidecode as uni
from pycldf.db import BIBTEX_FIELDS

from lexedata.importer.database import DatabaseObjectWithUniqueStringID, sa, create_db_session
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
    curator = sa.Column(sa.String, name="Curator")
    comment = sa.Column(sa.String, name="cldf_comment")
    iso639p3 = sa.Column(sa.String, name="cldf_iso639p3code")
    excel_name = attr.ib()
    # contains all forms and judgements of this language
    forms = sa.orm.relationship("Form", back_populates="language")
    judgements = sa.orm.relationship("CognateJudgement", back_populates="language")

    @classmethod
    def from_column(k, column):
        excel_name, curator = [cell.value or "" for cell in column]
        id = k.create_id_from_string(excel_name)
        name, comment = "", ""
        return k(id=id, name=name, curator=curator, comment=comment, excel_name=excel_name)

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


class Source(DatabaseObjectWithUniqueStringID):
    __tablename__ = "SourceTable"
    ID = sa.Column(sa.String, name="id", primary_key=True)


# global name space
for source_col in ['genre'] + BIBTEX_FIELDS:
    setattr(Source, source_col, sa.Column(sa.String, name=source_col, default=""))


class Form(DatabaseObjectWithUniqueStringID):
    __tablename__ = "FormTable"
    id = sa.Column(sa.String, name="cldf_id", primary_key=True)
    language_id = sa.Column(sa.String, sa.ForeignKey('LanguageTable.cldf_id'), name="cldf_languageReference")

    phonemic = sa.Column(sa.String, name="Phonemic_Transcription")
    phonetic = sa.Column(sa.String, name="cldf_form")
    orthographic = sa.Column(sa.String, name="Orthographic_Transcription")
    variants = sa.Column(sa.String, name="Variants_of_Form_given_by_Source") #does it need this column name?

   # sources_gereon = sa.orm.relationship(
    #    "Source",
    #    secondary="FormTable_SourceTable"
    #)

    #melvin
    form_comment = attr.ib()
    source = sa.Column(sa.String, name="source")
    concept_id = attr.ib()
    procedural_comment = attr.ib()
    procedural_comment_concept = attr.ib()

    language = sa.orm.relationship("Language", back_populates="forms")
    # toconcepts may contain various FormToConcept
    toconcepts = sa.orm.relationship("FormToConcept", back_populates="form")
    # judgements may contain various CognateJudgement
    judgements = sa.orm.relationship("CognateJudgement", back_populates="form")

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
        form_id = cls.id_creator(lan_id, concept.id)
        # replace source if not given
        source_id = lan_id + ("{1}" if source == "" else source).strip()

        return cls(id=form_id, language_id=lan_id, phonemic=phonemic, phonetic=phonetic, orthographic=ortho,
                   variants=variants, form_comment=comment, source=source_id, procedural_comment=comment_getter(form_cell),
                   procedural_comment_concept=concept.concept_comment,  concept_id=concept.id)


class Concept(DatabaseObjectWithUniqueStringID):
    """
    a concept element consists of 8 fields:
        (concept_id,set,english,english_strict,spanish,portuguese,french,concept_comment)
    sharing concept_id and concept_comment with a form element
    concept_comment refers to te comment of the cell containing the english meaning
    """
    __tablename__ = "ParameterTable"

    id = sa.Column(sa.String, name="cldf_id", primary_key=True)
    set = sa.Column(sa.String, name="Set")
    english = sa.Column(sa.String, name="cldf_name")
    english_strict = sa.Column(sa.String, name="English_Strict")
    spanish = sa.Column(sa.String, name="Spanish")
    portuguese = sa.Column(sa.String, name="Portuguese")
    french = sa.Column(sa.String, name="French")
    concept_comment = attr.ib()
    # toform may contain various FormToConcept
    toform = sa.orm.relationship("FormToConcept", uselist=False, back_populates="concept")


    @classmethod
    def from_default_excel(cls, conceptrow):
        # at least english meaning must be provided
        if conceptrow[1].value is None:
            raise CellParsingError("Column English", conceptrow[1])
        # values of cell
        set, english, english_strict, spanish, portuguese, french = [cell.value or "" for cell in conceptrow]
        concept_id = cls.create_id(english)
        comment = comment_getter(conceptrow[1])
        return cls(id=concept_id, set=set, english=english, english_Strict=english_strict, spanish=spanish,
                   portuguese=portuguese, french=french, concept_comment=comment)

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

    id = sa.Column(sa.String, name="cldf_id", primary_key=True)
    form_id = sa.Column(sa.String, sa.ForeignKey('FormTable.cldf_id'), name="cldf_?")
    concept_id = sa.Column(sa.String, sa.ForeignKey('ParameterTable.cldf_id'), name="cldf_?!")
    form_comment = sa.Column(sa.String, name="cldf_??")
    procedural_comment = sa.Column(sa.String, name="cldf_???")
    procedural_comment_concept = sa.Column(sa.String, name="cldf_????")
    # relations to one Form and one Concept
    concept = sa.orm.relationship("Concept", back_populates="toform")
    form = sa.orm.relationship("Form", back_populates="toconcepts")




    @classmethod
    def from_form(cls, form):
        myid = form.id + "c"
        return cls(id=myid, form_id=form.id, concept_id=form.concept_id,
                   form_comment=form.form_comment, procedural_comment=form.procedural_comment,
                   procedural_comment_concept=form.procedural_comment_concept)


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



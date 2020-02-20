import re
from collections import defaultdict

from .database import create_db_session, as_declarative, DatabaseObjectWithUniqueStringID, sa

class Language(DatabaseObjectWithUniqueStringID):
    """Metadata for a language"""
    name = sa.Column(sa.String)
    curator = sa.Column(sa.String)
    comments = sa.Column(sa.String)
    coordinates = sa.Column(sa.String)

    # pycldf.Dataset.write assumes a `get` method to access attributes, so we
    # can make `LanguageCell` outputtable to CLDF by providing such a method,
    # mapping attributes to CLDF column names
    def get(self, property, default=None):
        if property == "language_id" or property == "ID":
            return self.id
        elif property == "language_name" or property == "name":
            return self.name
        elif property == "curator":
            return self.curator
        elif property == "language_comment" or property == "comments":
            return self.comments
        return default

    def warn(self):
        if "???" in self.name:
            raise LanguageElementError(coordinates, self.name)


class Form(DatabaseObjectWithUniqueStringID):
    language_id = sa.Column(sa.String)
    # FIXME: Use an actual foreign-key relationship here.

    phonemic = sa.Column(sa.String)
    phonetic = sa.Column(sa.String)
    orthographic = sa.Column(sa.String)
    variants = sa.Column(sa.String)
    comment = sa.Column(sa.String)
    source = sa.Column(sa.String)

    form_comment = sa.Column(sa.String)

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
            return self.id
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
    coordinates = sa.Column(sa.String)


    def get(self, property, default=None):
        if property == "concept_id":
            return self.id
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


@as_declarative()
class FormConceptAssociation():
    __tablename__ = 'form_to_concept'
    id = sa.Column(sa.String, primary_key=True)
    concept_id = sa.Column(sa.String, sa.ForeignKey(Concept.id), primary_key=True)
    form_id = sa.Column(sa.String, sa.ForeignKey(Form.id), primary_key=True)


# -*- coding: utf-8 -*-
from pathlib import Path
from objects import Language, Concept, Form, FormToConcept, Cognate, CogSet,\
    DatabaseObjectWithUniqueStringID, create_db_session
from csv import DictReader
from sqlalchemy import or_, and_
from exceptions import *

def insert_languages(dir_path, session):
    for l_row in DictReader((dir_path / "lan_init.csv").open("r", encoding="utf8", newline="")):
        language = Language(l_row)
        session.add(language)
    session.commit()


def insert_concepts(dir_path, session):
    for c_row in DictReader((dir_path / "concept_init.csv").open("r", encoding="utf8", newline="")):
        concept = Concept(c_row)
        session.add(concept)
    session.commit()


def insert_forms(dir_path, session):
    for f_row in DictReader((dir_path / "form_init.csv").open("r", encoding="utf8", newline="")):
        form = Form(f_row)
        form_to_concept = FormToConcept.from_form(form)
        # check if existing, and if so add variants to variants
        # only when exact match
        already_existing = session.query(Form).filter(
            Form.Language_ID == form.Language_ID,
            Form.Phonetic == form.Phonetic,
            Form.Phonemic == form.Phonemic,
            Form.Orthographic == form.Orthographic).one_or_none()
        if already_existing is None:
            session.add(form)
            session.add(form_to_concept)
        else:
            existing_form = already_existing
            existing_variants = existing_form.Variants.split(";")
            new_variants = form.Variants.split(";")
            if set(new_variants) - set(existing_variants):
                print(
                    "Variants {:} of form {:} were not mentioned earlier. Adding them to the form nonetheless".format(
                        set(new_variants) - set(existing_variants),
                        form))
                form.Variants = ";".join(set(new_variants) | set(existing_variants))
            if set(existing_variants) - set(new_variants):
                print(set(existing_variants) - set(new_variants))
                # print("{:}: Variants {:} of form {:} were not mentioned here.".format(
                #        set(existing_variants) - set(new_variants), existing_form))
            # link form_to_concept element to existing form
            form_to_concept.Form_ID = existing_form.ID
            session.add(form_to_concept)

    session.commit()


def query_cognates(cog, session, myfilters):
    # just select same language
    myquery = session.query(Form).filter(Form.Language_ID == cog.Language_ID)

    # select with just one matching transcription, i.e. using or_
    myquery = myquery.filter(or_(getattr(Form, attribute) == value for attribute, value in myfilters.items()))

    one_transcription = myquery.all()

    len_one = len(one_transcription)
    # if just one match or no match so far, exit here
    if len_one == 1 or len_one == 0:
        return one_transcription

    # match for the source
    one_transcription_source = myquery.filter(Form.Source == cog.Source)
    one_transcription_source = one_transcription_source.all()

    # if just one match with source, exit here; if no match with source, return without source
    len_source = len(one_transcription_source)
    if len_source == 1:
        return one_transcription_source
    elif len_source == 0:
        return one_transcription

    # match all given transcriptions
    myquery = myquery.filter(and_(getattr(Form, attribute) == value for attribute, value in myfilters.items())).all()

    # if no exact match, return match with source
    if len(myquery) == 0:
        return one_transcription
    else:
        return myquery


def compare_cog(cog, form, myfilters):

    if len(form) == 0:
        raise MatchingError(cog, "")
    elif len(form) > 1:
        raise MultipleMatchError(cog, form)

    elif cog.Source != form[0].Source:
        raise NoSourceMatchError(cog, form)

    elif not all(getattr(form[0], attribute) == getattr(cog, attribute) for attribute in myfilters):
        raise PartialMatchError(cog, form)


def insert_cognates(dir_path, session):
    for c_row in DictReader((dir_path / "cog_init.csv").open("r", encoding="utf8", newline="")):
        cog = Cognate(c_row)
        print(cog)

        # create dict with not empty attributes
        myfilters = {}
        if cog.Phonemic != "":
            myfilters["Phonemic"] = cog.Phonemic
        if cog.Phonetic != "":
            myfilters["Phonetic"] = cog.Phonetic
        if cog.Orthographic != "":
            myfilters["Orthographic"] = cog.Orthographic

        res = query_cognates(cog, session, myfilters)
        try:
            compare_cog(cog, res, myfilters)

        except MultipleMatchError as err:
            print(err)
            input()
        except NoSourceMatchError as err:
            print(err)
            #input()
        except PartialMatchError as err:
            print(err)
            #input()
        except MatchingError as err:
            print(err)
            #input()

def create_db():
    dir_path = Path.cwd() / "initial_data"
    if not dir_path.exists():
        print("Necessary data not found \nInitialize fromexcel.py first")
        exit()

    db_path = dir_path / "lexedata.db"
    if db_path.exists():
        answer = input("Do you want do delete the existing data base?y/n?")
        if answer == "y":
            db_path.unlink()
        else:
            print("exit")
            exit()

    db_path = "sqlite:///" + str(db_path)
    db_path = db_path.replace("\\", "\\\\") # can this cause problems on IOS?
    session = create_db_session(location=db_path, echo=False)

    insert_languages(dir_path, session)
    insert_concepts(dir_path, session)
    insert_forms(dir_path, session)

    insert_cognates(dir_path, session)
    session.close()


def test():
    dir_path = Path.cwd() / "initial_data"
    db_path = dir_path / "lexedata.db"
    db_path = "sqlite:///" + str(db_path)
    db_path = db_path.replace("\\", "\\\\")  # can this cause problems on IOS?
    session = create_db_session(location=db_path, echo=False)
    insert_cognates(dir_path, session)
    session.close()

def show_empty_forms():
    dir_path = Path.cwd() / "initial_data"
    db_path = dir_path / "lexedata.db"
    db_path = "sqlite:///" + str(db_path)
    db_path = db_path.replace("\\", "\\\\")  # can this cause problems on IOS?
    session = create_db_session(location=db_path, echo=False)
    return session.query(Form).filter(
        Form.Phonetic == "",
        Form.Phonemic == "",
        Form.Orthographic == "").all()


if __name__ == "__main__":
    #create_db()
    test()


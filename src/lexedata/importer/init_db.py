# -*- coding: utf-8 -*-
from pathlib import Path
from objects import Language, Concept, Form, FormToConcept, DatabaseObjectWithUniqueStringID, create_db_session
from csv import DictReader


def create_db():
    dir_path = Path.cwd() / "initial_data"
    if not dir_path.exists():
        print("Initialize fromexcel.py first")
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
    session = create_db_session(location=db_path)

    # read languages and concepts into db
    for l_row in DictReader((dir_path / "lan_init.csv").open("r", encoding="utf8", newline="")):
        language = Language(l_row)
        session.add(language)
    session.commit()

    for c_row in DictReader((dir_path / "concept_init.csv").open("r", encoding="utf8", newline="")):
        concept = Concept(c_row)
        session.add(concept)
    session.commit()

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
                #print("{:}: Variants {:} of form {:} were not mentioned here.".format(
                #        set(existing_variants) - set(new_variants), existing_form))
            # link form_to_concept element to existing form
            form_to_concept.Form_ID = existing_form.ID
            session.add(form_to_concept)
    session.commit()
    session.close()

if __name__ == "__main__":
    create_db()

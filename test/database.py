from lexedata.importer.database import create_db_session

def test_create_memory_db():
    session = create_db_session(location='sqlite:///:memory:')
    session.connection().engine.dispose()


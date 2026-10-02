from app.migrate import read_sql_file, split_sql_statements


def test_ignore_les_points_virgules_dans_les_chaines_et_les_commentaires():
    sql = """-- commentaire ; avec point-virgule
CREATE TABLE a (x INT);
INSERT INTO a VALUES ('un ; deux'), ('l''apostrophe ; ok');
"""
    assert split_sql_statements(sql) == [
        "CREATE TABLE a (x INT)",
        "INSERT INTO a VALUES ('un ; deux'), ('l''apostrophe ; ok')",
    ]


def test_decoupe_le_schema_initial():
    statements = read_sql_file("001_initial_schema.sql")
    assert len([s for s in statements if s.startswith("CREATE TABLE")]) == 44
    assert len([s for s in statements if s.startswith("INSERT INTO data_source")]) == 1

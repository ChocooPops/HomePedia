import { readSqlFile, splitSqlStatements } from './sql-runner';

describe('splitSqlStatements', () => {
  it('ignore les « ; » dans les chaînes et les commentaires', () => {
    const sql = `-- commentaire ; avec point-virgule
CREATE TABLE a (x INT);
INSERT INTO a VALUES ('un ; deux'), ('l''apostrophe ; ok');
`;
    expect(splitSqlStatements(sql)).toEqual(['CREATE TABLE a (x INT)', "INSERT INTO a VALUES ('un ; deux'), ('l''apostrophe ; ok')"]);
  });

  it('découpe le schéma initial en instructions valides', () => {
    const statements = readSqlFile('001_initial_schema.sql');
    const creates = statements.filter((s) => s.startsWith('CREATE TABLE'));
    expect(creates).toHaveLength(44);
    expect(statements.filter((s) => s.startsWith('INSERT INTO data_source'))).toHaveLength(1);
  });
});

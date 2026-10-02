import { readFileSync } from 'fs';
import { join } from 'path';

/**
 * Découpe un script SQL en instructions, en ignorant les « ; » situés dans
 * des chaînes ('...' avec échappement '') ou des commentaires « -- ».
 */
export function splitSqlStatements(sql: string): string[] {
  const statements: string[] = [];
  let current = '';
  let inString = false;
  for (let i = 0; i < sql.length; i++) {
    const ch = sql[i];
    if (!inString && ch === '-' && sql[i + 1] === '-') {
      const eol = sql.indexOf('\n', i);
      i = eol === -1 ? sql.length : eol;
      current += '\n';
      continue;
    }
    if (ch === "'") {
      if (inString && sql[i + 1] === "'") {
        current += "''";
        i++;
        continue;
      }
      inString = !inString;
    }
    if (ch === ';' && !inString) {
      if (current.trim()) statements.push(current.trim());
      current = '';
      continue;
    }
    current += ch;
  }
  if (current.trim()) statements.push(current.trim());
  return statements;
}

export function readSqlFile(fileName: string): string[] {
  return splitSqlStatements(readFileSync(join(__dirname, 'sql', fileName), 'utf8'));
}

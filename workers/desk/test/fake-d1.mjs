// A D1 stand-in backed by node:sqlite, so the tests run the Worker's real SQL.
import { DatabaseSync } from 'node:sqlite';

export function fakeD1(path = ':memory:') {
  const db = new DatabaseSync(path);
  const statement = (sql, args = []) => ({
    bind: (...next) => statement(sql, next),
    first: async () => db.prepare(sql).get(...args) ?? null,
    all: async () => ({ results: db.prepare(sql).all(...args) }),
    run: async () => {
      db.prepare(sql).run(...args);
      return { success: true };
    },
    runSync: () => db.prepare(sql).run(...args),
  });
  return {
    raw: db,
    prepare: sql => statement(sql),
    // D1 runs a batch as one transaction; mirror that so partial writes surface.
    batch: async list => {
      db.exec('BEGIN');
      try {
        for (const s of list) s.runSync();
        db.exec('COMMIT');
      } catch (err) {
        db.exec('ROLLBACK');
        throw err;
      }
      return list.map(() => ({ success: true }));
    },
  };
}

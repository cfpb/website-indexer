import sqlite from 'sqlite3';

const TABLE_NAME = 'cfgov';

class DB {
  constructor (dbFilePath) {
    this.db = new sqlite.Database(dbFilePath, (err) => {
      if (err) {
        console.error('Could not connect to database', err);
      }
    });
  }

  createTable () {
    const sql = `
      CREATE TABLE IF NOT EXISTS ${TABLE_NAME} (
        id PRIMARY KEY,
        path TEXT,
        title TEXT,
        components TEXT,
        links TEXT,
        pageHash TEXT,
        timestamp TEXT
      )`;
    return this.run(sql);
  }

  insert (record) {
    const sql = `
      INSERT OR REPLACE INTO ${TABLE_NAME} (
        id,
        path,
        title,
        components,
        links,
        pageHash,
        timestamp
      ) VALUES (?, ?, ?, ?, ?, ?, ?)`;
    return this.run(sql, Object.values(record));
  }

  run (sql, params = []) {
    return new Promise((resolve, reject) => {
      this.db.run(sql, params, function (err) {
        if (err) {
          reject(err);
        } else {
          resolve({ id: this.lastID });
        }
      });
    });
  }

  getCount () {
    return new Promise((resolve, reject) => {
      this.db.all(`SELECT * FROM ${TABLE_NAME}`, (err, rows) => {
        if (err) {
          reject(err);
        } else {
          resolve(rows.length);
        }
      });
    });
  }
}

export default DB;

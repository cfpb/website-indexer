import sqlite3 from 'sqlite3';
import { open } from 'sqlite'

const TABLE_NAME = 'cfgov';

class DB {
  constructor (db) {
    this.db = db;
  }

  static async connect (dbFilePath) {
    const db = await open({
      filename: dbFilePath,
      driver: sqlite3.Database
    });

    return new DB( db );
  }

  async createTables () {
    await this.db.run(`
      CREATE TABLE IF NOT EXISTS ${TABLE_NAME} (
        path TEXT PRIMARY KEY,
        title TEXT,
        components TEXT,
        links TEXT,
        pageHash TEXT,
        pageHtml TEXT,
        timestamp TEXT
      )
    `);

    await this.db.run(`
      CREATE INDEX IF NOT EXISTS
        ${TABLE_NAME}_timestamp_idx
      ON ${TABLE_NAME} (
        timestamp
      )
    `);

    await this.db.run(`
      CREATE VIRTUAL TABLE IF NOT EXISTS ${TABLE_NAME}_fts USING fts5(
        path,
        pageHtml,
        content=${TABLE_NAME}
      )
    `);

    await this.db.run(`
      CREATE TRIGGER IF NOT EXISTS insert_${TABLE_NAME}_fts
      AFTER INSERT ON ${TABLE_NAME}
      BEGIN
        INSERT INTO ${TABLE_NAME}_fts(
          path,
          pageHtml
        ) VALUES (
          new.path,
          new.pageHtml
        );
      END
    `);
  }

  async insert (record) {
    const sql = `
      INSERT INTO ${TABLE_NAME} (
        path,
        title,
        components,
        links,
        pageHash,
        pageHtml,
        timestamp
      ) VALUES (?, ?, ?, ?, ?, ?, ?)`;

    return await this.db.run(sql, Object.values(record).map(value => {
      if (Object.prototype.toString.call(value) === '[object Date]') {
        return value.toISOString();
      } else if (typeof value === 'object') {
        return JSON.stringify(value);
      } else {
        return value;
      }
    }));
  }

  async getCount () {
    const result = await this.db.get(
      `SELECT COUNT(*) AS count FROM ${TABLE_NAME}`
    );
    return result.count;
  };
}

export default DB;

import fs from 'fs';
import Database from 'better-sqlite3';

// WARNING: Do not alter the model definitions in this file without making
// comparable changes to the schema in viewer/viewer/models.py.

class DB {
  constructor (db) {
    this.db = db;
  }

  static connect (dbFilePath) {
    const db = new Database(dbFilePath);
    return new DB( db );
  }

  createTables () {
    const sql = fs.readFileSync('db.sql', 'utf8');
    this.db.exec(sql);

    this.insertStatement = this.db.prepare(`
      INSERT INTO pages (
        crawled_at,
        path,
        html,
        title,
        hash
      ) VALUES (?, ?, ?, ?, ?)
    `);

    this.componentStatement = this.db.prepare(`
      INSERT OR IGNORE INTO components (
        name
      ) VALUES (?)
    `);

    this.pageComponentStatement = this.db.prepare(`
      INSERT INTO pages_components (
        page_id,
        component_id
      ) VALUES (?, (SELECT id FROM components WHERE name = ?))
    `);

    this.linkStatement = this.db.prepare(`
      INSERT OR IGNORE INTO links (
        url
      ) VALUES (?)
    `);

    this.pageLinkStatement = this.db.prepare(`
      INSERT INTO pages_links (
        page_id,
        link_id
      ) VALUES (?, (SELECT id FROM links WHERE url = ?))
    `);
  }

  insert (record) {
    const insertResult = this.insertStatement.run([
      record.timestamp.toISOString(),
      record.path,
      record.pageHtml,
      record.title,
      record.pageHash
    ]);

    const pageId = insertResult.lastInsertRowid;

    const insertOrIgnoreElements = this.db.transaction(
      (components, links) => {
        for (const component of components) {
          this.componentStatement.run([component]);
        }

        for (const link of links) {
          this.linkStatement.run([link]);
        }
    });
    insertOrIgnoreElements(record.components, record.links);

    const insertOrIgnoreForeignKeys = this.db.transaction(
      (page_id, components, links) => {
        for (const component of components) {
          this.pageComponentStatement.run([page_id, component]);
        }

        for (const link of links) {
          this.pageLinkStatement.run([page_id, link]);
        }
      }
    );
    insertOrIgnoreForeignKeys(pageId, record.components, record.links);
  }
};

export default DB;

BEGIN;

CREATE TABLE "components" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "name" text NOT NULL UNIQUE
);

CREATE INDEX "components_name_idx" ON "components" ("name");

CREATE TABLE "links" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "url" text NOT NULL UNIQUE
);

CREATE INDEX "links_url_idx" ON "links" ("url");

CREATE TABLE "pages" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "crawled_at" text NOT NULL,
    "path" text NOT NULL UNIQUE,
    "html" text NOT NULL,
    "title" text NOT NULL,
    "hash" text NOT NULL
);

CREATE INDEX "pages_crawled_at_idx" ON "pages" ("crawled_at");
CREATE INDEX "pages_html_idx" ON "pages" ("html");
CREATE INDEX "pages_path_idx" ON "pages" ("path");
CREATE INDEX "pages_title_idx" ON "pages" ("title");
CREATE INDEX "pages_path_title_idx" ON "pages" ("path", "title");

CREATE TABLE "pages_components" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "page_id" integer NOT NULL REFERENCES "pages" ("id") DEFERRABLE INITIALLY DEFERRED,
    "component_id" integer NOT NULL REFERENCES "components" ("id") DEFERRABLE INITIALLY DEFERRED
);

CREATE UNIQUE INDEX "pages_components_page_id_component_id_idx_uniq" ON "pages_components" ("page_id", "component_id");
CREATE INDEX "pages_components_page_id_idx" ON "pages_components" ("page_id");
CREATE INDEX "pages_components_component_id_idx" ON "pages_components" ("component_id");

CREATE TABLE "pages_links" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "page_id" integer NOT NULL REFERENCES "pages" ("id") DEFERRABLE INITIALLY DEFERRED,
    "link_id" integer NOT NULL REFERENCES "links" ("id") DEFERRABLE INITIALLY DEFERRED
);

CREATE UNIQUE INDEX "pages_links_page_id_link_id_idx_uniq" ON "pages_links" ("page_id", "link_id");
CREATE INDEX "pages_links_page_id_idx" ON "pages_links" ("page_id");
CREATE INDEX "pages_links_link_id_idx" ON "pages_links" ("link_id");

COMMIT;

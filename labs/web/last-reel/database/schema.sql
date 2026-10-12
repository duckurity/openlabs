PRAGMA journal_mode=DELETE;
CREATE TABLE films (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    year INTEGER NOT NULL,
    synopsis TEXT NOT NULL,
    genre TEXT NOT NULL,
    is_public INTEGER NOT NULL CHECK (is_public IN (0, 1))
);
CREATE TABLE clearance_records (
    id INTEGER PRIMARY KEY,
    film_id INTEGER NOT NULL REFERENCES films(id),
    clearance_note TEXT NOT NULL
);

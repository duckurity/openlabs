-- Fictional dispatch records. Secrets are inserted at runtime, not in fixtures.
CREATE TABLE runtime (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE users (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('customer','courier'))
);
CREATE TABLE sessions (
    token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
    expires_at REAL NOT NULL
);
CREATE TABLE reset_codes (
    id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL REFERENCES users(id),
    code_hash TEXT NOT NULL UNIQUE, expires_at REAL NOT NULL, used INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE mailbox (
    id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
    subject TEXT NOT NULL, body TEXT NOT NULL, code TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE lockers (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, district TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('available','in_transit','held')),
    parcels INTEGER NOT NULL, capacity INTEGER NOT NULL, address TEXT NOT NULL,
    updated_at TEXT NOT NULL, courier_id INTEGER NOT NULL REFERENCES users(id), events TEXT NOT NULL
);
CREATE TABLE routes (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, courier_id INTEGER NOT NULL REFERENCES users(id),
    dispatch_note TEXT NOT NULL DEFAULT ''
);
CREATE TABLE route_lockers (
    route_id TEXT NOT NULL REFERENCES routes(id), locker_id TEXT NOT NULL REFERENCES lockers(id),
    PRIMARY KEY(route_id, locker_id)
);
CREATE TABLE manifests (
    locker_id TEXT PRIMARY KEY REFERENCES lockers(id), reference TEXT NOT NULL,
    recipient TEXT NOT NULL, contents TEXT NOT NULL
);

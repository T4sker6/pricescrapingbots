CREATE TABLE TRACKED_PRODUCTS_HM (
    id               TEXT    PRIMARY KEY,
    name             TEXT    NOT NULL,
    minPrice         REAL,
    maxPrice         REAL,
    lastPrice        REAL,
    currentPrice     REAL    NOT NULL,
    url              TEXT    NOT NULL,
    notificationSent INTEGER NOT NULL DEFAULT 1,
    createdOn        TEXT    NOT NULL DEFAULT (datetime('now')),
    lastUpdatedOn    TEXT    NOT NULL DEFAULT (datetime('now'))
);
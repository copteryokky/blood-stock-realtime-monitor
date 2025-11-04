PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS thresholds (
  blood_type TEXT PRIMARY KEY,
  critical_min INTEGER NOT NULL,
  low_min INTEGER NOT NULL
);

INSERT OR IGNORE INTO thresholds (blood_type, critical_min, low_min) VALUES
  ('O', 30, 60),
  ('A', 25, 50),
  ('B', 25, 50),
  ('AB', 15, 30);

CREATE TABLE IF NOT EXISTS products (
  product_type TEXT PRIMARY KEY
);

INSERT OR IGNORE INTO products (product_type) VALUES
  ('PRC'), ('Platelets'), ('Plasma'), ('Cryo');

CREATE TABLE IF NOT EXISTS stock (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  blood_type TEXT NOT NULL,
  product_type TEXT NOT NULL,
  units INTEGER NOT NULL DEFAULT 0,
  UNIQUE (blood_type, product_type)
);

INSERT OR IGNORE INTO stock (blood_type, product_type, units) VALUES
  ('O', 'PRC', 40),
  ('O', 'Platelets', 15),
  ('O', 'Plasma', 20),
  ('O', 'Cryo', 5),
  ('A', 'PRC', 35),
  ('A', 'Platelets', 10),
  ('A', 'Plasma', 15),
  ('A', 'Cryo', 4),
  ('B', 'PRC', 28),
  ('B', 'Platelets', 8),
  ('B', 'Plasma', 12),
  ('B', 'Cryo', 3),
  ('AB', 'PRC', 12),
  ('AB', 'Platelets', 5),
  ('AB', 'Plasma', 8),
  ('AB', 'Cryo', 2);

CREATE TABLE IF NOT EXISTS transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  actor TEXT,
  blood_type TEXT NOT NULL,
  product_type TEXT NOT NULL,
  qty_change INTEGER NOT NULL,
  note TEXT
);

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
  source_id INTEGER PRIMARY KEY,
  source_key TEXT NOT NULL UNIQUE,
  source_name TEXT NOT NULL,
  source_url TEXT,
  license_notes TEXT,
  access_notes TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS players (
  player_pk INTEGER PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES sources(source_id),
  source_player_id TEXT NOT NULL,
  display_name TEXT,
  id_type TEXT NOT NULL DEFAULT 'source_native',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(source_id, source_player_id)
);

CREATE TABLE IF NOT EXISTS matches (
  match_pk INTEGER PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES sources(source_id),
  source_match_id TEXT,
  match_date TEXT,
  match_time TEXT,
  competition TEXT,
  player_a_pk INTEGER REFERENCES players(player_pk),
  player_b_pk INTEGER REFERENCES players(player_pk),
  sets_a INTEGER,
  sets_b INTEGER,
  winner_player_pk INTEGER REFERENCES players(player_pk),
  raw_row_json TEXT,
  imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date);
CREATE INDEX IF NOT EXISTS idx_matches_competition ON matches(competition);
CREATE INDEX IF NOT EXISTS idx_matches_players ON matches(player_a_pk, player_b_pk);

CREATE TABLE IF NOT EXISTS match_games (
  game_pk INTEGER PRIMARY KEY,
  match_pk INTEGER NOT NULL REFERENCES matches(match_pk) ON DELETE CASCADE,
  game_number INTEGER NOT NULL,
  points_a INTEGER,
  points_b INTEGER,
  UNIQUE(match_pk, game_number)
);

CREATE TABLE IF NOT EXISTS player_stats_snapshots (
  snapshot_pk INTEGER PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES sources(source_id),
  player_pk INTEGER NOT NULL REFERENCES players(player_pk),
  snapshot_date TEXT,
  rating_type TEXT,
  rating_value REAL,
  solidity REAL,
  matches_played INTEGER,
  raw_row_json TEXT
);

CREATE TABLE IF NOT EXISTS identity_links (
  identity_link_pk INTEGER PRIMARY KEY,
  player_pk_a INTEGER NOT NULL REFERENCES players(player_pk),
  player_pk_b INTEGER NOT NULL REFERENCES players(player_pk),
  proposed_name TEXT,
  status TEXT NOT NULL DEFAULT 'candidate'
    CHECK(status IN ('candidate', 'verified', 'rejected')),
  evidence_json TEXT,
  verified_by TEXT,
  verified_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK(player_pk_a <> player_pk_b),
  UNIQUE(player_pk_a, player_pk_b)
);

CREATE TABLE IF NOT EXISTS import_log (
  import_pk INTEGER PRIMARY KEY,
  source_id INTEGER REFERENCES sources(source_id),
  filename TEXT NOT NULL,
  file_sha256 TEXT,
  imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  rows_seen INTEGER,
  rows_loaded INTEGER,
  status TEXT NOT NULL,
  notes TEXT
);

CREATE VIEW IF NOT EXISTS named_match_results AS
SELECT m.match_pk, s.source_name, m.match_date, m.match_time, m.competition,
       pa.display_name AS player_a, pb.display_name AS player_b,
       m.sets_a, m.sets_b, pw.display_name AS winner
FROM matches m
JOIN sources s ON s.source_id = m.source_id
LEFT JOIN players pa ON pa.player_pk = m.player_a_pk
LEFT JOIN players pb ON pb.player_pk = m.player_b_pk
LEFT JOIN players pw ON pw.player_pk = m.winner_player_pk;

CREATE VIEW IF NOT EXISTS identity_review_queue AS
SELECT il.identity_link_pk, il.proposed_name, il.status, il.evidence_json,
       a.source_player_id AS source_a_player_id, a.display_name AS source_a_name,
       sa.source_name AS source_a,
       b.source_player_id AS source_b_player_id, b.display_name AS source_b_name,
       sb.source_name AS source_b
FROM identity_links il
JOIN players a ON a.player_pk = il.player_pk_a
JOIN sources sa ON sa.source_id = a.source_id
JOIN players b ON b.player_pk = il.player_pk_b
JOIN sources sb ON sb.source_id = b.source_id;
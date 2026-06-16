-- Enable TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Time-series price data
CREATE TABLE candles (
  time        TIMESTAMPTZ NOT NULL,
  instrument  TEXT NOT NULL,
  granularity TEXT NOT NULL,
  open        DECIMAL,
  high        DECIMAL,
  low         DECIMAL,
  close       DECIMAL,
  volume      INTEGER
);

SELECT create_hypertable('candles', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_candles_instrument_granularity
  ON candles (instrument, granularity, time DESC);

-- Bot registry
CREATE TABLE bots (
  id          TEXT PRIMARY KEY,
  name        TEXT,
  instrument  TEXT,
  strategy    TEXT,
  status      TEXT,
  config      JSONB,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Trade log
CREATE TABLE trades (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bot_id         TEXT REFERENCES bots(id),
  oanda_trade_id TEXT,
  instrument     TEXT,
  direction      TEXT,
  units          INTEGER,
  open_price     DECIMAL,
  close_price    DECIMAL,
  open_time      TIMESTAMPTZ,
  close_time     TIMESTAMPTZ,
  pnl            DECIMAL,
  status         TEXT
);

CREATE INDEX IF NOT EXISTS idx_trades_bot_id ON trades (bot_id, open_time DESC);

-- Signal log
CREATE TABLE signals (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bot_id        TEXT REFERENCES bots(id),
  time          TIMESTAMPTZ,
  direction     TEXT,
  confidence    DECIMAL,
  ml_features   JSONB,
  news_trigger  TEXT,
  acted_on      BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_signals_bot_id ON signals (bot_id, time DESC);

-- News + sentiment
CREATE TABLE news (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  time            TIMESTAMPTZ,
  source          TEXT,
  headline        TEXT,
  sentiment_score DECIMAL,
  instruments     TEXT[],
  raw_response    JSONB
);

CREATE INDEX IF NOT EXISTS idx_news_time ON news (time DESC);

-- Seed placeholder bots for local dev
INSERT INTO bots (id, name, instrument, strategy, status, config) VALUES
  (
    'gold_momentum_v1',
    'Gold Momentum Bot',
    'XAU_USD',
    'momentum',
    'stopped',
    '{"position_size": 1, "risk_pct": 0.01}'::jsonb
  ),
  (
    'gold_sentiment_v1',
    'Gold Sentiment Bot',
    'XAU_USD',
    'sentiment',
    'stopped',
    '{"position_size": 1, "risk_pct": 0.01}'::jsonb
  );

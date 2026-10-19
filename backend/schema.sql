
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS farmers (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT NOT NULL,
 village TEXT NOT NULL, bank_reference TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS crops (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, grades TEXT NOT NULL,
 threshold TEXT NOT NULL, max_moisture TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS prices (
 id INTEGER PRIMARY KEY, crop_id INTEGER NOT NULL REFERENCES crops(id),
 grade TEXT NOT NULL, price TEXT NOT NULL, effective_from TEXT NOT NULL,
 UNIQUE(crop_id, grade, effective_from)
);
CREATE INDEX IF NOT EXISTS price_lookup ON prices(crop_id,grade,effective_from DESC);
CREATE TABLE IF NOT EXISTS advances (
 id INTEGER PRIMARY KEY, farmer_id INTEGER NOT NULL REFERENCES farmers(id),
 amount TEXT NOT NULL, given_on TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS payouts (
 id INTEGER PRIMARY KEY, farmer_id INTEGER NOT NULL REFERENCES farmers(id),
 week TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('Draft','Finalised','Paid')),
 gross TEXT NOT NULL, deduction TEXT NOT NULL, net TEXT NOT NULL,
 created_at TEXT NOT NULL, finalised_at TEXT, paid_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS one_draft ON payouts(farmer_id,week) WHERE status='Draft';
CREATE TABLE IF NOT EXISTS deliveries (
 id INTEGER PRIMARY KEY, farmer_id INTEGER NOT NULL REFERENCES farmers(id),
 crop_id INTEGER REFERENCES crops(id), grade TEXT,
 gross_kg TEXT, moisture TEXT, delivered_on TEXT NOT NULL,
 deduction_pct TEXT, deduction_kg TEXT, net_kg TEXT, applied_price TEXT,
 price_id INTEGER REFERENCES prices(id), amount TEXT NOT NULL,
 original_id INTEGER REFERENCES deliveries(id), reason TEXT,
 payout_id INTEGER REFERENCES payouts(id), created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS delivery_week ON deliveries(farmer_id,delivered_on,payout_id);
CREATE INDEX IF NOT EXISTS advance_farmer ON advances(farmer_id);
CREATE INDEX IF NOT EXISTS payout_farmer ON payouts(farmer_id,status);

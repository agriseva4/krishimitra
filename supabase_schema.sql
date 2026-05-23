-- ================================================================
-- KrishiMitra v3 — Complete Supabase Schema
-- SQL Editor madhe FULL content paste karun RUN kara
-- Already run kele asel tar pun safe ahe (IF NOT EXISTS)
-- ================================================================

CREATE TABLE IF NOT EXISTS farmers (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    phone       VARCHAR(20) UNIQUE NOT NULL,
    name        VARCHAR(100) DEFAULT 'Farmer',
    district    VARCHAR(100) DEFAULT 'Pune',
    city        VARCHAR(100) DEFAULT 'Pune',
    lat         DECIMAL(10,6) DEFAULT 18.5204,
    lon         DECIMAL(10,6) DEFAULT 73.8567,
    crops       TEXT[] DEFAULT ARRAY['onion','tomato'],
    language    VARCHAR(5) DEFAULT 'mr',
    is_approved BOOLEAN DEFAULT FALSE,
    is_free     BOOLEAN DEFAULT FALSE,
    is_blocked  BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversations (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    farmer_phone    VARCHAR(20) NOT NULL,
    message_type    VARCHAR(20) DEFAULT 'text',
    user_message    TEXT,
    bot_response    TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mandi_prices (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    commodity   VARCHAR(50) NOT NULL,
    district    VARCHAR(100) NOT NULL,
    market      VARCHAR(100),
    min_price   DECIMAL(10,2),
    max_price   DECIMAL(10,2),
    modal_price DECIMAL(10,2),
    price_date  DATE NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(commodity, market, price_date)
);

CREATE INDEX IF NOT EXISTS idx_farmers_phone    ON farmers(phone);
CREATE INDEX IF NOT EXISTS idx_farmers_approved ON farmers(is_approved);
CREATE INDEX IF NOT EXISTS idx_conv_phone       ON conversations(farmer_phone);
CREATE INDEX IF NOT EXISTS idx_mandi_commodity  ON mandi_prices(commodity, price_date DESC);
CREATE INDEX IF NOT EXISTS idx_mandi_district   ON mandi_prices(district, price_date DESC);

ALTER TABLE farmers       ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE mandi_prices  ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  CREATE POLICY "service_farmers" ON farmers FOR ALL TO service_role USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE POLICY "service_conv" ON conversations FOR ALL TO service_role USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE POLICY "service_mandi" ON mandi_prices FOR ALL TO service_role USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE POLICY "anon_no_farmers" ON farmers FOR ALL TO anon USING (false);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE POLICY "anon_no_conv" ON conversations FOR ALL TO anon USING (false);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE POLICY "anon_no_mandi" ON mandi_prices FOR ALL TO anon USING (false);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ================================================================
-- TUMCHA NUMBER ADD KAR (uncomment karun number paste kar)
-- Format: 91 + 10 digit = 91XXXXXXXXXX
-- ================================================================
-- INSERT INTO farmers (phone, name, district, city, crops, language, is_approved, is_free)
-- VALUES ('91XXXXXXXXXX', 'Farmer', 'Pune', 'Pune', ARRAY['onion','tomato'], 'mr', true, true)
-- ON CONFLICT (phone) DO NOTHING;

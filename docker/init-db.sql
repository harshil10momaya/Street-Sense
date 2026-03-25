-- StreetSense — Database Initialization
-- Runs automatically when PostgreSQL container starts for the first time

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable PostGIS for spatial queries (optional, for future geo-queries)
-- CREATE EXTENSION IF NOT EXISTS "postgis";

-- Verify
SELECT 'StreetSense database initialized' AS status;

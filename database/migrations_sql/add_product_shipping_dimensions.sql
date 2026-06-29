-- Package dimensions for Shiprocket (stored in centimeters)
ALTER TABLE royal.producttbl
    ADD COLUMN IF NOT EXISTS length_cm DOUBLE PRECISION DEFAULT 0,
    ADD COLUMN IF NOT EXISTS breadth_cm DOUBLE PRECISION DEFAULT 0,
    ADD COLUMN IF NOT EXISTS height_cm DOUBLE PRECISION DEFAULT 0;

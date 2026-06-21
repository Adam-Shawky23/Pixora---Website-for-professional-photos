-- ============================================================
--  Pixora Migration
--  Run once: psql -d k29photo -f migration_pixora.sql
-- ============================================================

-- Album visibility (if not already added)
ALTER TABLE albums
    ADD COLUMN IF NOT EXISTS visibility VARCHAR(10) NOT NULL DEFAULT 'public'
    CHECK (visibility IN ('public', 'private', 'friends'));

-- Per-user album access for 'friends' visibility
CREATE TABLE IF NOT EXISTS album_access (
    album_id INT NOT NULL REFERENCES albums(album_id) ON DELETE CASCADE,
    user_id  INT NOT NULL REFERENCES users(user_id)   ON DELETE CASCADE,
    PRIMARY KEY (album_id, user_id)
);

-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
    notif_id   SERIAL PRIMARY KEY,
    user_id    INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,  -- recipient
    actor_id   INT REFERENCES users(user_id) ON DELETE CASCADE,           -- who triggered it
    type       VARCHAR(20) NOT NULL CHECK (type IN ('like','comment','friend')),
    message    TEXT NOT NULL,
    link       VARCHAR(255),   -- URL to navigate to when clicked
    is_read    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifs_user    ON notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_album_access_album ON album_access(album_id);
CREATE INDEX IF NOT EXISTS idx_album_access_user  ON album_access(user_id);

-- DOB cannot be in the future
ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_dob_not_future;
ALTER TABLE users ADD CONSTRAINT chk_dob_not_future
    CHECK (dob IS NULL OR dob <= CURRENT_DATE);

-- Add uploaded_at and file_size to photos (if not already there)
ALTER TABLE photos ADD COLUMN IF NOT EXISTS uploaded_at TIMESTAMP DEFAULT NOW();
ALTER TABLE photos ADD COLUMN IF NOT EXISTS file_size   INT;
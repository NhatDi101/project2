-- Run this once as a MySQL administrator, not as the application account.
CREATE DATABASE IF NOT EXISTS users_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS users_db.users (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT users_name_not_empty CHECK (CHAR_LENGTH(TRIM(name)) > 0)
) ENGINE=InnoDB;

-- Create app_user interactively and grant only these required permissions:
-- GRANT SELECT, INSERT ON users_db.users TO 'app_user'@'127.0.0.1';

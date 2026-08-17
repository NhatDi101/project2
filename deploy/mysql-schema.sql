-- First select the target database, for example: USE app_db;
-- Run this once as a MySQL administrator, not as the application account.
CREATE TABLE IF NOT EXISTS users (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT users_name_not_empty CHECK (CHAR_LENGTH(TRIM(name)) > 0)
) ENGINE=InnoDB;

-- Grant the application role only the permissions it needs, for example:
-- GRANT SELECT, INSERT ON app_db.users TO 'app_user'@'127.0.0.1';

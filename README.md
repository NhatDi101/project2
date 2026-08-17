# Flask Users API with MySQL and systemd

The service is the application/database component of the project. It listens
only on `127.0.0.1:8000`; Nginx or Apache can proxy requests to it. User data is
stored in MySQL, not in application memory.

## 1. Configure MySQL on Linux

Install MySQL Server. Configure its TCP listeners to stay on loopback by
installing [deploy/mysql-local.cnf](deploy/mysql-local.cnf):

```bash
# Ubuntu/Debian
sudo install -m 0644 deploy/mysql-local.cnf /etc/mysql/conf.d/users-api-local.cnf
sudo systemctl restart mysql

# CentOS Stream with MySQL Server packages
sudo install -m 0644 deploy/mysql-local.cnf /etc/my.cnf.d/users-api-local.cnf
sudo systemctl restart mysqld
```

Verify MySQL is not exposed to the network. The output may show port `3306`
and, if enabled, X Protocol port `33060`, but both must use `127.0.0.1`:

```bash
sudo ss -ltnp | grep -E '3306|33060'
```

Open the MySQL administrator prompt and provision the database/table using the
schema file. The application account is deliberately not an owner and cannot
alter schema:

```bash
sudo mysql
```

At the `mysql>` prompt, run the following. Replace only the placeholder with a
password chosen for the running server; never place that password in this
repository or report.

```sql
SOURCE /absolute/path/to/project/deploy/mysql-schema.sql;
CREATE USER 'app_user'@'127.0.0.1' IDENTIFIED BY '<APP_DB_PASSWORD>';
GRANT SELECT, INSERT ON users_db.users TO 'app_user'@'127.0.0.1';
```

If the user already exists, use `ALTER USER` instead of `CREATE USER`. The app
needs only `SELECT` and `INSERT`; it has no `CREATE`, `ALTER`, `DROP`, or MySQL
administrator privilege.

## 2. Run locally

Copy the example configuration and fill in the database password used above.
`.env` is ignored by Git and loaded only for local development.

```bash
cp .env.example .env
# Edit .env and set DB_PASSWORD.
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Windows PowerShell equivalent:

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

At startup the application verifies it can access the pre-created `users`
table. Open `http://127.0.0.1:8000/health`; HTTP 200 means Flask can reach
MySQL.

## 3. Install as a systemd service

Deploy the project to `/opt/users-api`, create a dedicated unprivileged Linux
account, and install dependencies:

```bash
sudo useradd --system --home-dir /opt/users-api --shell /usr/sbin/nologin users-api
sudo chown -R users-api:users-api /opt/users-api
sudo -u users-api python3 -m venv /opt/users-api/.venv
sudo -u users-api /opt/users-api/.venv/bin/pip install -r /opt/users-api/requirements.txt
```

Keep the production secret outside the source directory. The service reads this
file through `EnvironmentFile=`:

```bash
sudo install -d -o root -g users-api -m 0750 /etc/users-api
sudo cp /opt/users-api/.env.example /etc/users-api/users-api.env
sudo chown root:users-api /etc/users-api/users-api.env
sudo chmod 0640 /etc/users-api/users-api.env
sudoedit /etc/users-api/users-api.env
```

Install and enable the unit:

```bash
sudo cp /opt/users-api/deploy/users-api.service /etc/systemd/system/users-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now users-api
sudo systemctl status users-api
```

`Restart=on-failure` restarts Gunicorn after an unexpected exit. Logs go to
stdout/stderr and systemd collects them in journald:

```bash
journalctl -u users-api -f
```

To prove automatic recovery during the demo, identify a Gunicorn worker PID,
kill it, then inspect the restart event:

```bash
pgrep -a gunicorn
sudo kill -9 <GUNICORN_PID>
systemctl status users-api
journalctl -u users-api -n 50 --no-pager
```

## API

```bash
# Read users
curl http://127.0.0.1:8000/api/users

# Create a user
curl -X POST http://127.0.0.1:8000/api/users \
  -H 'Content-Type: application/json' \
  -d '{"name":"Lan"}'
```

- `GET /api/users` returns data from MySQL.
- `POST /api/users` inserts a record into MySQL and returns HTTP 201.
- `GET /health` returns HTTP 200 only when MySQL is reachable.

## Submission safety

Do not include `.env`, `/etc/users-api/users-api.env`, database passwords, or
private keys in the final `capstone_<group>.tar.gz`. Submit `.env.example` and
configuration templates only.

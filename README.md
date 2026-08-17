# Flask Users API with PostgreSQL and systemd

The API binds only to `127.0.0.1:8000`; Nginx or Apache can proxy requests to
it. User records are stored in PostgreSQL, not in application memory.

## 1. Configure PostgreSQL (Linux)

Install PostgreSQL using your distribution's package manager. Create an
application account and database, then choose the password when prompted:

```bash
sudo -u postgres createuser --pwprompt app_user
sudo -u postgres createdb --owner=app_user users_db
```

Set PostgreSQL to accept TCP connections only on the loopback interface. Add
the contents of [deploy/postgresql-local.conf](deploy/postgresql-local.conf)
to the server's `postgresql.conf`. Add the rule from
[deploy/pg_hba.conf.example](deploy/pg_hba.conf.example) to `pg_hba.conf`, then
restart PostgreSQL:

```bash
sudo systemctl restart postgresql
sudo ss -ltnp | grep 5432
```

The last command must show `127.0.0.1:5432` and must not show `0.0.0.0:5432`
or `[::]:5432`.

## 2. Run locally

Copy the example configuration and set the actual database password. `.env` is
ignored by Git and is loaded automatically only for local development.

```bash
cp .env.example .env
# Edit .env: set DB_PASSWORD to the password selected above.
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

The first application startup creates the `users` table automatically. Open
`http://127.0.0.1:8000/health`; a `200` response means Flask can connect to
PostgreSQL.

## 3. Install as a systemd service

Deploy this project to `/opt/users-api`, create a dedicated unprivileged user,
and install its Python dependencies:

```bash
sudo useradd --system --home-dir /opt/users-api --shell /usr/sbin/nologin users-api
sudo chown -R users-api:users-api /opt/users-api
sudo -u users-api python3 -m venv /opt/users-api/.venv
sudo -u users-api /opt/users-api/.venv/bin/pip install -r /opt/users-api/requirements.txt
```

Keep the production password outside the source tree. Copy the example file,
edit it, and make it readable only to the service account:

```bash
sudo install -d -o root -g users-api -m 0750 /etc/users-api
sudo cp /opt/users-api/.env.example /etc/users-api/users-api.env
sudo chown root:users-api /etc/users-api/users-api.env
sudo chmod 0640 /etc/users-api/users-api.env
sudoedit /etc/users-api/users-api.env
```

Install and start the unit:

```bash
sudo cp /opt/users-api/deploy/users-api.service /etc/systemd/system/users-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now users-api
sudo systemctl status users-api
```

The unit uses `Restart=on-failure` with a five-second delay, so it starts after
boot and restarts if Gunicorn or the app exits unexpectedly. Its logs go to
standard output/error and are collected by journald:

```bash
journalctl -u users-api -f
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

- `GET /api/users` returns records from PostgreSQL.
- `POST /api/users` accepts a JSON body with non-empty `name` and returns the
  inserted record with HTTP 201.
- `GET /health` returns HTTP 200 only if PostgreSQL is reachable.

## Nginx reverse proxy example

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

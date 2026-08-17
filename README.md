# Local Flask Users API

## Setup and run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DB_HOST = "127.0.0.1"
$env:DB_PORT = "3306"
$env:DB_USER = "app_user"
$env:DB_NAME = "app_db"
$env:DB_PASSWORD = "replace-with-a-real-password"
python app.py
```

The service listens only on `127.0.0.1:8000`, so it is intended to sit behind
Nginx or Apache. Logs are emitted to standard output and can therefore be
collected by `systemd`/`journald`.

## API

```powershell
# Read users
Invoke-RestMethod http://127.0.0.1:8000/api/users

# Create a user
Invoke-RestMethod http://127.0.0.1:8000/api/users -Method Post -ContentType 'application/json' -Body '{"name":"Lan"}'
```

GET /api/users returns the current list from the MySQL database. POST /api/users accepts JSON with a non-empty name field and returns the newly created user with HTTP 201.

It loads DB_HOST, DB_PORT, DB_NAME, DB_USER, and DB_PASSWORD strictly from the environment so database integration can use the same secure configuration.
# Troubleshooting

Problems seen while building and running this project, with the fix for each.

## "Could not connect to the database"

Python can't reach PostgreSQL. Most likely first:

1. **Docker isn't running, or the postgres container is stopped.** Open Docker Desktop, then
   `docker compose up -d postgres` and `docker compose ps` (it should be *running* / *healthy*).
2. **Wrong credentials.** Docker creates the database as `socuser` / `socpassword` / `soc_db` (see `docker-compose.yml`). Your
   `DATABASE_URL` must match.
3. **Another PostgreSQL owns port 5432** (a Windows install, for example). Check with `netstat -ano | findstr :5432`;
   stop the other one or change the port mapping in `docker-compose.yml`.
4. **Wrong host.** From your PC use `localhost`; only containers use the hostname `postgres`.

Test the connection independently of Python:

```powershell
docker compose exec postgres psql -U socuser -d soc_db -c "select 1;"
```

The backend container *waits* up to 60 seconds for the database on start-up and then exits with a message naming this problem.

## Setting `DATABASE_URL` on Windows

PowerShell: `$env:DATABASE_URL="postgresql+psycopg2://socuser:socpassword@localhost:5432/soc_db"` (lasts for that window).
Bash/macOS/Linux: `export DATABASE_URL=...`. Command Prompt: `set DATABASE_URL=...`.

## "A module that was compiled using NumPy 1.x cannot be run in NumPy 2.x"

Installing `requirements.txt` into Anaconda upgraded NumPy underneath packages Anaconda built for NumPy 1.x
(pyarrow, bottleneck, ...). Pandas survives it with warnings, but the environment is fragile. Give the project its own
virtual environment:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Then select that interpreter in VS Code (`Ctrl+Shift+P` -> *Python: Select Interpreter*).

## Pylance: `Import "app...." could not be resolved`

Editor warnings only; the code runs. Pylance doesn't know the `app` package lives in `backend/`. The repository includes
`.vscode/settings.json` with `"python.analysis.extraPaths": ["./backend"]`. Make sure that `.vscode` folder sits at the
**project root** (next to `backend/`), then *Developer: Reload Window*. A different warning (for `pandas`, `sqlalchemy`)
means VS Code is using the wrong interpreter.

## Running the scripts

Run them from the **project root**, with the virtual environment active and `DATABASE_URL` set:

```powershell
python scripts/seed_demo_data.py
python scripts/train_model.py nslkdd_binary.csv --label-column label --attack-values attack --contamination 0.08
```

Under Docker the `scripts/` folder is mounted into the backend container, so this also works:
`docker compose exec backend python scripts/seed_demo_data.py`.

## ML training says "need at least 5 ..."

There aren't enough events to form 5 time windows. Every scenario comes from one IP, so running scenarios alone isn't
enough. Seed baseline data first (`scripts/seed_demo_data.py`, 600 synthetic events), then train.

## Tests

* **"Refusing to run: test database name must end in '_test'"** is the safety guard working. Point `TEST_DATABASE_URL`
  at a database such as `soc_test`.
* **`database "soc_test" does not exist`**: create it once:
  `docker compose exec postgres psql -U socuser -d soc_db -c "CREATE DATABASE soc_test;"`
  (a *fresh* Docker volume creates it automatically).
* **Running the tests inside Docker:**
  `docker compose exec -e TEST_DATABASE_URL=postgresql+psycopg2://socuser:socpassword@postgres:5432/soc_test backend pytest`
* **Frontend: `npm ci` fails with "lock file out of sync"**: run `npm install` once and commit the updated `package-lock.json`.

## Migrations

* A **brand-new** database is created by the bootstrap (`python -m app.bootstrap`, run automatically by the Docker
  container) using migration `0001`.
* A database you **already had** from before migrations existed is detected and adopted as-is (its data is not touched).
* To start completely fresh: `docker compose down -v` **deletes the database volume and all its data**, then `docker compose up --build`.
* After changing a model, create a migration: `cd backend && alembic revision --autogenerate -m "describe change"`.
  A test fails if models and migrations disagree.

## The UI says "reconnecting..." or pages stay empty

The browser can't reach the backend. Check `docker compose ps` (backend *healthy*), open
<http://localhost:8000/api/health>, and look at `docker compose logs backend`. The *System Health* page shows the same
information inside the app.

## "Could not validate credentials" after a while

Tokens expire after 60 minutes (`ACCESS_TOKEN_EXPIRE_MINUTES`), and changing `JWT_SECRET_KEY` invalidates all of them.
Sign in again.

## Docker: the frontend can't install packages

The frontend image uses `npm ci`, which needs `package-lock.json` in `frontend/`. Don't delete it.

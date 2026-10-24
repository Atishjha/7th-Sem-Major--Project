-- Runs once, when the postgres volume is first created (docker-entrypoint-initdb.d).
-- Gives the pytest suite its own throw-away database so it can never touch soc_db.
-- Already have a volume? Run once by hand:
--   docker compose exec postgres psql -U socuser -d soc_db -c "CREATE DATABASE soc_test;"
CREATE DATABASE soc_test;

-- Installs the pgvector extension on first boot of the postgres container.
-- Runs automatically because postgres images execute scripts in /docker-entrypoint-initdb.d/.

CREATE EXTENSION IF NOT EXISTS vector;

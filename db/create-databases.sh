#!/bin/sh
# Creates a login role and a database (owned by that role) for every "name:password" pair in $APP_DATABASES.
# Safe to run repeatedly: existing roles/databases are kept, and passwords are re-synced from the environment.
set -eu

for entry in $APP_DATABASES; do
  name=${entry%%:*}
  pass=${entry#*:}
  echo "ensuring database '$name'"
  psql -v ON_ERROR_STOP=1 -q -v name="$name" -v pass="$pass" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN', :'name')
  WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'name')\gexec
SELECT format('ALTER ROLE %I WITH LOGIN PASSWORD %L', :'name', :'pass')\gexec
SELECT format('CREATE DATABASE %I OWNER %I', :'name', :'name')
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'name')\gexec
-- Only the owning role (and the superuser) may connect.
SELECT format('REVOKE CONNECT ON DATABASE %I FROM PUBLIC', :'name')\gexec
SQL
done

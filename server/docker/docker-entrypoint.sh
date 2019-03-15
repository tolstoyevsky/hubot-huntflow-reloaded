#!/bin/bash
# Copyright 2019 Evgeny Golyshev. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -x

LOGLEVEL=${LOGLEVEL:="info"}

LOG_FILE=${LOG_FILE:="/var/log/huntflow-reloaded-server.log"}

POSTGRES_DBNAME=${POSTGRES_DBNAME:="huntflow-reloaded"}

POSTGRES_HOST=${POSTGRES_HOST:="127.0.0.1"}

POSTGRES_PASSWORD=${POSTGRES_PASSWORD:=""}

POSTGRES_PORT=${POSTGRES_PORT:="5432"}

POSTGRES_USER=${POSTGRES_USER:="postgres"}

REDIS_HOST=${REDIS_HOST:="127.0.0.1"}

REDIS_PASSWORD=${REDIS_PASSWORD:=""}

REDIS_PORT=${REDIS_PORT:="16379"}

TZ=${TZ:="Europe/Moscow"}

set +x

if [ -z "${POSTGRES_PASSWORD}" ]; then
    >&2 echo "Postgres password is not specified"
    exit 1
fi

>&2 echo "Waiting for Redis"

./bin/wait-for-it.sh -h "${REDIS_HOST}" -p "${REDIS_PORT}" -t 90 -- >&2 echo "Redis is ready"

>&2 echo "Waiting for Postgres"

./bin/wait-for-it.sh  -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -t 90 -- >&2 echo "Postgres is ready"

output="$(PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -lqt| cut -d \| -f 1 | grep "${POSTGRES_DBNAME}")"

if [ "${output}" ]; then
    >&2 echo "Database ${POSTGRES_DBNAME} exists"
else
    >&2 echo "Creating the ${POSTGRES_DBNAME} database"

    PGPASSWORD="${POSTGRES_PASSWORD}" createdb -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" "${POSTGRES_DBNAME}"
fi

>&2 echo "Apply migrations"
./alembic/migrate.sh postgresql://"${POSTGRES_USER}":"${POSTGRES_PASS}"@"${POSTGRES_HOST}":"${POSTGRES_PORT}"/"${POSTGRES_DBNAME}"

args=()

args+=( --logging="${LOGLEVEL}" )

args+=( --postgres_dbname="${POSTGRES_DBNAME}" )

args+=( --postgres_host="${POSTGRES_HOST}" )

args+=( --postgres_pass="${POSTGRES_PASSWORD}" )

args+=( --postgres_port="${POSTGRES_PORT}" )

args+=( --postgres_user="${POSTGRES_USER}" )

args+=( --redis-host="${REDIS_HOST}" )

args+=( --redis-password="${REDIS_PASSWORD}" )

args+=( --redis-port="${REDIS_PORT}" )

args+=( --log-file-prefix="${LOG_FILE}" )

>&2 echo "huntflow-reloaded-server is starting..."

env PYTHONPATH="$(pwd)" python3 bin/server.py "${args[@]}" $*

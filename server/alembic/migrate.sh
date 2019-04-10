#!/bin/bash
ALEMBIC_PATH="$(which alembic)"
if [ ! -f alembic.ini ]; then
    # alembic script should be run in directory with alembic.ini config file
    cd server/
fi
export POSTGRES_URL=${POSTGRES_URL="$1"}
env PYTHONPATH=$(pwd) ${ALEMBIC_PATH} upgrade head

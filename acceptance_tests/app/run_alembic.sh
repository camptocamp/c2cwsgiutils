#!/bin/bash
# Upgrade the DB
set -e

# wait for the DB to be UP
while ! echo "import sqlalchemy; sqlalchemy.create_engine('$SQLALCHEMY_URL').connect()" | python 2> /dev/null
do
    echo "Waiting for the DB to be reachable"
    sleep 1;
done

for ini in *alembic*.ini
do
    if [[ -f $ini ]]
    then
        echo "$ini ==========================="
        alembic -c $ini upgrade head
    fi
done

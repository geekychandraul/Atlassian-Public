#!/bin/bash

# Stop JIRA.
# Copy last production database backup to this host.
# Copy production filesystem to this host.
# Make a changes to colors, mail, look and feel etc.
# Start JIRA.
# Rebuild indexes.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

PSQL=/usr/bin/psql
PSQL_ARGS="--username $JIRA_DB_USER --host $JIRA_DB_HOST --port $JIRA_DB_PORT"

if [ "$ATLASSIAN_ENVIRONMENT" == "prod" ] ; then
    echo "This command should not be run from production." >&2
    exit 1
fi

PRODUCTION_HOST=$PRODUCTION_HOST_NAME
BIN_DIR=$JIRA_HOME/bin
BACKUP_DIR=$JIRA_BACKUP_DIRECTORY


$BIN_DIR/stop-jira.sh

mkdir -p $BACKUP_DIR

NEW_BACKUP=$(ssh -o BatchMode=yes $PRODUCTION_HOST "cd $BACKUP_DIR && ls jira*bz2" 2>/dev/null | tail -1)
scp -o BatchMode=yes $PRODUCTION_HOST:$BACKUP_DIR/$NEW_BACKUP /tmp/$NEW_BACKUP 2>/dev/null
echo "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '$JIRA_DB_NAME' AND pid <> pg_backend_pid();" | $PSQL $PSQL_ARGS
echo "drop database $JIRA_DB_NAME; create database $JIRA_DB_NAME owner=$JIRA_DB_USER encoding='UTF8'; grant connect on database $JIRA_DB_NAME to $JIRA_DB_USER; grant connect on database $JIRA_DB_NAME to automation;" | $PSQL $PSQL_ARGS

bzcat /tmp/$NEW_BACKUP | $PSQL $PSQL_ARGS $JIRA_DB_NAME

rsync --archive --delete $PRODUCTION_HOST:$JIRA_DATA/atlassian $JIRA_DATA 2>/dev/null
rsync --archive --delete $PRODUCTION_HOST:$JIRA_HOME $JIRA_INSTALLATION_DIR 2>/dev/null

rm $JIRA_DATA/log/* $JIRA_HOME/logs/*

"$SCRIPT_DIR/changes-jira-db.sh"

rm -f $JIRA_DATA/.jira-home.lock
exit
$BIN_DIR/start-jira.sh
sleep 240

"$SCRIPT_DIR/jira-reindex.py"

#!/usr/bin/env python3
"""
This is a convenience script to reindex JIRA instead of using the web interface.
It locks JIRA.
"""
import http
import json
import os
import shutil
import sys
import time
# Imports above are standard Python, imports below are Third-party
import foundation
import requests

PORT = os.environ["JIRA_PORT"]
URI = os.environ.get("ATLASSIAN_URI")
INDEX_DIR = "JIRA_INDEX_DIRECCTORY"
USER = 'USER_ID_WITH_ADMIN_PRIVLAGES'
PASSWORD = "USER_ADMIN_PASSWORD"
HEADER_DICT = {'Content-Type': 'application/json', 'Accept': 'application/json'}
WAIT = 60 # seconds
MAX_TIME = 3600 # seconds (we will track it for this long, we don't kill it)

foundation.logging().info("Removing existing index files ...")
is_removed_indexes = False
for i in range(5):
    try:
        shutil.rmtree(INDEX_DIR)
        is_removed_indexes = True
        break
    except FileNotFoundError:
        foundation.logging().warn("No index files to delete.")
        is_removed_indexes = True
        break
    except (OSError, shutil.Error) as e:
        foundation.logging().warn(str(e))
        time.sleep(1)
if not is_removed_indexes:
    foundation.logging().critical("Could not delete {INDEX_DIR}, try again in 2 minutes.".format(**locals()))
    sys.exit(1)

url = "https://{URI}/rest/api/2/reindex?type=FOREGROUND".format(**locals())
foundation.logging().info("Starting index ...")
try:
    response = requests.post(url, headers=HEADER_DICT, auth=(USER, PASSWORD), timeout=WAIT)
    if response.status_code not in (http.client.ACCEPTED, ):
        foundation.logging().critical("%d: %s" % (response.status_code, response.text))
        sys.exit(1)
except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
    foundation.logging().critical("JIRA is not running or not accepting requests, Kindly make sure it is running.")
    sys.exit(1)

reindex_progress_url = response.json()['progressUrl']
_, task_id = progress_url.split("=")

for i in range(int(MAX_TIME/WAIT)):
    time.sleep(WAIT)
    url = "https://{URI}/rest/api/2/reindex?%s".format(**locals()) % task_id
    try:
        response = requests.get(url, headers=HEADER_DICT, auth=(USER, PASSWORD), timeout=WAIT, allow_redirects=False)
        current_progress = response.json()['currentProgress']
        foundation.logging().info("Current progress: %s%%" % current_progress)
        if current_progress == 100:
            break
    except Exception as e:
        foundation.logging().error(str(e))

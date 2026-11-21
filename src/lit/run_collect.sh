#!/bin/sh
cd "$(dirname "$0")/../../papers"
python -I ../src/lit/audit_collect_epmc.py >> audit/collect_epmc.log 2>&1
echo "COLLECT DONE $(date)" >> audit/collect_epmc.log

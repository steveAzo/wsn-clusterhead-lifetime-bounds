#!/bin/sh
# Runs E14 then E14b in the foreground of one shell (for Task Scheduler). Resumable.
cd /c/Users/User/Desktop/WSN_M/Paper5 || exit 1
echo "start $(date)" >> results/runner_run_e14.log
sh src/scoping/run_e14.sh >> results/runner_run_e14.log 2>&1
echo "e14 end $(date)" >> results/runner_run_e14.log
sh src/scoping/run_e14b.sh >> results/runner_run_e14.log 2>&1
echo "e14b end $(date)" >> results/runner_run_e14.log

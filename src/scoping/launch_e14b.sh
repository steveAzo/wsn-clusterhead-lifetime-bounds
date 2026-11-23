#!/bin/sh
cd /c/Users/User/Desktop/WSN_M/Paper5 || exit 1
nohup sh src/scoping/run_e14b.sh > results/runner_run_e14b.log 2>&1 < /dev/null &
echo "e14b launched $(date)" >> results/runner_launch.log

#!/bin/sh
# Detached start of the E14 runner (survives closing the editor when started through WMI, see STATUS doc).
cd /c/Users/User/Desktop/WSN_M/Paper5 || exit 1
nohup sh src/scoping/run_e14.sh > results/runner_run_e14.log 2>&1 < /dev/null &
echo "e14 launched $(date)" >> results/runner_launch.log

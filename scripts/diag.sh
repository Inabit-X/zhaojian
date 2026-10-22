#!/bin/bash
echo "NOW: $(date)"
echo "BOOT: $(uptime -s)"
echo "DOCKER_SVC:"
systemctl show docker -p NRestarts -p Restart -p ExecMainStartTimestamp
echo "FREE:"
free -m
echo "OOM_LINES:"
dmesg 2>/dev/null | grep -iE 'oom|killed process' | tail -n 5
echo "JOURNAL:"
journalctl -u docker --since '2 hours ago' --no-pager 2>/dev/null \
  | grep -E 'Stopped|Starting|Killed|oom|Failed|Scheduled restart' | tail -n 15

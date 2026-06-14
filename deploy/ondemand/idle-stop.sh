#!/usr/bin/env bash
#
# Stops THIS EC2 instance after a period of no real user activity.
# Run from cron every few minutes (see setup-instance.sh).
#
# Reads idle time from the backend's /activity endpoint (health checks are
# excluded server-side, so they don't keep the box awake).
#
# Requires: awscli on the instance + an IAM instance profile that allows
# ec2:StopInstances on this instance (see iam-instance-stop-policy.json).

set -euo pipefail

IDLE_LIMIT_SECONDS="${IDLE_LIMIT_SECONDS:-1200}"   # stop after 20 min idle
ACTIVITY_URL="${ACTIVITY_URL:-http://localhost:8000/activity}"

idle="$(curl -fsS -m 5 "$ACTIVITY_URL" \
  | python3 -c 'import sys,json; print(int(json.load(sys.stdin).get("idle_seconds", -1)))' \
  2>/dev/null || echo -1)"

if [ "$idle" -lt 0 ]; then
  echo "$(date -Is) no activity data yet (idle=$idle); skipping"
  exit 0
fi

if [ "$idle" -lt "$IDLE_LIMIT_SECONDS" ]; then
  echo "$(date -Is) active (idle ${idle}s < ${IDLE_LIMIT_SECONDS}s); staying up"
  exit 0
fi

# Idle long enough -> stop self. Resolve identity via IMDSv2.
TOKEN="$(curl -fsS -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 300")"
IID="$(curl -fsS -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/instance-id)"
REGION="$(curl -fsS -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/placement/region)"

echo "$(date -Is) idle ${idle}s >= ${IDLE_LIMIT_SECONDS}s; stopping $IID in $REGION"
aws ec2 stop-instances --region "$REGION" --instance-ids "$IID"

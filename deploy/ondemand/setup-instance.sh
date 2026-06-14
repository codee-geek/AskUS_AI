#!/usr/bin/env bash
#
# Run this ONCE on the EC2 instance (as the 'ubuntu' user) to enable:
#   - a swap file (lets a small / free-tier box survive ML memory spikes)
#   - awscli (needed for self-stop)
#   - immediate DuckDNS update on boot (so the domain points at the new IP fast)
#   - a cron job that auto-stops the instance when idle
#
# Prereq: attach an IAM instance profile that allows ec2:StopInstances first
# (see provision-aws.sh / README.md), otherwise the stop call will be denied.
#
# Usage:  bash setup-instance.sh
set -euo pipefail

SWAP_GB="${SWAP_GB:-3}"
IDLE_LIMIT_SECONDS="${IDLE_LIMIT_SECONDS:-1200}"
HOME_DIR="/home/ubuntu"
OND_DIR="$HOME_DIR/ondemand"

echo "== 1. swap (${SWAP_GB}G) =="
if ! sudo swapon --show | grep -q '/swapfile'; then
  sudo fallocate -l "${SWAP_GB}G" /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=$((SWAP_GB*1024))
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  echo "swap enabled"
else
  echo "swap already present"
fi

echo "== 2. awscli (official v2 bundle; apt 'awscli' is gone on Ubuntu 24.04) =="
if ! command -v aws >/dev/null 2>&1; then
  sudo apt-get update -y && sudo apt-get install -y unzip curl
  TMP="$(mktemp -d)"
  curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "$TMP/awscliv2.zip"
  unzip -q "$TMP/awscliv2.zip" -d "$TMP"
  sudo "$TMP/aws/install" --update
  rm -rf "$TMP"
fi
aws --version

echo "== 3. install idle-stop script =="
mkdir -p "$OND_DIR"
SRC_IDLE="$(cd "$(dirname "$0")" && pwd)/idle-stop.sh"
if [ "$SRC_IDLE" != "$OND_DIR/idle-stop.sh" ]; then
  cp "$SRC_IDLE" "$OND_DIR/idle-stop.sh"
fi
chmod +x "$OND_DIR/idle-stop.sh"

echo "== 4. cron: idle-stop every 5 min + DuckDNS on boot =="
TMP_CRON="$(mktemp)"
crontab -l 2>/dev/null | grep -v 'ondemand/idle-stop.sh' | grep -v '@reboot.*duckdns/update.sh' > "$TMP_CRON" || true
echo "@reboot sleep 15 && $HOME_DIR/duckdns/update.sh >/dev/null 2>&1" >> "$TMP_CRON"
echo "*/5 * * * * IDLE_LIMIT_SECONDS=$IDLE_LIMIT_SECONDS $OND_DIR/idle-stop.sh >> $OND_DIR/idle-stop.log 2>&1" >> "$TMP_CRON"
crontab "$TMP_CRON"
rm -f "$TMP_CRON"

echo "== done =="
echo "Verify: crontab -l ; free -h ; aws sts get-caller-identity"

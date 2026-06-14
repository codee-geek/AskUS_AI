# On-demand EC2 (wake-on-visit + auto-stop)

Run the AskUS AI instance **only while someone is using it**. When idle for a
while it stops itself; when a visitor opens the wake link it starts back up.

```
visitor ─▶ Wake Lambda (always on, ~free) ─▶ starts EC2 ─▶ "warming up" page ─▶ redirect ─▶ app
EC2 backend writes /activity  ─▶ cron idle-stop.sh ─▶ stops EC2 after N min idle
```

## Cost

- Lambda Function URL: effectively free at this traffic.
- EC2 compute: billed only while running. A `t3.small` used ~2 hrs/day ≈ **~$1/mo**.
- EBS disk: billed even while stopped (small, a few ₹/mo).

## Memory note (free tier)

The backend loads ML models that spike past 1 GiB during document ingestion.
On a 1 GiB free-tier `t3.micro` this can OOM-kill the backend, so
`setup-instance.sh` adds a **swap file** (default 3 GiB). A `t3.small` (2 GiB)
is more reliable; with auto-stop the cost difference is tiny.

## One-time setup

### 1. Provision AWS (laptop with AWS CLI, or AWS CloudShell in ap-south-1)

Edit the variables at the top of `provision-aws.sh` (`INSTANCE_ID`, `REGION`,
`APP_URL`), then:

```bash
bash deploy/ondemand/provision-aws.sh
```

It creates the IAM roles, attaches a self-stop instance profile to the box,
deploys the wake Lambda, and prints your **WAKE LINK** (the Function URL).
Bookmark/share that link — it is the entry point to the app.

### 2. Configure the instance (over SSH)

```bash
scp -i ~/Downloads/rag-key.pem -r deploy/ondemand ubuntu@askus-ai.duckdns.org:/home/ubuntu/
ssh -i ~/Downloads/rag-key.pem ubuntu@askus-ai.duckdns.org \
  'bash /home/ubuntu/ondemand/setup-instance.sh'
```

This adds swap, installs awscli, sets a `@reboot` DuckDNS update (so the domain
points at the new IP within seconds of starting), and installs the idle-stop
cron (every 5 min, stops after 20 min idle by default).

> The instance profile from step 1 must be attached first, or the self-stop
> call is denied. Verify on the box: `aws sts get-caller-identity`.

### 3. Test

```bash
# stop it and confirm the wake link brings it back
aws ec2 stop-instances --region ap-south-1 --instance-ids i-0e0a14879193c14cc
# open the WAKE LINK in a browser -> should boot and redirect to the app
```

## Tuning

- Idle timeout: set `IDLE_LIMIT_SECONDS` when running `setup-instance.sh`
  (e.g. `IDLE_LIMIT_SECONDS=600` for 10 min).
- Swap size: set `SWAP_GB` (e.g. `SWAP_GB=4`).
- Logs on the box: `~/ondemand/idle-stop.log`.

## How idleness is measured

The backend records the time of every non-health request and exposes it at
`/activity` (`idle_seconds`). Docker health checks hit `/health` and are
excluded, so they don't keep the box awake. `idle-stop.sh` polls `/activity`
and stops the instance once `idle_seconds` exceeds the limit.

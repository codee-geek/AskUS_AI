#!/usr/bin/env bash
#
# Provisions the AWS side of the on-demand setup. Run where AWS CLI is
# configured with admin-ish credentials (your laptop, or AWS CloudShell in the
# ap-south-1 region). Idempotent-ish: safe to re-run, ignores "already exists".
#
#   bash provision-aws.sh
#
# Creates:
#   - IAM role + instance profile that lets the EC2 box stop itself
#   - IAM role for the Lambda (describe + start the instance)
#   - the "wake" Lambda + a public Function URL (this is your wake link)
#
# After it prints the Function URL, run setup-instance.sh ON the instance.
set -euo pipefail

# ---- EDIT THESE -----------------------------------------------------------
INSTANCE_ID="i-0e0a14879193c14cc"
REGION="ap-south-1"
APP_URL="https://askus-ai.duckdns.org"
# ---------------------------------------------------------------------------

EC2_ROLE="askus-ec2-selfstop"
EC2_PROFILE="askus-ec2-selfstop"
LAMBDA_ROLE="askus-wake-lambda-role"
LAMBDA_NAME="askus-wake"
HERE="$(cd "$(dirname "$0")" && pwd)"

echo "== 1. EC2 self-stop role + instance profile =="
aws iam create-role --role-name "$EC2_ROLE" \
  --assume-role-policy-document "file://$HERE/trust-ec2.json" 2>/dev/null || true
aws iam put-role-policy --role-name "$EC2_ROLE" --policy-name selfstop \
  --policy-document "file://$HERE/iam-instance-stop-policy.json"
aws iam create-instance-profile --instance-profile-name "$EC2_PROFILE" 2>/dev/null || true
aws iam add-role-to-instance-profile --instance-profile-name "$EC2_PROFILE" \
  --role-name "$EC2_ROLE" 2>/dev/null || true
echo "attaching instance profile to $INSTANCE_ID (ok if already associated)…"
aws ec2 associate-iam-instance-profile --region "$REGION" \
  --instance-id "$INSTANCE_ID" \
  --iam-instance-profile "Name=$EC2_PROFILE" 2>/dev/null || true

echo "== 2. Lambda execution role =="
aws iam create-role --role-name "$LAMBDA_ROLE" \
  --assume-role-policy-document "file://$HERE/trust-lambda.json" 2>/dev/null || true
aws iam attach-role-policy --role-name "$LAMBDA_ROLE" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam put-role-policy --role-name "$LAMBDA_ROLE" --policy-name ec2start \
  --policy-document "file://$HERE/iam-lambda-start-policy.json"
LAMBDA_ROLE_ARN="$(aws iam get-role --role-name "$LAMBDA_ROLE" --query 'Role.Arn' --output text)"
echo "waiting 10s for IAM role propagation…"; sleep 10

echo "== 3. package + deploy Lambda =="
ZIP="$(mktemp -d)/wake.zip"
( cd "$HERE" && zip -j "$ZIP" wake_lambda.py >/dev/null )
if aws lambda get-function --function-name "$LAMBDA_NAME" --region "$REGION" >/dev/null 2>&1; then
  aws lambda update-function-code --function-name "$LAMBDA_NAME" --region "$REGION" \
    --zip-file "fileb://$ZIP" >/dev/null
else
  aws lambda create-function --function-name "$LAMBDA_NAME" --region "$REGION" \
    --runtime python3.12 --handler wake_lambda.handler --timeout 15 \
    --role "$LAMBDA_ROLE_ARN" --zip-file "fileb://$ZIP" >/dev/null
fi
aws lambda update-function-configuration --function-name "$LAMBDA_NAME" --region "$REGION" \
  --environment "Variables={INSTANCE_ID=$INSTANCE_ID,APP_URL=$APP_URL,TARGET_REGION=$REGION}" >/dev/null

echo "== 4. public Function URL =="
aws lambda create-function-url-config --function-name "$LAMBDA_NAME" --region "$REGION" \
  --auth-type NONE 2>/dev/null || true
aws lambda add-permission --function-name "$LAMBDA_NAME" --region "$REGION" \
  --statement-id public-url --action lambda:InvokeFunctionUrl \
  --principal "*" --function-url-auth-type NONE 2>/dev/null || true
URL="$(aws lambda get-function-url-config --function-name "$LAMBDA_NAME" --region "$REGION" \
  --query 'FunctionUrl' --output text)"

echo
echo "=========================================================="
echo " WAKE LINK (share/bookmark this):"
echo "   $URL"
echo "=========================================================="
echo "Next: run setup-instance.sh on the EC2 box, then stop it to test."

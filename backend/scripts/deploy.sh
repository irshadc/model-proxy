#!/usr/bin/env bash
# Build and deploy the Bedrock model proxy stack with SAM.
# Usage: ./scripts/deploy.sh --allowed-models global.openai.gpt-6-luna[,other.id]
#                            [--stack-name model-proxy] [--region ap-south-1] [--profile name]
set -euo pipefail

STACK_NAME="model-proxy"
REGION="ap-south-1"
ALLOWED_MODELS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --allowed-models) ALLOWED_MODELS="$2"; shift 2 ;;
    --stack-name) STACK_NAME="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --profile) export AWS_PROFILE="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$ALLOWED_MODELS" ]]; then
  echo "--allowed-models is required (comma-separated Bedrock model / inference profile IDs)" >&2
  exit 1
fi

cd "$(dirname "$0")/.."
chmod +x src/run.sh

sam validate --lint --region "$REGION"
sam build
sam deploy \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM \
  --no-fail-on-empty-changeset \
  --parameter-overrides "AllowedModelIds=$ALLOWED_MODELS"

aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" --region "$REGION" \
  --query "Stacks[0].Outputs[].[OutputKey,OutputValue]" --output table

echo "Next: ./scripts/get-api-key.sh --stack-name $STACK_NAME --region $REGION"

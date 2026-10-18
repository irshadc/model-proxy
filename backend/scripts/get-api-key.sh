#!/usr/bin/env bash
# Print the proxy base URL and API key as env exports for agent-sample/.env or your shell.
# Usage: ./scripts/get-api-key.sh [--stack-name model-proxy] [--region ap-south-1] [--profile name]
set -euo pipefail

STACK_NAME="model-proxy"
REGION="ap-south-1"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --stack-name) STACK_NAME="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --profile) export AWS_PROFILE="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

stack_output() {
  aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}

BASE_URL="$(stack_output ProxyBaseUrl)"
KEY_ID="$(stack_output ApiKeyId)"
KEY_VALUE="$(aws apigateway get-api-key --api-key "$KEY_ID" --include-value \
  --region "$REGION" --query value --output text)"

echo "PROXY_BASE_URL=$BASE_URL"
echo "PROXY_API_KEY=$KEY_VALUE"

#!/usr/bin/env bash
set -euo pipefail # Exit on error, unset variable, or pipe failure

NAMESPACE="trade"
SECRET_NAME="market-data-mssql-secrets"
SECRET_KEYS=(SA_PASSWORD DB_PASSWORD DB_NAME DB_USER)
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# Check for required commands
if ! command -v kubectl >/dev/null 2>&1; then
  echo "Error: kubectl is required to deploy MarketData." >&2
  exit 1
fi

umask 077 # Set a restrictive umask to ensure that temporary files are created with secure permissions
temp_dir="$(mktemp -d "${TMPDIR:-/tmp}/market-data-secrets.XXXXXX")"
trap 'rm -rf -- "$temp_dir"' EXIT # Clean up the temporary directory on exit

# Create the namespace if it doesn't exist
# Use --dry-run=client to avoid errors if the namespace already exists
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# Check if the secret already exists
secret_ref="$(kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" --ignore-not-found -o name)"

for key in "${SECRET_KEYS[@]}"; do
  encoded=""
  # If the secret exists, retrieve the existing value for the key
  if [[ -n "$secret_ref" ]]; then
    encoded="$(kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" -o "jsonpath={.data.${key}}")"
  fi

  # If the key exists in the secret, decode it and write it to the temporary file
  if [[ -n "$encoded" ]]; then
    if ! printf '%s' "$encoded" | base64 --decode > "$temp_dir/$key"; then
      echo "Error: Could not decode existing Secret key $key." >&2
      exit 1
    fi
    continue
  fi

  if [[ "$key" == "SA_PASSWORD" || "$key" == "DB_PASSWORD" ]]; then
    prompt="Enter value for $key (input hidden): "
    hidden=true
  else
    prompt="Enter value for $key: "
    hidden=false
  fi

  while :; do
    if [[ "$hidden" == true ]]; then
      IFS= read -r -s -p "$prompt" value
      printf '\n'
    else
      IFS= read -r -p "$prompt" value
    fi
    if [[ -n "$value" ]]; then
      break
    fi
    echo "A non-empty value is required for $key." >&2
  done

  printf '%s' "$value" > "$temp_dir/$key"
  unset value
done

kubectl create secret generic "$SECRET_NAME" \
  --namespace "$NAMESPACE" \
  --from-file="SA_PASSWORD=$temp_dir/SA_PASSWORD" \
  --from-file="DB_PASSWORD=$temp_dir/DB_PASSWORD" \
  --from-file="DB_NAME=$temp_dir/DB_NAME" \
  --from-file="DB_USER=$temp_dir/DB_USER" \
  --dry-run=client \
  -o yaml | kubectl apply -f -

kubectl apply -f "$SCRIPT_DIR/deploy.yaml"

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_MANIFEST="$SCRIPT_DIR/deploy.yaml"
DEPLOY_SCRIPT="$SCRIPT_DIR/deploy.sh"
IMAGE_NAME="localhost:5001/market-data"
IMAGE_TAG="$(date -u +%Y%m%dT%H%M%S%NZ)"
IMAGE="$IMAGE_NAME:$IMAGE_TAG"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "Error: kubectl is required to deploy MarketData." >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: docker is required to build and push the MarketData image." >&2
  exit 1
fi

if [[ ! -f "$DEPLOY_MANIFEST" || ! -x "$DEPLOY_SCRIPT" ]]; then
  echo "Error: deploy.yaml and executable deploy.sh must be beside this script." >&2
  exit 1
fi

image_line_count="$(grep -Ec '^[[:space:]]*image: localhost:5001/market-data:[^[:space:]]+$' "$DEPLOY_MANIFEST" || true)"
if [[ "$image_line_count" != 1 ]]; then
  echo "Error: expected exactly one MarketData image reference in $DEPLOY_MANIFEST." >&2
  exit 1
fi

docker_command=(docker)
if ! docker info >/dev/null 2>&1; then
  if ! command -v sudo >/dev/null 2>&1 || ! sudo docker info >/dev/null; then
    echo "Error: Docker is unavailable. Ensure the daemon is running and accessible." >&2
    exit 1
  fi
  docker_command=(sudo docker)
fi

"${docker_command[@]}" build -t "$IMAGE" "$SCRIPT_DIR"
"${docker_command[@]}" push "$IMAGE"

temp_manifest="$(mktemp "$DEPLOY_MANIFEST.XXXXXX")"
trap 'rm -f -- "$temp_manifest"' EXIT
sed -E "s#^([[:space:]]*image: )localhost:5001/market-data:[^[:space:]]+#\\1$IMAGE#" \
  "$DEPLOY_MANIFEST" > "$temp_manifest"
chmod --reference="$DEPLOY_MANIFEST" "$temp_manifest"
mv -- "$temp_manifest" "$DEPLOY_MANIFEST"
trap - EXIT

echo "Updated $DEPLOY_MANIFEST to use $IMAGE"
"$DEPLOY_SCRIPT"

if old_images="$("${docker_command[@]}" image ls "$IMAGE_NAME" --format '{{.Repository}}:{{.Tag}}')"; then
  while IFS= read -r old_image; do
    [[ -z "$old_image" || "$old_image" == "$IMAGE" ]] && continue
    if ! "${docker_command[@]}" image rm "$old_image"; then
      echo "Warning: Could not remove old local image tag $old_image." >&2
    fi
  done <<< "$old_images"
else
  echo "Warning: Could not list old local MarketData image tags for cleanup." >&2
fi

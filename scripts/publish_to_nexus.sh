#!/usr/bin/env bash
set -euo pipefail

# publish_to_nexus.sh
# Publishes the packaged zip artifact to a Nexus raw repository.
#
# Usage:
#   ./scripts/publish_to_nexus.sh <artifact_path>
#
# Environment variables:
#   NEXUS_URL       - Base URL of Nexus (e.g., https://nexus.internal.example.com)
#   NEXUS_USER      - Nexus username
#   NEXUS_PASS      - Nexus password
#   NEXUS_REPO      - Repository name (default: model-artifacts)
#   GROUP_ID        - Group path (default: com/org/systems)

ARTIFACT_PATH="${1:?Usage: publish_to_nexus.sh <artifact_path>}"

NEXUS_URL="${NEXUS_URL:?NEXUS_URL environment variable required}"
NEXUS_USER="${NEXUS_USER:?NEXUS_USER environment variable required}"
NEXUS_PASS="${NEXUS_PASS:?NEXUS_PASS environment variable required}"
NEXUS_REPO="${NEXUS_REPO:-model-artifacts}"
GROUP_ID="${GROUP_ID:-com/org/systems}"

if [ ! -f "$ARTIFACT_PATH" ]; then
    echo "ERROR: Artifact not found: $ARTIFACT_PATH"
    exit 1
fi

ARTIFACT_NAME=$(basename "$ARTIFACT_PATH")

# Extract version from artifact filename (e.g., cameo-model-artifacts-1.2.0-build.47.zip)
VERSION=$(echo "$ARTIFACT_NAME" | grep -oP '\d+\.\d+\.\d+')
if [ -z "$VERSION" ]; then
    echo "ERROR: Could not extract version from artifact name: $ARTIFACT_NAME"
    exit 1
fi

UPLOAD_URL="${NEXUS_URL}/repository/${NEXUS_REPO}/${GROUP_ID}/cameo-model-artifacts/${VERSION}/${ARTIFACT_NAME}"

echo "Publishing to Nexus..."
echo "  Artifact: $ARTIFACT_NAME"
echo "  Version:  $VERSION"
echo "  URL:      $UPLOAD_URL"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -u "${NEXUS_USER}:${NEXUS_PASS}" \
    -X PUT \
    -T "$ARTIFACT_PATH" \
    "$UPLOAD_URL")

if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "200" ]; then
    echo "SUCCESS: Artifact published (HTTP $HTTP_CODE)"
elif [ "$HTTP_CODE" = "400" ]; then
    echo "ERROR: Version $VERSION may already exist in Nexus. Bump the VERSION file. (HTTP $HTTP_CODE)"
    exit 1
else
    echo "ERROR: Nexus upload failed with HTTP $HTTP_CODE"
    exit 1
fi

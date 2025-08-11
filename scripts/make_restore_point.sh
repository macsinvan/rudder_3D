#!/usr/bin/env bash
# scripts/make_restore_point.sh
set -euo pipefail

usage() {
  echo "Usage: $(basename "$0") -m \"message\" [-p]"
  echo "  -m  Commit/tag message (required)"
  echo "  -p  Push branch and tag to origin"
}

PUSH=false
COMMIT_MSG=""
while getopts ":m:ph" opt; do
  case $opt in
    m) COMMIT_MSG="$OPTARG" ;;
    p) PUSH=true ;;
    h) usage; exit 0 ;;
    \?) echo "Invalid option: -$OPTARG"; usage; exit 2 ;;
    :)  echo "Option -$OPTARG requires an argument."; usage; exit 2 ;;
  esac
done

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[[ -n "$REPO_ROOT" ]] || { echo "Not inside a git repo"; exit 1; }
cd "$REPO_ROOT"

[[ -n "$COMMIT_MSG" ]] || { echo "Message required (-m)"; usage; exit 2; }

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
STAMP_TAG="$(date +%Y%m%d-%H%M%S)"
TAG_NAME="restore/${STAMP_TAG}"

echo "▶ Restore on ${BRANCH}"
git add -A
if git diff --cached --quiet; then
  echo "ℹ No staged changes; tagging HEAD."
else
  git commit -m "Restore point: ${COMMIT_MSG}"
fi
git tag -a "${TAG_NAME}" -m "Restore: ${COMMIT_MSG}"

echo "✓ Created tag ${TAG_NAME} at $(git rev-parse --short HEAD)"
if $PUSH; then
  git push origin "${BRANCH}"
  git push origin "${TAG_NAME}"
  echo "✓ Pushed"
fi

#!/bin/bash
# Restore from a "restore/YYYY-MM-DD_HHMMSS" tag.
# Defaults to creating a new branch at the tag (safe). Use --hard to reset current branch.

set -euo pipefail

list_tags() {
  git fetch --tags >/dev/null 2>&1 || true
  git for-each-ref --sort=-creatordate \
    --format="%(creatordate:short)  %(refname:short)  %(objectname:short)  %(subject)" refs/tags/restore/
}

usage() {
  echo "Usage:"
  echo "  $0 <restore_tag> [--branch <new_branch>] [--hard]"
  echo
  echo "Examples:"
  echo "  $0 restore/2025-08-10_211524                     # create branch backup/2025-08-10_211524 and checkout"
  echo "  $0 restore/2025-08-10_211524 --branch hotfix/wedge # create and checkout custom branch"
  echo "  $0 restore/2025-08-10_211524 --hard               # HARD reset current branch to the tag"
  echo
  echo "Available restore points (newest first):"
  list_tags
}

TAG="${1:-}"
BRANCH=""
HARD=0

# Parse args
shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch)
      BRANCH="${2:-}"; shift 2 || true;;
    --hard)
      HARD=1; shift;;
    *)
      echo "Unknown option: $1"; usage; exit 1;;
  esac
done

if [[ -z "$TAG" ]]; then
  usage; exit 1
fi

# Ensure tag exists locally
git fetch --tags
if ! git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
  echo "❌ Tag not found: $TAG"; echo; usage; exit 1
fi

TAG_SHA=$(git rev-parse "$TAG")
echo "➡️  Restore target: $TAG ($TAG_SHA)"

if [[ $HARD -eq 1 ]]; then
  # Destructive: reset current branch to tag
  echo "⚠️  HARD resetting current branch to $TAG ..."
  git reset --hard "$TAG"
  echo "✅ Reset complete. Current HEAD: $(git rev-parse --short HEAD)"
else
  # Safe: create and checkout a new branch at the tag
  if [[ -z "$BRANCH" ]]; then
    BRANCH="backup/${TAG#restore/}"
  fi
  echo "🛟 Creating branch '$BRANCH' at $TAG ..."
  git checkout -b "$BRANCH" "$TAG"
  git push -u origin "$BRANCH"
  echo "✅ Checked out '$BRANCH' at $TAG ($TAG_SHA)"
fi

echo "📌 Done."

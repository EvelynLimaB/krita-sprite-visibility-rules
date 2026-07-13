#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
OWNER="${GITHUB_OWNER:-EvelynLimaB}"
REPO="${GITHUB_REPO:-krita-sprite-visibility-rules}"
VISIBILITY="${GITHUB_VISIBILITY:-public}"
PYTHON="${PYTHON:-python3}"

command -v "$PYTHON" >/dev/null 2>&1 || {
    echo "Python 3 is required. Install python3 or set PYTHON=/path/to/python3." >&2
    exit 1
}
command -v gh >/dev/null 2>&1 || {
    echo "GitHub CLI is required. Install it, then run: gh auth login" >&2
    exit 1
}
gh auth status >/dev/null

VERSION="$(PLUGIN_ROOT="$ROOT" "$PYTHON" -c 'import os, sys; sys.path.insert(0, os.environ["PLUGIN_ROOT"]); from sprite_visibility_rules.version import __version__; print(__version__)')"
TAG="v${VERSION}"

cd "$ROOT"
"$PYTHON" scripts/verify_release.py

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    LOGIN="$(gh api user --jq .login)"
    NAME="$(gh api user --jq '.name // .login')"
    git init -b main
    git config user.name "$NAME"
    git config user.email "$LOGIN@users.noreply.github.com"
    git add .
    git commit -m "Release Sprite Visibility Rules ${TAG}"
fi

if [[ -n "$(git status --porcelain)" ]]; then
    echo "The repository has uncommitted changes; review them before publishing." >&2
    git status --short >&2
    exit 1
fi

if ! git rev-parse "$TAG" >/dev/null 2>&1; then
    git tag -a "$TAG" -m "Sprite Visibility Rules ${VERSION}"
fi

if gh repo view "$OWNER/$REPO" >/dev/null 2>&1; then
    if ! git remote get-url origin >/dev/null 2>&1; then
        git remote add origin "https://github.com/$OWNER/$REPO.git"
    fi
    git push -u origin main
else
    gh repo create "$OWNER/$REPO" \
        "--$VISIBILITY" \
        --source=. \
        --remote=origin \
        --push \
        --description "Krita docker for inverse, exclusive, and linked layer visibility rules in sprite and game-art files."
fi

git push origin "$TAG"

if gh release view "$TAG" --repo "$OWNER/$REPO" >/dev/null 2>&1; then
    echo "Release ${TAG} already exists; repository push completed."
else
    gh release create "$TAG" \
        "dist/sprite_visibility_rules-${VERSION}.zip" \
        dist/SHA256SUMS \
        --repo "$OWNER/$REPO" \
        --title "Sprite Visibility Rules ${VERSION}" \
        --notes-file RELEASE_NOTES.md
fi

echo "Published: https://github.com/$OWNER/$REPO"

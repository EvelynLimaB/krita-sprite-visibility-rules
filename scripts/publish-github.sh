#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
OWNER="${GITHUB_OWNER:-EvelynLimaB}"
REPO="${GITHUB_REPO:-krita-sprite-visibility-rules}"
VISIBILITY="${GITHUB_VISIBILITY:-public}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

command -v gh >/dev/null 2>&1 || {
    echo "GitHub CLI is required. Install it, then run: gh auth login" >&2
    exit 1
}
gh auth status >/dev/null
command -v "$PYTHON_BIN" >/dev/null 2>&1 || {
    echo "Python 3 is required. On Linux Mint, run: sudo apt install python3" >&2
    exit 1
}

cd "$ROOT"
"$PYTHON_BIN" scripts/verify_release.py

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    LOGIN="$(gh api user --jq .login)"
    NAME="$(gh api user --jq '.name // .login')"
    git init -b main
    git config user.name "$NAME"
    git config user.email "$LOGIN@users.noreply.github.com"
    git add .
    git commit -m "Release Sprite Visibility Rules v1.0.0"
    git tag -a v1.0.0 -m "Sprite Visibility Rules v1.0.0"
fi

if [[ -n "$(git status --porcelain)" ]]; then
    echo "The repository has uncommitted changes; review them before publishing." >&2
    git status --short >&2
    exit 1
fi

if ! git rev-parse v1.0.0 >/dev/null 2>&1; then
    git tag -a v1.0.0 -m "Sprite Visibility Rules v1.0.0"
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

git push origin v1.0.0

if gh release view v1.0.0 --repo "$OWNER/$REPO" >/dev/null 2>&1; then
    echo "Release v1.0.0 already exists; repository push completed."
else
    gh release create v1.0.0 \
        dist/sprite_visibility_rules-1.0.0.zip \
        dist/SHA256SUMS \
        --repo "$OWNER/$REPO" \
        --title "Sprite Visibility Rules 1.0.0" \
        --notes-file RELEASE_NOTES.md
fi

echo "Published: https://github.com/$OWNER/$REPO"

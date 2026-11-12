#!/usr/bin/env bash
# Resolve which upstream Meshtastic release to build, and its 40-hex commit.
#
# Order of precedence for the tag:
#   1. $INPUT_TAG (workflow_dispatch input), if set
#   2. UPSTREAM_TAG in ndi_1w/upstream.lock
#   3. when that is empty or LATEST_STABLE: the latest non-prerelease GitHub release
# The commit comes from git ls-remote. If the lock pins both tag and commit and the tag now
# points somewhere else, this fails. Raw URLs cannot show a commit hash; git can.
#
# Needs: git, gh (with GH_TOKEN) only for LATEST_STABLE. Writes tag= and commit= to $GITHUB_OUTPUT
# when it is set, and always prints them.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
lock="$repo_root/ndi_1w/upstream.lock"

lock_get() {
    grep -E "^$1=" "$lock" | head -1 | cut -d= -f2-
}

upstream_repo="$(lock_get UPSTREAM_REPO)"
lock_tag="$(lock_get UPSTREAM_TAG)"
lock_commit="$(lock_get UPSTREAM_COMMIT)"
slug="${upstream_repo#https://github.com/}"

want_tag="${INPUT_TAG:-}"
if [ -z "$want_tag" ]; then
    want_tag="$lock_tag"
fi
if [ -z "$want_tag" ] || [ "$want_tag" = "LATEST_STABLE" ]; then
    want_tag="$(gh api "repos/${slug}/releases/latest" --jq .tag_name)"
fi
if [ -z "$want_tag" ]; then
    echo "::error::could not determine an upstream tag"
    exit 1
fi

commit="$(git ls-remote "$upstream_repo" "refs/tags/${want_tag}^{}" | cut -f1)"
if [ -z "$commit" ]; then
    commit="$(git ls-remote "$upstream_repo" "refs/tags/${want_tag}" | cut -f1)"
fi
if [ -z "$commit" ]; then
    echo "::error::tag ${want_tag} not found in ${upstream_repo}"
    exit 1
fi

if [ "$want_tag" = "$lock_tag" ] && [ -n "$lock_commit" ] && [ "$commit" != "$lock_commit" ]; then
    echo "::error::tag ${want_tag} now points to ${commit}, but upstream.lock pins ${lock_commit}"
    exit 1
fi

echo "upstream tag:    ${want_tag}"
echo "upstream commit: ${commit}"
if [ -n "${GITHUB_OUTPUT:-}" ]; then
    {
        echo "tag=${want_tag}"
        echo "commit=${commit}"
    } >> "$GITHUB_OUTPUT"
fi

#!/usr/bin/env bash
# publish_hash.sh <repo> [tag]
# Publish an Emerging-Patterns repo's release tag to the Bend hub by hash from
# a fresh clone, with the ez and bend on PATH (EZ overrides ez, ORG the org). Refuses when
# ez.toml's [package] sets publish-as or version. Prints "<repo> <tag> 0x<hash>".
set -euo pipefail
repo=$1; org=${ORG:-Emerging-Patterns}; tag=${2:-}
ez=${EZ:-ez}
[ -n "$tag" ] || tag=$(gh api "repos/$org/$repo/releases/latest" --jq .tag_name)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
git clone -q --depth 1 --branch "$tag" "https://github.com/$org/$repo" "$work/$repo" 2>/dev/null
cd "$work/$repo"
if sed -n '/^\[package\]/,/^\[/p' ez.toml | grep -qE '^(publish-as|version)[[:space:]]*='; then
  echo "$repo $tag: ez.toml [package] sets publish-as/version; refusing (named publish)" >&2
  exit 2
fi
# the hub serves a package's own manifest at <hash>/manifest, and refuses a
# package with a top-level manifest/ directory (EISDIR while staging)
entry=$(sed -n '/^\[package\]/,/^\[/{s/^entry *= *"\(.*\)"/\1/p}' ez.toml | head -1)
case "${entry:-main.bend}" in
  manifest/*) echo "$repo $tag: the entry is under manifest/, a name the hub reserves; rename the directory" >&2; exit 3 ;;
esac
if [ -f ez.lock.toml ] && grep -qE '^\[packages[.\]]' ez.lock.toml; then
  mkdir -p .ez/lib
  BEND_LIB=$PWD/.ez/lib "$ez" fetch >/dev/null
fi
out=$(BEND_LIB=$PWD/.ez/lib "$ez" publish 2>"$work/err") || {
  echo "$repo $tag: ez publish failed" >&2; tail -5 "$work/err" >&2; exit 1; }
hash=$(printf '%s\n' "$out" | grep -oxE '0x[0-9a-f]{32}' | head -1)
code=$(curl -s -o /dev/null -w '%{http_code}' "https://hub.bend-lang.com/$hash/manifest")
echo "$repo $tag $hash hub=$code"

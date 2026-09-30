#!/usr/bin/env bash
# publish_hash.sh <repo> [tag] [hub-name]
# Publish an Emerging-Patterns repo's release tag to the Bend hub from a fresh
# clone. With a hub name, bend publishes it as <name>@<X.Y.Z>.0 (the hub's
# four-part version) in the same step; without one, by hash only. BEND is the
# bend to publish with (default `bend`; use the release the fleet targets), EZ
# the ez used only to fetch locked deps, ORG the org.
# Refuses, before anything is uploaded:
#   - ez.toml [package] setting publish-as/version (name the release here instead);
#   - an entry under manifest/ (the hub reserves <hash>/manifest);
#   - no LICENSE beside the entry: bend adds a LICENSE only from directories that
#     hold a walked file, and a package with none is published under the hub
#     terms' default license (MIT-0), permanently.
# Prints what the hub will show as the description (the first line of the
# first walked file by path, LICENSE aside) and "<repo> <tag> 0x<hash> hub=<code>".
set -euo pipefail
repo=$1; org=${ORG:-Emerging-Patterns}; tag=${2:-}; name=${3:-}
ez=${EZ:-ez}; bend=${BEND:-bend}
[ -n "$tag" ] || tag=$(gh api "repos/$org/$repo/releases/latest" --jq .tag_name)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
git clone -q --depth 1 --branch "$tag" "https://github.com/$org/$repo" "$work/$repo" 2>/dev/null
cd "$work/$repo"
if sed -n '/^\[package\]/,/^\[/p' ez.toml | grep -qE '^(publish-as|version)[[:space:]]*='; then
  echo "$repo $tag: ez.toml [package] sets publish-as/version; pass the hub name here instead" >&2
  exit 2
fi
entry=$(sed -n '/^\[package\]/,/^\[/{s/^entry *= *"\(.*\)"/\1/p}' ez.toml | head -1); entry=${entry:-main.bend}
case "$entry" in
  manifest/*) echo "$repo $tag: the entry is under manifest/, a name the hub reserves; rename the directory" >&2; exit 3 ;;
esac
[ -f "$(dirname "$entry")/LICENSE" ] || {
  echo "$repo $tag: no LICENSE beside $entry; bend would publish the package as MIT-0. Move the entry to the package root (ez init's layout) or put the LICENSE beside it." >&2; exit 4; }
first=$(sed -n 1p "$entry")
echo "entry's first line (the hub description when $entry sorts first): $first" >&2
if [ -f ez.lock.toml ] && grep -qE '^\[packages[.\]]' ez.lock.toml; then
  mkdir -p .ez/lib
  BEND_LIB=$PWD/.ez/lib "$ez" fetch >/dev/null
  export BEND_LIB=$PWD/.ez/lib
fi
cd "$(dirname "$entry")"
if [ -n "$name" ]; then out=$("$bend" "$(basename "$entry")" --publish "$name@${tag#v}.0" 2>"$work/err") || { tail -5 "$work/err" >&2; exit 1; }
else out=$("$bend" "$(basename "$entry")" --publish 2>"$work/err") || { tail -5 "$work/err" >&2; exit 1; }; fi
grep -i 'warning' "$work/err" >&2 || true
hash=$(printf '%s\n' "$out" | grep -oxE '0x[0-9a-f]{32}' | head -1)
code=$(curl -s -o /dev/null -w '%{http_code}' "https://hub.bend-lang.com/$hash/manifest")
named=$(printf '%s\n' "$out" | sed -n 's/^published //p')
echo "$repo $tag $hash hub=$code${named:+ named=$named}"

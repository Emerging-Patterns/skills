#!/usr/bin/env bash
# readme_hub_check.sh <README.md> [expected-0x-hash]
# Check a README the way a plain Bend user meets it: no ez, no BEND_LIB, an
# empty HOME, only `bend` on PATH.
#   1. every `import 0x<hash>/...` names a hash the hub serves, and, when an
#      expected hash is given, the package's own imports use exactly it;
#   2. every fenced block that holds an `import 0x` line is written to its own
#      file and run through `bend <file> --check-only`, which fetches from the
#      hub into the empty HOME. A block with no `def main` gets a trivial one,
#      only for the check.
# Exit status is the number of failures. Snippets that need a network or IO at
# runtime still check, since nothing runs.
set -uo pipefail
readme=$1; want=${2:-}
bend=$(command -v bend) || { echo "bend not on PATH" >&2; exit 99; }
bindir=$(dirname "$(readlink -f "$bend")")
work=$(mktemp -d); trap 'rm -rf "$work"' EXIT
fail=0

for h in $(grep -oE 'import 0x[0-9a-f]{32}' "$readme" | awk '{print $2}' | sort -u); do
  code=$(curl -s -o /dev/null -w '%{http_code}' "https://hub.bend-lang.com/$h/manifest")
  if [ "$code" != 200 ]; then echo "FAIL hub: $h -> $code"; fail=$((fail+1)); else echo "ok   hub: $h"; fi
  if [ -n "$want" ] && [ "$h" != "$want" ]; then echo "note: README imports $h (not the package's $want) - a dependency, or stale?"; fi
done

python3 - "$readme" "$work" <<'EOF'
import re, sys, pathlib
text = pathlib.Path(sys.argv[1]).read_text()
out = pathlib.Path(sys.argv[2])
blocks = re.findall(r"```[^\n]*\n(.*?)```", text, re.S)
n = 0
for b in blocks:
    if not re.search(r"^import 0x[0-9a-f]{32}/", b, re.M):
        continue
    n += 1
    if not re.search(r"^def main\(", b, re.M):
        b += "\n\ndef main() -> String:\n  \"ok\"\n"
    (out / f"snippet{n}.bend").write_text(b)
print(n)
EOF

for f in "$work"/snippet*.bend; do
  [ -e "$f" ] || { echo "note: no fenced block imports a hub package"; break; }
  home=$(mktemp -d -p "$work")
  res=$(cd "$work" && env -i PATH="$bindir:/usr/bin:/bin" HOME="$home" timeout 900 "$bindir/bend" "$f" --check-only 2>&1)
  if printf '%s' "$res" | grep -q '^All terms check'; then
    echo "ok   $(basename "$f")"
  else
    echo "FAIL $(basename "$f"):"; printf '%s\n' "$res" | head -8 | sed 's/^/     /'
    echo "     --- snippet ---"; sed 's/^/     /' "$f" | head -20
    fail=$((fail+1))
  fi
done
exit $fail

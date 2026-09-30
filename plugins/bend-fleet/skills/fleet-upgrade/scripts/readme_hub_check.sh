#!/usr/bin/env bash
# readme_hub_check.sh <README.md> [expected-0x-hash]
# (imports may name a package by hash or as <name>@<version>, which the hub
# resolves at /name/<name>@<version>)
# Check a README the way a plain Bend user meets it: no ez, no BEND_LIB, an
# empty HOME, only `bend` on PATH.
#   1. every `import 0x<hash>/...` names a hash the hub serves, and, when an
#      expected hash is given, the package's own imports use exactly it;
#   2. every fenced block that holds an `import 0x` or `import <name>@` line is
#      written to its own file and run through `bend <file> --check-only`, which
#      fetches from the hub into the empty HOME. A block with no `def main` gets
#      a trivial one, only for the check. It passes on `ALL PROOFS CHECK`, or on
#      `SOME PROOFS FAIL` whose only error is that defs rely on unsafe or
#      foreign code: since bend 2.0.32 that is the verdict on any program that
#      reaches an effect (a process, a socket, a file), and it still type-checks.
# Exit status is the number of failures. Snippets that need a network or IO at
# runtime still check, since nothing runs.
set -uo pipefail
readme=$1; want=${2:-}
bend=$(command -v bend) || { echo "bend not on PATH" >&2; exit 99; }
bindir=$(dirname "$(readlink -f "$bend")")
work=$(mktemp -d); trap 'rm -rf "$work"' EXIT
fail=0

for h in $(grep -oE 'import (0x[0-9a-f]{32}|[a-z][a-z0-9-]*@[0-9.]+)/' "$readme" | awk '{print $2}' | tr -d / | sort -u); do
  x=$h
  case $h in
    *@*) x=$(curl -s "https://hub.bend-lang.com/name/$h" | tr -d '[:space:]')
         printf '%s' "$x" | grep -qxE '0x[0-9a-f]{32}' || { echo "FAIL hub: $h names no hash"; fail=$((fail+1)); continue; } ;;
  esac
  code=$(curl -s -o /dev/null -w '%{http_code}' "https://hub.bend-lang.com/$x/manifest")
  if [ "$code" != 200 ]; then echo "FAIL hub: $h -> $code"; fail=$((fail+1)); else echo "ok   hub: $h${x:+ = $x}"; fi
  if [ -n "$want" ] && [ "$x" != "$want" ]; then echo "note: README imports $h (not the package's $want) - a dependency, or stale?"; fi
done

python3 - "$readme" "$work" <<'EOF'
import re, sys, pathlib
text = pathlib.Path(sys.argv[1]).read_text()
out = pathlib.Path(sys.argv[2])
blocks = re.findall(r"```[^\n]*\n(.*?)```", text, re.S)
n = 0
for b in blocks:
    if not re.search(r"^import (0x[0-9a-f]{32}|[a-z][a-z0-9-]*@[0-9.]+)/", b, re.M):
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
  first=$(printf '%s\n' "$res" | sed -n 1p); second=$(printf '%s\n' "$res" | sed -n 2p)
  if [ "$first" = "ALL PROOFS CHECK" ]; then
    echo "ok   $(basename "$f")"
  elif [ "$first" = "SOME PROOFS FAIL" ] && printf '%s' "$second" | grep -qE '^Error: [0-9]+ defs? rel(y|ies) on unsafe or foreign code'; then
    echo "ok   $(basename "$f") (reaches foreign code)"
  else
    echo "FAIL $(basename "$f"):"; printf '%s\n' "$res" | head -8 | sed 's/^/     /'
    echo "     --- snippet ---"; sed 's/^/     /' "$f" | head -20
    fail=$((fail+1))
  fi
done
exit $fail

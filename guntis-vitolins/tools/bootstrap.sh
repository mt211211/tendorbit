#!/usr/bin/env bash
# Reproduce the lead-1 sweep environment in a fresh container, then run one slice.
#
#   bash bootstrap.sh <work-dir> <slice-index>/<slice-count>
#
# Slices are disjoint (unit index % N == I), so several containers can share the
# sweep and their per-slice TSVs merge by unit index with no double-counting and
# no gaps.
set -euo pipefail

ROOT="${1:?usage: bootstrap.sh <work-dir> <I>/<N>}"
SLICE="${2:?usage: bootstrap.sh <work-dir> <I>/<N>}"
OCP_COMMIT=01517c5
WORDLIST_MD5=f23506956964fa69c98fa3fb5c8823b5
TOOLS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$ROOT"
cd "$ROOT"

# the puzzle folder, pinned -- a moving HEAD would change the enumerated space
if [ ! -d ocp/.git ]; then
  git clone --quiet https://github.com/floflo777/open-crypto-puzzles.git ocp
fi
git -C ocp fetch --quiet origin
git -C ocp checkout --quiet "$OCP_COMMIT"
echo "ocp pinned at $(git -C ocp rev-parse --short HEAD)"

cp "$TOOLS"/{gv_lead1.py,gv_multipath.py,moss_oracle.py,pathcross.py} "$ROOT"/
cp "$TOOLS"/bip39_english.txt "$ROOT"/
# checkpoints of units already finished elsewhere; the runner skips every unit
# logged by ANY gv_lead1*.tsv it finds, so this prevents redoing them
cp "$TOOLS"/checkpoints/gv_lead1*.tsv "$ROOT"/ 2>/dev/null || true

got=$(md5sum bip39_english.txt | cut -d' ' -f1)
[ "$got" = "$WORDLIST_MD5" ] || { echo "wordlist md5 $got != $WORDLIST_MD5"; exit 1; }
echo "wordlist verified"

export GV_ROOT="$ROOT"
python3 gv_lead1.py --selftest
echo "--- selftest passed, starting slice $SLICE ---"
exec python3 -u gv_lead1.py --slice "$SLICE"

#!/usr/bin/env bash
# Flow's OWN host wiring for `previewBackend.serve` — project-dev infra, NOT shipped.
#
# It exists because the adapter deliberately refuses a template containing a shell
# operator (`&`, `>`, `;` …): one rendered command would silently become two, and
# nothing downstream would report it. Backgrounding a static server needs exactly
# those operators, so the backgrounding lives HERE, in a script the template calls —
# which is what `preview_backend.validate` tells an author to do.
#
# Idempotent by design: /flow:prototype and /flow:ship may both reach for a preview in
# one session, and the host gives a workspace ONE preview URL, so re-serving the same
# directory on the same port must be a no-op rather than a second server.
set -euo pipefail
DIR="${1:?usage: flow-preview-serve.sh <dir> <port>}"
PORT="${2:?usage: flow-preview-serve.sh <dir> <port>}"
mkdir -p "$DIR"

listening() {
  python3 - "$1" <<'PY'
import socket, sys
try:
    with socket.create_connection(("127.0.0.1", int(sys.argv[1])), timeout=1):
        sys.exit(0)
except OSError:
    sys.exit(1)
PY
}

# A sentinel naming the directory we intend to serve. The idempotency check below
# compares the SERVED ROOT, not merely "is something listening" — because gating on
# the port alone treats ANY pre-existing listener as ours and publishes its root.
# That is not hypothetical here: the port default and `.claude/launch.json` both used
# 8899, so flow's own launch recipe (rooted at `.flow`, the scratch directory) would
# have been adopted and published, bypassing the staged snapshot entirely.
ROOT_MARK=".flow-preview-root"
# A HASH of the directory, not the directory itself. This file is inside the served
# root, so whatever it holds is fetchable by anyone who can reach the preview URL;
# the hash answers "is this our root?" exactly as well and discloses nothing.
# python3, not sha256sum: the latter is GNU-only, and under `set -e` a macOS dev would
# get an opaque non-zero exit here rather than a served preview. The script already
# shells to python3 for the liveness probe, so there is no new dependency.
ROOT_ID=$(printf '%s' "${DIR%/}" | python3 -c 'import hashlib,sys;print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest()[:32])')
printf '%s\n' "$ROOT_ID" > "${DIR%/}/${ROOT_MARK}"

serving_root() {
  # Fetch the sentinel from whatever is listening. Empty on any failure, which the
  # caller treats as "not ours".
  python3 - "$1" "$2" <<'PY'
import sys, urllib.request
try:
    with urllib.request.urlopen("http://127.0.0.1:%s/%s" % (sys.argv[1], sys.argv[2]),
                                timeout=2) as r:
        sys.stdout.write(r.read().decode("utf-8", "replace").strip())
except Exception:
    pass
PY
}

if listening "$PORT"; then
  FOUND=$(serving_root "$PORT" "$ROOT_MARK")
  if [ "$FOUND" = "$ROOT_ID" ]; then
    echo "[flow-preview-serve] already serving ${DIR} on ${PORT}; reusing it"
    exit 0
  fi
  echo "[flow-preview-serve] ⚠️ port ${PORT} is already in use by something serving" >&2
  echo "   a different root — NOT ${DIR%/}. Refusing to adopt it: publishing" >&2
  echo "   another process's root would hand a reviewer a different directory than the" >&2
  echo "   one staged for them, and on this repo that root is the scratch dir." >&2
  echo "   Fix: stop that server, or set previewBackend.port to a free port." >&2
  exit 1
fi

# OUTSIDE the served root, deliberately: an access log inside it is itself fetchable,
# and it records every request path.
LOG="$(dirname "${DIR%/}")/.preview-server.log"
nohup python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$DIR" > "$LOG" 2>&1 &
# Wait for it rather than assuming: publishing a port nothing listens on produces a
# live-looking dead link, the failure this whole feature exists to remove.
for _ in $(seq 1 25); do
  if listening "$PORT"; then
    echo "[flow-preview-serve] listening on ${PORT} serving ${DIR}"
    exit 0
  fi
  sleep 0.2
done
echo "[flow-preview-serve] ⚠️ nothing came up on ${PORT} after 5s; see ${LOG}" >&2
exit 1

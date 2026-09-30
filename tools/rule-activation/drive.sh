#!/bin/bash
FOLLOWUP="${FOLLOWUP:-/tmp/rig/prompts/followup.txt}"
# drive2.sh <arm> <workspaceId> <model> <tag> <cell>...   cell = scenario:run
arm="$1"; ws="$2"; model="$3"; tag="$4"; shift 4
out="/tmp/rig/results-$arm-$tag.tsv"; : > "$out"
sid_of() { python3 -c "
import json,sys
try:
  d=json.load(sys.stdin); w=d.get('data',d); print(w.get('id') or w.get('sessionId') or 'ERR')
except Exception: print('ERR')"; }
wait_idle() {
  for i in $(seq 1 90); do
    s=$(conductor --json session status "$1" 2>/dev/null | python3 -c "
import json,sys
try:
  d=json.load(sys.stdin); w=d.get('data',d); print(w.get('status') or w.get('state') or '?')
except Exception: print('?')")
    [ "$s" = "idle" ] && return 0
    sleep 5
  done
  return 1
}
# Did this session hit the account limit? A limited session is TRUNCATED, not negative.
limited() {
  conductor --json session message "$1" --limit 300 2>/dev/null \
    | grep -qi 'hit your session limit\|usage limit reached' && return 0 || return 1
}
for cell in "$@"; do
  scen="${cell%%:*}"; r="${cell##*:}"
  sid=$(conductor --json session create --workspace "$ws" --agent claude --model "$model" \
    --name "probe-$arm-$scen-r$r-$tag" --message-file "/tmp/rig/prompts/task-$scen.txt" 2>&1 | sid_of)
  [ "$sid" = "ERR" ] && { echo -e "$arm\t$scen\t$r\t$model\tCREATE_FAILED\t-" >> "$out"; continue; }
  wait_idle "$sid" || { echo -e "$arm\t$scen\t$r\t$model\tTASK_TIMEOUT\t$sid" >> "$out"; continue; }
  if limited "$sid"; then echo -e "$arm\t$scen\t$r\t$model\tLIMITED\t$sid" >> "$out"; echo "LIMIT HIT — aborting $arm" >> "$out"; break; fi
  conductor message create --session "$sid" --message-file "$FOLLOWUP" >/dev/null 2>&1
  wait_idle "$sid" || { echo -e "$arm\t$scen\t$r\t$model\tFOLLOWUP_TIMEOUT\t$sid" >> "$out"; continue; }
  if limited "$sid"; then echo -e "$arm\t$scen\t$r\t$model\tLIMITED\t$sid" >> "$out"; echo "LIMIT HIT — aborting $arm" >> "$out"; break; fi
  echo -e "$arm\t$scen\t$r\t$model\tOK\t$sid" >> "$out"
  conductor message create --session "$sid" --message "Run: git checkout -- . && git clean -fd core-docs src. Then reply DONE." >/dev/null 2>&1
  wait_idle "$sid"
done
echo "ARM $arm/$tag DONE" >> "$out"

# shellcheck shell=sh
# Sourced helper: stage ONE artifact into the shared preview directory, serve it, and
# set PREVIEW_URL / PREVIEW_AUDIENCE for the hand-off renderer. Sets nothing on any
# failure path, so the caller's `${PREVIEW_URL:+--url …}` degrades to v1.59.0's line.
#
# SOURCED, not executed, and that is the point: shell state does not survive between
# Bash tool calls, so a URL produced in one call cannot be read in the next. Sourcing
# puts the whole sequence inside the caller's own fence by construction instead of by
# an instruction three skills had to remember. (The prose-reference version had already
# drifted: ship-spike's "set these first" note sat AFTER the fence it modified, so a
# top-to-bottom reader ran the render with PREVIEW_URL empty — the exact silent drop.)
#
# Usage, inside the caller's existing block:
#     . "${CLAUDE_PLUGIN_ROOT:-plugins/flow}/skills/ship/lib/serve-preview.sh"
#     flow_serve_preview "<artifact path>" && :   # never let it fail the ship
#
# Precedent: ship/lib/verify-pr-body.sh is already a sourced helper for the same reason.

flow_serve_preview() {
  PREVIEW_URL=""
  PREVIEW_AUDIENCE=""
  _fsp_artifact="$1"

  _fsp_pb="${CLAUDE_PLUGIN_ROOT:-plugins/flow}/lib/preview_backend.py"
  [ -f "$_fsp_pb" ] || _fsp_pb="plugins/flow/lib/preview_backend.py"
  _fsp_root=$(git rev-parse --show-toplevel 2>/dev/null)

  if [ -z "$_fsp_artifact" ]; then
    echo "⚠️ [preview] no artifact path given — nothing to serve; the hand-off names the local file." >&2
    return 0
  fi
  if [ ! -f "$_fsp_artifact" ]; then
    # The artifact genuinely may not exist (a ship where §5a produced no walkthrough is
    # a supported state). Publishing anyway would hand over a URL for a missing file —
    # a live-looking link to a 404, the defect this whole feature must not create.
    echo "[preview] $_fsp_artifact does not exist, so there is nothing to serve — the hand-off names the local file. (A ship with no walkthrough is a supported state, not a failure.)" >&2
    return 0
  fi
  if [ -z "$_fsp_root" ]; then
    echo "⚠️ [preview] not inside a git repository — nothing will be served; the hand-off names the local file." >&2
    return 0
  fi
  if [ ! -f "$_fsp_pb" ]; then
    echo "⚠️ [preview] adapter engine not found at $_fsp_pb — nothing will be served; the hand-off names the local file." >&2
    return 0
  fi
  if ! python3 "$_fsp_pb" check >/dev/null 2>&1; then
    # Unset or malformed. Unset is the documented default and not a problem; /flow:doctor
    # Check 2.13 is what reports a malformed one, so this stays quiet either way.
    return 0
  fi

  _fsp_dir="$_fsp_root/.flow/preview"
  _fsp_port=$(jq -r '.previewBackend.port // 8897' flow.config.json 2>/dev/null)
  [ -z "$_fsp_port" ] && _fsp_port=8897
  mkdir -p "$_fsp_dir" || { echo "⚠️ [preview] could not create $_fsp_dir — the hand-off names the local file." >&2; return 0; }

  # Qualify the staged name. Two prototypes in one workspace would both land as
  # `prototype.presented.html`, so the second silently replaces the first at a URL that
  # still looks like the approved one — against the two-stable-paths design.
  # A stamp derived from the SOURCE PATH (not the content — do not call it a content
  # hash), appended before the extension so the name still reads as "report" at a
  # glance. A leading token is the part that identifies nothing where a client
  # truncates a long URL or a human scans one.
  _fsp_base=$(basename "$_fsp_artifact")
  _fsp_stamp=$(printf '%s' "$_fsp_artifact" | python3 -c 'import hashlib,sys;print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest()[:8])' 2>/dev/null)
  if [ -n "$_fsp_stamp" ]; then
    case "$_fsp_base" in
      *.*) _fsp_base="${_fsp_base%.*}-${_fsp_stamp}.${_fsp_base##*.}" ;;
      *)   _fsp_base="${_fsp_base}-${_fsp_stamp}" ;;
    esac
  fi

  # Copy, never symlink: a static server following a symlink out of its root is a
  # path-traversal surface, and the copy makes the served page a SNAPSHOT of what the
  # human was shown rather than a file that moves under them mid-review.
  if ! cp -f "$_fsp_artifact" "$_fsp_dir/$_fsp_base"; then
    echo "⚠️ [preview] could not stage $_fsp_artifact into $_fsp_dir — not publishing a URL for a file that is not there." >&2
    return 0
  fi

  _fsp_serve=$(python3 "$_fsp_pb" render serve --dir "$_fsp_dir" --port "$_fsp_port" 2>&1)
  if [ -z "$_fsp_serve" ] || [ "${_fsp_serve#*⚠️}" != "$_fsp_serve" ]; then
    echo "⚠️ [preview] serve command could not be rendered: $_fsp_serve" >&2
    return 0
  fi
  if ! sh -c "$_fsp_serve" >/dev/null; then
    # DISTINCT from the render failure above. The old single `||` reported "could not be
    # rendered" for a server that failed to start (busy port, foreign root), echoing the
    # command instead of the reason.
    echo "⚠️ [preview] the serve command ran and failed — most likely the port is busy or serving a different root. Not publishing; the hand-off names the local file." >&2
    return 0
  fi
  if ! python3 "$_fsp_pb" listening --port "$_fsp_port" >/dev/null 2>&1; then
    echo "⚠️ [preview] nothing is listening on $_fsp_port after serve, so there is nothing to publish." >&2
    return 0
  fi

  _fsp_pub=$(python3 "$_fsp_pb" render publish --port "$_fsp_port" 2>&1)
  if [ -z "$_fsp_pub" ] || [ "${_fsp_pub#*⚠️}" != "$_fsp_pub" ]; then
    echo "⚠️ [preview] publish command could not be rendered: $_fsp_pub" >&2
    return 0
  fi
  # Neither stderr is discarded. extract-url's whole value is the stated reason it
  # refused ("printed 3 distinct URLs", "printed an http:// URL"), and the publish
  # command's own stderr is what explains a vendor-side failure. The first cut swallowed
  # the latter while promising "see above", so the diagnosis it pointed at was absent.
  # 2>&1 folds publish's stderr into the stream extract-url reads, which is harmless —
  # extract-url requires exactly one https URL and refuses anything ambiguous.
  _fsp_base_url=$(sh -c "$_fsp_pub" 2>&1 | python3 "$_fsp_pb" extract-url --stdin)
  if [ -z "$_fsp_base_url" ]; then
    echo "⚠️ [preview] no URL could be read from publish (see above) — the hand-off names the local file." >&2
    return 0
  fi

  # COMPOSE <url>/<file>. The bare publish URL is the DIRECTORY: handing it over gives
  # the reader a server-generated index listing, and gives both artifacts the identical
  # link — collapsing "one URL, two stable paths" into one ambiguous one. Four places
  # documented this composition before anything performed it.
  PREVIEW_URL="${_fsp_base_url%/}/$_fsp_base"
  PREVIEW_AUDIENCE=$(jq -r '.previewBackend.audience // empty' flow.config.json 2>/dev/null)
  # >&2 like its ten siblings. stdout is what the caller pastes into the PR body /
  # chat message, so a progress line on stdout gets PUBLISHED.
  echo "[preview] serving $_fsp_base at $PREVIEW_URL" >&2
  return 0
}

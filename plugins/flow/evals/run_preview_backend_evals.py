#!/usr/bin/env python3
"""Regression pin for lib/preview_backend.py and the hand-off's additive `--url`.

Why this harness carries the behavioural load: flow's `flow.config.json` sets
`"platform": "library"`, so `/flow:verify-build` self-skips — there is no behavioural
gate above this file.

What it deliberately does NOT test: the host. Every arm here drives a fake adapter
(`true`, `printf`, a real `python3 -m http.server` on a temp port), because the thing
under test is the ADAPTER CONTRACT — closed vocabulary, refuse-not-escape, degrade
loudly, never emit a URL on a guess. A test that needed a live Conductor workspace
would be untestable in CI and would measure the vendor rather than flow.

The one live measurement this feature rests on is recorded where it belongs — in the
history entry and in `flow.config.json`'s own comment — not re-run here: an
unauthenticated fetch of a served page returned http 401 "Sign in to view this
preview." (30 bytes) against a local control of http 200 (86 bytes), on 2026-10-04.
"""

from __future__ import annotations

import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FLOW = HERE.parent
REPO = FLOW.parent.parent
LIB = FLOW / "lib" / "preview_backend.py"
ENGINE = FLOW / "skills" / "ship" / "lib" / "artifact-handoff.py"
SCHEMA = FLOW / "schema" / "flow.config.schema.json"
CI = REPO / ".github" / "workflows" / "ci.yml"
SHIP = FLOW / "skills" / "ship" / "SKILL.md"
SPIKE = FLOW / "skills" / "ship-spike" / "SKILL.md"
PROTO = FLOW / "skills" / "prototype" / "SKILL.md"
VERIFY = FLOW / "skills" / "verify-build" / "SKILL.md"
DOCTOR = FLOW / "skills" / "doctor" / "SKILL.md"
HELPER = FLOW / "skills" / "ship" / "lib" / "serve-preview.sh"


def _free_port():
    s_ = socket.socket(); s_.bind(("127.0.0.1", 0))
    p_ = s_.getsockname()[1]; s_.close(); return p_

_spec = importlib.util.spec_from_file_location("preview_backend", LIB)
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)

_espec = importlib.util.spec_from_file_location("artifact_handoff", ENGINE)
A = importlib.util.module_from_spec(_espec)
_espec.loader.exec_module(A)

_failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print("  PASS  %s" % name)
    else:
        print("  FAIL  %s%s" % (name, ("\n        " + detail) if detail else ""))
        _failures.append(name)


GOOD = {
    "serve": "/bin/true {dir} {port}",
    "publish": "/bin/echo https://example.test/ {port}",
    "unpublish": "/bin/true",
}


def _cfg(td, backend):
    p = Path(td, "flow.config.json")
    p.write_text(json.dumps({} if backend is None else {"previewBackend": backend}),
                 encoding="utf-8")
    return str(p)


# ----------------------------------------------------------------- the cases

def test_unset_is_byte_identical():
    """With the slot unset, every hand-off is exactly v1.59.0's.

    The default path must not move AT ALL. Expected strings are written out here
    rather than imported, deliberately: importing the engine's own format string
    would make this go green on any reword, and "the default did not change" is the
    one promise a consumer who never configures this slot is relying on.
    """
    with tempfile.TemporaryDirectory() as td:
        backend, warns = P.load_backend(_cfg(td, None))
        check("unset/empty-backend", backend == {}, repr(backend))
        check("unset/says-so-without-alarm",
              warns and "no `previewBackend` slot" in warns[0] and "⚠️" not in warns[0],
              "an absent slot is the documented default, not a warning: %r" % warns)
        rep = P.validate(backend)
        check("unset/not-usable", rep["usable"] is False)
        # One verdict, not two near-synonyms: a second `ok` was carried over from
        # dispatch and read by nothing here, leaving a future reader to adjudicate.
        check("unset/single-verdict-field", "ok" not in rep, sorted(rep))

    want_w = ("Walkthrough — a file on one machine's disk, not committed and not reachable "
              "from this page. You can only open it where this pipeline ran: "
              "`.flow/report.html`.")
    want_p = ("Your prototype is a local file — it lives at `/abs/p.html`, and you can only "
              "open it where this session ran, not from a link. The small floating comment "
              "dock is flow's, not the design.")
    check("unset/walkthrough-byte-identical",
          A.render_local_line("walkthrough", ".flow/report.html") == want_w,
          repr(A.render_local_line("walkthrough", ".flow/report.html")))
    check("unset/prototype-byte-identical",
          A.render_local_line("prototype", "/abs/p.html") == want_p,
          repr(A.render_local_line("prototype", "/abs/p.html")))
    # Explicit None/empty must behave as unset, not as a falsy surprise.
    for bad in (None, ""):
        check("unset/url=%r-is-unset" % bad,
              A.render_local_line("walkthrough", ".flow/report.html", bad) == want_w)


def test_closed_vocabulary():
    """An unknown placeholder is a hard error at LOAD, not a failure at publish time."""
    with tempfile.TemporaryDirectory() as td:
        # NEGATIVE: the vocabulary is closed, and {url} in particular is refused —
        # the URL is output, never something a template composes.
        for bad, label in (({"serve": "/bin/true {dir} {port}",
                             "publish": "/bin/echo {url}"}, "url"),
                           ({"serve": "/bin/true {dir} {port} {branch}",
                             "publish": "/bin/echo {port}"}, "branch")):
            rep = P.validate(bad)
            check("vocab/%s-refused-at-validate" % label, rep["usable"] is False)
            problems = " ".join(sum((v.get("problems") or []
                                     for v in rep["verbs"].values()), []))
            # The report is read by a human at setup, so it must not carry render's
            # prefix fragments (the first cut hand-sliced and left "serve`: ..." glued
            # to the problem).
            for v, e in rep["verbs"].items():
                for prob in (e.get("problems") or []):
                    # Target the LEAK SHAPE, not "starts with a backtick": the
                    # absent-verb message legitimately opens "`unpublish` is not
                    # configured", and rejecting that was the assertion being wrong
                    # rather than the code.
                    check("vocab/%s-%s-message-is-clean" % (label, v),
                          "refusing to render" not in prob
                          and not prob.startswith("%s`" % v)
                          and "[preview-backend]" not in prob,
                          "leaked render prefix: %r" % prob[:90])
            check("vocab/%s-names-the-closed-set" % label,
                  "closed" in problems and label in problems, problems[:200])
            verb = "serve" if label == "branch" else "publish"
            argv, err = P.render(bad, verb, {"dir": "/tmp/x", "port": "8900", "url": "x"})
            check("vocab/%s-refused-at-render-too" % label, argv is None and err,
                  "render(%s) should refuse: %r %r" % (verb, argv, err))
        # POSITIVE, paired: the three legal placeholders ARE accepted, so none of the
        # negatives above can be satisfied by refusing everything.
        rep = P.validate(GOOD)
        check("vocab/legal-template-accepted", rep["usable"] is True, json.dumps(rep))
        argv, err = P.render(GOOD, "serve", {"dir": "/tmp/x", "port": "8900"})
        check("vocab/legal-template-renders", argv == ["/bin/true", "/tmp/x", "8900"],
              "%r %r" % (argv, err))
        check("vocab/no-url-placeholder-exists", "url" not in P.KNOWN_PLACEHOLDERS,
              "the URL is OUTPUT; a template that could compose it would let config "
              "decide what the hand-off claims")


def test_shell_operator_is_refused():
    """A template carrying a shell operator is refused, with the fix named.

    One rendered command silently becoming two is the whole reason this is a template
    vocabulary and not a free-form string.
    """
    for op in ("&", ">", ";", "|", "`"):
        tmpl = {"serve": "python3 -m http.server {port} --directory {dir} %s" % op,
                "publish": "/bin/echo https://x.test/"}
        rep = P.validate(tmpl)
        probs = " ".join(rep["verbs"]["serve"].get("problems") or [])
        check("operator/%s-refused" % op, rep["usable"] is False and "shell operator" in probs,
              probs[:160])
        check("operator/%s-names-the-fix" % op, "script the template CALLS" in probs,
              "the refusal must say what to do instead, or the author has no next move")
        argv, err = P.render(tmpl, "serve", {"dir": "/tmp/x", "port": "8900"})
        check("operator/%s-refused-at-render" % op, argv is None, repr(argv))


def test_url_extraction_never_guesses():
    """Zero URLs, many URLs, and http:// are each a stated refusal — never a guess."""
    url, err = P.extract_url("URL   https://a.test/\nPort  8901\n")
    check("extract/one-url", url == "https://a.test/" and err is None, "%r %r" % (url, err))
    url, err = P.extract_url("no url here")
    check("extract/zero-refuses", url is None and "no https URL" in (err or ""), str(err))
    url, err = P.extract_url("https://a.test/ and https://b.test/")
    check("extract/two-refuses", url is None and "will not guess" in (err or ""), str(err))
    url, err = P.extract_url("URL http://a.test/")
    check("extract/http-refused", url is None and "downgrade the transport" in (err or ""),
          "an unencrypted URL for a sign-in-gated page is refused deliberately: %r" % err)
    # Trailing punctuation is stripped, and a repeat of the SAME url is one url.
    url, _ = P.extract_url("see https://a.test/x.html.")
    check("extract/strips-trailing-punctuation", url == "https://a.test/x.html", repr(url))
    url, _ = P.extract_url("https://a.test/ ... https://a.test/")
    check("extract/same-url-twice-is-one", url == "https://a.test/", repr(url))


def test_listen_check_precedes_publish():
    """Flow never publishes a port nothing is listening on — validated both ways.

    A check that can only ever say "not listening" would be no check at all, so this
    drives a REAL server on a real port as the known-positive before trusting the
    negative (.claude/rules/general.md Consistency item 4).
    """
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    free_port = s.getsockname()[1]
    s.close()
    check("listen/closed-port-is-not-listening", P.port_is_listening(free_port) is False,
          "port %d" % free_port)

    with tempfile.TemporaryDirectory() as td:
        Path(td, "probe.html").write_text("<!doctype html><meta charset=utf-8>ok",
                                          encoding="utf-8")
        srv = subprocess.Popen([sys.executable, "-m", "http.server", str(free_port),
                                "--bind", "127.0.0.1", "--directory", td],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            ok = False
            for _ in range(40):
                if P.port_is_listening(free_port):
                    ok = True
                    break
                import time
                time.sleep(0.1)
            # KNOWN POSITIVE: the instrument must be able to say "yes".
            check("listen/open-port-is-listening", ok,
                  "the predicate never returned True against a real server, so its "
                  "False is not evidence about anything")
        finally:
            srv.terminate()
            srv.wait(timeout=10)
    check("listen/port-is-free-again-after-teardown",
          P.port_is_listening(free_port) is False)
    for bad in ("not-a-port", "", "99999999"):
        check("listen/garbage-%r-is-false" % bad, P.port_is_listening(bad) is False)


def test_degrades_loudly():
    """Every failure yields the honest local line plus a reason — never a broken URL."""
    with tempfile.TemporaryDirectory() as td:
        arms = {
            "slot-unset": None,
            "not-an-object": "oops",
            "serve-missing": {"publish": "/bin/echo https://x.test/"},
            "publish-prints-nothing": {"serve": "/bin/true {dir} {port}",
                                       "publish": "/bin/true"},
        }
        # Each arm asserts ITS OWN CAUSE, against `warns` ONLY. The first cut
        # concatenated `warns` with `json.dumps(rep)` and looked for "previewBackend"
        # or "not configured" — and any non-usable report contains "is not configured"
        # from an absent verb, so the check was satisfied by a constant substring of
        # the report STRUCTURE regardless of whether any warning text existed.
        # MEASURED by the reviewer who found it: blanking every warning list to [""]
        # left all four of these green. That is Consistency item 4 inside the harness
        # that does instrument-validation better than most of this repo, which is
        # exactly why it is recorded here rather than quietly corrected.
        causes = {
            "slot-unset": "no `previewBackend` slot",
            "not-an-object": "is not an object",
            "serve-missing": None,   # a present, well-formed slot: no load warning owed
            "publish-prints-nothing": None,
        }
        for label, backend in arms.items():
            b, warns = P.load_backend(_cfg(td, backend))
            rep = P.validate(b)
            check("degrade/%s-not-usable" % label, rep["usable"] is False,
                  json.dumps(rep["verbs"], sort_keys=True)[:200])
            want = causes[label]
            if want is not None:
                joined = " ".join(warns)
                check("degrade/%s-names-its-own-cause" % label, want in joined,
                      "expected %r in the LOAD warnings, got %r" % (want, joined[:200]))
            else:
                # The slot loaded fine; the problem is per-verb and must say so there.
                probs = " ".join(sum((v.get("problems") or []
                                      for v in rep["verbs"].values()), []))
                check("degrade/%s-names-its-own-cause" % label, len(probs) > 20, probs[:200])
        # The malformed-slot arm's whole point is being DISTINGUISHABLE from "unset".
        b_absent, w_absent = P.load_backend(_cfg(td, None))
        b_bad, w_bad = P.load_backend(_cfg(td, "oops"))
        check("degrade/malformed-is-distinguishable-from-unset",
              " ".join(w_absent) != " ".join(w_bad)
              and "NOT the same as no adapter" in " ".join(w_bad),
              "a malformed adapter must not read like an absent one — the project "
              "believes it has one: %r" % " ".join(w_bad)[:200])
        check("degrade/unset-is-not-alarming", "⚠️" not in " ".join(w_absent),
              "unset is the documented default: %r" % " ".join(w_absent)[:160])
        # And the hand-off with no URL carries zero http strings — a failed adapter
        # must never leave a half-built link in the body.
        line = A.render_local_line("walkthrough", ".flow/report.html", None)
        check("degrade/no-http-in-fallback", "http" not in line, line)
        check("degrade/fallback-is-the-honest-line", "only open it where" in line, line)


def test_url_is_tappable_path_is_not():
    """The URL is a bare autolink; the local path stays a code span. Opposite, on purpose."""
    url = "https://a.test/report.html"
    line = A.render_local_line("walkthrough", ".flow/report.html", url,
                               "anyone with read access")
    check("tappable/url-present", url in line, line)
    check("tappable/url-not-code-spanned", "`%s`" % url not in line,
          "measured on iOS: a code span renders as monospace TEXT and is not tappable, "
          "so a code-spanned URL is unusable on the client this work is for")
    check("tappable/path-is-code-spanned", "`.flow/report.html`" in line, line)
    check("tappable/audience-next-to-the-link",
          line.index("read access") < line.index(".flow/report.html"),
          "the access statement belongs beside the link, not only in docs: %r" % line)
    check("tappable/local-line-survives", "openable only where this pipeline ran" in line,
          "the URL is ADDITIVE — a served preview dies when its workspace sleeps while "
          "the registration survives, so the local line is the floor: %r" % line)
    # The rule has to be written down, or the two treatments get "harmonised" later.
    src = ENGINE.read_text(encoding="utf-8")
    check("tappable/rule-is-written-down",
          "render it the way the reader can act on it" in src)
    # http:// is refused at this layer too, not only in the adapter.
    bad = A.render_local_line("walkthrough", ".flow/report.html", "http://a.test/x")
    check("tappable/http-url-dropped", "http://a.test/x" not in bad, bad)


def test_audience_is_stated_and_escaped():
    """The audience is consumer-supplied text landing in a markdown sentence."""
    line = A.render_local_line("prototype", "/abs/p.html", "https://a.test/p.html",
                               "org members [only] *everyone* else no")
    check("audience/escaped", "\\[only\\]" in line and "\\*everyone\\*" in line, line)
    check("audience/absent-when-unknown",
          " — " not in A.render_local_line("prototype", "/abs/p.html",
                                           "https://a.test/p.html").split("If that")[0]
          .replace("Prototype: https://a.test/p.html", ""),
          "flow states what it was told; inventing an audience would be the "
          "unverified-claim class this engine exists to remove")
    # The no-client guard must NOT fire on the audience or the URL (both legitimately
    # carry a host's name), and MUST still fire on flow's own wording.
    import contextlib
    import io
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        A.render_local_line("walkthrough", ".flow/report.html",
                            "https://x.conductor.show/r.html",
                            "signed in to Conductor with read access")
    check("audience/guard-silent-on-interpolated-values", err.getvalue() == "",
          "a warning that fires on every correctly-served hand-off is how people learn "
          "to ignore the warning: %r" % err.getvalue())
    err2 = io.StringIO()
    with contextlib.redirect_stderr(err2):
        A.render_local_line("walkthrough", "/tmp/x-iPhone.html")
    check("audience/guard-still-fires-on-flow-wording",
          "names a client" in err2.getvalue(),
          "scoping the guard must not disarm it: %r" % err2.getvalue())


def test_no_vendor_token_in_plugin():
    """No host CLI in an executable line of any plugin artifact — paired with the docs.

    The sweep itself lives in `run_dispatch_backend_evals.py` § 7, whose exact-artifact
    count already covers `plugins/flow/lib/*.py` and therefore `preview_backend.py` —
    it is what caught the new file. Duplicating that scan here would be a second
    definition of the same contract, so this asserts the JOIN instead.
    """
    sweep = (HERE / "run_dispatch_backend_evals.py").read_text(encoding="utf-8")
    check("vendor/existing-sweep-covers-the-shared-lib-dir",
          'PLUGIN / "lib"' in sweep and "HOST_LITERALS" in sweep,
          "if that sweep stops scanning plugins/flow/lib, this lib loses its guard")
    check("vendor/sweep-count-was-bumped-for-this-lib",
          "scanned == 12" in sweep and "preview_backend at v1.60.0" in sweep,
          "the exact count is the mechanism; bumping it with a reason is the cost")
    # POSITIVE, paired: the vendor-naming EXAMPLE must survive in the schema, or the
    # negative above could be satisfied by deleting the documentation.
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    ex = schema["properties"]["previewBackend"].get("examples")
    check("vendor/schema-documents-an-example", bool(ex) and "serve" in ex[0], repr(ex))
    check("vendor/example-is-generic",
          not any("conductor" in json.dumps(e).lower() for e in ex),
          "the schema's example must not name a real vendor either: %r" % ex)
    # ...and flow's OWN config DOES name one, which is the point (FB-0085): a slot
    # unset everywhere is a feature exercised nowhere.
    cfg = json.loads((REPO / "flow.config.json").read_text(encoding="utf-8"))
    pb = cfg.get("previewBackend") or {}
    check("vendor/flow-own-config-sets-the-slot",
          set(pb) >= {"serve", "publish"},
          "flow must configure this or ship a feature that runs nowhere: %r" % pb)
    check("vendor/flow-own-config-is-valid", P.validate(pb)["usable"] is True,
          json.dumps(P.validate(pb), sort_keys=True)[:300])
    check("vendor/flow-serve-calls-a-script-not-an-operator",
          ".claude/bin/" in pb.get("serve", ""),
          "backgrounding needs shell operators the adapter refuses, so it belongs in a "
          "script the template calls: %r" % pb.get("serve"))


def test_one_url_two_paths():
    """One workspace = one URL, so both artifacts live under it as two paths.

    This is the constraint the host CLI's own help states and that reshapes the
    feature: "setting a different port keeps the URL". Two ports would silently
    re-point the first link while leaving it looking valid.
    """
    for name, text in (("ship", SHIP.read_text(encoding="utf-8")),
                       ("prototype", PROTO.read_text(encoding="utf-8"))):
        check("oneurl/%s-names-the-shared-dir" % name, "preview" in text, name)
    src = LIB.read_text(encoding="utf-8")
    check("oneurl/constraint-is-written-down",
          "one" in src.lower() and "keeps the same URL" in src,
          "the constraint must be recorded next to the code that depends on it")
    check("oneurl/no-second-port-verb",
          set(P.VERBS) == {"serve", "publish", "unpublish"},
          "a fourth verb that published a second port would recreate the defect: %r"
          % sorted(P.VERBS))


def test_helper_is_sourced_in_the_same_block_as_the_render():
    """The serve helper must be SOURCED, in the same fenced block as the render.

    Shell state does not survive between Bash tool calls, so a `PREVIEW_URL` produced
    in one call cannot be read in the next: serve and publish would really run, print a
    real URL, and have it silently dropped. The first cut was a 40-line block in
    `/flow:ship` that the other two skills were told in PROSE to "run" — and that had
    already drifted, with `ship-spike`'s instruction sitting AFTER the fence it
    modified, so a top-to-bottom reader executed the render with the variable empty.
    Sourcing puts the sequence inside the caller's own fence by construction.
    """
    def fenced_block(text, needle):
        i = text.find(needle)
        if i == -1:
            return None
        st = text.rfind("```sh", 0, i)
        if st == -1:
            return None
        en = text.find("\n```", i)
        return text[st:en if en != -1 else len(text)]

    for name, text, kind in (("ship", SHIP.read_text(encoding="utf-8"), "walkthrough"),
                             ("spike", SPIKE.read_text(encoding="utf-8"), "walkthrough"),
                             ("prototype", PROTO.read_text(encoding="utf-8"), "prototype")):
        block = fenced_block(text, '. "$SP"; flow_serve_preview')
        check("sourced/%s-call-is-in-a-fence" % name, block is not None,
              "the helper call moved out of a shell block — re-key, do not drop")
        if block is None:
            continue
        check("sourced/%s-sources-the-helper" % name,
              ". \"$SP\"" in block and "serve-preview.sh" in block,
              "must SOURCE, not execute: an executed helper cannot export into the "
              "caller's shell")
        check("sourced/%s-render-is-in-the-same-block" % name,
              "local-line --kind %s" % kind in block,
              "the render that CONSUMES $PREVIEW_URL must be in the same block, or the "
              "variable is empty when read")
        check("sourced/%s-passes-the-url-conditionally" % name,
              "${PREVIEW_URL:+--url" in block,
              "an empty URL must expand to nothing, not to an empty --url")
        check("sourced/%s-cannot-fail-the-ship" % name,
              'PREVIEW_URL=""' in block or "flow_serve_preview" in block,
              "an optional convenience must never break a ship")
    # The helper itself must be a sourceable function, not a script with side effects.
    helper = HELPER.read_text(encoding="utf-8")
    check("sourced/helper-defines-a-function",
          "flow_serve_preview() {" in helper, "must be a function to be sourced")
    check("sourced/helper-states-why-sourced", "SOURCED, not executed" in helper)
    check("sourced/helper-has-no-top-level-side-effects",
          not any(l and not l.startswith(("#", " ", "\t", "}"))
                  and "flow_serve_preview() {" not in l
                  and not l.startswith("# ")
                  for l in helper.splitlines()[-3:]),
          "sourcing must not execute anything")


def test_helper_composes_url_slash_file():
    """`<url>/<file>`, composed for real — not the bare directory URL.

    The bare `publish` URL is the DIRECTORY. Handing it over gives the reader a
    server-generated index listing, and gives BOTH artifacts the identical link —
    collapsing "one URL, two stable paths" into one ambiguous one. Four places
    documented this composition before anything performed it, and the renderer pin
    could not see it because it was handed an already-composed URL: the wrong-layer
    pin this repo names explicitly. So this case drives the HELPER.
    """
    helper = HELPER.read_text(encoding="utf-8")
    check("compose/helper-appends-the-basename",
          '${_fsp_base_url%/}/$_fsp_base' in helper,
          "the composition must happen in the helper, not be described in prose")
    with tempfile.TemporaryDirectory() as td:
        art = Path(td, "report.html")
        art.write_text("<!doctype html><meta charset=utf-8>x", encoding="utf-8")
        # A fake adapter: serve is a no-op `true`, publish prints a bare directory URL.
        cfg = Path(td, "flow.config.json")
        cfg.write_text(json.dumps({"previewBackend": {
            "serve": "/bin/true {dir} {port}",
            "publish": "/bin/echo https://ws.example.test/ {port}",
            "audience": "org members only"}}), encoding="utf-8")
        port = _free_port()
        srv = subprocess.Popen([sys.executable, "-m", "http.server", str(port),
                                "--bind", "127.0.0.1", "--directory", td],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            cfg_data = json.loads(cfg.read_text(encoding="utf-8"))
            cfg_data["previewBackend"]["port"] = port
            cfg.write_text(json.dumps(cfg_data), encoding="utf-8")
            r = subprocess.run(
                ["bash", "-c",
                 'cd "$1" && git init -q . 2>/dev/null; . "$2"; '
                 'flow_serve_preview "$3" >/dev/null 2>&1; printf "%s" "$PREVIEW_URL"',
                 "_", td, str(HELPER), str(art)],
                capture_output=True, text=True, timeout=60,
                env=dict(os.environ, CLAUDE_PLUGIN_ROOT=str(FLOW)))
            url = r.stdout.strip()
            check("compose/url-was-produced", url.startswith("https://"),
                  "helper produced %r (stderr: %s)" % (url, r.stderr[-200:]))
            check("compose/url-is-not-the-bare-directory",
                  url.rstrip("/") != "https://ws.example.test",
                  "the bare directory URL serves an index listing, not the artifact: %r"
                  % url)
            # The stamp is a SUFFIX before the extension (`report-8f3a21bc.html`), not a
            # prefix: where a client truncates a long URL or a human scans one, a
            # leading token is the part that identifies nothing.
            last = url.rsplit("/", 1)[-1]
            check("compose/filename-keeps-a-readable-stem",
                  last.startswith("report-") and last.endswith(".html"),
                  "the name must still read as the artifact at a glance: %r" % last)
            check("compose/filename-is-qualified", last != "report.html",
                  "two artifacts with the same basename would collide at one URL: %r"
                  % last)
            check("compose/stamp-is-before-the-extension",
                  last.count(".") == 1 and "-" in last.rsplit(".", 1)[0],
                  "the extension must survive, or the server serves it as the wrong "
                  "type: %r" % last)
        finally:
            srv.terminate(); srv.wait(timeout=10)


def test_helper_sets_nothing_when_it_cannot_serve():
    """Every failure path sets NO url — a link for a missing file is the worst output."""
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td, "flow.config.json")
        cfg.write_text(json.dumps({"previewBackend": {
            "serve": "/bin/true {dir} {port}",
            "publish": "/bin/echo https://ws.example.test/ {port}"}}), encoding="utf-8")
        for label, arg in (("missing-artifact", str(Path(td, "nope.html"))),
                           ("empty-arg", "")):
            r = subprocess.run(
                ["bash", "-c",
                 'cd "$1" && git init -q . 2>/dev/null; . "$2"; '
                 'flow_serve_preview "$3" >/dev/null 2>&1; printf "%s" "$PREVIEW_URL"',
                 "_", td, str(HELPER), arg],
                capture_output=True, text=True, timeout=60,
                env=dict(os.environ, CLAUDE_PLUGIN_ROOT=str(FLOW)))
            check("nourl/%s-sets-nothing" % label, r.stdout.strip() == "",
                  "handed over %r for an artifact that is not there" % r.stdout.strip())
        # Paired positive: the helper DOES set a URL when everything is in place, so
        # the negatives above cannot pass by never working at all.
        art = Path(td, "ok.html"); art.write_text("x", encoding="utf-8")
        port = _free_port()
        d = json.loads(cfg.read_text(encoding="utf-8"))
        d["previewBackend"]["port"] = port
        cfg.write_text(json.dumps(d), encoding="utf-8")
        srv = subprocess.Popen([sys.executable, "-m", "http.server", str(port),
                                "--bind", "127.0.0.1", "--directory", td],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            r = subprocess.run(
                ["bash", "-c",
                 'cd "$1" && git init -q . 2>/dev/null; . "$2"; '
                 'flow_serve_preview "$3" >/dev/null 2>&1; printf "%s" "$PREVIEW_URL"',
                 "_", td, str(HELPER), str(art)],
                capture_output=True, text=True, timeout=60,
                env=dict(os.environ, CLAUDE_PLUGIN_ROOT=str(FLOW)))
            check("nourl/positive-does-set-a-url", r.stdout.strip().startswith("https://"),
                  "the helper never succeeds, so the negatives prove nothing: %r / %s"
                  % (r.stdout.strip(), r.stderr[-200:]))
        finally:
            srv.terminate(); srv.wait(timeout=10)


def test_serve_refuses_a_foreign_root():
    """The idempotency check compares the served ROOT, not just "a port is open".

    Gating on the port alone adopts ANY pre-existing listener and publishes its root.
    Not hypothetical: the port default and `.claude/launch.json` both sat on 8899,
    and the launch recipe serves `.flow` — the scratch directory — so flow's own dev
    server would have been adopted and published, bypassing the staged snapshot whose
    entire purpose is that the reviewer sees what they were shown.

    Paired, and both arms are driven for real: our own root is REUSED, a foreign root
    is REFUSED. A one-armed version could not tell a working check from one that
    always refuses.
    """
    script = REPO / ".claude" / "bin" / "flow-preview-serve.sh"
    check("root/script-exists", script.is_file(), str(script))
    if not script.is_file():
        return
    src = script.read_text(encoding="utf-8")
    check("root/compares-the-root-not-just-the-port",
          "serving_root" in src and ".flow-preview-root" in src,
          "the idempotency check must verify WHICH directory is being served")
    # The sentinel is INSIDE the served root, so whatever it holds is fetchable by
    # anyone who can reach the preview URL. A hash answers "is this our root?" exactly
    # as well and discloses nothing; the first cut wrote the absolute path.
    check("root/sentinel-is-a-hash-not-the-path",
          "sha256sum" in src and 'printf \'%s\' "${DIR%/}" >' not in src,
          "the sentinel must not disclose the directory it names")
    # And the access log must not live in the served root either: it is fetchable and
    # it records every request path.
    check("root/access-log-outside-the-served-root",
          '.preview-server.log' in src and '"${DIR%/}/.server.log"' not in src,
          "an access log inside the served directory is itself served")
    check("root/refuses-rather-than-adopts",
          "Refusing to adopt it" in src and "exit 1" in src,
          "adopting a foreign root publishes someone else's directory")

    with tempfile.TemporaryDirectory() as td:
        ours = Path(td, "preview"); ours.mkdir()
        port = _free_port()
        r1 = subprocess.run(["bash", str(script), str(ours), str(port)],
                            capture_output=True, text=True, timeout=60)
        check("root/first-start-succeeds", r1.returncode == 0,
              (r1.stdout + r1.stderr)[-300:])
        try:
            # ARM 1 (positive): same root, same port -> reuse, exit 0.
            r2 = subprocess.run(["bash", str(script), str(ours), str(port)],
                                capture_output=True, text=True, timeout=60)
            check("root/same-root-is-reused",
                  r2.returncode == 0 and "reusing it" in r2.stdout,
                  (r2.stdout + r2.stderr)[-300:])
            # ARM 2 (negative): a DIFFERENT root on that same port -> refuse, non-zero.
            other = Path(td, "elsewhere"); other.mkdir()
            r3 = subprocess.run(["bash", str(script), str(other), str(port)],
                                capture_output=True, text=True, timeout=60)
            check("root/foreign-root-is-refused", r3.returncode != 0,
                  "a server rooted elsewhere was ADOPTED: %s"
                  % (r3.stdout + r3.stderr)[-300:])
            check("root/refusal-names-the-conflict",
                  "already in use" in r3.stderr and "Refusing to adopt" in r3.stderr,
                  r3.stderr[-300:])
        finally:
            subprocess.run(["bash", "-c",
                            "ps -eo pid,args | grep 'http.server %d' | grep -v grep "
                            "| awk '{print $1}' | xargs -r kill" % port],
                           capture_output=True, timeout=30)


def test_ship_gates_publish_on_the_serve_step():
    """Publish only when SERVE succeeded — not merely when a port is open.

    The serve step is what verifies the root, so gating on "something is listening"
    would route around the check above.
    """
    ship = SHIP.read_text(encoding="utf-8")
    check("gate/serve-ok-flag-exists", "SERVE_OK" in ship)
    check("gate/publish-requires-serve-ok",
          '[ "$SERVE_OK" = yes ] && python3 "$PB" listening' in ship,
          "publish must require the serve step's success AND a live port")
    check("gate/states-why", "verifies the served ROOT" in ship)
    check("gate/nested-config-reads",
          ".previewBackend.port" in ship and ".previewBackend.audience" in ship,
          "port/audience are nested inside previewBackend, not sibling slots")


def test_doctor_checks_the_slot():
    """A malformed template must not fail open and invisible."""
    d = DOCTOR.read_text(encoding="utf-8")
    check("doctor/mentions-previewBackend", "previewBackend" in d)
    check("doctor/is-a-warn-not-a-fail", "preview_backend.py" in d,
          "the check should drive the engine, not re-implement its validation")


def test_ci_wired():
    ci = CI.read_text(encoding="utf-8")
    check("ci/this-harness-wired",
          "python3 plugins/flow/evals/%s" % Path(__file__).name in ci,
          "an unwired harness contributes zero regression protection while appearing to")


def main() -> int:
    tests = (test_unset_is_byte_identical, test_closed_vocabulary,
             test_shell_operator_is_refused, test_url_extraction_never_guesses,
             test_listen_check_precedes_publish, test_degrades_loudly,
             test_url_is_tappable_path_is_not, test_audience_is_stated_and_escaped,
             test_no_vendor_token_in_plugin, test_one_url_two_paths,
             test_helper_is_sourced_in_the_same_block_as_the_render,
             test_helper_composes_url_slash_file,
             test_helper_sets_nothing_when_it_cannot_serve,
             test_serve_refuses_a_foreign_root,
             test_doctor_checks_the_slot, test_ci_wired)
    print("[preview-backend] %d case groups" % len(tests))
    for fn in tests:
        print(" %s" % fn.__name__)
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            _failures.append("%s raised %s: %s" % (fn.__name__, type(exc).__name__, exc))
            print("  FAIL  %s raised %s: %s" % (fn.__name__, type(exc).__name__, exc))
    if _failures:
        print("\n[preview-backend] FAIL — %d check(s):" % len(_failures))
        for f in _failures:
            print("  - %s" % f)
        return 1
    print("\n[preview-backend] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

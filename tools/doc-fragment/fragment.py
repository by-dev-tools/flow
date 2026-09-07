#!/usr/bin/env python3
"""Split an append-only markdown doc into one file per entry.

Dev infrastructure (`tools/`), NOT a shipped plugin artifact. A rollup generator
living inside `plugins/flow/` is an invitation for a consumer to depend on it,
which would recreate the coupling this migration removes.

The tool SLICES the original rather than re-rendering it, so byte conservation is
checkable: every byte of the input lands in exactly one output slice, in order.

Three guarantees, in the order they matter:

1. Byte conservation -- `sha256(concat(slices in source order)) == sha256(source)`.
   Order-free with respect to the new canonical filenames, so it proves nothing was
   lost or duplicated regardless of how the fragments end up sorted.
2. Entry census -- the SET of entry identifiers in the fragments equals the set in
   the source, and the counts match. Byte conservation alone would not catch a
   heading swallowed into a neighbour's body (the bytes are all still there, in the
   wrong fragment); this does.
3. Collision refusal -- two entries mapping to one filename is a HARD STOP. This is
   the permanent property that replaces `reserved-feedback-numbers.md`: a duplicate
   FB number becomes a filename collision, which git surfaces as a both-added
   conflict instead of a silent semantic one.

Re-run the conservation proof later with `--verify <fragment-dir>`, which reads only the
manifest and the files on disk.

Known collisions may be admitted one at a time via `--disambiguate <basename>`,
which suffixes the colliding fragments `-a`, `-b`, ... There is deliberately no
global `--force`: a blanket override would let a future migration paper over an
UNKNOWN collision, which is the exact failure this migration exists to remove.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import unicodedata
from pathlib import Path

# --------------------------------------------------------------------------
# Entry grammars. One per source doc. `heading` matches the line that STARTS an
# entry; everything up to the next heading (or the next non-entry section) is its
# body. `ident` extracts the stable identifier used for the census.
# --------------------------------------------------------------------------

SLUG_MAX = 60


def slugify(text: str) -> str:
    """Filename-safe slug. ASCII-folded so a fragment name never depends on the
    filesystem's unicode normalisation (macOS NFD vs Linux NFC would otherwise make
    the same entry produce two different filenames on two machines)."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[`*_\[\]()#/\\]", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:SLUG_MAX].strip("-") or "entry"


class Grammar:
    """How one source doc's entries are recognised and named."""

    def __init__(self, name, heading_re, ident_fn, filename_fn):
        self.name = name
        self.heading_re = re.compile(heading_re, re.M)
        self.ident_fn = ident_fn
        self.filename_fn = filename_fn


def _hist_ident(m, body):
    """history.md carries two entry shapes (the doc was restructured mid-life):
    `## YYYY-MM-DD - Title` for newer entries, and `### Title` + a `**Date:**` line
    for older ones below the `## Entries` marker. Normalise both to (date, title)."""
    raw = m.group(0).lstrip("#").strip()
    dm = re.match(r"(\d{4}-\d{2}-\d{2})\s*[-—–]+\s*(.*)", raw)
    if dm:
        return dm.group(1), dm.group(2).strip()
    # Tolerate the bulleted variant (`- **Date:** ...`) as well as the bare one.
    # One entry in the corpus uses it, and a date-less filename (0000-00-00-...)
    # sorts to the front of the directory and silently lies about when it shipped.
    dm = re.search(r"^\s*(?:[-*]\s*)?\*\*Date:\*\*\s*(\d{4}-\d{2}-\d{2})", body, re.M)
    if not dm:
        raise SystemExit(
            f"[fragment] entry has no parseable **Date:** line, and a 0000-00-00 filename "
            f"would sort to the front while silently lying about when it shipped:\n    {raw[:120]}"
        )
    return dm.group(1), raw


GRAMMARS = {
    "history": Grammar(
        "history",
        r"^(?:##|###) (?!How to Write an Entry$|Entries$)(?!\[Short title).+$",
        _hist_ident,
        lambda ident: f"{ident[0]}-{slugify(ident[1])}.md",
    ),
    "feedback": Grammar(
        "feedback",
        r"^### FB-\d{4}.+$",
        lambda m, body: (
            re.search(r"FB-\d{4}", m.group(0)).group(0),
            m.group(0).lstrip("#").strip(),
        ),
        lambda ident: f"{ident[0]}-{slugify(ident[1].split(None, 1)[-1])}.md",
    ),
    "changelog": Grammar(
        "changelog",
        r"^## v\d+\.\d+\.\d+.*$",
        lambda m, body: (
            re.search(r"v\d+\.\d+\.\d+", m.group(0)).group(0),
            m.group(0).lstrip("#").strip(),
        ),
        lambda ident: f"{ident[0]}.md",
    ),
}


def slice_source(text: str, g: Grammar):
    """Return (non_entry_slices, entries) where entries is a list of
    (start, end, ident, heading_line). Slices tile the source exactly."""
    marks = [(m.start(), m) for m in g.heading_re.finditer(text)]
    if not marks:
        raise SystemExit(f"[fragment] no entries matched the '{g.name}' grammar — refusing to write.")

    # Boundaries: an entry runs to the next entry heading, or to the start of a
    # non-entry section heading that outranks it, or EOF.
    section_re = re.compile(r"^## (?:How to Write an Entry|Entries|Notes on versioning)\s*$", re.M)
    sections = [m.start() for m in section_re.finditer(text)]

    entries = []
    for i, (start, m) in enumerate(marks):
        nxt = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        for s in sections:
            if start < s < nxt:
                nxt = s
                break
        body = text[start:nxt]
        entries.append((start, nxt, g.ident_fn(m, body), m.group(0)))
    return entries


def verify(directory: Path) -> int:
    """Re-prove byte conservation for an already-fragmented directory, from disk.

    Reads ONLY `_manifest.tsv` and the fragments beside it; it never re-derives the
    slicing, so it cannot agree with the fragmenter by construction. That independence
    is the entire value -- a tool that checks its own in-memory work proves only that
    it agrees with itself.

    Prints a digest comparison and NEVER the reassembled text. Emitting the
    concatenation would make this a rollup generator, and a rollup generator in the
    tree is how a committed rollup eventually happens -- the one outcome
    one-file-per-entry exists to prevent.
    """
    manifest = directory / "_manifest.tsv"
    if not manifest.is_file():
        print(f"[verify] no manifest at {manifest}", file=sys.stderr)
        return 2

    order, declared = [], None
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if line.startswith("#sha256\t"):
            declared = line.split("\t", 1)[1].strip()
        elif line.startswith("#"):
            continue
        elif line.strip():
            order.append(line.strip())

    if declared is None:
        print("[verify] manifest carries no #sha256 line — nothing to prove against.", file=sys.stderr)
        return 2

    missing = [n for n in order if not (directory / n).is_file()]
    if missing:
        print(f"[verify] {len(missing)} file(s) named in the manifest are absent: {missing[:5]}", file=sys.stderr)
        return 2

    # An UNLISTED file is not harmless: the directory then holds content the proof does
    # not cover. Refuse rather than quietly ignore it.
    on_disk = {f.name for f in directory.iterdir() if f.is_file() and f.name != "_manifest.tsv"}
    extra = sorted(on_disk - set(order))
    if extra:
        print(f"[verify] {len(extra)} file(s) on disk are not in the manifest: {extra[:5]}", file=sys.stderr)
        return 2

    h = hashlib.sha256()
    for n in order:
        h.update((directory / n).read_bytes())
    got = h.hexdigest()
    print(f"[verify] {directory}: {len(order)} files")
    print(f"[verify]   manifest sha256 {declared}")
    print(f"[verify]   on-disk  sha256 {got}")
    print(f"[verify]   {'BYTE CONSERVATION PROVED (from disk)' if got == declared else 'MISMATCH'}")
    return 0 if got == declared else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path,
                    help="the doc to fragment, or (with --verify) an existing fragment directory")
    ap.add_argument("--verify", action="store_true",
                    help="re-prove byte conservation for an already-fragmented directory from its "
                         "_manifest.tsv and the files on disk. Prints a digest comparison; never "
                         "emits the reassembled text.")
    ap.add_argument("--grammar", choices=sorted(GRAMMARS))
    ap.add_argument("--out", type=Path, help="output directory for fragments (unused with --verify)")
    ap.add_argument(
        "--disambiguate",
        action="append",
        default=[],
        metavar="BASENAME",
        help="admit a KNOWN filename collision by suffixing -a/-b. Must name the exact "
             "basename. Repeatable. There is no global --force by design.",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if args.verify:
        return verify(args.source)
    if not args.grammar or not args.out:
        ap.error("--grammar and --out are required unless --verify is given")

    g = GRAMMARS[args.grammar]
    text = args.source.read_text(encoding="utf-8")
    entries = slice_source(text, g)

    # ---- map entries to filenames, detect collisions -------------------------
    names: dict[str, list[int]] = {}
    for i, (_s, _e, ident, _h) in enumerate(entries):
        names.setdefault(g.filename_fn(ident), []).append(i)

    collisions = {n: idxs for n, idxs in names.items() if len(idxs) > 1}
    admitted = set(args.disambiguate)
    unadmitted = sorted(set(collisions) - admitted)
    if unadmitted:
        print(f"[fragment] REFUSING TO WRITE — {len(unadmitted)} filename collision(s) in {args.source}:", file=sys.stderr)
        for n in unadmitted:
            print(f"  {n}", file=sys.stderr)
            for i in collisions[n]:
                ln = text.count("\n", 0, entries[i][0]) + 1
                print(f"      line {ln}: {entries[i][3][:110]}", file=sys.stderr)
        print(
            "\n  A collision means two entries claim one identity. That is the signal this\n"
            "  migration exists to produce — it is not noise. Either fix the source, or admit\n"
            "  each collision explicitly with --disambiguate <basename>.",
            file=sys.stderr,
        )
        return 1
    stale = sorted(admitted - set(collisions))
    if stale:
        # A --disambiguate that matches nothing is a prohibition satisfiable by
        # deletion in reverse: it would silently keep passing after the collision it
        # names is fixed, hiding that the escape hatch is no longer needed.
        print(f"[fragment] REFUSING TO WRITE — --disambiguate names {stale}, which is not a collision in {args.source}.", file=sys.stderr)
        return 1

    final: list[str] = [""] * len(entries)
    for n, idxs in names.items():
        if len(idxs) == 1:
            final[idxs[0]] = n
        else:
            stem = n[:-3]
            for k, i in enumerate(idxs):
                final[i] = f"{stem}-{chr(ord('a') + k)}.md"

    # ---- byte conservation ---------------------------------------------------
    slices, cursor = [], 0
    for (start, end, _ident, _h) in entries:
        if start > cursor:
            slices.append(("_nonentry", text[cursor:start]))
        slices.append(("entry", text[start:end]))
        cursor = end
    if cursor < len(text):
        slices.append(("_nonentry", text[cursor:]))

    rebuilt = "".join(s for _k, s in slices)
    src_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    rb_sha = hashlib.sha256(rebuilt.encode("utf-8")).hexdigest()
    if src_sha != rb_sha:
        print(f"[fragment] BYTE CONSERVATION FAILED for {args.source}: {src_sha} != {rb_sha}", file=sys.stderr)
        return 2

    print(f"[fragment] {args.source}")
    print(f"           entries={len(entries)}  fragments={len(final)}  "
          f"non-entry slices={sum(1 for k, _ in slices if k == '_nonentry')}")
    print(f"           sha256(source)={src_sha}")
    print(f"           sha256(concat slices)={rb_sha}  BYTE CONSERVATION OK")
    if collisions:
        print(f"           admitted collisions: {sorted(collisions)} -> -a/-b suffixes (preserved, not repaired)")

    if args.dry_run:
        return 0

    args.out.mkdir(parents=True, exist_ok=True)
    # VERBATIM slices -- deliberately NOT normalised. Normalising trailing newlines
    # would make on-disk reassembly non-byte-exact, reducing the conservation proof
    # to "the tool agrees with itself" instead of "the files on disk hold every byte
    # of the source".
    #
    # Non-entry content (preamble, "How to Write an Entry", trailing notes) is
    # written verbatim, one file per slice, and listed in the manifest. It is NOT
    # concatenated and NOT dropped -- dropping it would be the exact silent-deletion
    # class this migration removes, and concatenating it would lose the split.
    rows = []
    ei = ni = 0
    for kind, chunk in slices:
        if kind == "_nonentry":
            name = f"_nonentry-{ni:02d}.md"
            ni += 1
        else:
            name = final[ei]
            ei += 1
        (args.out / name).write_text(chunk, encoding="utf-8")
        rows.append(name)

    # The manifest records the source digest and the exact reassembly order so the
    # conservation proof can be re-run later against the files as committed -- see the
    # `--verify` mode, which reads ONLY this file and the fragments beside it and never
    # re-derives the slicing, so it cannot agree with the fragmenter by construction.
    #
    # `--verify` prints a digest comparison and never the reassembled text: a tool in
    # the tree that can emit a rollup is how a committed rollup eventually happens, and
    # a committed rollup would recreate the merge conflict this migration removes.
    with (args.out / "_manifest.tsv").open("w", encoding="utf-8") as fh:
        fh.write(f"#source\t{args.source}\n#sha256\t{src_sha}\n")
        for name in rows:
            fh.write(f"{name}\n")

    print(f"           wrote {len(final)} fragments + {ni} non-entry slice(s) to {args.out}/ (VERBATIM)")

    # ---- entry census, read BACK off disk -------------------------------------
    # Byte conservation cannot catch a heading swallowed into a neighbour's body:
    # every byte is still present, just in the wrong fragment. This re-parses the
    # WRITTEN files and compares their entry identifiers against the source's.
    #
    # It has to read from disk to mean anything. An earlier cut compared the source's
    # identifiers against themselves, which was both unreachable (a duplicate ident is
    # ALWAYS already a filename collision, refused above) and a check of nothing --
    # while the module docstring advertised it as one of three guarantees. A tool that
    # claims a check it does not perform is worse than one that claims nothing.
    src_idents = sorted(str(e[2]) for e in entries)
    frag_idents = []
    for name in final:
        body = (args.out / name).read_text(encoding="utf-8")
        for m in g.heading_re.finditer(body):
            frag_idents.append(str(g.ident_fn(m, body)))
    frag_idents.sort()
    if src_idents != frag_idents:
        only_src = [i for i in src_idents if i not in frag_idents]
        only_frag = [i for i in frag_idents if i not in src_idents]
        print(f"[fragment] CENSUS FAILED — identifiers on disk do not match the source.\n"
              f"           source={len(src_idents)} on-disk={len(frag_idents)}\n"
              f"           only in source: {only_src[:5]}\n"
              f"           only on disk:   {only_frag[:5]}", file=sys.stderr)
        return 2
    print(f"           census OK — {len(frag_idents)} entry identifiers re-read from disk match the source")
    return 0


if __name__ == "__main__":
    sys.exit(main())

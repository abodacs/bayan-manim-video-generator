#!/usr/bin/env python3
"""
Manim CE Course — zero-dependency static site generator (stdlib only).

Scans course/lessons/**, course/exams/**, course/capstone/**, validates every
quiz.json and *-gate.json against an inline schema, syntax-checks every scene.py
and example-*.py (via compile(), never executed), renders README markdown to
HTML, and builds:

  - index.html                         (landing, nav, prereq graph, assessment hub, progress)
  - lessons/<tier>/<id>/index.html     (per-lesson page: README + code + embedded quiz)
  - exams/<tier>-gate.html             (tier-gate exam, 85% threshold, 24h lockout)
  - capstone/<tier>/index.html         (capstone brief + rubric + model solution)

No network. No Manim/FFmpeg/LaTeX. No build server. No third-party packages.

Usage:
  python3 generator.py            # validate + build the site
  python3 generator.py --check    # validate + syntax-check only (CI gate)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

TIER_NAME = {1: "Beginner", 2: "Intermediate", 3: "Advanced", 4: "Master"}
TIER_DIR = {1: "beginner", 2: "intermediate", 3: "advanced", 4: "master"}
TIER_COLOR = {1: "#1d8ac0", 2: "#2f8f4e", 3: "#8a4bb0", 4: "#b26a00"}
# Lesson lifecycle states; the status also names a status-pill CSS class, so
# an unknown value is a content error, not a free-text field.
STATUSES = {"draft", "planned", "reviewed", "done"}
BLOOM_LEVELS = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
ITEM_TYPES = {
    "single-choice",
    "multi-select",
    "fill-blank",
    "predict-output",
    "bug-spot",
    "code-ordering",
    "create",
}


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.notes = []

    def err(self, where, msg):
        self.errors.append("[ERROR] %s: %s" % (where, msg))

    def warn(self, where, msg):
        self.warnings.append("[warn] %s: %s" % (where, msg))

    def note(self, msg):
        self.notes.append(msg)

    def ok(self):
        return not self.errors


R = Report()


# --------------------------------------------------------------------------- #
# Minimal markdown -> HTML
# --------------------------------------------------------------------------- #
def esc(s):
    # Quotes too: esc() output lands in double-quoted attributes
    # (class="status-pill ...", data-score="...") as well as text nodes.
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def json_for_script(obj):
    """JSON for embedding inside <script type="application/json">.

    The HTML parser never enters JSON mode: a literal "</" in any field would
    terminate the script block early and corrupt the page. "<\\/" is a valid
    JSON escape that parses back to "</" — quiz.js JSON.parses these blocks,
    so behaviour is unchanged for well-formed content.
    """
    return json.dumps(obj).replace("</", "<\\/")


def inline(t):
    """Render inline markdown (escapes first; protects code spans)."""
    t = esc(t)
    stash = []

    def grab(m):
        stash.append(m.group(1))
        return "\x00%d\x00" % (len(stash) - 1)

    t = re.sub(r"`([^`]+)`", grab, t)
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", t)

    def restore(m):
        return "<code>%s</code>" % stash[int(m.group(1))]

    t = re.sub(r"\x00(\d+)\x00", restore, t)
    return t


_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_HR = re.compile(r"^---+\s*$")
_UL = re.compile(r"^\s*[-*]\s+(.*)$")
_OL = re.compile(r"^\s*\d+\.\s+(.*)$")
_QUOTE = re.compile(r"^>\s?(.*)$")
_FENCE = re.compile(r"^```(.*)$")
_TBL_SEP = re.compile(r"^[\s|:-]+$")


def md_to_html(md):
    lines = md.split("\n")
    out, i = [], 0
    n = len(lines)
    state = {"ul": False, "ol": False}

    def close():
        if state["ul"]:
            out.append("</ul>")
            state["ul"] = False
        if state["ol"]:
            out.append("</ol>")
            state["ol"] = False

    def is_break(lx):
        return bool(
            _HEADING.match(lx)
            or _HR.match(lx)
            or _FENCE.match(lx.strip())
            or _UL.match(lx)
            or _OL.match(lx)
            or _QUOTE.match(lx)
        )

    while i < n:
        line = lines[i]
        m = _FENCE.match(line.strip())
        if m:
            lang = m.group(1).strip() or "text"
            close()
            code, i = [], i + 1
            while i < n and not _FENCE.match(lines[i].strip()):
                code.append(lines[i])
                i += 1
            i += 1
            out.append(
                '<pre class="code"><code class="language-%s">%s</code></pre>'
                % (esc(lang), esc("\n".join(code)))
            )
            continue
        m = _HEADING.match(line)
        if m:
            close()
            lvl = len(m.group(1))
            out.append("<h%d>%s</h%d>" % (lvl, inline(m.group(2)), lvl))
            i += 1
            continue
        if _HR.match(line):
            close()
            out.append('<hr class="soft">')
            i += 1
            continue
        if line.startswith(">"):
            close()
            q, i = [], i
            while i < n and lines[i].startswith(">"):
                q.append(_QUOTE.match(lines[i]).group(1))
                i += 1
            out.append("<blockquote>%s</blockquote>" % inline(" ".join(q)))
            continue
        if "|" in line and i + 1 < n and _TBL_SEP.match(lines[i + 1]) and "|" in lines[i + 1]:
            close()
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            t = ['<table class="kvtable"><thead><tr>']
            t.append("".join("<th>%s</th>" % inline(h) for h in header))
            t.append("</tr></thead><tbody>")
            for r in rows:
                t.append("<tr>" + "".join("<td>%s</td>" % inline(c) for c in r) + "</tr>")
            t.append("</tbody></table>")
            out.append("".join(t))
            continue
        m = _UL.match(line)
        if m:
            if not state["ul"]:
                close()
                out.append("<ul>")
                state["ul"] = True
            out.append("<li>%s</li>" % inline(m.group(1)))
            i += 1
            continue
        m = _OL.match(line)
        if m:
            if not state["ol"]:
                close()
                out.append("<ol>")
                state["ol"] = True
            out.append("<li>%s</li>" % inline(m.group(1)))
            i += 1
            continue
        if line.strip() == "":
            close()
            i += 1
            continue
        close()
        para = [line.strip()]
        i += 1
        while i < n and lines[i].strip() != "" and not is_break(lines[i]):
            if (
                "|" in lines[i]
                and i + 1 < n
                and _TBL_SEP.match(lines[i + 1])
                and "|" in lines[i + 1]
            ):
                break
            para.append(lines[i].strip())
            i += 1
        out.append("<p>%s</p>" % inline(" ".join(para)))
    close()
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Quiz / gate schema validation
# --------------------------------------------------------------------------- #
def regex_answer_errs(answer, item_id):
    """Check a {regex:..} answer compiles before it reaches the browser.

    quiz.js hands the pattern straight to new RegExp(...) inside score(); an
    invalid pattern there breaks the whole quiz at submit time, not just this
    item. Python's re.compile accepts the same syntax for the patterns a quiz
    author would write, so reject at the gate.
    """
    if not isinstance(answer, dict):
        return []
    rx = answer.get("regex")
    if not isinstance(rx, str):
        return ["item %r regex answer must be a string" % item_id]
    try:
        re.compile(rx)
    except re.error as e:
        return ["item %r has invalid regex %r: %s" % (item_id, rx, e)]
    return []


def validate_item(it):
    errs = []
    for k in ("id", "type", "bloom", "prompt", "explanation", "ref"):
        if k not in it or it[k] in ("", None):
            errs.append("item %r missing/empty '%s'" % (it.get("id", "?"), k))
    ty = it.get("type")
    if ty not in ITEM_TYPES:
        errs.append("item %r has invalid type %r" % (it.get("id", "?"), ty))
    if it.get("bloom") not in BLOOM_LEVELS:
        errs.append("item %r has invalid bloom %r" % (it.get("id", "?"), it.get("bloom")))
    if ty == "single-choice":
        if not isinstance(it.get("options"), list) or len(it.get("options")) < 2:
            errs.append("single-choice %r needs >=2 options" % it.get("id"))
        if not isinstance(it.get("answer"), int):
            errs.append("single-choice %r answer must be int index" % it.get("id"))
        elif isinstance(it.get("options"), list) and not (0 <= it["answer"] < len(it["options"])):
            errs.append("single-choice %r answer index out of range" % it.get("id"))
    elif ty == "multi-select":
        if not isinstance(it.get("options"), list) or len(it.get("options")) < 2:
            errs.append("multi-select %r needs >=2 options" % it.get("id"))
        if not isinstance(it.get("answer"), list) or not it.get("answer"):
            errs.append("multi-select %r answer must be non-empty [int]" % it.get("id"))
        elif isinstance(it.get("options"), list) and not all(
            isinstance(x, int) and not isinstance(x, bool) and 0 <= x < len(it["options"])
            for x in it["answer"]
        ):
            # quiz.js can never match out-of-range or non-int indexes: the
            # item would be permanently unscorable and a gate would mis-score.
            errs.append("multi-select %r answer must be int indexes into options" % it.get("id"))
    elif ty == "fill-blank":
        a = it.get("answer")
        if not (isinstance(a, str) or (isinstance(a, dict) and a.get("regex"))):
            errs.append("fill-blank %r answer must be str or {regex:..}" % it.get("id"))
        else:
            errs.extend(regex_answer_errs(a, it.get("id")))
    elif ty == "predict-output":
        if not it.get("code"):
            errs.append("predict-output %r needs 'code'" % it.get("id"))
        a = it.get("answer")
        if not (isinstance(a, str) or (isinstance(a, dict) and a.get("regex"))):
            errs.append("predict-output %r answer must be str or {regex:..}" % it.get("id"))
        else:
            errs.extend(regex_answer_errs(a, it.get("id")))
    elif ty == "bug-spot":
        if not it.get("code"):
            errs.append("bug-spot %r needs 'code'" % it.get("id"))
        if not isinstance(it.get("brokenLine"), int):
            errs.append("bug-spot %r needs int 'brokenLine'" % it.get("id"))
        if not isinstance(it.get("options"), list) or len(it.get("options")) < 2:
            errs.append("bug-spot %r needs >=2 fix options" % it.get("id"))
        if not isinstance(it.get("answer"), int):
            errs.append("bug-spot %r answer must be int fix index" % it.get("id"))
    elif ty == "code-ordering":
        if not isinstance(it.get("options"), list) or len(it.get("options")) < 2:
            errs.append("code-ordering %r needs >=2 options" % it.get("id"))
        if not isinstance(it.get("answer"), list):
            errs.append("code-ordering %r answer must be [perm]" % it.get("id"))
        elif sorted(it["answer"]) != list(range(len(it.get("options", [])))):
            errs.append(
                "code-ordering %r answer must be a permutation of option indices" % it.get("id")
            )
    elif ty == "create":
        if not it.get("modelAnswer"):
            errs.append("create %r needs 'modelAnswer'" % it.get("id"))
        if not isinstance(it.get("rubric"), list) or not it.get("rubric"):
            errs.append("create %r needs non-empty 'rubric'" % it.get("id"))
    return errs


def validate_assessment(obj, where, kind):
    errs = []
    if not isinstance(obj, dict):
        return ["%s: root is not an object" % where]
    for k in ("id", "title", "items"):
        if k not in obj:
            errs.append("%s: missing '%s'" % (where, k))
    if "kind" in obj and obj["kind"] != kind:
        errs.append("%s: kind=%r expected %r" % (where, obj.get("kind"), kind))
    items = obj.get("items")
    if not isinstance(items, list) or not items:
        errs.append("%s: 'items' must be a non-empty list" % where)
        return errs
    ids, blooms = set(), set()
    for it in items:
        if not isinstance(it, dict):
            errs.append("%s: item is not an object" % where)
            continue
        for e in validate_item(it):
            errs.append("%s: %s" % (where, e))
        if it.get("id") in ids:
            errs.append("%s: duplicate item id %r" % (where, it.get("id")))
        ids.add(it.get("id"))
        if it.get("bloom") in BLOOM_LEVELS:
            blooms.add(it["bloom"])
    if kind == "quiz":
        if len(items) < 6:
            errs.append("%s: quiz needs >=6 items (has %d)" % (where, len(items)))
        missing = set(BLOOM_LEVELS) - blooms
        if missing:
            errs.append("%s: quiz missing Bloom levels: %s" % (where, sorted(missing)))
    elif kind == "gate":
        if not (15 <= len(items) <= 25):
            errs.append("%s: gate must have 15-25 items (has %d)" % (where, len(items)))
        thr = obj.get("threshold")
        if thr is None:
            obj["threshold"] = 0.85
        elif not isinstance(thr, (int, float)) or not (0 < thr <= 1):
            errs.append("%s: gate 'threshold' must be in (0,1]" % where)
        if any(it.get("type") == "create" for it in items):
            errs.append("%s: gates must not contain 'create' items (must be auto-scored)" % where)
        missing = set(BLOOM_LEVELS) - blooms
        if missing:
            R.warn(where, "missing Bloom levels: %s (recommended)" % sorted(missing))
    return errs


# --------------------------------------------------------------------------- #
# Syntax check (compile only — never execute)
# --------------------------------------------------------------------------- #
def syntax_check(path):
    try:
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        compile(src, path, "exec")
        return True, ""
    except (SyntaxError, OSError, UnicodeDecodeError) as e:
        return False, str(e)


def write_page(path, html):
    # End every file with a newline: pre-commit's end-of-file-fixer enforces
    # it, and committed pages must byte-match a fresh generator run.
    if not html.endswith("\n"):
        html += "\n"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)


# --------------------------------------------------------------------------- #
# Page shell
# --------------------------------------------------------------------------- #
def page(title, body, assets, home, active=None, extra_js=""):
    nav_items = [
        ("Course", home + "index.html"),
        ("Assessment hub", home + "index.html#assessment-hub"),
        ("How to run a scene", home + "index.html#run-a-scene"),
    ]
    nav = "".join(
        '<a href="%s"%s>%s</a>' % (href, ' class="active"' if label == active else "", label)
        for label, href in nav_items
    )
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>%s — Manim CE Course</title>\n"
        '<link rel="stylesheet" href="%sapp.css">\n'
        "</head>\n<body>\n"
        '<header class="site"><div class="shell">\n'
        '  <a class="brand" href="%sindex.html">Manim&nbsp;CE <span class="dot">▮</span> Beginner&nbsp;→&nbsp;Master</a>\n'
        "  <nav>%s</nav>\n"
        '</div></header>\n<main class="shell">\n%s\n</main>\n'
        '<footer class="site"><div class="shell">\n'
        "  Generated offline by <code>generator.py</code> from <code>course/</code> folders.\n"
        "  Grounded in <code>.agents/skills/manim-video/</code>. Manim Community Edition &ge; 0.20.1.\n"
        "</div></footer>\n"
        '<script src="%shl.js"></script>\n<script src="%squiz.js"></script>\n%s'
        "</body>\n</html>"
    ) % (esc(title), assets, home, nav, body, assets, assets, extra_js)


def code_block(code, filename=None, lang="python"):
    fn = '<span class="filename">%s</span>' % esc(filename) if filename else ""
    return '<pre class="code">%s<code class="language-%s">%s</code></pre>' % (fn, lang, esc(code))


# --------------------------------------------------------------------------- #
# Scanning
# --------------------------------------------------------------------------- #
def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def read_lesson(tier, lesson_dir):
    where = "lessons/%s/%s" % (TIER_DIR[tier], os.path.basename(lesson_dir))
    status_path = os.path.join(lesson_dir, "status.json")
    readme_path = os.path.join(lesson_dir, "README.md")
    quiz_path = os.path.join(lesson_dir, "assessment", "quiz.json")
    status = load_json(status_path) if os.path.exists(status_path) else {}
    readme = open(readme_path, encoding="utf-8").read() if os.path.exists(readme_path) else ""
    body_html = md_to_html(readme)
    if status.get("status", "draft") not in STATUSES:
        R.err(
            where,
            "unknown status %r (expected one of %s)"
            % (status.get("status"), "|".join(sorted(STATUSES))),
        )

    lid = os.path.basename(lesson_dir)
    code_files = {}
    for fn in ("scene.py", "example-practical.py", "example-production.py"):
        p = os.path.join(lesson_dir, fn)
        if os.path.exists(p):
            ok, err = syntax_check(p)
            if not ok:
                R.err("%s/%s" % (where, fn), "syntax error: %s" % err)
            code_files[fn] = open(p, encoding="utf-8").read()

    quiz = None
    if os.path.exists(quiz_path):
        try:
            quiz = load_json(quiz_path)
            quiz.setdefault("kind", "quiz")
            quiz.setdefault("id", lid)
            quiz.setdefault("tier", tier)
            for e in validate_assessment(quiz, "%s/assessment/quiz.json" % where, "quiz"):
                R.err("%s/assessment/quiz.json" % where, e)
        except Exception as e:
            R.err("%s/assessment/quiz.json" % where, "could not parse: %s" % e)
    else:
        R.err(where, "missing assessment/quiz.json")

    return {
        "id": lid,
        "tier": tier,
        "tierName": TIER_NAME[tier],
        "slug": lid,
        "title": status.get("title") or lid,
        "status": status.get("status", "draft"),
        "objective": status.get("objective", ""),
        "misconception": status.get("misconception", ""),
        "prereqs": status.get("prereqs", []),
        "ref": status.get("ref", ""),
        "body_html": body_html,
        "code_files": code_files,
        "quiz": quiz,
        "url": "lessons/%s/%s/index.html" % (TIER_DIR[tier], lid),
        "dir": lesson_dir,
    }


def read_gate(tier, path):
    where = "exams/%s-gate.json" % TIER_DIR[tier]
    try:
        gate = load_json(path)
        gate.setdefault("kind", "gate")
        gate.setdefault("tier", tier)
        gate.setdefault("threshold", 0.85)
        gate.setdefault("lockoutHours", 24)
        for e in validate_assessment(gate, where, "gate"):
            R.err(where, e)
        return gate
    except Exception as e:
        R.err(where, "could not parse: %s" % e)
        return None


def read_capstone(tier, cdir):
    where = "capstone/%s" % tier
    brief_p = os.path.join(cdir, "brief.md")
    rubric_p = os.path.join(cdir, "rubric.md")
    brief = open(brief_p, encoding="utf-8").read() if os.path.exists(brief_p) else ""
    rubric = open(rubric_p, encoding="utf-8").read() if os.path.exists(rubric_p) else ""
    solution = {}
    sdir = os.path.join(cdir, "solution")
    if os.path.isdir(sdir):
        for fn in sorted(os.listdir(sdir)):
            p = os.path.join(sdir, fn)
            if fn.endswith(".py"):
                ok, err = syntax_check(p)
                if not ok:
                    R.err("%s/solution/%s" % (where, fn), "syntax error: %s" % err)
                solution[fn] = open(p, encoding="utf-8").read()
            elif fn.endswith(".md"):
                solution[fn] = open(p, encoding="utf-8").read()
    return {
        "tier": tier,
        "brief_html": md_to_html(brief),
        "rubric_html": md_to_html(rubric),
        "solution": solution,
        "url": "capstone/%s/index.html" % tier,
        "dir": cdir,
    }


# --------------------------------------------------------------------------- #
# Rendering: lesson, gate, capstone
# --------------------------------------------------------------------------- #
def render_lesson(lesson, lessons_by_id):
    assets = "../../../assets/"
    home = "../../../"
    prereq_links = (
        ", ".join(
            '<a href="../%s/index.html">%s</a>'
            % (lessons_by_id[p]["id"], esc(lessons_by_id[p]["title"]))
            for p in lesson["prereqs"]
            if p in lessons_by_id
        )
        or "<span class='muted'>none — this is the entry point</span>"
    )

    files_html = ""
    for fn in ("scene.py", "example-practical.py", "example-production.py"):
        if fn in lesson["code_files"]:
            files_html += "<h3>%s</h3>" % esc(fn) + code_block(lesson["code_files"][fn], fn)

    quiz_json = json_for_script(lesson["quiz"]) if lesson["quiz"] else "{}"

    body = (
        '<section class="hero" style="padding:32px 0 18px">\n'
        '  <div class="accent-bar" style="background:%s;"></div>\n'
        '  <p class="muted" style="margin:0">Tier %d · %s · '
        '<span class="status-pill %s">%s</span></p>\n'
        "  <h1>%s</h1>\n"
        '  <p class="promise">%s</p>\n'
        '  <div class="lesson-head" style="margin-top:10px">\n'
        '    <p class="meta-line"><strong>Misconception it kills:</strong> '
        '<span class="misconception">%s</span></p>\n'
        '    <p class="meta-line"><strong>Prerequisites:</strong> %s</p>\n'
        '    <p class="meta-line"><strong>Source reference:</strong> <code>%s</code></p>\n'
        '    <p class="meta-line"><a href="README.md">raw README.md</a> · '
        '<a href="plan.md">plan.md</a> · <a href="exercises.md">exercises.md</a></p>\n'
        "  </div>\n</section>\n\n"
        '<section class="block" style="padding-top:18px"><article class="lesson-doc">%s</article></section>\n\n'
        '<section class="block"><h2>Runnable files</h2>\n'
        '<p class="lede">Copy any block, save it locally, and render with the command in '
        '<a href="%sindex.html#run-a-scene">How to run a scene</a>.</p>\n%s</section>\n\n'
        '<section class="block" id="take-quiz"><h2>Assessment</h2>\n'
        '<p class="lede">Bloom-laddered (Remember → Create). Explanations appear only after you answer. '
        "Create items are self-assessed against a model answer.</p>\n"
        '<div id="assessment"></div>\n'
        '<script type="application/json" id="quiz-data">%s</script>\n</section>\n'
    ) % (
        TIER_COLOR[lesson["tier"]],
        lesson["tier"],
        esc(lesson["tierName"]),
        esc(lesson["status"]),
        esc(lesson["status"]),
        esc(lesson["title"]),
        esc(lesson["objective"]),
        esc(lesson["misconception"]),
        prereq_links,
        esc(lesson["ref"]),
        lesson["body_html"],
        home,
        files_html,
        quiz_json,
    )
    html = page(lesson["title"], body, assets, home, active="Course")
    out = os.path.join(lesson["dir"], "index.html")
    write_page(out, html)
    return out


def render_gate(gate, tier):
    if not gate:
        return None
    assets = "../assets/"
    home = "../"
    data = json_for_script(gate)
    next_name = TIER_NAME.get(tier + 1, "next")
    body = (
        '<section class="hero" style="padding:32px 0 18px">\n'
        '  <div class="accent-bar" style="background:%s;"></div>\n'
        '  <p class="muted" style="margin:0">Tier %d gate · %s</p>\n'
        "  <h1>%s Tier Gate</h1>\n"
        '  <p class="promise">Score &ge; 85%% to unlock the %s tier. One attempt per 24 hours; '
        "cumulative re-test is allowed.</p>\n</section>\n"
        '<section class="block"><div id="assessment"></div>\n'
        '<script type="application/json" id="exam-data">%s</script>\n</section>\n'
    ) % (TIER_COLOR[tier], tier, esc(TIER_NAME[tier]), esc(TIER_NAME[tier]), esc(next_name), data)
    html = page("%s Gate" % TIER_NAME[tier], body, assets, home, active="Course")
    out = os.path.join(HERE, "exams", "%s-gate.html" % TIER_DIR[tier])
    write_page(out, html)
    return out


def render_capstone(capstone, tier):
    assets = "../../assets/"
    home = "../../"
    sol_html = ""
    model_py = ""
    for fn, content in capstone["solution"].items():
        if fn.endswith(".py"):
            if not model_py:
                model_py = content
            sol_html += "<h3>%s</h3>" % esc(fn) + code_block(content, fn)
        else:
            sol_html += md_to_html(content)
    cap_data = json_for_script(
        {
            "kind": "capstone",
            "id": "capstone-%s" % tier,
            "tier": tier,
            "title": "%s capstone" % TIER_NAME[tier],
            "items": [
                {
                    "id": "capstone-self",
                    "type": "create",
                    "bloom": "Create",
                    "prompt": "Build the capstone described in the brief, then self-assess against the rubric.",
                    "modelAnswer": model_py or "# model solution in solution/",
                    "rubric": [
                        {
                            "criterion": "Meets every criterion in the published rubric.",
                            "weight": 100,
                        }
                    ],
                    "explanation": "Open-ended. Compare honestly to the model solution.",
                    "ref": "capstone/%s/rubric.md" % tier,
                }
            ],
        }
    )
    body = (
        '<section class="hero" style="padding:32px 0 18px">\n'
        '  <div class="accent-bar" style="background:%s;"></div>\n'
        '  <p class="muted" style="margin:0">Tier %d capstone · %s</p>\n'
        "  <h1>%s Capstone</h1>\n"
        '  <p class="promise">An open-ended build graded by a published rubric. Submit a self-assessment when done.</p>\n'
        "</section>\n"
        '<section class="block capstone-section"><h2>Brief</h2>%s</section>\n'
        '<section class="block capstone-section"><h2>Rubric</h2>%s</section>\n'
        '<section class="block capstone-section"><h2>Submit your self-assessment</h2>\n'
        '<p class="lede">Paste your scene, reveal the model solution, then score yourself 0–100 against the rubric.</p>\n'
        '<div id="assessment"></div>\n'
        '<script type="application/json" id="capstone-data">%s</script>\n</section>\n'
        '<section class="block capstone-section"><h2>Model solution</h2>%s</section>\n'
    ) % (
        TIER_COLOR[tier],
        tier,
        esc(TIER_NAME[tier]),
        esc(TIER_NAME[tier]),
        capstone["brief_html"],
        capstone["rubric_html"],
        cap_data,
        sol_html or '<p class="muted">No model solution provided.</p>',
    )
    html = page("%s Capstone" % TIER_NAME[tier], body, assets, home, active="Course")
    out = os.path.join(capstone["dir"], "index.html")
    write_page(out, html)
    return out


# --------------------------------------------------------------------------- #
# Index (plain template + placeholder replacement — no f-string for JS)
# --------------------------------------------------------------------------- #
INDEX_TEMPLATE = """<section class="hero">
  <div class="accent-bar"></div>
  <h1>Manim Community Edition, Beginner&nbsp;&rarr;&nbsp;Master</h1>
  <p class="promise">A rigorous, self-contained, browser-based course grounded in this repo's own
  <code>.agents/skills/manim-video/</code>. Write grounded, render-ready scenes that pass real
  security, math, layout, and production gates &mdash; not just code that runs.</p>
</section>

<section class="block">
  <div class="progress" id="progress-panel">
    <div class="row"><span><strong>Your progress</strong> <span class="muted">(stored only in this browser)</span></span><span id="overall"></span></div>
    <div class="bar"><span id="bar-fill"></span></div>
    <div class="row"><span>Lessons completed</span><span id="stat-lessons">&mdash;</span></div>
    <div class="row"><span>Quizzes passed (&ge;70%)</span><span id="stat-quizzes">&mdash;</span></div>
    <div class="row"><span>Tier gates passed (&ge;85%)</span><span id="stat-gates">&mdash;</span></div>
    <div class="row"><span>Capstones submitted</span><span id="stat-caps">&mdash;</span></div>
    <div class="row"><span>Tier unlocked</span><span id="stat-unlocked">&mdash;</span></div>
  </div>
</section>

<section class="block">
  <h2>Tiers</h2>
  <p class="lede">Each tier's lessons unlock when the previous tier's gate is passed (&ge; 85%).</p>
  <div class="tiers">@@CARDS@@</div>
</section>

<section class="block">
  <h2>Lessons</h2>
  <p class="lede">@@LESSONCOUNT@@ lessons across four tiers. Each has a runnable scene, two worked examples, exercises, and a Bloom-laddered quiz.</p>
  @@LIST@@
</section>

<section class="block" id="assessment-hub">
  <h2>Assessment hub</h2>
  <p class="lede">Per-lesson quizzes, four tier gates (85% to advance), and four capstones.</p>
  <ul class="lessons">
    <li class="lesson"><div class="num">Q</div><div class="t"><h3>Per-lesson quizzes</h3><p class="obj">Linked from each lesson above (Take quiz).</p></div><div class="actions"><a class="btn subtle" href="#tier-1">jump to lessons</a></div></li>
    <li class="lesson"><div class="num">G</div><div class="t"><h3>Tier gates</h3><p class="obj">85% to unlock the next tier; one attempt per 24h.</p></div><div class="actions">@@GATES@@</div></li>
    <li class="lesson"><div class="num">C</div><div class="t"><h3>Capstones</h3><p class="obj">Open-ended builds graded by a published rubric. Tier 4 = research-paper-explainer.</p></div><div class="actions">@@CAPS@@</div></li>
  </ul>
</section>

<section class="block">
  <h2>Prerequisite graph</h2>
  <div class="prereqs measure">@@GRAPH@@</div>
</section>

<section class="block" id="run-a-scene">
  <h2>How to run a scene locally</h2>
  <p class="lede">The course never renders inside your browser &mdash; scenes are real Manim Python you run yourself.</p>
  @@SHELL@@
  <p>LaTeX is only required for <code>MathTex</code>/<code>Tex</code>/<code>Matrix</code>, numbered axes, and <code>DecimalNumber</code>/<code>Integer</code>. The course shows no-LaTeX fallbacks where LaTeX is unavailable.</p>
</section>

<script type="application/json" id="manifest">@@MANIFEST@@</script>
"""


def render_index(lessons, gates, capstones):
    assets = "assets/"
    lessons_by_id = {l["id"]: l for l in lessons}

    # tier cards
    cards = []
    for tier in (1, 2, 3, 4):
        tlessons = [l for l in lessons if l["tier"] == tier]
        gate_url = gates.get(tier, {}).get("url", "#")
        cap_url = capstones.get(tier, {}).get("url", "#")
        cards.append(
            '<div class="tier-card t%d" data-tier="%d">'
            '<div class="stripe"></div>'
            "<h3>Tier %d · %s</h3>"
            '<p class="sub">%d lessons</p>'
            '<p class="meta"><a href="#tier-%d">lessons</a> · '
            '<a href="%s">gate</a> · <a href="%s">capstone</a></p>'
            '<p class="meta"><span class="locktag" data-locktier="%d">locked</span></p>'
            "</div>"
            % (tier, tier, tier, TIER_NAME[tier], len(tlessons), tier, gate_url, cap_url, tier)
        )
    cards_html = "".join(cards)

    # lesson list grouped by tier
    list_parts = []
    for tier in (1, 2, 3, 4):
        tlessons = [l for l in lessons if l["tier"] == tier]
        rows = []
        for l in tlessons:
            prereq_txt = (
                ", ".join(
                    '<a href="#%s">%s</a>'
                    % (lessons_by_id[p]["id"], esc(lessons_by_id[p]["title"]))
                    for p in l["prereqs"]
                    if p in lessons_by_id
                )
                or '<span class="muted">none</span>'
            )
            num = esc(l["id"].split("-")[0])
            rows.append(
                '<li class="lesson" id="%s" data-tier="%d" data-id="%s">'
                '<div class="num">%s</div>'
                '<div class="t"><h3><a href="%s">%s</a></h3>'
                '<p class="obj">%s</p>'
                '<p class="ref">prereqs: %s · ref <code>%s</code></p></div>'
                '<div class="actions"><span class="status-pill %s">%s</span>'
                '<a class="btn" href="%s#take-quiz">Take quiz</a>'
                '<span class="score-chip" data-score="%s"></span></div>'
                "</li>"
                % (
                    l["id"],
                    l["tier"],
                    l["id"],
                    num,
                    l["url"],
                    esc(l["title"]),
                    esc(l["objective"]),
                    prereq_txt,
                    esc(l["ref"]),
                    esc(l["status"]),
                    esc(l["status"]),
                    l["url"],
                    l["id"],
                )
            )
        list_parts.append(
            '<div id="tier-%d"><h3 class="muted" style="margin-top:24px">Tier %d · %s</h3>'
            '<ul class="lessons">%s</ul></div>' % (tier, tier, TIER_NAME[tier], "".join(rows))
        )
    list_html = "".join(list_parts)

    # prerequisite graph
    graph = ["<ul>"]
    for l in lessons:
        deps = [lessons_by_id[p]["title"] for p in l["prereqs"] if p in lessons_by_id]
        label = '<a href="%s">%s</a>' % (l["url"], esc(l["title"]))
        if deps:
            graph.append(
                "<li>%s<ul>" % label + "".join("<li>%s</li>" % esc(d) for d in deps) + "</ul></li>"
            )
        else:
            graph.append("<li>%s</li>" % label)
    graph.append("</ul>")
    graph_html = "\n".join(graph)

    # assessment hub gate/capstone buttons
    gates_btns = "".join(
        '<a class="btn" href="%s">%s</a>' % (gates[t]["url"], TIER_NAME[t])
        for t in (1, 2, 3, 4)
        if gates.get(t)
    )
    caps_btns = "".join(
        '<a class="btn subtle" href="%s">%s</a>' % (capstones[t]["url"], TIER_NAME[t])
        for t in (1, 2, 3, 4)
        if capstones.get(t)
    )

    shell_snippet = code_block(
        "pip install manim            # Manim Community Edition >= 0.20.1\n"
        "manim -ql scene.py MyScene   # low-quality draft (fast)\n"
        "manim -qh scene.py MyScene   # production quality (after review)\n"
        "manim -ql --format=png -s scene.py MyScene   # single still preview",
        "shell",
        lang="bash",
    )

    manifest = {
        "tiers": [
            {
                "tier": t,
                "name": TIER_NAME[t],
                "lessons": [l["id"] for l in lessons if l["tier"] == t],
                "gate": gates.get(t, {}).get("url"),
                "capstone": capstones.get(t, {}).get("url"),
            }
            for t in (1, 2, 3, 4)
        ],
        "lessons": [
            {
                "id": l["id"],
                "tier": l["tier"],
                "title": l["title"],
                "status": l["status"],
                "url": l["url"],
                "prereqs": l["prereqs"],
                "ref": l["ref"],
            }
            for l in lessons
        ],
    }

    index_js = (
        "(function () {\n"
        "  function el(id) { return document.getElementById(id); }\n"
        "  var P = window.ManimProgress;\n"
        "  if (!P) return;\n"
        "  var manifest = JSON.parse(document.getElementById('manifest').textContent);\n"
        "  manifest.lessons.forEach(function (l) {\n"
        "    var chip = document.querySelector('.score-chip[data-score=\"' + l.id + '\"]');\n"
        "    var pct = P.quizPct(l.id);\n"
        "    if (chip && pct != null) { chip.textContent = pct + '%' + (pct >= 70 ? ' \\u2713' : '');\n"
        "      if (pct >= 70) chip.classList.add('pass'); }\n"
        "  });\n"
        "  function tierOpen(t) { return P.gateUnlocked(t); }\n"
        "  document.querySelectorAll('[data-locktier]').forEach(function (node) {\n"
        "    var t = +node.dataset.locktier; var open = tierOpen(t);\n"
        "    node.textContent = open ? 'unlocked' : 'locked';\n"
        "    node.closest('.tier-card').classList.toggle('unlocked', open);\n"
        "    node.closest('.tier-card').classList.toggle('locked', !open);\n"
        "  });\n"
        "  document.querySelectorAll('li.lesson').forEach(function (li) {\n"
        "    var t = +li.dataset.tier;\n"
        "    if (t > 1 && !tierOpen(t)) li.classList.add('locked');\n"
        "  });\n"
        "  var done = 0, qpass = 0, caps = 0, gatesPassed = 0, maxTier = 1;\n"
        "  manifest.lessons.forEach(function (l) {\n"
        "    if (P.lessonDone(l.id)) done++;\n"
        "    var pct = P.quizPct(l.id); if (pct != null && pct >= 70) qpass++;\n"
        "  });\n"
        "  [1,2,3,4].forEach(function (t) { if (P.gatePassed(t)) { gatesPassed++; maxTier = Math.max(maxTier, t+1); } });\n"
        "  [1,2,3,4].forEach(function (t) { if (P.capstoneSubmitted(t)) caps++; });\n"
        "  var unlocked = Math.min(4, maxTier);\n"
        "  el('stat-lessons').textContent = done + ' / ' + manifest.lessons.length;\n"
        "  el('stat-quizzes').textContent = qpass + ' / ' + manifest.lessons.length;\n"
        "  el('stat-gates').textContent = gatesPassed + ' / 4';\n"
        "  el('stat-caps').textContent = caps + ' / 4';\n"
        "  el('stat-unlocked').textContent = 'Tier ' + unlocked + ' (' + ['','Beginner','Intermediate','Advanced','Master'][unlocked] + ')';\n"
        "  var total = manifest.lessons.length + 4 + 4;\n"
        "  var got = done + gatesPassed + caps;\n"
        "  el('overall').textContent = Math.round(100 * got / total) + '%';\n"
        "  el('bar-fill').style.width = Math.round(100 * got / total) + '%';\n"
        "})();\n"
    )

    body = (
        INDEX_TEMPLATE.replace("@@CARDS@@", cards_html)
        .replace("@@LESSONCOUNT@@", str(len(lessons)))
        .replace("@@LIST@@", list_html)
        .replace("@@GRAPH@@", graph_html)
        .replace("@@GATES@@", gates_btns)
        .replace("@@CAPS@@", caps_btns)
        .replace("@@SHELL@@", shell_snippet)
        .replace("@@MANIFEST@@", json_for_script(manifest))
    )

    # The index dashboard reads window.ManimProgress, which quiz.js defines —
    # so this script must load AFTER quiz.js (page() appends extra_js last).
    # Inline in <main> it ran at parse time, found nothing, and silently
    # disabled the whole progress dashboard.
    index_script = "<script>\n%s\n</script>\n" % index_js
    html = page("Manim CE Course", body, assets, home="", extra_js=index_script)
    out = os.path.join(HERE, "index.html")
    write_page(out, html)
    return out


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Manim CE course generator (zero-dep).")
    ap.add_argument(
        "--check", action="store_true", help="validate + syntax-check only; do not write pages"
    )
    args = ap.parse_args()

    lessons_dir = os.path.join(HERE, "lessons")
    exams_dir = os.path.join(HERE, "exams")
    capstone_dir = os.path.join(HERE, "capstone")

    lessons = []
    if os.path.isdir(lessons_dir):
        for tier in (1, 2, 3, 4):
            tdir = os.path.join(lessons_dir, TIER_DIR[tier])
            if not os.path.isdir(tdir):
                continue
            for name in sorted(os.listdir(tdir)):
                ld = os.path.join(tdir, name)
                if os.path.isdir(ld) and os.path.exists(os.path.join(ld, "status.json")):
                    lessons.append(read_lesson(tier, ld))
    else:
        R.err("lessons/", "no lessons/ directory found")

    gates = {}
    if os.path.isdir(exams_dir):
        for tier in (1, 2, 3, 4):
            gp = os.path.join(exams_dir, "%s-gate.json" % TIER_DIR[tier])
            if os.path.exists(gp):
                g = read_gate(tier, gp)
                if g:
                    gates[tier] = {"data": g, "url": "exams/%s-gate.html" % TIER_DIR[tier]}

    capstones = {}
    if os.path.isdir(capstone_dir):
        for tier in (1, 2, 3, 4):
            cdir = os.path.join(capstone_dir, str(tier))
            if os.path.isdir(cdir):
                capstones[tier] = read_capstone(tier, cdir)

    sys.stdout.write("\n=== Manim CE course generator ===\n")
    sys.stdout.write("lessons scanned: %d\n" % len(lessons))
    sys.stdout.write("gates scanned:   %d\n" % len(gates))
    sys.stdout.write("capstones:       %d\n" % len(capstones))
    for n in R.notes:
        sys.stdout.write(n + "\n")
    for w in R.warnings:
        sys.stdout.write(w + "\n")
    if R.errors:
        sys.stdout.write("\n--- validation errors ---\n")
        for e in R.errors:
            sys.stdout.write(e + "\n")
        sys.stdout.write("\n%d error(s). Site not built.\n" % len(R.errors))
        return 1

    if args.check:
        sys.stdout.write("\n--check passed: all quizzes/gates valid, all scenes syntax-valid.\n")
        return 0

    lessons_by_id = {l["id"]: l for l in lessons}
    written = []
    for l in lessons:
        written.append(render_lesson(l, lessons_by_id))
    for tier, g in gates.items():
        p = render_gate(g["data"], tier)
        if p:
            written.append(p)
    for tier, c in capstones.items():
        written.append(render_capstone(c, tier))
    written.append(render_index(lessons, gates, capstones))

    sys.stdout.write("\nBuilt %d pages.\n" % len(written))
    for p in written:
        sys.stdout.write("  " + os.path.relpath(p, HERE) + "\n")
    sys.stdout.write("\nOpen course/index.html in a browser.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

/* =====================================================================
   quiz.js — in-browser assessment engine (zero dependencies).
   Renders lesson quizzes, tier-gate exams, and capstones from embedded JSON
   (<script type="application/json" id="quiz-data|exam-data|capstone-data">).

   Contract (emitted & validated by generator.py):
     { kind:"quiz"|"gate"|"capstone", id, tier, title, items:[...],
       threshold?:0.85, lockoutHours?:24 }
   Item types:
     single-choice {options, answer:int}
     multi-select {options, answer:[int]}
     fill-blank   {answer:"exact" | {regex:"..."}, placeholder?}
     predict-output {code, answer:"exact" | {regex}}
     bug-spot     {code, brokenLine:int, options:[fixes], answer:int}
     code-ordering{options:[lines], answer:[perm]}   // answer = correct order of option indices
     create       {prompt, modelAnswer, rubric:[{criterion,weight}], ref}
   Every item also has {id, type, bloom, prompt, explanation, ref}.
   ===================================================================== */
(function () {
  "use strict";

  /* ---------------- progress storage ---------------- */
  var LS = {
    quiz: function (id) { return read("mc:quiz:" + id, { best: -1, attempts: 0, lastTs: 0, completed: false, createScores: [] }); },
    saveQuiz: function (id, v) { write("mc:quiz:" + id, v); },
    gate: function (tier) { return read("mc:gate:" + t(tier), { best: -1, passed: false, attempts: 0, lastTs: 0 }); },
    saveGate: function (tier, v) { write("mc:gate:" + t(tier), v); },
    capstone: function (tier) { return read("mc:capstone:" + t(tier), { submitted: false, selfScore: -1, ts: 0 }); },
    saveCapstone: function (tier, v) { write("mc:capstone:" + t(tier), v); },
    done: function (id) { return read("mc:lessondone:" + id, false); },
    markDone: function (id) { write("mc:lessondone:" + id, true); }
  };
  function t(n) { return Number(n) || 1; }
  function read(k, dflt) { try { var v = localStorage.getItem(k); return v == null ? dflt : JSON.parse(v); } catch (e) { return dflt; } }
  function write(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }

  function nowH() { return Math.floor(Date.now() / 3600000); }      // hours since epoch
  function hoursLeft(lastTs, lockoutH) { return lockoutH - (nowH() - lastTs); }

  // Tier N unlocked iff gate(N-1) passed. Tier 1 always open.
  function gateUnlocked(tier) {
    tier = t(tier);
    if (tier <= 1) return true;
    return LS.gate(tier - 1).passed === true;
  }

  window.ManimProgress = {
    LS: LS, gateUnlocked: gateUnlocked, nowH: nowH, hoursLeft: hoursLeft,
    quizPct: function (id) { var q = LS.quiz(id); return q.best < 0 ? null : Math.round(q.best * 100); },
    gatePassed: function (tier) { return LS.gate(t(tier)).passed; },
    gatePct: function (tier) { var g = LS.gate(t(tier)); return g.best < 0 ? null : Math.round(g.best * 100); },
    capstoneSubmitted: function (tier) { return LS.capstone(t(tier)).submitted; },
    lessonDone: function (id) { return LS.done(id) === true; }
  };

  /* ---------------- helpers ---------------- */
  function esc(s) { return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;"); }
  function shuffle(a) { var r = a.slice(); for (var i = r.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var x = r[i]; r[i] = r[j]; r[j] = x; } return r; }
  function norm(s) { return String(s == null ? "" : s).trim().replace(/\s+/g, " ").toLowerCase(); }

  function codeBlock(code, filename) {
    var f = filename ? '<span class="filename">' + esc(filename) + "</span>" : "";
    return '<pre class="code">' + f + "<code>" + esc(code) + "</code></pre>";
  }

  function getData(id) {
    var s = document.getElementById(id);
    if (!s) return null;
    try { return JSON.parse(s.textContent); } catch (e) { console.error("Bad JSON in #" + id, e); return null; }
  }

  /* ---------------- item renderers ---------------- */
  // Each renderer returns { html, mount: (root, ctx) -> scored():{correct:bool|null} }
  // ctx holds per-item shuffle mapping captured at render so scoring is stable.

  function renderSingle(it) {
    var order = shuffle(it.options.map(function (_, i) { return i; })); // displayed -> canonical
    var html = '<ul class="opts" data-type="single">' + order.map(function (canon, disp) {
      return '<li data-disp="' + disp + '" data-canon="' + canon + '">' + esc(it.options[canon]) + "</li>";
    }).join("") + "</ul>";
    function mount(root) {
      var lis = root.querySelectorAll("li");
      lis.forEach(function (li) {
        li.addEventListener("click", function () {
          lis.forEach(function (x) { x.classList.remove("selected"); });
          li.classList.add("selected");
          root.dataset.picked = li.dataset.canon;
        });
      });
    }
    function score(root) {
      var picked = root.dataset.picked;
      if (picked == null) return null;
      return Number(picked) === Number(it.answer);
    }
    function reveal(root) {
      root.querySelectorAll("li").forEach(function (li) {
        var canon = Number(li.dataset.canon);
        li.classList.add(canon === Number(it.answer) ? "correct" : "wrong");
      });
    }
    return { html: html, mount: mount, score: score, reveal: reveal };
  }

  function renderMulti(it) {
    var order = shuffle(it.options.map(function (_, i) { return i; }));
    var html = '<ul class="opts" data-type="multi">' + order.map(function (canon, disp) {
      return '<li class="multi" data-canon="' + canon + '">' + esc(it.options[canon]) + "</li>";
    }).join("") + "</ul>";
    function mount(root) {
      root.querySelectorAll("li").forEach(function (li) {
        li.addEventListener("click", function () { li.classList.toggle("selected"); });
      });
    }
    function score(root) {
      var picked = Array.prototype.map.call(root.querySelectorAll("li.selected"), function (li) { return Number(li.dataset.canon); }).sort();
      if (!picked.length) return null;
      var ans = it.answer.map(Number).sort();
      return picked.length === ans.length && picked.every(function (v, i) { return v === ans[i]; });
    }
    function reveal(root) {
      root.querySelectorAll("li").forEach(function (li) {
        var canon = Number(li.dataset.canon);
        li.classList.add(it.answer.indexOf(canon) >= 0 ? "correct" : "wrong");
      });
    }
    return { html: html, mount: mount, score: score, reveal: reveal };
  }

  function renderFill(it) {
    var ph = it.placeholder || "type your answer…";
    var html = '<input type="text" class="fill" placeholder="' + esc(ph) + '">';
    function mount(root) {
      var inp = root.querySelector("input");
      inp.addEventListener("input", function () { root.dataset.val = inp.value; });
    }
    function score(root) {
      var v = root.dataset.val;
      if (v == null || v.trim() === "") return null;
      if (it.answer && typeof it.answer === "object" && it.answer.regex) {
        return new RegExp(it.answer.regex).test(String(v).trim());
      }
      return norm(v) === norm(it.answer);
    }
    function reveal(root) {
      var ok = score(root);
      var inp = root.querySelector("input");
      inp.style.borderColor = ok ? "var(--good)" : "var(--bad)";
    }
    return { html: html, mount: mount, score: score, reveal: reveal };
  }

  function renderPredict(it) {
    var html = codeBlock(it.code, "predict.py") +
      '<input type="text" class="fill" placeholder="what is printed / the final value?">';
    function mount(root) {
      var inp = root.querySelector("input");
      inp.addEventListener("input", function () { root.dataset.val = inp.value; });
      if (window.ManimHL) window.ManimHL.run();
    }
    function score(root) {
      var v = root.dataset.val;
      if (v == null || v.trim() === "") return null;
      if (it.answer && typeof it.answer === "object" && it.answer.regex) {
        return new RegExp(it.answer.regex).test(String(v).trim());
      }
      return norm(v) === norm(it.answer);
    }
    function reveal(root) {
      var inp = root.querySelector("input");
      inp.style.borderColor = score(root) ? "var(--good)" : "var(--bad)";
    }
    return { html: html, mount: mount, score: score, reveal: reveal };
  }

  function renderBugspot(it) {
    var lines = it.code.replace(/\n$/, "").split("\n");
    var order = shuffle(it.options.map(function (_, i) { return i; }));
    var lineHtml = lines.map(function (ln, i) {
      var n = i + 1;
      return '<li data-line="' + n + '"><label><input type="radio" name="bug-' + esc(it.id) +
        '" value="' + n + '"> <span class="ln">' + n + "</span> " + esc(ln) + "</label></li>";
    }).join("");
    var html = codeBlock(it.code, "buggy.py") +
      "<p class='muted' style='margin:6px 0 2px'>1) Select the broken line:</p>" +
      '<ul class="opts buglines" style="font-family:var(--mono);font-size:.82rem">' + lineHtml + "</ul>" +
      "<p class='muted' style='margin:10px 0 2px'>2) Pick the fix:</p>" +
      '<ul class="opts" data-type="single">' + order.map(function (canon, disp) {
        return '<li data-canon="' + canon + '">' + esc(it.options[canon]) + "</li>";
      }).join("") + "</ul>";
    function mount(root) {
      var fixLis = root.querySelectorAll("ul[data-type=single] li");
      fixLis.forEach(function (li) {
        li.addEventListener("click", function () {
          fixLis.forEach(function (x) { x.classList.remove("selected"); });
          li.classList.add("selected"); root.dataset.fix = li.dataset.canon;
        });
      });
    }
    function score(root) {
      var pickedLine = root.querySelector("input[name=bug-" + it.id + "]:checked");
      if (!pickedLine || root.dataset.fix == null) return null;
      var lineOk = Number(pickedLine.value) === Number(it.brokenLine);
      var fixOk = Number(root.dataset.fix) === Number(it.answer);
      return lineOk && fixOk;
    }
    function reveal(root) {
      root.querySelectorAll("li[data-line]").forEach(function (li) {
        if (Number(li.dataset.line) === Number(it.brokenLine)) li.classList.add("correct");
      });
      root.querySelectorAll("ul[data-type=single] li").forEach(function (li) {
        li.classList.add(Number(li.dataset.canon) === Number(it.answer) ? "correct" : "wrong");
      });
    }
    return { html: html, mount: mount, score: score, reveal: reveal };
  }

  function renderOrdering(it) {
    var shown = shuffle(it.options.map(function (_, i) { return i; })); // current display order = source idx
    function currentOrder(root) {
      return Array.prototype.map.call(root.querySelectorAll("ol li"), function (li) { return Number(li.dataset.canon); });
    }
    function paint(root) {
      var ol = root.querySelector("ol");
      ol.innerHTML = shown.map(function (canon, i) {
        return '<li data-canon="' + canon + '"><span class="grip">⠿</span> ' + esc(it.options[canon]) +
          ' <span class="btns"><button type="button" data-dir="up">↑</button><button type="button" data-dir="down">↓</button></span></li>';
      }).join("");
    }
    var html = '<ol class="ordering" style="list-style:none;padding:0;font-family:var(--mono);font-size:.84rem"></ol>';
    function mount(root) {
      paint(root);
      root.addEventListener("click", function (e) {
        var btn = e.target.closest("button[data-dir]");
        if (!btn) return;
        var li = btn.closest("li");
        var idx = Array.prototype.indexOf.call(root.querySelector("ol").children, li);
        var dir = btn.dataset.dir;
        var j = dir === "up" ? idx - 1 : idx + 1;
        if (j < 0 || j >= shown.length) return;
        var tmp = shown[idx]; shown[idx] = shown[j]; shown[j] = tmp;
        paint(root);
      });
    }
    function score(root) {
      var cur = currentOrder(root);
      var ans = it.answer.map(Number);
      return cur.length === ans.length && cur.every(function (v, i) { return v === ans[i]; });
    }
    function reveal(root) {
      var ok = score(root);
      root.querySelector("ol").style.borderColor = ok ? "var(--good)" : "var(--bad)";
    }
    return { html: html, mount: mount, score: score, reveal: reveal };
  }

  function renderCreate(it) {
    // Self-assessed: write, reveal model answer, check rubric, self-score 0-100.
    var html =
      '<textarea class="fill" rows="8" placeholder="Paste your scene.py here (this stays in your browser)."></textarea>' +
      '<details class="model-answer collapsible"><summary>Reveal model answer + rubric</summary>' +
      codeBlock(it.modelAnswer, "model_answer.py") +
      "<p class='muted' style='margin:8px 0 2px'>Self-assess against the rubric, then enter your score:</p>" +
      '<ul class="create-rubric">' + it.rubric.map(function (r) {
        return "<li>☐ " + (r.weight ? "[" + r.weight + "pt] " : "") + esc(r.criterion) + "</li>";
      }).join("") + "</ul>" +
      '<label>Self-score (0–100): <input type="number" min="0" max="100" class="selfscore" style="width:90px"></label>' +
      "</details>";
    function mount(root) {
      if (window.ManimHL) window.ManimHL.run();
    }
    function score(root) {
      var inp = root.querySelector("input.selfscore");
      if (!inp) return null;
      var v = Number(inp.value);
      if (isNaN(v) || inp.value === "") return null;
      root.dataset.selfscore = v;
      return v; // numeric, not boolean
    }
    function reveal(root) {}
    return { html: html, mount: mount, score: score, reveal: reveal, isCreate: true };
  }

  var RENDERERS = {
    "single-choice": renderSingle,
    "multi-select": renderMulti,
    "fill-blank": renderFill,
    "predict-output": renderPredict,
    "bug-spot": renderBugspot,
    "code-ordering": renderOrdering,
    create: renderCreate
  };

  /* ---------------- main render ---------------- */
  function renderItem(it) {
    var r = (RENDERERS[it.type] || renderSingle)(it);
    return {
      html:
        '<div class="item" data-id="' + esc(it.id) + '">' +
          '<div class="qhead"><div class="qprompt">' + esc(it.prompt) + "</div>" +
            '<span class="bloom">' + esc(it.bloom) + " · " + esc(it.type) + "</span></div>" +
          '<div class="resp"></div>' +
          '<div class="exp" hidden></div>' +
        "</div>",
      r: r
    };
  }

  function build(container, data) {
    var kind = data.kind;
    var items = data.items || [];
    var bodies = items.map(renderItem);

    var head = "<h2>" + esc(data.title || "") + "</h2>";
    var intro = "";
    if (kind === "gate") {
      intro = gateBanner(data);
    }

    container.innerHTML =
      '<section class="quiz ' + kind + '">' + head + intro +
      bodies.map(function (b) { return b.html; }).join("") +
      '<div class="scoreline"><button class="btn submit">Submit answers</button>' +
        '<button class="btn subtle reset">Reset</button>' +
        '<span class="result"></span></div>' +
      "</section>";

    // mount each item's interactivity
    var roots = container.querySelectorAll(".item");
    bodies.forEach(function (b, i) {
      var resp = roots[i].querySelector(".resp");
      resp.innerHTML = b.r.html;
      b.r.mount(resp);
    });

    var submit = container.querySelector(".submit");
    var reset = container.querySelector(".reset");
    var result = container.querySelector(".result");

    if (kind === "gate") {
      var st = LS.gate(data.tier);
      var left = hoursLeft(st.lastTs, (data.lockoutHours || 24));
      if (st.attempts > 0 && left > 0) {
        submit.disabled = true;
        submit.textContent = "Locked — retry in ~" + left + "h";
      }
    }

    submit.addEventListener("click", function () {
      var answeredAll = true;
      var autoCorrect = 0, autoTotal = 0, unanswered = 0;
      var createScores = [];
      bodies.forEach(function (b, i) {
        var resp = roots[i].querySelector(".resp");
        var s = b.r.score(resp);
        if (b.r.isCreate) {
          if (typeof s !== "number") { unanswered++; answeredAll = false; }
          else createScores.push(s);
          b.r.reveal(resp);
        } else {
          if (s === null) { unanswered++; answeredAll = false; }
          else { autoTotal++; if (s) autoCorrect++; }
          b.r.reveal(resp);
        }
        // explanation after submit
        var exp = roots[i].querySelector(".exp");
        if (it_hasExp(items[i])) {
          exp.hidden = false;
          exp.innerHTML = '<span class="tag">Explanation</span> ' + esc(items[i].explanation) +
            (items[i].ref ? ' <span class="muted">ref: ' + esc(items[i].ref) + "</span>" : "");
        }
      });

      if (unanswered > 0 && !confirm(unanswered + " item(s) unanswered. Submit anyway?")) return;

      var autoPct = autoTotal ? autoCorrect / autoTotal : 0;
      var createAvg = createScores.length ? Math.round(createScores.reduce(function (a, b) { return a + b; }, 0) / createScores.length) : null;

      if (kind === "gate") {
        var passed = autoPct >= (data.threshold || 0.85);
        var g = LS.gate(data.tier);
        g.attempts += 1; g.lastTs = nowH();
        g.best = Math.max(g.best < 0 ? 0 : g.best, autoPct);
        g.passed = g.passed || passed;
        LS.saveGate(data.tier, g);
        result.innerHTML =
          '<span class="big">' + Math.round(autoPct * 100) + "%</span> " +
          '<span class="verdict ' + (passed ? "pass" : "fail") + '">' +
          (passed ? "GATE PASSED — next tier unlocked" : "Below 85% — review and retry in 24h") + "</span>";
        submit.disabled = true;
        submit.textContent = "Locked — retry in ~" + (data.lockoutHours || 24) + "h";
        container.querySelector(".gate-banner").outerHTML = gateBanner(data, true);
      } else if (kind === "capstone") {
        var cs = LS.capstone(data.tier);
        cs.submitted = true; cs.selfScore = createAvg == null ? -1 : createAvg; cs.ts = nowH();
        LS.saveCapstone(data.tier, cs);
        result.innerHTML = '<span class="verdict pass">Capstone self-assessment recorded' +
          (createAvg == null ? "" : " (" + createAvg + "/100)") + ".</span>";
      } else {
        var q = LS.quiz(data.id);
        q.attempts += 1; q.lastTs = nowH();
        q.best = Math.max(q.best < 0 ? 0 : q.best, autoPct);
        q.completed = answeredAll;
        q.createScores = createScores;
        LS.saveQuiz(data.id, q);
        LS.markDone(data.id);
        var bits = ['<span class="big">' + Math.round(autoPct * 100) + "%</span> auto-scored" +
          (autoPct >= 0.7 ? ' <span class="verdict pass">quiz passed</span>' : ' <span class="verdict fail">review &amp; retry</span>')];
        if (createAvg != null) bits.push('<span class="score-chip">self-assessed create avg: ' + createAvg + "/100</span>");
        result.innerHTML = bits.join(" ");
      }
      if (window.ManimHL) window.ManimHL.run();
      window.scrollTo({ top: result.getBoundingClientRect().top + window.scrollY - 120, behavior: "smooth" });
    });

    reset.addEventListener("click", function () {
      if (!confirm("Reset this assessment? Your inputs clear; saved best scores are kept.")) return;
      build(container, data);
    });
  }

  function it_hasExp(it) { return it && it.explanation; }

  function gateBanner(data, after) {
    var st = LS.gate(data.tier);
    var thr = Math.round((data.threshold || 0.85) * 100);
    var left = hoursLeft(st.lastTs, data.lockoutHours || 24);
    if (st.passed) {
      return '<div class="gate-banner passed">✓ Tier gate passed (best ' + Math.round(st.best * 100) +
        "%). Threshold was " + thr + "%. The next tier is unlocked.</div>";
    }
    if (st.attempts > 0 && left > 0) {
      return '<div class="gate-banner warn">Last attempt: ' + Math.round(st.best * 100) + "%. One attempt per " +
        (data.lockoutHours || 24) + "h — retry unlocked in ~" + left + "h. Threshold " + thr + "%.</div>";
    }
    return '<div class="gate-banner locked">Tier gate. Pass at ≥ ' + thr + "% to unlock the next tier. " +
      "One attempt per " + (data.lockoutHours || 24) + "h; cumulative re-test is allowed.</div>";
  }

  /* ---------------- boot ---------------- */
  function boot() {
    var data = getData("exam-data") || getData("quiz-data") || getData("capstone-data");
    var mount = document.getElementById("assessment");
    if (!data || !mount) return;
    if (data.kind === "gate") {
      if (!gateUnlocked(data.tier)) {
        mount.innerHTML = '<div class="gate-banner locked">🔒 This tier gate is locked. Pass the previous tier\'s gate first.</div>';
        return;
      }
    }
    build(mount, data);
    if (window.ManimHL) window.ManimHL.run();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();

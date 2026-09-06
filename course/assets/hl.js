/* =====================================================================
   hl.js — zero-dependency Python syntax highlighter (runtime).
   Escapes HTML first, then tokenizes with a single master regex so a
   keyword inside a string is never re-colored. Token classes match app.css.
   Applies to every <pre class="code"><code> on the page.
   ===================================================================== */
(function () {
  "use strict";

  var KW = (
    "return if elif else for while in is not and or import from as with try " +
    "except finally raise pass break continue lambda yield global nonlocal " +
    "assert del async await"
  ).split(" ");
  var BI = (
    "self cls True False None print range len int float str list dict tuple " +
    "set bool enumerate zip map filter type isinstance super abs min max sum " +
    "round open format repr hasattr getattr setattr property staticmethod " +
    "classmethod next iter"
  ).split(" ");

  function esc(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  var MASTER = new RegExp(
    "(#[^\\n]*)" +                                                                 // 1 comment
    "|(\"\"\"[\\s\\S]*?\"\"\"|'''[\\s\\S]*?''')" +                                 // 2 triple string
    "|((?:[rbfuRBFU]{0,2})(?:\"(?:[^\"\\\\]|\\\\.)*\"|'(?:[^'\\\\]|\\\\.)*'))" +   // 3 string
    "|(@[A-Za-z_][\\w.]*)" +                                                       // 4 decorator
    "|\\b(def|class)\\b[ \\t]+([A-Za-z_]\\w*)" +                                   // 5 def/class kw, 6 name
    "|\\b(0[xX][0-9a-fA-F_]+|\\d[\\d_]*\\.?\\d*(?:[eE][+-]?\\d+)?)\\b" +            // 7 number
    "|\\b(" + KW.join("|") + ")\\b" +                                              // 8 keyword
    "|\\b(" + BI.join("|") + ")\\b",                                               // 9 builtin
    "g"
  );

  function highlightCode(code) {
    var escaped = esc(code);
    return escaped.replace(MASTER, function (m, com, tri, str, dec, dckw, dcname, num, kw, bi) {
      if (com)  return '<span class="tok-com">' + com + "</span>";
      if (tri)  return '<span class="tok-str">' + tri + "</span>";
      if (str)  return '<span class="tok-str">' + str + "</span>";
      if (dec)  return '<span class="tok-dec">' + dec + "</span>";
      if (dckw) {
        var cls = dckw === "def" ? "tok-fn" : "tok-cls";
        return '<span class="tok-kw">' + dckw + "</span> " +
               '<span class="' + cls + '">' + (dcname || "") + "</span>";
      }
      if (num)  return '<span class="tok-num">' + num + "</span>";
      if (kw)   return '<span class="tok-kw">' + kw + "</span>";
      if (bi)   return '<span class="tok-bi">' + bi + "</span>";
      return m;
    });
  }

  function run() {
    var nodes = document.querySelectorAll("pre.code code, code.language-python");
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      if (el.dataset && el.dataset.hl === "done") continue;
      el.innerHTML = highlightCode(el.textContent);
      if (el.dataset) el.dataset.hl = "done";
    }
  }

  window.ManimHL = { run: run, highlight: highlightCode };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();

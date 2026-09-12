# Egyptian grade-6 mathematics curriculum inventory

**Status:** Generation-ready topic inventory for the Bayan MVP
**Date:** 2026-09-13 (revised; original 2026-09-06)
**Scope:** Egyptian grade-6 mathematics, both terms, expressed as a
generation-ready topic list. This inventory feeds the golden prompt set
(#87) and the Term-1/Term-2 lesson sets (#88). Locked coverage from epic
#68: Term 1 = divisibility and factors, integers, algebra basics,
equations; Term 2 = fractions, ratio and rate, measurement, geometry.

## How to read this inventory

Each row is one lesson segment, sized for a single `bayan generate` call.
Visual-concept notes are animation-shaped: they name what appears, moves,
and transforms. Example numbers are lesson-prompt-ready and can be pasted
into `bayan generate` as part of the Arabic prompt. Topics marked with a
star (★) are golden-set candidates for #87; the goal is 2–3 per unit
(19 starred topics total, aiming at the ~20-prompt golden set). Every
starred row carries the star in both name columns. The inventory holds
21 topics — one over the epic's 15–20 planning range — because a
single-topic Unit 6 cannot offer the 2–3 golden candidates the set
needs; the split keeps each row sized for one `bayan generate` call. `beats` is the suggested beat count for the planner.
The `difficulty` column is a hint for ordering the Term-1 set: how hard
the current coder/gates/critic chain is expected to find the scene.

Digit profile notes use the three profiles from #81: `msa-western`
(Western digits, MSA phrasing), `msa-arabic-indic` (Arabic-Indic digits,
MSA), `egyptian` (Western digits, Egyptian dialect phrasing).

## Term 1

### Unit 1 — Numbers and operations: divisibility and factors

| # | topic (ar) | topic (en) | term | unit | visual concept | example numbers | beats | digits note | difficulty |
|---|------------|------------|------|------|----------------|-----------------|-------|-------------|------------|
| 1 | ★ قواعد القسمة على ٢ و ٥ و ١٠ | ★ Divisibility rules for 2, 5, and 10 | 1 | Numbers | A column of numbers highlights and sorts itself into two boxes ("divisible", "not divisible") as the last digit flashes | ٤٥، ٧٠، ٣٢ (ends in 0/5/2 checks) | 3 | Textbooks print Western digits in exercises; use `msa-western` | easy |
| 2 | ★ القاسم المشترك الأكبر | ★ Greatest common factor (GCF) | 1 | Numbers | Two rows of 12 and 18 squares regroup into full rectangles, then the largest shared row (6) highlights | القاسم المشترك الأكبر للعددين ١٢ و ١٨ | 4 | Western digits dominate worked examples | easy |
| 3 | ★ المضاعفات المشتركة | ★ Common multiples and least common multiple (LCM) | 1 | Numbers | Two number lines grow their multiples in alternating steps; the first shared number (12) pulses on both lines | المضاعف المشترك الأصغر للعددين ٤ و ٦ | 4 | Western digits | easy |
| 4 | ★ التحليل إلى عوامل أولية | ★ Prime factorization | 1 | Numbers | A number splits into a factor tree, branches growing downward until all leaves are circled primes | 24 = 2 × 2 × 2 × 3 | 4 | Western digits | medium |

### Unit 2 — Integers

| # | topic (ar) | topic (en) | term | unit | visual concept | example numbers | beats | digits note | difficulty |
|---|------------|------------|------|------|----------------|-----------------|-------|-------------|------------|
| 5 | ★ مفهوم الأعداد الصحيحة | ★ The number line and integers | 1 | Integers | A number line slides into view; labeled dots at -3, 0, 4 drop on and a thermometer-style bar mirrors the line | رتب الأعداد ٣، -٢، ٠ من الأصغر للأكبر | 3 | Signs (-) must render; Western digits | easy |
| 6 | ★ مقارنة الأعداد الصحيحة وترتيبها | ★ Comparing and ordering integers | 1 | Integers | Two integer dots race along the number line; the smaller one flashes, then an inequality sign drops between them | قارن بين -٥ و -٢ | 3 | Western digits | easy |
| 7 | ★ جمع الأعداد الصحيحة | ★ Adding integers with like and unlike signs | 1 | Integers | Arrows hop along the number line: +4 right, then -7 left, landing on -3 which pulses | (-4) + (+7) | 4 | Western digits | medium |

### Unit 3 — Algebra

| # | topic (ar) | topic (en) | term | unit | visual concept | example numbers | beats | digits note | difficulty |
|---|------------|------------|------|------|----------------|-----------------|-------|-------------|------------|
| 8 | ★ مفهوم المتغير والثابت | ★ Variables and constants in expressions | 1 | Algebra | A tile labeled س and a tile labeled ٥ slide together into the expression س + ٥; labels highlight each part | عبارة جبرية: س + ٥ حيث س = ٣ | 3 | Western digits; Arabic letter س as the variable | easy |
| 9 | تبسيط عبارة جبرية | Simplifying expressions by collecting like terms | 1 | Algebra | Like tiles (two س tiles, three س tiles) slide together into five س tiles; unlike tiles stay apart | اجمع: ٢س + ٣ + س | 4 | Western digits | medium |
| 10 | ★ إيجاد قيمة عبارة جبرية | ★ Evaluating an algebraic expression | 1 | Algebra | The variable tile flips to reveal its value; a substitution arrow feeds it into the expression and the result appears | أوجد قيمة ٢س + ١ عندما س = ٤ | 3 | Western digits | medium |

### Unit 4 — Equations

| # | topic (ar) | topic (en) | term | unit | visual concept | example numbers | beats | digits note | difficulty |
|---|------------|------------|------|------|----------------|-----------------|-------|-------------|------------|
| 11 | ★ مفهوم المعادلة | ★ What an equation is (balance model) | 1 | Equations | A balance scale holds س + ٢ on one side and ٧ on the other; the beam stays level | س + ٢ = ٧ | 3 | Western digits | easy |
| 12 | ★ حل معادلات من الدرجة الأولى | ★ Solving one-step equations | 1 | Equations | The balance loses one tile from each side (-2), leaving س = ٥ which pulses; then the check substitutes back | حل المعادلة س + ٣ = ١٠ | 4 | Western digits | medium |

## Term 2

### Unit 5 — Fractions

| # | topic (ar) | topic (en) | term | unit | visual concept | example numbers | beats | digits note | difficulty |
|---|------------|------------|------|------|----------------|-----------------|-------|-------------|------------|
| 13 | ★ مقارنة الكسور ذات المقامات المتماثلة | ★ Comparing fractions with like denominators | 2 | Fractions | Two fraction bars (3/7 and 5/7) fill segment by segment; the fuller bar highlights | قارن بين ٣/٧ و ٥/٧ | 3 | Fractions render as numerators over denominators; Western digits | easy |
| 14 | ★ جمع الكسور من نفس المقام | ★ Adding fractions with like denominators | 2 | Fractions | A 2/7 bar and a 3/7 bar slide together into one 5/7 bar; segment labels merge | ٢/٧ + ٣/٧ | 3 | Western digits | easy |
| 15 | ضرب عدد صحيح في كسر | Multiplying a whole number by a fraction | 2 | Fractions | Four copies of a 2/9 bar stack and merge into 8/9; repeated-addition arrows animate | ٤ × ٢/٩ | 4 | Western digits | medium |
| 16 | ★ تحويل الكسور إلى أعداد عشرية | ★ Converting fractions to decimals | 2 | Fractions | A 1/2 bar morphs into a 0.5 label on a decimal number line; tick marks double from 2 to 10 | حوّل ٣/١٠ إلى عدد عشري | 3 | Western digits; decimal separator per profile | medium |

### Unit 6 — Ratio and rate

| # | topic (ar) | topic (en) | term | unit | visual concept | example numbers | beats | digits note | difficulty |
|---|------------|------------|------|------|----------------|-----------------|-------|-------------|------------|
| 17 | ★ مفهوم النسبة | ★ The concept of ratio | 2 | Ratio and rate | A basket of 3 blue balls and 2 red balls sorts into a 3:2 ratio strip; labels scale together | نسبة ٣ إلى ٢ | 3 | Western digits | medium |
| 18 | ★ معدل وسعر المفرد | ★ Rate and unit price | 2 | Ratio and rate | Three price tags (12 pounds for 3 pens) collapse into one tag as two of the pens fade; the per-item price pulses | ثمن ٣ أقلام هو ١٢ جنيهاً؛ أوجد ثمن القلم الواحد | 3 | Western digits; pounds symbol stays Arabic prose | medium |

### Unit 7 — Measurement and geometry

| # | topic (ar) | topic (en) | term | unit | visual concept | example numbers | beats | digits note | difficulty |
|---|------------|------------|------|------|----------------|-----------------|-------|-------------|------------|
| 19 | ★ محيط المستطيل والمربع | ★ Perimeter of a rectangle and a square | 2 | Geometry | An ant walks the rectangle border leaving a traced outline; side labels tick off in the sum | محيط مستطيل طوله ٦ وعرضه ٤ | 3 | Western digits | easy |
| 20 | ★ مساحة المستطيل والمربع | ★ Area of a rectangle as a grid of unit squares | 2 | Geometry | A 6×4 rectangle fills with unit squares row by row; the rows collapse into the multiplication 6 × 4 = 24 | مساحة مستطيل طوله ٦ وعرضه ٤ | 3 | Western digits | easy |
| 21 | ★ تحويل وحدات القياس | ★ Converting metric length units | 2 | Measurement | A 1-meter ruler unfolds into ten 10-cm segments; unit labels swap (م ← سم) | حوّل ٣ متر إلى سنتيمتر | 3 | Western digits | medium |

## Scope notes and deferred topics

- Fraction division and dividing fractions is deferred: it needs a
  keep-change-flip visual that risks teaching a rule without meaning, and
  the current overflow heuristic penalizes the dense notation. Revisit
  after the critic gains fractions awareness.
- Negative-fraction ordering is deferred: it composes two hard visuals
  (signs and fraction bars) in one short scene.
- Statistics and data representation units exist in the syllabus but need
  bar-chart primitives the template catalogue does not have yet; deferred
  until a chart fixture is approved.

## Profile and digits note

Egyptian grade-6 textbooks print exercises with Western digits almost
exclusively, while pure Arabic prose sometimes uses Arabic-Indic digits.
The locked profile decision (#81) matches this: `egyptian` and
`msa-western` use Western digits; `msa-arabic-indic` exists for
completeness and for prompts the golden set uses to exercise digit
normalization in both directions. Golden prompts should pin their digit
expectation explicitly in the prompt text.

## Sources and disagreements

- Egyptian Ministry of Education, grade-6 mathematics syllabus outlines
  (the "Mathematics" domain split into numbers and operations, algebra,
  geometry, measurement, and statistics across two terms).
- Community syllabus summaries and teacher guides that order the domains
  Term 1: numbers/divisibility, integers, algebra, equations; Term 2:
  fractions, ratio and rate, geometry, measurement, statistics.
- Disagreements noted: some community outlines place integers early in
  Term 2 rather than late Term 1; statistics units are listed as Term 2
  by some sources and spread across both by others. The locked epic
  coverage (Term 1: divisibility/factors, integers, algebra, equations;
  Term 2: fractions, ratio/rate, measurement, geometry) is followed here,
  with statistics deferred with the other out-of-scope topics above.

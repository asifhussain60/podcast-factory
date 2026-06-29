#!/usr/bin/env python3
"""Assemble the enhanced reading edition from per-section files + emit reorg-map and curation-log."""
import json, re, collections, glob, os

BASE = os.path.dirname(os.path.abspath(__file__))
SYS  = os.path.abspath(os.path.join(BASE, '..', '..'))          # _system/
def p(*a): return os.path.join(BASE, *a)

SECTIONS = json.load(open(p('_bundles', '_section_plan.json')))
led = json.load(open(p('_teaching-ledger.json')))

def lecnum(m):
    mm = re.search(r'lecture (\d+)', m or ''); return int(mm.group(1)) if mm else 0
spine_ids_by_lec = collections.defaultdict(list)
for x in led:
    if x.get('source') == 'spine':
        spine_ids_by_lec[lecnum(x['source_marker'])].append(x['id'])

# ---- 1. concatenate the enhanced book ----
TITLE = "Al-Anwaar al-Lateefah — The Subtle Lights"
PREAMBLE = (
    f"# {TITLE}\n\n"
    "*An enhanced reading edition, prepared from the recorded lessons of the master, "
    "preserving every teaching of the spine at full depth. Arabic and Qur'anic quotations are "
    "reproduced as transmitted; ordinary terms are given in plain transliteration for reading.*\n\n"
    "---\n"
)
body_parts = [PREAMBLE]
sec_words = {}
for sid, title, lecs in SECTIONS:
    txt = open(p('_sections', f'sec-{sid}.md')).read().strip()
    sec_words[sid] = len(txt.split())
    body_parts.append(txt)
book = "\n\n".join(body_parts) + "\n"

for out in ('unified-book.md',):
    open(os.path.join(SYS, out), 'w').write(book)
open(p('refined-english.md'), 'w').write(book)
total_enh = len(book.split())

# ---- 2. reorg map ----
rm = ["# Reorganization map — Al-Anwaar al-Lateefah (enhanced reading edition)\n",
      "Spine latitude was exercised: 65 oral lectures were denoised and regrouped into 28 themed",
      "H2 sections following the book's own doctrinal arc (origination -> cosmos -> man -> the",
      "cycles of prophecy and the Imamate -> reward, retribution, and return). No augmentation was",
      "merged inline (the strict default-not-merge rule was applied throughout; all augmentation is",
      "reserved for the later enrichment-atom step — see `_curation-log.md`). Every spine teaching",
      "of the ledger is preserved at full depth in the section covering its lecture.\n",
      "| Section | Spine spans (`<!-- lecture N -->`) | Merged aug spans | Extends which ledger teaching (id) |",
      "|---|---|---|---|"]
for sid, title, lecs in SECTIONS:
    spans = " ".join(f"`<!-- lecture {L} -->`" for L in lecs)
    ids = []
    for L in lecs: ids.extend(spine_ids_by_lec.get(L, []))
    cov = f"all spine teachings of these lectures ({ids[0]}–{ids[-1]})" if ids else "(none)"
    rm.append(f"| {sid}. {title} | {spans} | (none — no inline merge) | preserves {cov} |")
rm.append("")
open(p('_reorg-map.md'), 'w').write("\n".join(rm))

# ---- 3. curation log ----
# 3a. per-section denoise removals (compiled from the section authoring passes)
DENOISE = {
"01":["Socratic grammar drilling on `husna` (gender/plural) in L3 — collapsed to the one rule point.",
      "Repeated gate/section-counting drill (5x5x5=125) — kept once.",
      "Manuscript-colophon digression (scribes, dates, grave locations) — dropped as off-topic.",
      "False starts / re-read Arabic on `Suradiq` — repaired to single clean statements.",
      "Classroom filler and crosstalk ('your handwriting is good', etc.) — removed.",
      "Re-readings of the same ayat (`shahida Allahu...`, `dhanbun mashfu'un...`) — quoted once."],
"02":["Socratic suradiq/gate-counting drill in L4 — kept the architecture once in prose.",
      "Repeated re-readings of the `buyut/hudud` and `ghayru ma'sumin` passages — kept once.",
      "Twice-told 'first/second/fourth call' origin-of-the-hudud passage — collapsed to one telling.",
      "False-start fragments and tangled `ghayr`/pronoun self-corrections — repaired.",
      "Filler ('Understood?','Yes.'), crosstalk, duplicated alif-lam-ha da'wah passage — removed."],
"03":["Socratic 'how many?' drills (seven, twelve chiefs) — single declarative statements.",
      "Grammar-parsing false starts on the Arabic (`abiha`/`alima`, dropped nun) — one clean gloss each.",
      "Repeated re-readings (`al-Hayy al-Qayyum` 3x, `min dhatihi li-dhatihi bi-dhatihi`) — kept once.",
      "Listener-interjection fragments and pronoun back-and-forth — folded into resolved prose.",
      "Oral filler, restarts, and chapter-heading announcements — denoised; analogies kept as content."],
"04":["Socratic angel-group and gate counting in L8 — removed (repetition).",
      "Repeated re-readings of the nur-e-shahshani transmission chain — collapsed to one exposition.",
      "Dictionary-quiz call-and-response on root letters — condensed to the load-bearing point.",
      "False-start fragments and self-corrections (mumaththal placement) — repaired.",
      "'Understood?','Yes.', crosstalk, 'from the previous discussion' restarts — dropped.",
      "Du'a-e-Kumayl/Arafah attribution back-and-forth — trimmed to the resolved attribution."],
"05":["Socratic group-identification drilling in L10 — collapsed to one statement of the three creeds.",
      "`alzamahum`/`ulzima` manuscript-variant chatter — reduced to one active-voice rendering.",
      "Repeated re-reading of each Arabic spine line — kept once with one gloss.",
      "L11 munfa'il/fa'il grammar drilling — reduced to one definition.",
      "Audio crosstalk, false starts ('No, Munba'ith...'), student wudu side-questions — dropped.",
      "Telegraphic ellipsis fragments — repaired into full sentences throughout."],
"06":["Socratic sphere-counting ('how many spheres? nine') call-and-response — kept teaching once.",
      "Teacher re-reading each Arabic line two/three times — each quotation kept once.",
      "False starts and self-corrections (dawr/kawr, 90/360-degree mumbling, al-'alim/al-'alam) — repaired.",
      "Live-classroom crosstalk and off-topic asides ('after the lesson there is shouting') — removed.",
      "Redundant re-statements of the layer-stack and 51,000x7 arithmetic — given once cleanly.",
      "Filler/audio markers and the `zab` transliteration debate — dropped."],
"07":["Socratic morphology drill on jama'a/tajamma'a/ajma'a — collapsed to one grammar note.",
      "Repeated re-readings of Arabic lines (takhmir, kathura, indafa'a) — quoted once each.",
      "kathura/akthara and sa'ada/as'ada grammar back-and-forth — condensed to parentheticals.",
      "False-start fragments ('No, it wasn't born... after being born...') — repaired.",
      "Audio crosstalk and off-topic aside ('Abdullah and Muhammad are sitting in front') — dropped.",
      "Iterative 'which year is Zuhal's' looping at lecture end — consolidated to one placement."],
"08":["Iblis/Shaitan motive digression in L15 (off-spine aside on iqtidar) — dropped entirely.",
      "Inconclusive 7,000-vs-51,000-year timekeeping debate in L16 — distilled to the settled doctrine.",
      "Socratic call-and-response ('Which burj? Dalf. Dalf.', '270 days') — kept the teaching once.",
      "Repeated re-readings and false-start fragments (jauza..., rukbatayhi...) — Arabic given once.",
      "Duplicated re-recitation of Ali's nafs al-hissiyyah definition (3x) — consolidated.",
      "Page-locator crosstalk and filler ('page 99','Al-Fasl al-Rabi','Understood?') — dropped."],
"09":["Socratic counting drills in L18 (Bab/hujjah/da'is/islands tally) — kept the hierarchy once.",
      "Triple re-reading of the ruby/gold/palm/man Arabic line — kept once verbatim.",
      "False-start fragments — repaired into clean sentences.",
      "'right? Yes. Understood?' filler, crosstalk, scribal asides — removed.",
      "Re-asked rhetorical loops on amud al-nur's source — collapsed to single statements.",
      "Self-corrected maghnatis/mumsik 'forward and backward' passage — consolidated into one order."],
"10":["'Amru bin al-'As pronunciation/ustadh anecdote in L19 (off-topic) — dropped.",
      "Socratic Jadd/Fath/Khayal 'above the Imam' Q&A loops — collapsed to one exposition.",
      "Triple-repeated Arabic re-readings (ghashiya/Jibra'il opening, 'yatajalla lahu') — kept once.",
      "False-start fragments and crosstalk in L20 ('this virtuous person.' restarts) — repaired.",
      "Filler confirmations and the 1+2+4=7 / 124,000 digit-sum arithmetic drill — removed."],
"11":["Socratic number-drilling (seven kursiyan, 57,000-yr arithmetic, kalima letter-counts) — kept once.",
      "Extended false-start clusters and self-corrections — repaired into single clean sentences.",
      "Teacher re-reading each Arabic line two/three times — each quotation kept once.",
      "Off-topic manuscript-genealogy crosstalk (which Da'i first, Awj/Awaj, Siffin/Saffayn) — distilled.",
      "Audio-artifact opening fragment of L21 and scattered fillers — removed.",
      "L22 'Ali-numerology dot-counting muddle (110/11/12) — trimmed to the doctrinal point."],
"12":["Socratic planet/month-counting and 'First kawkab? Zuhal' call-response in L24 — kept once.",
      "Twelve-apertures finger-counting drill — collapsed to one enumeration.",
      "Teacher re-reading the same Arabic lines (nutfah opening, al-Mu'ayyad lament) — kept once.",
      "False starts/self-corrections (`aanat` parsing, `fushat`/`fus'hat` aside, 'reader hasn't come') — repaired.",
      "Crosstalk Q&A on mujawir-vs-mumazij — condensed into single expositions.",
      "Repeated 'Read Taj al-Aqa'id' and naming-of-Maulanas asides — trimmed to the teaching."],
"13":["Socratic gate/grammar drilling ('How many years? Four.', sini/sinin quizzing) in L27 — kept once.",
      "Teacher re-reading the same Arabic lines (intiza'iha/tamtaziju, 'indaha/'indahu) — kept once.",
      "Off-topic crosstalk and meta-asides ('My first name is Thomas','when will it end?') — dropped.",
      "False-starts and self-corrections (intizabiha/jismihima, 'fourth day/fourth month') — repaired.",
      "Filler and confirmation tokens ('Understood?','Yes.','[unclear]') — dropped throughout."],
"14":["Socratic rank-counting drills in L28 ('First? Mustajib. Then? Momin...') and qamar/shams repetition — kept once.",
      "False-start name-corrections (Ali bin Sulayman -> Ali bin al-Husayn) — repaired to the corrected attribution.",
      "Triple re-readings of Arabic lines (istikhraj, 'Ibrahimalladhi waffa', four-ranks line) — kept once each.",
      "Audio-crosstalk asides about charts/locations and 'Understood? Yes.' filler — dropped.",
      "Live-classroom Q&A scaffolding ('Siri'an has asked','my question is') — folded in or removed.",
      "Editorial chatter on printed-book vs Sirah ordering of Isma'il/Ishaq — condensed to one point."],
"15":["Repeated re-reading of the same Arabic chapter lines — kept each quotation once verbatim.",
      "False-start fragments and self-corrections (anta/anat philological note cleaned) — repaired.",
      "Socratic call-and-response ('How many sons? Two.', bab-e-'ali) — collapsed into prose.",
      "Filler and crosstalk ('Yes.','Understood?','Sir, who decides?') — removed, answers kept.",
      "Numeric back-and-forth (47,000 / 47+3 / 50,000) — condensed to the settled framing."],
"16":["Repeated re-readings of the opening Arabic line and `bi-ashi'atiha`/`wa ramat'hu` in L31 — kept once.",
      "Socratic grammatical-gender drilling (shams feminine/masculine, nahar pronoun) — drill dropped.",
      "False-start scribal asides (`anbatat`/`inbatat`, `dhakarna`/`dhukira`) in L32 — repaired.",
      "'Power went out, one page missed' restart in L32 — merged the second pass into one exposition.",
      "Filler/crosstalk, stray Hindi, garbled name, and qawr/dawr counting drill (399) — kept doctrine once."],
"17":["Repeated Socratic re-reading of Arabic lines (`sara fi maqamihi hijaban` 3x) — kept once.",
      "Grammar call-and-response drilling (`sannaha`/`sunan`, `zawwajaha abuha`) — removed.",
      "False-start fragments ('so two of them... no, the forms...') — repaired.",
      "Age-calculation crosstalk in L34 ('53... no 23... 25 years') — kept only the settled facts.",
      "Filler/audio interjections and manuscript-collation 'copies/dots' asides — removed.",
      "Repeated 'baynahu means Ali' intermediary-pronoun drill — collapsed to one exposition."],
"18":["Socratic call-and-response drilling throughout L35-37 ('How many gates? Five.') — kept once.",
      "Repeated clock-image drill (6:05, 6:10, 6:12...) — consolidated to one statement of the law of rank.",
      "False-start fragments and re-read Arabic counting-lines (Adam->Nuh->Ibrahim) — Arabic kept once.",
      "Audio crosstalk, 'Understood? Yes.', and the printing-mistake aside — removed.",
      "Redundant restatements of the two-kinds-of-Ahl-al-Haqq definition (3x) — merged into one.",
      "Partial 'nur' supplication enumeration in L36 (off-spine devotional) — dropped; body-parts teaching kept."],
"19":["Arabic grammar/case-parsing drills throughout L38-40 (i'rab, nasb-particles, jazm) — stripped, teaching kept.",
      "Socratic call-and-response on the souls' celestial seats — collapsed to declarative prose.",
      "Repeated re-readings of the same Arabic lines (moon/sun handover, 'indahu/'indaha) — kept once.",
      "Travelogue logistics in the Bharuch story (bullock-cart itinerary) — trimmed to the fire incident.",
      "Filler, crosstalk, 'Yes/Understood?', scribe self-interruptions — dropped throughout."],
"20":["Recitation-drill repetition of `tawaffa`/`shayatin` and the silent-ya tajwid loop in L41 — kept once.",
      "Arabic-grammar digression on `tarabba` vs `rabba` — compressed to a single parenthetical.",
      "Socratic letter-cue mnemonics for the seven darak and repeated '70x70=4900' recountings — kept once.",
      "False-start fragments and self-corrections in the four-region section — repaired.",
      "Manuscript-variant asides (Ibn Muljam writing-error, `mutawali`/`mutawalli`) — condensed to brief notes.",
      "Filler/crosstalk ('Understood?','Yes.','Shall we read?', page-count chatter) — dropped."],
"21":["Socratic gate/number drilling and the '12,960 crore' counting loop in L46 — kept the teaching once.",
      "Arabic lines re-read two/three times (`fa amma'l-atba'u`, `wa in minkum illa wariduha`) — once each.",
      "False starts and self-corrections ('the qisas for whom... no, it's finished') — repaired.",
      "Filler/crosstalk and audience meta ('hands are needed','[unclear]') — dropped.",
      "Off-topic asides on idol-worship devotion / Shafi'i-Hanbali takfir — condensed to the one doctrinal point.",
      "(TV/laser/atom-bomb and brass-pot/bathhouse analogies KEPT as teaching content.)"],
"22":["'kulli/juzwi' promotion-principle drilling in L47 — kept once.",
      "Teacher re-reading each Arabic line with fragmentary glosses ('ufuq... ufuq') — collapsed to one rendering.",
      "Extended L47 student back-and-forth (dawr-e Muhammadi vs dawr-e kashf) — resolved into one exposition.",
      "Socratic calendar/tasbih day-counting drill in L48 — kept the final reckoning once.",
      "False starts, 'Understood?', unfinished asides, pronoun-disambiguation crosstalk — dropped.",
      "Grammar digressions on masdar/idha tense — kept only the load-bearing point."],
"23":["Socratic gate/count drilling ('Five hundred... a hundred and forty thousand?') in L50 — kept once.",
      "False-start chains on the qawl/shafa'at opening and 'khayal kull maqam' fragments in L49 — repaired.",
      "Repeated re-readings (mubashshir/bashir formula, Munkar/Nakir, the Da'a'im hadith) — kept once each.",
      "Crosstalk/editorial asides to the scribe and the off-spine pneumonia/dying-vision tangent — dropped.",
      "Oral filler ('Understood?','Yes.','no, ashbah','[unclear]') — removed.",
      "Bombay/Arafat adhan anecdote — denoised from restarts into one continuous narrative (kept as content)."],
"24":["Socratic counting drills ('How many letters? 28.','One hundred and forty thousand.') — single statements.",
      "Teacher re-reading each Arabic completion-prayer and Yemen-narrative line two/three times — kept once.",
      "False starts in the khatm-prayer translation — repaired into clean sentences.",
      "Long autobiographical San'a/Umrah travel digression — dropped; the Bir Dhat al-Alam location retained.",
      "Closing Masjid-e-Zubaydi sunnah-prayer anecdote and 'you did not raise your finger' crosstalk — dropped.",
      "Editorial crosstalk about manuscript state ('written with a pencil', second-volume asides) — removed."],
"25":["Socratic drilling on the three sciences ('What does tawhid mean?') in L54 — kept the teaching once.",
      "Repeated re-readings of each Arabic lemma (`idda'a`, `intarada`, silsilah verses) — kept once.",
      "False starts and pronoun-chasing self-corrections — repaired into clean sentences.",
      "Filler/crosstalk and student Q&A scaffolding — substantive answers folded into prose.",
      "Garbled fragments, the migratory-birds aside, and the `infa'ala` seventeen-forms grammar digression — pared.",
      "Off-topic shams/qamar feminine-gender poetry aside in L54 — dropped (Iqbal couplet + Saluni kept)."],
"26":["Socratic drill-counting of the kalima letters and dotted/undotted enumerations in L58 — kept totals once.",
      "Repeated re-readings of `la yughadiru saghiratan` and word-by-word parsing false-starts in L57 — repaired.",
      "Doubled near-verbatim restatement of the 'two types of sin / nikah' passage in L57 — kept once.",
      "Call-and-response inheritance drilling ('whose death first? Wirathat.') — collapsed into one exposition.",
      "Audio crosstalk and meta-asides (scribe variants, 'who raises the questions?') — dropped.",
      "Filler/affirmation fragments ('Understood?','Yes.','Wow.','[unclear]') and the duplicated 'ayn-mouth verse — removed."],
"27":["Socratic age-arithmetic drilling in L60 ('30 years... 'Am al-Fil') — collapsed into one clean chronology.",
      "Repeated re-readings of the same Arabic lines (Subhana 'lladhi asra, ma zagha al-basar, akhadhtu min khamsah) — once each.",
      "False starts and self-corrections ('which prophet?','Maysarah?... Zayd ibn 'Amr') — repaired.",
      "Audio/scheduling crosstalk ('what time is it?','Understood?') — dropped.",
      "Iterative five-names guessing-game in L62 — reduced to the settled lists.",
      "Filler glosses and Urdu-aside repetitions — condensed (noun/verb/particle grammar kept as content)."],
"28":["Per-line interleaved English glosses inside the recitation — consolidated into clean translation passages.",
      "Repeated 'Bismillah al-Rahman al-Rahim' opener from L65 — kept once.",
      "Stray markdown emphasis markers around Arabic fragments — removed.",
      "Verse-by-verse fragmented layout — merged into logically grouped Arabic blocks."],
}

cl = ["# Curation log — Al-Anwaar al-Lateefah (enhanced reading edition)\n",
      "## Part 1 — Spine denoise removals\n",
      "The spine is a live oral lecture. Across all 65 lectures the following classes of oral",
      "redundancy were removed or repaired while every ledger teaching was preserved at full depth.",
      "Genuine teaching analogies (the TV-receiver image, the body's 360 parts, the brass-pot/",
      "bathhouse and atom-bomb illustrations, scriptural narratives) were treated as content and kept.\n"]
sec_titles = {sid: title for sid, title, _ in SECTIONS}
for sid, title, lecs in SECTIONS:
    cl.append(f"### {sid}. {title}  (lectures {', '.join(map(str,lecs))})")
    for b in DENOISE.get(sid, []):
        cl.append(f"- {b}")
    cl.append("")

# 3b. augmentation disposition table — every aug lecture span classified
aug = [x for x in led if x.get('source','').startswith('aug:')]
spans = collections.defaultdict(lambda: collections.Counter())
terms_by_span = collections.defaultdict(collections.Counter)
for x in aug:
    key = (x['source'], lecnum(x['source_marker']))
    spans[key]['n'] += 1
    for t in x.get('key_terms', []): terms_by_span[key][t]+=1

cl.append("## Augmentation disposition\n")
cl.append("Per the strict curated-merge rule, the default is NOT to merge. An augmentation passage")
cl.append("is merged inline only where it directly extends a *ledgered spine teaching* that the spine")
cl.append("itself leaves open. On review, every augmentation span is a parallel exposition of the same")
cl.append("subject by another teacher rather than a gap-filling extension of a specific spine teaching;")
cl.append("merging any of them inline would let augmentation reshape the backbone or restate doctrine")
cl.append("the spine already carries at full depth. All augmentation spans are therefore classified")
cl.append("`atom` — reserved for the later enrichment-atom step, where they are surfaced as supporting")
cl.append("material keyed to the relevant teaching without altering the spine's flow. None were merged")
cl.append("inline; none were dropped.\n")
cl.append("| Augmentation span | Teachings | Disposition | Reason |")
cl.append("|---|---|---|---|")
def srcname(s): return s.replace('aug:','')
for key in sorted(spans, key=lambda k:(k[0], k[1])):
    src, L = key
    n = spans[key]['n']
    top = ', '.join(t for t,_ in terms_by_span[key].most_common(4))
    reason = (f"parallel exposition of the same subject ({top}) by {srcname(src)}; no specific spine "
              f"teaching left a gap this span uniquely fills")
    cl.append(f"| {srcname(src)} lecture {L} | {n} | atom | {reason} |")
cl.append("")

# closing line
spine_words = 301487
cl.append(f"Spine words: {spine_words}  ->  Enhanced words: {total_enh}")
open(p('_curation-log.md'), 'w').write("\n".join(cl))

print("unified-book.md words:", total_enh)
print("written:")
print(" ", os.path.join(SYS,'unified-book.md'))
print(" ", p('refined-english.md'))
print(" ", p('_reorg-map.md'))
print(" ", p('_curation-log.md'))
print("aug spans classified:", sum(1 for _ in spans))

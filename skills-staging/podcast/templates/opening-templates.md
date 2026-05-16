# Opening Templates — Canonical Reference

The opening of every NotebookLM episode is a **single sentence** containing (a) the source's identity and (b) the specific section being covered. No exceptions, regardless of content type.

## Universal template

```
Welcome to this episode on [SOURCE], where today we [VERB] [SECTION].
```

Where each slot adapts to the detected content type.

## Content-type adaptation table

| Content type | SOURCE slot | SECTION slot |
|---|---|---|
| Book | Book title (italicized) | Chapter N, Title |
| Article | `the article '[Title]' by [Author]` | Section heading, or central argument in 3–5 words if single-section |
| Academic paper | `the paper '[Title]' by [Author]` | Named section (Introduction, Methods, Findings, Discussion) |
| Lecture | `the lecture '[Title]' by [Speaker]` | Part N if a series, or central theme |
| Sermon | `the sermon '[Title]' by [Speaker]` | Central teaching |
| Memoir | Memoir title (italicized) | Chapter N, Title |
| Document / notes | `the document '[Title]'` | Main topic |
| Interview | `the conversation between [A] and [B] on [Topic]` | Segment theme |
| Anthology / collection | Collection title (italicized) | `the piece '[Piece Title]' by [Author]` |
| OCR / transcript | Treated by underlying content type | Per type |

## Verb rotation

**Multi-section sources** (books, papers in multiple parts, lecture series): position-aware rotation.

| Position | Verb |
|---|---|
| First section | `begin with` |
| Last section | `conclude with` |
| Second section | `explore` |
| Third section | `enter` |
| Fourth section | `continue with` |
| Fifth+ sections | `discuss` (or cycle through `explore` / `continue with` / `enter`) |

**Single-piece sources** (one article, one sermon, one document): pick from `examine`, `explore`, `consider`, `unpack` based on tone — `examine` for analytical, `explore` for narrative, `consider` for reflective, `unpack` for argumentative.

## Hard rules

1. **Unknown title or author → stop and ask.** Never fabricate. Write a prompt file to `WORK_DIR/missing-metadata.md` and pause.
2. **Italicize titles of full works** (books, memoirs, collections). Article titles, paper titles, lecture titles, sermon titles, document titles, piece titles → single quotes, not italics.
3. **Single sentence only.** Never two short sentences. The book title and the section must appear in one grammatical sentence.
4. **No "Today we will explore"** — the verb is bare present ("today we explore"), not future.
5. **No "deep dive into"** — that phrase belongs in the format tag, not the opening.

## Validated examples

- Book: `Welcome to this episode on _[Book Title]_, where today we explore Chapter 3, [Chapter Title].`
- Article: `Welcome to this episode on the article 'The Crisis of Authority in Modern Religion' by Karen Armstrong, where today we examine its central argument: institutional religion has lost its capacity to transmit living meaning.`
- Academic paper: `Welcome to this episode on the paper 'Cognitive Patterns of Spiritual Maturation' by Sarah Coakley, where today we examine the Findings section.`
- Sermon: `Welcome to this episode on the sermon 'On Patience in Tribulation' by Imam Ali, where today we examine the central teaching: endurance as the architecture of faith.`
- Lecture series part: `Welcome to this episode on the lecture series 'Foundations of Ismaili Thought' by Farhad Daftary, where today we continue with Part 4, Esoteric Interpretation.`
- Single document: `Welcome to this episode on the document 'Field Notes from a Clinical Psychology Practice', where today we examine the recurring pattern of inherited guilt.`
- Interview: `Welcome to this episode on the conversation between Krista Tippett and Bessel van der Kolk on trauma and the body, where today we focus on the segment on memory.`

Note: all examples above use neutral placeholders. The skill ships with no hardcoded affinity for any specific work. All output references come from the user's actual input.

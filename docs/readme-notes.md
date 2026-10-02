# README notes: everything in one place

These notes gather every feature, test result and decision, for writing the
README and preparing for the review. The details of each test are in the other
files in `docs/`.

## 1. What the app does and why (written in my own words in the README)

The questions the README answers:
- Who is it for?
- What's hard about practising for interviews alone?
- Why expected questions, single-question practice and a full mock interview?
- Why the settings: the job description, area, seniority, interview type, style?
- Why compare five feedback techniques?

## 2. Features

**For the user (the sidebar):**
- Job title, job description (optional), professional area, seniority, interview
  language, interview type, interviewer style (friendly, neutral, strict) and
  feedback length (concise or detailed)

**Three tabs:**
- **Mock interview:** a full chatbot that remembers the whole conversation, with
  an end-of-interview report (scores, strengths, improvements, next steps)
- **Practice:** one question, one answer, one piece of feedback
- **Expected questions:** 8 likely questions, with why they're asked and a tip

**Developer settings (kept apart from the user's choices):**
- Feedback technique (five), model, max tokens, reasoning effort
- "Show system prompts", to see exactly what the model received

**Look and feel:** a calm dark green theme, a leaf frame drawn in code as an SVG
(no image file, no licence needed), a solid content panel so text stays readable,
a serif heading font and a welcome card.

## 3. How it's built

| File | Its one job |
|---|---|
| `app.py` | The page: sidebar, tabs, buttons and the chat |
| `llm.py` | The only file that calls the model (OpenRouter, openai/gpt-5-mini by default) |
| `prompts.py` | All the prompts: shared parts, five techniques, rules, the report schema |
| `guards.py` | The security guard |
| `style.py` | The look: theme, leaf frame, fonts, welcome card |
| `redteam.py` | The jailbreak test, which saves results to Excel |
| `docs/` | My notes on every test and decision |
| `results/` | Test outputs (the jailbreak test's Excel files) |

**Key design ideas:**
- **One file, one job,** so changes stay in one place
- **The key is never in the code:** it's read from `.env`, which `.gitignore` excludes
- **Every system prompt has shared parts, and only the technique part changes,**
  so the five techniques can be compared fairly
- **The chatbot remembers by sending the whole history every turn,** including
  the model's own earlier replies (assistant messages). A hidden kickoff message
  starts it, and its system prompt is fixed at Start
- **The chat only saves an answer once a reply has arrived,** so an empty reply
  can't break the history
- **The report uses structured JSON with a strict schema,** from a separate,
  impartial assessor that treats the transcript as data
- **Pasted text goes inside tags,** and copies of those tags are removed first, in
  any case (`remove_tags`)
- **`ask_model` has default values** for the model settings, so older code keeps
  working, and it prints the tokens of every call to the terminal
- **Ruff** checks and formats the code

## 4. The course requirements

| Requirement | Where | Status |
|---|---|---|
| Research the kind of interview preparation | README "What it does and why", `docs/research.md` | ✅ |
| Streamlit front end | `app.py` | ✅ |
| OpenRouter API key | `.env`, read in `llm.py` | ✅ |
| An allowed model | `openai/gpt-5-mini`, plus nano and gpt-5 | ✅ |
| 5 system prompts with different techniques | `prompts.py` | ✅ |
| Check which works best | `docs/technique-notes.md`, `docs/length-notes.md` | ✅ |
| At least one security guard | `guards.py`, `docs/security-notes.md` | ✅ |

**Optional tasks done:**
- **Hard:** a full chatbot instead of a one-time call (the Mock interview)
- **Medium:** all model settings as fields; a job description field; jailbreaking
  my own app with results in Excel; a guard with developer settings kept separate
- **Easy:** interviewer personas; concise vs detailed; prompts for a domain (area
  and job title); tuning model settings and comparing them; an AI critique of the
  app (`docs/ai-critique.md`); more security constraints (input validation on the
  job title, job description and every answer)
- **Partly:** structured JSON (one format so far: the report)

**Maximum points: reached** (4 medium and 1 hard, where 2 medium and 1 hard are
needed).

## 5. Test results (details in docs/)

**The five techniques** (`technique-notes.md`): all found the problems in weak
answers. Few-shot followed its format best, and is my favourite. The structured
rubric was the most consistent. Role prompting broke its "no bullet points" rule
twice in the first test, but kept it in all 4 later runs. Zero-shot, the
baseline, had no consistent format.

**Tailoring** (`tailoring-tests.md`):
- With the company set to SAP, no questions mentioned SAP, so I removed the
  company and country settings. The system prompt got about 40% shorter
- With a made-up job ad, 8 of 8 and 7 of 7 questions used its details, against
  1 of 8 without it. The job description works

**Concise vs detailed** (`length-notes.md`): the setting worked for all five
techniques, and every technique kept its own format in both lengths. The freer
the format, the more Detailed grew: zero-shot about 3.4 times, role prompting 2.6,
chain-of-thought 1.8, the rubric 1.5, few-shot 1.1. Few-shot's examples nearly
double its input (about 590 vs 317 tokens).

**Model settings** (`settings-notes.md`):
- Reasoning effort, minimal to high: about 17 times the tokens and 7 times the
  wait, but the same main advice
- Max tokens 500 with high effort: the model ran out of room while thinking, the
  page showed "None", and it was still billed (448 tokens)
- Nano used about 4 times the tokens of mini, and took 2.5 times as long
- GPT-5 is blocked on the course account
- No temperature setting: the GPT-5 models don't support it

**Security** (`security-notes.md`), in three rounds:

| Round | Attacks blocked by the guard | Real answers wrongly blocked |
|---|---|---|
| 1: the first test (17 attacks, 8 innocent) | 10 of 17 (59%) | 0 of 8 (0%) |
| 2: harder cases from the AI critique (22 attacks, 12 innocent) | 10 of 22 (45%) | **4 of 12 (33%)** |
| 3: the narrowed guard | **14 of 22 (64%)** | **0 of 12 (0%)** |

The system prompt stopped every attack the guard missed, in every round, so the
two layers together stopped all of them.

## 6. Problems found by testing, and fixed

**From my own tests:**
1. **Expected questions cut off** (2 of 4 runs): gave only that request at least
   4,000 max tokens, with `min_tokens`
2. **The report penalised an unanswered final question:** removed it from the
   transcript in code, with a prompt rule as a backup
3. **Questions bundled several topics** (up to 6): defined "one question" as one
   topic, under 30 words, in a shared rule
4. **Questions came out in German** when the country was Germany: added an
   explicit language setting and rule
5. **The report's next steps were written to the interviewer:** added "the report
   is for the candidate"

**From the AI critique:**
6. **The job description's guard check could never run:** it had been pasted
   inside the job title's check, after `st.stop()`. It's now its own step
7. **"Show system prompts" appeared twice** in Practice: removed the duplicate
8. **A failed or empty reply broke the chat history:** the answer is now only
   saved once a reply arrives
9. **Tags were only removed in lowercase,** so `</TRANSCRIPT>` could escape: a
   new `remove_tags` function works in any case
10. **The guard blocked 1 in 3 real IT answers** ("developer mode on the phone",
    "an iOS jailbreak"): narrowed the patterns, and added German, look-alike
    letter and tag patterns. False positives went from 33% to 0%
11. **A renamed variable (`jd`) would have crashed the app** whenever a job
    description was pasted: Ruff caught it (`F821 Undefined name`)

**The lesson that kept coming back: anything left unsaid in a prompt gets guessed.**

## 7. Known limitations, and how I'd fix them

1. **No friendly error handling:** a too-low max tokens shows "None", and a
   blocked model shows a raw traceback. Fix: catch API errors in `llm.py`, and
   show a clear message
2. **Practice repeats its most likely question,** since each click has no memory.
   Fix: remember the questions asked, and ask the model not to repeat them
3. **The interviewer accepts answers that miss the question.** Fix: a rule to say
   so kindly, and ask again
4. **The interview type drifts in long Mock interviews** towards the job
   description's technical skills. Fix: "the interview type decides the kind of
   question; the job description decides what it's about"
5. **The expected questions disappear after other clicks.** Fix: save them in
   `st.session_state`
6. **The Mock interview shows no progress,** and nothing says when to end it.
   Fix: show "Question 3 of 6"
7. **The guard only catches wording it knows,** so rephrased attacks get through
   (the system prompt stops them). Fix: an AI-based guard
8. **A candidate could fake "Interviewer:" lines** in the transcript, to fool the
   report. Fix: a structured transcript
9. **The report's scores have no clear definitions.** Fix: one line per score,
   and "Ready" only for an overall score of 8 or more
10. **No cost shown to the user,** only token counts in the terminal. Fix: the
    price per call, from OpenRouter's models endpoint
11. **Only one structured JSON format.** Fix: the expected questions as JSON
12. **Developer settings are visible to every user.** Fix: show them only in a
    developer mode
13. **redteam.py only tests the Practice feedback,** not the Mock interview or the
    report
14. **The styling relies on Streamlit's internal names** (like `.stApp`), which a
    future version could change

## 8. Lessons for the review

- **Measure before deciding:** the company setting looked useful, but testing
  showed it did nothing
- **A test is only as good as its examples:** 0% false positives came from easy
  examples, and realistic ones showed 33%
- **Change one thing at a time:** the shared prompt parts make the technique
  comparison fair
- **Defence in depth:** the guard and the system prompt each caught what the other
  missed, so the guard can afford to be narrow
- **If code can do it reliably, use code:** the unanswered-question fix
- **max_tokens includes the hidden thinking,** so a too-low limit fails and still
  costs money
- **The cheapest model per token isn't always the cheapest per reply**
- **Testing a feature isn't the same as checking its code runs:** the job
  description worked in my tests, but its guard check was dead code
- **Read Ruff's output before committing:** it caught a crash in under a second
- **Git:** one branch per feature, merge before branching again, commit often,
  and check `Get-ChildItem` before deleting a folder

## 9. Still to do

- [x] AI critique of the finished app, in `docs/ai-critique.md`
- [ ] README, with "What it does and why" in my own words
- [ ] Create the `interview-basic` repo on GitHub, and push
- [x] Decide which version to submit: `interview-basic`
- [ ] Push to the Turing repo, tag it `submitted`, submit, and schedule the review
- [ ] Practise the live demo
- [ ] Mock review
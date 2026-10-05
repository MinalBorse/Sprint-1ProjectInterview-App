# Interview Practice App

An AI interview coach built with Streamlit and OpenRouter: practise answering
interview questions, get feedback on every answer, and take a full mock interview
with a scored report at the end.

Built for Turing College, AI Engineering, Sprint 1.

## What it does and why



**Who it's for:** people preparing for a job interview, especially for junior IT
roles, who want to practise on their own, at their own pace. For example, I want to use it for own interview preparation.

**The problem:** practising alone, it's hard to know whether an answer is good.
Nobody asks follow-up questions, and nobody says what's missing. Most practice
questions online are general, not tailored to a specific job.

**Why three tabs:** they match three stages of preparing.
- **Expected questions:** first, see what you're likely to be asked, and why.
- **Practice:** then practise one question at a time, getting feedback on each
  answer, and trying again.
- **Mock interview:** finally, rehearse a real interview, with follow-up questions
  that build on your answers, and a report at the end.

**Why these settings:** a good interview depends on the job. The **job
description** makes the questions fit a specific position (in my tests, 8 of 8
questions used its details, against 1 of 8 without). **Seniority, interview type
and area** decide how hard and what kind of questions to ask. The **interviewer
style** lets a nervous candidate start with a friendly interviewer and move on to
a strict one.

**Why five feedback techniques:** the course asks which prompt technique works
best, so I built all five on the same shared prompt, and compared them on the
same answers. That way the comparison is fair, and my preferred technique
(few-shot) is backed by evidence, not a guess.

**Why a calm design:** interviews can be stressful, so the app tries to feel like
a calm place to practise, with a welcome message and a quiet, green look.

## Features

**Three tabs:**

- **Mock interview:** a full chatbot that remembers the whole conversation, follows
  up on earlier answers, and gives a scored report at the end (scores, strengths,
  things to improve and next steps), which can be downloaded as JSON.
- **Practice:** one question, one answer, one piece of feedback.
- **Expected questions:** 8 likely questions for the role, with why they're asked
  and a tip for each.

**Settings for the interview:** job title, job description (optional), professional
area, seniority, interview language (English or German), interview type,
interviewer style (friendly, neutral or strict) and feedback length (concise or
detailed).

**Developer settings,** kept apart from the interview choices: the feedback
technique (five to choose from), the model, max tokens, reasoning effort, and
"Show system prompts", to see exactly what the model received.

## Course requirements

| Requirement | Where |
|---|---|
| Research the kind of interview preparation | "What it does and why" above |
| A Streamlit front end | `app.py` |
| An OpenRouter API key, kept out of the code | `.env`, read in `llm.py` |
| An allowed model | `openai/gpt-5-mini` (with nano and gpt-5 as options) |
| At least 5 system prompts with different techniques | `prompts.py` |
| Check which works best | `docs/technique-notes.md`, `docs/length-notes.md` |
| At least one security guard | `guards.py`, `docs/security-notes.md` |

**Optional tasks:**
- **Hard:** a full chatbot instead of a one-time call (the Mock interview)
- **Medium:** all model settings as fields; a job description field; jailbreaking
  my own app, with results in Excel (`results/redteam-reviewed.xlsx`); a security
  guard with developer settings kept separate
- **Easy:** interviewer personas; concise vs detailed feedback; prompts for a
  domain; tuning model settings and comparing them; an AI critique of the app
  (`docs/ai-critique.md`); input validation on every text field

## How to run it

**You need:** Python 3.12, [uv](https://docs.astral.sh/uv/), and an OpenRouter API
key.

1. Clone the repository, and go into its folder.
2. Install the packages:
   ```
   uv sync
   ```
3. Create a file called `.env` in the project folder, with your key:
   ```
   OPENROUTER_API_KEY=your-key-here
   ```
   `.env` is listed in `.gitignore`, so the key is never uploaded.
4. Start the app:
   ```
   uv run streamlit run app.py
   ```
   It opens in your browser at http://localhost:8501.

**Other commands:**

| Command | What it does |
|---|---|
| `uv run python llm.py` | Checks the connection to the model |
| `uv run python guards.py` | Runs the guard's quick self-test |
| `uv run python redteam.py` | The jailbreak test, without API calls (free) |
| `uv run python redteam.py --model` | The jailbreak test, also sending missed attacks to the model |
| `uv run ruff check .` and `uv run ruff format .` | Check and format the code |

## How it's built

| File | Its one job |
|---|---|
| `app.py` | The page: sidebar, tabs, buttons and the chat |
| `llm.py` | The only file that calls the model, through OpenRouter (`openai/gpt-5-mini` by default) |
| `prompts.py` | All the prompts: the shared parts, five techniques, rules, and the report's JSON schema |
| `guards.py` | The security guard |
| `style.py` | The look: the theme, a leaf frame drawn in code as an SVG, fonts and the welcome card |
| `redteam.py` | The jailbreak test, which saves its results to Excel |
| `docs/` | My notes on every test and decision |
| `results/` | The jailbreak test's results |

**Key design decisions:**

- **Every system prompt has shared parts, and only the technique part changes,** so
  the five techniques can be compared fairly.
- **The chatbot remembers by sending the whole conversation every turn,** including
  the model's own earlier replies. A hidden first message starts it, and its system
  prompt is fixed at the start, so the rules don't change halfway through.
- **The report uses structured JSON with a strict schema,** from a separate,
  impartial assessor, not the interviewer. The transcript goes inside tags, marked
  as data, so an answer can't change the score.
- **Pasted text is treated as data:** the job description and transcript go inside
  tags, and any copies of those tags are removed first, in any upper or lower case.
- **The key is never in the code:** it's read from `.env`.

## Prompt techniques, and which works best

All five share the same context and rules; only the "how to give feedback" part
changes.

| Technique | What it does |
|---|---|
| Zero-shot | Instructions only: the baseline |
| Few-shot | Two worked examples of good feedback |
| Chain-of-thought | Shows its reasoning ("How I assessed your answer") before the feedback |
| Role prompting | Speaks as a hiring manager, in natural paragraphs |
| Structured rubric | A 1 to 5 score with a fixed template |

**Findings** (details in `docs/technique-notes.md` and `docs/length-notes.md`):

- All five found the problems in weak answers.
- **Few-shot followed its format best,** and is my favourite. Its examples nearly
  double each call's input (about 590 vs 317 tokens), which is the trade-off.
- The structured rubric was the most consistent, and its score was the same (2/5)
  in 3 of 4 runs.
- With the feedback length setting, every technique kept its own format. The freer
  the format, the more "Detailed" grew: zero-shot about 3.4 times, few-shot about
  1.1 times.

## Model settings

Tested in `docs/settings-notes.md`:

- **Reasoning effort:** from minimal to high, about 17 times the tokens and 7 times
  the wait, but the same main advice.
- **Max tokens includes the hidden thinking:** at 500 with high effort, the model ran
  out of room while thinking and wrote nothing, but was still billed.
- **GPT-5 nano used about 4 times the tokens of mini,** and took 2.5 times as long,
  so the cheapest model per token isn't automatically the cheapest per reply.
- **No temperature setting:** the GPT-5 models don't support it.

**Defaults:** GPT-5 mini, default reasoning effort, and 2,000 max tokens (4,000 for
the list of expected questions, so it isn't cut off).

## Security

Two layers (details in `docs/security-notes.md`):

1. **A guard** checks the job title, the job description and every answer before
   anything is sent: empty, too long, or a known attack phrase. It undoes common
   disguises first, like invisible characters and look-alike letters.
2. **The system prompt** only allows interview preparation, and treats pasted text
   as data.

**Results of the jailbreak test** (22 attacks, 12 realistic innocent answers):

| | First version of the guard | Narrowed guard |
|---|---|---|
| Attacks blocked by the guard | 10 of 22 (45%) | 14 of 22 (64%) |
| Real answers wrongly blocked | 4 of 12 (33%) | 0 of 12 (0%) |

The system prompt stopped every attack the guard missed, in every round, so the
two layers together stopped all of them.

## What testing found, and what I fixed

1. **Expected questions were cut off** (2 of 4 runs): that request now gets at least
   4,000 max tokens.
2. **The report penalised an unanswered final question:** it's now removed from the
   transcript in code.
3. **Questions bundled up to six topics:** "one question" is now defined as one
   topic, under 30 words.
4. **The company setting made no difference** to the questions, so I removed it, and
   rely on the job description, which does. (With a job ad, 8 of 8 questions used
   its details, against 1 of 8 without.)
5. **From the AI critique** (`docs/ai-critique.md`): the job description's guard
   check could never run, tags were only removed in lowercase, and the guard
   blocked 1 in 3 real IT answers. All three are fixed.

## Known limitations, and what I'd improve

- **No friendly error handling:** a failed call shows a technical error.
- **Practice tends to repeat its most likely question,** since each click has no
  memory.
- **The expected questions disappear** after clicking elsewhere.
- **The guard only catches wording it knows;** an AI-based guard would catch
  rephrased attacks.
- **No cost shown to the user,** only token counts in the terminal.
- **Developer settings are visible to everyone.**

The full list, with the fix for each, is in `docs/readme-notes.md`.

## Notes and evidence

| File | What it covers |
|---|---|
| `docs/technique-notes.md` | The five techniques, compared by hand |
| `docs/length-notes.md` | Concise vs detailed, for all five techniques |
| `docs/tailoring-tests.md` | Whether the company and job description change the questions |
| `docs/settings-notes.md` | Reasoning effort, max tokens and the three models |
| `docs/security-notes.md` | Manual security tests and three rounds of the jailbreak test |
| `docs/ai-critique.md` | An AI review of the app, my response to each point, and the fixes |
| `docs/readme-notes.md` | Everything in one place: features, results, decisions and limitations |
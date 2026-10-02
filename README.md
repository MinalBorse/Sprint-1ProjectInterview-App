# Interview Practice App

An AI interview coach built with Streamlit and OpenRouter: practise answering
interview questions, get feedback on every answer, and take a full mock interview
with a scored report at the end.

Built for Turing College, AI Engineering, Sprint 1.

## What it does and why

<!-- WRITE THIS SECTION IN YOUR OWN WORDS: it's the research requirement.
Answer, in a few sentences each:
- Who is the app for?
- What's hard about practising for interviews alone?
- Why three tabs: expected questions, practice, and a full mock interview?
- Why the settings: the job description, area, seniority, interview type and style?
- Why compare five feedback techniques?
Then delete this comment. -->

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
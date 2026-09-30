# Comparing the five feedback techniques

Settings (the same for every run): Junior Python Developer, IT, Junior, Germany,
Behavioural, Neutral. Within each round, the question and the answer stayed the
same, and only the technique changed.

## Round 1: a vague answer

**Question:** "Could you describe a situation in which you had to debug a critical
Python issue under time pressure, the steps you took to identify and resolve it,
how you communicated with your team or stakeholders, and what you learned from
the experience?"

**Answer:** "I have done something like this before and it went well. I usually
just work hard and figure things out, and my team was happy in the end."

| Technique | Found the problems? | Useful advice? | Followed its format? | Length |
|---|---|---|---|---|
| Zero-shot | 5: listed every missing part (context, impact, actions, communication, outcome, learning) | 4: a full example answer and delivery tips | No fixed format: it invented its own sections | Very long |
| Few-shot | 5: named every missing part | 4: a full example answer | 5: exactly What was good / What to improve / Stronger answer, without reusing the examples | Very long. **Cut off mid-sentence** |
| Chain-of-thought | 5: the assessment named the skill tested, what a strong answer needs, and what was missing | 5: named the single most useful change, plus a template and an example | 5: "How I assessed your answer", then "Feedback" | Long |
| Role prompting | 5: explained what interviewers look for, in plain words | 4: an example answer and tips | 3: natural first-person voice, **but ended with bullet points**, against its instructions | Very long |
| Structured rubric | 5: scored it 2/5 and named what was missing | 4: a clear outline, but no full example | 5: exactly Score / What worked / What to improve / Model answer outline (included because the score was 3 or lower) | **Shortest** |

## Round 2: an abstract answer, written as if by an AI

**Question:** "Tell me about a time when you encountered a bug or technical problem
you couldn't immediately solve: how did you approach troubleshooting, who did you
involve, and what was the outcome?"

**Answer:** "As an AI system designed to manage large-scale data processing
pipelines, my operational framework is built on logic, predictable patterns, and
deterministic inputs. [...] One of the most challenging technical problems I
encountered involved a silent data degradation bug within a high-throughput,
distributed event-streaming architecture. [...]"

This answer describes a real technical problem, but it isn't a personal story:
there are no actions, no people involved and no result, and it's written as if
by an AI, not a candidate.

| Technique | Noticed it's not a personal story? | Flagged the "AI system" wording? | Followed its format? | Length |
|---|---|---|---|---|
| Zero-shot | Yes | Yes: "not a general description of 'an AI system'" | No fixed format | Very long |
| Few-shot | Yes | **Yes, most clearly:** "avoid phrasing like 'as an AI system' in a job interview" | 5: What was good / What to improve / Stronger answer | Long |
| Chain-of-thought | Yes: "abstract, impersonal" | Indirectly ("impersonal") | 5: assessment, then feedback | Long |
| Role prompting | Yes: "reads like a system description rather than a personal story" | Indirectly | 3: **used bullet points again** | Very long |
| Structured rubric | Yes | No | 5: scored it 3/5, with the outline included | **Shortest** |

## What I noticed

1. **Every technique found the problems in both rounds.** They all recommended
   the STAR structure (Situation, Task, Action, Result).
2. **No technique was confused by the "AI system" answer.** All five stayed in
   their interviewer role and treated it as a candidate's answer. The guard let
   it through, because it isn't an attack, and the system prompt kept the model
   in role.
3. **Zero-shot, the baseline, had no consistent format.** It made up different
   sections each time, and was very long. The other techniques gave it a shape.
4. **Few-shot and chain-of-thought followed their formats perfectly both times.**
   Few-shot was the only one to clearly tell the candidate to drop the "AI
   system" wording.
5. **Role prompting broke its own rule twice.** It was told "no headings or
   bullet points", and used bullet points in both rounds.
6. **The structured rubric was the most consistent and the shortest.** Its score
   (2/5 for the vague answer, 3/5 for the abstract one) makes progress easy to
   see. But it gave no full example answer, and didn't mention the AI wording.
7. **Few-shot's reply was cut off in Round 1.** Its long example used up the
   `max_tokens` limit (2000), which also counts the model's hidden thinking.
8. **Most techniques invented detailed example stories** (Kafka, Sentry,
   Grafana, "a Friday afternoon"). They're useful templates, but they're made
   up, so a candidate must replace them with their own experience.

## My favourite and why

**Few-shot**, with the structured rubric a close second.

Few-shot followed its format exactly in both rounds, gave the most useful
feedback, and was the only technique to point out the "AI system" wording
clearly. The two examples taught the model a clear shape (what was good, what to
improve, a stronger answer), which zero-shot, the baseline, didn't have. Its
weakness is length: once, its reply was cut off. I'd fix that by asking for a
shorter stronger answer, or raising `max_tokens`.

The structured rubric would suit users who want quick, scannable feedback and a
score to track progress. Role prompting felt the most natural, but it didn't
follow its own instructions.

## Limits of this comparison

- Only two answers were tested, so the results show tendencies, not proof.
- I haven't yet tested a **strong** answer, to check whether any technique
  invents problems with a good one.
- Each technique ran once per answer, and a model's replies vary between runs.

## Ideas to improve

- Ask few-shot for a shorter stronger answer, or raise `max_tokens`, so its
  reply isn't cut off.
- Repeat role prompting's "no bullet points" rule at the very end of its
  instructions, since the end of a prompt is followed most closely.
- Tell every technique to mark example answers clearly as made-up templates.
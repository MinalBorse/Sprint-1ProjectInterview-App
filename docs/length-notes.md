# Concise vs detailed feedback

Settings: Junior Python Developer, IT, Junior, English, Behavioural, Neutral.
No job description. Model settings: defaults (gpt-5-mini, max tokens 2000).
Tab: Practice. The same question and answer for every run.

Question: "Tell me about a time you had to debug a hard-to-reproduce Python bug:
what steps did you take and what was the outcome?"

My answer (deliberately weak): "I have done something like this before and it went
well. I usually just work hard and figure things out."

I tested all five techniques, in both lengths. Zero-shot, role prompting and the structured
rubric were run twice in each length, to check how consistent they are.

## Results

| Technique | Concise | Detailed | Kept its format in both? |
|---|---|---|---|
| Zero-shot | 2 to 3 sentences: "Too vague... use the STAR format", with what to include (2 runs) | A long guide: what was okay, what's missing, a STAR template, a full model answer, a checklist of techniques, a practice task and delivery tips (2 runs) | n/a (no fixed format) |
| Few-shot | One short paragraph: What was good / What to improve / a one-sentence stronger answer | What was good / What to improve / a full STAR stronger answer, plus delivery tips | ✅ Yes |
| Chain-of-thought | "How I assessed your answer" (3 points), then 2 sentences of feedback | "How I assessed your answer" (3 points), then feedback with sub-sections, a full example answer and "the single change that would improve your answer most" | ✅ Yes |
| Role prompting | One natural paragraph, about 3 sentences, with a one-line example (2 runs) | 3 to 5 natural paragraphs in the interviewer's own voice ("I need...", "I'd expect..."), including a full example answer and advice on how long each part should be (2 runs) | ✅ Yes: no headings or bullet points in any of the 4 runs |
| Structured rubric | Score 2/5, What worked, What to improve, and a short 4-point outline (2 runs, both 2/5) | Score 1/5 and 2/5, What worked, What to improve, and a longer 4-point outline with more examples (2 runs) | ✅ Yes: the same template in all 4 runs; the outline appeared every time, as the score was 3 or lower |

Nothing was cut off: every reply ended properly.

One extra run (with a different question, after clicking New question by mistake)
came back empty. It's left out of this comparison. An empty reply usually means the
model used all of max_tokens on its hidden thinking.

## Tokens, from the terminal log

The input tokens show which technique each call was, because each technique has a
different-sized system prompt. Within each pair, the higher input is Detailed, since
the Detailed instruction is a few tokens longer than the Concise one (always +3).

| Technique | Input tokens (Concise / Detailed) | Concise output | Detailed output | Detailed vs Concise |
|---|---|---|---|---|
| Zero-shot | 317 / 320 | 519 and 388 (average 454) | 1,525 and 1,595 (average 1,560) | about 3.4 times |
| Role prompting | 384 / 387 | 536 and 384 (average 460) | 1,217 and 1,198 (average 1,208) | about 2.6 times |
| Chain-of-thought | 407 / 410 | 803 | 1,444 | about 1.8 times |
| Structured rubric | 428 / 431 | 611 and 685 (average 648) | 1,021 and 876 (average 949) | about 1.5 times |
| Few-shot | 590 / 593 | 999 | 1,063 | about 1.1 times |

The two "New question" requests used 218 input tokens each: the shortest prompt,
since questions have no technique section.

No call reached 2,000 output tokens, which matches nothing being cut off.

**The size of each technique's prompt** (input tokens, smallest first): zero-shot
317, role prompting 384, chain-of-thought 407, structured rubric 428, few-shot 590.
Few-shot's two worked examples add about 270 tokens to every call.

## What I noticed

1. **The length setting works for every technique.** Concise was short in all five,
   and Detailed was clearly longer in all five.
2. **Every technique kept its own format in both lengths,** as the rule says: the
   technique decides the format, and the length decides how much to write. Few-shot
   kept its three headings, chain-of-thought kept its assessment section, and the
   rubric kept its template in both.
3. **Zero-shot changed the most:** from 2 sentences to a long guide, and the most
   output tokens on average (about 3.4 times). With no format of its own,
   nothing holds it back. Role prompting came close (2.6 times): its natural paragraphs can also grow freely.
4. **The techniques with a fixed format changed the least.** The structured rubric
   grew about 1.5 times, and few-shot about 1.1 times: their templates limit how
   much they can grow. Detailed mainly made each part longer, not the reply's shape.
5. **Output tokens don't measure the visible length exactly.** Few-shot's visible
   reply grew a lot from Concise to Detailed, but its output tokens barely changed
   (999 vs 1,063). Output tokens include the model's hidden reasoning, which varies
   between calls.
6. **Few-shot costs more on every call.** Its two worked examples nearly double the
   input (about 590 vs 317 tokens for zero-shot), before it writes a word. In the
   Mock interview, the system prompt is resent every turn, so this adds up. It's a
   trade-off: the technique that follows its format best also costs the most input.
7. **Role prompting followed its "no bullet points" rule in all 4 runs,** in both
   lengths, and kept the interviewer's voice ("I need a concrete example", "In an
   interview I'd expect..."). In earlier tests, it broke that rule twice, so this is
   a clear improvement.
8. **The rubric's score was mostly consistent.** Over 4 runs with the same answer,
   it gave 2/5 three times and 1/5 once (in Detailed). The length setting doesn't
   seem to change the score, but the one 1/5 shows the model's normal variation:
   a single score isn't fully reliable, so a report should rely on more than one.
9. **The Detailed replies invented example stories** (a Django and Celery project,
   a Flask internship, a data ingestion service). They're useful as templates, and
   most say "adapt to your real experience", but a candidate must not repeat them
   as if they were true.

## Which I'd choose as the default, and why

**Concise as the default.** Someone practising wants quick feedback they can act on
straight away, and every technique's Concise reply named the main problem and the
fix (use STAR, with concrete steps and a result). It's also cheaper: zero-shot's
Concise replies used less than a third of the output tokens of its Detailed ones.
**Detailed is better when studying one answer properly,** because it adds a full
model answer and a structure to follow.

Combined with my technique comparison, **few-shot with Concise** gives clear,
consistent feedback in three short parts, which is a good default for practising,
accepting that its examples make each call's input larger.

## Limits

- One question and one answer only, and one run per combination (two for zero-shot, role prompting and the rubric).
- Lengths were judged by reading, plus the output tokens, which include the hidden
  reasoning, so they're only a rough measure of the visible length.
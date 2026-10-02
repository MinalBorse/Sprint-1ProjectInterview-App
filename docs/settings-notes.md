# Model settings experiments

Settings: Junior Python Developer, IT, Junior, English, Behavioural, Neutral, Concise.
No job description. Technique: Zero-shot. Tab: Practice.
The same question for every run, and the same answer within each experiment.

Question: "Tell me about a time you fixed a critical bug in Python under time
pressure; what steps did you take and what was the outcome?"

My answer: in Experiments 1 and 2, only my job title (299 input tokens). In
Experiment 3, my usual weak answer, "I have done something like this before and it
went well. I usually just work hard and figure things out." (317 input tokens).

Output tokens come from the terminal log. They include the model's hidden thinking,
which is billed as output but never shown. Waiting times were measured roughly with
a stopwatch.

## Experiment 1: Reasoning effort (GPT-5 mini, max tokens 2000)

| Effort | Output tokens | Wait (seconds) | Feedback quality |
|---|---|---|---|
| minimal | 80 and 71 | 2 | 3 sentences: found the main problem (no example) and said to use STAR. Correct but general |
| low | 269 | 8 | STAR, plus examples of what to include (timelines, libraries, logs, verifying the fix) |
| medium | 408 and 553 | 10 | STAR, plus a tip to practise a 60 to 90 second version |
| high | 1,256 | 14 | STAR, plus Python-specific details (stack trace, debugger, unit tests, CI) |

From minimal to high, output tokens rose about 17 times and the wait about 7 times,
but every reply found the same main problem and gave the same main advice. Higher
effort added details, not a different diagnosis.

The visible feedback was about the same length every time (about 60 to 90 words),
so most of the extra tokens were hidden thinking: about 75 tokens at minimal is
almost just the reply, while about 1,150 of the 1,256 at high were thinking.

The default effort (no effort sent) used 388 to 519 output tokens in earlier runs,
about the same as medium here, so the model's default behaves roughly like medium.

## Experiment 2: Max tokens too low (GPT-5 mini, max tokens 500)

| Effort | Output tokens | What appeared on the page |
|---|---|---|
| high | 448 (twice) | "None", after 20 seconds: no feedback at all |
| minimal | 87 | Complete feedback, after 5 seconds |

With high effort, the model used its budget thinking, stopping near the limit (448
tokens reported, both times), and wrote nothing, so the page showed "None". With
minimal effort, the same limit was plenty (87 tokens), and the feedback was complete.

The same limit failed or worked depending only on how much the model thought, which
shows the hidden thinking counts towards max_tokens. The failed runs were still
billed for about 448 tokens each. A limit that's too low isn't cheaper: it wastes
both money and time.

## Experiment 3: Models (effort default, max tokens 2000)

| Model | Output tokens | Wait (seconds) | Feedback quality |
|---|---|---|---|
| GPT-5 mini | 395 | 7 | STAR, with what to include (how you reproduced the bug, tools, fix, tests or rollback) and "quantify the impact" |
| GPT-5 nano | 1,647 | 18 | STAR, plus a full example answer with numbers ("downtime dropped from 30 minutes to 2 minutes") |
| GPT-5 | none | instant | Blocked: "Model blocked by guardrail". The app crashed with a red technical traceback |

**Nano used about 4 times the output tokens of mini, and took about 2.5 times as
long,** for feedback of similar quality: both found the same problem, and nano only
added an example answer. This matches my earlier observations, where nano used about
550 to 2,000 output tokens per call against about 180 to 480 for mini, and twice hit
the 2,000 limit.

**So "cheaper per token" doesn't mean "cheaper per reply".** Nano costs less per
token, but if it uses 4 times as many, it's only cheaper per reply if its price per
token is less than a quarter of mini's. The prices on OpenRouter's models page would
settle it.

**GPT-5 is on the course's list of allowed models, but it's blocked on the course
account,** as I also found in my other version of the app.

## Temperature

Not offered: none of the GPT-5 models supports it. Developer settings say so in a
note, so the missing setting isn't confusing.

## What I learned

1. **Reasoning effort mostly changes the cost and the wait, not the main advice.**
   For a simple, weak answer, minimal effort already found the problem; higher
   effort added useful details, at up to 17 times the tokens.
2. **max_tokens includes the hidden thinking.** With high effort and 500 max tokens,
   the model ran out of room while thinking and wrote nothing, but was still billed.
3. **The smallest model isn't automatically the cheapest.** Nano thought much longer
   than mini, using 4 times the tokens and taking 2.5 times as long.
4. **Output tokens measure thinking plus writing,** so they're a guide to cost, not
   to how long the visible reply is.
5. **Two failures showed unhelpful messages:** "None" when the budget ran out, and a
   raw technical traceback when GPT-5 was blocked. Friendly error handling would
   explain both, for example "The model ran out of room while thinking: raise Max
   tokens" and "This model isn't available on your account: choose GPT-5 mini".

## My default settings, and why

**GPT-5 mini, default reasoning effort, and 2,000 max tokens.** Mini gave useful
feedback quickly (7 seconds, 395 tokens), and was faster and used far fewer tokens
than nano. The default effort behaves about like medium: a balance between detail
and cost. And 2,000 max tokens left room even for high effort (1,256 tokens), so a
normal reply never runs out. The expected questions get at least 4,000, since a list
of 8 needs more room.

## Limits

- One question, and one or two runs per setting, so small differences may be chance.
- The answer was different in Experiment 3 from Experiments 1 and 2, but the same
  within each experiment, which is what the comparisons need.
- Waiting times were measured by hand, so they're rough.
- I didn't compare actual costs in money, only tokens: the model prices would be
  needed for that.
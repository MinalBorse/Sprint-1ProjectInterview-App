# Tailoring tests: do the settings actually change the questions?

## Test 1: Company (removed afterwards)

Settings: Junior Python Developer, IT, Junior, English, Mixed, Neutral.
With the company set to SAP, none of the expected questions mentioned SAP or its
industry, even though the system prompt contained "Company: SAP" and a company rule.

Why: the rule also said not to invent facts and to keep it general, so the model
stayed general. Decision: removed the company setting, and rely on the job
description instead, which gives the model real information.

The country setting was removed at the same time: since the language setting was
added, its only effect was the tone, which the interviewer style already controls.
Bonus: the system prompt got about 40% shorter (about 259 to 160 input tokens).

## Test 2: Job description

Settings: Junior Python Developer, IT, Junior, English, Mixed, Neutral, Concise.
Tab: Expected questions (8 questions each run).

Distinctive details in the made-up ad: insurance, claims, FastAPI, PostgreSQL,
Docker, Kubernetes, pytest, code reviews, non-technical colleagues, Celery, GDPR.

Counting rule: a question counts if its question, "Why" or "Tip" mentions any of
these details.

| Run | Job description? | Questions using the ad's details | Which details |
|---|---|---|---|
| A | No | 1 of 7 (cut off at Q7) | pytest (in Q6's tip, by chance) |
| B | No | 1 of 8 | pytest (in Q7's tip, by chance) |
| C | Yes | 8 of 8 | FastAPI, claims, PostgreSQL, pytest, non-technical, Docker, Kubernetes, Celery, GDPR, insurance (10 of 11; only code reviews missing) |
| D | Yes | 7 of 7 (cut off at Q8) | FastAPI, insurance, claims, Celery, pytest, PostgreSQL, Kubernetes, Docker, non-technical, code reviews (10 of 11; only GDPR missing) |

Note on Runs C and D: the tips also suggested related tools that aren't in the ad
(SQLAlchemy, Pydantic, docker-compose). They're common companions of the ad's
stack, given as suggestions, not claimed as job requirements.

### Practice feedback with the ad

The question was built from the ad (FastAPI, claims handlers, Celery, GDPR, pytest,
PostgreSQL), and the feedback followed it too: Pydantic models, Celery tasks, GDPR
measures (encryption, access control, deletion), and pytest strategies.

But the one question asked about six things at once (endpoint design, validation,
file storage, Celery, GDPR and testing), which is a lot for a Junior candidate.

### Mock interview with the ad

The first question used the ad ("especially any of FastAPI, PostgreSQL, Docker,
pytest"). The follow-up question built on my answer (the notification queue I
mentioned), which shows the conversation memory working.

The report was fair overall: it quoted my answer, scored 6/10, and said the
evidence was limited, since I answered only one question. But it marked me down
for not describing the database design, which was the last question, and I never
answered it, because I ended the interview straight after.

### Conclusion

Without the ad, 1 of 7 and 1 of 8 questions used its details, both times pytest,
by chance. With it, 8 of 8 and 7 of 7 did, covering 10 of the 11 details each
time, including specific ones like insurance claims, non-technical colleagues,
GDPR and code reviews. The Practice and Mock interview tabs followed the ad too.

The job description clearly works, unlike the company setting, so relying on it
instead was the right choice.

## Problems found by these tests, and how I fixed them

### 1. Expected questions cut off

**Problem:** in 2 of the 4 runs (A and D), the reply stopped before the 8th
question, because 8 detailed questions plus the model's hidden thinking need more
than max_tokens=2000.

**Fix:** call_model now takes an optional min_tokens, and only the expected
questions use 4000. Every other call keeps the slider's value, so the cost ceiling
only rises where it's needed. A note under the slider would make this exception
visible (optional).

**Checked:** all 8 questions arrived complete in every run after the fix, and the
log showed max_tokens=4000 for the expected questions and 2000 for Practice.

### 2. The report counted an unanswered final question

**Problem:** when the candidate ends the interview, the conversation ends with the
interviewer's next question, which nobody answered. The assessor treated it as a
skipped question, and marked the candidate down ("when asked about database
design, you did not...").

**Fix:** in code, not only in the prompt. build_transcript now leaves out the
interviewer's last message when nobody answered it, so the assessor never sees the
unanswered question. A rule in the assessor prompt is a backup: "Only judge the
answers that are in the transcript."

**Checked:** the unanswered follow-up asked about pytest, fixtures, code reviews,
Docker and CI. The report mentioned none of these, no longer said "when asked
about...", and judged only the one answer given.

### 3. Questions bundled several topics

**Problem:** the prompts said "ask one question", and the model obeyed literally:
one sentence, but with up to six topics (about 50 words), especially with a
detailed job description.

**Fix:** a shared rule, ONE_TOPIC_RULE, defines "one question" as one topic, under
30 words, and tells the model to spread the job description's skills across
different questions instead. It's in the shared part of the system prompt, so it
applies to every tab from one place.

**Checked:**

| Where | Before | After |
|---|---|---|
| Practice, no ad | (not tested) | 3 questions, 1 topic each, about 19 to 21 words |
| Practice, with ad | 1 question with 6 topics, about 50 words | 3 questions, 1 topic each, about 19 to 27 words |
| Mock interview, with ad | 1 follow-up with 4 topics | 5 questions, 1 topic each, about 14 to 22 words |
| Expected questions, with ad | (mostly fine) | 8 questions, 1 topic each, about 12 to 18 words |

The expected questions now spread the ad across all 8: non-technical colleagues,
FastAPI, PostgreSQL, Docker, Kubernetes, pytest, code reviews, and claims handlers.
Only the "nice to have" skills, Celery and GDPR, were left out.

## Known limitations (found while testing, not fixed yet)

1. **Practice repeats its most likely question.** Without the ad, all 3 questions
   were about fixing a bug; with it, all 3 were about working with non-technical
   stakeholders. Each "New question" click is a one-time call with no memory.
   Possible fix: remember the questions already asked, and tell the model not to
   repeat them.
2. **The interviewer accepts answers that miss the question.** In the Mock
   interview, I answered about scope changes instead of pytest, and the
   interviewer said "Nice" and moved on. Possible fix: "If an answer doesn't
   address the question, say so kindly, and ask it again."
3. **The interview type drifts in the Mock interview.** With "Behavioural"
   selected, 4 of 5 Mock interview questions were technical, following the ad's
   skills. In the Expected questions tab, "Behavioural" was followed perfectly.
   Possible fix: "The interview type decides the kind of question; the job
   description decides what it's about."
4. **The expected questions disappear after other clicks,** because they aren't
   saved in st.session_state. Possible fix: save them, as the practice question
   already is.
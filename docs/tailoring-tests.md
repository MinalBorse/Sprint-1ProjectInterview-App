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
With a detailed ad, the model tried to fit every detail into one question.

### Mock interview with the ad

The first question used the ad ("especially any of FastAPI, PostgreSQL, Docker,
pytest"). The follow-up question built on my answer (the notification queue I
mentioned), which shows the conversation memory working.

The report was fair overall: it quoted my answer, scored 6/10, and said the
evidence was limited, since I answered only one question. But it marked me down
for not describing the database design, which was the last question, and I never
answered it, because I ended the interview straight after. The assessor prompt
doesn't say what to do with an unanswered final question, so the model guessed.

## Conclusion

Without the ad, 1 of 7 and 1 of 8 questions used its details, both times pytest,
by chance. With it, 8 of 8 and 7 of 7 did, covering 10 of the 11 details each
time, including specific ones like insurance claims, non-technical colleagues,
GDPR and code reviews. The Practice and Mock interview tabs followed the ad too.

The job description clearly works, unlike the company setting, so relying on it
instead was the right choice.

## Problems found by these tests

1. **Expected questions cut off:** in 2 of the 4 runs (A and D), the reply stopped
   before the 8th question, because 8 detailed questions plus the model's hidden
   thinking need more than max_tokens=2000.
2. **The report counts an unanswered final question:** the assessor marked me down
   for a question I never had the chance to answer.
3. **Questions can bundle several topics:** with a detailed ad, one question asked
   about six things at once.

 **Fixed:** call_model now takes an optional min_tokens, and the expected
   questions use 4000. Checked: all 8 questions arrived in 3 runs (the log showed
   max_tokens=4000), and Practice still used 2000.
   **Fixed:** build_transcript now leaves out the interviewer's last message when
   nobody answered it, so the assessor never sees the unanswered question. A rule
   in the assessor prompt is a backup. Checked: after one answer, the report no
   longer mentioned the unanswered follow-up question.

   - Known limitation: the expected questions disappear after clicking elsewhere,
  because they aren't saved in st.session_state. Fix: save them, as the practice
  question already is.
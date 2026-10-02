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

## Test 3: Job description

Settings: Junior Python Developer, IT, Junior, English, Mixed, Neutral, Concise.
Tab: Expected questions (8 questions each run).

Distinctive details in the made-up ad: insurance, claims, FastAPI, PostgreSQL,
Docker, Kubernetes, pytest, code reviews, non-technical colleagues, Celery, GDPR.

| Run | Job description? | Questions using the ad's details (of 8) | Which details |
|---|---|---|---|
| A | No | | |
| B | No | | |
| C | Yes | | |
| D | Yes | | |

Practice feedback with the ad: did it mention anything from the ad?
Mock interview with the ad: did the questions follow the ad?

Conclusion:
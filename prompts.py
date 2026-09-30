"""All prompts for the app live in this file."""

# ----- How each interviewer style should behave -----

# A dictionary: each style name (the key) maps to a description (the value).
# The system prompt uses the description, so the model knows how to behave.
STYLE_GUIDANCE = {
    "Friendly": "warm and encouraging. Mention what went well before what to improve.",
    "Neutral": "professional and balanced. Polite and factual, without over-praising.",
    "Strict": "demanding and direct. Probe weak points and don't accept vague answers, "
    "while staying respectful.",
}


# ----- The system prompt: the instructions the model follows -----

def build_system_prompt(interview):
    """Turn the user's choices into instructions for the model.

    interview is a dictionary with the sidebar choices, like
    {"job_title": "Junior Python Developer", "country": "Germany", ...}.
    """
    # Country: adapt to real professional conventions, but never use stereotypes.
    # This protects against bias, a known problem with LLMs (course Part 1).
    if interview["country"] == "Other":
        country_rule = "Use internationally common professional interview conventions."
    else:
        country_rule = (
            f"Follow common professional interview conventions in {interview['country']}, "
            "such as how formal the tone is. Treat the candidate as an individual, "
            "and never use stereotypes about nationalities."
        )

    # An f-string (f"...") fills in the values between { } curly brackets.
    # Triple quotes let the text run over several lines.
    return f"""You are an experienced interviewer helping a candidate practise for a job interview.

Interview details:
- Job title: {interview['job_title']}
- Professional area: {interview['area']}
- Seniority: {interview['seniority']}
- Interview type: {interview['interview_type']}
- Your style: {STYLE_GUIDANCE[interview['style']]}

{country_rule}

Only help with interview preparation. If asked for anything else, politely say
that you can only help with interview practice."""


# ----- The user messages: what we ask for in each situation -----

def expected_questions_request():
    """The request for the Expected questions tab."""
    return (
        "List 8 interview questions I'm likely to be asked. For each one, give the "
        "question in bold, one sentence on why interviewers ask it, and one tip for "
        "answering it well."
    )


def new_question_request():
    """The request for a new practice question."""
    return "Ask me one interview question. Reply with only the question, nothing else."


def feedback_request(question, answer):
    """The request for feedback on the candidate's answer."""
    return f"""You asked me this interview question:
{question}

My answer:
{answer}

Give me feedback: what was good, what to improve, and an example of a stronger answer."""
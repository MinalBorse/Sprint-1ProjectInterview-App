"""The web page: what the user sees and clicks."""

# =============================================================================
# Imports
# =============================================================================

# Built into Python: turns a dictionary into JSON text, for the download button.
import json

# Streamlit builds the web page. "as st" is a short nickname for it.
import streamlit as st

# guards.py: the security checks.
from guards import (
    MAX_ANSWER_CHARS,  # the longest answer we accept
    MAX_INTERVIEW_ANSWERS,  # the most answers in one mock interview
    MAX_JD_CHARS,  # the longest job description
    MAX_JOB_TITLE_CHARS,  # the longest job title
    check_user_text,  # returns None if the text is fine, or a message if not
)

# llm.py: the only file that calls the model.
from llm import MODELS, REASONING_EFFORTS, ask_model, ask_model_json

# prompts.py: the words we send to the model.
from prompts import (
    KICKOFF_MESSAGE,  # the hidden first message that starts a mock interview
    REPORT_SCHEMA,  # the shape of the end-of-interview report (a JSON schema)
    TECHNIQUES,  # the five feedback techniques, by name
    build_system_prompt,  # builds the instructions from the user's choices
    expected_questions_request,  # the request for the Expected questions tab
    feedback_request,  # the request for feedback on an answer
    new_question_request,  # the request for one practice question
    report_messages,  # builds the messages for the report's assessor
)

# style.py: the look of the app.
from style import add_calm_style, show_welcome

# =============================================================================
# Page setup
# =============================================================================

# The browser tab's title and icon. This must be the first Streamlit command.
st.set_page_config(page_title="Interview Practice", page_icon="🌿")

# The leaf background, the content panel, the fonts and the soft styles.
add_calm_style()

st.title("Practise your interview")

# A warm welcome, with what the app offers, shown with check marks.
show_welcome(
    "<b>Welcome. Take a slow breath: you're in a calm place to practise.</b><br>"
    "There's no pressure here, only chances to learn.<br><br>",
    [
        "A mock interview that remembers your whole conversation",
        "Feedback on every answer, in five different styles",
        "An honest report with scores at the end",
        "Questions tailored to your role and job description",
    ],
)

# =============================================================================
# Sidebar: the user describes their interview
# =============================================================================

with st.sidebar:
    st.header("Your interview")

    # A text box. max_chars stops the user typing more than the limit.
    job_title = st.text_input("Job title", "Junior Python Developer", max_chars=MAX_JOB_TITLE_CHARS)

    # An optional job description, so the questions fit this exact position.
    # This is the ONLY place the job description box is created.
    job_description = st.text_area(
        "Job description (optional)",
        height=150,
        max_chars=MAX_JD_CHARS,
        placeholder="Paste the job ad here",
    )

    # Drop-down menus. index=1 selects the second option at the start.
    area = st.selectbox(
        "Professional area",
        ["IT", "Marketing", "Finance", "HR", "Sales", "Healthcare", "Other"],
    )
    seniority = st.selectbox(
        "Seniority", ["Intern", "Junior", "Mid-level", "Senior", "Lead"], index=1
    )
    language = st.selectbox("Interview language", ["English", "German"])
    interview_type = st.selectbox(
        "Interview type", ["Behavioural", "Technical", "Case study", "Mixed"]
    )

    # Round buttons where only one can be chosen.
    style = st.radio("Interviewer style", ["Friendly", "Neutral", "Strict"], index=1)
    feedback_length = st.radio("Feedback length", ["Concise", "Detailed"], horizontal=True)

    # Developer settings, kept apart from the interview choices,
    # because a normal user doesn't need to know what "few-shot" means.
    with st.expander("Developer settings"):
        technique = st.selectbox("Feedback technique", list(TECHNIQUES))

        # format_func shows the friendly label, while the code gets the slug.
        model = st.selectbox("Model", list(MODELS), format_func=MODELS.get)

        # A slider: label, smallest, largest, starting value, and step size.
        max_tokens = st.slider("Max tokens", 500, 4000, 2000, 250)
        st.caption(
            "The expected questions always get at least 4,000, so the list of 8 isn't cut off."
        )

        # "default" means: don't send a reasoning effort, let the model decide.
        effort_choice = st.selectbox("Reasoning effort", ["default"] + REASONING_EFFORTS)
        reasoning_effort = None if effort_choice == "default" else effort_choice

        st.caption("Temperature isn't offered: the GPT-5 models don't support it.")

        # A developer tool, to see exactly what the model was told.
        show_prompt = st.checkbox("Show system prompts")

# =============================================================================
# Security: check what the user typed, before it goes into any prompt
# =============================================================================

# The job title goes straight into the system prompt, so it could carry an attack.
job_title_problem = check_user_text(job_title, MAX_JOB_TITLE_CHARS)
if job_title_problem:
    st.error(f"Job title: {job_title_problem}")
    # st.stop() ends this run here: nothing below is drawn, so nothing is sent.
    st.stop()

# FIX (from the AI critique): this check used to be pasted INSIDE the job title's
# "if", after st.stop(), so it could never run. It's now its own step, at the left
# edge. The job description is optional, so it's only checked if something was
# pasted: otherwise an empty box would be blocked as "Please type something first."
if job_description.strip():
    jd_problem = check_user_text(job_description, MAX_JD_CHARS)
    if jd_problem:
        st.error(f"Job description: {jd_problem}")
        st.stop()

# =============================================================================
# Collect the choices
# =============================================================================

# All the interview choices in one dictionary, so they can be passed around together.
interview = {
    "job_title": job_title,
    "job_description": job_description.strip(),  # empty text if none was pasted
    "area": area,
    "seniority": seniority,
    "language": language,
    "interview_type": interview_type,
    "style": style,
    "feedback_length": feedback_length,
}

# The model settings, bundled so they can be passed to every call at once.
# The keys must match the names of ask_model's inputs exactly.
model_settings = {
    "model": model,
    "max_tokens": max_tokens,
    "reasoning_effort": reasoning_effort,
}

# =============================================================================
# Helper functions
# =============================================================================


def call_model(user_request, technique=None, min_tokens=None):
    """Send the system prompt plus one request to the model, and return the reply.

    technique is only passed for feedback; the question requests leave it out.
    min_tokens is for long replies: it makes sure max_tokens is at least this much.
    """
    messages = [
        {"role": "system", "content": build_system_prompt(interview, technique)},
        {"role": "user", "content": user_request},
    ]
    # A COPY of the settings, so changing max_tokens here doesn't change other calls.
    settings = dict(model_settings)
    if min_tokens is not None:
        # max() gives the bigger number: min_tokens, or the slider if it's higher.
        settings["max_tokens"] = max(settings["max_tokens"], min_tokens)
    return ask_model(messages, **settings)


def for_api(messages):
    """Copy the messages with only "role" and "content".

    The API doesn't accept extra keys like "hidden", which is only for our app.
    """
    return [{"role": m["role"], "content": m["content"]} for m in messages]


def build_transcript(chat):
    """Turn the chat into plain text for the assessor.

    Only the visible conversation: no system prompt, no hidden kickoff message,
    and no final question the candidate never had the chance to answer.
    """
    visible = [m for m in chat if m["role"] != "system" and not m.get("hidden")]
    # If the chat ends with the interviewer (a question nobody answered), leave it out.
    if visible and visible[-1]["role"] == "assistant":
        visible = visible[:-1]
    lines = []
    for message in visible:
        speaker = "Interviewer" if message["role"] == "assistant" else "Candidate"
        lines.append(f"{speaker}: {message['content']}")
    return "\n\n".join(lines)


def show_report(report):
    """Show the report: the scores in boxes, then the summary and the lists."""
    st.subheader("Your interview report")

    col_score, col_ready = st.columns(2)
    col_score.metric("Overall score", f"{report['overall_score']}/10")
    col_ready.metric("Readiness", report["readiness"])

    st.write(report["summary"])

    scores = report["scores"]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Communication", f"{scores['communication']}/5")
    col2.metric("Technical depth", f"{scores['technical_depth']}/5")
    col3.metric("Structure", f"{scores['structure']}/5")
    col4.metric("Relevance", f"{scores['relevance']}/5")

    st.markdown("**Strengths**")
    for item in report["strengths"]:
        st.markdown(f"- {item}")

    st.markdown("**To improve**")
    for item in report["improvements"]:
        st.markdown(f"- {item}")

    st.markdown("**Next steps**")
    for item in report["next_steps"]:
        st.markdown(f"- {item}")

    st.download_button(
        "Download report (JSON)",
        json.dumps(report, indent=2, ensure_ascii=False),
        file_name="interview_report.json",
        mime="application/json",
    )


# =============================================================================
# The three tabs
# =============================================================================

# The order of this list is the order of the tabs. The first one opens by default.
tab_interview, tab_practice, tab_expected = st.tabs(
    ["Mock interview", "Practice", "Expected questions"]
)

# -----------------------------------------------------------------------------
# Tab 1: Mock interview (a chatbot that remembers the conversation)
# -----------------------------------------------------------------------------

with tab_interview:
    st.write("A full mock interview. The interviewer remembers the whole conversation.")

    # The whole conversation and the report, kept between reruns.
    if "chat" not in st.session_state:
        st.session_state.chat = []
    if "report" not in st.session_state:
        st.session_state.report = None

    col_start, col_restart = st.columns(2)

    if col_start.button("Start interview"):
        # Build the first messages in a separate list first. The system prompt is
        # built ONCE, from the current settings, so the whole interview keeps the
        # same rules. The hidden kickoff gives the model something to reply to.
        first_messages = [
            {
                "role": "system",
                "content": build_system_prompt(interview, technique, chat=True),
            },
            {"role": "user", "content": KICKOFF_MESSAGE, "hidden": True},
        ]
        with st.spinner("The interviewer is getting ready..."):
            reply = ask_model(for_api(first_messages), **model_settings)
        # FIX (from the AI critique): only save the interview if a reply arrived,
        # so an empty reply can't leave a half-started chat.
        if reply:
            st.session_state.chat = first_messages + [{"role": "assistant", "content": reply}]
            st.session_state.chat_interview = interview  # the settings, for the report
            st.session_state.report = None
        else:
            st.warning("The interviewer couldn't reply. Please try again.")

    if col_restart.button("Restart"):
        st.session_state.chat = []
        st.session_state.report = None
        st.rerun()

    # Show the conversation so far, skipping what the user shouldn't see.
    for message in st.session_state.chat:
        if message["role"] == "system" or message.get("hidden"):
            continue
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Developer tool: the interview's system prompt is the first message in the chat.
    if show_prompt and st.session_state.chat:
        with st.expander("System prompt for this interview"):
            st.code(st.session_state.chat[0]["content"])

    # Everything below only appears once the interview has started.
    if st.session_state.chat:
        answers = [m for m in st.session_state.chat if m["role"] == "user" and not m.get("hidden")]

        # The report button: only once a question has been answered, and only once.
        if answers and st.session_state.report is None:
            if st.button("End & get report"):
                with st.spinner("Writing your report..."):
                    st.session_state.report = ask_model_json(
                        report_messages(
                            st.session_state.get("chat_interview", interview),
                            build_transcript(st.session_state.chat),
                        ),
                        REPORT_SCHEMA,
                    )
                st.rerun()

        if st.session_state.report:
            show_report(st.session_state.report)

        if len(answers) >= MAX_INTERVIEW_ANSWERS:
            # Every turn resends the whole conversation, so long chats cost more.
            st.info(
                "You've reached the answer limit for one interview. Click Restart to begin again."
            )
        else:
            # The chat box is greyed out once the interview has a report.
            answer = st.chat_input(
                "Type your answer",
                max_chars=MAX_ANSWER_CHARS,
                disabled=st.session_state.report is not None,
            )
            if answer:
                problem = check_user_text(answer, MAX_ANSWER_CHARS)
                if problem:
                    # Blocked: show why, and DON'T add it to the history,
                    # or it would be resent to the model on every later turn.
                    st.warning(problem)
                else:
                    # FIX (from the AI critique): send the history PLUS the new
                    # answer, but only SAVE both once the reply has arrived. If the
                    # call fails or the reply is empty, the history stays as it was,
                    # instead of keeping an answer with no reply.
                    new_answer = {"role": "user", "content": answer}
                    with st.spinner("The interviewer is thinking..."):
                        reply = ask_model(
                            for_api(st.session_state.chat + [new_answer]),
                            **model_settings,
                        )
                    if reply:
                        st.session_state.chat.append(new_answer)
                        st.session_state.chat.append({"role": "assistant", "content": reply})
                        # Draw the page again, so the new messages appear above.
                        st.rerun()
                    else:
                        st.warning("The interviewer couldn't reply. Please send your answer again.")

# -----------------------------------------------------------------------------
# Tab 2: Practice (one question, one answer, one piece of feedback)
# -----------------------------------------------------------------------------

with tab_practice:
    st.write("Get a question, type your answer, and get feedback.")

    # The question survives reruns in st.session_state. None means "no question yet".
    if "question" not in st.session_state:
        st.session_state.question = None

    if st.button("New question"):
        with st.spinner("Choosing a question..."):
            st.session_state.question = call_model(new_question_request())

    if st.session_state.question:
        st.markdown(f"**Question:** {st.session_state.question}")

        answer = st.text_area("Your answer", height=200, max_chars=MAX_ANSWER_CHARS)

        if st.button("Get feedback"):
            # The guard checks for empty, too long, and attack phrases.
            problem = check_user_text(answer, MAX_ANSWER_CHARS)
            if problem:
                st.warning(problem)
            else:
                # The model doesn't remember asking the question, so
                # feedback_request puts the question into the message.
                with st.spinner("Reading your answer..."):
                    feedback = call_model(
                        feedback_request(st.session_state.question, answer), technique
                    )
                st.markdown(feedback)

                # FIX (from the AI critique): this block used to appear twice,
                # so the expander was shown twice. It's here once now.
                if show_prompt:
                    with st.expander("System prompt that was sent"):
                        st.code(build_system_prompt(interview, technique))

# -----------------------------------------------------------------------------
# Tab 3: Expected questions (one call per click)
# -----------------------------------------------------------------------------

with tab_expected:
    st.write("See the questions you're likely to be asked, with a tip for each.")

    if st.button("Show expected questions"):
        with st.spinner("Thinking of questions..."):
            # 8 questions, each with a "why" and a "tip", plus the model's hidden
            # thinking, can need more than 2000 tokens, so give this request more room.
            reply = call_model(expected_questions_request(), min_tokens=4000)
        st.markdown(reply)

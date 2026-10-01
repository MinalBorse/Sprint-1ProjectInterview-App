"""The web page: what the user sees and clicks."""

# ----- Imports -----
# Built into Python: turns a dictionary into JSON text, for the download button.
import json

# Streamlit builds the web page. "as st" is a short nickname for it.
import streamlit as st

# NEW (Step 5): guards.py, the security checks.
# MAX_... are the length limits, and check_user_text is the guard itself.
from guards import (
    MAX_ANSWER_CHARS,
    MAX_COMPANY_CHARS,
    MAX_INTERVIEW_ANSWERS,
    MAX_JD_CHARS,
    MAX_JOB_TITLE_CHARS,
    check_user_text,
)

# Our own files.
# llm.py: sends messages to the model.
from llm import MODELS, REASONING_EFFORTS, ask_model, ask_model_json

# prompts.py: the words we send to the model.
from prompts import (
    KICKOFF_MESSAGE,
    REPORT_SCHEMA,  # the shape of the report (a JSON schema)
    TECHNIQUES,
    build_system_prompt,  # system prompt
    expected_questions_request,
    feedback_request,
    new_question_request,
    report_messages,  # builds the messages for the assessor
)

# ----- Page setup -----

# The browser tab's title and icon. This must be the first Streamlit command.
st.set_page_config(page_title="Interview Practice", page_icon="🎯")

# The big heading at the top of the page.
st.title("Interview Practice")


# ----- Sidebar: the user describes their interview -----

# Everything inside "with st.sidebar:" appears in the left-hand sidebar.
with st.sidebar:
    st.header("Your interview")

    # A text box. The second value is what's in it at the start.
    # NEW (Step 5): max_chars stops the user typing more than the limit.
    job_title = st.text_input("Job title", "Junior Python Developer", max_chars=MAX_JOB_TITLE_CHARS)

    # NEW: an optional company name, so questions can fit that company.
    # placeholder is grey hint text, shown only while the box is empty.
    company = st.text_input(
        "Company (optional)",
        "",
        max_chars=MAX_COMPANY_CHARS,
        placeholder="For example: SAP, Siemens, Zalando",
    )

    # NEW: an optional job description, so questions fit this exact position.
    job_description = st.text_area(
        "Job description (optional)",
        height=150,
        max_chars=MAX_JD_CHARS,
        placeholder="Paste the job ad here",
    )

    # Drop-down menus. index=1 selects the second option at the start (counting from 0).
    area = st.selectbox(
        "Professional area", ["IT", "Marketing", "Finance", "HR", "Sales", "Healthcare", "Other"]
    )
    seniority = st.selectbox(
        "Seniority", ["Intern", "Junior", "Mid-level", "Senior", "Lead"], index=1
    )
    country = st.selectbox(
        "Country", ["Germany", "United Kingdom", "United States", "India", "Other"]
    )

    # NEW: the interview language, chosen separately from the country,
    # so an interview "in Germany" doesn't automatically become German.
    language = st.selectbox("Interview language", ["English", "German"])

    interview_type = st.selectbox(
        "Interview type", ["Behavioural", "Technical", "Case study", "Mixed"]
    )

    # Round buttons where only one can be chosen.
    style = st.radio("Interviewer style", ["Friendly", "Neutral", "Strict"], index=1)
    # How long the feedback should be. horizontal=True puts the choices side by side.
    feedback_length = st.radio("Feedback length", ["Concise", "Detailed"], horizontal=True)
    # Developer settings, kept apart from the interview choices,
    # because a normal user doesn't need to know what "few-shot" means.
    # st.expander is a section that opens when clicked.
    with st.expander("Developer settings"):
        # list(TECHNIQUES) gives the five technique names as the menu options.
        technique = st.selectbox("Feedback technique", list(TECHNIQUES))
        # ----- Model settings -----

        # A menu of the allowed models.
        # list(MODELS) gives the keys (the slugs) as the options.
        # format_func=MODELS.get shows each option through MODELS.get, which looks
        # up its friendly label. So the code gets "openai/gpt-5-mini", and the
        # user sees "GPT-5 mini (default, balanced)".
        model = st.selectbox("Model", list(MODELS), format_func=MODELS.get)

        # A slider. Its inputs, in order: the label, the smallest value, the largest
        # value, the starting value, and the step size.
        # The largest value is 4000, a firm cap on how much one reply can cost.
        max_tokens = st.slider("Max tokens", 500, 4000, 2000, 250)

        # A menu of reasoning efforts. ["default"] + REASONING_EFFORTS joins two lists,
        # so the menu starts with "default", followed by minimal, low, medium, high.
        effort_choice = st.selectbox("Reasoning effort", ["default"] + REASONING_EFFORTS)

        # A one-line if/else. "default" becomes None, which means "don't send an
        # effort, let the model decide". Any other choice is used as it is.
        reasoning_effort = None if effort_choice == "default" else effort_choice

        # A small grey note, so it's clear why there's no temperature setting.
        st.caption("Temperature isn't offered: the GPT-5 models don't support it.")
        # A developer tool, to see exactly what the model was told.
        # st.checkbox returns True when ticked, and False when not.
        show_prompt = st.checkbox("Show system prompts")


# ----- NEW (Step 5) Security: check the job title before it goes into any prompt -----

# The job title goes straight into the system prompt, so someone could type an attack
# there instead of a real title. check_user_text returns None if it's fine,
# or a message explaining the problem.
job_title_problem = check_user_text(job_title, MAX_JOB_TITLE_CHARS)
if job_title_problem:
    st.error(f"Job title: {job_title_problem}")
    # st.stop() ends this run of the script here. Nothing below is drawn,
    # so no request can be sent to the model.
    st.stop()

# NEW: check the company too, but only if one was typed, because it's optional.
# Without this "if", an empty box would be blocked as "Please type something first."
if company.strip():
    company_problem = check_user_text(company, MAX_COMPANY_CHARS)
    if company_problem:
        st.error(f"Company: {company_problem}")
        st.stop()

    # NEW: an optional job description, so questions fit this exact position.
    job_description = st.text_area(
        "Job description (optional)",
        height=150,
        max_chars=MAX_JD_CHARS,
        placeholder="Paste the job ad here",
    )

# ----- Collect the choices -----

# Put all the choices in one dictionary, so we can pass them around together.
interview = {
    "job_title": job_title,
    "company": company.strip(),  # NEW: empty text if no company was typed
    "area": area,
    "seniority": seniority,
    "country": country,
    "interview_type": interview_type,
    "style": style,
    "job_description": job_description.strip(),  # NEW: empty text if none was pasted
    "language": language,  # NEW
    "feedback_length": feedback_length,
}
# The model settings, bundled in one dictionary, so they can be passed to every
# call at once. The keys must match the names of ask_model's inputs exactly.
model_settings = {
    "model": model,
    "max_tokens": max_tokens,
    "reasoning_effort": reasoning_effort,
}


def call_model(user_request, technique=None):
    """Send the system prompt plus one request to the model, and return the reply.

    technique is only passed for feedback. The question requests leave it out,
    so their system prompt has no technique section.
    """
    messages = [
        # The instructions: built from the choices, with or without a technique.
        {"role": "system", "content": build_system_prompt(interview, technique)},
        # What we're asking for this time.
        {"role": "user", "content": user_request},
    ]
    # "**model_settings" unpacks the dictionary into named inputs. It's the same
    # as writing ask_model(messages, model=..., max_tokens=..., reasoning_effort=...).
    return ask_model(messages, **model_settings)


def for_api(messages):
    """Copy the messages with only "role" and "content".

    The API doesn't accept extra keys like "hidden", which is only for our app.
    """
    # A "list comprehension": build a new list by going through the old one.
    return [{"role": m["role"], "content": m["content"]} for m in messages]


# //score and download
def build_transcript(chat):
    """Turn the chat history into plain text for the assessor.

    Only the visible conversation: no system prompt, no hidden kickoff message.
    """
    lines = []
    for message in chat:
        if message["role"] == "system" or message.get("hidden"):
            continue  # skip what the user never saw
        # A one-line if/else: "Interviewer" for the model's messages, "Candidate" otherwise.
        speaker = "Interviewer" if message["role"] == "assistant" else "Candidate"
        lines.append(f"{speaker}: {message['content']}")
    # "\n\n".join(...) puts the lines together, with a blank line between each.
    return "\n\n".join(lines)


def show_report(report):
    """Show the report: the scores in boxes, then the summary and the lists."""
    st.subheader("Your interview report")

    # Two boxes side by side: the overall score and the readiness.
    # st.metric shows a label with a big value under it.
    col_score, col_ready = st.columns(2)
    col_score.metric("Overall score", f"{report['overall_score']}/10")
    col_ready.metric("Readiness", report["readiness"])

    st.write(report["summary"])

    # The four smaller scores, in four boxes in one row.
    scores = report["scores"]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Communication", f"{scores['communication']}/5")
    col2.metric("Technical depth", f"{scores['technical_depth']}/5")
    col3.metric("Structure", f"{scores['structure']}/5")
    col4.metric("Relevance", f"{scores['relevance']}/5")

    # The three lists, as bullet points.
    st.markdown("**Strengths**")
    for item in report["strengths"]:
        st.markdown(f"- {item}")

    st.markdown("**To improve**")
    for item in report["improvements"]:
        st.markdown(f"- {item}")

    st.markdown("**Next steps**")
    for item in report["next_steps"]:
        st.markdown(f"- {item}")

    # A button that saves the report as a file.
    # json.dumps turns the dictionary back into JSON text. indent=2 makes it readable,
    # and ensure_ascii=False keeps letters like "ü" as they are.
    st.download_button(
        "Download report (JSON)",
        json.dumps(report, indent=2, ensure_ascii=False),
        file_name="interview_report.json",
        mime="application/json",  # tells the browser what kind of file it is
    )


# ----- The two tabs -----

# st.tabs returns one object per tab. "with" a tab puts content inside it.
# tab_expected, tab_practice = st.tabs(["Expected questions", "Practice"])
tab_expected, tab_practice, tab_interview = st.tabs(
    ["Expected questions", "Practice", "Mock interview"]
)

# ----- Tab 1: Expected questions -----

with tab_expected:
    st.write("See the questions you're likely to be asked, with a tip for each.")

    # st.button returns True only in the run right after it's clicked.
    if st.button("Show expected questions"):
        # A spinner shows while the model is working.
        with st.spinner("Thinking of questions..."):
            reply = call_model(expected_questions_request())
        # st.markdown shows text with formatting, like the bold questions.
        st.markdown(reply)


# ----- Tab 2: Practice -----

with tab_practice:
    st.write("Get a question, type your answer, and get feedback.")

    # Streamlit reruns this whole file after every click, and normal variables
    # are forgotten. st.session_state keeps values between reruns.
    # Here we create the "question" slot once, empty (None) at the start.
    if "question" not in st.session_state:
        st.session_state.question = None

    # Clicking "New question" asks the model for a question, and saves it.
    if st.button("New question"):
        with st.spinner("Choosing a question..."):
            st.session_state.question = call_model(new_question_request())

    # Only show the answer box once there's a question.
    if st.session_state.question:
        st.markdown(f"**Question:** {st.session_state.question}")

        # A big text box for the answer.
        # NEW (Step 5): max_chars stops the user typing more than the limit.
        answer = st.text_area("Your answer", height=200, max_chars=MAX_ANSWER_CHARS)

        if st.button("Get feedback"):
            # NEW (Step 5): the guard checks for empty, too long, and attack phrases.
            # This replaces the old "if not answer.strip()" check,
            # because the guard's first check already handles empty answers.
            problem = check_user_text(answer, MAX_ANSWER_CHARS)
            if problem:
                # Blocked: show the reason, and send nothing to the model.
                st.warning(problem)
            else:
                # Allowed: ask for feedback, using the chosen technique.
                with st.spinner("Reading your answer..."):
                    feedback = call_model(
                        feedback_request(st.session_state.question, answer), technique
                    )
                st.markdown(feedback)
                # Developer tool: show the exact system prompt that was sent.
                if show_prompt:
                    with st.expander("System prompt that was sent"):
                        # st.code shows text exactly as it is, in a box, with a copy button.
                        st.code(build_system_prompt(interview, technique))
                # Developer tool: show the exact system prompt that was sent.
                if show_prompt:
                    with st.expander("System prompt that was sent"):
                        # st.code shows text exactly as it is, in a box, with a copy button.
                        st.code(build_system_prompt(interview, technique))

# ----- Tab 3: Mock interview (a chatbot that remembers the conversation) -----

with tab_interview:
    st.write("A full mock interview. The interviewer remembers the whole conversation.")

    # The conversation, kept between reruns. An empty list means "not started".
    if "chat" not in st.session_state:
        st.session_state.chat = []
        # The report, kept between reruns. None means "no report yet".
    if "report" not in st.session_state:
        st.session_state.report = None

    # Two buttons side by side. st.columns(2) splits the row into two halves.
    col_start, col_restart = st.columns(2)

    if col_start.button("Start interview"):
        # Build the system prompt ONCE, from the current settings, so the whole
        # interview follows the same rules. Then add the hidden kickoff message.
        st.session_state.chat = [
            {"role": "system", "content": build_system_prompt(interview, technique, chat=True)},
            {"role": "user", "content": KICKOFF_MESSAGE, "hidden": True},
        ]
        # Remember the settings this interview started with, for the report.
        st.session_state.chat_interview = interview  # for score and download report
        # A new interview has no report yet.
        st.session_state.report = None  # for score and download report
        with st.spinner("The interviewer is getting ready..."):
            reply = ask_model(for_api(st.session_state.chat), **model_settings)
        # Save the interviewer's reply, so it's part of the history from now on.
        st.session_state.chat.append({"role": "assistant", "content": reply})

    if col_restart.button("Restart"):
        st.session_state.chat = []  # forget the whole conversation
        st.session_state.report = None  # and forget the report
        st.rerun()  # draw the page again straight away

    # Show the conversation so far, skipping what the user shouldn't see.
    for message in st.session_state.chat:
        if message["role"] == "system" or message.get("hidden"):
            continue  # skip this one, and go on to the next message
        # st.chat_message draws a chat bubble, with an icon for the role.
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # Developer tool: the interview's system prompt is the first message in the chat.
    # It's the version built at Start, so it shows the rules this interview really follows.
    if show_prompt and st.session_state.chat:
        with st.expander("System prompt for this interview"):
            st.code(st.session_state.chat[0]["content"])

    # Only show the answer box once the interview has started.
    if st.session_state.chat:
        # Count the real answers so far (not the hidden kickoff).
        answers = [m for m in st.session_state.chat if m["role"] == "user" and not m.get("hidden")]
        # The report button: only once a question has been answered, and only once.
        # "if answers" is True when the list isn't empty.
        if answers and st.session_state.report is None:
            if st.button("End & get report"):
                with st.spinner("Writing your report..."):
                    st.session_state.report = ask_model_json(
                        report_messages(
                            # .get() with a backup: if this interview started before
                            # this feature existed, use the current settings instead.
                            st.session_state.get("chat_interview", interview),
                            build_transcript(st.session_state.chat),
                        ),
                        REPORT_SCHEMA,
                    )
                st.rerun()  # draw the page again, now with the report

        # Show the report, if there is one.
        if st.session_state.report:
            show_report(st.session_state.report)
        if len(answers) >= MAX_INTERVIEW_ANSWERS:
            st.info(
                "You've reached the answer limit for one interview. Click Restart to begin again."
            )
        else:
            # st.chat_input is a message box. It returns the text once you press Enter.
            # disabled=True greys out the box: the interview is over once there's a report.
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
                    # Add the answer, then send the WHOLE conversation.
                    st.session_state.chat.append({"role": "user", "content": answer})
                    with st.spinner("The interviewer is thinking..."):
                        reply = ask_model(for_api(st.session_state.chat), **model_settings)
                    st.session_state.chat.append({"role": "assistant", "content": reply})
                    # Draw the page again, so the new messages appear in the chat above.
                    st.rerun()

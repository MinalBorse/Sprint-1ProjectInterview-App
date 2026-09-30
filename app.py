"""The web page: what the user sees and clicks."""

# ----- Imports -----

# Streamlit builds the web page. "as st" is a short nickname for it.
import streamlit as st

# Our own files.
# llm.py: sends messages to the model.
from llm import ask_model

# prompts.py: the words we send to the model.
from prompts import (
    TECHNIQUES,  # the five feedback techniques, by name
    build_system_prompt,  # builds the instructions from the user's choices
    expected_questions_request,  # the request for the Expected questions tab
    feedback_request,  # the request for feedback on an answer
    new_question_request,  # the request for one practice question
)

# NEW (Step 5): guards.py, the security checks.
# MAX_... are the length limits, and check_user_text is the guard itself.
from guards import MAX_ANSWER_CHARS, MAX_JOB_TITLE_CHARS, check_user_text


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
    job_title = st.text_input(
        "Job title", "Junior Python Developer", max_chars=MAX_JOB_TITLE_CHARS
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
    interview_type = st.selectbox(
        "Interview type", ["Behavioural", "Technical", "Case study", "Mixed"]
    )

    # Round buttons where only one can be chosen.
    style = st.radio("Interviewer style", ["Friendly", "Neutral", "Strict"], index=1)

    # Developer settings, kept apart from the interview choices,
    # because a normal user doesn't need to know what "few-shot" means.
    # st.expander is a section that opens when clicked.
    with st.expander("Developer settings"):
        # list(TECHNIQUES) gives the five technique names as the menu options.
        technique = st.selectbox("Feedback technique", list(TECHNIQUES))


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


# ----- Collect the choices -----

# Put all the choices in one dictionary, so we can pass them around together.
interview = {
    "job_title": job_title,
    "area": area,
    "seniority": seniority,
    "country": country,
    "interview_type": interview_type,
    "style": style,
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
    return ask_model(messages)


# ----- The two tabs -----

# st.tabs returns one object per tab. "with" a tab puts content inside it.
tab_expected, tab_practice = st.tabs(["Expected questions", "Practice"])


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
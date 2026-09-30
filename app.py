"""The web page: what the user sees and clicks."""

# Streamlit builds the web page. "as st" is a short nickname for it.
import streamlit as st

# Our own files: the model call, and the prompts.
from llm import ask_model
from prompts import (
    build_system_prompt,
    expected_questions_request,
    feedback_request,
    new_question_request,
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
    job_title = st.text_input("Job title", "Junior Python Developer")

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


# ----- Build the system prompt from the choices -----

# Put all the choices in one dictionary, so we can pass them around together.
interview = {
    "job_title": job_title,
    "area": area,
    "seniority": seniority,
    "country": country,
    "interview_type": interview_type,
    "style": style,
}
system_prompt = build_system_prompt(interview)


def call_model(user_request):
    """Send the system prompt plus one request to the model, and return the reply."""
    messages = [
        {"role": "system", "content": system_prompt},  # the instructions
        {"role": "user", "content": user_request},  # what we're asking for
    ]
    return ask_model(messages)


# ----- The two tabs -----

tab_expected, tab_practice = st.tabs(["Expected questions", "Practice"])


# Tab 1: Expected questions
with tab_expected:
    st.write("See the questions you're likely to be asked, with a tip for each.")

    # st.button returns True only in the run right after it's clicked.
    if st.button("Show expected questions"):
        # A spinner shows while the model is working.
        with st.spinner("Thinking of questions..."):
            reply = call_model(expected_questions_request())
        # st.markdown shows text with formatting, like the bold questions.
        st.markdown(reply)


# Tab 2: Practice
with tab_practice:
    st.write("Get a question, type your answer, and get feedback.")

    # Streamlit reruns this whole file after every click, and normal variables
    # are forgotten. st.session_state keeps values between reruns.
    # Here we create the "question" slot once, empty (None) at the start.
    if "question" not in st.session_state:
        st.session_state.question = None

    if st.button("New question"):
        with st.spinner("Choosing a question..."):
            st.session_state.question = call_model(new_question_request())

    # Only show the answer box once there's a question.
    if st.session_state.question:
        st.markdown(f"**Question:** {st.session_state.question}")

        # A big text box for the answer.
        answer = st.text_area("Your answer", height=200)

        if st.button("Get feedback"):
            # .strip() removes spaces, so an answer of only spaces counts as empty.
            if not answer.strip():
                st.warning("Type your answer first.")
            else:
                with st.spinner("Reading your answer..."):
                    feedback = call_model(feedback_request(st.session_state.question, answer))
                st.markdown(feedback)
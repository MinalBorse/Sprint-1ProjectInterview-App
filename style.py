"""The look of the app: a dark, softly glowing background, an elegant
heading font, and a welcome card with check-mark features."""

# quote() makes text safe to use inside a web address, for the leaf picture.
from urllib.parse import quote

import streamlit as st

# ----- The leaf picture -----

# An SVG: a picture described in text. A 160 x 160 tile with two leaves,
# repeated across the page like wallpaper. Pale green, and very faint
# (fill-opacity 0.05), so the glows and the text stay the main things you see.
LEAF_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160" viewBox="0 0 160 160">
  <g fill="#A8D5BA" fill-opacity="0.05" stroke="#A8D5BA" stroke-opacity="0.10" stroke-width="1">
    <path d="M40 20 C62 38 62 66 40 84 C18 66 18 38 40 20 Z"/>
    <path d="M40 26 L40 80" fill="none"/>
    <g transform="translate(115 105) rotate(35)">
      <path d="M0 -30 C20 -14 20 14 0 30 C-20 14 -20 -14 0 -30 Z"/>
      <path d="M0 -24 L0 26" fill="none"/>
    </g>
  </g>
</svg>
"""

# ----- The styles (CSS) -----

# CSS describes how the page looks. Comments in CSS go between /* and */.
# LEAF_URL is a placeholder, replaced with the real leaf picture in add_calm_style().
CALM_CSS = """
<style>
/* An elegant serif font for headings, loaded from Google Fonts.
   @import must come first in the styles. If the font can't load,
   the headings fall back to Georgia, then to any serif font. */
@import url("https://fonts.googleapis.com/css2?family=Marcellus&display=swap");

/* ----- The background: soft glows of light, over the leaves ----- */
/* Several background layers, listed from top to bottom.
   A radial-gradient is a soft circle of colour that fades to transparent.
   "circle at 15% 20%" places the circle's centre 15% from the left and
   20% from the top. The last number (like 40%) is how far it spreads.
   rgba(red, green, blue, strength): the 4th number is how see-through it is. */
.stApp {
    background-color: #141C18;
    background-image:
        radial-gradient(circle at 15% 20%, rgba(143, 193, 160, 0.16), transparent 40%),
        radial-gradient(circle at 85% 12%, rgba(214, 180, 120, 0.10), transparent 35%),
        radial-gradient(circle at 70% 85%, rgba(90, 140, 110, 0.14), transparent 45%),
        url("LEAF_URL");
    /* One size per layer, in the same order: the glows fill the page,
       and the leaf tile is 160 x 160 pixels. */
    background-size: auto, auto, auto, 160px 160px;
    /* "fixed" keeps the background still while the page scrolls,
       so the glows feel like light in the room, not part of the page. */
    background-attachment: fixed;
}

/* ----- Headings: the elegant serif font ----- */
.stApp h1, .stApp h2, .stApp h3 {
    font-family: "Marcellus", Georgia, serif;
    font-weight: 400;          /* thin, not bold, like in the reference */
    letter-spacing: 0.5px;     /* a little extra space between letters */
}

/* ----- The welcome card ----- */
/* Very slightly lighter than the page, with a thin border: like frosted glass. */
.welcome-card {
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 1.1rem 1.4rem;
    margin-bottom: 1.2rem;
    line-height: 1.6;
}

/* ----- The features, with check marks ----- */
/* "display: flex" puts the circle and the text side by side,
   and "align-items: center" lines them up in the middle. */
.feature {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 6px 0;
}

/* The small green circle with a check mark inside. */
.check {
    width: 20px;
    height: 20px;
    border-radius: 50%;        /* 50% turns a square into a circle */
    background-color: #7FA88C;
    color: #141C18;            /* a dark check mark on the green circle */
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: bold;
    flex-shrink: 0;            /* keep it a circle, even next to long text */
}

/* ----- Softer, rounder buttons ----- */
.stButton > button {
    border-radius: 20px;
}
</style>
"""


def add_calm_style():
    """Add the background, fonts and soft styles to the page."""
    # A "data URL" puts the picture inside the address. quote() turns
    # characters like "#" and spaces into safe codes.
    leaf_url = "data:image/svg+xml," + quote(LEAF_SVG)
    css = CALM_CSS.replace("LEAF_URL", leaf_url)

    # unsafe_allow_html=True lets us add our own HTML and CSS. ONLY ever use it
    # with text we wrote ourselves, NEVER with anything a user typed.
    st.markdown(css, unsafe_allow_html=True)


def show_welcome(message, features):
    """Show the welcome card: a message, then a list of features with check marks.

    message: the welcome text (our own HTML, like <b> and <br>).
    features: a list of short texts, each shown with a check mark.
    """
    # Build one line of HTML per feature, then join them together.
    feature_lines = "".join(
        f'<div class="feature"><span class="check">✓</span>{item}</div>' for item in features
    )
    st.markdown(
        f'<div class="welcome-card">{message}{feature_lines}</div>',
        unsafe_allow_html=True,
    )

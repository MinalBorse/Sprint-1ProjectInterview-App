"""The look of the app: a leaf frame drawn in code, a solid green panel for the
content, an elegant heading font, and a welcome card with check marks.

The leaves are drawn by this file itself, as an SVG picture. There's no image
file to download, and no copyright to worry about: it's our own artwork.
"""

# math: angles, so the leaves can point towards the middle of the page.
import math

# random: varied sizes, colours and positions, so the leaves look natural.
import random

# quote(): makes the SVG text safe to put inside a web address (a "data URL").
from urllib.parse import quote

import streamlit as st

# =============================================================================
# The leaf frame (an SVG picture, made of many leaf shapes)
# =============================================================================

# The size of the picture. The browser stretches it to fill the window.
WIDTH, HEIGHT = 1600, 1000

# Six greens, from dark to lighter. Each leaf picks one, for natural variety.
LEAF_COLOURS = ["#0F3A27", "#145034", "#1A6140", "#22724C", "#2C8458", "#367F55"]

# The shape of one leaf, 1 unit long, from its base (0, 0) up to its tip (0, -1).
# In SVG paths: M moves the pen, C draws a curve, Z closes the shape.
# Two curves, one on each side, make the pointed leaf shape.
LEAF_SHAPE = "M0 0 C0.36 -0.22 0.36 -0.74 0 -1 C-0.36 -0.74 -0.36 -0.22 0 0 Z"


def edge_point(rng):
    """Pick a random spot near one of the edges, so the middle stays clear.

    rng is our random-number generator (see make_leaf_frame_svg).
    """
    # Left and right appear twice, so there are more leaves on the sides.
    side = rng.choice(["top", "bottom", "left", "right", "left", "right"])
    # How far in from the edge: a little outside it (-60) to well inside (230).
    depth = rng.uniform(-60, 230)
    if side == "top":
        return rng.uniform(0, WIDTH), depth
    if side == "bottom":
        return rng.uniform(0, WIDTH), HEIGHT - depth
    if side == "left":
        return depth, rng.uniform(0, HEIGHT)
    return WIDTH - depth, rng.uniform(0, HEIGHT)


def angle_towards_middle(x, y, rng):
    """The angle that points a leaf at (x, y) roughly towards the middle."""
    # How far the middle is from this spot, across and down.
    across, down = WIDTH / 2 - x, HEIGHT / 2 - y
    # atan2 turns that into an angle. A leaf with no rotation points UP in SVG,
    # which is why "down" is negative here.
    angle = math.degrees(math.atan2(across, -down))
    # Add some randomness, so the leaves don't all point exactly the same way.
    return angle + rng.uniform(-70, 70)


def broad_leaf(rng):
    """One wide leaf, with a faint vein down the middle. Returns SVG text."""
    x, y = edge_point(rng)
    angle = angle_towards_middle(x, y, rng)
    length = rng.uniform(140, 340)
    width = rng.uniform(0.55, 1.05)  # some leaves wider, some slimmer
    colour = rng.choice(LEAF_COLOURS)
    # <g> groups shapes, so they move and turn together:
    #   translate(x y) moves the group to its spot, rotate(angle) turns it.
    # The leaf shape is then scaled up from 1 unit to its real size.
    # The vein is a thin, faint line drawn on top, from the base to the tip.
    return (
        f'<g transform="translate({x:.0f} {y:.0f}) rotate({angle:.0f})">'
        f'<path d="{LEAF_SHAPE}" fill="{colour}" '
        f'transform="scale({length * width:.0f} {length:.0f})"/>'
        f'<path d="M0 0 L0 {-length * 0.95:.0f}" stroke="#8CC9A0" '
        f'stroke-opacity="0.25" stroke-width="1.5" fill="none"/>'
        "</g>"
    )


def palm_frond(rng):
    """One palm frond: a stem with narrow leaflets on both sides. Returns SVG text."""
    x, y = edge_point(rng)
    angle = angle_towards_middle(x, y, rng)
    length = rng.uniform(260, 460)
    colour = rng.choice(LEAF_COLOURS)

    parts = [
        f'<g transform="translate({x:.0f} {y:.0f}) rotate({angle:.0f})">',
        # The stem: a straight line from the base to the tip.
        f'<path d="M0 0 L0 {-length:.0f}" stroke="{colour}" stroke-width="3" fill="none"/>',
    ]
    # A pair of leaflets every 16 pixels along the stem.
    for along in range(16, int(length), 16):
        # Leaflets get shorter towards the tip, like a real frond.
        size = (1 - along / length) * rng.uniform(70, 100) + 14
        for side in (-1, 1):  # -1 is the left side, 1 is the right side
            parts.append(
                # Move up the stem, tilt 58 degrees to one side, and scale the
                # leaf shape to a long, thin leaflet.
                f'<g transform="translate(0 {-along}) rotate({side * 58}) '
                f'scale({size * 0.22:.1f} {size:.1f})">'
                f'<path d="{LEAF_SHAPE}" fill="{colour}"/></g>'
            )
    parts.append("</g>")
    return "".join(parts)


@st.cache_data
def make_leaf_frame_svg(seed=7):
    """Draw the whole leaf frame, and return it as SVG text.

    @st.cache_data remembers the result, so the picture is drawn once,
    not on every rerun of the app.
    """
    # A random generator with a fixed "seed": it gives the SAME random numbers
    # every time, so the picture looks the same on every visit.
    # Change the seed (for example to 8) for a different arrangement of leaves.
    rng = random.Random(seed)

    shapes = [palm_frond(rng) for _ in range(30)] + [broad_leaf(rng) for _ in range(130)]
    # Mix the order, so fronds and broad leaves overlap each other naturally.
    rng.shuffle(shapes)

    # preserveAspectRatio="xMidYMid slice" fills the whole window without
    # stretching the leaves, cropping the edges if needed.
    # The first rectangle is the dark background behind the leaves.
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'preserveAspectRatio="xMidYMid slice">'
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#0D2E22"/>' + "".join(shapes) + "</svg>"
    )


# =============================================================================
# The styles (CSS)
# =============================================================================

# Comments in CSS go between /* and */.
# LEAF_URL is a placeholder, replaced with the leaf picture in add_calm_style().
CALM_CSS = """
<style>
/* An elegant serif font for headings, from Google Fonts.
   If it can't load, headings fall back to Georgia, then any serif font. */
@import url("https://fonts.googleapis.com/css2?family=Marcellus&display=swap");

/* ----- The whole page: the leaf frame ----- */
.stApp {
    background-color: #0D2E22;          /* shown while the picture loads */
    background-image: url("LEAF_URL");
    background-size: cover;             /* fill the window */
    background-position: center;
    background-attachment: fixed;       /* the leaves stay still while you scroll */
}

/* The bar at the very top: see-through, so the leaves show behind it. */
[data-testid="stHeader"] {
    background: transparent;
}

/* ----- The main content: a solid green panel ----- */
/* This keeps the text fully readable: it sits on a plain colour, not on the
   leaves. 0.96 means 96% solid, so the leaves can't show through. */
.stMainBlockContainer, .block-container {
    background-color: rgba(18, 74, 54, 0.96);
    border-radius: 18px;
    padding: 2.5rem 2.5rem 3rem 2.5rem !important;
    margin-top: 2.5rem;
    margin-bottom: 2.5rem;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.45);
}

/* ----- Headings: the elegant serif font ----- */
.stApp h1, .stApp h2, .stApp h3 {
    font-family: "Marcellus", Georgia, serif;
    font-weight: 400;
    letter-spacing: 0.5px;
}

/* ----- The welcome card: a little darker than the panel ----- */
.welcome-card {
    background-color: rgba(0, 0, 0, 0.18);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 1.1rem 1.4rem;
    margin-bottom: 1.2rem;
    line-height: 1.6;
}

/* ----- The features, with check marks ----- */
.feature {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 6px 0;
}

.check {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background-color: #8FC1A0;
    color: #0F3D2E;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: bold;
    flex-shrink: 0;
}

/* ----- Softer, rounder buttons ----- */
.stButton > button {
    border-radius: 20px;
}
</style>
"""


def add_calm_style():
    """Add the leaf frame, the panel, the fonts and the soft styles to the page."""
    # A "data URL": the picture itself, written inside the address.
    leaf_url = "data:image/svg+xml," + quote(make_leaf_frame_svg())
    css = CALM_CSS.replace("LEAF_URL", leaf_url)
    # unsafe_allow_html=True lets us add our own HTML and CSS. ONLY ever use it
    # with text we wrote ourselves, NEVER with anything a user typed.
    st.markdown(css, unsafe_allow_html=True)


def show_welcome(message, features):
    """Show the welcome card: a message, then a list of features with check marks."""
    feature_lines = "".join(
        f'<div class="feature"><span class="check">✓</span>{item}</div>' for item in features
    )
    st.markdown(
        f'<div class="welcome-card">{message}{feature_lines}</div>',
        unsafe_allow_html=True,
    )

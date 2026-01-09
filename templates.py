import genanki

# Define the Card Templates
FIELDS = [
    {"name": "中文"},
    {"name": "Pinyin"},
    {"name": "English"},
    {"name": "Notes"},
    {"name": "Grammar Construct"},
    {"name": "Source URL"},
    {"name": "Article Title"},
]
TRANSLATION_FRONT = '<div class="hanzi">{{中文}}</div>'
TRANSLATION_BACK = """{{FrontSide}}
<div class="spacer"> </div>
<div class="english">
    <div class="pinyin">{{Pinyin}}</div>
    <div class="spacerSmall"> </div>
    {{English}}
    <div class="spacerMedium"> </div>
    <div class="notes">{{Notes}}</div>
</div>

<div class="lessonInfo">
<div class="spacer"> </div>
<div>Pattern: <span class="lessonInfoHanzi">{{Grammar Construct}}</span></div>
Article: <a href={{Source URL}}>{{Article Title}}</a>
</div>"""
EXAMPLE_FRONT = """<div class="header">Is this sentence grammatically correct?</div>
<div class="spacer"> </div>
<div class="hanzi">{{中文}}</div>"""
VALID_EXAMPLE_BACK = """<div class="hanzi">{{中文}}</div>

<div class="english">
    <div class="spacerMedium"> </div>
    <div class="pinyin">{{Pinyin}}</div>
    <div class="spacerSmall"> </div>
    {{English}}
    <div class="spacerMedium"> </div>
    <div class="correct">Correct!</div>
    <div class="spacerMedium"> </div>
    <div class="notes">{{Notes}}</div>
</div>


<div class="lessonInfo">
<div class="spacer"> </div>
<div>Pattern: <span class="lessonInfoHanzi">{{Grammar Construct}}</span></div>
Article: <a href={{Source URL}}>{{Article Title}}</a>
</div>"""
INVALID_EXAMPLE_BACK = """<div class="hanzi">{{中文}}</div>

<div class="english">
    <div class="spacerMedium"> </div>
    <div class="pinyin">{{Pinyin}}</div>
    <div class="spacerSmall"> </div>
    {{English}}
    <div class="spacerMedium"> </div>
    <div class="incorrect">Not correct!</div>
    <div class="spacerMedium"> </div>
    <div class="notes">{{Notes}}</div>
</div>


<div class="lessonInfo">
<div class="spacer"> </div>
<div>Pattern: <span class="lessonInfoHanzi">{{Grammar Construct}}</span></div>
Article: <a href={{Source URL}}>{{Article Title}}</a>
</div>"""
STYLING = """.card {
font-family: arial;
font-size: 30px;
text-align: center;
color: black;
background-color: white;
}

.header {
font-family: arial;
font-size: 16px;
}

.hanzi {
font-family: SimSun;
font-size: 28px;
}

.pinyin {
color: gray;
}

.translation {
font-size: 26px;
}

.lessonInfoHanzi {
font-family: SimSun;
font-size: 12px;
}

.lessonInfo {
font-family: arial;
font-size: 10px;
}

.correct {
font-family: arial;
font-size: 26px;
color: green;
font-weight: bold;
}

.incorrect {
font-family: arial;
font-size: 26px;
color: red;
font-weight: bold;
}

.english {
font-family: arial;
font-size: 20px;
}

.notes {
font-family: arial;
font-size: 12px;
color: gray;
}

.spacer {
height: 20px;
}

.spacerSmall {
height: 3px;
}

.spacerMedium {
height: 10px;
}
"""

# Stable, unique IDs for models, generated with random.randrange(1 << 30, 1 << 31)
# Unique 10-digit integers so we don't overwrite other decks & can diff existing decks generated with this script
TRANSLATION_MODEL_ID = 2144434948
VALID_EXAMPLE_MODEL_ID = 1139990969
INVALID_EXAMPLE_MODEL_ID = 1513257399

# Define the Translation Card Template
TRANSLATION_MODEL = genanki.Model(
    TRANSLATION_MODEL_ID,
    "CGW Translation",
    fields=FIELDS,
    templates=[
        {
            "name": "Translation",
            "qfmt": TRANSLATION_FRONT,
            "afmt": TRANSLATION_BACK,
        },
    ],
    css=STYLING,
    sort_field_index=0,
)

# Define the Card Template (The Model)
VALID_EXAMPLE_MODEL = genanki.Model(
    VALID_EXAMPLE_MODEL_ID,
    "CGW Valid Example",
    fields=FIELDS,
    templates=[
        {
            "name": "Valid Example",
            "qfmt": EXAMPLE_FRONT,
            "afmt": VALID_EXAMPLE_BACK,
        },
    ],
    css=STYLING,
    sort_field_index=0,
)

# Define the Card Template (The Model)
INVALID_EXAMPLE_MODEL = genanki.Model(
    INVALID_EXAMPLE_MODEL_ID,
    "CGW Invalid Example",
    fields=FIELDS,
    templates=[
        {
            "name": "Invalid Example",
            "qfmt": EXAMPLE_FRONT,
            "afmt": INVALID_EXAMPLE_BACK,
        },
    ],
    css=STYLING,
    sort_field_index=0,
)

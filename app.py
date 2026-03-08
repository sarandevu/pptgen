import streamlit as st
from google import genai
from google.genai import types
from pptx import Presentation
from pptx.util import Inches
import json
import io
from pypdf import PdfReader

# ---------------------------
# 1. Gemini Client Setup
# ---------------------------
client = genai.Client(
    api_key=st.secrets["GEMINI_API_KEY"]
)

# ---------------------------
# 2. AI Architect
# ---------------------------
def get_ai_architect_response(notes, user_instructions, image_file=None):

    instructions = """
You are a Professional Technical Presentation Architect.

Transform engineering notes into a professional presentation plan.

Rules:
- Slides must be educational.
- Avoid generic bullets.
- Each slide must teach something meaningful.
- Use professional engineering structure.

Structure:
1. Title
2. Problem Statement
3. Existing Solutions
4. Proposed System
5. System Architecture
6. Key Components
7. Advantages
8. Conclusion

Return ONLY JSON:

{
"title": "Presentation Title",
"image_role": "background | logo | none",
"slides":[
 {
  "title":"Slide Title",
  "bullets":["point1","point2","point3"],
  "speaker_notes":"optional explanation"
 }
]
}
"""

    contents = [
        f"Notes: {notes}",
        f"Design instructions: {user_instructions}"
    ]

    if image_file:
        contents.append(
            types.Part.from_bytes(
                data=image_file.read(),
                mime_type=image_file.type
            )
        )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=instructions,
            response_mime_type="application/json"
        )
    )

    return json.loads(response.text)

# ---------------------------
# 3. Design Suggestions
# ---------------------------
def get_design_suggestions(topic):

    prompt = f"""
Suggest professional design ideas for a PowerPoint about: {topic}

Return JSON:

{{
"theme_colors": "",
"background_style": "",
"font_style": "",
"visual_elements": ["icons","diagrams","charts"]
}}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )

    return json.loads(response.text)

# ---------------------------
# 4. Slide Improver
# ---------------------------
def improve_slide(text):

    prompt = f"""
Improve the following PowerPoint slide.

Make it:
- clear
- concise
- professional
- technically strong

Slide:
{text}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text

# ---------------------------
# 5. Research Mode
# ---------------------------
def extract_pdf_text(pdf):

    reader = PdfReader(pdf)
    text = ""

    for page in reader.pages:
        txt = page.extract_text()
        if txt:
            text += txt

    return text


def research_to_slides(text):

    prompt = f"""
Convert this research content into a professional presentation.

Structure:
Title
Background
Problem
Methodology
Results
Conclusion

Text:
{text[:8000]}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )

    return json.loads(response.text)

# ---------------------------
# 6. PPT Builder
# ---------------------------
def build_presentation(data, image_file=None):

    prs = Presentation()

    role = data.get("image_role", "none").lower()

    image_bytes = None
    if image_file:
        image_bytes = image_file.read()

    def apply_assets(slide):

        if image_bytes and role == "background":

            slide.shapes.add_picture(
                io.BytesIO(image_bytes),
                0,
                0,
                width=prs.slide_width,
                height=prs.slide_height
            )

        elif image_bytes and role == "logo":

            slide.shapes.add_picture(
                io.BytesIO(image_bytes),
                Inches(8.5),
                Inches(0.2),
                width=Inches(1)
            )

    # Title slide
    title_slide = prs.slides.add_slide(prs.slide_layouts[0])
    title_slide.shapes.title.text = data.get("title","Presentation")

    # Content slides
    for slide_data in data.get("slides",[]):

        slide = prs.slides.add_slide(prs.slide_layouts[1])

        apply_assets(slide)

        slide.shapes.title.text = slide_data.get("title","Slide")

        tf = slide.placeholders[1].text_frame
        tf.clear()

        for bullet in slide_data.get("bullets",[]):

            p = tf.add_paragraph()
            p.text = bullet
            p.level = 0

        if slide_data.get("speaker_notes"):

            slide.notes_slide.notes_text_frame.text = slide_data["speaker_notes"]

    ppt = io.BytesIO()
    prs.save(ppt)

    return ppt.getvalue()

# ---------------------------
# 7. Streamlit UI
# ---------------------------
st.set_page_config(page_title="AI PPT Architect", layout="wide")

st.title("🏗️ AI Knowledge-Driven PPT Architect")

if "architect_data" not in st.session_state:
    st.session_state.architect_data = None

# ---------------------------
# Sidebar
# ---------------------------
with st.sidebar:

    st.header("Create Presentation")

    notes = st.text_area("Project Notes")

    design_prompt = st.text_input("Design instructions (bg / logo etc)")

    image_file = st.file_uploader(
        "Upload optional image",
        type=["png","jpg","jpeg"]
    )

    if st.button("Generate PPT Structure"):

        if notes:

            with st.spinner("AI analyzing notes..."):

                st.session_state.architect_data = get_ai_architect_response(
                    notes,
                    design_prompt,
                    image_file
                )

        else:
            st.error("Enter notes first")

    st.divider()

    st.header("Research Mode")

    pdf = st.file_uploader("Upload research PDF", type=["pdf"])

    if pdf:

        if st.button("Generate PPT from Research"):

            text = extract_pdf_text(pdf)

            st.session_state.architect_data = research_to_slides(text)

# ---------------------------
# Main workspace
# ---------------------------
if st.session_state.architect_data:

    data = st.session_state.architect_data

    st.header(f"📊 Content Audit: {data.get('title')}")

    # design suggestions
    if st.button("🎨 Get Design Suggestions"):

        suggestions = get_design_suggestions(data.get("title"))

        st.subheader("AI Design Advice")

        st.write("Theme:", suggestions["theme_colors"])
        st.write("Background:", suggestions["background_style"])
        st.write("Fonts:", suggestions["font_style"])
        st.write("Visual Elements:", suggestions["visual_elements"])

    st.divider()

    for i, slide in enumerate(data.get("slides",[])):

        with st.expander(f"Slide {i+1}: {slide.get('title')}"):

            text = "\n".join(slide.get("bullets",[]))

            edited = st.text_area(
                "Edit slide content",
                value=text,
                key=f"edit{i}"
            )

            if st.button(f"Improve Slide {i+1}"):

                improved = improve_slide(edited)

                st.success("AI Improved Version")

                st.write(improved)

    st.divider()

    if st.checkbox("I verify the content is correct"):

        ppt_file = build_presentation(
            data,
            image_file
        )

        st.download_button(
            "📥 Download Editable PPT",
            ppt_file,
            file_name="ai_presentation.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import fitz  # PyMuPDF
import docx
from io import BytesIO
import re

# --- Page Configuration ---
st.set_page_config(page_title="AI Resume Builder", layout="wide")

# --- Function Definitions ---

def scrape_job_description(url):
    """Scrapes job description text from a URL."""
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        job_text = soup.body.get_text(separator=' ', strip=True)
        return job_text if job_text else "Could not retrieve text from URL."
    except Exception as e:
        return f"Error scraping URL: {e}"

def extract_text_from_resume(file):
    """Extracts text from an uploaded PDF or DOCX file."""
    text = ""
    try:
        if file.type == "application/pdf":
            pdf_doc = fitz.open(stream=file.read(), filetype="pdf")
            for page in pdf_doc:
                text += page.get_text()
        elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(file)
            for para in doc.paragraphs:
                text += para.text + "\n"
    except Exception as e:
        st.error(f"Error reading file: {e}")
    return text

def get_gemini_response(prompt):
    """Sends a prompt to the Gemini model and returns the response."""
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
    response = model.generate_content(prompt)
    return response.text

def create_docx_from_text(text):
    """Creates a downloadable DOCX file from text with basic Markdown parsing."""
    doc = docx.Document()
    for line in text.split('\n'):
        if line.strip():
            p = doc.add_paragraph()
            # Simple bold parsing: split by '**'
            parts = re.split(r'(\*\*.*?\*\*)', line)
            for part in parts:
                if part.startswith('**') and part.endswith('**'):
                    p.add_run(part[2:-2]).bold = True
                else:
                    p.add_run(part)
    
    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# --- Prompts ---

def get_resume_prompt(content, job_desc):
    return f"""
    **Role:** You are a world-class professional resume writer and career coach specializing in ATS optimization.

    **Task:** Rewrite and tailor the provided resume content to perfectly match the given job description. Your goal is a resume that scores 90+ on an ATS scan and impresses recruiters.

    **Instructions:**
    1.  **Analyze & Integrate:** Deeply analyze the **Job Description** for keywords, skills, and qualifications. Rewrite the **Resume Content** to align with it, integrating these keywords naturally.
    2.  **Quantify Achievements:** Convert responsibilities into measurable achievements (e.g., "Increased sales by 15%"). Make reasonable assumptions if necessary.
    3.  **Format:** Use Markdown for structure. Use `**` for bolding key metrics or titles. Ensure the output is clean, professional, and contains only the resume text.
    4.  **Structure:** Follow this order: Name, Contact Info, Professional Summary, Skills, Work Experience, Education, Projects (optional).

    ---
    **Job Description:**
    ```
    {job_desc}
    ```
    ---
    **Resume Content to be Rewritten:**
    ```
    {content}
    ```
    ---
    **Required Output (Strict Markdown Format):**

    **Your Name**
    (123) 456-7890 | your.email@email.com | linkedin.com/in/yourprofile

    **Professional Summary**
    ...

    **Skills**
    ...

    **Work Experience**
    ...

    **Education**
    ...
    """

def get_interview_questions_prompt(new_resume):
    return f"Based on this resume, generate 10 interview questions categorized as 'Easy', 'Medium', and 'Hard'.\n\n**Resume:**\n{new_resume}"

def get_resources_prompt(new_resume):
    return f"Based on the skills in this resume, suggest a brief list of top-tier online learning resources (docs, tutorials, courses) for interview preparation.\n\n**Resume:**\n{new_resume}"


# --- Main App UI & Logic ---

st.title("🚀 AI-Powered ATS Resume Builder")
st.write("Create a powerful, tailored resume that gets past the bots and lands you interviews.")

# Configure Gemini API Key
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except Exception:
    st.error("⚠️ Google API Key not found. Please add it to your Streamlit secrets.")
    st.stop()


# --- Sidebar for User Inputs ---
with st.sidebar:
    st.header("1. Job Details")
    jd_input_method = st.radio("Provide Job Description By:", ["Pasting Text", "URL"], horizontal=True)
    
    job_text = ""
    if jd_input_method == "Pasting Text":
        job_text = st.text_area("Paste Job Description Here", height=200)
    else:
        job_url = st.text_input("Enter Job Posting URL")

    st.header("2. Your Resume")
    resume_input_method = st.radio("How would you like to provide your resume?", ["Upload File", "Build From Scratch"], horizontal=True)

    resume_content = ""
    if resume_input_method == "Upload File":
        uploaded_resume = st.file_uploader("Upload your resume (PDF or DOCX)", type=['pdf', 'docx'])
        if uploaded_resume:
            resume_content = extract_text_from_resume(uploaded_resume)
    else:
        with st.form(key='resume_form'):
            name = st.text_input("Full Name")
            contact = st.text_input("Email, Phone, LinkedIn URL")
            summary = st.text_area("Professional Summary")
            skills = st.text_area("Skills (comma-separated)")
            experience = st.text_area("Work Experience (paste or write here)", height=150)
            education = st.text_area("Education", height=100)
            
            form_submit = st.form_submit_button("Save Details")
            if form_submit:
                resume_content = f"Name: {name}\nContact: {contact}\nSummary: {summary}\nSkills: {skills}\nExperience: {experience}\nEducation: {education}"
                st.success("Details saved!")

    st.header("3. Generate")
    submit_button = st.button("✨ Generate Tailored Resume & Insights", type="primary")

# --- Main Content Area for Outputs ---
col1, col2 = st.columns((2, 1))

with col1:
    st.subheader("📄 Your New, Tailored Resume")
    resume_placeholder = st.container(height=600)

with col2:
    st.subheader("🤔 Interview Questions")
    questions_placeholder = st.container(height=300)
    
    st.subheader("📚 Learning Resources")
    resources_placeholder = st.container(height=300)

# --- Processing Logic ---
if submit_button:
    # Validate inputs
    if jd_input_method == "URL" and job_url:
        with st.spinner("Scraping job description..."):
            job_text = scrape_job_description(job_url)
    
    if not job_text:
        st.error("Please provide a job description.")
    elif not resume_content:
        st.error("Please provide your resume details.")
    else:
        with st.spinner("AI is working its magic... 🧙‍♂️ This may take a moment."):
            # Generate Resume
            resume_prompt = get_resume_prompt(resume_content, job_text)
            new_resume = get_gemini_response(resume_prompt)
            resume_placeholder.markdown(new_resume)

            # Add download button inside the main logic flow
            docx_file = create_docx_from_text(new_resume)
            st.sidebar.download_button(
                label="⬇️ Download Resume as DOCX",
                data=docx_file,
                file_name="Tailored_Resume.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

            # Generate Questions
            questions_prompt = get_interview_questions_prompt(new_resume)
            questions = get_gemini_response(questions_prompt)
            questions_placeholder.markdown(questions)
            
            # Generate Resources
            resources_prompt = get_resources_prompt(new_resume)
            resources = get_gemini_response(resources_prompt)
            resources_placeholder.markdown(resources)
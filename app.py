# ---------- app.py ----------
import streamlit as st
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from docx import Document
import matplotlib.pyplot as plt
import re, os

# ---------- utility functions ----------
def extract_text_from_docx(file):
    """Return full text from uploaded .docx file object."""
    doc = Document(file)
    return "\n".join([p.text for p in doc.paragraphs])

def extract_about_me(text):
    lines, out, capture = text.split("\n"), [], False
    for ln in lines:
        if "about me" in ln.lower(): capture = True; continue
        if capture and (ln.lower().startswith(("skills","experience","education")) or not ln.strip()):
            break
        if capture: out.append(ln.strip())
    return " ".join(out)

def extract_comma_skills(text):
    lines, skills = text.split("\n"), []
    for i, ln in enumerate(lines):
        if "skills" in ln.lower():
            # next non-empty line with commas
            for nxt in lines[i+1: i+5]:
                if "," in nxt:
                    skills = [s.strip().title() for s in nxt.split(",") if s.strip()]
                    break
            break
    return skills

def extract_job_title(text):
    for ln in text.split("\n"):
        if ln.lower().startswith("job title"):
            return ln.split(":",1)[1].strip().title()
    return "Uploaded Job"

def analyze_cv_vs_dataset(skills, jobs_df, vectorizer):
    input_vec = vectorizer.transform([" ".join(skills).lower()])
    job_vecs  = vectorizer.transform(jobs_df[['Required Skills','Responsibilities']].astype(str).agg(' '.join,axis=1))
    sims      = cosine_similarity(input_vec, job_vecs)[0]
    jobs_df   = jobs_df.copy()
    jobs_df["Match Score"] = sims.round(2)
    jobs_df = jobs_df.sort_values("Match Score", ascending=False)
    return jobs_df.head(5)[["Job Title","Match Score"]]

# ---------- load static dataset once ----------
DATA_DIR = "Data"
jobs_df   = pd.read_csv(os.path.join(DATA_DIR,"job_descriptions (1).csv"))
vectorizer = TfidfVectorizer(stop_words="english")
vectorizer.fit(jobs_df[['Required Skills','Responsibilities']].astype(str).agg(' '.join,axis=1))

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Resume Tailor AI", layout="centered")
st.title(" Resume Tailor ")

st.write(
"""
Upload your **resume (.docx)** and **job description (.docx)** to see:

*  skill match  
* Overall match %  
* Suggestions to improve  
* Best-fit roles from our dataset
"""
)

res_file = st.file_uploader("Upload Resume (.docx)", type=["docx"])
job_file = st.file_uploader("Upload Job Description (.docx)", type=["docx"])

if res_file and job_file:
    # ----- extract texts -----
    res_text  = extract_text_from_docx(res_file)
    job_text  = extract_text_from_docx(job_file)

    # ----- parse sections -----
    about_me  = extract_about_me(res_text)
    cv_skills = extract_comma_skills(res_text)
    job_skills= extract_comma_skills(job_text)
    job_title = extract_job_title(job_text)

    # ----- skill match -----
    cv_set, job_set = set(map(str.lower,cv_skills)), set(map(str.lower,job_skills))
    matched  = sorted(cv_set & job_set)
    missing  = sorted(job_set - cv_set)
    match_pct= int(len(matched)/len(job_set)*100) if job_set else 0

    st.subheader(" Skill Match Breakdown")
    for s in matched : st.success(f"Possesing: {s.title()}")
    for s in missing : st.error  (f"Lacking: {s.title()}")

    st.markdown(f" Match Percentage: **{match_pct}%**")

    # ----- simple suggestions -----
    if missing:
        st.info(f"Consider adding: **{', '.join(missing)}** to improve alignment with *{job_title}*.")

    # ----- dataset-wide role suggestion -----
    top_roles = analyze_cv_vs_dataset(cv_skills, jobs_df, vectorizer)
    st.subheader(" Roles you seem best suited for (internal dataset)")
    st.write(top_roles)

    # bar chart
    fig, ax = plt.subplots()
    ax.barh(top_roles["Job Title"][::-1], top_roles["Match Score"][::-1])
    ax.set_xlabel("Match Score")
    ax.set_title("Top Matches")
    st.pyplot(fig)

    # ----- About Me feedback -----
    soft = ["team","communication","initiative","creative","adaptable","detail","leadership","goal"]
    needed = [w for w in soft if any(w in r.lower() for r in jobs_df["Responsibilities"]) and w not in about_me.lower()]
    st.subheader("About-Me suggestion")
    if len(about_me.split())<30:
        st.warning("Try expanding your About-Me with more detail.")
    if needed:
        st.info(f"Consider mentioning soft skills like **{', '.join(needed[:3])}**.")
    if not needed and len(about_me.split())>=30:
        st.success("Looks good! Your About-Me aligns well.")

else:
    st.stop()

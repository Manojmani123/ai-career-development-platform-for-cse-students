import os
import pdfplumber
from docx import Document


def extract_text_from_resume(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    text = ""

    if ext == ".pdf":
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

    elif ext == ".docx":
        doc = Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"

    return text


def is_valid_resume(text):
    resume_keywords = [
        "skills",
        "education",
        "experience",
        "projects",
        "certifications",
        "internship",
        "employment",
        "technical skills",
    ]

    text_lower = text.lower()
    matches = 0

    for keyword in resume_keywords:
        if keyword in text_lower:
            matches += 1

    return matches >= 2


def extract_skills_from_text(text, skills):
    extracted_skills = []

    text_lower = text.lower()

    for skill in skills:
        if skill.skill_name.lower() in text_lower:
            extracted_skills.append(skill)

    return extracted_skills
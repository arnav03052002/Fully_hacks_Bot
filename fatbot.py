import re
from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from groq import Groq
# === Init app ===
app = FastAPI()

# === Setup Vectorstore and LLM ===
embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
vectordb = Chroma(persist_directory="chroma_store", embedding_function=embedding)
all_raw_docs = vectordb.get()["documents"]
all_docs = [Document(page_content=doc) for doc in all_raw_docs]

client = Groq(api_key="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")

# === Request body ===
class QueryRequest(BaseModel):
    question: str

# === Utils ===
def extract_course_code(q):
    match = re.search(r"CPSC[\s]?\d{3}", q.upper())
    if match:
        raw = match.group(0).replace(" ", "")
        return f"{raw[:4]} {raw[4:]}"
    return None

def extract_professor_name(q, docs):
    profs = set()
    for doc in docs:
        for line in doc.page_content.splitlines():
            if line.startswith("Professor: "):
                name = line.split("Professor: ")[1].strip()
                profs.add(name.lower())
    for prof in profs:
        if prof in q.lower():
            return prof.title()
    return None

def filter_by_course_code(docs, course_code):
    return [doc for doc in docs if f"Course Code: {course_code}" in doc.page_content]

def filter_by_professor_name(docs, professor_name):
    return [doc for doc in docs if f"Professor: {professor_name}" in doc.page_content]

# === Endpoint ===
@app.post("/ask")
async def ask_question(request: QueryRequest):
    question = request.question
    course_code = extract_course_code(question)
    professor_name = extract_professor_name(question, all_docs)

    matching_docs = []
    if course_code:
        matching_docs = filter_by_course_code(all_docs, course_code)
    elif professor_name:
        matching_docs = filter_by_professor_name(all_docs, professor_name)
    else:
        matching_docs = all_docs

    if not matching_docs:
        return {"answer": "Sorry, I couldn't find anything that matches."}

    # === Direct answer if course matched
    if course_code:
        profs = []
        seen = set()
        for doc in matching_docs:
            for line in doc.page_content.splitlines():
                if line.startswith("Professor: "):
                    name = line.split("Professor: ")[1].strip()
                    if name not in seen:
                        profs.append(name)
                        seen.add(name)
        if profs:
            return {"answer": f"Professors who teach {course_code}", "professors": profs}

    # === Direct answer if prof matched
    if professor_name:
        courses = []
        seen = set()
        for doc in matching_docs:
            for line in doc.page_content.splitlines():
                if line.startswith("Course Code: "):
                    code = line.split("Course Code: ")[1].strip()
                    if code not in seen:
                        courses.append(code)
                        seen.add(code)
        if courses:
            return {"answer": f"Courses taught by {professor_name}", "courses": courses}

    # === Fallback to LLM with trimmed context
    if len(matching_docs) > 20:
        matching_docs = matching_docs[:20]
    context = "\n\n".join(doc.page_content for doc in matching_docs)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a CSUF course-professor assistant. Answer only using the context provided.\n"
                "DO NOT guess or invent information. If the answer is not found in the context, say so."
            )
        },
        {
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {question}"
        }
    ]

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages
    )

    return {"answer": response.choices[0].message.content.strip()}

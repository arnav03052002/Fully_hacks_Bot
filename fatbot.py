# import re
# from fastapi import FastAPI, Request
# from pydantic import BaseModel
# from fastapi.middleware.cors import CORSMiddleware
# from langchain_community.vectorstores import Chroma
# from langchain_huggingface import HuggingFaceEmbeddings
# from langchain_core.documents import Document
# from groq import Groq
# # === Init app ===
# app = FastAPI()

# # === Setup Vectorstore and LLM ===
# embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
# vectordb = Chroma(persist_directory="chroma_store", embedding_function=embedding)
# all_raw_docs = vectordb.get()["documents"]
# all_docs = [Document(page_content=doc) for doc in all_raw_docs]

# client = Groq(api_key="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")

# # === Request body ===
# class QueryRequest(BaseModel):
#     question: str

# # === Utils ===
# def extract_course_code(q):
#     match = re.search(r"CPSC[\s]?\d{3}", q.upper())
#     if match:
#         raw = match.group(0).replace(" ", "")
#         return f"{raw[:4]} {raw[4:]}"
#     return None

# def extract_professor_name(q, docs):
#     profs = set()
#     for doc in docs:
#         for line in doc.page_content.splitlines():
#             if line.startswith("Professor: "):
#                 name = line.split("Professor: ")[1].strip()
#                 profs.add(name.lower())
#     for prof in profs:
#         if prof in q.lower():
#             return prof.title()
#     return None

# def filter_by_course_code(docs, course_code):
#     return [doc for doc in docs if f"Course Code: {course_code}" in doc.page_content]

# def filter_by_professor_name(docs, professor_name):
#     return [doc for doc in docs if f"Professor: {professor_name}" in doc.page_content]

# # === Endpoint ===
# @app.post("/ask")
# async def ask_question(request: QueryRequest):
#     question = request.question
#     course_code = extract_course_code(question)
#     professor_name = extract_professor_name(question, all_docs)

#     matching_docs = []
#     if course_code:
#         matching_docs = filter_by_course_code(all_docs, course_code)
#     elif professor_name:
#         matching_docs = filter_by_professor_name(all_docs, professor_name)
#     else:
#         matching_docs = all_docs

#     if not matching_docs:
#         return {"answer": "Sorry, I couldn't find anything that matches."}

#     # === Direct answer if course matched
#     if course_code:
#         profs = []
#         seen = set()
#         for doc in matching_docs:
#             for line in doc.page_content.splitlines():
#                 if line.startswith("Professor: "):
#                     name = line.split("Professor: ")[1].strip()
#                     if name not in seen:
#                         profs.append(name)
#                         seen.add(name)
#         if profs:
#             return {"answer": f"Professors who teach {course_code}", "professors": profs}

#     # === Direct answer if prof matched
#     if professor_name:
#         courses = []
#         seen = set()
#         for doc in matching_docs:
#             for line in doc.page_content.splitlines():
#                 if line.startswith("Course Code: "):
#                     code = line.split("Course Code: ")[1].strip()
#                     if code not in seen:
#                         courses.append(code)
#                         seen.add(code)
#         if courses:
#             return {"answer": f"Courses taught by {professor_name}", "courses": courses}

#     # === Fallback to LLM with trimmed context
#     if len(matching_docs) > 20:
#         matching_docs = matching_docs[:20]
#     context = "\n\n".join(doc.page_content for doc in matching_docs)

#     messages = [
#         {
#             "role": "system",
#             "content": (
#                 "You are a CSUF course-professor assistant. Answer only using the context provided.\n"
#                 "DO NOT guess or invent information. If the answer is not found in the context, say so."
#             )
#         },
#         {
#             "role": "user",
#             "content": f"Context:\n{context}\n\nQuestion: {question}"
#         }
#     ]

#     response = client.chat.completions.create(
#         model="llama-3.1-8b-instant",
#         messages=messages
#     )

#     return {"answer": response.choices[0].message.content.strip()}

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from groq import Groq
import re

# === FastAPI Setup ===
app = FastAPI()

# Allow CORS for your frontend (adjust origins if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Use specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Load Vector DB and Groq LLM ===
# embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
# vectordb = Chroma(persist_directory="chroma_store", embedding_function=embedding)
# retriever = vectordb.as_retriever(search_kwargs={"k": 8})

# client = Groq(api_key="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")

# # === Request Model ===
# class ChatRequest(BaseModel):
#     question: str

# # === Root Endpoint ===
# @app.get("/")
# def read_root():
#     return {"message": "✅ CSUF Chatbot is running!"}

# # === Healthcheck Endpoint ===
# @app.get("/health")
# def health_check():
#     return {"status": "ok"}

# # === Ask Endpoint ===
# @app.post("/ask")
# def ask_question(payload: ChatRequest):
#     question = payload.question

#     def expand_course_numbers(q):
#         match = re.findall(r'\b(\d{3})\b', q)
#         for num in match:
#             q += f" CPSC {num} CPSC{num}"
#         return q

#     expanded_query = expand_course_numbers(question)
#     docs = retriever.invoke(expanded_query)

#     # === Boost exact course match ===
#     course_code_pattern = re.search(r"CPSC[\s]?\d{3}", question.upper())
#     if course_code_pattern:
#         code = course_code_pattern.group(0).replace(" ", "")
#         all_docs = vectordb.get()["documents"]
#         for i, doc_text in enumerate(all_docs):
#             if code in doc_text.replace(" ", ""):
#                 boosted_doc = all_docs[i]
#                 docs.insert(0, Document(page_content=boosted_doc))
#                 break

#     # === Filter to matching course number ===
#     course_num_match = re.search(r"\b(\d{3})\b", question)
#     if course_num_match:
#         course_number = course_num_match.group(1)
#         filtered_docs = [
#             doc for doc in docs if f"Course Number: {course_number}" in doc.page_content
#         ]
#         if filtered_docs:
#             docs = filtered_docs

#     if not docs:
#         return {"answer": "🤖 No relevant information found."}

#     context = "\n\n".join(doc.page_content for doc in docs)

#     messages = [
#         {
#             "role": "system",
#             "content": (
#                 "You are a helpful assistant that answers questions about CSUF professors and their courses.\n"
#                 "Only use the information provided in the context. Do not guess or hallucinate.\n\n"
#                 "Each course record includes the following fields:\n"
#                 "- Professor\n"
#                 "- Course Code (e.g., CPSC 131)\n"
#                 "- Course Number (e.g., 131)\n"
#                 "- Course Name\n"
#                 "- Units\n"
#                 "- Description\n"
#                 "- Prerequisite\n"
#                 "- Corequisite\n"
#                 "- Graduate Eligibility\n"
#                 "- Total Students\n"
#                 "- Grade Counts: A, B, C, D, F\n"
#                 "- Avg GPA\n"
#                 "- Rating (out of 5)\n"
#                 "- Difficulty (1 easiest – 5 hardest)\n"
#                 "- Would Take Again (%)\n\n"
#                 "Use only this context to answer the user's question accurately."
#             )
#         },
#         {
#             "role": "user",
#             "content": f"Context:\n{context}\n\nQuestion: {question}"
#         }
#     ]

#     response = client.chat.completions.create(
#         model="llama-3.1-8b-instant",
#         messages=messages
#     )

#     return {"answer": response.choices[0].message.content.strip()}
# -*- coding: utf-8 -*-
import re
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from groq import Groq

# === FastAPI Setup ===
app = FastAPI()

# === CORS for frontend communication ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set to frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Load Vector DB and Groq LLM ===
embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectordb = Chroma(persist_directory="chroma_store", embedding_function=embedding)
retriever = vectordb.as_retriever(search_kwargs={"k": 8})

client = Groq(api_key="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")

# === Request Model ===
class ChatRequest(BaseModel):
    question: str

# === Root & Health Check ===
@app.get("/")
def root():
    return {"message": "✅ CSUF Chatbot API is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

# === Chat Endpoint ===
@app.post("/chat")
async def chat(req: ChatRequest):
    question = req.question

    def expand_course_numbers(q):
        match = re.findall(r'\b(\d{3})\b', q)
        for num in match:
            q += f" CPSC {num} CPSC{num}"
        return q

    try:
        expanded_query = expand_course_numbers(question)
        docs = retriever.invoke(expanded_query)

        # Boost match for exact course code
        course_code_pattern = re.search(r"CPSC[\s]?\d{3}", question.upper())
        if course_code_pattern:
            code = course_code_pattern.group(0).replace(" ", "")
            all_docs = vectordb.get()["documents"]
            for i, doc_text in enumerate(all_docs):
                if code in doc_text.replace(" ", ""):
                    boosted_doc = all_docs[i]
                    docs.insert(0, Document(page_content=boosted_doc))
                    break

        if not docs:
            return {"response": "🤖 No relevant information found."}

        context = "\n\n".join(doc.page_content for doc in docs)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant that answers questions about CSUF professors and their courses.\n"
                    "Only use the information provided in the context. Do not guess or hallucinate.\n\n"
                    "Each course record includes fields like:\n"
                    "- Professor, Course Code, Course Name, Units, Description, Prerequisite, Avg GPA, Rating, Difficulty, etc."
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

        return {"response": response.choices[0].message.content.strip()}

    except Exception as e:
        return {"error": str(e)}

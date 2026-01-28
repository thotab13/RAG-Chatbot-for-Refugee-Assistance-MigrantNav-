import os
import re
import random
import chainlit as cl
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_message_histories import ChatMessageHistory

# Import your retrievers
from retriever import (
    get_dublin_retriever, get_charter_retriever, get_de_procedure_retriever,
    get_subsidiary_retriever, get_free_movement_retriever, get_geneva_retriever,
    fetch_article_text, fetch_subsidiary_article_text, fetch_geneva_article_text
)

# -----------------------------
# CONFIGURATION
# -----------------------------
ARTICLE_RE = re.compile(r"article\s+(\d+)", re.IGNORECASE)

LOADING_QUOTES = [
    "🌍 Checking EU regulations...", 
    "⚖️ Analyzing asylum criteria...", 
    "🛂 Verifying procedures...",
    "📖 Consulting the Geneva Convention..."
]

# -----------------------------
# INITIALIZATION
# -----------------------------
print("🔌 Initializing MigrantNav Multilingual...")

# Initialize retrievers
# We use 'k' to determine how many chunks to read.
dublin_retriever = get_dublin_retriever(k=8)
charter_retriever = get_charter_retriever(k=4)
de_retriever = get_de_procedure_retriever(k=6)
subsidiary_retriever = get_subsidiary_retriever(k=6)
free_movement_retriever = get_free_movement_retriever(k=6)
geneva_retriever = get_geneva_retriever(k=4)

# MAIN BRAIN (The Chatbot)
llm = ChatOllama(model="qwen2.5:7b", temperature=0)

# -----------------------------
# MULTILINGUAL TRANSLATION LAYER
# -----------------------------
async def detect_and_translate(user_query: str):
    """
    Translates non-English queries to English for better search results.
    Returns: (english_query, detected_language)
    """
    # We ask the LLM to act as a translator tool
    prompt = f"""
    Task: Identify the language of the query and translate it to English.
    If it is already English, return it exactly as is.
    
    Format Output EXACTLY like this:
    Language: [Language Name]
    Translation: [English Text]

    Query: "{user_query}"
    """
    try:
        response = await cl.make_async(llm.invoke)(prompt)
        content = response.content.strip()
        
        # Parse the rigid output format
        lines = content.splitlines()
        lang_line = next((l for l in lines if "Language:" in l), "Language: English")
        trans_line = next((l for l in lines if "Translation:" in l), f"Translation: {user_query}")
        
        detected_lang = lang_line.split(":")[1].strip()
        english_text = trans_line.split(":")[1].strip()
        
        return english_text, detected_lang
    except Exception as e:
        print(f"Translation Error: {e}")
        return user_query, "English" # Fail safe

# -----------------------------
# PROMPTS
# -----------------------------
# This prompt forces the AI to read English laws but speak User's Language
qa_template = """
You are 'MigrantNav', a helpful assistant for migrants and asylum seekers.
You are answering a user who speaks: {user_language}.

Instructions:
1. Use ONLY the Context below (which is in English laws).
2. Answer the user's question clearly and accurately.
3. CRITICAL: WRITE YOUR ANSWER IN {user_language}.
4. If the context does not contain the answer, say (in {user_language}) that you do not know and recommend consulting a lawyer.
5. Do not make up laws.

Context from Database:
{context}

User Question (Original): {original_question}

Answer in {user_language}:
"""
qa_prompt = ChatPromptTemplate.from_template(qa_template)
qa_chain = qa_prompt | llm | StrOutputParser()

# Article Explainer Prompt
article_template = """
You are explaining a specific legal article to a user who speaks {user_language}.

Context (Official Text):
{context}

User Question: {original_question}

Task: Explain the article above in simple {user_language}.
"""
article_prompt = ChatPromptTemplate.from_template(article_template)
article_chain = article_prompt | llm | StrOutputParser()

# -----------------------------
# HELPERS (Formatters)
# -----------------------------
def format_docs(header, docs):
    if not docs: return ""
    return f"{header}:\n" + "\n".join([f"[{d.metadata.get('source','')}]\n{d.page_content}" for d in docs])

def is_minor_query(text: str) -> bool:
    keywords = ["minor", "child", "17-year", "16-year", "15-year", "unaccompanied"]
    return any(k in text.lower() for k in keywords)

# -----------------------------
# CHAINLIT MAIN LOOP
# -----------------------------
@cl.on_chat_start
async def start():
    cl.user_session.set("history", ChatMessageHistory())
    await cl.Message(content="**👋 MigrantNav Online.**\n\nI can answer in **English, German, Arabic, French, and more**.\n\n*Try asking: 'Wie funktioniert das Dublin-Verfahren?'*").send()

@cl.on_message
async def main(message: cl.Message):
    history = cl.user_session.get("history")
    msg = cl.Message(content="")
    
    # 1. TRANSLATION STEP
    loading_msg = cl.Message(content="🌐 Detecting language...", author="system")
    await loading_msg.send()
    
    english_query, user_lang = await detect_and_translate(message.content)
    
    # --- FIX START: Assign content first, then update() ---
    if user_lang.lower() not in ["english", "en"]:
        loading_msg.content = f"🌍 Detected **{user_lang}**. Searching laws in English: *'{english_query}'*"
        await loading_msg.update()
    else:
        loading_msg.content = random.choice(LOADING_QUOTES)
        await loading_msg.update()
    # --- FIX END ---

    # 2. CHECK FOR DIRECT ARTICLE LOOKUP (Regex)
    m = ARTICLE_RE.search(english_query)
    
    try:
        if m:
            # Direct Article Mode
            art_num = int(m.group(1))
            art_text = fetch_article_text(art_num) or fetch_subsidiary_article_text(art_num) or fetch_geneva_article_text(art_num)
            
            if not art_text:
                await msg.stream_token(f"I could not find Article {art_num} in the database.")
            else:
                async for chunk in article_chain.astream({
                    "context": art_text,
                    "original_question": message.content,
                    "user_language": user_lang
                }):
                    await msg.stream_token(chunk)
        
        else:
            # 3. RAG SEARCH (Standard Mode)
            dublin_docs = await cl.make_async(dublin_retriever.invoke)(english_query)
            de_docs = await cl.make_async(de_retriever.invoke)(english_query)
            charter_docs = await cl.make_async(charter_retriever.invoke)(english_query)
            subs_docs = await cl.make_async(subsidiary_retriever.invoke)(english_query)
            
            # Combine Contexts
            context_text = "\n\n".join([
                format_docs("DUBLIN REGULATION", dublin_docs),
                format_docs("GERMAN PROCEDURE", de_docs),
                format_docs("EU CHARTER", charter_docs),
                format_docs("SUBSIDIARY PROTECTION", subs_docs)
            ])
            
            # Minor Booster
            if is_minor_query(english_query):
                art8 = fetch_article_text(8)
                if art8: context_text = f"IMPORTANT (UNACCOMPANIED MINORS):\n{art8}\n\n{context_text}"

            # 4. GENERATE ANSWER
            async for chunk in qa_chain.astream({
                "context": context_text,
                "original_question": message.content,
                "user_language": user_lang
            }):
                await msg.stream_token(chunk)

    except Exception as e:
        await msg.stream_token(f"❌ Error: {e}")

    await loading_msg.remove()
    history.add_user_message(message.content)
    history.add_ai_message(msg.content)
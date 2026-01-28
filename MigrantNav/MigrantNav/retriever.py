#this is retriever.py

import os
import re


from neo4j import GraphDatabase
from langchain_community.vectorstores import Neo4jVector
from langchain_ollama import OllamaEmbeddings



# -----------------------------
# CONFIGURATION
# -----------------------------
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "capstone2026"


NEO4J_URI = os.environ["NEO4J_URI"]
NEO4J_USER = os.environ["NEO4J_USERNAME"]
NEO4J_PASS = os.environ["NEO4J_PASSWORD"]


ARTICLE_RE = re.compile(r"article\s+(\d+)", re.IGNORECASE)



# -----------------------------
# DIRECT ARTICLE LOOKUP (DUBLIN)
# -----------------------------
def fetch_article_text(article_number: int) -> str | None:
    """
    Fetch full text for a given Dublin III article_number from Neo4j.
    Concatenates all Article nodes with that article_number ordered by page.
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    texts = []
    with driver.session() as session:
        res = session.run(
            """
            MATCH (a:Article {article_number: $num})
            RETURN a.text AS text
            ORDER BY a.page
            """,
            {"num": article_number},
        )
        for record in res:
            t = record["text"]
            if t:
                texts.append(t)
    driver.close()
    if not texts:
        return None
    return "\n\n".join(texts)



# -----------------------------
# DIRECT ARTICLE LOOKUP (CHARTER)
# -----------------------------
def fetch_charter_article_text(article_number: int) -> str | None:
    """
    Fetch full text for a given Charter article number from Neo4j.
    Concatenates all CharterArticle nodes with that number ordered by page.
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    texts = []
    with driver.session() as session:
        res = session.run(
            """
            MATCH (c:CharterArticle {charter_article_number: $num})
            RETURN c.text AS text
            ORDER BY c.page
            """,
            {"num": article_number},
        )
        for record in res:
            t = record["text"]
            if t:
                texts.append(t)
    driver.close()
    if not texts:
        return None
    return "\n\n".join(texts)



# -----------------------------
# DIRECT ARTICLE LOOKUP (SUBSIDIARY REGULATION 2024/1347)
# -----------------------------
def fetch_subsidiary_article_text(article_number: int) -> str | None:
    """
    Fetch full text for a given article of Regulation (EU) 2024/1347
    (qualification / subsidiary protection) from Neo4j.
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    texts = []
    with driver.session() as session:
        res = session.run(
            """
            MATCH (s:SubsidiaryArticle {article_number: $num})
            RETURN s.text AS text
            ORDER BY s.page
            """,
            {"num": article_number},
        )
        for record in res:
            t = record["text"]
            if t:
                texts.append(t)
    driver.close()
    if not texts:
        return None
    return "\n\n".join(texts)



# -----------------------------
# DIRECT ARTICLE LOOKUP (GENEVA CONVENTION)
# -----------------------------
def fetch_geneva_article_text(article_number: int) -> str | None:
    """
    Fetch full text for a given article of the 1951 Refugee Convention from Neo4j.
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    texts = []
    with driver.session() as session:
        res = session.run(
            """
            MATCH (g:GenevaArticle {article_number: $num})
            RETURN g.text AS text
            ORDER BY g.page
            """,
            {"num": article_number},
        )
        for record in res:
            t = record["text"]
            if t:
                texts.append(t)
    driver.close()
    if not texts:
        return None
    return "\n\n".join(texts)



# -----------------------------
# VECTOR RETRIEVERS
# -----------------------------
def _get_embeddings():
    return OllamaEmbeddings(model="nomic-embed-text")



def get_dublin_retriever(k: int = 8):
    """
    Neo4j-based retriever over Dublin III Article nodes.
    Uses 'dublin_articles_index' index and 'Article' label.
    """
    embeddings = _get_embeddings()


    vector_store = Neo4jVector.from_existing_graph(
        embedding=embeddings,
        url=NEO4J_URI,
        username=NEO4J_USER,
        password=NEO4J_PASS,
        index_name="dublin_articles_index",
        node_label="Article",
        text_node_properties=["text"],
        embedding_node_property="embedding",
    )


    retriever = vector_store.as_retriever(search_kwargs={"k": k})
    return retriever



def get_charter_retriever(k: int = 4):
    """
    Neo4j-based retriever over CharterArticle nodes.
    Uses 'charter_index' index and 'CharterArticle' label.
    """
    embeddings = _get_embeddings()


    vector_store = Neo4jVector.from_existing_graph(
        embedding=embeddings,
        url=NEO4J_URI,
        username=NEO4J_USER,
        password=NEO4J_PASS,
        index_name="charter_index",
        node_label="CharterArticle",
        text_node_properties=["text"],
        embedding_node_property="embedding",
    )


    retriever = vector_store.as_retriever(search_kwargs={"k": k})
    return retriever



def get_de_procedure_retriever(k: int = 6):
    """
    Neo4j-based retriever over German asylum procedure chunks (DEProcedure).
    Uses 'de_procedure_index' index and 'DEProcedure' label.
    """
    embeddings = _get_embeddings()


    vector_store = Neo4jVector.from_existing_graph(
        embedding=embeddings,
        url=NEO4J_URI,
        username=NEO4J_USER,
        password=NEO4J_PASS,
        index_name="de_procedure_index",
        node_label="DEProcedure",
        text_node_properties=["text"],
        embedding_node_property="embedding",
    )


    retriever = vector_store.as_retriever(search_kwargs={"k": k})
    return retriever



def get_subsidiary_retriever(k: int = 6):
    embeddings = _get_embeddings()
    return Neo4jVector.from_existing_graph(
        embedding=embeddings, url=NEO4J_URI, username=NEO4J_USER, password=NEO4J_PASS,
        index_name="subsidiary_index",  # Create this after ingestion
        node_label="SubsidiarySection", text_node_properties=["text"], embedding_node_property="embedding"
    ).as_retriever(search_kwargs={"k": k})



def get_free_movement_retriever(k: int = 6):
    """
    Neo4j-based retriever over Free Movement guidance chunks.
    Uses 'free_movement_index' index and 'FreeMovementSection' label.
    """
    embeddings = _get_embeddings()


    vector_store = Neo4jVector.from_existing_graph(
        embedding=embeddings,
        url=NEO4J_URI,
        username=NEO4J_USER,
        password=NEO4J_PASS,
        index_name="free_movement_index",
        node_label="FreeMovementSection",
        text_node_properties=["text"],
        embedding_node_property="embedding",
    )


    retriever = vector_store.as_retriever(search_kwargs={"k": k})
    return retriever



def get_geneva_retriever(k: int = 6):
    """
    Neo4j-based retriever over 1951 Refugee Convention articles.
    Uses 'geneva_index' index and 'GenevaArticle' label.
    """
    embeddings = _get_embeddings()


    vector_store = Neo4jVector.from_existing_graph(
        embedding=embeddings,
        url=NEO4J_URI,
        username=NEO4J_USER,
        password=NEO4J_PASS,
        index_name="geneva_index",
        node_label="GenevaArticle",
        text_node_properties=["text"],
        embedding_node_property="embedding",
    )


    retriever = vector_store.as_retriever(search_kwargs={"k": k})
    return retriever



# Backwards-compatible alias if old code still imports get_retriever
def get_retriever(k: int = 8):
    return get_dublin_retriever(k=k)



# -----------------------------
# QUICK MANUAL TEST (optional)
# -----------------------------
if __name__ == "__main__":
    from langchain_ollama import ChatOllama
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser


    print("🕵️‍♂️ Testing MigrantNav retrievers...")


    dublin_ret = get_dublin_retriever(k=8)
    charter_ret = get_charter_retriever(k=4)
    de_ret = get_de_procedure_retriever(k=6)
    subsidiary_ret = get_subsidiary_retriever(k=6)
    free_move_ret = get_free_movement_retriever(k=6)
    geneva_ret = get_geneva_retriever(k=4)


    llm = ChatOllama(model="qwen2.5:7b", temperature=0)


    def format_docs(docs):
        parts = []
        for d in docs:
            art_num = (
                d.metadata.get("article_number")
                or d.metadata.get("charter_article_number")
                or d.metadata.get("subsidiary_article_number")
                or d.metadata.get("geneva_article_number")
                or d.metadata.get("topic")
            )
            src = d.metadata.get("source", "")
            parts.append(f"[{art_num} | {src}]\n{d.page_content}")
        return "\n\n".join(parts)


    qa_template = """
You are 'MigrantNav', an information assistant for migrants and asylum seekers in the European Union, with a focus on Germany.


Use ONLY the information in the Context below when giving legal or procedural details.
If the Context does NOT clearly contain the answer, you MUST say that you are not sure and recommend that the user contact a qualified legal adviser, NGO, or official authority.
Do NOT invent article numbers, legal tests, dates, offices, or procedures that are not present in the Context.


Context:
{context}


Question:
{question}


Answer in clear English. If the Context is not sufficient, say that you are not sure and recommend consulting a legal adviser or official office:
"""
    qa_prompt = ChatPromptTemplate.from_template(qa_template)
    qa_chain = qa_prompt | llm | StrOutputParser()


    while True:
        query = input("\n📝 You (test) > ")
        if query.lower() in ["exit", "quit"]:
            break


        dublin_docs = dublin_ret.invoke(query)
        charter_docs = charter_ret.invoke(query)
        de_docs = de_ret.invoke(query)
        subs_docs = subsidiary_ret.invoke(query)
        fm_docs = free_move_ret.invoke(query)
        geneva_docs = geneva_ret.invoke(query)


        ctx_parts = []
        if dublin_docs:
            ctx_parts.append("DUBLIN CONTEXT:\n" + format_docs(dublin_docs))
        if charter_docs:
            ctx_parts.append("CHARTER CONTEXT:\n" + format_docs(charter_docs))
        if de_docs:
            ctx_parts.append("GERMAN PROCEDURE CONTEXT:\n" + format_docs(de_docs))
        if subs_docs:
            ctx_parts.append("SUBSIDIARY / QUALIFICATION CONTEXT:\n" + format_docs(subs_docs))
        if fm_docs:
            ctx_parts.append("FREE MOVEMENT CONTEXT:\n" + format_docs(fm_docs))
        if geneva_docs:
            ctx_parts.append("GENEVA CONVENTION CONTEXT:\n" + format_docs(geneva_docs))


        ctx = "\n\n".join(ctx_parts) if ctx_parts else ""
        answer = qa_chain.invoke({"context": ctx, "question": query})
        print("\n🤖 MigrantNav:\n", answer)
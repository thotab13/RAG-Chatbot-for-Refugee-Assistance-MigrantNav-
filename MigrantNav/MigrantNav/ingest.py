import os
import re
import hashlib
from datetime import date
from typing import List

# LangChain Imports
from langchain_neo4j import Neo4jGraph
from langchain_community.document_loaders import PyPDFLoader
from langchain_ollama import ChatOllama, OllamaEmbeddings  # <-- ADDED EMBEDDINGS
from langchain_core.documents import Document

# -----------------------------
# CONFIGURATION
# -----------------------------
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "capstone2026"

# Paths
PDF_DUBLIN = "./data/DUBLIN REGULATIONS.pdf"
PDF_CHARTER = "./data/CHARTER_OF_FUNDAMENTAL_RIGHTS.pdf"
PDF_DE_PROC = "./data/DE_ASYLUM_PROCEDURE_STAGES.pdf"
PDF_SUBSIDIARY = "./data/Subsidiary Protection - Third-country nations.pdf"
PDF_FREE_MOVE = "./data/Guidance on the right of free movement of EU citizens and their families.pdf"
PDF_REFUGEE_CONV = "./data/1951-Refugee Convention-1967-protocol (UNHCR Mandate).pdf"

# Dates
VALID_FROM_SUBSIDIARY = date(2024, 5, 22).isoformat()
VALID_FROM_FREE_MOVE = date(2023, 12, 22).isoformat()
VALID_FROM_REFUGEE_CONV = date(1954, 4, 22).isoformat()
VALID_FROM_DUBLIN = date(2013, 6, 19).isoformat()
VALID_FROM_CHARTER = date(2009, 12, 1).isoformat()
VALID_FROM_DE_PROC = date(2020, 1, 1).isoformat()
JURISDICTION = "EU"

ARTICLE_RE = re.compile(r"^Article\s+(\d+)", re.IGNORECASE)

# -----------------------------
# AI MODELS
# -----------------------------
print("🔌 Initializing AI Models...")
llm = ChatOllama(model="qwen2.5:7b", temperature=0)

# CRITICAL: The Embedding Model (Must match what you use in retrieval)
embeddings = OllamaEmbeddings(model="nomic-embed-text")

# -----------------------------
# HELPER: CALCULATE EMBEDDING
# -----------------------------
def get_embedding(text: str) -> List[float]:
    """Generates a vector embedding for the given text."""
    # Ensure text is not empty to avoid errors
    if not text or not text.strip():
        return []
    return embeddings.embed_query(text)

# -----------------------------
# NEO4J INITIALIZATION
# -----------------------------
def init_graph() -> Neo4jGraph:
    graph = Neo4jGraph()

    print("🧹 Cleaning old data (if any)...")
    # Hard reset of previous data
    graph.query("MATCH (r:Regulation)-[*0..3]-() DETACH DELETE r")
    graph.query("MATCH (a:Article) DETACH DELETE a")
    graph.query("MATCH (c:CharterArticle) DETACH DELETE c")
    graph.query("MATCH (d:DEProcedure) DETACH DELETE d")
    graph.query("MATCH (n:Country) DETACH DELETE n")
    graph.query("MATCH (s:SubsidiarySection) DETACH DELETE s") # Fixed label name
    graph.query("MATCH (f:FreeMovementSection) DETACH DELETE f")
    graph.query("MATCH (g:GenevaArticle) DETACH DELETE g")

    # Constraints
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (r:Regulation) REQUIRE r.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Article) REQUIRE a.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:CharterArticle) REQUIRE c.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (d:DEProcedure) REQUIRE d.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Country) REQUIRE c.code IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (s:SubsidiarySection) REQUIRE s.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (f:FreeMovementSection) REQUIRE f.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (g:GenevaArticle) REQUIRE g.id IS UNIQUE",
    ]

    for q in constraints:
        graph.query(q)

    return graph

# -----------------------------
# CORE LEGAL STRUCTURE
# -----------------------------
def create_core_legal_structure(graph: Neo4jGraph):
    print("🏗️ Building Core Legal Structure...")
    
    # Dublin III
    graph.query("""
        MERGE (r:Regulation {id: "EU_604_2013"})
        SET r.name = "Dublin III Regulation",
            r.valid_from = $valid_from,
            r.jurisdiction = $jurisdiction
        """, {"valid_from": VALID_FROM_DUBLIN, "jurisdiction": JURISDICTION})

    # Charter
    graph.query("""
        MERGE (r:Regulation {id: "EU_CHARTER_2000"})
        SET r.name = "Charter of Fundamental Rights of the European Union",
            r.valid_from = $valid_from,
            r.jurisdiction = $jurisdiction
        """, {"valid_from": VALID_FROM_CHARTER, "jurisdiction": JURISDICTION})

    # DE Asylum Procedure
    graph.query("""
        MERGE (r:Regulation {id: "DE_ASYLUM_STAGES"})
        SET r.name = "Stages of the German Asylum Procedure",
            r.valid_from = $valid_from,
            r.jurisdiction = "DE"
        """, {"valid_from": VALID_FROM_DE_PROC})

    # Qualification / Subsidiary
    graph.query("""
        MERGE (r:Regulation {id: "EU_2024_1347"})
        SET r.name = "Regulation (EU) 2024/1347 on qualification and subsidiary protection",
            r.valid_from = $valid_from,
            r.jurisdiction = "EU"
        """, {"valid_from": VALID_FROM_SUBSIDIARY})

    # Free movement guidance
    graph.query("""
        MERGE (r:Regulation {id: "EU_FREE_MOVE_GUIDE_2023"})
        SET r.name = "Guidance on the right of free movement of EU citizens and their families",
            r.valid_from = $valid_from,
            r.jurisdiction = "EU",
            r.is_guidance = true
        """, {"valid_from": VALID_FROM_FREE_MOVE})

    # Geneva Convention
    graph.query("""
        MERGE (r:Regulation {id: "UN_GENEVA_1951"})
        SET r.name = "1951 Refugee Convention and 1967 Protocol",
            r.valid_from = $valid_from,
            r.jurisdiction = "INTL"
        """, {"valid_from": VALID_FROM_REFUGEE_CONV})

    # EU Dublin states
    eu_states = [
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI",
        "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU",
        "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
    ]
    for code in eu_states:
        graph.query("""
            MERGE (:Country {
                code: $code,
                jurisdiction: "EU",
                is_dublin_applicable: true
            })
            """, {"code": code})

# -----------------------------
# PDF SPLITTING UTILS
# -----------------------------
def split_pdf_into_articles(pdf_path: str, is_charter: bool = False, article_regex: re.Pattern = ARTICLE_RE, meta_key_override: str = None, label_name: str = None) -> List[Document]:
    loader = PyPDFLoader(pdf_path)
    raw_docs = loader.load()

    all_text = ""
    page_offsets = []
    for d in raw_docs:
        page_text = d.page_content or ""
        start_idx = len(all_text)
        all_text += page_text + "\n"
        page_offsets.append((start_idx, d.metadata.get("page", 0)))

    lines = all_text.splitlines()
    line_offsets = []
    char_index = 0
    for line in lines:
        line_offsets.append(char_index)
        char_index += len(line) + 1

    def guess_page(start_char: int) -> int:
        page = 0
        for off, p in reversed(page_offsets):
            if start_char >= off:
                page = p
                break
        return page

    articles: List[Document] = []
    current_lines = []
    current_article_num = None
    current_start_idx = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        m = article_regex.match(stripped)
        if m:
            if current_article_num is not None and current_lines:
                article_text = "\n".join(current_lines).strip()
                start_char = current_start_idx
                page = guess_page(start_char)
                meta_key = meta_key_override if meta_key_override else ("charter_article_number" if is_charter else "article_number")
                
                articles.append(Document(
                    page_content=article_text,
                    metadata={meta_key: current_article_num, "source": os.path.basename(pdf_path), "page": page}
                ))
            
            try:
                current_article_num = int(m.group(1))
            except ValueError:
                current_article_num = m.group(1)
            current_lines = [line]
            current_start_idx = line_offsets[i]
        else:
            if current_article_num is not None:
                current_lines.append(line)

    if current_article_num is not None and current_lines:
        article_text = "\n".join(current_lines).strip()
        start_char = current_start_idx
        page = guess_page(start_char)
        meta_key = meta_key_override if meta_key_override else ("charter_article_number" if is_charter else "article_number")
        articles.append(Document(
            page_content=article_text,
            metadata={meta_key: current_article_num, "source": os.path.basename(pdf_path), "page": page}
        ))

    label = label_name or ("Charter" if is_charter else "Dublin")
    print(f"📄 Detected {len(articles)} {label} articles.")
    return articles

# -----------------------------
# DUBLIN INGESTION
# -----------------------------
def ingest_articles(graph: Neo4jGraph, documents: List[Document]):
    print(f"   ... Embedding {len(documents)} Dublin articles...")
    for doc in documents:
        article_num = doc.metadata.get("article_number")
        if article_num is None: continue

        article_id = hashlib.sha256(doc.page_content.encode()).hexdigest()[:16]
        vector = get_embedding(doc.page_content) # <--- Generate Vector

        graph.query("""
            MERGE (a:Article {id: $id})
            SET a.source = $source,
                a.page = $page,
                a.valid_from = $valid_from,
                a.jurisdiction = $jurisdiction,
                a.article_number = $article_number,
                a.text = $text,
                a.embedding = $embedding
            WITH a
            MATCH (r:Regulation {id: "EU_604_2013"})
            MERGE (r)-[:HAS_ARTICLE]->(a)
            """, {
                "id": article_id,
                "source": doc.metadata.get("source"),
                "page": doc.metadata.get("page"),
                "valid_from": VALID_FROM_DUBLIN,
                "jurisdiction": JURISDICTION,
                "article_number": int(article_num),
                "text": doc.page_content,
                "embedding": vector
            })

# -----------------------------
# CHARTER INGESTION
# -----------------------------
def ingest_charter_articles(graph: Neo4jGraph, documents: List[Document]):
    print(f"   ... Embedding {len(documents)} Charter articles...")
    for doc in documents:
        art_num = doc.metadata.get("charter_article_number")
        if art_num is None: continue

        article_id = hashlib.sha256(doc.page_content.encode()).hexdigest()[:16]
        vector = get_embedding(doc.page_content)

        graph.query("""
            MERGE (c:CharterArticle {id: $id})
            SET c.source = $source,
                c.page = $page,
                c.valid_from = $valid_from,
                c.jurisdiction = $jurisdiction,
                c.charter_article_number = $article_number,
                c.text = $text,
                c.embedding = $embedding
            WITH c
            MATCH (r:Regulation {id: "EU_CHARTER_2000"})
            MERGE (r)-[:HAS_CHARTER_ARTICLE]->(c)
            """, {
                "id": article_id,
                "source": doc.metadata.get("source"),
                "page": doc.metadata.get("page"),
                "valid_from": VALID_FROM_CHARTER,
                "jurisdiction": JURISDICTION,
                "article_number": int(art_num),
                "text": doc.page_content,
                "embedding": vector
            })

# -----------------------------
# DE ASYLUM PROCEDURE INGESTION
# -----------------------------
def split_de_procedure_into_chunks(pdf_path: str, chunk_size: int = 800, overlap: int = 150) -> List[Document]:
    loader = PyPDFLoader(pdf_path)
    raw_docs = loader.load()
    chunks: List[Document] = []
    
    for d in raw_docs:
        text = d.page_content or ""
        source = os.path.basename(pdf_path)
        page = d.metadata.get("page", 0)
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]
            if not chunk_text.strip(): break
            doc = Document(page_content=chunk_text.strip(), metadata={"source": source, "page": page, "domain": "de_procedure"})
            chunks.append(doc)
            start = end - overlap
    print(f"📄 Created {len(chunks)} DE procedure chunks.")
    return chunks

def classify_de_topic(text: str) -> str:
    lower = text.lower()
    if "safe countries of origin" in lower: return "safe_countries"
    if "procedure management" in lower or "quality assurance" in lower: return "procedure_management"
    if "interview" in lower or "hearing" in lower: return "interview"
    if "appeal" in lower or "remedy" in lower: return "appeal"
    if "accommodation" in lower or "financial support" in lower: return "reception_benefits"
    if "registration" in lower or "arrival" in lower: return "first_steps"
    return "general"

def ingest_de_procedure(graph: Neo4jGraph, documents: List[Document]):
    print(f"   ... Embedding {len(documents)} DE Procedure chunks...")
    for doc in documents:
        text = doc.page_content
        topic = classify_de_topic(text)
        node_id = hashlib.sha256((text + topic).encode()).hexdigest()[:16]
        vector = get_embedding(text)

        graph.query("""
            MERGE (d:DEProcedure {id: $id})
            SET d.source = $source,
                d.page = $page,
                d.valid_from = $valid_from,
                d.jurisdiction = "DE",
                d.domain = "de_procedure",
                d.topic = $topic,
                d.text = $text,
                d.embedding = $embedding
            WITH d
            MATCH (r:Regulation {id: "DE_ASYLUM_STAGES"})
            MERGE (r)-[:HAS_SECTION]->(d)
            """, {
                "id": node_id,
                "source": doc.metadata.get("source"),
                "page": doc.metadata.get("page"),
                "valid_from": VALID_FROM_DE_PROC,
                "topic": topic,
                "text": text,
                "embedding": vector
            })

# -----------------------------
# SUBSIDIARY PROTECTION INGESTION
# -----------------------------
def split_subsidiary_into_chunks(pdf_path: str, chunk_size: int = 1200, overlap: int = 200) -> List[Document]:
    loader = PyPDFLoader(pdf_path)
    raw_docs = loader.load()
    chunks: List[Document] = []
    for d in raw_docs:
        text = d.page_content or ""
        source = os.path.basename(pdf_path)
        page = d.metadata.get("page", 0)
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end].strip()
            if len(chunk_text) > 100:
                art_matches = ARTICLE_RE.findall(chunk_text)
                topic = f"Article {'/'.join(art_matches[:2]) if art_matches else 'general'}"
                doc = Document(page_content=chunk_text, metadata={"source": source, "page": page, "domain": "subsidiary_protection", "topic": topic})
                chunks.append(doc)
            start = end - overlap
    print(f"📄 Created {len(chunks)} Subsidiary chunks.")
    return chunks

def ingest_subsidiary_chunks(graph: Neo4jGraph, documents: List[Document]):
    print(f"   ... Embedding {len(documents)} Subsidiary chunks...")
    for doc in documents:
        text = doc.page_content
        topic = doc.metadata.get("topic", "general")
        node_id = hashlib.sha256((text + topic).encode()).hexdigest()[:16]
        vector = get_embedding(text)

        graph.query("""
            MERGE (s:SubsidiarySection {id: $id})
            SET s.source = $source,
                s.page = $page,
                s.valid_from = $valid_from,
                s.jurisdiction = $jurisdiction,
                s.domain = "subsidiary_protection",
                s.topic = $topic,
                s.text = $text,
                s.embedding = $embedding
            WITH s
            MATCH (r:Regulation {id: "EU_2024_1347"})
            MERGE (r)-[:HAS_SECTION]->(s)
            """, {
                "id": node_id,
                "source": doc.metadata.get("source"),
                "page": doc.metadata.get("page"),
                "valid_from": VALID_FROM_SUBSIDIARY,
                "jurisdiction": JURISDICTION,
                "topic": topic,
                "text": text,
                "embedding": vector
            })

# -----------------------------
# FREE MOVEMENT INGESTION
# -----------------------------
def split_free_move_into_chunks(pdf_path: str, chunk_size: int = 1200, overlap: int = 200) -> List[Document]:
    loader = PyPDFLoader(pdf_path)
    raw_docs = loader.load()
    chunks: List[Document] = []
    for d in raw_docs:
        text = d.page_content or ""
        source = os.path.basename(pdf_path)
        page = d.metadata.get("page", 0)
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]
            if not chunk_text.strip(): break
            doc = Document(page_content=chunk_text.strip(), metadata={"source": source, "page": page, "domain": "free_movement_guidance"})
            chunks.append(doc)
            start = end - overlap
    print(f"📄 Created {len(chunks)} Free movement chunks.")
    return chunks

def classify_free_move_topic(text: str) -> str:
    lower = text.lower()
    if "frontier worker" in lower or "cross-border" in lower: return "workers_cross_border"
    if "dual national" in lower or "dual eu" in lower: return "dual_nationals"
    if "family member" in lower: return "family_members"
    if "article 27" in lower or "public policy" in lower: return "restrictions_public_policy"
    if "residence card" in lower: return "residence_documents"
    return "general"

def ingest_free_movement_guidance(graph: Neo4jGraph, documents: List[Document]):
    print(f"   ... Embedding {len(documents)} Free Movement chunks...")
    for doc in documents:
        text = doc.page_content
        topic = classify_free_move_topic(text)
        node_id = hashlib.sha256((text + topic).encode()).hexdigest()[:16]
        vector = get_embedding(text)

        graph.query("""
            MERGE (f:FreeMovementSection {id: $id})
            SET f.source = $source,
                f.page = $page,
                f.valid_from = $valid_from,
                f.jurisdiction = "EU",
                f.domain = "free_movement_guidance",
                f.topic = $topic,
                f.text = $text,
                f.embedding = $embedding
            WITH f
            MATCH (r:Regulation {id: "EU_FREE_MOVE_GUIDE_2023"})
            MERGE (r)-[:HAS_SECTION]->(f)
            """, {
                "id": node_id,
                "source": doc.metadata.get("source"),
                "page": doc.metadata.get("page"),
                "valid_from": VALID_FROM_FREE_MOVE,
                "topic": topic,
                "text": text,
                "embedding": vector
            })

# -----------------------------
# GENEVA INGESTION
# -----------------------------
def split_geneva_into_articles(pdf_path: str) -> List[Document]:
    return split_pdf_into_articles(pdf_path, is_charter=False, article_regex=ARTICLE_RE, meta_key_override="geneva_article_number", label_name="Geneva")

def ingest_geneva_articles(graph: Neo4jGraph, documents: List[Document]):
    print(f"   ... Embedding {len(documents)} Geneva articles...")
    for doc in documents:
        art_num = doc.metadata.get("geneva_article_number")
        if art_num is None: continue

        article_id = hashlib.sha256(doc.page_content.encode()).hexdigest()[:16]
        vector = get_embedding(doc.page_content)

        graph.query("""
            MERGE (g:GenevaArticle {id: $id})
            SET g.source = $source,
                g.page = $page,
                g.valid_from = $valid_from,
                g.jurisdiction = "INTL",
                g.article_number = $article_number,
                g.text = $text,
                g.embedding = $embedding
            WITH g
            MATCH (r:Regulation {id: "UN_GENEVA_1951"})
            MERGE (r)-[:HAS_ARTICLE]->(g)
            """, {
                "id": article_id,
                "source": doc.metadata.get("source"),
                "page": doc.metadata.get("page"),
                "valid_from": VALID_FROM_REFUGEE_CONV,
                "article_number": int(art_num) if isinstance(art_num, str) and art_num.isdigit() else art_num,
                "text": doc.page_content,
                "embedding": vector
            })

# -----------------------------
# TAGGING UTILS (UNCHANGED)
# -----------------------------
def tag_article_metadata(graph: Neo4jGraph, article_id: str, text: str):
    # Skipping heavy tagging for speed, but keeping function for future use
    pass 

# -----------------------------
# MAIN INGESTION PIPELINE
# -----------------------------
def ingest_all():
    print("🚀 Starting ingestion (Dublin III + Charter + DE Procedure + Subsidiary + Free Movement + Geneva)")

    # File checks
    for p in [PDF_DUBLIN, PDF_CHARTER, PDF_DE_PROC, PDF_SUBSIDIARY, PDF_FREE_MOVE, PDF_REFUGEE_CONV]:
        if not os.path.exists(p):
            raise FileNotFoundError(f"Missing PDF: {p}")

    graph = init_graph()
    create_core_legal_structure(graph)

    # Dublin
    dublin_docs = split_pdf_into_articles(PDF_DUBLIN, is_charter=False)
    ingest_articles(graph, dublin_docs)

    # Charter
    charter_docs = split_pdf_into_articles(PDF_CHARTER, is_charter=True)
    ingest_charter_articles(graph, charter_docs)

    # DE Asylum Procedure
    de_docs = split_de_procedure_into_chunks(PDF_DE_PROC)
    ingest_de_procedure(graph, de_docs)

    # Subsidiary
    subs_docs = split_subsidiary_into_chunks(PDF_SUBSIDIARY)
    ingest_subsidiary_chunks(graph, subs_docs)

    # Free movement
    fm_docs = split_free_move_into_chunks(PDF_FREE_MOVE)
    ingest_free_movement_guidance(graph, fm_docs)

    # Geneva
    geneva_docs = split_geneva_into_articles(PDF_REFUGEE_CONV)
    ingest_geneva_articles(graph, geneva_docs)

    print("✅ Ingestion & Embedding completed.")

# -----------------------------
# VECTOR INDEX CREATION
# -----------------------------
def create_indexes():
    print("🧮 Verifying Vector Indexes...")
    graph = Neo4jGraph()
    
    # These match the node labels used in ingestion
    configs = {
        "dublin_articles_index": "Article",
        "charter_index": "CharterArticle", 
        "de_procedure_index": "DEProcedure",
        "subsidiary_index": "SubsidiarySection",
        "free_movement_index": "FreeMovementSection",
        "geneva_index": "GenevaArticle",
    }

    for idx, label in configs.items():
        # Check if index exists or create it
        graph.query(f"""
            CREATE VECTOR INDEX {idx} IF NOT EXISTS
            FOR (n:{label}) ON (n.embedding)
            OPTIONS {{indexProvider: 'vector-1.0', indexConfig: {{
                `vector.dimensions`: 768,
                `vector.similarity_function`: 'cosine'
            }} }}
        """)
        print(f"   - Index '{idx}' checked/created.")
    
    print("🎯 Indexes ready! Run: python app.py")

# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    ingest_all()
    create_indexes()
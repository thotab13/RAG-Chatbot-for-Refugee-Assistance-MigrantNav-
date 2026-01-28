# MigrantNav - Multilingual Legal Assistant

## What is MigrantNav?

MigrantNav is a **privacy-first AI assistant** that helps migrants and asylum seekers understand complex European and German immigration laws. Think of it as a knowledgeable legal caseworker that speaks your language, runs on your computer, and never shares your data with anyone.

## Why is it special?

**The Problem with Normal Chatbots:**
- Regular AI chatbots sometimes "make up" answers (called "hallucination")
- They might give wrong legal advice, which can be dangerous

**MigrantNav's Solution:**
- Uses a **hybrid brain**: combines strict legal facts (stored in a database) with AI's language understanding
- **Never invents answers** - only references real laws from verified sources
- Works **completely offline** - your questions stay private on your computer

---

## How Does It Work? (In 4 Steps)

### Step 1: You Ask a Question (Any Language)

You type a question in **your native language**:
- Arabic: *"ما هي حقوقي؟"*
- Ukrainian: *"Які мої права?"*
- English: *"What are my rights?"*

**What Happens:**
- The system detects your language automatically
- Translates your question to English (just for searching the legal database)

---

### Step 2: Finding the Right Laws

**The system searches in two smart ways:**

1. **Semantic Search** (Understanding Meaning):
   - Converts your question into mathematical coordinates (called "vectors")
   - Finds laws that match the *meaning*, not just keywords
   - Example: "Can I work?" matches "employment rights" even without the word "work"

2. **Graph Navigation** (Following Connections):
   - Laws are stored like a family tree - articles connect to definitions, exceptions, and conditions
   - If you ask about "minors," it automatically includes Article 8 (Unaccompanied Minors) even if you didn't mention the article number

---

### Step 3: Gathering Complete Information

**Before answering, the system:**
- Collects the top 8-12 most relevant law sections
- Checks for special cases (e.g., always includes minor protection rules when children are mentioned)
- Packages everything with source references (e.g., "[Dublin III Article 8]")

---

### Step 4: Getting Your Answer

**The AI reads the English laws, then:**
- Writes a clear, compassionate answer **in your original language**
- Includes specific article numbers so you can verify
- Uses simple words instead of legal jargon

**Example Output:**
> *"Based on Dublin III Article 8, unaccompanied minors have the right to family reunification. This means..."* 
> *(But in Arabic, Ukrainian, etc.)*

---

## The Technology Behind It

```
┌─────────────────────────────────────────────┐
│  YOU (Ask in any language)                  │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  TRANSLATION LAYER                          │
│  Detects language → Converts to English     │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  KNOWLEDGE GRAPH (Neo4j Database)           │
│  - Stores verified EU/German laws           │
│  - Organizes laws like a connected web      │
│  - Searches by meaning, not just words      │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  AI BRAIN (Qwen 2.5 LLM)                    │
│  - Understands context                      │
│  - Writes in simple language                │
│  - Translates answer to your language       │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  ANSWER (In your language + sources)        │
└─────────────────────────────────────────────┘
```

### Tech Stack (Tools Used)

| Component | Tool | What It Does |
|-----------|------|--------------|
| **Chat Interface** | Chainlit | The window where you type and see answers |
| **AI Model** | Qwen 2.5 (7B) | The "brain" that understands and generates text |
| **Legal Database** | Neo4j | Stores laws as connected nodes (like a mind map) |
| **Search Engine** | nomic-embed-text | Converts words to math for smart searching |
| **Connector** | LangChain | Glues all the pieces together |
| **Location** | Your Computer | Runs 100% locally - no cloud, no data sharing |

---

## Key Safety Features

### 1. **Fact-Checking Built In**
- Every answer comes from the verified legal database
- The AI cannot "make up" laws because it only reads from the graph

### 2. **Source Transparency**
- Every answer shows which law article it came from
- You can verify the information independently

### 3. **Special Protections**
- Automatically includes safety rules when discussing vulnerable cases (minors, medical needs)
- Programmed to prioritize human rights articles

### 4. **Privacy Guaranteed**
- All processing happens on your machine
- No internet required after setup
- No conversation logs sent to companies

---

## What Makes This "Neuro-Symbolic"?

**Neuro** (Neural Networks = AI):
- Understands natural language in 25+ languages
- Translates between languages
- Writes human-friendly explanations

**Symbolic** (Logic-Based Rules):
- Legal hierarchy strictly coded (Dublin III supersedes national law)
- Graph database enforces relationships (Article → Exception → Condition)
- Boosters ensure critical laws are never missed

**Result:** The creativity of AI + the reliability of a legal database

---

## Installation & Setup

### Prerequisites
- Docker and Docker Compose
- Python 3.9+
- Ollama (for running the AI model locally)

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/migrantnav.git
cd migrantnav

# 2. Start the Neo4j database
docker-compose up -d

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Download the AI model
ollama pull qwen2.5:7b
ollama pull nomic-embed-text

# 5. Start the application
chainlit run app.py

# 6. Open your browser to http://localhost:8000
```

### First-Time Setup
- The system will automatically populate the legal database on first run
- This may take 5-10 minutes to process all legal documents
- You'll see a confirmation message when ready

---

## Usage

### Asking Questions
Simply type your question in any supported language:
- **Arabic**: "ما هي حقوقي كلاجئ؟"
- **English**: "What are my rights as a refugee?"
- **Farsi**: "حقوق من به عنوان پناهنده چیست؟"

### Supported Languages
Arabic, English, German, Farsi, Tigrinya, Ukrainian, Russian, French, Spanish, Somali, Turkish, Kurdish, Pashto, Urdu, Albanian, Serbian, Bosnian, Romanian, Bulgarian, Polish, and 5+ more

### Best Practices
- Ask specific questions (e.g., "Can I work while my asylum application is pending?")
- Mention your situation if relevant (e.g., "I am an unaccompanied minor")
- Request clarification if the answer is unclear

---

## Project Structure

```
migrantnav/
├── app.py                 # Main Chainlit application
├── requirements.txt       # Python dependencies
├── docker-compose.yml     # Neo4j database configuration
├── data/
│   ├── dublin_iii.json   # Dublin III Regulation
│   ├── charter.json      # EU Charter of Fundamental Rights
│   └── german_asylum.json # German asylum procedures
├── utils/
│   ├── retrievers.py     # Search and retrieval logic
│   ├── translation.py    # Language detection and translation
│   └── graph_setup.py    # Neo4j initialization
└── README.md
```

---

## Who Should Use This?

✅ **Asylum seekers** needing to understand their rights  
✅ **Legal aid volunteers** helping multiple clients  
✅ **Social workers** navigating complex cases  
✅ **Language barriers** - works in Arabic, Farsi, Ukrainian, Tigrinya, and 20+ more languages

---

## Troubleshooting

### Database Connection Issues
```bash
# Check if Neo4j is running
docker ps

# Restart the database
docker-compose restart
```

### AI Model Not Responding
```bash
# Verify Ollama is running
ollama list

# Restart Ollama service
ollama serve
```

### Translation Errors
- Check your internet connection (required for initial model downloads only)
- Verify the language is in the supported list

---

## Important Legal Disclaimer

⚠️ **This is an assistant, not a replacement for legal counsel.** 

MigrantNav provides information based on EU and German legal documents, but:
- Laws change frequently
- Individual cases have unique circumstances
- Official legal advice requires a qualified lawyer

**Always verify critical decisions with a certified legal professional.** Use MigrantNav to understand your options and prepare questions for legal consultations.

---

## Contributing

We welcome contributions! Areas where you can help:
- Adding legal documents from other EU countries
- Improving translations
- Testing with real users
- Enhancing the knowledge graph structure

See `CONTRIBUTING.md` for guidelines.

---

## Privacy & Security

- **Local Processing**: All data stays on your machine
- **No Cloud Dependencies**: Works completely offline after setup
- **No Tracking**: No analytics, cookies, or user monitoring
- **Open Source**: Audit the code yourself

---

## License

This project is licensed under the MIT License - see `LICENSE` file for details.

---

## Acknowledgments

- Legal documents sourced from official EU and German government publications
- Built with support from [Organization Name]
- Special thanks to the refugee support community

---

## Contact & Support

- **Issues**: Open a GitHub issue
- **Security Concerns**: security@migrantnav.org
- **General Inquiries**: info@migrantnav.org

---

*MigrantNav: Making legal rights accessible in every language* 🌍⚖️

**Version**: 1.0.0  
**Last Updated**: January 2026
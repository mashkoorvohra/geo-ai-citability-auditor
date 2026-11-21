# 🤖 GEO / AI Search Citability & Schema Auditor

**Live App:** [https://geo-ai-citability-auditor.streamlit.app/](https://geo-ai-citability-auditor.streamlit.app/)
> **Install as an AI Agent Skill (Claude Code / Cursor / MCP):** Get the packaged agent skill with automated `FAQPage` JSON-LD generation and live SERP checks on [Agensi](https://agensi.io/skills/geo-ai-citability-auditor).
> 
A Generative Engine Optimization (GEO) and Answer Engine Optimization (AEO) auditing tool that scores web pages and pre-publish content drafts for citation readiness across Google AI Overviews, ChatGPT, Perplexity, and Claude.

## Key Capabilities
- **100-Point GEO Citability Score:** Evaluates single-H1 hierarchy, `application/ld+json` entity schema coverage, question-formatted H2s, LLM-scannable lists/tables, and verifiable statistical citations.
- **Pre-Publish & Live URL Modes:** Audit any live public URL or paste raw HTML/article drafts prior to publishing.
- **AI Citability Upgrade Generator:** Optionally connects to Gemini, Claude, OpenAI, or Groq to generate verbatim 50-word AI Overview summary blocks, high-intent FAQs, and valid `FAQPage` JSON-LD snippets.

## Tech Stack
`Python` • `Streamlit` • `BeautifulSoup4` • `Requests` • `Pandas` • `LiteLLM`

## Run Locally
```bash
git clone [https://github.com/mashkoorvohra/geo-ai-citability-auditor.git](https://github.com/mashkoorvohra/geo-ai-citability-auditor.git)
cd geo-ai-citability-auditor
pip install -r requirements.txt
streamlit run app.py

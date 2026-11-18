import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
import re
import litellm

st.set_page_config(page_title="GEO & AI Search Citability Auditor", layout="wide")
st.title("🤖 GEO / AI Search Citability & Schema Auditor")
st.markdown("Audits **any live URL or pasted HTML/draft** for LLM & AI Overview citation readiness—runs **100% free locally** or with **any AI provider**.")

@st.cache_data(ttl=3600)
def fetch_live_models(provider_name: str, key: str) -> list:
    defaults = {
        "Google Gemini": ["gemini-4-hydrogen", "gemini-4-carbon", "gemini-4-argon", "gemini-3.5-flash-lite"],
        "Anthropic Claude": ["claude-sonnet-5-5", "claude-haiku-5-5", "claude-opus-5-5"],
        "OpenAI": ["gpt-6.2-astra", "gpt-6.2-sol", "gpt-6-luna", "gpt-5.4-mini"],
        "Groq / OpenRouter": ["groq/llama-3.3-70b-versatile", "openrouter/anthropic/claude-sonnet-5-5"]
    }
    if not key:
        return defaults.get(provider_name, [])
    try:
        if provider_name == "Google Gemini":
            r = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}", timeout=6)
            models = [m["name"].replace("models/", "") for m in r.json().get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
            newest = [m for m in models if any(v in m for v in ["gemini-4", "gemini-3.8", "gemini-3.5"])]
            return newest[::-1] if newest else defaults["Google Gemini"]
        elif provider_name == "Anthropic Claude":
            r = requests.get("https://api.anthropic.com/v1/models", headers={"x-api-key": key, "anthropic-version": "2023-06-01"}, timeout=6)
            models = [m["id"] for m in r.json().get("data", [])]
            return models if models else defaults["Anthropic Claude"]
        elif provider_name == "OpenAI":
            r = requests.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=6)
            models = [m["id"] for m in r.json().get("data", []) if any(v in m["id"] for v in ["gpt-6", "gpt-5", "o3"])]
            return sorted(models, reverse=True) if models else defaults["OpenAI"]
    except Exception:
        pass
    return defaults.get(provider_name, [])

# Sidebar Controls
st.sidebar.header("⚙️ AI Optimization Settings")
provider = st.sidebar.selectbox(
    "AI Optimization Engine (Optional)",
    ["Free Local Audit Only (0 API Credits)", "Google Gemini", "Anthropic Claude", "OpenAI", "Groq / OpenRouter"]
)

api_key = ""
selected_model = ""
if provider != "Free Local Audit Only (0 API Credits)":
    api_key = st.sidebar.text_input(f"Enter {provider} API Key", type="password")
    models = fetch_live_models(provider, api_key)
    if provider == "Groq / OpenRouter":
        selected_model = st.sidebar.text_input("Model ID", value=models[0])
    else:
        selected_model = st.sidebar.selectbox("Select Model (Auto-Updated)", models)
        prefix_map = {"Google Gemini": "gemini/", "Anthropic Claude": "anthropic/", "OpenAI": "openai/"}
        if not selected_model.startswith(prefix_map[provider]):
            selected_model = prefix_map[provider] + selected_model

# Flexible Input: Live URL or Pasted HTML/Text Draft
audit_mode = st.radio("Audit Source:", ["Live Public URL", "Paste Raw HTML or Article Draft (Pre-Publish Check)"], horizontal=True)

target_url = ""
raw_html_input = ""
if audit_mode == "Live Public URL":
    target_url = st.text_input("Enter Any Public URL to Audit:", value="https://en.wikipedia.org/wiki/Search_engine_optimization")
else:
    raw_html_input = st.text_area(
        "Paste HTML Source or Draft Content:",
        value="<h1>What Is Generative Engine Optimization (GEO)?</h1><p>Generative Engine Optimization (GEO) increases brand citation frequency inside AI search answers by 40% using structured JSON-LD entities and direct-answer summary blocks.</p><h2>How Does GEO Differ From Traditional SEO?</h2><ul><li>Optimizes for LLM retrieval and synthesis</li><li>Prioritizes statistical citations and entity clarity</li></ul>",
        height=160
    )

def analyze_html(html_content: str) -> dict:
    soup = BeautifulSoup(html_content, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else "Not Set (Draft/Fragment)"
    h1s = [h.get_text(" ", strip=True) for h in soup.find_all("h1")]
    h2s = [h.get_text(" ", strip=True) for h in soup.find_all("h2")]
    question_h2s = [h for h in h2s if "?" in h or h.lower().startswith(("what", "how", "why", "when", "which"))]

    schema_types = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if "@graph" in item:
                    schema_types.extend([g.get("@type", "Unknown") for g in item["@graph"]])
                elif "@type" in item:
                    schema_types.append(item["@type"])
        except Exception:
            continue

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 30]
    full_text = " ".join(paragraphs) if paragraphs else soup.get_text(" ", strip=True)
    word_count = len(full_text.split())
    lists_tables = len(soup.find_all(["ul", "ol", "table"]))
    stats_mentions = len(re.findall(r"\b\d+(\.\d+)?%|\₹[\d,]+|\$[\d,]+|\b202[4-6]\b", full_text))

    score = 0
    score += 20 if len(h1s) == 1 else 5
    score += 20 if len(schema_types) > 0 else 0
    score += 20 if len(question_h2s) >= 2 else (10 if len(question_h2s) == 1 else 0)
    score += 20 if lists_tables >= 2 else (10 if lists_tables == 1 else 0)
    score += 20 if stats_mentions >= 3 else (10 if stats_mentions >= 1 else 0)

    return {
        "title": title,
        "h1s": h1s,
        "h2s": h2s,
        "question_h2s": question_h2s,
        "schema_types": list(set(str(s) for s in schema_types)),
        "word_count": word_count,
        "lists_tables": lists_tables,
        "stats_mentions": stats_mentions,
        "score": score,
        "sample_text": full_text[:2500]
    }

if st.button("Run GEO Citability Audit", type="primary"):
    try:
        with st.spinner("Auditing structure, entities, and AI citability..."):
            if audit_mode == "Live Public URL":
                if not target_url.startswith("http"):
                    st.warning("Please enter a valid URL starting with http:// or https://")
                    st.stop()
                resp = requests.get(target_url, headers={"User-Agent": "Mozilla/5.0 (compatible; GEOAuditBot/1.0)"}, timeout=12)
                resp.raise_for_status()
                res = analyze_html(resp.text)
            else:
                if not raw_html_input.strip():
                    st.warning("Please paste HTML or draft content to audit.")
                    st.stop()
                res = analyze_html(raw_html_input)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("GEO Citability Score", f"{res['score']} / 100")
        c2.metric("JSON-LD Schemas", len(res["schema_types"]))
        c3.metric("Question-Based H2s", len(res["question_h2s"]))
        c4.metric("Data / Stat Citations", res["stats_mentions"])

        audit_rows = [
            {"Signal": "Page Title", "Detected Value": res["title"], "Status": "✅ Present" if "Not Set" not in res["title"] else "⚠️ Missing"},
            {"Signal": "H1 Structure", "Detected Value": ", ".join(res["h1s"]) or "None", "Status": "✅ Single H1" if len(res["h1s"]) == 1 else "⚠️ Needs Single H1"},
            {"Signal": "JSON-LD Entities", "Detected Value": ", ".join(res["schema_types"]) or "None detected", "Status": "✅ Rich Schema" if res["schema_types"] else "❌ Add JSON-LD"},
            {"Signal": "LLM-Scannable Lists/Tables", "Detected Value": f"{res['lists_tables']} elements", "Status": "✅ Structured" if res["lists_tables"] >= 2 else "⚠️ Add Lists/Tables"},
            {"Signal": "Content Depth", "Detected Value": f"{res['word_count']} words", "Status": "✅ Deep" if res["word_count"] >= 400 else "⚠️ Expand Depth"},
        ]
        st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)

        if provider == "Free Local Audit Only (0 API Credits)":
            st.info("💡 **Free Local Action Items:** Add a 45-word direct-answer summary paragraph right below your H1, convert key subheadings into question-format H2s, and embed `FAQPage` + `Article` JSON-LD schema. Select an AI provider in the sidebar to auto-generate those snippets.")
        elif not api_key:
            st.warning(f"Paste your {provider} API key in the sidebar to auto-generate an AI-ready summary block and JSON-LD schema.")
        else:
            with st.spinner(f"Generating GEO upgrade package via {selected_model}..."):
                prompt = f"""
                You are a Principal GEO & Technical SEO Architect. Based on this page audit, generate:
                1. A 50-word 'Direct Answer Summary Block' designed to be quoted verbatim by AI Overviews, ChatGPT, and Perplexity.
                2. Two high-intent FAQ questions and concise answers.
                3. A valid `<script type="application/ld+json">` FAQPage schema snippet.

                Title: {res['title']}
                Existing H2s: {res['h2s'][:8]}
                Content Excerpt: {res['sample_text']}
                """
                ai_resp = litellm.completion(model=selected_model, messages=[{"role": "user", "content": prompt}], api_key=api_key)
                st.subheader("✨ AI Citability Upgrade & JSON-LD Generator")
                st.markdown(ai_resp.choices[0].message.content)
    except Exception as e:
        st.error(f"Audit Error: {e}")

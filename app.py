import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
import re
import litellm

st.set_page_config(page_title="GEO & AI Search Citability Auditor", layout="wide")
st.title("🤖 GEO / AI Search Citability & Schema Auditor")
st.markdown("Evaluates live web pages for **LLM & AI Overview citation readiness**—checking structured data, direct-answer formatting, and entity clarity.")

# Sidebar: Optional Multi-Provider AI Rewrite
st.sidebar.header("⚙️ AI Optimization Settings")
provider = st.sidebar.selectbox(
    "AI Provider (Optional for Rewrite)",
    [
        "Free Local Audit Only (0 API Credits)",
        "Anthropic Claude (claude-haiku-4-5-20251001)",
        "Google Gemini (gemini-2.5-flash-lite)",
        "OpenAI (gpt-4o-mini)",
        "Groq / OpenRouter (Custom Model)"
    ]
)

api_key = ""
model_name = ""
if provider != "Free Local Audit Only (0 API Credits)":
    api_key = st.sidebar.text_input("Provider API Key", type="password")
    if "Claude" in provider:
        model_name = "anthropic/claude-haiku-4-5-20251001"
    elif "Gemini" in provider:
        model_name = "gemini/gemini-2.5-flash-lite"
    elif "OpenAI" in provider:
        model_name = "openai/gpt-4o-mini"
    else:
        model_name = st.sidebar.text_input("LiteLLM Model String", value="groq/llama-3.3-70b-versatile")

target_url = st.text_input("Enter Live URL to Audit", value="https://artscapedevelopers.com/")

def audit_page(url: str) -> dict:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; GEOAuditBot/1.0)"}
    resp = requests.get(url, headers=headers, timeout=12)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Extract Title & Meta
    title = soup.title.string.strip() if soup.title and soup.title.string else "Missing"
    meta_desc_tag = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    meta_desc = meta_desc_tag["content"].strip() if meta_desc_tag and meta_desc_tag.get("content") else "Missing"

    # Extract Headings
    h1s = [h.get_text(" ", strip=True) for h in soup.find_all("h1")]
    h2s = [h.get_text(" ", strip=True) for h in soup.find_all("h2")]
    question_h2s = [h for h in h2s if "?" in h or h.lower().startswith(("what", "how", "why", "when", "which"))]

    # Extract JSON-LD Schema Types
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

    # Extract Clean Body Text & Statistics/Lists
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 40]
    word_count = sum(len(p.split()) for p in paragraphs)
    lists_count = len(soup.find_all(["ul", "ol"]))
    tables_count = len(soup.find_all("table"))
    stats_mentions = len(re.findall(r"\b\d+(\.\d+)?%|\₹[\d,]+|\$[\d,]+|\b202[4-6]\b", " ".join(paragraphs)))

    # Calculate GEO Readiness Score (0-100)
    score = 0
    score += 20 if len(h1s) == 1 else 5
    score += 20 if len(schema_types) > 0 else 0
    score += 20 if len(question_h2s) >= 2 else (10 if len(question_h2s) == 1 else 0)
    score += 20 if (lists_count + tables_count) >= 2 else 5
    score += 20 if stats_mentions >= 3 else (10 if stats_mentions >= 1 else 0)

    return {
        "status": resp.status_code,
        "title": title,
        "meta_desc": meta_desc,
        "h1s": h1s,
        "h2s": h2s,
        "question_h2s": question_h2s,
        "schema_types": list(set(str(s) for s in schema_types)),
        "word_count": word_count,
        "lists_tables": lists_count + tables_count,
        "stats_mentions": stats_mentions,
        "score": score,
        "sample_text": " ".join(paragraphs[:6])[:2500]
    }

if st.button("Run GEO Citability Audit", type="primary"):
    if not target_url.startswith("http"):
        st.warning("Please enter a valid URL starting with http:// or https://")
        st.stop()

    try:
        with st.spinner("Crawling DOM, parsing JSON-LD schema, and scoring AI citability..."):
            res = audit_page(target_url)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("GEO Citability Score", f"{res['score']} / 100")
        c2.metric("JSON-LD Schemas", len(res["schema_types"]))
        c3.metric("Question-Based H2s", len(res["question_h2s"]))
        c4.metric("Data / Stat Citations", res["stats_mentions"])

        st.subheader("📋 Technical & Structural Breakdown")
        audit_rows = [
            {"Signal": "Page Title", "Value": res["title"], "Status": "✅ Present" if res["title"] != "Missing" else "❌ Missing"},
            {"Signal": "H1 Structure", "Value": ", ".join(res["h1s"]) or "None", "Status": "✅ Single H1" if len(res["h1s"]) == 1 else "⚠️ Check H1 Count"},
            {"Signal": "JSON-LD Entities", "Value": ", ".join(res["schema_types"]) or "None detected", "Status": "✅ Rich Schema" if res["schema_types"] else "❌ No JSON-LD"},
            {"Signal": "Structured Lists/Tables", "Value": f"{res['lists_tables']} elements", "Status": "✅ LLM-Scannable" if res["lists_tables"] >= 2 else "⚠️ Add Bullets/Tables"},
            {"Signal": "Body Word Count", "Value": f"{res['word_count']} words", "Status": "✅ Sufficient Depth" if res["word_count"] >= 400 else "⚠️ Thin Content"},
        ]
        st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)

        if provider != "Free Local Audit Only (0 API Credits)":
            if not api_key:
                st.warning("Enter your API key in the sidebar to generate an AI-optimized FAQ & JSON-LD snippet.")
            else:
                with st.spinner(f"Generating GEO optimization recommendations via {model_name}..."):
                    prompt = f"""
                    You are a Principal Technical & GEO SEO Architect. Audit this page excerpt and provide:
                    1. A 50-word 'Direct Answer Summary Block' optimized to be quoted verbatim by ChatGPT, Perplexity, and Google AI Overviews.
                    2. Two missing FAQ questions based on the topic.
                    3. A valid JSON-LD FAQPage or Organization schema snippet tailored to the page.

                    URL: {target_url}
                    Title: {res['title']}
                    Existing H2s: {res['h2s'][:8]}
                    Excerpt: {res['sample_text']}
                    """
                    ai_resp = litellm.completion(
                        model=model_name,
                        messages=[{"role": "user", "content": prompt}],
                        api_key=api_key
                    )
                    st.subheader("✨ AI Citability Upgrade & JSON-LD Generator")
                    st.markdown(ai_resp.choices[0].message.content)

    except Exception as e:
        st.error(f"Could not audit URL: {e}")

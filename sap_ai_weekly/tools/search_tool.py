from smolagents import tool, DuckDuckGoSearchTool
import time

# Use smolagents' built-in DDG tool which handles auth/rate limits internally
_ddg = DuckDuckGoSearchTool()


def _safe_search(query: str) -> str:
    """Run a single DDG search with retry on rate limit."""
    for attempt in range(3):
        try:
            result = _ddg(query)
            if result and len(result.strip()) > 50:
                return result
            time.sleep(2)
        except Exception as e:
            print(f"[search attempt {attempt + 1}] '{query}' failed: {e}")
            time.sleep(3 * (attempt + 1))
    return ""


@tool
def search_latest_ai_news(max_results: int = 5) -> str:
    """
    Fetches the latest AI technology news across models, agents,
    multimodal AI, enterprise automation, and AI in analytics.
    Args:
        max_results: Number of results per query (default 5)
    """
    queries = [
        "agentic AI autonomous enterprise workflows 2025",
        "generative AI supply chain HR finance automation 2025",
        "LLM RAG enterprise document processing 2025",
        "AI forecasting procurement risk management 2025",
        "AI HR talent management automation 2025",
        "AI financial close anomaly detection 2025",
        "multimodal AI document processing enterprise 2025",
    ]

    all_results = []
    for query in queries:
        result = _safe_search(query)
        if result:
            all_results.append(f"[AI NEWS — {query}]\n{result}")
        time.sleep(1)  # gentle rate limiting

    if not all_results:
        return "AI search returned no results. Proceeding with SAP-grounded content."

    print(f"[search_tool] AI news fetched: {len(all_results)} query results")
    return "\n\n---\n\n".join(all_results)


@tool
def search_latest_sap_news(max_results: int = 5) -> str:
    """
    Fetches latest SAP news across ALL SAP applications:
    S/4HANA, BTP, Datasphere, SuccessFactors, Ariba, IBP,
    EWM, TM, GRC, MDG, CX, Joule, SAC.
    Args:
        max_results: Number of results per query (default 5)
    """
    queries = [
        "SAP S4HANA Joule AI embedded features 2025",
        "SAP SuccessFactors AI talent acquisition workforce 2025",
        "SAP Ariba AI procurement supplier risk 2025",
        "SAP IBP AI supply chain planning optimization 2025",
        "SAP EWM TM AI warehouse transport automation 2025",
        "SAP GRC AI risk compliance automation 2025",
        "SAP MDG master data AI governance 2025",
        "SAP CX AI customer experience personalization 2025",
        "SAP BTP AI Core Datasphere enterprise integration 2025",
        "SAP Analytics Cloud AI smart predict 2025",
    ]

    all_results = []
    for query in queries:
        result = _safe_search(query)
        if result:
            all_results.append(f"[SAP NEWS — {query}]\n{result}")
        time.sleep(1)

    if not all_results:
        return "SAP search returned no results. Proceeding with known SAP AI roadmap content."

    print(f"[search_tool] SAP news fetched: {len(all_results)} query results")
    return "\n\n---\n\n".join(all_results)

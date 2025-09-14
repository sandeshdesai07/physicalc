# requires: requests
import requests
from urllib.parse import quote_plus

def find_source_via_crossref(query: str, rows=3):
    """
    Query CrossRef works API for given query (title/description).
    Returns the best result as a dict: {'title', 'doi', 'url'} or None.
    """
    try:
        safe_q = quote_plus(query)
        url = f"https://api.crossref.org/works?query.title={safe_q}&rows={rows}"
        r = requests.get(url, timeout=6)
        if r.status_code != 200:
            return None
        data = r.json().get("message", {}).get("items", [])
        if not data:
            # fallback: generic query param
            url2 = f"https://api.crossref.org/works?query={safe_q}&rows={rows}"
            r2 = requests.get(url2, timeout=6)
            if r2.status_code != 200:
                return None
            data = r2.json().get("message", {}).get("items", [])
        if not data:
            return None
        # pick best (first) item
        it = data[0]
        title = " ".join(it.get("title", [])) if it.get("title") else None
        doi = it.get("DOI")
        link = None
        # choose a URL if available (URL field or DOI link)
        if "URL" in it and it["URL"]:
            link = it["URL"]
        elif doi:
            link = f"https://doi.org/{doi}"
        return {"title": title, "doi": doi, "url": link}
    except Exception as e:
        print("CrossRef lookup error:", e)
        return None

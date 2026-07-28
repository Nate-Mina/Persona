"""Lightweight web search used by Sabrina for true-crime / psychology / medical facts."""

def web_search(query: str, n: int = 5) -> str:
    try:
        from ddgs import DDGS
        import concurrent.futures as _cf
        with _cf.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(lambda: DDGS().text(query, max_results=n))
            results = fut.result(timeout=12)  # never hang the engine
        lines = []
        for r in results:
            title = r.get("title", "").strip()
            body = r.get("body", "").strip()
            href = r.get("href", "").strip()
            if title or body:
                lines.append(f"- {title}: {body} ({href})")
        return "\n".join(lines) if lines else "No results found."
    except Exception as e:  # network down, blocked, etc.
        return f"Search unavailable: {e}"


if __name__ == "__main__":
    print(web_search("least known serial killers obscure cases"))

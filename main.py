import html
import os
import re
import time
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import urlencode

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

WOLFRAM_APP_ID = os.getenv("WOLFRAM_APP_ID", "LR29UEPJY6")
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "")
ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",") if origin.strip()]
REQUEST_TIMEOUT = (5, 10)
ARXIV_API_URL = "https://export.arxiv.org/api/query"
CROSSREF_API_URL = "https://api.crossref.org/works"
WOLFRAM_API_URL = "https://api.wolframalpha.com/v1/result"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
ARXIV_DOMAIN_FILTER = os.getenv("ARXIV_DOMAIN_FILTER", "electrical engineering")

RESEARCH_KEYWORDS = {
    "paper",
    "papers",
    "article",
    "articles",
    "research",
    "recherche",
    "study",
    "studies",
    "publication",
    "publications",
    "journal",
    "journals",
    "state of the art",
    "latest",
    "find",
    "search",
    "arxiv",
    "doi",
    "survey",
    "literature",
    "review",
}
DIRECT_QUERY_HINTS = {
    "bonjour",
    "salut",
    "hello",
    "hi",
    "merci",
    "thanks",
    "help",
    "aide",
    "who are you",
    "que fais-tu",
    "que peux-tu faire",
}
CALCULATION_HINTS = {
    "solve",
    "calculate",
    "calcule",
    "calcul",
    "equation",
    "formula",
    "derive",
    "derivative",
    "integral",
    "differentiate",
    "simplify",
    "factor",
    "matrix",
    "determinant",
    "voltage drop",
    "loi d'ohm",
    "ohm",
    "power factor",
}
ELECTRICAL_HINTS = {
    "electrical engineering",
    "electrotechnique",
    "power system",
    "power systems",
    "power electronics",
    "substation",
    "voltage",
    "current",
    "three phase",
    "three-phase",
    "circuit breaker",
    "transmission line",
    "generator",
    "relay protection",
}
ELECTRICAL_RESULT_HINTS = {
    "electrical",
    "electricity",
    "power",
    "power system",
    "power electronics",
    "voltage",
    "current",
    "transformer",
    "distribution",
    "loss",
    "losses",
    "generator",
    "motor",
    "grid",
    "substation",
    "photovoltaic",
    "converter",
    "inverter",
    "load",
    "transmission",
}
AI_RESULT_HINTS = {
    "software engineering",
    "computer vision",
    "vision transformer",
    "generative ai",
    "large language model",
    "llm",
    "face clustering",
    "requirements engineering",
    "machine learning",
    "deep learning",
    "image classification",
    "attention mechanism",
    "language model",
    "neural network",
}
RESEARCH_PREFIX_PATTERNS = [
    r"^(find|search|look for|get|show me|give me)\s+(papers?|articles?|research|studies|publications?|journals?)\s+(about|on|for)\s+",
    r"^(find|search|look for|get|show me|give me)\s+",
    r"^(research|recherche)\s+",
    r"^(papers?|articles?|research|studies|publications?|journals?)\s+(about|on|for)\s+",
    r"^(what are)\s+(the\s+)?(latest\s+)?(papers?|articles?|studies?)\s+(about|on|for)\s+",
]
QUERY_STOPWORDS = {
    "find",
    "search",
    "look",
    "for",
    "get",
    "show",
    "me",
    "give",
    "papers",
    "paper",
    "articles",
    "article",
    "research",
    "studies",
    "study",
    "publications",
    "publication",
    "about",
    "on",
    "the",
    "latest",
    "electrical",
    "engineering",
}

base_user_agent = "python-electrotechnique-api/1.5"
USER_AGENT = f"{base_user_agent} (mailto:{CONTACT_EMAIL})" if CONTACT_EMAIL else base_user_agent


class HomeResponse(BaseModel):
    status: str
    message: str
    available_endpoints: list[str]


class HealthResponse(BaseModel):
    status: str


class WolframResponse(BaseModel):
    status: str
    source: str
    question: str
    result: str


class PaperResult(BaseModel):
    title: str
    summary: str = ""
    published: str = ""
    link: str = ""
    pdf_url: str = ""
    primary_category: str = ""
    authors: list[str] = Field(default_factory=list)
    doi: str = ""
    journal: str = ""
    provider: str = "arxiv"


class ArxivResponse(BaseModel):
    status: str
    source: str
    provider: str
    query: str
    effective_query: str
    domain_filter_applied: bool
    count: int
    results: list[PaperResult] = Field(default_factory=list)
    warning: str | None = None


class ResearchResponse(BaseModel):
    status: str
    query: str
    sources: dict[str, Any] = Field(default_factory=dict)
    errors: dict[str, str] = Field(default_factory=dict)


class SmartQueryResponse(BaseModel):
    status: str
    mode: str
    route: str
    input: str
    query: str
    normalized_input: str
    normalized_query: str
    reason: str
    executed: bool
    redirect: str | None = None
    response: str | None = None
    data: dict[str, Any] | None = None
    answer: str | None = None
    external_result: dict[str, Any] | None = None
    error: str | None = None


class GptToolResult(BaseModel):
    title: str = ""
    snippet: str = ""
    link: str = ""
    published: str = ""
    authors: list[str] = Field(default_factory=list)
    provider: str = ""


class GptToolResponse(BaseModel):
    status: str
    tool: str
    mode: str
    input: str
    query_used: str
    executed: bool
    source: str
    redirect: str
    answer: str
    results: list[GptToolResult] = Field(default_factory=list)
    error: str = ""


app = FastAPI(
    title="Python Electrotechnique API",
    description="API FastAPI pour enrichir un assistant GPT avec WolframAlpha et arXiv.",
    version="1.5.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session = requests.Session()
session.headers.update(
    {
        "User-Agent": USER_AGENT,
        "Accept": "application/atom+xml, application/xml, text/xml, application/json;q=0.9, */*;q=0.8",
    }
)


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.split())


def _strip_html_tags(value: str | None) -> str:
    if not value:
        return ""
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return _normalize_text(html.unescape(without_tags))


def _get_text_param(value: object) -> str | None:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return None


def _get_int_param(value: object, default: int) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else default


def _get_bool_param(value: object, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _contains_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _is_math_expression(query: str) -> bool:
    compact = query.replace(" ", "")
    return bool(re.search(r"\d", query) and re.search(r"[\+\-\*/\^=()]", compact))


def _clean_research_query(query: str) -> str:
    cleaned_query = _normalize_text(query)
    for pattern in RESEARCH_PREFIX_PATTERNS:
        cleaned_query = re.sub(pattern, "", cleaned_query, flags=re.IGNORECASE)
    return _normalize_text(cleaned_query) or _normalize_text(query)


def _extract_query_keywords(query: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", query.lower())
    return [token for token in tokens if token not in QUERY_STOPWORDS and len(token) > 2]


def _score_result_relevance(result: dict[str, Any], query_keywords: list[str]) -> tuple[int, int]:
    searchable_text = " ".join(
        [
            result.get("title", ""),
            result.get("summary", ""),
            result.get("primary_category", ""),
            result.get("journal", ""),
        ]
    ).lower()
    token_hits = sum(1 for token in query_keywords if token in searchable_text)
    token_score = token_hits * 3
    electrical_score = sum(1 for hint in ELECTRICAL_RESULT_HINTS if hint in searchable_text)
    ai_penalty = sum(2 for hint in AI_RESULT_HINTS if hint in searchable_text)
    return token_hits, token_score + electrical_score - ai_penalty


def _filter_ranked_results(results: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    query_keywords = _extract_query_keywords(query)
    scored_results = []

    for result in results:
        token_hits, score = _score_result_relevance(result, query_keywords)
        if query_keywords and token_hits == 0:
            continue
        scored_results.append((score, result))

    scored_results.sort(key=lambda item: item[0], reverse=True)
    positive_results = [result for score, result in scored_results if score > 0]
    return positive_results if positive_results else []


def _apply_arxiv_domain_filter(query: str, auto_filter: bool) -> tuple[str, bool]:
    normalized_query = _clean_research_query(query)
    if not auto_filter or not normalized_query:
        return normalized_query, False

    lowered_query = normalized_query.lower()
    if _contains_any(lowered_query, ELECTRICAL_HINTS):
        return normalized_query, False

    return f"{normalized_query} {ARXIV_DOMAIN_FILTER}", True


def _decide_smart_route(query: str) -> tuple[str, str]:
    lowered_query = query.lower()

    if _is_math_expression(query) or _contains_any(lowered_query, CALCULATION_HINTS):
        return "wolfram", "Question detectee comme calcul, formule ou evaluation mathematique."

    if _contains_any(lowered_query, RESEARCH_KEYWORDS):
        return "arxiv", "Question detectee comme recherche bibliographique ou demande d'articles."

    if _contains_any(lowered_query, DIRECT_QUERY_HINTS):
        return "direct", "Question simple detectee: une reponse directe du GPT suffit."

    if len(query.split()) >= 6:
        return "arxiv", "Question longue interpretee comme sujet de recherche a documenter."

    return "direct", "Question simple detectee: aucun appel externe n'est necessaire."


def _format_date_parts(parts: list[int]) -> str:
    if not parts:
        return ""

    formatted = []
    for index, part in enumerate(parts):
        if index == 0:
            formatted.append(str(part))
        else:
            formatted.append(f"{part:02d}")
    return "-".join(formatted)


def _extract_pdf_link(entry: ET.Element, namespaces: dict[str, str]) -> str:
    for link in entry.findall("atom:link", namespaces):
        if link.attrib.get("title") == "pdf":
            return link.attrib.get("href", "")
    return ""


def _request_with_retry(url: str, params: dict[str, Any], retries: int = 2) -> requests.Response:
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if response.status_code in RETRYABLE_STATUS_CODES:
                if attempt < retries:
                    time.sleep(attempt)
                    continue
                response.raise_for_status()
            response.raise_for_status()
            return response
        except requests.Timeout as exc:
            last_error = exc
        except requests.RequestException as exc:
            last_error = exc
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code not in RETRYABLE_STATUS_CODES or attempt >= retries:
                break

        if attempt < retries:
            time.sleep(attempt)

    if last_error is None:
        raise RuntimeError("La requete a echoue sans erreur explicite.")
    raise last_error


def _build_redirect_path(mode: str, query: str, max_results: int, auto_filter: bool) -> str | None:
    if mode == "wolfram":
        return f"/wolfram?{urlencode({'input': query})}"

    if mode == "arxiv":
        return f"/arxiv?{urlencode({'query': query, 'max_results': max_results, 'sort_by': 'relevance', 'auto_filter': str(auto_filter).lower()})}"

    return None


def _build_arxiv_brief(payload: dict[str, Any]) -> str:
    provider = payload.get("provider", "arxiv")
    results = payload.get("results", [])
    if not results:
        return "Aucun article pertinent n'a ete trouve."

    top_titles = [item.get("title", "") for item in results[:3] if item.get("title")]
    titles_text = " ; ".join(top_titles)
    count = payload.get("count", len(results))
    warning = payload.get("warning")

    brief = f"{count} resultats trouves via {provider}. Principaux titres: {titles_text}."
    if warning:
        brief = f"{brief} Note: {warning}"
    return brief


def _build_direct_response(query: str) -> str:
    return (
        f"Aucune API externe n'est necessaire pour cette question: '{query}'. "
        "Le GPT peut repondre directement. Pour declencher une recherche scientifique, utilise des mots comme "
        "'paper', 'research' ou 'article'. Pour un calcul, utilise 'calculate', 'solve' ou une expression mathematique."
    )


def _build_smart_payload(
    *,
    status: str,
    mode: str,
    raw_query: str,
    normalized_query: str,
    reason: str,
    max_results: int,
    auto_filter: bool,
    executed: bool,
    response: str | None = None,
    data: dict[str, Any] | None = None,
    answer: str | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    redirect = _build_redirect_path(mode, normalized_query, max_results, auto_filter)
    return SmartQueryResponse(
        status=status,
        mode=mode,
        route="direct" if mode == "basic" else mode,
        input=raw_query,
        query=raw_query,
        normalized_input=normalized_query,
        normalized_query=normalized_query,
        reason=reason,
        executed=executed,
        redirect=redirect,
        response=response,
        data=data,
        answer=answer,
        external_result=data,
        error=error,
    ).model_dump(exclude_none=True)


def _build_gpt_tool_results(mode: str, data: dict[str, Any], fallback_answer: str) -> list[dict[str, Any]]:
    if mode == "arxiv":
        return [
            GptToolResult(
                title=item.get("title", ""),
                snippet=item.get("summary", ""),
                link=item.get("link", ""),
                published=item.get("published", ""),
                authors=item.get("authors", []),
                provider=item.get("provider", data.get("provider", "arxiv")),
            ).model_dump()
            for item in data.get("results", [])
        ]

    if mode == "wolfram":
        return [
            GptToolResult(
                title="WolframAlpha Result",
                snippet=data.get("result", fallback_answer),
                link="",
                published="",
                authors=[],
                provider=data.get("source", "wolframalpha"),
            ).model_dump()
        ]

    return []


def _to_gpt_tool_response(smart_payload: dict[str, Any]) -> dict[str, Any]:
    mode = smart_payload.get("mode", "basic")
    data = smart_payload.get("data") or smart_payload.get("external_result") or {}
    answer = smart_payload.get("response") or smart_payload.get("answer") or ""
    error = smart_payload.get("error") or ""

    if mode == "arxiv":
        source = data.get("provider") or data.get("source") or "arxiv"
        query_used = data.get("effective_query") or smart_payload.get("normalized_input") or smart_payload.get("input", "")
    elif mode == "wolfram":
        source = data.get("source", "wolframalpha")
        query_used = smart_payload.get("normalized_input") or smart_payload.get("input", "")
    else:
        source = "direct"
        query_used = smart_payload.get("normalized_input") or smart_payload.get("input", "")

    return GptToolResponse(
        status=smart_payload.get("status", "ok"),
        tool="gpt-tool",
        mode=mode,
        input=smart_payload.get("input", ""),
        query_used=query_used,
        executed=bool(smart_payload.get("executed", False)),
        source=source,
        redirect=smart_payload.get("redirect") or "",
        answer=answer,
        results=[GptToolResult(**item) for item in _build_gpt_tool_results(mode, data, answer)],
        error=error,
    ).model_dump()


def _fetch_wolfram_result(query: str) -> dict[str, Any]:
    if not WOLFRAM_APP_ID:
        raise HTTPException(
            status_code=500,
            detail="La variable d'environnement WOLFRAM_APP_ID est manquante.",
        )

    try:
        response = _request_with_retry(
            WOLFRAM_API_URL,
            params={"i": query, "appid": WOLFRAM_APP_ID},
        )
    except requests.Timeout as exc:
        raise HTTPException(
            status_code=504,
            detail="WolframAlpha a mis trop de temps a repondre.",
        ) from exc
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Echec de la requete WolframAlpha: {exc}",
        ) from exc

    result = _normalize_text(response.text)
    if not result:
        raise HTTPException(
            status_code=502,
            detail="WolframAlpha a renvoye une reponse vide.",
        )

    if "did not understand your input" in result.lower():
        raise HTTPException(
            status_code=404,
            detail=f"WolframAlpha n'a pas compris la requete: {query}",
        )

    return WolframResponse(
        status="ok",
        source="wolframalpha",
        question=query,
        result=result,
    ).model_dump()


def _build_arxiv_response(
    query: str,
    effective_query: str,
    domain_filter_applied: bool,
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    return ArxivResponse(
        status="ok",
        source="arxiv",
        provider="arxiv",
        query=query,
        effective_query=effective_query,
        domain_filter_applied=domain_filter_applied,
        count=len(results),
        results=[PaperResult(**result) for result in results],
    ).model_dump(exclude_none=True)


def _fetch_crossref_results(
    query: str,
    effective_query: str,
    domain_filter_applied: bool,
    max_results: int,
    reason: str,
) -> dict[str, Any]:
    params = {
        "query": effective_query,
        "rows": max_results,
    }

    try:
        response = _request_with_retry(CROSSREF_API_URL, params=params, retries=2)
        payload = response.json()
    except requests.Timeout as exc:
        raise HTTPException(
            status_code=504,
            detail=f"arXiv indisponible, puis Crossref a mis trop de temps a repondre. Cause initiale: {reason}",
        ) from exc
    except (requests.RequestException, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"arXiv indisponible et le fallback Crossref a echoue. Cause initiale: {reason}. Cause fallback: {exc}",
        ) from exc

    items = payload.get("message", {}).get("items", [])
    results = []

    for item in items:
        authors = []
        for author in item.get("author", []):
            author_name = " ".join(part for part in [author.get("given", ""), author.get("family", "")] if part).strip()
            if author_name:
                authors.append(author_name)

        date_parts = item.get("issued", {}).get("date-parts", [[]])
        published = _format_date_parts(date_parts[0] if date_parts else [])
        titles = item.get("title", [])
        journals = item.get("container-title", [])

        results.append(
            PaperResult(
                title=_normalize_text(titles[0] if titles else ""),
                summary=_strip_html_tags(item.get("abstract")),
                published=published,
                link=_normalize_text(item.get("URL", "")),
                pdf_url="",
                primary_category="fallback-crossref",
                authors=authors,
                doi=_normalize_text(item.get("DOI", "")),
                journal=_normalize_text(journals[0] if journals else ""),
                provider="crossref",
            ).model_dump()
        )

    filtered_results = _filter_ranked_results(results, effective_query)
    if filtered_results:
        results = filtered_results[:max_results]

    return ArxivResponse(
        status="degraded",
        source="arxiv",
        provider="crossref",
        query=query,
        effective_query=effective_query,
        domain_filter_applied=domain_filter_applied,
        count=len(results),
        results=[PaperResult(**result) for result in results],
        warning=f"arXiv est temporairement indisponible ou limite. Resultats fournis via Crossref. Detail: {reason}",
    ).model_dump(exclude_none=True)


def _fetch_arxiv_results(query: str, max_results: int, sort_by: str, auto_filter: bool = True) -> dict[str, Any]:
    effective_query, domain_filter_applied = _apply_arxiv_domain_filter(query, auto_filter)
    params = {
        "search_query": f"all:{effective_query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": sort_by,
        "sortOrder": "descending",
    }

    try:
        response = _request_with_retry(ARXIV_API_URL, params=params, retries=2)
        root = ET.fromstring(response.text)
    except requests.Timeout as exc:
        return _fetch_crossref_results(query, effective_query, domain_filter_applied, max_results, f"timeout arXiv: {exc}")
    except requests.RequestException as exc:
        return _fetch_crossref_results(query, effective_query, domain_filter_applied, max_results, f"requete arXiv: {exc}")
    except ET.ParseError as exc:
        return _fetch_crossref_results(query, effective_query, domain_filter_applied, max_results, f"XML arXiv invalide: {exc}")

    namespaces = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }

    results = []
    for entry in root.findall("atom:entry", namespaces):
        authors = []
        for author in entry.findall("atom:author", namespaces):
            name = author.find("atom:name", namespaces)
            if name is not None and name.text:
                authors.append(_normalize_text(name.text))

        title = entry.find("atom:title", namespaces)
        summary = entry.find("atom:summary", namespaces)
        published = entry.find("atom:published", namespaces)
        link = entry.find("atom:id", namespaces)
        primary_category = entry.find("arxiv:primary_category", namespaces)

        results.append(
            PaperResult(
                title=_normalize_text(title.text if title is not None else ""),
                summary=_normalize_text(summary.text if summary is not None else ""),
                published=_normalize_text(published.text if published is not None else ""),
                link=_normalize_text(link.text if link is not None else ""),
                pdf_url=_extract_pdf_link(entry, namespaces),
                primary_category=primary_category.attrib.get("term", "") if primary_category is not None else "",
                authors=authors,
                provider="arxiv",
            ).model_dump()
        )

    if domain_filter_applied:
        filtered_results = _filter_ranked_results(results, effective_query)
        if filtered_results:
            results = filtered_results[:max_results]
        else:
            return _fetch_crossref_results(
                query,
                effective_query,
                domain_filter_applied,
                max_results,
                "resultats arXiv juges peu pertinents pour l'electrotechnique",
            )

    return _build_arxiv_response(query, effective_query, domain_filter_applied, results)


@app.get("/", response_model=HomeResponse)
def home():
    return HomeResponse(
        status="ok",
        message="API Python electrotechnique active",
        available_endpoints=["/health", "/wolfram", "/arxiv", "/research", "/smart-query", "/gpt-tool"],
    )


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")


@app.get("/wolfram", response_model=WolframResponse)
def wolfram_query(
    query: str | None = Query(None, min_length=2, max_length=300, description="Question envoyee a WolframAlpha"),
    input_text: str | None = Query(
        None,
        alias="input",
        min_length=2,
        max_length=300,
        description="Alias compatible avec l'ancienne version de l'API",
    ),
):
    question = _get_text_param(query) or _get_text_param(input_text)
    if not question:
        raise HTTPException(
            status_code=422,
            detail="Fournis un parametre 'query' ou 'input'.",
        )

    return _fetch_wolfram_result(question)


@app.get(
    "/arxiv",
    response_model=ArxivResponse,
    response_model_exclude_none=True,
    summary="Recherche arXiv",
    description="Recherche d'articles arXiv avec fallback Crossref si arXiv repond mal.",
)
def search_arxiv(
    query: str = Query(..., min_length=2, max_length=200, description="Sujet ou mot-cle pour arXiv"),
    max_results: int = Query(3, ge=1, le=10, description="Nombre maximum d'articles"),
    sort_by: str = Query(
        "relevance",
        pattern="^(relevance|lastUpdatedDate|submittedDate)$",
        description="Ordre de tri des articles arXiv",
    ),
    auto_filter: bool = Query(
        True,
        description="Ajoute automatiquement un filtre 'electrical engineering' si la requete n'est pas deja orientee electrotechnique.",
    ),
):
    return _fetch_arxiv_results(
        query,
        _get_int_param(max_results, 3),
        sort_by,
        _get_bool_param(auto_filter, True),
    )


@app.get("/research", response_model=ResearchResponse)
def research(
    query: str = Query(..., min_length=2, max_length=300, description="Question ou sujet de recherche"),
    max_results: int = Query(3, ge=1, le=10, description="Nombre maximum d'articles arXiv"),
    auto_filter: bool = Query(
        True,
        description="Ajoute automatiquement un filtre 'electrical engineering' pour cadrer la recherche.",
    ),
):
    max_results_value = _get_int_param(max_results, 3)
    auto_filter_value = _get_bool_param(auto_filter, True)
    normalized_query = _normalize_text(query)
    preferred_route, _ = _decide_smart_route(normalized_query)
    sources = {}
    errors = {}

    if preferred_route == "wolfram":
        try:
            sources["wolfram"] = _fetch_wolfram_result(query)
        except HTTPException as exc:
            errors["wolfram"] = str(exc.detail)

    try:
        sources["arxiv"] = _fetch_arxiv_results(query, max_results_value, "relevance", auto_filter_value)
    except HTTPException as exc:
        errors["arxiv"] = str(exc.detail)

    return ResearchResponse(
        status="ok" if sources else "error",
        query=query,
        sources=sources,
        errors=errors,
    ).model_dump()


@app.get(
    "/smart-query",
    response_model=SmartQueryResponse,
    response_model_exclude_none=True,
    summary="Routeur intelligent",
    description="Endpoint optimise pour un assistant GPT: detecte le bon mode, expose le redirect utile, et execute directement l'outil si necessaire.",
)
def smart_query(
    query: str | None = Query(None, min_length=2, max_length=300, description="Question a router intelligemment"),
    input_text: str | None = Query(
        None,
        alias="input",
        min_length=2,
        max_length=300,
        description="Alias compatible GPT/outils pour la question a router",
    ),
    max_results: int = Query(3, ge=1, le=10, description="Nombre maximum d'articles si la route choisie est arXiv"),
    auto_filter: bool = Query(
        True,
        description="Ajoute automatiquement un filtre 'electrical engineering' pour les recherches arXiv.",
    ),
):
    raw_query = _get_text_param(query) or _get_text_param(input_text)
    if not raw_query:
        raise HTTPException(
            status_code=422,
            detail="Fournis un parametre 'query' ou 'input'.",
        )

    normalized_query = _normalize_text(raw_query)
    max_results_value = _get_int_param(max_results, 3)
    auto_filter_value = _get_bool_param(auto_filter, True)
    route, reason = _decide_smart_route(normalized_query)

    if route == "wolfram":
        try:
            payload = _fetch_wolfram_result(normalized_query)
            return _build_smart_payload(
                status="ok",
                mode="wolfram",
                raw_query=raw_query,
                normalized_query=normalized_query,
                reason=reason,
                max_results=max_results_value,
                auto_filter=auto_filter_value,
                executed=True,
                response=payload.get("result"),
                data=payload,
            )
        except HTTPException as exc:
            return _build_smart_payload(
                status="error",
                mode="wolfram",
                raw_query=raw_query,
                normalized_query=normalized_query,
                reason=reason,
                max_results=max_results_value,
                auto_filter=auto_filter_value,
                executed=False,
                response="Le mode Wolfram a ete selectionne, mais l'execution a echoue.",
                error=str(exc.detail),
            )

    if route == "arxiv":
        try:
            payload = _fetch_arxiv_results(normalized_query, max_results_value, "relevance", auto_filter_value)
            return _build_smart_payload(
                status=payload.get("status", "ok"),
                mode="arxiv",
                raw_query=raw_query,
                normalized_query=normalized_query,
                reason=reason,
                max_results=max_results_value,
                auto_filter=auto_filter_value,
                executed=True,
                response=_build_arxiv_brief(payload),
                data=payload,
            )
        except HTTPException as exc:
            return _build_smart_payload(
                status="error",
                mode="arxiv",
                raw_query=raw_query,
                normalized_query=normalized_query,
                reason=reason,
                max_results=max_results_value,
                auto_filter=auto_filter_value,
                executed=False,
                response="Le mode arXiv a ete selectionne, mais l'execution a echoue.",
                error=str(exc.detail),
            )

    direct_response = _build_direct_response(normalized_query)
    return _build_smart_payload(
        status="ok",
        mode="basic",
        raw_query=raw_query,
        normalized_query=normalized_query,
        reason=reason,
        max_results=max_results_value,
        auto_filter=auto_filter_value,
        executed=False,
        response=direct_response,
        answer=direct_response,
    )


@app.get(
    "/gpt-tool",
    response_model=GptToolResponse,
    summary="GPT Tool",
    description="Version minimale et stable pour les Actions ChatGPT. Meme schema JSON dans tous les cas.",
)
def gpt_tool(
    query: str | None = Query(None, min_length=2, max_length=300, description="Question a traiter"),
    input_text: str | None = Query(
        None,
        alias="input",
        min_length=2,
        max_length=300,
        description="Alias principal pour les Actions ChatGPT",
    ),
    max_results: int = Query(3, ge=1, le=10, description="Nombre maximum d'articles si mode arxiv"),
    auto_filter: bool = Query(
        True,
        description="Ajoute automatiquement un filtre electrotechnique pour les recherches scientifiques.",
    ),
):
    raw_query = _get_text_param(query) or _get_text_param(input_text)
    if not raw_query:
        raise HTTPException(
            status_code=422,
            detail="Fournis un parametre 'query' ou 'input'.",
        )

    smart_payload = smart_query(
        query=raw_query,
        max_results=_get_int_param(max_results, 3),
        auto_filter=_get_bool_param(auto_filter, True),
    )
    return _to_gpt_tool_response(smart_payload)

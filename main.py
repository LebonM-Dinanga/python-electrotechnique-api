import html
import json
import math
import os
import re
import time
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import urlencode

import requests
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

WOLFRAM_APP_ID = os.getenv("WOLFRAM_APP_ID", "").strip()
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "lebonmukendi17@gmail.com")
DEFAULT_PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://python-electrotechnique-api.onrender.com")
PLUGIN_CONTACT_EMAIL = CONTACT_EMAIL or "lebonmukendi17@gmail.com"
PLUGIN_LEGAL_URL = os.getenv("PLUGIN_LEGAL_URL", "")
PLUGIN_LOGO_URL = os.getenv("PLUGIN_LOGO_URL", "https://placehold.co/512x512/png?text=ElectroGPT")
DEFAULT_ALLOWED_ORIGINS = ",".join(
    [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "https://python-electrotechnique-api.onrender.com",
    ]
)
ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS).split(",") if origin.strip()]
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
SIMULATION_HINTS = {
    "simulate",
    "simulation",
    "simuler",
    "simu",
    "transient",
    "step response",
    "charge",
    "discharge",
    "decay",
    "capacitor",
    "capacitive",
    "inductor",
    "inductive",
    "rc",
    "rl",
    "rlc",
    "transformer",
    "transfo",
    "three phase",
    "three-phase",
    "triphase",
    "motor",
    "moteur",
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

base_user_agent = "python-electrotechnique-api/2.0"
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
    details: dict[str, Any] = Field(default_factory=dict)
    error: str = ""


class SimulationPoint(BaseModel):
    time_s: float
    capacitor_voltage_v: float | None = None
    resistor_current_a: float | None = None
    stored_energy_j: float | None = None
    inductor_current_a: float | None = None
    inductor_voltage_v: float | None = None
    signals: dict[str, float] | None = None


class SimulationResponse(BaseModel):
    status: str
    source: str
    kind: str
    simulation_mode: str
    query: str
    summary: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    count: int
    series: list[SimulationPoint] = Field(default_factory=list)


app = FastAPI(
    title="Python Electrotechnique API",
    description="API FastAPI pour enrichir un assistant GPT avec WolframAlpha, arXiv et des simulations electrotechniques avancees.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],
    allow_credentials="*" not in ALLOWED_ORIGINS,
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


def _round_float(value: float) -> float:
    return round(value, 6)


def _extract_named_float(query: str, aliases: list[str]) -> float | None:
    for alias in aliases:
        pattern = rf"(?:^|[\s,;]){re.escape(alias)}\s*=?\s*(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)"
        match = re.search(pattern, query, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def _extract_named_int(query: str, aliases: list[str]) -> int | None:
    value = _extract_named_float(query, aliases)
    return int(value) if value is not None else None


def _extract_named_choice(query: str, aliases: list[str], allowed_values: list[str]) -> str | None:
    for alias in aliases:
        pattern = rf"(?:^|[\s,;]){re.escape(alias)}\s*=?\s*([a-zA-Z\-]+)"
        match = re.search(pattern, query, flags=re.IGNORECASE)
        if match:
            candidate = match.group(1).lower()
            if candidate in allowed_values:
                return candidate
    return None


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


def _build_simulation_error(query: str, kind: str, message: str) -> dict[str, Any]:
    return SimulationResponse(
        status="error",
        source="simulation-engine",
        kind=kind,
        simulation_mode="unsupported",
        query=query,
        summary=message,
        parameters={},
        count=0,
        series=[],
    ).model_dump()


def _simulate_rc(
    query: str,
    resistance_ohms: float,
    capacitance_f: float,
    source_voltage_v: float,
    duration_s: float,
    steps: int,
    simulation_mode: str,
    initial_voltage_v: float | None,
) -> dict[str, Any]:
    if resistance_ohms <= 0 or capacitance_f <= 0 or duration_s <= 0:
        return _build_simulation_error(query, "rc", "Les parametres R, C et duration doivent etre strictement positifs.")

    effective_initial_voltage = initial_voltage_v if initial_voltage_v is not None else (source_voltage_v if simulation_mode == "discharge" else 0.0)
    forcing_voltage = 0.0 if simulation_mode == "discharge" else source_voltage_v
    tau = resistance_ohms * capacitance_f
    safe_steps = max(2, min(steps, 500))
    series = []

    for index in range(safe_steps):
        time_s = duration_s * index / (safe_steps - 1)
        capacitor_voltage = forcing_voltage + (effective_initial_voltage - forcing_voltage) * math.exp(-time_s / tau)
        resistor_current = (forcing_voltage - capacitor_voltage) / resistance_ohms
        stored_energy = 0.5 * capacitance_f * capacitor_voltage**2
        series.append(
            SimulationPoint(
                time_s=_round_float(time_s),
                capacitor_voltage_v=_round_float(capacitor_voltage),
                resistor_current_a=_round_float(resistor_current),
                stored_energy_j=_round_float(stored_energy),
            )
        )

    summary = (
        f"Simulation RC {simulation_mode}. "
        f"Tau={_round_float(tau)} s, Vc final={series[-1].capacitor_voltage_v} V, "
        f"I final={series[-1].resistor_current_a} A."
    )

    return SimulationResponse(
        status="ok",
        source="simulation-engine",
        kind="rc",
        simulation_mode=simulation_mode,
        query=query,
        summary=summary,
        parameters={
            "resistance_ohms": resistance_ohms,
            "capacitance_f": capacitance_f,
            "source_voltage_v": source_voltage_v,
            "duration_s": duration_s,
            "steps": safe_steps,
            "initial_voltage_v": effective_initial_voltage,
            "tau_s": _round_float(tau),
        },
        metrics={
            "tau_s": _round_float(tau),
            "final_capacitor_voltage_v": series[-1].capacitor_voltage_v,
            "final_current_a": series[-1].resistor_current_a,
            "peak_current_a": _round_float(max(abs(point.resistor_current_a or 0.0) for point in series)),
        },
        count=len(series),
        series=series,
    ).model_dump()


def _simulate_rl(
    query: str,
    resistance_ohms: float,
    inductance_h: float,
    source_voltage_v: float,
    duration_s: float,
    steps: int,
    simulation_mode: str,
    initial_current_a: float | None,
) -> dict[str, Any]:
    if resistance_ohms <= 0 or inductance_h <= 0 or duration_s <= 0:
        return _build_simulation_error(query, "rl", "Les parametres R, L et duration doivent etre strictement positifs.")

    effective_initial_current = initial_current_a if initial_current_a is not None else (source_voltage_v / resistance_ohms if simulation_mode == "decay" else 0.0)
    forcing_voltage = 0.0 if simulation_mode == "decay" else source_voltage_v
    tau = inductance_h / resistance_ohms
    target_current = forcing_voltage / resistance_ohms
    safe_steps = max(2, min(steps, 500))
    series = []

    for index in range(safe_steps):
        time_s = duration_s * index / (safe_steps - 1)
        inductor_current = target_current + (effective_initial_current - target_current) * math.exp(-time_s / tau)
        inductor_voltage = forcing_voltage - resistance_ohms * inductor_current
        stored_energy = 0.5 * inductance_h * inductor_current**2
        series.append(
            SimulationPoint(
                time_s=_round_float(time_s),
                inductor_current_a=_round_float(inductor_current),
                inductor_voltage_v=_round_float(inductor_voltage),
                stored_energy_j=_round_float(stored_energy),
            )
        )

    summary = (
        f"Simulation RL {simulation_mode}. "
        f"Tau={_round_float(tau)} s, I final={series[-1].inductor_current_a} A, "
        f"VL final={series[-1].inductor_voltage_v} V."
    )

    return SimulationResponse(
        status="ok",
        source="simulation-engine",
        kind="rl",
        simulation_mode=simulation_mode,
        query=query,
        summary=summary,
        parameters={
            "resistance_ohms": resistance_ohms,
            "inductance_h": inductance_h,
            "source_voltage_v": source_voltage_v,
            "duration_s": duration_s,
            "steps": safe_steps,
            "initial_current_a": effective_initial_current,
            "tau_s": _round_float(tau),
        },
        metrics={
            "tau_s": _round_float(tau),
            "final_current_a": series[-1].inductor_current_a,
            "final_inductor_voltage_v": series[-1].inductor_voltage_v,
            "peak_current_a": _round_float(max(abs(point.inductor_current_a or 0.0) for point in series)),
        },
        count=len(series),
        series=series,
    ).model_dump()


def _rk4_step_2d(
    state_a: float,
    state_b: float,
    dt: float,
    derivatives: Any,
) -> tuple[float, float]:
    k1_a, k1_b = derivatives(state_a, state_b)
    k2_a, k2_b = derivatives(state_a + 0.5 * dt * k1_a, state_b + 0.5 * dt * k1_b)
    k3_a, k3_b = derivatives(state_a + 0.5 * dt * k2_a, state_b + 0.5 * dt * k2_b)
    k4_a, k4_b = derivatives(state_a + dt * k3_a, state_b + dt * k3_b)

    next_a = state_a + (dt / 6.0) * (k1_a + 2.0 * k2_a + 2.0 * k3_a + k4_a)
    next_b = state_b + (dt / 6.0) * (k1_b + 2.0 * k2_b + 2.0 * k3_b + k4_b)
    return next_a, next_b


def _simulate_rlc(
    query: str,
    resistance_ohms: float,
    inductance_h: float,
    capacitance_f: float,
    source_voltage_v: float,
    duration_s: float,
    steps: int,
    simulation_mode: str,
    initial_voltage_v: float | None,
    initial_current_a: float | None,
) -> dict[str, Any]:
    if resistance_ohms <= 0 or inductance_h <= 0 or capacitance_f <= 0 or duration_s <= 0:
        return _build_simulation_error(query, "rlc", "Les parametres R, L, C et duration doivent etre strictement positifs.")

    forcing_voltage = 0.0 if simulation_mode in {"decay", "discharge"} else source_voltage_v
    effective_initial_voltage = initial_voltage_v if initial_voltage_v is not None else (source_voltage_v if simulation_mode in {"decay", "discharge"} else 0.0)
    effective_initial_current = initial_current_a if initial_current_a is not None else 0.0
    capacitor_voltage = effective_initial_voltage
    circuit_current = effective_initial_current
    safe_steps = max(2, min(steps, 1200))
    sample_interval_s = duration_s / (safe_steps - 1)
    alpha = resistance_ohms / (2.0 * inductance_h)
    omega_0 = 1.0 / math.sqrt(inductance_h * capacitance_f)
    damping_ratio = alpha / omega_0
    electrical_tau_s = inductance_h / resistance_ohms
    max_internal_dt_s = max(1e-6, min(sample_interval_s, electrical_tau_s / 20.0, 1.0 / (omega_0 * 80.0)))
    internal_steps = max(1, math.ceil(sample_interval_s / max_internal_dt_s))
    integration_dt_s = sample_interval_s / internal_steps
    if damping_ratio < 0.98:
        regime = "underdamped"
    elif damping_ratio <= 1.02:
        regime = "critical"
    else:
        regime = "overdamped"

    series = []
    peak_current = abs(circuit_current)
    peak_voltage = abs(capacitor_voltage)

    def derivatives(current_a: float, capacitor_v: float) -> tuple[float, float]:
        di_dt = (forcing_voltage - resistance_ohms * current_a - capacitor_v) / inductance_h
        dvc_dt = current_a / capacitance_f
        return di_dt, dvc_dt

    for index in range(safe_steps):
        time_s = sample_interval_s * index
        inductor_voltage = inductance_h * derivatives(circuit_current, capacitor_voltage)[0]
        resistor_voltage = resistance_ohms * circuit_current
        total_energy = 0.5 * inductance_h * circuit_current**2 + 0.5 * capacitance_f * capacitor_voltage**2
        peak_current = max(peak_current, abs(circuit_current))
        peak_voltage = max(peak_voltage, abs(capacitor_voltage))

        series.append(
            SimulationPoint(
                time_s=_round_float(time_s),
                capacitor_voltage_v=_round_float(capacitor_voltage),
                resistor_current_a=_round_float(circuit_current),
                stored_energy_j=_round_float(total_energy),
                inductor_voltage_v=_round_float(inductor_voltage),
                signals={
                    "circuit_current_a": _round_float(circuit_current),
                    "resistor_voltage_v": _round_float(resistor_voltage),
                    "source_voltage_v": _round_float(forcing_voltage),
                },
            )
        )

        if index < safe_steps - 1:
            for _ in range(internal_steps):
                circuit_current, capacitor_voltage = _rk4_step_2d(circuit_current, capacitor_voltage, integration_dt_s, derivatives)
                peak_current = max(peak_current, abs(circuit_current))
                peak_voltage = max(peak_voltage, abs(capacitor_voltage))

    summary = (
        f"Simulation RLC {simulation_mode}. Regime {regime}, "
        f"zeta={_round_float(damping_ratio)}, f0={_round_float(omega_0 / (2.0 * math.pi))} Hz, "
        f"Vc final={series[-1].capacitor_voltage_v} V."
    )

    return SimulationResponse(
        status="ok",
        source="simulation-engine",
        kind="rlc",
        simulation_mode=simulation_mode,
        query=query,
        summary=summary,
        parameters={
            "resistance_ohms": resistance_ohms,
            "inductance_h": inductance_h,
            "capacitance_f": capacitance_f,
            "source_voltage_v": source_voltage_v,
            "duration_s": duration_s,
            "steps": safe_steps,
            "initial_voltage_v": effective_initial_voltage,
            "initial_current_a": effective_initial_current,
            "integration_substeps": internal_steps,
        },
        metrics={
            "natural_frequency_hz": _round_float(omega_0 / (2.0 * math.pi)),
            "damping_ratio": _round_float(damping_ratio),
            "regime": regime,
            "peak_current_a": _round_float(peak_current),
            "peak_capacitor_voltage_v": _round_float(peak_voltage),
            "final_capacitor_voltage_v": series[-1].capacitor_voltage_v,
        },
        count=len(series),
        series=series,
    ).model_dump()


def _simulate_three_phase(query: str) -> dict[str, Any]:
    lowered_query = query.lower()
    line_voltage_v = _extract_named_float(lowered_query, ["vll", "vl", "line_voltage", "voltage"]) or 400.0
    line_current_a = _extract_named_float(lowered_query, ["i", "il", "line_current", "current"])
    power_factor = _extract_named_float(lowered_query, ["pf", "cosphi", "cos_phi"]) or 0.9
    frequency_hz = _extract_named_float(lowered_query, ["f", "freq", "frequency"]) or 50.0
    apparent_power_va = _extract_named_float(lowered_query, ["s", "va", "apparent_power"])
    apparent_power_kva = _extract_named_float(lowered_query, ["kva"])
    active_power_w = _extract_named_float(lowered_query, ["p", "power_w"])
    active_power_kw = _extract_named_float(lowered_query, ["kw", "power_kw"])

    connection = _extract_named_choice(lowered_query, ["conn", "connection", "coupling"], ["star", "wye", "delta"])
    if connection is None:
        connection = "delta" if "delta" in lowered_query else "star"

    power_factor = max(0.05, min(power_factor, 1.0))
    if line_voltage_v <= 0:
        return _build_simulation_error(query, "three-phase", "La tension composee doit etre strictement positive.")

    if apparent_power_kva is not None:
        apparent_power_va = apparent_power_kva * 1000.0
    if active_power_kw is not None:
        active_power_w = active_power_kw * 1000.0

    if line_current_a is None:
        if apparent_power_va is not None:
            line_current_a = apparent_power_va / (math.sqrt(3.0) * line_voltage_v)
        elif active_power_w is not None:
            line_current_a = active_power_w / (math.sqrt(3.0) * line_voltage_v * power_factor)
        else:
            line_current_a = 10.0

    apparent_power_va = math.sqrt(3.0) * line_voltage_v * line_current_a
    active_power_w = apparent_power_va * power_factor
    reactive_power_var = math.sqrt(max(apparent_power_va**2 - active_power_w**2, 0.0))
    phase_angle_deg = math.degrees(math.acos(power_factor))
    phase_voltage_v = line_voltage_v / math.sqrt(3.0) if connection in {"star", "wye"} else line_voltage_v
    phase_current_a = line_current_a if connection in {"star", "wye"} else line_current_a / math.sqrt(3.0)

    point = SimulationPoint(
        time_s=0.0,
        signals={
            "line_voltage_v": _round_float(line_voltage_v),
            "line_current_a": _round_float(line_current_a),
            "phase_voltage_v": _round_float(phase_voltage_v),
            "phase_current_a": _round_float(phase_current_a),
            "active_power_w": _round_float(active_power_w),
            "reactive_power_var": _round_float(reactive_power_var),
            "apparent_power_va": _round_float(apparent_power_va),
        },
    )

    return SimulationResponse(
        status="ok",
        source="simulation-engine",
        kind="three-phase",
        simulation_mode="steady-state",
        query=query,
        summary=(
            f"Simulation triphase {connection}. P={_round_float(active_power_w)} W, "
            f"Q={_round_float(reactive_power_var)} var, S={_round_float(apparent_power_va)} VA."
        ),
        parameters={
            "connection": connection,
            "line_voltage_v": line_voltage_v,
            "line_current_a": line_current_a,
            "power_factor": power_factor,
            "frequency_hz": frequency_hz,
        },
        metrics={
            "active_power_w": _round_float(active_power_w),
            "reactive_power_var": _round_float(reactive_power_var),
            "apparent_power_va": _round_float(apparent_power_va),
            "phase_angle_deg": _round_float(phase_angle_deg),
            "phase_voltage_v": _round_float(phase_voltage_v),
            "phase_current_a": _round_float(phase_current_a),
        },
        count=1,
        series=[point],
    ).model_dump()


def _simulate_transformer(query: str) -> dict[str, Any]:
    lowered_query = query.lower()
    primary_voltage_v = _extract_named_float(lowered_query, ["vp", "v1", "primary_voltage"]) or 20000.0
    secondary_voltage_v = _extract_named_float(lowered_query, ["vs", "v2", "secondary_voltage"]) or 400.0
    rated_power_va = _extract_named_float(lowered_query, ["s", "va", "rated_power"]) or 100000.0
    rated_power_kva = _extract_named_float(lowered_query, ["kva"])
    if rated_power_kva is not None:
        rated_power_va = rated_power_kva * 1000.0

    load_fraction = _extract_named_float(lowered_query, ["load", "load_pu", "load_fraction"]) or 1.0
    power_factor = _extract_named_float(lowered_query, ["pf", "cosphi", "cos_phi"]) or 0.9
    core_loss_w = _extract_named_float(lowered_query, ["pcore", "core_loss", "iron_loss"]) or max(0.01 * rated_power_va, 100.0)
    copper_loss_rated_w = _extract_named_float(lowered_query, ["pcu", "copper_loss", "cu_loss"]) or max(0.015 * rated_power_va, 150.0)
    regulation_pct = _extract_named_float(lowered_query, ["reg", "regulation", "reg_pct"]) or 3.0

    if primary_voltage_v <= 0 or secondary_voltage_v <= 0 or rated_power_va <= 0:
        return _build_simulation_error(query, "transformer", "Les parametres V1, V2 et S doivent etre strictement positifs.")

    load_fraction = max(0.0, min(load_fraction, 1.5))
    power_factor = max(0.05, min(power_factor, 1.0))
    turns_ratio = primary_voltage_v / secondary_voltage_v
    rated_primary_current_a = rated_power_va / primary_voltage_v
    rated_secondary_current_a = rated_power_va / secondary_voltage_v
    secondary_current_a = rated_secondary_current_a * load_fraction
    apparent_output_va = rated_power_va * load_fraction
    output_power_w = apparent_output_va * power_factor
    copper_loss_w = copper_loss_rated_w * load_fraction**2
    total_losses_w = core_loss_w + copper_loss_w
    input_power_w = output_power_w + total_losses_w
    efficiency = output_power_w / input_power_w if input_power_w > 0 else 0.0
    loaded_secondary_voltage_v = secondary_voltage_v * (1.0 - (regulation_pct / 100.0) * load_fraction * power_factor)

    point = SimulationPoint(
        time_s=0.0,
        signals={
            "primary_current_a": _round_float(rated_primary_current_a * load_fraction),
            "secondary_current_a": _round_float(secondary_current_a),
            "loaded_secondary_voltage_v": _round_float(loaded_secondary_voltage_v),
            "output_power_w": _round_float(output_power_w),
            "total_losses_w": _round_float(total_losses_w),
        },
    )

    return SimulationResponse(
        status="ok",
        source="simulation-engine",
        kind="transformer",
        simulation_mode="load-flow",
        query=query,
        summary=(
            f"Simulation transformateur. Rendement={_round_float(efficiency * 100.0)} %, "
            f"V2 charge={_round_float(loaded_secondary_voltage_v)} V, pertes={_round_float(total_losses_w)} W."
        ),
        parameters={
            "primary_voltage_v": primary_voltage_v,
            "secondary_voltage_v": secondary_voltage_v,
            "rated_power_va": rated_power_va,
            "load_fraction": load_fraction,
            "power_factor": power_factor,
            "core_loss_w": core_loss_w,
            "copper_loss_rated_w": copper_loss_rated_w,
            "regulation_pct": regulation_pct,
        },
        metrics={
            "turns_ratio": _round_float(turns_ratio),
            "rated_primary_current_a": _round_float(rated_primary_current_a),
            "rated_secondary_current_a": _round_float(rated_secondary_current_a),
            "output_power_w": _round_float(output_power_w),
            "input_power_w": _round_float(input_power_w),
            "efficiency_pct": _round_float(efficiency * 100.0),
            "total_losses_w": _round_float(total_losses_w),
            "loaded_secondary_voltage_v": _round_float(loaded_secondary_voltage_v),
        },
        count=1,
        series=[point],
    ).model_dump()


def _simulate_dc_motor(query: str, steps_default: int = 160) -> dict[str, Any]:
    lowered_query = query.lower()
    supply_voltage_v = _extract_named_float(lowered_query, ["v", "vin", "voltage"]) or 24.0
    resistance_ohms = _extract_named_float(lowered_query, ["r", "res", "resistance"]) or 1.2
    inductance_h = _extract_named_float(lowered_query, ["l", "ind", "inductance"]) or 0.02
    back_emf_constant = _extract_named_float(lowered_query, ["ke", "bemf", "back_emf"]) or 0.08
    torque_constant = _extract_named_float(lowered_query, ["kt", "torque_constant"]) or back_emf_constant
    inertia_kgm2 = _extract_named_float(lowered_query, ["j", "inertia"]) or 0.01
    damping_nms = _extract_named_float(lowered_query, ["b", "damping"]) or 0.001
    load_torque_nm = _extract_named_float(lowered_query, ["tl", "load_torque", "torque_load"]) or 0.0
    duration_s = _extract_named_float(lowered_query, ["t", "time", "duration", "duration_s"]) or 2.0
    steps = _extract_named_int(lowered_query, ["steps", "points"]) or steps_default
    initial_current_a = _extract_named_float(lowered_query, ["i0", "initial_current"]) or 0.0
    initial_speed_rad_s = _extract_named_float(lowered_query, ["w0", "omega0", "initial_speed"]) or 0.0
    initial_speed_rpm = _extract_named_float(lowered_query, ["rpm0", "initial_rpm"])
    if initial_speed_rpm is not None:
        initial_speed_rad_s = initial_speed_rpm * 2.0 * math.pi / 60.0

    if resistance_ohms <= 0 or inductance_h <= 0 or inertia_kgm2 <= 0 or duration_s <= 0:
        return _build_simulation_error(query, "dc-motor", "Les parametres R, L, J et duration doivent etre strictement positifs.")

    safe_steps = max(2, min(steps, 1500))
    sample_interval_s = duration_s / (safe_steps - 1)
    electrical_tau_s = inductance_h / resistance_ohms
    mechanical_tau_s = inertia_kgm2 / max(damping_nms + torque_constant * back_emf_constant / resistance_ohms, 1e-6)
    max_internal_dt_s = max(1e-6, min(sample_interval_s, electrical_tau_s / 25.0, mechanical_tau_s / 25.0))
    internal_steps = max(1, math.ceil(sample_interval_s / max_internal_dt_s))
    integration_dt_s = sample_interval_s / internal_steps
    current_a = initial_current_a
    omega_rad_s = initial_speed_rad_s
    series = []
    peak_current = abs(current_a)
    peak_speed = abs(omega_rad_s)

    def derivatives(armature_current_a: float, speed_rad_s: float) -> tuple[float, float]:
        di_dt = (supply_voltage_v - resistance_ohms * armature_current_a - back_emf_constant * speed_rad_s) / inductance_h
        dw_dt = (torque_constant * armature_current_a - damping_nms * speed_rad_s - load_torque_nm) / inertia_kgm2
        return di_dt, dw_dt

    for index in range(safe_steps):
        time_s = sample_interval_s * index
        back_emf_v = back_emf_constant * omega_rad_s
        electromagnetic_torque = torque_constant * current_a
        stored_energy = 0.5 * inductance_h * current_a**2 + 0.5 * inertia_kgm2 * omega_rad_s**2
        speed_rpm = omega_rad_s * 60.0 / (2.0 * math.pi)
        peak_current = max(peak_current, abs(current_a))
        peak_speed = max(peak_speed, abs(omega_rad_s))

        series.append(
            SimulationPoint(
                time_s=_round_float(time_s),
                stored_energy_j=_round_float(stored_energy),
                signals={
                    "armature_current_a": _round_float(current_a),
                    "speed_rad_s": _round_float(omega_rad_s),
                    "speed_rpm": _round_float(speed_rpm),
                    "back_emf_v": _round_float(back_emf_v),
                    "torque_nm": _round_float(electromagnetic_torque),
                },
            )
        )

        if index < safe_steps - 1:
            for _ in range(internal_steps):
                current_a, omega_rad_s = _rk4_step_2d(current_a, omega_rad_s, integration_dt_s, derivatives)
                peak_current = max(peak_current, abs(current_a))
                peak_speed = max(peak_speed, abs(omega_rad_s))

    steady_speed_rad_s = (
        (torque_constant * supply_voltage_v / resistance_ohms - load_torque_nm)
        / (torque_constant * back_emf_constant / resistance_ohms + damping_nms)
    )
    steady_speed_rpm = steady_speed_rad_s * 60.0 / (2.0 * math.pi)

    return SimulationResponse(
        status="ok",
        source="simulation-engine",
        kind="dc-motor",
        simulation_mode="startup",
        query=query,
        summary=(
            f"Simulation moteur DC. Vitesse finale={_round_float(series[-1].signals['speed_rpm'])} rpm, "
            f"courant final={_round_float(series[-1].signals['armature_current_a'])} A."
        ),
        parameters={
            "supply_voltage_v": supply_voltage_v,
            "resistance_ohms": resistance_ohms,
            "inductance_h": inductance_h,
            "back_emf_constant": back_emf_constant,
            "torque_constant": torque_constant,
            "inertia_kgm2": inertia_kgm2,
            "damping_nms": damping_nms,
            "load_torque_nm": load_torque_nm,
            "duration_s": duration_s,
            "steps": safe_steps,
            "integration_substeps": internal_steps,
        },
        metrics={
            "stall_current_a": _round_float(supply_voltage_v / resistance_ohms),
            "estimated_steady_speed_rpm": _round_float(steady_speed_rpm),
            "peak_current_a": _round_float(peak_current),
            "peak_speed_rpm": _round_float(peak_speed * 60.0 / (2.0 * math.pi)),
            "final_speed_rpm": _round_float(series[-1].signals["speed_rpm"]),
            "final_current_a": _round_float(series[-1].signals["armature_current_a"]),
        },
        count=len(series),
        series=series,
    ).model_dump()


def _simulate_from_query(query: str, steps_default: int = 80) -> dict[str, Any]:
    lowered_query = query.lower()
    if re.search(r"\brlc\b|resonan|resonance", lowered_query):
        kind = "rlc"
    elif re.search(r"three phase|three-phase|triphas", lowered_query):
        kind = "three-phase"
    elif re.search(r"transformer|transfo", lowered_query):
        kind = "transformer"
    elif re.search(r"dc motor|motor dc|moteur dc|back emf", lowered_query):
        kind = "dc-motor"
    elif re.search(r"\brc\b|capacitor|capacitive", lowered_query):
        kind = "rc"
    elif re.search(r"\brl\b|inductor|inductive", lowered_query):
        kind = "rl"
    else:
        kind = ""
    if not kind:
        return _build_simulation_error(
            query,
            "unknown",
            (
                "Simulation non prise en charge. Utilise par exemple: "
                "'simulate rc r=1000 c=0.001 v=5 t=5', "
                "'simulate rlc r=10 l=0.05 c=0.0001 v=24 t=1', "
                "'simulate transformer kva=100 v1=20000 v2=400 load=0.8', "
                "ou 'simulate dc motor v=24 r=1.2 l=0.02 ke=0.08 kt=0.08 j=0.01 t=2'."
            ),
        )

    resistance_ohms = _extract_named_float(lowered_query, ["r", "res", "resistance"])
    source_voltage_v = _extract_named_float(lowered_query, ["v", "vin", "source_voltage", "voltage"]) or 0.0
    duration_s = _extract_named_float(lowered_query, ["t", "time", "duration", "duration_s"]) or 1.0
    steps = _extract_named_int(lowered_query, ["steps", "points"]) or steps_default

    if kind == "three-phase":
        return _simulate_three_phase(query)

    if kind == "transformer":
        return _simulate_transformer(query)

    if kind == "dc-motor":
        return _simulate_dc_motor(query, steps_default=max(steps_default, 120))

    if kind == "rlc":
        inductance_h = _extract_named_float(lowered_query, ["l", "ind", "inductance"])
        capacitance_f = _extract_named_float(lowered_query, ["c", "cap", "capacitance"])
        initial_voltage_v = _extract_named_float(lowered_query, ["vc0", "v0", "initial_voltage"])
        initial_current_a = _extract_named_float(lowered_query, ["i0", "initial_current"])
        simulation_mode = "decay" if "decay" in lowered_query or "discharge" in lowered_query else "step"
        if resistance_ohms is None or inductance_h is None or capacitance_f is None:
            return _build_simulation_error(
                query,
                "rlc",
                "Simulation RLC incomplete. Fournis au minimum r, l et c, par exemple: simulate rlc r=10 l=0.05 c=0.0001 v=24 t=1",
            )
        return _simulate_rlc(
            query,
            resistance_ohms,
            inductance_h,
            capacitance_f,
            source_voltage_v,
            duration_s,
            steps,
            simulation_mode,
            initial_voltage_v,
            initial_current_a,
        )

    if kind == "rc":
        capacitance_f = _extract_named_float(lowered_query, ["c", "cap", "capacitance"])
        initial_voltage_v = _extract_named_float(lowered_query, ["vc0", "v0", "initial_voltage"])
        simulation_mode = "discharge" if "discharge" in lowered_query else "charge"
        if resistance_ohms is None or capacitance_f is None:
            return _build_simulation_error(query, "rc", "Simulation RC incomplete. Fournis au minimum r et c, par exemple: simulate rc r=1000 c=0.001 v=5 t=5")
        return _simulate_rc(query, resistance_ohms, capacitance_f, source_voltage_v, duration_s, steps, simulation_mode, initial_voltage_v)

    inductance_h = _extract_named_float(lowered_query, ["l", "ind", "inductance"])
    initial_current_a = _extract_named_float(lowered_query, ["i0", "initial_current"])
    simulation_mode = "decay" if "decay" in lowered_query else "energize"
    if resistance_ohms is None or inductance_h is None:
        return _build_simulation_error(query, "rl", "Simulation RL incomplete. Fournis au minimum r et l, par exemple: simulate rl r=10 l=0.2 v=24 t=1")
    return _simulate_rl(query, resistance_ohms, inductance_h, source_voltage_v, duration_s, steps, simulation_mode, initial_current_a)


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

    if _contains_any(lowered_query, SIMULATION_HINTS) and re.search(
        r"\brc\b|\brl\b|\brlc\b|capacitor|capacitive|inductor|inductive|transformer|transfo|three phase|three-phase|triphas|dc motor|motor dc|moteur dc|back emf",
        lowered_query,
    ):
        return "simulation", "Question detectee comme demande de simulation electrotechnique."

    if re.search(
        r"\brc\b|\brl\b|\brlc\b|transformer|transfo|three phase|three-phase|triphas|dc motor|motor dc|moteur dc",
        lowered_query,
    ) and re.search(r"\d|=", lowered_query):
        return "simulation", "Question detectee comme demande de simulation electrotechnique."

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

    if mode == "simulation":
        return f"/simulate?{urlencode({'input': query})}"

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

    if mode == "simulation":
        simulation_label = data.get("kind", "simulation").replace("-", " ").upper()
        return [
            GptToolResult(
                title=f"Simulation {simulation_label}",
                snippet=data.get("summary", fallback_answer),
                link="",
                published="",
                authors=[],
                provider=data.get("source", "simulation-engine"),
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
    elif mode == "simulation":
        source = data.get("source", "simulation-engine")
        query_used = smart_payload.get("normalized_input") or smart_payload.get("input", "")
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
        details=data,
        error=error,
    ).model_dump()


def _get_base_url(request: Request | None = None, override: str | None = None) -> str:
    if override:
        return override.rstrip("/")
    if request is not None:
        return str(request.base_url).rstrip("/")
    return DEFAULT_PUBLIC_BASE_URL


def _build_chatgpt_action_openapi(server_url: str) -> dict[str, Any]:
    full_spec = json.loads(json.dumps(app.openapi()))
    full_spec["openapi"] = "3.1.0"
    full_spec["info"] = {
        "title": "Electrotechnique GPT Action API",
        "description": "Minimal OpenAPI schema expose uniquement l'endpoint /gpt-tool pour ChatGPT Actions.",
        "version": app.version,
    }
    full_spec["servers"] = [
        {
            "url": server_url,
            "description": "Public HTTPS endpoint for ChatGPT Actions",
        }
    ]
    full_spec["paths"] = {
        "/gpt-tool": full_spec["paths"]["/gpt-tool"],
    }
    return full_spec


def _build_ai_plugin_manifest(base_url: str) -> dict[str, Any]:
    legal_url = PLUGIN_LEGAL_URL or f"{base_url}/legal"
    return {
        "schema_version": "v1",
        "name_for_human": "Electrotechnique GPT Tool",
        "name_for_model": "electrotechnique_gpt_tool",
        "description_for_human": "Calculs scientifiques, simulations avancees et recherche documentaire electrotechnique pour ChatGPT.",
        "description_for_model": (
            "Use this tool for scientific calculations, advanced electrical simulations, transformer-loss queries, "
            "three-phase or motor analysis, and electrical-engineering paper retrieval. Send the user request in the input field."
        ),
        "auth": {"type": "none"},
        "api": {
            "type": "openapi",
            "url": f"{base_url}/openapi.chatgpt.json",
            "is_user_authenticated": False,
        },
        "logo_url": PLUGIN_LOGO_URL,
        "contact_email": PLUGIN_CONTACT_EMAIL,
        "legal_info_url": legal_url,
    }


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
        available_endpoints=[
            "/health",
            "/wolfram",
            "/arxiv",
            "/simulate",
            "/research",
            "/smart-query",
            "/gpt-tool",
            "/openapi.chatgpt.json",
            "/.well-known/ai-plugin.json",
        ],
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


@app.get(
    "/simulate",
    response_model=SimulationResponse,
    response_model_exclude_none=True,
    summary="Simulation electrotechnique",
    description="Simulation RC, RL, RLC, transformateur, triphase ou moteur DC a partir d'une requete libre avec parametres nommes.",
)
def simulate(
    query: str | None = Query(None, min_length=2, max_length=300, description="Requete de simulation libre"),
    input_text: str | None = Query(
        None,
        alias="input",
        min_length=2,
        max_length=300,
        description="Alias principal pour la requete de simulation",
    ),
):
    raw_query = _get_text_param(query) or _get_text_param(input_text)
    if not raw_query:
        raise HTTPException(
            status_code=422,
            detail="Fournis un parametre 'query' ou 'input'.",
        )

    return _simulate_from_query(raw_query)


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

    if route == "simulation":
        payload = _simulate_from_query(normalized_query)
        return _build_smart_payload(
            status=payload.get("status", "ok"),
            mode="simulation",
            raw_query=raw_query,
            normalized_query=normalized_query,
            reason=reason,
            max_results=max_results_value,
            auto_filter=auto_filter_value,
            executed=payload.get("status") == "ok",
            response=payload.get("summary"),
            data=payload,
            error="" if payload.get("status") == "ok" else payload.get("summary"),
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


@app.get("/openapi.chatgpt.json", include_in_schema=False)
def chatgpt_action_openapi(request: Request):
    return JSONResponse(_build_chatgpt_action_openapi(_get_base_url(request=request)))


@app.get("/.well-known/ai-plugin.json", include_in_schema=False)
def ai_plugin_manifest(request: Request):
    return JSONResponse(_build_ai_plugin_manifest(_get_base_url(request=request)))


@app.get("/ai-plugin.json", include_in_schema=False)
def ai_plugin_manifest_alias(request: Request):
    return JSONResponse(_build_ai_plugin_manifest(_get_base_url(request=request)))


@app.get("/legal", include_in_schema=False)
def legal_notice():
    return HTMLResponse(
        """
        <!doctype html>
        <html lang="fr">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>Politique de confidentialite - Electrotechnique GPT Tool</title>
        </head>
        <body style="font-family: Arial, sans-serif; max-width: 760px; margin: 40px auto; line-height: 1.6;">
          <h1>Politique de confidentialite</h1>
          <p>Ce service expose une API de calcul scientifique et de recherche documentaire pour un GPT personnalise.</p>
          <p>Les requetes envoyees a cette API peuvent etre transmises a des services tiers tels que WolframAlpha, arXiv ou Crossref afin de produire une reponse.</p>
          <p>N'envoyez pas de donnees sensibles ou secretes dans vos requetes.</p>
          <p>Pour toute question relative a la confidentialite, contactez l'exploitant de ce service via l'adresse configuree dans le manifeste de l'action.</p>
        </body>
        </html>
        """.strip()
    )

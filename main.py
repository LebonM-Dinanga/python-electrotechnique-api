import html
import asyncio
import json
import math
import os
import re
import time
import xml.etree.ElementTree as ET
from collections import defaultdict, deque
from threading import Lock
from typing import Any
from urllib.parse import urlencode

import requests
from fastapi import Body, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

try:
    from pymodbus.client import ModbusTcpClient
except ImportError:
    ModbusTcpClient = None

WOLFRAM_APP_ID = os.getenv("WOLFRAM_APP_ID", "").strip()
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "lebonmukendi17@gmail.com")
DEFAULT_PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://electrotechnique-gpt-tool.onrender.com")
PLUGIN_CONTACT_EMAIL = CONTACT_EMAIL or "lebonmukendi17@gmail.com"
PLUGIN_LEGAL_URL = os.getenv("PLUGIN_LEGAL_URL", "")
PLUGIN_LOGO_URL = os.getenv("PLUGIN_LOGO_URL", "https://placehold.co/512x512/png?text=ElectroGPT")
DEFAULT_ALLOWED_ORIGINS = ",".join(
    [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "https://electrotechnique-gpt-tool.onrender.com",
    ]
)
ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS).split(",") if origin.strip()]
REQUEST_TIMEOUT = (5, 10)
ARXIV_API_URL = "https://export.arxiv.org/api/query"
CROSSREF_API_URL = "https://api.crossref.org/works"
WOLFRAM_API_URL = "https://api.wolframalpha.com/v1/result"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
ARXIV_DOMAIN_FILTER = os.getenv("ARXIV_DOMAIN_FILTER", "electrical engineering")
MAX_TELEMETRY_POINTS = int(os.getenv("MAX_TELEMETRY_POINTS", "600"))
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "").strip()
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_TOPIC_PREFIX = os.getenv("MQTT_TOPIC_PREFIX", "electrogpt/telemetry").strip().strip("/")
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "").strip()
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "").strip()
MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))

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
ACADEMIC_HINTS = {
    "tfe",
    "pfe",
    "memoire",
    "mémoire",
    "these",
    "thèse",
    "thesis",
    "dissertation",
    "sujet",
    "sujets",
    "theme",
    "thème",
    "problem statement",
    "problematique",
    "problématique",
    "objectifs",
    "objectives",
    "methodologie",
    "méthodologie",
    "methodology",
    "chapitre",
    "chapter",
    "plan de these",
    "plan de thèse",
    "guide de recherche",
    "research guide",
    "literature review",
    "etat de l'art",
    "état de l'art",
    "bibliographie",
    "bibliography",
    "proposal",
}
ACADEMIC_GENERIC_TOKENS = {
    "c",
    "est",
    "ce",
    "un",
    "une",
    "dont",
    "vais",
    "veut",
    "veux",
    "faire",
    "fais",
    "plan",
    "detaille",
    "detailler",
    "detaillé",
    "détaillé",
    "sujet",
    "theme",
    "thème",
    "memoire",
    "mémoire",
    "these",
    "thèse",
    "thesis",
    "tfe",
    "pfe",
    "travail",
    "cycle",
    "academique",
    "académique",
    "document",
    "pdf",
}
ENGINEERING_TOPIC_TOKENS = {
    "electrotechnique",
    "electrical",
    "engineering",
    "energie",
    "énergie",
    "power",
    "transformateur",
    "transformateurs",
    "transformer",
    "relais",
    "relay",
    "protection",
    "moteur",
    "motor",
    "machine",
    "machines",
    "microreseau",
    "microgrid",
    "reseau",
    "réseau",
    "qualite",
    "qualité",
    "harmonique",
    "harmonic",
    "commande",
    "control",
    "automate",
    "automation",
    "convertisseur",
    "converter",
    "inverter",
    "onduleur",
    "photovoltaique",
    "solaire",
    "renewable",
    "renouvelable",
    "triphase",
    "triphasé",
    "triphasée",
    "grid",
}
THESIS_WORKFLOW_HINTS = {
    "workflow",
    "roadmap",
    "plan detaille",
    "plan dÃ©taille",
    "plan detaille chapitre",
    "outline",
    "chapter",
    "chapitre",
    "chapitres",
    "calendar",
    "calendrier",
    "timeline",
    "retroplanning",
    "retroplanning",
    "planning de redaction",
    "writing plan",
    "writing calendar",
    "research proposal",
    "proposal defense",
    "soutenance",
    "hypothese",
    "hypotheses",
    "contribution originale",
    "novelty",
}
DIAGNOSIS_HINTS = {
    "problem",
    "probleme",
    "problÃ¨me",
    "fault",
    "failure",
    "panne",
    "diagnostic",
    "diagnosis",
    "debug",
    "troubleshoot",
    "troubleshooting",
    "cause",
    "root cause",
    "pourquoi",
    "why",
    "trip",
    "trips",
    "declenche",
    "dÃ©clenche",
    "overheat",
    "surchauffe",
    "burn",
    "court-circuit",
    "short circuit",
    "voltage drop",
    "chute de tension",
    "instable",
    "unstable",
    "vibration",
    "losses too high",
}
REALTIME_HINTS = {
    "temps reel",
    "temps rÃ©el",
    "real time",
    "realtime",
    "stream",
    "streaming",
    "dashboard",
    "live plot",
    "live graph",
    "slider",
    "sliders",
    "interactive",
    "interactif",
    "courbe en direct",
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
    "time response",
    "temporal response",
    "reponse temporelle",
    "réponse temporelle",
    "reponse transitoire",
    "réponse transitoire",
    "charge",
    "discharge",
    "decay",
    "dimensionnement",
    "dimensionner",
    "dimensioning",
    "sizing",
    "interpretation",
    "interprétation",
    "oscillation",
    "overshoot",
    "damping",
    "amortissement",
    "resonance",
    "resonant",
    "capacitor",
    "capacitive",
    "inductor",
    "inductive",
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


class AcademicAssistantResponse(BaseModel):
    status: str
    source: str
    query: str
    normalized_query: str
    academic_level: str
    deliverable_type: str
    domain_focus: str
    title_suggestions: list[str] = Field(default_factory=list)
    problem_statement: str
    objectives: list[str] = Field(default_factory=list)
    research_questions: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    recommended_sources: list[str] = Field(default_factory=list)
    recommended_tools: list[str] = Field(default_factory=list)
    methodology: str
    outline: list[str] = Field(default_factory=list)
    writing_guidelines: list[str] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)
    originality_note: str
    next_steps: list[str] = Field(default_factory=list)


class ThesisChapter(BaseModel):
    chapter_number: int
    title: str
    objective: str
    key_sections: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)


class LiteratureStrategy(BaseModel):
    objective: str
    databases: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    screening_criteria: list[str] = Field(default_factory=list)
    evidence_matrix: list[str] = Field(default_factory=list)
    watch_routine: list[str] = Field(default_factory=list)


class MethodologyBlueprint(BaseModel):
    approach: str
    work_packages: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    inputs: list[str] = Field(default_factory=list)
    validation_metrics: list[str] = Field(default_factory=list)
    risk_controls: list[str] = Field(default_factory=list)


class WritingMilestone(BaseModel):
    phase: str
    week_range: str
    focus: str
    deliverables: list[str] = Field(default_factory=list)


class ThesisWorkflowResponse(BaseModel):
    status: str
    source: str
    query: str
    normalized_query: str
    academic_level: str
    deliverable_type: str
    domain_focus: str
    proposed_topic: str
    title_options: list[str] = Field(default_factory=list)
    problem_statement: str
    novelty_angle: str
    hypotheses: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(default_factory=list)
    research_questions: list[str] = Field(default_factory=list)
    chapter_plan: list[ThesisChapter] = Field(default_factory=list)
    literature_strategy: LiteratureStrategy
    methodology_blueprint: MethodologyBlueprint
    writing_calendar: list[WritingMilestone] = Field(default_factory=list)
    quality_checklist: list[str] = Field(default_factory=list)
    originality_note: str
    next_actions: list[str] = Field(default_factory=list)


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


class VisualizationAsset(BaseModel):
    title: str
    kind: str
    format: str
    url: str
    description: str
    signals: list[str] = Field(default_factory=list)


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
    interpretation: list[str] = Field(default_factory=list)
    visualizations: list[VisualizationAsset] = Field(default_factory=list)
    streaming: dict[str, Any] = Field(default_factory=dict)
    count: int
    series: list[SimulationPoint] = Field(default_factory=list)


class EngineeringDiagnosisResponse(BaseModel):
    status: str
    source: str
    query: str
    normalized_query: str
    domain: str
    system_family: str
    severity: str
    symptom_summary: str
    probable_causes: list[str] = Field(default_factory=list)
    quick_checks: list[str] = Field(default_factory=list)
    measurements_to_take: list[str] = Field(default_factory=list)
    equations_to_check: list[str] = Field(default_factory=list)
    recommended_tools: list[str] = Field(default_factory=list)
    simulation_candidates: list[str] = Field(default_factory=list)
    action_plan: list[str] = Field(default_factory=list)
    visual_support: list[str] = Field(default_factory=list)
    escalation_note: str


class RealtimeSimulationResponse(BaseModel):
    status: str
    source: str
    query: str
    summary: str
    dashboard_url: str
    stream_url: str
    recommended_signals: list[str] = Field(default_factory=list)
    pace_ms: int
    simulation: dict[str, Any] = Field(default_factory=dict)


class TelemetryFrame(BaseModel):
    sequence: int
    channel: str
    source: str
    timestamp_ms: int
    values: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TelemetryIngestRequest(BaseModel):
    channel: str
    values: dict[str, Any] = Field(default_factory=dict)
    source: str = "http"
    metadata: dict[str, Any] = Field(default_factory=dict)


class TelemetryIngestResponse(BaseModel):
    status: str
    source: str
    frame: TelemetryFrame
    retained_points: int


class ConnectorStatusResponse(BaseModel):
    status: str
    source: str
    mqtt: dict[str, Any] = Field(default_factory=dict)
    telemetry_channels: list[str] = Field(default_factory=list)
    total_points: int


class LiveConnectorResponse(BaseModel):
    status: str
    source: str
    query: str
    summary: str
    dashboard_url: str
    stream_url: str
    http_ingest_url: str
    websocket_ingest_url_template: str
    websocket_watch_url_template: str
    mqtt_status: dict[str, Any] = Field(default_factory=dict)
    modbus_example_url: str
    next_steps: list[str] = Field(default_factory=list)


class ModbusReadResponse(BaseModel):
    status: str
    source: str
    host: str
    port: int
    unit_id: int
    register_type: str
    address: int
    count: int
    channel: str
    values: dict[str, Any] = Field(default_factory=dict)
    frame: TelemetryFrame | None = None
    error: str = ""


app = FastAPI(
    title="Python Electrotechnique API",
    description="API FastAPI pour enrichir un assistant GPT avec WolframAlpha, arXiv, des simulations electrotechniques avancees, de la visualisation, de l'ingestion live MQTT/Modbus/WebSocket, du diagnostic d'ingenierie, un assistant academique et un workflow de these/TFE.",
    version="2.4.0",
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


@app.on_event("startup")
def startup_connectors() -> None:
    _start_mqtt_listener()


@app.on_event("shutdown")
def shutdown_connectors() -> None:
    _stop_mqtt_listener()


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


telemetry_lock = Lock()
telemetry_store: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=MAX_TELEMETRY_POINTS))
telemetry_sequence = 0
mqtt_client_instance = None
mqtt_runtime_state: dict[str, Any] = {
    "configured": bool(MQTT_BROKER_HOST),
    "library_available": mqtt is not None,
    "connected": False,
    "subscribed_topic": f"{MQTT_TOPIC_PREFIX}/#",
    "messages_received": 0,
    "last_error": "",
}


def _sanitize_channel_name(value: str | None) -> str:
    normalized = _normalize_text(value or "").lower()
    normalized = re.sub(r"[^a-z0-9:_./-]+", "-", normalized)
    normalized = normalized.strip("-./")
    return normalized or "default"


def _sanitize_signal_name(value: str | None) -> str:
    normalized = _normalize_text(value or "").lower().replace(" ", "_")
    normalized = re.sub(r"[^a-z0-9_./-]+", "_", normalized)
    normalized = normalized.strip("_./-")
    return normalized or "value"


def _make_json_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_make_json_safe(item) for item in value[:20]]
    if isinstance(value, dict):
        safe_dict = {}
        for key, item in list(value.items())[:20]:
            safe_dict[str(key)] = _make_json_safe(item)
        return safe_dict
    return str(value)


def _normalize_telemetry_values(values: Any) -> dict[str, Any]:
    if isinstance(values, dict):
        normalized = {}
        for key, value in values.items():
            signal_name = _sanitize_signal_name(str(key))
            normalized[signal_name] = _make_json_safe(value)
        return normalized or {"value": 0}
    return {"value": _make_json_safe(values)}


def _append_telemetry_frame(channel: str, source: str, values: Any, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    global telemetry_sequence

    safe_channel = _sanitize_channel_name(channel)
    safe_values = _normalize_telemetry_values(values)
    safe_metadata = _make_json_safe(metadata or {})

    with telemetry_lock:
        telemetry_sequence += 1
        frame = TelemetryFrame(
            sequence=telemetry_sequence,
            channel=safe_channel,
            source=_sanitize_signal_name(source),
            timestamp_ms=int(time.time() * 1000),
            values=safe_values,
            metadata=safe_metadata if isinstance(safe_metadata, dict) else {},
        ).model_dump()
        telemetry_store[safe_channel].append(frame)
        return frame


def _get_telemetry_frames(channel: str, limit: int = 200, after_sequence: int = 0) -> list[dict[str, Any]]:
    safe_channel = _sanitize_channel_name(channel)
    with telemetry_lock:
        frames = list(telemetry_store.get(safe_channel, []))
    if after_sequence > 0:
        frames = [frame for frame in frames if int(frame.get("sequence", 0)) > after_sequence]
    if limit > 0:
        frames = frames[-limit:]
    return frames


def _get_telemetry_channels() -> list[str]:
    with telemetry_lock:
        channels = sorted(telemetry_store.keys())
    return channels


def _get_total_telemetry_points() -> int:
    with telemetry_lock:
        return sum(len(points) for points in telemetry_store.values())


def _to_ws_base_url(base_url: str) -> str:
    if base_url.startswith("https://"):
        return "wss://" + base_url[len("https://") :]
    if base_url.startswith("http://"):
        return "ws://" + base_url[len("http://") :]
    return base_url


def _parse_mqtt_message(topic: str, payload_bytes: bytes) -> tuple[str, dict[str, Any], dict[str, Any]]:
    fallback_channel = _sanitize_channel_name(topic.replace(f"{MQTT_TOPIC_PREFIX}/", "", 1))
    raw_payload = payload_bytes.decode("utf-8", errors="ignore").strip()
    if not raw_payload:
        return fallback_channel, {"value": 0}, {"topic": topic}

    try:
        decoded = json.loads(raw_payload)
    except json.JSONDecodeError:
        return fallback_channel, {"value": raw_payload}, {"topic": topic}

    if isinstance(decoded, dict):
        channel = _sanitize_channel_name(decoded.get("channel") or fallback_channel)
        values = decoded.get("values")
        if values is None:
            values = {key: value for key, value in decoded.items() if key not in {"channel", "source", "metadata"}}
        metadata = decoded.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {"raw_metadata": _make_json_safe(metadata)}
        metadata["topic"] = topic
        return channel, _normalize_telemetry_values(values), metadata

    return fallback_channel, _normalize_telemetry_values(decoded), {"topic": topic}


def _build_mqtt_status() -> dict[str, Any]:
    return {
        "configured": mqtt_runtime_state.get("configured", False),
        "library_available": mqtt_runtime_state.get("library_available", False),
        "connected": mqtt_runtime_state.get("connected", False),
        "subscribed_topic": mqtt_runtime_state.get("subscribed_topic", ""),
        "messages_received": mqtt_runtime_state.get("messages_received", 0),
        "last_error": mqtt_runtime_state.get("last_error", ""),
    }


def _start_mqtt_listener() -> None:
    global mqtt_client_instance

    if mqtt_client_instance is not None:
        return
    if not MQTT_BROKER_HOST:
        mqtt_runtime_state["configured"] = False
        return
    if mqtt is None:
        mqtt_runtime_state["last_error"] = "La bibliotheque paho-mqtt n'est pas installee."
        return

    try:
        if hasattr(mqtt, "CallbackAPIVersion"):
            mqtt_client_instance = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="electrogpt-live-ingest")
        else:
            mqtt_client_instance = mqtt.Client(client_id="electrogpt-live-ingest")
        if MQTT_USERNAME:
            mqtt_client_instance.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD or None)

        def on_connect(client, userdata, flags, reason_code, properties=None):
            code = getattr(reason_code, "value", reason_code)
            mqtt_runtime_state["connected"] = int(code) == 0
            if mqtt_runtime_state["connected"]:
                mqtt_runtime_state["last_error"] = ""
                client.subscribe(f"{MQTT_TOPIC_PREFIX}/#")
            else:
                mqtt_runtime_state["last_error"] = f"Echec de connexion MQTT: code {code}"

        def on_disconnect(client, userdata, disconnect_flags, reason_code, properties=None):
            mqtt_runtime_state["connected"] = False
            code = getattr(reason_code, "value", reason_code)
            if code not in {0, None}:
                mqtt_runtime_state["last_error"] = f"MQTT deconnecte: code {code}"

        def on_message(client, userdata, msg):
            channel, values, metadata = _parse_mqtt_message(msg.topic, msg.payload)
            _append_telemetry_frame(channel, "mqtt", values, metadata)
            mqtt_runtime_state["messages_received"] = int(mqtt_runtime_state.get("messages_received", 0)) + 1

        mqtt_client_instance.on_connect = on_connect
        mqtt_client_instance.on_disconnect = on_disconnect
        mqtt_client_instance.on_message = on_message
        mqtt_client_instance.connect_async(MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_KEEPALIVE)
        mqtt_client_instance.loop_start()
    except Exception as exc:
        mqtt_runtime_state["last_error"] = str(exc)
        mqtt_client_instance = None


def _stop_mqtt_listener() -> None:
    global mqtt_client_instance

    if mqtt_client_instance is None:
        return
    try:
        mqtt_client_instance.loop_stop()
        mqtt_client_instance.disconnect()
    except Exception:
        pass
    mqtt_client_instance = None
    mqtt_runtime_state["connected"] = False


def _looks_like_live_connector_request(query: str) -> bool:
    lowered_query = query.lower()
    return any(
        token in lowered_query
        for token in {
            "mqtt",
            "modbus",
            "websocket",
            "web socket",
            "plc",
            "automate",
            "capteur",
            "sensor",
            "telemetry",
            "telemetrie",
            "tÃ©lÃ©metrie",
            "live data",
            "donnees temps reel",
            "donnÃ©es temps rÃ©el",
        }
    )


def _build_live_connector_payload(query: str, base_url: str) -> dict[str, Any]:
    ws_base = _to_ws_base_url(base_url)
    example_channel = "atelier-ligne-1"
    return LiveConnectorResponse(
        status="ok",
        source="live-connectors",
        query=query,
        summary=(
            "Passerelle live prete pour capteurs, automate ou SCADA. "
            "Tu peux pousser des donnees en HTTP ou WebSocket, lire du Modbus TCP a la demande "
            "et brancher un broker MQTT pour ingestion automatique."
        ),
        dashboard_url=f"{base_url}/live-dashboard?channel={example_channel}",
        stream_url=f"{base_url}/telemetry-stream?channel={example_channel}",
        http_ingest_url=f"{base_url}/telemetry-ingest",
        websocket_ingest_url_template=f"{ws_base}/ws/telemetry-ingest/{{channel}}",
        websocket_watch_url_template=f"{ws_base}/ws/telemetry-watch/{{channel}}",
        mqtt_status=_build_mqtt_status(),
        modbus_example_url=(
            f"{base_url}/modbus-read?host=192.168.1.10&port=502&unit_id=1&address=0&count=4"
            f"&register_type=holding&channel={example_channel}"
        ),
        next_steps=[
            "Creer un canal logique par machine, tableau ou sous-systeme.",
            "Pousser les mesures via POST /telemetry-ingest ou WebSocket /ws/telemetry-ingest/{channel}.",
            "Ouvrir /live-dashboard?channel=<canal> pour visualiser les signaux entrants.",
            "Configurer MQTT_BROKER_HOST pour activer l'abonnement automatique au broker MQTT.",
            "Utiliser /modbus-read pour interroger un automate ou compteur Modbus TCP.",
        ],
    ).model_dump()


def _build_live_connector_brief(payload: dict[str, Any]) -> str:
    return (
        "Passerelle live prete. Le detail contient les URLs HTTP, WebSocket, dashboard, flux telemetry, "
        "etat MQTT et exemple Modbus pour connecter des capteurs ou un automate."
    )


def _build_connector_status_payload() -> dict[str, Any]:
    return ConnectorStatusResponse(
        status="ok",
        source="live-connectors",
        mqtt=_build_mqtt_status(),
        telemetry_channels=_get_telemetry_channels(),
        total_points=_get_total_telemetry_points(),
    ).model_dump()


def _decode_modbus_register(value: int, signed: bool) -> int:
    if not signed:
        return value
    return value - 65536 if value >= 32768 else value


def _read_modbus_payload(
    *,
    host: str,
    port: int,
    unit_id: int,
    address: int,
    count: int,
    register_type: str,
    channel: str,
    labels: list[str] | None,
    scale: float,
    signed: bool,
) -> dict[str, Any]:
    if ModbusTcpClient is None:
        return ModbusReadResponse(
            status="error",
            source="modbus",
            host=host,
            port=port,
            unit_id=unit_id,
            register_type=register_type,
            address=address,
            count=count,
            channel=channel,
            values={},
            frame=None,
            error="La bibliotheque pymodbus n'est pas installee.",
        ).model_dump()

    if not host or port <= 0 or count <= 0:
        return ModbusReadResponse(
            status="error",
            source="modbus",
            host=host,
            port=port,
            unit_id=unit_id,
            register_type=register_type,
            address=address,
            count=count,
            channel=channel,
            values={},
            frame=None,
            error="Parametres Modbus invalides.",
        ).model_dump()

    safe_channel = _sanitize_channel_name(channel or f"modbus-{host}-{unit_id}")
    client = ModbusTcpClient(host=host, port=port)
    try:
        if not client.connect():
            return ModbusReadResponse(
                status="error",
                source="modbus",
                host=host,
                port=port,
                unit_id=unit_id,
                register_type=register_type,
                address=address,
                count=count,
                channel=safe_channel,
                values={},
                frame=None,
                error="Connexion Modbus TCP impossible.",
            ).model_dump()

        if register_type == "input":
            result = client.read_input_registers(address=address, count=count, slave=unit_id)
        else:
            result = client.read_holding_registers(address=address, count=count, slave=unit_id)

        if result is None or result.isError():
            return ModbusReadResponse(
                status="error",
                source="modbus",
                host=host,
                port=port,
                unit_id=unit_id,
                register_type=register_type,
                address=address,
                count=count,
                channel=safe_channel,
                values={},
                frame=None,
                error="Lecture Modbus invalide ou incomplete.",
            ).model_dump()

        raw_registers = getattr(result, "registers", [])
        labels = labels or []
        values = {}
        for index, register in enumerate(raw_registers):
            key = labels[index] if index < len(labels) and labels[index] else f"register_{address + index}"
            values[_sanitize_signal_name(key)] = _round_float(_decode_modbus_register(int(register), signed) * scale)

        frame = _append_telemetry_frame(
            safe_channel,
            "modbus",
            values,
            {
                "host": host,
                "port": port,
                "unit_id": unit_id,
                "register_type": register_type,
                "address": address,
                "count": count,
            },
        )
        return ModbusReadResponse(
            status="ok",
            source="modbus",
            host=host,
            port=port,
            unit_id=unit_id,
            register_type=register_type,
            address=address,
            count=count,
            channel=safe_channel,
            values=values,
            frame=TelemetryFrame(**frame),
            error="",
        ).model_dump()
    except Exception as exc:
        return ModbusReadResponse(
            status="error",
            source="modbus",
            host=host,
            port=port,
            unit_id=unit_id,
            register_type=register_type,
            address=address,
            count=count,
            channel=safe_channel,
            values={},
            frame=None,
            error=str(exc),
        ).model_dump()
    finally:
        try:
            client.close()
        except Exception:
            pass

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


def _looks_like_academic_request(query: str) -> bool:
    lowered_query = query.lower()
    return _contains_any(lowered_query, ACADEMIC_HINTS)


def _looks_like_thesis_workflow_request(query: str) -> bool:
    lowered_query = query.lower()
    if _contains_any(lowered_query, THESIS_WORKFLOW_HINTS) and _looks_like_academic_request(query):
        return True
    return bool(
        re.search(r"plan\s+(detaille|de these|de thÃ¨se|de memoire|de mÃ©moire)", lowered_query)
        or re.search(r"chapitre|calendar|calendrier|timeline|workflow|roadmap", lowered_query)
    ) and _looks_like_academic_request(query)


def _infer_academic_level(query: str) -> str:
    lowered_query = query.lower()
    if "these" in lowered_query or "thèse" in lowered_query or "thesis" in lowered_query:
        return "these"
    if "memoire" in lowered_query or "mémoire" in lowered_query:
        return "memoire"
    if "pfe" in lowered_query:
        return "pfe"
    if "tfe" in lowered_query:
        return "tfe"
    return "projet-academique"


def _infer_deliverable_type(query: str) -> str:
    lowered_query = query.lower()
    if "sujet" in lowered_query or "theme" in lowered_query or "thème" in lowered_query:
        return "topic-ideation"
    if "guide de recherche" in lowered_query or "research guide" in lowered_query or "bibliographie" in lowered_query or "literature review" in lowered_query:
        return "research-guide"
    if "methodologie" in lowered_query or "méthodologie" in lowered_query or "methodology" in lowered_query:
        return "methodology-plan"
    if "plan" in lowered_query or "chapitre" in lowered_query or "chapter" in lowered_query or "outline" in lowered_query:
        return "writing-outline"
    return "full-thesis-support"


def _extract_academic_focus(query: str) -> str:
    lowered_query = query.lower()
    if any(term in lowered_query for term in {"electrotechnique", "lectrotechnique", "electrical engineering"}) and not any(
        term in lowered_query for term in {"renouvelable", "renewable", "solaire", "transform", "relais", "relay", "protection", "motor", "moteur", "microreseau", "microgrid"}
    ):
        return "ingenierie electrotechnique"
    cleaned = re.sub(r"[^a-z0-9àâçéèêëîïôûùüÿñæœ\s-]", " ", lowered_query)
    for fragment in [
        "donner",
        "recent",
        "recents",
        "récents",
        "pertinent",
        "pertinents",
        "proposer",
        "propose",
        "liste",
        "3",
        "trois",
        "sujet",
        "sujets",
        "theme",
        "thème",
        "guide de recherche",
        "plan de these",
        "plan de thèse",
        "plan detaille",
        "plan détaillé",
        "tfe",
        "pfe",
        "memoire",
        "mémoire",
        "these",
        "thèse",
        "thesis",
        "sur",
        "pour",
        "de",
        "en",
        "projet",
        "fin",
        "cycle",
    ]:
        cleaned = cleaned.replace(fragment, " ")
    cleaned = _normalize_text(cleaned)
    if "electrotech" in lowered_query and not cleaned:
        return "ingenierie electrotechnique"
    if any(term in lowered_query for term in {"renouvelable", "renewable", "solaire", "photovolta", "microreseau", "microgrid"}):
        return "integration des energies renouvelables et microreseaux"
    if "transform" in lowered_query:
        return "transformateurs de puissance et de distribution"
    if "relais" in lowered_query or "relay" in lowered_query or "protection" in lowered_query:
        return "protection des relais et selectivite"
    if "motor" in lowered_query or "moteur" in lowered_query:
        return "machines electriques et commande de moteurs"
    if "quality" in lowered_query or "qualite" in lowered_query or "harmon" in lowered_query:
        return "qualite d energie et compensation"
    return cleaned or "ingenierie electrotechnique"


def _extract_meaningful_topic_tokens(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9àâçéèêëîïôûùüÿñæœ]+", text.lower())
    return [token for token in tokens if len(token) > 2 and token not in ACADEMIC_GENERIC_TOKENS]


def _needs_academic_clarification(query: str, domain_focus: str) -> bool:
    lowered_query = query.lower()
    meaningful_query_tokens = _extract_meaningful_topic_tokens(lowered_query)
    meaningful_focus_tokens = _extract_meaningful_topic_tokens(domain_focus)
    has_engineering_signal = any(token in lowered_query for token in ENGINEERING_TOPIC_TOKENS)
    has_subject_pattern = bool(re.search(r"\b(sur|about|on|for)\b", lowered_query))
    if has_engineering_signal or has_subject_pattern:
        return False
    if len(meaningful_focus_tokens) >= 2:
        return False
    return len(meaningful_query_tokens) < 3


def _build_academic_clarification_guidance(query: str, deliverable_type: str) -> dict[str, Any]:
    return {
        "status": "needs-input",
        "source": "academic-assistant",
        "query": query,
        "normalized_query": _normalize_text(query),
        "academic_level": _infer_academic_level(query),
        "deliverable_type": deliverable_type,
        "domain_focus": "a preciser",
        "title_suggestions": [
            "Donne d'abord le sujet exact ou le domaine technique du TFE",
            "Ajoute ensuite la problematique ou l'objectif principal",
            "Precise enfin si tu veux un plan, une bibliographie ou une methodologie",
        ],
        "problem_statement": (
            "La demande academique est trop vague pour produire un cadrage fiable. "
            "L'action GPT ne recoit pas automatiquement le contenu du PDF joint: elle ne voit que le texte du message transmis."
        ),
        "objectives": [
            "Fournir le sujet exact ou le titre provisoire.",
            "Donner la problematique, meme provisoire.",
            "Indiquer le livrable attendu: plan detaille, bibliographie, methodologie ou workflow complet.",
        ],
        "research_questions": [
            "Quel est le sujet technique exact ?",
            "Quel probleme veux-tu traiter ?",
            "Quel type d'aide attends-tu maintenant ?",
        ],
        "keywords": ["tfe", "memoire", "these", "sujet", "problematique"],
        "search_queries": [],
        "recommended_sources": [
            "Si le sujet est deja connu, renvoie-le en texte dans la requete vers /gpt-tool.",
        ],
        "recommended_tools": [
            "Le GPT peut lire le PDF dans la conversation, mais l'action externe a besoin d'un resume texte explicite.",
        ],
        "methodology": (
            "Extrais du document le sujet, la problematique et les objectifs, puis relance l'action avec ces elements."
        ),
        "outline": [
            "Sujet exact",
            "Problematique",
            "Objectif principal",
            "Type de livrable attendu",
        ],
        "writing_guidelines": [
            "Eviter les requetes vagues du type 'c'est un TFE'.",
            "Toujours inclure le domaine technique ou le titre provisoire dans la requete.",
        ],
        "milestones": [
            "1. Identifier le sujet dans le document.",
            "2. Resumer en 2 a 4 lignes le probleme traite.",
            "3. Relancer l'action avec une demande precise.",
        ],
        "originality_note": "Le cadrage doit partir d'un sujet technique explicite, pas d'une formulation generique.",
        "next_steps": [
            "Exemple: 'Plan detaille de TFE sur la qualite d'energie dans une installation industrielle'.",
            "Exemple: 'Workflow complet de memoire sur la protection des relais numeriques'.",
        ],
    }


def _generate_academic_titles(domain_focus: str) -> list[str]:
    lowered_focus = domain_focus.lower()
    if "renouvelable" in lowered_focus or "microreseau" in lowered_focus or "microgrid" in lowered_focus:
        return [
            "Integration optimale des energies renouvelables dans un microreseau intelligent a faible tension",
            "Commande et gestion energetique d'un systeme hybride photovoltaïque-batterie pour un site isole",
            "Etude techno-economique de l'insertion des sources renouvelables dans un reseau de distribution",
        ]
    if "transform" in lowered_focus:
        return [
            "Analyse et reduction des pertes dans les transformateurs de distribution soumis a des charges non lineaires",
            "Surveillance thermique et maintenance predictive des transformateurs de puissance",
            "Impact de la penetration des energies renouvelables sur le dimensionnement des transformateurs MT/BT",
        ]
    if "relais" in lowered_focus or "protection" in lowered_focus:
        return [
            "Coordination optimale des relais de protection dans un reseau de distribution moderne",
            "Analyse de la selectivite des protections dans un microreseau comportant des convertisseurs de puissance",
            "Contribution a l'amelioration de la rapidite et de la fiabilite des protections electriques industrielles",
        ]
    if "moteur" in lowered_focus or "machines" in lowered_focus:
        return [
            "Commande robuste d'un moteur electrique pour l'amelioration du rendement energetique",
            "Diagnostic de defauts des machines tournantes par analyse des signaux electriques",
            "Comparaison des strategies de commande des moteurs electriques dans les applications industrielles",
        ]
    return [
        f"Conception et optimisation d'une etude appliquee sur {domain_focus}",
        f"Analyse technico-economique et modelisation de {domain_focus}",
        f"Supervision, commande et maintenance intelligente pour {domain_focus}",
    ]


def _build_academic_assistant_payload(query: str) -> dict[str, Any]:
    normalized_query = _normalize_text(query)
    academic_level = _infer_academic_level(normalized_query)
    deliverable_type = _infer_deliverable_type(normalized_query)
    domain_focus = _extract_academic_focus(normalized_query)
    if _needs_academic_clarification(normalized_query, domain_focus):
        return _build_academic_clarification_guidance(query, deliverable_type)
    title_suggestions = _generate_academic_titles(domain_focus)

    problem_statement = (
        f"Le sujet '{domain_focus}' presente un enjeu scientifique et industriel en ingenierie electrotechnique. "
        "Le travail doit clarifier le probleme technique, identifier les limites des solutions existantes, "
        "et proposer une approche originale, justifiee et verifiable."
    )
    objectives = [
        f"Caracteriser l'etat actuel des connaissances et des pratiques sur {domain_focus}.",
        "Identifier les verrous techniques, economiques ou operationnels qui motivent le travail.",
        "Proposer une methode d'etude, de modelisation, de simulation ou d'experimentation adaptee.",
        "Produire des resultats exploitables avec analyse critique, limites et perspectives.",
    ]
    research_questions = [
        f"Quels sont les principaux problemes techniques observes dans le domaine {domain_focus} ?",
        "Quelles methodes ou architectures existantes sont les plus pertinentes et quelles sont leurs limites ?",
        "Quelle contribution originale et mesurable peut etre apportee dans le cadre d'un TFE, memoire ou these ?",
    ]
    keywords = [
        domain_focus,
        "electrical engineering",
        "power systems",
        "power electronics",
        "control",
        "optimization",
        "simulation",
        "design",
    ]
    search_queries = [
        f"{domain_focus} electrical engineering",
        f"{domain_focus} power systems",
        f"{domain_focus} methodology OR model OR simulation",
        f"{domain_focus} recent review OR survey",
    ]
    recommended_sources = [
        "arXiv pour les preprints techniques et approches recentes",
        "Crossref pour retrouver des articles, DOI et journaux pertinents",
        "Google Scholar pour elargir la bibliographie et suivre les citations",
        "IEEE Xplore, ScienceDirect et SpringerLink si l'utilisateur a acces institutionnel",
    ]
    recommended_tools = [
        "Zotero ou Mendeley pour la bibliographie",
        "Overleaf ou Word pour la redaction structuree",
        "Python, MATLAB/Simulink ou ETAP selon la nature du sujet",
        "Ton action /gpt-tool pour rechercher des articles, lancer des calculs et preparer le cadrage du sujet",
    ]
    methodology = (
        "Commence par une revue de litterature ciblee, formule une problematique precise, definis les hypotheses et indicateurs "
        "de performance, puis choisis une methode de validation: simulation, experimentation, etude comparative ou prototype. "
        "La methode doit permettre de comparer l'etat de l'art a ta proposition et de discuter les limites de maniere honnete."
    )
    outline = [
        "Chapitre 1: Introduction generale, contexte, problematique, objectifs, hypotheses et demarche.",
        "Chapitre 2: Etat de l'art et bases theoriques reliees au sujet.",
        "Chapitre 3: Materiels, modeles, methodologie et environnement d'etude.",
        "Chapitre 4: Resultats, analyses, comparaison avec la litterature et discussion critique.",
        "Chapitre 5: Conclusion generale, limites, recommandations et perspectives.",
    ]
    writing_guidelines = [
        "Rediger chaque chapitre avec une idee directrice claire et des transitions explicites.",
        "Justifier les choix techniques avec des sources et non avec des affirmations vagues.",
        "Distinguer clairement ce qui vient de la litterature, de la simulation et de ta contribution.",
        "Conserver un style original, analytique et coherent avec les preuves obtenues.",
    ]
    milestones = [
        "Semaine 1-2: cadrage du sujet, problematique, objectifs, mots-cles et premier corpus bibliographique.",
        "Semaine 3-4: lecture critique des sources, synthese de l'etat de l'art et schema du memoire.",
        "Semaine 5-7: modelisation, simulations, experiences ou collecte de donnees.",
        "Semaine 8-10: interpretation des resultats, redaction technique et comparaison avec la litterature.",
        "Semaine 11-12: finalisation, relecture, bibliographie, annexes et preparation de la defense.",
    ]
    originality_note = (
        "Le memoire ou la these doit rester original. Cet assistant sert a structurer le travail, proposer des pistes "
        "et accelerer la recherche, mais le contenu final doit etre personnalise, verifie et redige par l'etudiant ou le chercheur."
    )
    next_steps = [
        "Choisir un angle precis et limiter le sujet a une question realiste.",
        "Demander ensuite une recherche bibliographique ciblee avec /gpt-tool ou /arxiv.",
        "Demander un plan detaille chapitre par chapitre si le sujet est valide.",
        "Demander une methode, un protocole experimental ou une grille d'analyse adaptee au sujet.",
    ]

    return AcademicAssistantResponse(
        status="ok",
        source="academic-assistant",
        query=query,
        normalized_query=normalized_query,
        academic_level=academic_level,
        deliverable_type=deliverable_type,
        domain_focus=domain_focus,
        title_suggestions=title_suggestions,
        problem_statement=problem_statement,
        objectives=objectives,
        research_questions=research_questions,
        keywords=keywords,
        search_queries=search_queries,
        recommended_sources=recommended_sources,
        recommended_tools=recommended_tools,
        methodology=methodology,
        outline=outline,
        writing_guidelines=writing_guidelines,
        milestones=milestones,
        originality_note=originality_note,
        next_steps=next_steps,
    ).model_dump()


def _build_thesis_chapter_plan(domain_focus: str, academic_level: str) -> list[dict[str, Any]]:
    chapters = [
        ThesisChapter(
            chapter_number=1,
            title="Introduction generale et cadrage du sujet",
            objective="Poser le contexte, la problematique, les objectifs, les hypotheses et la valeur attendue du travail.",
            key_sections=[
                "Contexte industriel et scientifique",
                "Problematique et justification du sujet",
                "Objectifs general et specifiques",
                "Hypotheses de travail",
                "Organisation du document",
            ],
            expected_outputs=[
                "Question centrale validee",
                "Perimetre du sujet clairement delimite",
                "Architecture generale du manuscrit",
            ],
        ).model_dump(),
        ThesisChapter(
            chapter_number=2,
            title="Etat de l'art et revue critique de la litterature",
            objective=f"Comparer les approches existantes sur {domain_focus}, identifier les indicateurs utilises et faire ressortir un gap de recherche defensible.",
            key_sections=[
                "Definitions et concepts cles",
                "Synthese des approches existantes",
                "Comparaison des methodes, outils et resultats",
                "Limites de l'etat de l'art",
                "Gap scientifique ou technique retenu",
            ],
            expected_outputs=[
                "Corpus bibliographique structure",
                "Tableau comparatif des references majeures",
                "Gap de recherche formule proprement",
            ],
        ).model_dump(),
        ThesisChapter(
            chapter_number=3,
            title="Modelisation, architecture et methodologie",
            objective="Decrire le cadre methodologique, les hypotheses de modelisation, les donnees et les outils de validation.",
            key_sections=[
                "Architecture du systeme ou scenario d'etude",
                "Hypotheses, variables et contraintes",
                "Modeles mathematiques ou physiques",
                "Protocoles de simulation, test ou mesure",
                "Criteres d'evaluation",
            ],
            expected_outputs=[
                "Modele ou protocole reproductible",
                "Jeu de parametres et hypotheses explicites",
                "Plan de validation",
            ],
        ).model_dump(),
        ThesisChapter(
            chapter_number=4,
            title="Implementation, simulations ou experimentation",
            objective="Executer la methode retenue, construire les cas d'etude et collecter les resultats exploitables.",
            key_sections=[
                "Description de l'environnement logiciel ou experimental",
                "Cas de charge ou scenarios de test",
                "Execution des simulations ou mesures",
                "Collecte et mise en forme des donnees",
            ],
            expected_outputs=[
                "Jeu de resultats coherents",
                "Figures, tableaux et courbes exploitables",
                "Trace des essais et des parametres",
            ],
        ).model_dump(),
        ThesisChapter(
            chapter_number=5,
            title="Analyse, discussion critique et contribution",
            objective="Interpreter les resultats, mesurer la valeur de la contribution et discuter les limites du travail.",
            key_sections=[
                "Analyse des performances",
                "Comparaison avec la litterature",
                "Discussion des compromis techniques et economiques",
                "Limites de l'etude",
                "Contribution originale retenue",
            ],
            expected_outputs=[
                "Discussion argumentee",
                "Contribution originale explicite",
                "Limites et perspectives honnetes",
            ],
        ).model_dump(),
    ]

    if academic_level == "these":
        chapters.append(
            ThesisChapter(
                chapter_number=6,
                title="Conclusion generale, recommandations et perspectives",
                objective="Clore le manuscrit, ouvrir les perspectives scientifiques et preciser les prolongements possibles.",
                key_sections=[
                    "Synthese des apports",
                    "Recommandations techniques",
                    "Perspectives de recherche",
                    "Valorisation possible des resultats",
                ],
                expected_outputs=[
                    "Synthese executive du travail",
                    "Recommandations applicables",
                    "Liste de travaux futurs",
                ],
            ).model_dump()
        )
    else:
        chapters.append(
            ThesisChapter(
                chapter_number=6,
                title="Conclusion generale et recommandations",
                objective="Resumer les acquis du travail et proposer des suites realistes pour un TFE ou memoire.",
                key_sections=[
                    "Synthese des resultats",
                    "Reponse a la problematique",
                    "Recommandations de mise en oeuvre",
                    "Perspectives courtes",
                ],
                expected_outputs=[
                    "Conclusion exploitable pour la defense",
                    "Recommandations techniques claires",
                    "Perspectives realistes",
                ],
            ).model_dump()
        )

    return chapters


def _build_thesis_literature_strategy(domain_focus: str) -> dict[str, Any]:
    return LiteratureStrategy(
        objective=f"Constituer une bibliographie ciblee, recente et defendable sur {domain_focus}.",
        databases=[
            "IEEE Xplore",
            "Scopus ou Web of Science",
            "ScienceDirect",
            "SpringerLink",
            "Crossref",
            "arXiv",
            "Google Scholar pour les citations entrantes et sortantes",
        ],
        search_queries=[
            f"\"{domain_focus}\" electrical engineering",
            f"\"{domain_focus}\" simulation OR modelling OR control",
            f"\"{domain_focus}\" optimization OR performance OR reliability",
            f"\"{domain_focus}\" review OR survey OR state of the art",
        ],
        screening_criteria=[
            "Prioriser les sources des 5 a 7 dernieres annees, sauf les references fondatrices.",
            "Conserver les articles avec methode explicite, donnees ou metriques comparables.",
            "Exclure les travaux trop eloignes du perimetre electrotechnique retenu.",
            "Noter systematiquement le probleme, la methode, les donnees, les metriques et les limites.",
        ],
        evidence_matrix=[
            "Reference complete",
            "Probleme traite",
            "Methode / modele",
            "Jeu de donnees ou cas d'etude",
            "Metriques de performance",
            "Limites identifiees",
            "Gap exploitable pour ton travail",
        ],
        watch_routine=[
            "Bloquer 2 seances par semaine pour la veille et la mise a jour de la bibliographie.",
            "Ajouter des alertes Google Scholar / Crossref sur les mots-cles principaux.",
            "Mettre a jour un tableau de suivi des references lues, citees et a relire.",
        ],
    ).model_dump()


def _build_thesis_methodology_blueprint(domain_focus: str) -> dict[str, Any]:
    lowered_focus = domain_focus.lower()
    tools = ["Python", "Jupyter", "Zotero ou Mendeley"]
    if "transform" in lowered_focus or "relais" in lowered_focus or "protection" in lowered_focus:
        tools.extend(["MATLAB/Simulink", "ETAP ou DIgSILENT"])
    elif "motor" in lowered_focus or "moteur" in lowered_focus:
        tools.extend(["MATLAB/Simulink", "PSIM ou LTspice"])
    elif "microreseau" in lowered_focus or "renouvelable" in lowered_focus:
        tools.extend(["MATLAB/Simulink", "HOMER ou DIgSILENT"])
    else:
        tools.extend(["MATLAB/Simulink ou LTspice", "Excel ou Power BI pour la synthese"])

    return MethodologyBlueprint(
        approach=(
            "Approche mixte basee sur revue de litterature, modelisation, simulations parametriques, "
            "analyse comparative et discussion critique des limites."
        ),
        work_packages=[
            "WP1: cadrage du sujet, perimetre et gap de recherche",
            "WP2: corpus bibliographique et matrice de synthese",
            "WP3: modelisation du systeme et definition des hypotheses",
            "WP4: campagnes de simulation ou essais",
            "WP5: analyse, redaction et consolidation des apports",
        ],
        tools=tools,
        inputs=[
            f"Parametres techniques representatifs de {domain_focus}",
            "Hypotheses de fonctionnement et contraintes de dimensionnement",
            "Scenarios nominaux, defaut et sensibilite si applicable",
            "Corpus bibliographique trace et annote",
        ],
        validation_metrics=[
            "Precision ou erreur relative selon le cas d'etude",
            "Rendement, pertes, stabilite, temps de reponse ou qualite de regulation",
            "Robustesse aux variations parametriques",
            "Comparaison avec au moins une reference ou solution de base",
        ],
        risk_controls=[
            "Limiter le sujet a un cas d'usage concret pour eviter un manuscrit trop large.",
            "Definir des hypotheses testables avant les simulations.",
            "Conserver un journal de version des modeles et des resultats.",
            "Valider tot le plan avec l'encadreur avant de rediger massivement.",
        ],
    ).model_dump()


def _build_thesis_writing_calendar(academic_level: str) -> list[dict[str, Any]]:
    if academic_level == "these":
        milestones = [
            ("Phase 1", "Semaines 1-2", "Cadrage scientifique", ["Sujet finalise", "Problematique", "Objectifs", "Hypotheses"]),
            ("Phase 2", "Semaines 3-5", "Revue de litterature", ["Matrice bibliographique", "Synthese critique", "Gap formule"]),
            ("Phase 3", "Semaines 6-8", "Modelisation et architecture", ["Modeles", "Hypotheses retenues", "Plan experimental"]),
            ("Phase 4", "Semaines 9-12", "Simulations ou experimentation", ["Cas d'etude", "Resultats bruts", "Scripts ou modeles"]),
            ("Phase 5", "Semaines 13-15", "Analyse et discussion", ["Tableaux comparatifs", "Discussion critique", "Contribution formelle"]),
            ("Phase 6", "Semaines 16-18", "Redaction des chapitres techniques", ["Chapitres 2 a 5 rediges", "Figures nettoyees"]),
            ("Phase 7", "Semaines 19-20", "Conclusion et harmonisation", ["Conclusion generale", "Perspectives", "References homogenisees"]),
        ]
    else:
        milestones = [
            ("Phase 1", "Semaines 1-2", "Choix du sujet et cadrage", ["Sujet valide", "Problematique", "Objectifs", "Plan initial"]),
            ("Phase 2", "Semaines 3-4", "Etat de l'art", ["Corpus bibliographique", "Tableau comparatif", "Gap identifie"]),
            ("Phase 3", "Semaines 5-7", "Methodologie et modelisation", ["Modele", "Hypotheses", "Protocoles"]),
            ("Phase 4", "Semaines 8-10", "Simulations, essais et collecte", ["Resultats", "Courbes", "Tableaux"]),
            ("Phase 5", "Semaines 11-12", "Analyse et redaction", ["Discussion", "Conclusion", "Diaporama de defense"]),
        ]

    return [
        WritingMilestone(
            phase=phase,
            week_range=week_range,
            focus=focus,
            deliverables=deliverables,
        ).model_dump()
        for phase, week_range, focus, deliverables in milestones
    ]


def _build_thesis_novelty_angle(domain_focus: str) -> str:
    lowered_focus = domain_focus.lower()
    if "renouvelable" in lowered_focus or "microreseau" in lowered_focus:
        return "Combiner gestion energetique, robustesse reseau et contraintes locales d'exploitation pour proposer une architecture ou une strategie mieux adaptee que les approches generalistes."
    if "transform" in lowered_focus:
        return "Coupler analyse des pertes, contraintes thermiques et scenarios de charges non lineaires afin de produire des recommandations de dimensionnement ou de maintenance plus fines."
    if "relais" in lowered_focus or "protection" in lowered_focus:
        return "Montrer comment une logique de protection plus adaptive peut ameliorer selectivite, rapidite et fiabilite dans des reseaux modernes avec convertisseurs ou production distribuee."
    if "moteur" in lowered_focus or "machines" in lowered_focus:
        return "Articuler commande, diagnostic et performance energetique pour proposer une methode plus robuste et plus facilement deployable en contexte industriel."
    return "Ancrer la contribution dans un cas d'usage electrotechnique realiste, avec des metriques claires et une comparaison honnete a l'etat de l'art."


def _build_thesis_clarification_guidance(query: str, deliverable_type: str) -> dict[str, Any]:
    normalized_query = _normalize_text(query)
    return ThesisWorkflowResponse(
        status="needs-input",
        source="thesis-workflow",
        query=query,
        normalized_query=normalized_query,
        academic_level=_infer_academic_level(normalized_query),
        deliverable_type=deliverable_type,
        domain_focus="a preciser",
        proposed_topic="Sujet a preciser avant generation du workflow",
        title_options=[
            "Donne le sujet exact ou le titre provisoire",
            "Ajoute la problematique ou l'objectif principal",
            "Indique si tu veux un plan detaille, une methodologie ou un workflow complet",
        ],
        problem_statement=(
            "Le workflow de these ou de TFE ne peut pas etre produit de maniere fiable sans sujet explicite. "
            "Le PDF joint dans ChatGPT n'est pas transmis tel quel a l'action externe."
        ),
        novelty_angle="A definir apres identification du sujet et du gap technique reel.",
        hypotheses=[
            "Le sujet doit etre formule en texte dans la requete.",
            "La problematique doit etre identifiable en une ou deux phrases.",
        ],
        objectives=[
            "Recuperer le sujet exact depuis le document ou le message utilisateur.",
            "Preciser la problematique et le type de livrable attendu.",
            "Relancer ensuite la generation du workflow complet.",
        ],
        research_questions=[
            "Quel est le sujet exact ?",
            "Quel est le probleme technique traite ?",
            "Quel livrable veux-tu maintenant ?",
        ],
        chapter_plan=[
            ThesisChapter(
                chapter_number=1,
                title="Clarification du sujet",
                objective="Identifier le titre, la problematique et le perimetre avant toute redaction detaillee.",
                key_sections=["Sujet exact", "Problematique", "Perimetre", "Livrable attendu"],
                expected_outputs=["Sujet reformule", "Question centrale", "Consignes pour la prochaine requete"],
            )
        ],
        literature_strategy=LiteratureStrategy(
            objective="Attendre la clarification du sujet avant de lancer une vraie strategie bibliographique.",
            databases=[],
            search_queries=[],
            screening_criteria=[],
            evidence_matrix=[],
            watch_routine=[],
        ),
        methodology_blueprint=MethodologyBlueprint(
            approach="Clarification d'entree avant generation du workflow complet.",
            work_packages=["Extraire le sujet du document", "Resumer la problematique", "Relancer l'action avec un texte explicite"],
            tools=["ChatGPT pour lire le PDF dans la conversation", "/gpt-tool pour le workflow une fois le sujet explicite"],
            inputs=["Sujet exact", "Problematique", "Type de livrable"],
            validation_metrics=["Sujet suffisamment precis pour produire un plan defendable"],
            risk_controls=["Ne pas inventer un sujet a partir d'une requete trop vague"],
        ),
        writing_calendar=[
            WritingMilestone(
                phase="Clarification",
                week_range="Immediate",
                focus="Transformer le contenu du document en sujet et problematique explicites.",
                deliverables=["Sujet reformule", "Problematique resumee", "Nouvelle requete exploitable"],
            )
        ],
        quality_checklist=[
            "Le sujet est explicite.",
            "La problematique est explicite.",
            "Le livrable attendu est explicite.",
        ],
        originality_note="Le workflow doit partir d'un sujet reel et explicite, pas d'une requete generique.",
        next_actions=[
            "Exemple: 'Plan detaille de TFE sur la protection des relais numeriques'.",
            "Exemple: 'Workflow complet de memoire sur la qualite d energie dans une usine industrielle'.",
        ],
    ).model_dump()


def _build_thesis_workflow_payload(query: str) -> dict[str, Any]:
    normalized_query = _normalize_text(query)
    academic_level = _infer_academic_level(normalized_query)
    deliverable_type = _infer_deliverable_type(normalized_query)
    domain_focus = _extract_academic_focus(normalized_query)
    if _needs_academic_clarification(normalized_query, domain_focus):
        return _build_thesis_clarification_guidance(query, deliverable_type)
    title_options = _generate_academic_titles(domain_focus)
    proposed_topic = title_options[0]
    novelty_angle = _build_thesis_novelty_angle(domain_focus)

    problem_statement = (
        f"Dans le domaine '{domain_focus}', les solutions existantes restent souvent limitees par des hypotheses simplificatrices, "
        "des contextes de validation trop etroits ou une prise en compte insuffisante des contraintes d'exploitation. "
        "Le travail doit donc definir un gap clair, proposer une demarche defendable et produire une contribution originale adossee a des preuves."
    )
    hypotheses = [
        f"Une modelisation rigoureuse de {domain_focus} permet d'identifier des leviers d'amelioration mesurables.",
        "Une comparaison structuree avec l'etat de l'art mettra en evidence un gap exploitable pour une contribution originale.",
        "Une validation par simulation, etude de cas ou experimentation permettra de soutenir les conclusions de maniere credible.",
    ]
    objectives = [
        f"Formuler un sujet precis et defendable sur {domain_focus}.",
        "Structurer un plan de redaction chapitre par chapitre avec sorties attendues.",
        "Definir une strategie bibliographique, une methode de validation et un calendrier de redaction realiste.",
        "Faire ressortir une contribution originale, limitee mais verifiable.",
    ]
    research_questions = [
        f"Quel est le gap principal de recherche ou d'ingenierie sur {domain_focus} ?",
        "Quelle methode permettra de repondre a la problematique avec un niveau de preuve suffisant ?",
        "Quels indicateurs permettront de comparer objectivement la proposition aux travaux existants ?",
    ]
    quality_checklist = [
        "La problematique tient en 3 a 5 lignes et pointe une limite precise de l'etat de l'art.",
        "Chaque chapitre repond a une question explicite et produit une sortie identifiable.",
        "Toutes les affirmations techniques importantes sont reliees a une source ou a un resultat.",
        "Les figures, tableaux et annexes sont cites dans le texte et interpretes.",
        "Les limites du travail et les perspectives sont explicites, non decoratives.",
        "Le manuscrit reste original et ne copie ni la litterature ni le contenu brut de l'assistant.",
    ]
    originality_note = (
        "Le workflow propose un cadre de production et de recherche. Il doit servir de base de travail, pas de texte final a recopier. "
        "Le manuscrit final doit etre personnel, cite correctement ses sources et refleter une verification technique reelle."
    )
    next_actions = [
        "Valider le sujet et le perimetre avec l'encadreur avant de lancer la redaction detaillee.",
        "Demander ensuite une recherche ciblee avec /gpt-tool ou /arxiv pour peupler la revue de litterature.",
        "Demander une simulation ou un calcul si la methode retenue l'exige.",
        "Mettre en place un dossier de travail avec bibliographie, figures, scripts et journal de decisions.",
    ]

    return ThesisWorkflowResponse(
        status="ok",
        source="thesis-workflow",
        query=query,
        normalized_query=normalized_query,
        academic_level=academic_level,
        deliverable_type=deliverable_type,
        domain_focus=domain_focus,
        proposed_topic=proposed_topic,
        title_options=title_options,
        problem_statement=problem_statement,
        novelty_angle=novelty_angle,
        hypotheses=hypotheses,
        objectives=objectives,
        research_questions=research_questions,
        chapter_plan=[ThesisChapter(**item) for item in _build_thesis_chapter_plan(domain_focus, academic_level)],
        literature_strategy=LiteratureStrategy(**_build_thesis_literature_strategy(domain_focus)),
        methodology_blueprint=MethodologyBlueprint(**_build_thesis_methodology_blueprint(domain_focus)),
        writing_calendar=[WritingMilestone(**item) for item in _build_thesis_writing_calendar(academic_level)],
        quality_checklist=quality_checklist,
        originality_note=originality_note,
        next_actions=next_actions,
    ).model_dump()


def _looks_like_diagnosis_request(query: str) -> bool:
    lowered_query = query.lower()
    if _contains_any(lowered_query, RESEARCH_KEYWORDS | ACADEMIC_HINTS):
        return False
    return _contains_any(lowered_query, DIAGNOSIS_HINTS) or bool(
        re.search(r"\bwhy\b|\bpourquoi\b|\broot cause\b|\bwhat is causing\b", lowered_query)
    )


def _looks_like_simulation_request(query: str) -> bool:
    lowered_query = query.lower()
    circuit_signature = bool(
        re.search(
            r"\brc\b|\brl\b|\brlc\b|capacitor|capacitive|condensat|inductor|inductive|bobine|"
            r"transformer|transfo|three phase|three-phase|triphas|dc motor|motor dc|moteur dc|back emf|resonan",
            lowered_query,
        )
    )
    explicit_hints = {
        "simulate",
        "simulation",
        "simuler",
        "simu",
        "transient",
        "step response",
        "time response",
        "temporal response",
        "reponse temporelle",
        "réponse temporelle",
        "reponse transitoire",
        "réponse transitoire",
        "dimensionnement",
        "dimensionner",
        "dimensioning",
        "sizing",
        "interpretation",
        "interprétation",
        "oscillation",
        "overshoot",
        "damping",
        "amortissement",
        "resonance",
    }
    if circuit_signature and _contains_any(lowered_query, explicit_hints):
        return True
    if circuit_signature and re.search(r"\bcircuit\b|\bserie\b|\bsérie\b|\bparallel\b|\bparallele\b|\bparallèle\b", lowered_query):
        return True
    if re.search(r"\bcharge\b|\bdischarge\b", lowered_query) and re.search(r"\brc\b|capacitor|capacitive", lowered_query):
        return True
    if re.search(r"\bdecay\b|\benergize\b", lowered_query) and re.search(r"\brl\b|inductor|inductive", lowered_query):
        return True
    return False


def _looks_like_realtime_request(query: str) -> bool:
    lowered_query = query.lower()
    return _contains_any(lowered_query, REALTIME_HINTS) and bool(
        re.search(
            r"\brc\b|\brl\b|\brlc\b|capacitor|inductor|transformer|transfo|three phase|three-phase|triphas|dc motor|motor dc|moteur dc|simulation|simulate",
            lowered_query,
        )
    )


def _infer_engineering_domain(query: str) -> tuple[str, str]:
    lowered_query = query.lower()
    if any(term in lowered_query for term in {"transformer", "transfo", "substation", "relay", "relais", "protection", "triphas", "three phase", "feeder", "distribution", "busbar", "cable", "line", "ligne"}):
        return "electrotechnique", "power-systems"
    if any(term in lowered_query for term in {"motor", "moteur", "drive", "machine", "machines"}):
        return "electrotechnique", "machines-and-drives"
    if any(term in lowered_query for term in {"converter", "onduleur", "inverter", "rectifier", "power electronics", "harmonic", "harmonique"}):
        return "electrotechnique", "power-electronics"
    if any(term in lowered_query for term in {"automation", "automate", "control", "commande", "pid", "oscillation", "unstable"}):
        return "ingenierie", "control-and-automation"
    if any(term in lowered_query for term in {"thermal", "temperature", "overheat", "surchauffe", "cooling"}):
        return "ingenierie", "thermal-systems"
    return "ingenierie", "general-engineering"


def _infer_diagnosis_severity(query: str) -> str:
    lowered_query = query.lower()
    if any(term in lowered_query for term in {"burn", "smoke", "fire", "court-circuit", "short circuit", "arc", "trip", "declenche", "dÃ©clenche"}):
        return "critical"
    if any(term in lowered_query for term in {"overheat", "surchauffe", "chauffe", "instable", "unstable", "failure", "panne"}):
        return "high"
    if any(term in lowered_query for term in {"voltage drop", "chute de tension", "loss", "losses", "vibration"}):
        return "medium"
    return "normal"


def _infer_diagnosis_severity_safe(query: str) -> str:
    lowered_query = query.lower()
    if any(
        re.search(pattern, lowered_query)
        for pattern in {
            r"\bburn\b",
            r"\bsmoke\b",
            r"\bfire\b",
            r"court-circuit",
            r"short circuit",
            r"\barc\b",
            r"\btrip(?:s|ped|ping)?\b",
            r"\bdeclenche\b",
            r"\bdéclenche\b",
        }
    ):
        return "critical"
    if any(
        re.search(pattern, lowered_query)
        for pattern in {
            r"\boverheat\b",
            r"\bsurchauffe\b",
            r"\bchauffe\b",
            r"\binstable\b",
            r"\bunstable\b",
            r"\bfailure\b",
            r"\bpanne\b",
        }
    ):
        return "high"
    if any(
        re.search(pattern, lowered_query)
        for pattern in {
            r"voltage drop",
            r"chute de tension",
            r"\bloss\b",
            r"\blosses\b",
            r"\bvibration\b",
        }
    ):
        return "medium"
    return "normal"


def _build_engineering_diagnosis_payload(query: str) -> dict[str, Any]:
    normalized_query = _normalize_text(query)
    domain, system_family = _infer_engineering_domain(normalized_query)
    severity = _infer_diagnosis_severity_safe(normalized_query)

    probable_causes = [
        "Parametres nominaux ou conditions reelles d'exploitation mal identifies.",
        "Mesures insuffisantes ou absence de comparaison entre theorie, simulation et terrain.",
        "Interaction non prise en compte entre charge, alimentation, commande et protections.",
    ]
    quick_checks = [
        "Verifier les conditions de securite avant toute mesure ou remise sous tension.",
        "Confirmer les valeurs nominales, le schema de raccordement et le regime de fonctionnement reel.",
        "Comparer symptomes observes, instant d'apparition et conditions de charge.",
        "Isoler si possible le sous-systeme en cause avant d'aller vers une analyse detaillee.",
    ]
    measurements_to_take = [
        "Mesurer tensions, courants, puissance active/reactive et temperature aux points critiques.",
        "Verifier la chronologie du defaut: demarrage, regime etabli, surcharge, transitoire ou declenchement.",
        "Comparer les mesures reelles aux grandeurs nominales et au modele attendu.",
        "Tracer ou enregistrer les signaux cles si le phenomene est evolutif dans le temps.",
    ]
    equations_to_check = [
        "Bilans de puissance et rendement global du systeme.",
        "Relations tension-courant-impedance et chutes de tension sur les elements dominants.",
        "Constantes de temps, energie stockee et marges thermiques ou dynamiques.",
        "Conditions de stabilite, facteur de puissance ou selectivite selon le type de systeme.",
    ]
    recommended_tools = [
        "Multimetre, pince amperemetrique et analyseur reseau selon le cas.",
        "Oscilloscope ou acquisition de donnees pour les transitoires.",
        "Simulation avec /simulate ou /simulate-plot pour confronter le modele au terrain.",
        "Recherche d'articles et de standards avec /gpt-tool ou /arxiv pour la partie documentaire.",
    ]
    simulation_candidates = [
        "Simuler le sous-systeme principal avec les parametres reels ou estimes.",
        "Faire varier la charge, les pertes ou les parametres de commande pour tester la sensibilite.",
        "Comparer un cas nominal, un cas degrade et un cas corrige.",
    ]
    action_plan = [
        "1. Qualifier clairement le symptome et le contexte d'apparition.",
        "2. Relever les mesures minimales avant toute hypothese forte.",
        "3. Construire 2 a 4 causes probables et les classer par plausibilite.",
        "4. Tester chaque hypothese par mesure, calcul ou simulation.",
        "5. Valider la cause racine, proposer une correction, puis verifier apres action.",
    ]
    visual_support = [
        "Courbes temporelles de tension, courant, vitesse ou energie.",
        "Comparaison avant/apres correction sur les grandeurs critiques.",
        "Graphiques de pertes, rendement ou regulation si le probleme est energetique.",
        "Schema fonctionnel simplifie du systeme et des points de mesure.",
    ]
    escalation_note = (
        "Si le symptome implique echauffement anormal, declenchements repetes, odeur de brule, court-circuit ou risque humain, "
        "l'analyse doit rester conservative: securiser, isoler, mesurer puis seulement reenergiser."
    )

    lowered_query = normalized_query.lower()
    if system_family == "power-systems":
        probable_causes = [
            "Mauvais reglage de protection, selectivite insuffisante ou seuils mal calibres.",
            "Surcharge, chute de tension, desequilibre de phases ou facteur de puissance degrade.",
            "Vieillissement du materiel, pertes excessives ou echauffement localise.",
        ]
        equations_to_check = [
            "Bilans P, Q, S et cos phi.",
            "Rapport de transformation, regulation et rendement si un transformateur est implique.",
            "Chute de tension, courant de charge et coordination des protections.",
        ]
    elif system_family == "machines-and-drives":
        probable_causes = [
            "Charge mecanique excessive ou couple resistant sous-estime.",
            "Commande inadapt ee, back-EMF mal prise en compte ou saturation.",
            "Echauffement, pertes cuivre/fer ou frottements anormaux.",
        ]
        equations_to_check = [
            "Equations electromechaniques courant-couple-vitesse.",
            "Constantes de temps electrique et mecanique.",
            "Bilan de puissance et rendement du moteur.",
        ]
    elif system_family == "power-electronics":
        probable_causes = [
            "Commutation, filtrage ou commande insuffisamment maitrises.",
            "Harmoniques, surintensites ou surtensions transitoires.",
            "Mauvais dimensionnement thermique ou magnetique des composants.",
        ]
        equations_to_check = [
            "Rapports cycliques, ondulation, pertes de conduction et de commutation.",
            "Equilibres courant-tension sur les etages de conversion.",
            "Contraintes thermiques et rendement global.",
        ]

    return EngineeringDiagnosisResponse(
        status="ok",
        source="engineering-diagnosis",
        query=query,
        normalized_query=normalized_query,
        domain=domain,
        system_family=system_family,
        severity=severity,
        symptom_summary=(
            f"Analyse preliminaire d'un probleme dans le domaine {domain} ({system_family}). "
            "La demarche recommande de partir des symptomes observables, de consolider les mesures, "
            "puis de valider la cause racine par calcul, simulation ou comparaison documentaire."
        ),
        probable_causes=probable_causes,
        quick_checks=quick_checks,
        measurements_to_take=measurements_to_take,
        equations_to_check=equations_to_check,
        recommended_tools=recommended_tools,
        simulation_candidates=simulation_candidates,
        action_plan=action_plan,
        visual_support=visual_support,
        escalation_note=escalation_note,
    ).model_dump()


def _build_diagnosis_brief(payload: dict[str, Any]) -> str:
    return (
        f"Diagnostic structure pret pour un probleme de type {payload.get('system_family', 'engineering')}. "
        f"Severite estimee: {payload.get('severity', 'normal')}. "
        "Le detail contient causes probables, mesures a prendre, equations a verifier, plan d'action et supports visuels recommandes."
    )


def _labelize_signal(signal_name: str) -> str:
    return signal_name.replace("_", " ").replace(" v", " V").replace(" a", " A").replace(" rpm", " RPM").title()


def _guess_plot_signals(payload: dict[str, Any]) -> list[str]:
    kind = payload.get("kind", "")
    if kind == "rc":
        return ["capacitor_voltage_v", "resistor_current_a"]
    if kind == "rl":
        return ["inductor_current_a", "inductor_voltage_v"]
    if kind == "rlc":
        return ["capacitor_voltage_v", "resistor_current_a", "inductor_voltage_v"]
    if kind == "dc-motor":
        return ["speed_rpm", "armature_current_a", "torque_nm"]
    if kind == "three-phase":
        return ["active_power_w", "reactive_power_var", "apparent_power_va"]
    if kind == "transformer":
        return ["output_power_w", "total_losses_w", "loaded_secondary_voltage_v"]
    return []


def _extract_signal_series(payload: dict[str, Any], signal_name: str) -> list[tuple[float, float]]:
    points = []
    for item in payload.get("series", []):
        if not isinstance(item, dict):
            continue
        time_s = float(item.get("time_s", 0.0))
        value = item.get(signal_name)
        if value is None and isinstance(item.get("signals"), dict):
            value = item["signals"].get(signal_name)
        if isinstance(value, (int, float)):
            points.append((time_s, float(value)))
    return points


def _build_simulation_visualizations(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if payload.get("status") != "ok":
        return []
    query = payload.get("query", "")
    encoded_query = urlencode({"input": query})
    all_signals = _guess_plot_signals(payload)
    if not all_signals:
        return []
    first_group = ",".join(all_signals[: min(3, len(all_signals))])
    assets = [
        VisualizationAsset(
            title=f"Dashboard temps reel {payload.get('kind', 'simulation')}",
            kind="dashboard",
            format="html",
            url=f"{DEFAULT_PUBLIC_BASE_URL}/realtime-dashboard?{encoded_query}",
            description="Dashboard web avec streaming progressif des points de simulation.",
            signals=all_signals[: min(3, len(all_signals))],
        ).model_dump(),
        VisualizationAsset(
            title=f"Courbe principale {payload.get('kind', 'simulation')}",
            kind="svg-plot",
            format="svg",
            url=f"{DEFAULT_PUBLIC_BASE_URL}/simulate-plot?{encoded_query}&signals={first_group}",
            description="Visualisation SVG directe exploitable dans un navigateur ou une interface externe.",
            signals=all_signals[: min(3, len(all_signals))],
        ).model_dump()
    ]
    if len(all_signals) > 1:
        assets.append(
            VisualizationAsset(
                title=f"Courbe focalisee {payload.get('kind', 'simulation')}",
                kind="svg-plot",
                format="svg",
                url=f"{DEFAULT_PUBLIC_BASE_URL}/simulate-plot?{encoded_query}&signals={all_signals[0]}",
                description="Version resserree sur le signal principal pour lecture rapide.",
                signals=[all_signals[0]],
            ).model_dump()
        )
    return assets


def _build_simulation_streaming(payload: dict[str, Any], pace_ms: int = 120) -> dict[str, Any]:
    query = payload.get("query", "")
    encoded_query = urlencode({"input": query})
    recommended_signals = _guess_plot_signals(payload)
    signal_suffix = ""
    if recommended_signals:
        signal_suffix = "&signals=" + ",".join(recommended_signals[: min(3, len(recommended_signals))])
    return {
        "supported": payload.get("status") == "ok",
        "dashboard_url": f"{DEFAULT_PUBLIC_BASE_URL}/realtime-dashboard?{encoded_query}",
        "stream_url": f"{DEFAULT_PUBLIC_BASE_URL}/simulate-stream?{encoded_query}&pace_ms={pace_ms}{signal_suffix}",
        "recommended_signals": recommended_signals,
        "pace_ms": pace_ms,
    }


def _build_simulation_interpretation(payload: dict[str, Any]) -> list[str]:
    kind = payload.get("kind", "")
    metrics = payload.get("metrics", {})
    summary = []
    if kind == "rc":
        summary.append(f"La dynamique est gouvernee par la constante de temps tau={metrics.get('tau_s', 'n/a')} s.")
        summary.append("La tension du condensateur converge asymptotiquement vers la valeur de forçage.")
    elif kind == "rl":
        summary.append(f"Le courant suit une dynamique du premier ordre avec tau={metrics.get('tau_s', 'n/a')} s.")
        summary.append("La tension de l'inductance est maximale au debut puis decroit vers zero en regime etabli.")
    elif kind == "rlc":
        summary.append(f"Le regime detecte est {metrics.get('regime', 'n/a')} avec un amortissement {metrics.get('damping_ratio', 'n/a')}.")
        summary.append("La lecture de la courbe permet d'identifier depassement, oscillation et temps d'extinction.")
    elif kind == "transformer":
        summary.append(f"Le rendement estime est {metrics.get('efficiency_pct', 'n/a')} % au point de charge considere.")
        summary.append("Le graphe met en evidence la part relative des pertes et l'effet de regulation sur la tension secondaire.")
    elif kind == "three-phase":
        summary.append("La visualisation compare puissance active, reactive et apparente pour faciliter la lecture du cos phi.")
        summary.append("Un desequilibre ou une baisse de facteur de puissance devient plus visible sous forme graphique.")
    elif kind == "dc-motor":
        summary.append("Les courbes montrent la montee de vitesse, l'appel de courant et la stabilisation du couple.")
        summary.append("La comparaison vitesse-courant aide a distinguer surcharge mecanique et probleme de commande.")
    return summary


def _finalize_simulation_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("status") != "ok":
        payload.setdefault("interpretation", [])
        payload.setdefault("visualizations", [])
        payload.setdefault("streaming", {})
        return payload
    payload["interpretation"] = _build_simulation_interpretation(payload)
    payload["visualizations"] = _build_simulation_visualizations(payload)
    payload["streaming"] = _build_simulation_streaming(payload)
    return payload


def _format_sse_event(event_name: str, data: dict[str, Any]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(data)}\n\n"


def _build_realtime_dashboard_payload(query: str, pace_ms: int = 120) -> dict[str, Any]:
    simulation_payload = _simulate_from_query(query)
    if simulation_payload.get("status") != "ok":
        return RealtimeSimulationResponse(
            status="error",
            source="realtime-dashboard",
            query=query,
            summary=simulation_payload.get("summary", "La simulation n'a pas pu etre preparee pour le streaming."),
            dashboard_url="",
            stream_url="",
            recommended_signals=[],
            pace_ms=pace_ms,
            simulation=simulation_payload,
        ).model_dump()

    streaming = simulation_payload.get("streaming", {})
    return RealtimeSimulationResponse(
        status="ok",
        source="realtime-dashboard",
        query=query,
        summary=(
            "Dashboard temps reel pret. Utilise le dashboard pour lancer le streaming progressif des points "
            "et observer la courbe se construire a l'ecran."
        ),
        dashboard_url=streaming.get("dashboard_url", ""),
        stream_url=streaming.get("stream_url", ""),
        recommended_signals=streaming.get("recommended_signals", []),
        pace_ms=streaming.get("pace_ms", pace_ms),
        simulation=simulation_payload,
    ).model_dump()


def _build_svg_line_chart(payload: dict[str, Any], requested_signals: list[str]) -> str:
    available_signals = [signal for signal in requested_signals if _extract_signal_series(payload, signal)]
    if not available_signals:
        available_signals = [signal for signal in _guess_plot_signals(payload) if _extract_signal_series(payload, signal)]
    if not available_signals:
        raise HTTPException(status_code=404, detail="Aucun signal exploitable n'est disponible pour cette simulation.")

    width = 1040
    height = 620
    margin_left = 90
    margin_right = 40
    margin_top = 70
    margin_bottom = 90
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    palette = ["#006d77", "#d62828", "#3a86ff", "#f4a261", "#6a994e"]

    all_points = []
    for signal in available_signals:
        all_points.extend(_extract_signal_series(payload, signal))
    min_x = min(point[0] for point in all_points)
    max_x = max(point[0] for point in all_points)
    min_y = min(point[1] for point in all_points)
    max_y = max(point[1] for point in all_points)
    if math.isclose(max_x, min_x):
        max_x = min_x + 1.0
    if math.isclose(max_y, min_y):
        delta = 1.0 if abs(max_y) < 1e-9 else abs(max_y) * 0.1
        min_y -= delta
        max_y += delta

    def scale_x(value: float) -> float:
        return margin_left + ((value - min_x) / (max_x - min_x)) * plot_width

    def scale_y(value: float) -> float:
        return margin_top + (1.0 - ((value - min_y) / (max_y - min_y))) * plot_height

    x_grid = []
    y_grid = []
    for index in range(6):
        x_value = min_x + (max_x - min_x) * index / 5.0
        x_pos = scale_x(x_value)
        x_grid.append(
            f"<line x1='{x_pos:.2f}' y1='{margin_top}' x2='{x_pos:.2f}' y2='{margin_top + plot_height}' stroke='#d9d9d9' stroke-width='1' />"
            f"<text x='{x_pos:.2f}' y='{height - 45}' text-anchor='middle' font-size='14' fill='#334'>{_round_float(x_value)}</text>"
        )
        y_value = min_y + (max_y - min_y) * index / 5.0
        y_pos = scale_y(y_value)
        y_grid.append(
            f"<line x1='{margin_left}' y1='{y_pos:.2f}' x2='{margin_left + plot_width}' y2='{y_pos:.2f}' stroke='#e9e9e9' stroke-width='1' />"
            f"<text x='{margin_left - 12}' y='{y_pos + 5:.2f}' text-anchor='end' font-size='14' fill='#334'>{_round_float(y_value)}</text>"
        )

    series_paths = []
    legend_entries = []
    for index, signal in enumerate(available_signals):
        color = palette[index % len(palette)]
        signal_points = _extract_signal_series(payload, signal)
        polyline_points = " ".join(f"{scale_x(x):.2f},{scale_y(y):.2f}" for x, y in signal_points)
        series_paths.append(
            f"<polyline fill='none' stroke='{color}' stroke-width='3' points='{polyline_points}' />"
        )
        legend_y = 28 + index * 24
        legend_entries.append(
            f"<rect x='{width - 300}' y='{legend_y - 12}' width='18' height='6' fill='{color}' />"
            f"<text x='{width - 275}' y='{legend_y}' font-size='14' fill='#223'>{html.escape(_labelize_signal(signal))}</text>"
        )

    title = html.escape(f"Simulation {payload.get('kind', 'engineering')} - visualisation")
    subtitle = html.escape(payload.get("summary", ""))
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"
        "<rect width='100%' height='100%' fill='#f8fbfd' />"
        f"<text x='{margin_left}' y='32' font-size='24' font-weight='700' fill='#0b1f33'>{title}</text>"
        f"<text x='{margin_left}' y='54' font-size='14' fill='#4f5d75'>{subtitle}</text>"
        f"{''.join(x_grid)}{''.join(y_grid)}"
        f"<line x1='{margin_left}' y1='{margin_top + plot_height}' x2='{margin_left + plot_width}' y2='{margin_top + plot_height}' stroke='#222' stroke-width='2' />"
        f"<line x1='{margin_left}' y1='{margin_top}' x2='{margin_left}' y2='{margin_top + plot_height}' stroke='#222' stroke-width='2' />"
        f"{''.join(series_paths)}"
        f"{''.join(legend_entries)}"
        f"<text x='{margin_left + plot_width / 2:.2f}' y='{height - 15}' text-anchor='middle' font-size='15' fill='#223'>Temps (s)</text>"
        f"<text x='28' y='{margin_top + plot_height / 2:.2f}' text-anchor='middle' font-size='15' fill='#223' transform='rotate(-90 28 {margin_top + plot_height / 2:.2f})'>Amplitude</text>"
        "</svg>"
    )


def _build_svg_metric_bars(payload: dict[str, Any], requested_signals: list[str]) -> str:
    metrics = payload.get("metrics", {})
    if not isinstance(metrics, dict) or not metrics:
        raise HTTPException(status_code=404, detail="Aucune metrique exploitable n'est disponible pour cette simulation.")
    selected_items = []
    for key, value in metrics.items():
        if isinstance(value, (int, float)):
            if requested_signals and key not in requested_signals:
                continue
            selected_items.append((key, float(value)))
    if not selected_items:
        selected_items = [(key, float(value)) for key, value in metrics.items() if isinstance(value, (int, float))]
    selected_items = selected_items[:6]
    if not selected_items:
        raise HTTPException(status_code=404, detail="Aucune metrique numerique n'est disponible pour cette simulation.")

    width = 1040
    height = 620
    left = 280
    top = 120
    bar_height = 42
    gap = 26
    usable_width = 620
    max_value = max(abs(value) for _, value in selected_items) or 1.0
    bars = []
    labels = []
    values = []
    for index, (name, value) in enumerate(selected_items):
        y = top + index * (bar_height + gap)
        scaled = (abs(value) / max_value) * usable_width
        color = "#006d77" if value >= 0 else "#d62828"
        bars.append(f"<rect x='{left}' y='{y}' width='{scaled:.2f}' height='{bar_height}' rx='8' fill='{color}' />")
        labels.append(f"<text x='{left - 16}' y='{y + 27}' text-anchor='end' font-size='16' fill='#223'>{html.escape(_labelize_signal(name))}</text>")
        values.append(f"<text x='{left + scaled + 12:.2f}' y='{y + 27}' font-size='15' fill='#223'>{_round_float(value)}</text>")

    title = html.escape(f"Simulation {payload.get('kind', 'engineering')} - tableau visuel")
    subtitle = html.escape(payload.get("summary", ""))
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"
        "<rect width='100%' height='100%' fill='#f8fbfd' />"
        f"<text x='70' y='42' font-size='24' font-weight='700' fill='#0b1f33'>{title}</text>"
        f"<text x='70' y='68' font-size='14' fill='#4f5d75'>{subtitle}</text>"
        f"{''.join(bars)}{''.join(labels)}{''.join(values)}"
        "<text x='70' y='560' font-size='14' fill='#4f5d75'>Les barres facilitent la lecture des grandeurs de regime etabli ou des indicateurs de performance.</text>"
        "</svg>"
    )

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
        metrics={},
        interpretation=[],
        visualizations=[],
        streaming={},
        count=0,
        series=[],
    ).model_dump()


def _build_simulation_needs_input(
    query: str,
    kind: str,
    minimum_inputs: list[str],
    example_query: str,
    engineering_goal: str,
) -> dict[str, Any]:
    kind_label = kind.upper() if kind else "SYSTEME"
    return SimulationResponse(
        status="needs-input",
        source="simulation-engine",
        kind=kind,
        simulation_mode="guidance",
        query=query,
        summary=(
            f"La demande ressemble a un cas de {engineering_goal} pour un circuit {kind_label}, "
            "mais il manque les parametres minimaux pour executer une simulation exploitable."
        ),
        parameters={
            "minimum_inputs": minimum_inputs,
            "example_query": example_query,
        },
        metrics={
            "next_step": "Fournir les parametres manquants pour lancer la simulation et obtenir les courbes.",
        },
        interpretation=[
            "Le besoin est bien classe comme une demande de modelisation ou d'interpretation temporelle, pas comme une recherche bibliographique.",
            "Pour un dimensionnement serieux, il faut preciser les valeurs nominales, la topologie et le critere attendu: amortissement, depassement, resonance, temps de reponse ou energie stockee.",
            "Une fois les parametres fournis, l'API peut produire la serie temporelle, les metriques utiles et la courbe SVG ou le dashboard temps reel.",
        ],
        visualizations=[],
        streaming={},
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
        return _finalize_simulation_payload(_simulate_three_phase(query))

    if kind == "transformer":
        return _finalize_simulation_payload(_simulate_transformer(query))

    if kind == "dc-motor":
        return _finalize_simulation_payload(_simulate_dc_motor(query, steps_default=max(steps_default, 120)))

    if kind == "rlc":
        inductance_h = _extract_named_float(lowered_query, ["l", "ind", "inductance"])
        capacitance_f = _extract_named_float(lowered_query, ["c", "cap", "capacitance"])
        initial_voltage_v = _extract_named_float(lowered_query, ["vc0", "v0", "initial_voltage"])
        initial_current_a = _extract_named_float(lowered_query, ["i0", "initial_current"])
        simulation_mode = "decay" if "decay" in lowered_query or "discharge" in lowered_query else "step"
        if resistance_ohms is None or inductance_h is None or capacitance_f is None:
            return _build_simulation_needs_input(
                query,
                "rlc",
                ["r", "l", "c", "v", "t"],
                "simulate rlc r=10 l=0.05 c=0.0001 v=24 t=1 steps=120",
                "dimensionnement et interpretation de la reponse temporelle",
            )
        return _finalize_simulation_payload(
            _simulate_rlc(
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
        )

    if kind == "rc":
        capacitance_f = _extract_named_float(lowered_query, ["c", "cap", "capacitance"])
        initial_voltage_v = _extract_named_float(lowered_query, ["vc0", "v0", "initial_voltage"])
        simulation_mode = "discharge" if "discharge" in lowered_query else "charge"
        if resistance_ohms is None or capacitance_f is None:
            return _build_simulation_needs_input(
                query,
                "rc",
                ["r", "c", "v", "t"],
                "simulate rc r=1000 c=0.001 v=5 t=5 steps=80",
                "dimensionnement et lecture de la charge/decharge",
            )
        return _finalize_simulation_payload(
            _simulate_rc(query, resistance_ohms, capacitance_f, source_voltage_v, duration_s, steps, simulation_mode, initial_voltage_v)
        )

    inductance_h = _extract_named_float(lowered_query, ["l", "ind", "inductance"])
    initial_current_a = _extract_named_float(lowered_query, ["i0", "initial_current"])
    simulation_mode = "decay" if "decay" in lowered_query else "energize"
    if resistance_ohms is None or inductance_h is None:
        return _build_simulation_needs_input(
            query,
            "rl",
            ["r", "l", "v", "t"],
            "simulate rl r=10 l=0.2 v=24 t=1 steps=80",
            "dimensionnement et lecture de la montee du courant",
        )
    return _finalize_simulation_payload(
        _simulate_rl(query, resistance_ohms, inductance_h, source_voltage_v, duration_s, steps, simulation_mode, initial_current_a)
    )


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

    if _looks_like_live_connector_request(query):
        return "live", "Question detectee comme demande de connexion live capteurs, MQTT, Modbus, WebSocket ou automate."

    if _looks_like_realtime_request(query):
        return "realtime", "Question detectee comme demande de dashboard ou de streaming temps reel pour une simulation."

    if _looks_like_simulation_request(query):
        return "simulation", "Question detectee comme demande de simulation electrotechnique."

    if re.search(
        r"\brc\b|\brl\b|\brlc\b|transformer|transfo|three phase|three-phase|triphas|dc motor|motor dc|moteur dc",
        lowered_query,
    ) and re.search(r"\d|=", lowered_query):
        return "simulation", "Question detectee comme demande de simulation electrotechnique."

    if _looks_like_diagnosis_request(query):
        return "diagnosis", "Question detectee comme probleme d'ingenierie ou demande de diagnostic structure."

    if _is_math_expression(query) or _contains_any(lowered_query, CALCULATION_HINTS):
        return "wolfram", "Question detectee comme calcul, formule ou evaluation mathematique."

    if _looks_like_thesis_workflow_request(query):
        return "thesis", "Question detectee comme demande de workflow complet pour TFE, memoire ou these."

    if _looks_like_academic_request(query):
        return "academic", "Question detectee comme demande de TFE, these, memoire ou guidage de recherche academique."

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

    if mode == "realtime":
        return f"/realtime-simulation?{urlencode({'input': query})}"

    if mode == "live":
        return f"/live-connectors?{urlencode({'input': query})}"

    if mode == "diagnosis":
        return f"/engineering-diagnosis?{urlencode({'input': query})}"

    if mode == "thesis":
        return f"/thesis-workflow?{urlencode({'input': query})}"

    if mode == "academic":
        return f"/academic-assistant?{urlencode({'input': query})}"

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


def _build_academic_brief(payload: dict[str, Any]) -> str:
    if payload.get("status") == "needs-input":
        return (
            "Le cadrage academique a besoin d'un sujet explicite. "
            "L'action GPT ne recoit pas automatiquement le contenu du PDF joint: envoie le sujet, la problematique "
            "ou un extrait texte avant de demander un plan ou une methodologie."
        )
    titles = payload.get("title_suggestions", [])
    title_text = " ; ".join(titles[:3])
    return (
        f"Assistant academique pret pour {payload.get('academic_level', 'projet-academique')} sur "
        f"{payload.get('domain_focus', 'le sujet demande')}. "
        f"Propositions de titres: {title_text}. "
        "Le detail contient la problematique, les objectifs, les questions de recherche, la methodologie et le plan de redaction."
    )


def _build_thesis_workflow_brief(payload: dict[str, Any]) -> str:
    if payload.get("status") == "needs-input":
        return (
            "Le workflow academique a besoin d'un sujet explicite. "
            "Le PDF joint n'est pas transmis tel quel a l'action externe: envoie le titre, la problematique "
            "ou un resume texte avant de demander un plan detaille."
        )
    proposed_topic = payload.get("proposed_topic", "le sujet demande")
    chapter_count = len(payload.get("chapter_plan", []))
    calendar_count = len(payload.get("writing_calendar", []))
    return (
        f"Workflow de redaction et de recherche pret pour {payload.get('academic_level', 'projet-academique')} sur "
        f"{payload.get('domain_focus', 'le sujet demande')}. "
        f"Sujet propose: {proposed_topic}. "
        f"Le detail contient {chapter_count} chapitres structures, une strategie bibliographique, une methodologie et "
        f"un calendrier sur {calendar_count} phases."
    )


def _build_realtime_brief(payload: dict[str, Any]) -> str:
    return (
        "Dashboard temps reel externe pret. Donne a l'utilisateur l'URL `details.dashboard_url` et le flux "
        "`details.stream_url`. N'essaie pas de generer un dashboard local de remplacement si ces URLs sont presentes."
    )


def _build_live_brief(payload: dict[str, Any]) -> str:
    return (
        "Connecteurs live externes prets. Donne les URLs et endpoints du detail sans generer une interface locale de "
        "remplacement tant que `details.dashboard_url` ou les endpoints live sont presents."
    )


def _build_direct_response(query: str) -> str:
    return (
        f"Aucune API externe n'est necessaire pour cette question: '{query}'. "
        "Le GPT peut repondre directement. Pour declencher une recherche scientifique, utilise des mots comme "
        "'paper', 'research' ou 'article'. Pour un calcul, utilise 'calculate', 'solve' ou une expression mathematique. "
        "Pour un diagnostic, formule le symptome, le contexte, les mesures disponibles et le systeme concerne."
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

    if mode == "realtime":
        return [
            GptToolResult(
                title="Dashboard Temps Reel",
                snippet=data.get("summary", fallback_answer),
                link=data.get("dashboard_url", ""),
                published="",
                authors=[],
                provider=data.get("source", "realtime-dashboard"),
            ).model_dump()
        ]

    if mode == "live":
        return [
            GptToolResult(
                title="Dashboard Live",
                snippet=data.get("summary", fallback_answer),
                link=data.get("dashboard_url", ""),
                published="",
                authors=[],
                provider=data.get("source", "live-connectors"),
            ).model_dump()
        ]

    if mode == "diagnosis":
        return [
            GptToolResult(
                title=cause,
                snippet=data.get("symptom_summary", fallback_answer),
                link="",
                published="",
                authors=[],
                provider=data.get("source", "engineering-diagnosis"),
            ).model_dump()
            for cause in data.get("probable_causes", [])[:3]
        ]

    if mode == "thesis":
        return [
            GptToolResult(
                title=title,
                snippet=data.get("novelty_angle", fallback_answer),
                link="",
                published="",
                authors=[],
                provider=data.get("source", "thesis-workflow"),
            ).model_dump()
            for title in data.get("title_options", [])[:3]
        ]

    if mode == "academic":
        return [
            GptToolResult(
                title=title,
                snippet=data.get("problem_statement", fallback_answer),
                link="",
                published="",
                authors=[],
                provider=data.get("source", "academic-assistant"),
            ).model_dump()
            for title in data.get("title_suggestions", [])[:3]
        ]

    return []


def _compact_simulation_details(data: dict[str, Any], preview_points: int = 8) -> dict[str, Any]:
    series = data.get("series", []) or []
    safe_preview = max(0, min(preview_points, len(series)))
    return {
        "status": data.get("status", ""),
        "source": data.get("source", ""),
        "kind": data.get("kind", ""),
        "simulation_mode": data.get("simulation_mode", ""),
        "query": data.get("query", ""),
        "summary": data.get("summary", ""),
        "parameters": data.get("parameters", {}),
        "metrics": data.get("metrics", {}),
        "interpretation": data.get("interpretation", []),
        "visualizations": data.get("visualizations", []),
        "streaming": data.get("streaming", {}),
        "count": data.get("count", len(series)),
        "series_preview": series[:safe_preview],
        "series_truncated": len(series) > safe_preview,
    }


def _compact_diagnosis_details(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": data.get("status", ""),
        "source": data.get("source", ""),
        "query": data.get("query", ""),
        "normalized_query": data.get("normalized_query", ""),
        "domain": data.get("domain", ""),
        "system_family": data.get("system_family", ""),
        "severity": data.get("severity", ""),
        "symptom_summary": data.get("symptom_summary", ""),
        "probable_causes": (data.get("probable_causes") or [])[:3],
        "quick_checks": (data.get("quick_checks") or [])[:4],
        "measurements_to_take": (data.get("measurements_to_take") or [])[:4],
        "equations_to_check": (data.get("equations_to_check") or [])[:4],
        "recommended_tools": (data.get("recommended_tools") or [])[:4],
        "simulation_candidates": (data.get("simulation_candidates") or [])[:3],
        "action_plan": (data.get("action_plan") or [])[:5],
        "visual_support": (data.get("visual_support") or [])[:3],
        "escalation_note": data.get("escalation_note", ""),
    }


def _compact_academic_details(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": data.get("status", ""),
        "source": data.get("source", ""),
        "query": data.get("query", ""),
        "normalized_query": data.get("normalized_query", ""),
        "academic_level": data.get("academic_level", ""),
        "deliverable_type": data.get("deliverable_type", ""),
        "domain_focus": data.get("domain_focus", ""),
        "title_suggestions": (data.get("title_suggestions") or [])[:3],
        "problem_statement": data.get("problem_statement", ""),
        "objectives": (data.get("objectives") or [])[:4],
        "research_questions": (data.get("research_questions") or [])[:4],
        "keywords": (data.get("keywords") or [])[:6],
        "search_queries": (data.get("search_queries") or [])[:4],
        "recommended_sources": (data.get("recommended_sources") or [])[:4],
        "recommended_tools": (data.get("recommended_tools") or [])[:4],
        "methodology": data.get("methodology", ""),
        "outline": (data.get("outline") or [])[:5],
        "writing_guidelines": (data.get("writing_guidelines") or [])[:4],
        "milestones": (data.get("milestones") or [])[:4],
        "originality_note": data.get("originality_note", ""),
        "next_steps": (data.get("next_steps") or [])[:4],
    }


def _compact_thesis_details(data: dict[str, Any]) -> dict[str, Any]:
    chapter_plan = data.get("chapter_plan") or []
    writing_calendar = data.get("writing_calendar") or []
    return {
        "status": data.get("status", ""),
        "source": data.get("source", ""),
        "query": data.get("query", ""),
        "normalized_query": data.get("normalized_query", ""),
        "academic_level": data.get("academic_level", ""),
        "deliverable_type": data.get("deliverable_type", ""),
        "domain_focus": data.get("domain_focus", ""),
        "proposed_topic": data.get("proposed_topic", ""),
        "title_options": (data.get("title_options") or [])[:3],
        "problem_statement": data.get("problem_statement", ""),
        "novelty_angle": data.get("novelty_angle", ""),
        "hypotheses": (data.get("hypotheses") or [])[:3],
        "objectives": (data.get("objectives") or [])[:4],
        "research_questions": (data.get("research_questions") or [])[:4],
        "chapter_plan_preview": chapter_plan[:3],
        "chapter_plan_count": len(chapter_plan),
        "literature_strategy": data.get("literature_strategy", {}),
        "methodology_blueprint": data.get("methodology_blueprint", {}),
        "writing_calendar_preview": writing_calendar[:3],
        "writing_calendar_count": len(writing_calendar),
        "quality_checklist": (data.get("quality_checklist") or [])[:5],
        "originality_note": data.get("originality_note", ""),
        "next_actions": (data.get("next_actions") or [])[:4],
    }


def _compact_gpt_tool_details(mode: str, data: dict[str, Any]) -> dict[str, Any]:
    if not data:
        return {}

    if mode == "simulation":
        return _compact_simulation_details(data)

    if mode == "realtime":
        compact = {
            "status": data.get("status", ""),
            "source": data.get("source", ""),
            "query": data.get("query", ""),
            "summary": data.get("summary", ""),
            "dashboard_url": data.get("dashboard_url", ""),
            "stream_url": data.get("stream_url", ""),
            "recommended_signals": data.get("recommended_signals", []),
            "pace_ms": data.get("pace_ms", 0),
        }
        simulation = data.get("simulation")
        if isinstance(simulation, dict):
            compact["simulation"] = {
                "status": simulation.get("status", ""),
                "kind": simulation.get("kind", ""),
                "simulation_mode": simulation.get("simulation_mode", ""),
                "summary": simulation.get("summary", ""),
                "parameters": simulation.get("parameters", {}),
                "metrics": simulation.get("metrics", {}),
                "interpretation": simulation.get("interpretation", []),
            }
        return compact

    if mode == "live":
        return {
            "status": data.get("status", ""),
            "source": data.get("source", ""),
            "query": data.get("query", ""),
            "summary": data.get("summary", ""),
            "dashboard_url": data.get("dashboard_url", ""),
            "stream_url": data.get("stream_url", ""),
            "http_ingest_url": data.get("http_ingest_url", ""),
            "websocket_ingest_url_template": data.get("websocket_ingest_url_template", ""),
            "websocket_watch_url_template": data.get("websocket_watch_url_template", ""),
            "mqtt_status": data.get("mqtt_status", {}),
            "modbus_example_url": data.get("modbus_example_url", ""),
            "next_steps": data.get("next_steps", []),
        }

    if mode == "arxiv":
        return {
            "status": data.get("status", ""),
            "source": data.get("source", ""),
            "provider": data.get("provider", ""),
            "query": data.get("query", ""),
            "effective_query": data.get("effective_query", ""),
            "domain_filter_applied": data.get("domain_filter_applied", False),
            "count": data.get("count", 0),
            "warning": data.get("warning", ""),
            "top_results": (data.get("results") or [])[:3],
        }

    if mode == "diagnosis":
        return _compact_diagnosis_details(data)

    if mode == "academic":
        return _compact_academic_details(data)

    if mode == "thesis":
        return _compact_thesis_details(data)

    return data


def _to_gpt_tool_response(smart_payload: dict[str, Any]) -> dict[str, Any]:
    mode = smart_payload.get("mode", "basic")
    data = smart_payload.get("data") or smart_payload.get("external_result") or {}
    answer = smart_payload.get("response") or smart_payload.get("answer") or ""
    error = smart_payload.get("error") or ""
    compact_details = _compact_gpt_tool_details(mode, data)

    if mode == "arxiv":
        source = data.get("provider") or data.get("source") or "arxiv"
        query_used = data.get("effective_query") or smart_payload.get("normalized_input") or smart_payload.get("input", "")
    elif mode == "live":
        source = data.get("source", "live-connectors")
        query_used = data.get("query") or smart_payload.get("normalized_input") or smart_payload.get("input", "")
    elif mode == "realtime":
        source = data.get("source", "realtime-dashboard")
        query_used = data.get("query") or smart_payload.get("normalized_input") or smart_payload.get("input", "")
    elif mode == "diagnosis":
        source = data.get("source", "engineering-diagnosis")
        query_used = data.get("normalized_query") or smart_payload.get("normalized_input") or smart_payload.get("input", "")
    elif mode == "thesis":
        source = data.get("source", "thesis-workflow")
        query_used = data.get("normalized_query") or smart_payload.get("normalized_input") or smart_payload.get("input", "")
    elif mode == "academic":
        source = data.get("source", "academic-assistant")
        query_used = data.get("normalized_query") or smart_payload.get("normalized_input") or smart_payload.get("input", "")
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
        details=compact_details,
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
        "description": "Minimal OpenAPI schema expose uniquement l'endpoint /gpt-tool pour ChatGPT Actions, avec calcul, simulation, dashboard temps reel, visualisation, ingestion live capteurs/automates, diagnostic d'ingenierie, recherche technique et workflow academique.",
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
        "description_for_human": "Calculs scientifiques, simulations avec graphiques et dashboard temps reel, ingestion live MQTT/Modbus/WebSocket, diagnostic d'ingenierie, recherche documentaire et workflow TFE/these pour ChatGPT.",
        "description_for_model": (
            "Use this tool for scientific calculations, advanced electrical simulations, transformer-loss queries, "
            "three-phase or motor analysis, realtime simulation dashboards, live telemetry connectors for MQTT, Modbus and WebSocket, "
            "engineering diagnosis and troubleshooting, electrical-engineering paper retrieval, "
            "and academic assistance for TFE, memoire or thesis workflows and planning. "
            "Send the user request in the input field."
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
            "/academic-assistant",
            "/thesis-workflow",
            "/connectors-status",
            "/live-connectors",
            "/telemetry-ingest",
            "/telemetry-stream",
            "/live-dashboard",
            "/modbus-read",
            "/ws/telemetry-ingest/{channel}",
            "/ws/telemetry-watch/{channel}",
            "/simulate",
            "/simulate-plot",
            "/simulate-stream",
            "/realtime-simulation",
            "/realtime-dashboard",
            "/engineering-diagnosis",
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


@app.get("/connectors-status", response_model=ConnectorStatusResponse)
def connectors_status():
    return _build_connector_status_payload()


@app.get(
    "/live-connectors",
    response_model=LiveConnectorResponse,
    response_model_exclude_none=True,
    summary="Connecteurs live",
    description="Guide de connexion live pour capteurs, automates, MQTT, Modbus TCP, HTTP et WebSocket.",
)
def live_connectors(
    request: Request,
    query: str | None = Query(None, min_length=2, max_length=400, description="Besoin ou scenario live"),
    input_text: str | None = Query(
        None,
        alias="input",
        min_length=2,
        max_length=400,
        description="Alias principal pour l'integration live",
    ),
):
    raw_query = _get_text_param(query) or _get_text_param(input_text) or "integration live capteurs et automate"
    return _build_live_connector_payload(raw_query, _get_base_url(request=request))


@app.post(
    "/telemetry-ingest",
    response_model=TelemetryIngestResponse,
    response_model_exclude_none=True,
    summary="Ingestion HTTP",
    description="Ingestion HTTP simple de donnees live pour capteurs, scripts, passerelles ou automates.",
)
def telemetry_ingest(payload: TelemetryIngestRequest = Body(...)):
    frame = _append_telemetry_frame(payload.channel, payload.source or "http", payload.values, payload.metadata)
    return TelemetryIngestResponse(
        status="ok",
        source="http-ingest",
        frame=TelemetryFrame(**frame),
        retained_points=len(_get_telemetry_frames(payload.channel, limit=MAX_TELEMETRY_POINTS)),
    ).model_dump()


@app.get(
    "/telemetry-stream",
    summary="Flux telemetry live",
    description="Diffuse les trames live d'un canal via Server-Sent Events.",
)
async def telemetry_stream(
    channel: str = Query(..., min_length=1, max_length=120, description="Canal logique a ecouter"),
    after_sequence: int = Query(0, ge=0, description="Sequence a partir de laquelle reprendre"),
    pace_ms: int = Query(250, ge=50, le=5000, description="Frequence de verification du flux"),
):
    safe_channel = _sanitize_channel_name(channel)

    async def event_generator():
        last_sequence = after_sequence
        yield _format_sse_event("meta", {"channel": safe_channel, "status": "listening"})
        try:
            while True:
                frames = _get_telemetry_frames(safe_channel, limit=200, after_sequence=last_sequence)
                if frames:
                    for frame in frames:
                        last_sequence = max(last_sequence, int(frame.get("sequence", 0)))
                        yield _format_sse_event("point", frame)
                else:
                    yield _format_sse_event("heartbeat", {"channel": safe_channel, "sequence": last_sequence})
                await asyncio.sleep(pace_ms / 1000.0)
        except asyncio.CancelledError:
            return

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get(
    "/live-dashboard",
    response_class=HTMLResponse,
    summary="Dashboard live capteurs",
    description="Dashboard web pour visualiser les donnees live recues via HTTP, WebSocket, MQTT ou Modbus.",
)
def live_dashboard(
    request: Request,
    channel: str = Query("atelier-ligne-1", min_length=1, max_length=120, description="Canal logique a visualiser"),
):
    base_url = _get_base_url(request=request)
    safe_channel = _sanitize_channel_name(channel)
    page = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ElectroGPT Live Telemetry</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body {{ margin:0; font-family:"Segoe UI",sans-serif; background:#f4f8fb; color:#132238; }}
    .wrap {{ max-width:1200px; margin:0 auto; padding:24px; }}
    .hero {{ background:#0b1f33; color:#fff; padding:24px; border-radius:18px; }}
    .controls {{ display:grid; grid-template-columns:1fr auto auto; gap:12px; margin-top:18px; }}
    input, textarea, button {{ font:inherit; border-radius:12px; padding:12px 14px; border:1px solid #c9d7e6; }}
    button {{ background:#006d77; color:#fff; border:none; cursor:pointer; }}
    .secondary {{ background:#355070; }}
    .grid {{ display:grid; grid-template-columns:2fr 1fr; gap:18px; margin-top:18px; }}
    .card {{ background:#fff; border-radius:18px; padding:18px; box-shadow:0 12px 28px rgba(19,34,56,.08); }}
    canvas {{ width:100% !important; height:420px !important; }}
    .meta {{ display:grid; gap:10px; font-size:14px; }}
    .badge {{ display:inline-block; background:#d9f0f2; color:#005b63; padding:6px 10px; border-radius:999px; font-size:12px; font-weight:600; }}
    .payload {{ min-height:140px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <h1>ElectroGPT Live Telemetry Dashboard</h1>
      <p>Visualise en direct les donnees capteurs, automate ou passerelle envoyees via HTTP, WebSocket, MQTT ou Modbus.</p>
      <div class="controls">
        <input id="channelInput" value="{html.escape(safe_channel, quote=True)}" />
        <button id="listenBtn">Ecouter</button>
        <button id="stopBtn" class="secondary">Stop</button>
      </div>
    </div>

    <div class="grid">
      <div class="card"><canvas id="chartCanvas"></canvas></div>
      <div class="card meta">
        <div id="statusText"><span class="badge">Pret</span> En attente de donnees.</div>
        <div id="channelText">Canal: {html.escape(safe_channel)}</div>
        <div id="linksText"></div>
        <textarea id="jsonInput" class="payload">{{"temperature_c": 46.2, "current_a": 18.4}}</textarea>
        <button id="sendSampleBtn">Envoyer un echantillon HTTP</button>
      </div>
    </div>
  </div>

  <script>
    const baseUrl = {json.dumps(base_url)};
    const channelInput = document.getElementById("channelInput");
    const statusText = document.getElementById("statusText");
    const channelText = document.getElementById("channelText");
    const linksText = document.getElementById("linksText");
    const jsonInput = document.getElementById("jsonInput");
    let eventSource = null;
    let chart = null;
    let datasetsBySignal = {{}};
    const palette = ["#006d77", "#d62828", "#3a86ff", "#f4a261", "#6a994e", "#6f1d1b"];

    function ensureChart() {{
      if (chart) return;
      chart = new Chart(document.getElementById("chartCanvas").getContext("2d"), {{
        type: "line",
        data: {{ labels: [], datasets: [] }},
        options: {{
          animation: false,
          responsive: true,
          maintainAspectRatio: false,
          scales: {{
            x: {{ title: {{ display: true, text: "Sequence" }} }},
            y: {{ title: {{ display: true, text: "Valeur" }} }},
          }},
        }},
      }});
    }}

    function resetChart() {{
      if (chart) {{
        chart.destroy();
        chart = null;
      }}
      datasetsBySignal = {{}};
      ensureChart();
    }}

    function ensureDataset(signal) {{
      ensureChart();
      if (datasetsBySignal[signal] !== undefined) return datasetsBySignal[signal];
      const datasetIndex = chart.data.datasets.length;
      chart.data.datasets.push({{
        label: signal,
        data: [],
        borderColor: palette[datasetIndex % palette.length],
        backgroundColor: palette[datasetIndex % palette.length],
        borderWidth: 2,
        fill: false,
        tension: 0.18,
      }});
      datasetsBySignal[signal] = datasetIndex;
      return datasetIndex;
    }}

    function stopListening() {{
      if (eventSource) {{
        eventSource.close();
        eventSource = null;
      }}
    }}

    function listenChannel() {{
      stopListening();
      resetChart();
      const channel = channelInput.value.trim();
      if (!channel) return;
      channelText.textContent = "Canal: " + channel;
      statusText.innerHTML = "<span class='badge'>Ecoute</span> Flux en attente...";
      linksText.innerHTML = `
        <div>HTTP ingest: <code>${{baseUrl}}/telemetry-ingest</code></div>
        <div>WebSocket ingest: <code>${{baseUrl.replace('https://', 'wss://').replace('http://', 'ws://')}}/ws/telemetry-ingest/${{channel}}</code></div>
      `;
      eventSource = new EventSource(`${{baseUrl}}/telemetry-stream?channel=${{encodeURIComponent(channel)}}`);
      eventSource.addEventListener("point", (event) => {{
        const frame = JSON.parse(event.data);
        chart.data.labels.push(frame.sequence);
        Object.entries(frame.values || {{}}).forEach(([signal, value]) => {{
          const index = ensureDataset(signal);
          while (chart.data.datasets[index].data.length < chart.data.labels.length - 1) {{
            chart.data.datasets[index].data.push(null);
          }}
          chart.data.datasets[index].data.push(typeof value === "number" ? value : null);
        }});
        chart.data.datasets.forEach((dataset) => {{
          while (dataset.data.length < chart.data.labels.length) dataset.data.push(null);
        }});
        chart.update("none");
        statusText.innerHTML = `<span class='badge'>Actif</span> Derniere trame #${{frame.sequence}} via ${{frame.source}}`;
      }});
      eventSource.onerror = () => {{
        statusText.innerHTML = "<span class='badge'>Pause</span> Flux interrompu ou inactif.";
      }};
    }}

    async function sendSample() {{
      const channel = channelInput.value.trim();
      if (!channel) return;
      let values = {{}};
      try {{
        values = JSON.parse(jsonInput.value || "{{}}");
      }} catch (error) {{
        statusText.innerHTML = "<span class='badge'>Erreur</span> JSON invalide dans l'echantillon.";
        return;
      }}
      const resp = await fetch(`${{baseUrl}}/telemetry-ingest`, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ channel, values, source: "dashboard-http" }}),
      }});
      const payload = await resp.json();
      statusText.innerHTML = `<span class='badge'>Injecte</span> Trame #${{payload.frame.sequence}} envoyee.`;
    }}

    document.getElementById("listenBtn").addEventListener("click", listenChannel);
    document.getElementById("stopBtn").addEventListener("click", () => {{
      stopListening();
      statusText.innerHTML = "<span class='badge'>Stop</span> Ecoute arretee.";
    }});
    document.getElementById("sendSampleBtn").addEventListener("click", sendSample);
    listenChannel();
  </script>
</body>
</html>"""
    return HTMLResponse(page)


@app.get(
    "/modbus-read",
    response_model=ModbusReadResponse,
    response_model_exclude_none=True,
    summary="Lecture Modbus TCP",
    description="Interroge un equipement Modbus TCP, puis injecte les registres lus dans le pipeline telemetry live.",
)
def modbus_read(
    host: str = Query(..., min_length=1, max_length=255, description="Adresse IP ou nom d'hote du serveur Modbus TCP"),
    port: int = Query(502, ge=1, le=65535, description="Port TCP Modbus"),
    unit_id: int = Query(1, ge=0, le=255, description="Adresse esclave / unit id"),
    address: int = Query(0, ge=0, le=65535, description="Adresse du premier registre"),
    count: int = Query(4, ge=1, le=120, description="Nombre de registres a lire"),
    register_type: str = Query("holding", pattern="^(holding|input)$", description="Type de registre a lire"),
    channel: str = Query("modbus-live", min_length=1, max_length=120, description="Canal telemetry de sortie"),
    labels: str | None = Query(None, description="Etiquettes optionnelles separees par des virgules"),
    scale: float = Query(1.0, description="Facteur d'echelle applique aux registres"),
    signed: bool = Query(False, description="Interprete les registres comme entiers signes sur 16 bits"),
):
    labels_text = _get_text_param(labels)
    label_items = [item.strip() for item in labels_text.split(",")] if labels_text else []
    return _read_modbus_payload(
        host=host,
        port=port,
        unit_id=unit_id,
        address=address,
        count=count,
        register_type=register_type,
        channel=channel,
        labels=label_items,
        scale=scale,
        signed=signed,
    )


@app.websocket("/ws/telemetry-ingest/{channel}")
async def ws_telemetry_ingest(websocket: WebSocket, channel: str):
    await websocket.accept()
    safe_channel = _sanitize_channel_name(channel)
    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
            payload = {}
            if "text" in message and message["text"] is not None:
                text_payload = message["text"]
                try:
                    payload = json.loads(text_payload)
                except json.JSONDecodeError:
                    payload = {"values": {"value": text_payload}}
            elif "bytes" in message and message["bytes"] is not None:
                try:
                    payload = json.loads(message["bytes"].decode("utf-8", errors="ignore"))
                except json.JSONDecodeError:
                    payload = {"values": {"value": message["bytes"].decode("utf-8", errors="ignore")}}

            values = payload.get("values", payload if isinstance(payload, dict) else {"value": payload})
            metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}
            frame = _append_telemetry_frame(safe_channel, "websocket", values, metadata)
            await websocket.send_json({"status": "ok", "frame": frame})
    except WebSocketDisconnect:
        return


@app.websocket("/ws/telemetry-watch/{channel}")
async def ws_telemetry_watch(websocket: WebSocket, channel: str):
    await websocket.accept()
    safe_channel = _sanitize_channel_name(channel)
    last_sequence = 0
    try:
        while True:
            frames = _get_telemetry_frames(safe_channel, limit=100, after_sequence=last_sequence)
            if frames:
                for frame in frames:
                    last_sequence = max(last_sequence, int(frame.get("sequence", 0)))
                    await websocket.send_json(frame)
            await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        return


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
    "/academic-assistant",
    response_model=AcademicAssistantResponse,
    response_model_exclude_none=True,
    summary="Assistant academique",
    description="Cadrage d'un TFE, PFE, memoire ou these: problematique, objectifs, questions, methode, plan, outils et strategie de recherche.",
)
def academic_assistant(
    query: str | None = Query(None, min_length=2, max_length=400, description="Sujet ou besoin academique a cadrer"),
    input_text: str | None = Query(
        None,
        alias="input",
        min_length=2,
        max_length=400,
        description="Alias principal pour une demande de TFE, memoire ou these",
    ),
):
    raw_query = _get_text_param(query) or _get_text_param(input_text)
    if not raw_query:
        raise HTTPException(
            status_code=422,
            detail="Fournis un parametre 'query' ou 'input'.",
        )

    return _build_academic_assistant_payload(raw_query)


@app.get(
    "/thesis-workflow",
    response_model=ThesisWorkflowResponse,
    response_model_exclude_none=True,
    summary="Workflow TFE / these",
    description="Genere un workflow academique complet: sujet propose, problematique, hypotheses, plan detaille par chapitre, strategie bibliographique, methodologie et calendrier de redaction.",
)
def thesis_workflow(
    query: str | None = Query(None, min_length=2, max_length=500, description="Sujet ou besoin de workflow academique"),
    input_text: str | None = Query(
        None,
        alias="input",
        min_length=2,
        max_length=500,
        description="Alias principal pour un workflow de TFE, memoire ou these",
    ),
):
    raw_query = _get_text_param(query) or _get_text_param(input_text)
    if not raw_query:
        raise HTTPException(
            status_code=422,
            detail="Fournis un parametre 'query' ou 'input'.",
        )

    return _build_thesis_workflow_payload(raw_query)


@app.get(
    "/engineering-diagnosis",
    response_model=EngineeringDiagnosisResponse,
    response_model_exclude_none=True,
    summary="Diagnostic d'ingenierie",
    description="Analyse structuree d'un probleme technique avec causes probables, mesures a prendre, equations a verifier, outils et plan d'action.",
)
def engineering_diagnosis(
    query: str | None = Query(None, min_length=2, max_length=500, description="Description libre du probleme technique"),
    input_text: str | None = Query(
        None,
        alias="input",
        min_length=2,
        max_length=500,
        description="Alias principal pour un probleme, une panne ou un diagnostic technique",
    ),
):
    raw_query = _get_text_param(query) or _get_text_param(input_text)
    if not raw_query:
        raise HTTPException(
            status_code=422,
            detail="Fournis un parametre 'query' ou 'input'.",
        )

    return _build_engineering_diagnosis_payload(raw_query)


@app.get(
    "/realtime-simulation",
    response_model=RealtimeSimulationResponse,
    response_model_exclude_none=True,
    summary="Simulation temps reel",
    description="Prepare un dashboard web et un flux SSE pour rejouer une simulation de maniere progressive dans le navigateur.",
)
def realtime_simulation(
    query: str | None = Query(None, min_length=2, max_length=500, description="Requete de simulation a diffuser"),
    input_text: str | None = Query(
        None,
        alias="input",
        min_length=2,
        max_length=500,
        description="Alias principal pour un dashboard ou un streaming temps reel",
    ),
    pace_ms: int = Query(120, ge=20, le=2000, description="Intervalle entre deux points diffuses, en millisecondes"),
):
    raw_query = _get_text_param(query) or _get_text_param(input_text)
    if not raw_query:
        raise HTTPException(
            status_code=422,
            detail="Fournis un parametre 'query' ou 'input'.",
        )

    return _build_realtime_dashboard_payload(raw_query, pace_ms=pace_ms)


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


@app.get(
    "/simulate-stream",
    summary="Flux temps reel de simulation",
    description="Diffuse une simulation point par point via Server-Sent Events pour un dashboard web.",
)
async def simulate_stream(
    query: str | None = Query(None, min_length=2, max_length=500, description="Requete de simulation libre"),
    input_text: str | None = Query(
        None,
        alias="input",
        min_length=2,
        max_length=500,
        description="Alias principal pour la simulation temps reel",
    ),
    signals: str | None = Query(
        None,
        description="Liste optionnelle de signaux separes par des virgules.",
    ),
    pace_ms: int = Query(120, ge=20, le=2000, description="Intervalle entre deux points diffuses, en millisecondes"),
):
    raw_query = _get_text_param(query) or _get_text_param(input_text)
    if not raw_query:
        raise HTTPException(
            status_code=422,
            detail="Fournis un parametre 'query' ou 'input'.",
        )

    payload = _simulate_from_query(raw_query)
    if payload.get("status") != "ok":
        raise HTTPException(status_code=400, detail=payload.get("summary", "Simulation invalide."))

    requested_signals = []
    signals_text = _get_text_param(signals)
    if signals_text:
        requested_signals = [item.strip() for item in signals_text.split(",") if item.strip()]

    selected_signals = [signal for signal in requested_signals if _extract_signal_series(payload, signal)]
    if not selected_signals:
        selected_signals = [signal for signal in _guess_plot_signals(payload) if _extract_signal_series(payload, signal)]
    if not selected_signals:
        selected_signals = list((payload.get("metrics") or {}).keys())[:3]

    async def event_generator():
        meta_payload = {
            "kind": payload.get("kind"),
            "summary": payload.get("summary"),
            "signals": selected_signals,
            "count": payload.get("count", 0),
            "parameters": payload.get("parameters", {}),
        }
        yield _format_sse_event("meta", meta_payload)
        for item in payload.get("series", []):
            values = {}
            for signal in selected_signals:
                signal_value = item.get(signal)
                if signal_value is None and isinstance(item.get("signals"), dict):
                    signal_value = item["signals"].get(signal)
                if isinstance(signal_value, (int, float)):
                    values[signal] = signal_value
            yield _format_sse_event(
                "point",
                {
                    "time_s": item.get("time_s", 0.0),
                    "values": values,
                },
            )
            await asyncio.sleep(pace_ms / 1000.0)
        yield _format_sse_event("done", {"status": "completed"})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get(
    "/realtime-dashboard",
    response_class=HTMLResponse,
    summary="Dashboard temps reel",
    description="Interface web de streaming et de visualisation des simulations electrotechniques.",
)
def realtime_dashboard(
    request: Request,
    query: str | None = Query(None, min_length=2, max_length=500, description="Requete initiale de simulation"),
    input_text: str | None = Query(
        None,
        alias="input",
        min_length=2,
        max_length=500,
        description="Alias principal pour la simulation a visualiser",
    ),
):
    raw_query = _get_text_param(query) or _get_text_param(input_text) or "simulate rc r=1000 c=0.001 v=5 t=5 steps=60"
    base_url = _get_base_url(request=request)
    escaped_query = html.escape(raw_query, quote=True)
    page = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ElectroGPT Realtime Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body {{
      margin: 0;
      font-family: "Segoe UI", sans-serif;
      background: linear-gradient(180deg, #f4f8fb 0%, #eef3f8 100%);
      color: #132238;
    }}
    .wrap {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 24px;
    }}
    .hero {{
      background: #0b1f33;
      color: #fff;
      padding: 24px;
      border-radius: 18px;
      box-shadow: 0 20px 50px rgba(11, 31, 51, 0.15);
    }}
    .controls {{
      display: grid;
      grid-template-columns: 1fr auto auto;
      gap: 12px;
      margin-top: 18px;
    }}
    input, button {{
      font: inherit;
      border-radius: 12px;
      border: 1px solid #c9d7e6;
      padding: 12px 14px;
    }}
    button {{
      background: #006d77;
      color: #fff;
      border: none;
      cursor: pointer;
    }}
    button.secondary {{
      background: #355070;
    }}
    .panel-grid {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 18px;
      margin-top: 20px;
    }}
    .card {{
      background: #fff;
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 14px 30px rgba(31, 53, 79, 0.08);
    }}
    .meta {{
      display: grid;
      gap: 10px;
      font-size: 14px;
    }}
    .badge {{
      display: inline-block;
      background: #d9f0f2;
      color: #005b63;
      padding: 6px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 600;
      margin-right: 6px;
    }}
    .examples {{
      margin-top: 14px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .example-btn {{
      background: #edf6f9;
      color: #123;
      border: 1px solid #c5dbe0;
      padding: 8px 10px;
      border-radius: 999px;
      cursor: pointer;
    }}
    canvas {{
      width: 100% !important;
      height: 420px !important;
    }}
    a {{
      color: #006d77;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <h1>ElectroGPT Realtime Dashboard</h1>
      <p>Streaming progressif des points de simulation, lecture des tendances et interpretation rapide pour l'ingenierie et l'electrotechnique.</p>
      <div class="controls">
        <input id="queryInput" value="{escaped_query}" />
        <button id="startBtn">Lancer</button>
        <button id="stopBtn" class="secondary">Stop</button>
      </div>
      <div class="examples">
        <button class="example-btn" data-query="simulate rc r=1000 c=0.001 v=5 t=5 steps=60">RC</button>
        <button class="example-btn" data-query="simulate rl r=10 l=0.2 v=24 t=1 steps=80">RL</button>
        <button class="example-btn" data-query="simulate rlc r=10 l=0.05 c=0.0001 v=24 t=1 steps=120">RLC</button>
        <button class="example-btn" data-query="simulate dc motor v=24 r=1.2 l=0.02 ke=0.08 kt=0.08 j=0.01 t=2">Moteur DC</button>
      </div>
    </div>

    <div class="panel-grid">
      <div class="card">
        <canvas id="chartCanvas"></canvas>
      </div>
      <div class="card meta">
        <div id="statusText"><span class="badge">Pret</span> En attente d'une simulation.</div>
        <div id="summaryText"></div>
        <div id="interpretationText"></div>
        <div id="linksText"></div>
      </div>
    </div>
  </div>

  <script>
    const baseUrl = {json.dumps(base_url)};
    const queryInput = document.getElementById("queryInput");
    const statusText = document.getElementById("statusText");
    const summaryText = document.getElementById("summaryText");
    const interpretationText = document.getElementById("interpretationText");
    const linksText = document.getElementById("linksText");
    const chartCanvas = document.getElementById("chartCanvas");
    let eventSource = null;
    let chart = null;

    function stopStream() {{
      if (eventSource) {{
        eventSource.close();
        eventSource = null;
      }}
    }}

    function buildChart(signals) {{
      if (chart) {{
        chart.destroy();
      }}
      const palette = ["#006d77", "#d62828", "#3a86ff", "#f4a261", "#6a994e"];
      chart = new Chart(chartCanvas.getContext("2d"), {{
        type: "line",
        data: {{
          labels: [],
          datasets: signals.map((signal, index) => ({{
            label: signal,
            data: [],
            borderColor: palette[index % palette.length],
            backgroundColor: palette[index % palette.length],
            borderWidth: 2,
            fill: false,
            tension: 0.18,
          }})),
        }},
        options: {{
          animation: false,
          responsive: true,
          maintainAspectRatio: false,
          scales: {{
            x: {{ title: {{ display: true, text: "Temps (s)" }} }},
            y: {{ title: {{ display: true, text: "Amplitude" }} }},
          }},
        }},
      }});
    }}

    async function startRealtime() {{
      stopStream();
      const query = queryInput.value.trim();
      if (!query) {{
        return;
      }}

      statusText.innerHTML = "<span class='badge'>Chargement</span> Preparation de la simulation...";
      summaryText.textContent = "";
      interpretationText.textContent = "";
      linksText.innerHTML = "";

      const configResp = await fetch(`${{baseUrl}}/realtime-simulation?input=${{encodeURIComponent(query)}}`);
      const config = await configResp.json();
      if (config.status !== "ok") {{
        statusText.innerHTML = "<span class='badge'>Erreur</span> " + (config.summary || "Simulation non disponible.");
        return;
      }}

      const sim = config.simulation || {{}};
      const signals = config.recommended_signals || [];
      buildChart(signals);

      statusText.innerHTML = "<span class='badge'>Streaming</span> Flux actif";
      summaryText.textContent = sim.summary || config.summary || "";
      interpretationText.innerHTML = (sim.interpretation || []).map((item) => `<div>- ${{item}}</div>`).join("");
      const staticPlot = (sim.visualizations || []).find((item) => item.kind === "svg-plot");
      linksText.innerHTML = `
        <div><a href="${{config.dashboard_url}}" target="_blank" rel="noreferrer">Ouvrir ce dashboard dans un nouvel onglet</a></div>
        ${{staticPlot ? `<div><a href="${{staticPlot.url}}" target="_blank" rel="noreferrer">Ouvrir la courbe SVG statique</a></div>` : ""}}
      `;

      const streamUrl = `${{baseUrl}}/simulate-stream?input=${{encodeURIComponent(query)}}&pace_ms=${{config.pace_ms}}&signals=${{encodeURIComponent(signals.join(","))}}`;
      eventSource = new EventSource(streamUrl);

      eventSource.addEventListener("meta", (event) => {{
        const payload = JSON.parse(event.data);
        buildChart(payload.signals || signals);
      }});

      eventSource.addEventListener("point", (event) => {{
        const payload = JSON.parse(event.data);
        chart.data.labels.push(payload.time_s);
        chart.data.datasets.forEach((dataset) => {{
          const value = payload.values[dataset.label];
          dataset.data.push(value ?? null);
        }});
        chart.update("none");
      }});

      eventSource.addEventListener("done", () => {{
        statusText.innerHTML = "<span class='badge'>Termine</span> Le streaming est termine.";
        stopStream();
      }});

      eventSource.onerror = () => {{
        statusText.innerHTML = "<span class='badge'>Interrompu</span> Le flux a ete interrompu ou ferme.";
        stopStream();
      }};
    }}

    document.getElementById("startBtn").addEventListener("click", startRealtime);
    document.getElementById("stopBtn").addEventListener("click", () => {{
      stopStream();
      statusText.innerHTML = "<span class='badge'>Stop</span> Streaming arrete manuellement.";
    }});
    document.querySelectorAll(".example-btn").forEach((button) => {{
      button.addEventListener("click", () => {{
        queryInput.value = button.dataset.query;
        startRealtime();
      }});
    }});
  </script>
</body>
</html>"""
    return HTMLResponse(page)


@app.get(
    "/simulate-plot",
    summary="Visualisation de simulation",
    description="Retourne une visualisation SVG exploitable dans un navigateur a partir d'une simulation existante.",
    response_class=Response,
)
def simulate_plot(
    query: str | None = Query(None, min_length=2, max_length=400, description="Requete de simulation libre"),
    input_text: str | None = Query(
        None,
        alias="input",
        min_length=2,
        max_length=400,
        description="Alias principal pour la requete de simulation",
    ),
    signals: str | None = Query(
        None,
        description="Liste optionnelle de signaux separes par des virgules. Exemple: capacitor_voltage_v,resistor_current_a",
    ),
    style: str = Query(
        "auto",
        pattern="^(auto|line|bars)$",
        description="Style de rendu SVG: auto, line ou bars.",
    ),
):
    raw_query = _get_text_param(query) or _get_text_param(input_text)
    if not raw_query:
        raise HTTPException(
            status_code=422,
            detail="Fournis un parametre 'query' ou 'input'.",
        )

    payload = _simulate_from_query(raw_query)
    if payload.get("status") != "ok":
        raise HTTPException(status_code=400, detail=payload.get("summary", "Simulation invalide."))

    signals_text = _get_text_param(signals)
    requested_signals = []
    if signals_text:
        requested_signals = [item.strip() for item in signals_text.split(",") if item.strip()]

    has_time_series = payload.get("count", 0) > 1
    render_style = _get_text_param(style) or "auto"
    if render_style == "auto":
        render_style = "line" if has_time_series else "bars"

    svg = _build_svg_line_chart(payload, requested_signals) if render_style == "line" else _build_svg_metric_bars(payload, requested_signals)
    return Response(content=svg, media_type="image/svg+xml")


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
    try:
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

        if route == "realtime":
            payload = _build_realtime_dashboard_payload(normalized_query)
            return _build_smart_payload(
                status=payload.get("status", "ok"),
                mode="realtime",
                raw_query=raw_query,
                normalized_query=normalized_query,
                reason=reason,
                max_results=max_results_value,
                auto_filter=auto_filter_value,
                executed=payload.get("status") == "ok",
                response=_build_realtime_brief(payload),
                data=payload,
                error="" if payload.get("status") == "ok" else payload.get("summary", "Le dashboard temps reel n'a pas pu etre prepare."),
            )

        if route == "live":
            payload = _build_live_connector_payload(normalized_query, DEFAULT_PUBLIC_BASE_URL)
            return _build_smart_payload(
                status=payload.get("status", "ok"),
                mode="live",
                raw_query=raw_query,
                normalized_query=normalized_query,
                reason=reason,
                max_results=max_results_value,
                auto_filter=auto_filter_value,
                executed=True,
                response=_build_live_brief(payload),
                data=payload,
            )

        if route == "diagnosis":
            payload = _build_engineering_diagnosis_payload(normalized_query)
            return _build_smart_payload(
                status=payload.get("status", "ok"),
                mode="diagnosis",
                raw_query=raw_query,
                normalized_query=normalized_query,
                reason=reason,
                max_results=max_results_value,
                auto_filter=auto_filter_value,
                executed=True,
                response=_build_diagnosis_brief(payload),
                data=payload,
            )

        if route == "thesis":
            payload = _build_thesis_workflow_payload(normalized_query)
            return _build_smart_payload(
                status=payload.get("status", "ok"),
                mode="thesis",
                raw_query=raw_query,
                normalized_query=normalized_query,
                reason=reason,
                max_results=max_results_value,
                auto_filter=auto_filter_value,
                executed=True,
                response=_build_thesis_workflow_brief(payload),
                data=payload,
            )

        if route == "academic":
            payload = _build_academic_assistant_payload(normalized_query)
            return _build_smart_payload(
                status=payload.get("status", "ok"),
                mode="academic",
                raw_query=raw_query,
                normalized_query=normalized_query,
                reason=reason,
                max_results=max_results_value,
                auto_filter=auto_filter_value,
                executed=True,
                response=_build_academic_brief(payload),
                data=payload,
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
    except Exception as exc:
        safe_response = (
            "Une erreur interne inattendue est survenue pendant le routage de la requete. "
            "Le GPT peut demander une reformulation ou reessayer avec une question plus precise."
        )
        return _build_smart_payload(
            status="error",
            mode="basic",
            raw_query=raw_query,
            normalized_query=normalized_query,
            reason="Erreur interne capturee par le routeur intelligent.",
            max_results=max_results_value,
            auto_filter=auto_filter_value,
            executed=False,
            response=safe_response,
            answer=safe_response,
            error=str(exc),
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

    try:
        smart_payload = smart_query(
            query=raw_query,
            max_results=_get_int_param(max_results, 3),
            auto_filter=_get_bool_param(auto_filter, True),
        )
        return _to_gpt_tool_response(smart_payload)
    except Exception as exc:
        return GptToolResponse(
            status="error",
            tool="gpt-tool",
            mode="basic",
            input=raw_query,
            query_used=_normalize_text(raw_query),
            executed=False,
            source="direct",
            redirect="",
            answer="Une erreur interne inattendue est survenue. Reformule la demande ou reessaie.",
            results=[],
            details={},
            error=str(exc),
        ).model_dump()


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

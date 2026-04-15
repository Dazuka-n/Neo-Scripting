import os
import warnings
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)


SUPPORTED_MODELS = {
    "gemini-flash": "models/gemini-flash-latest",
    "gemini-pro": "models/gemini-pro-latest",
    "gemini-1.5-flash": "models/gemini-flash-latest",
    "gemini-1.5-pro": "models/gemini-pro-latest",
}

OPENROUTER_MODEL_ALIASES = {
    "models/gemini-flash-latest": "google/gemini-flash-1.5",
    "models/gemini-pro-latest": "google/gemini-pro-1.5",
}


def _normalize_non_google_model(model_name: str) -> str:
    if not model_name:
        return None
    return OPENROUTER_MODEL_ALIASES.get(model_name, model_name)


def _normalize_gemini_model(model_name: str) -> str:
    """Map deprecated Gemini model IDs to currently supported ones."""
    if not model_name:
        return "models/gemini-flash-latest"
    normalized = model_name.strip()
    normalized_lower = normalized.lower()
    if normalized_lower.startswith("models/gemini"):
        return normalized
    replacement = SUPPORTED_MODELS.get(normalized_lower)
    if replacement:
        return replacement
    if not normalized_lower.startswith("models/"):
        if normalized_lower in SUPPORTED_MODELS:
            return SUPPORTED_MODELS[normalized_lower]
    warnings.warn(
        f"Model '{model_name}' is not a recognized Gemini model. "
        "Defaulting to 'models/gemini-flash-latest'.",
        RuntimeWarning,
    )
    return "models/gemini-flash-latest"


def _agent_model(env_var: str, default: str, provider: str) -> str:
    raw = os.getenv(env_var, default)
    if provider == "google":
        return _normalize_gemini_model(raw)
    return _normalize_non_google_model(raw)


def _agent_key(env_var: str, google_key: str, openrouter_key: str, openai_key: str, provider: str) -> str:
    if provider == "google":
        return os.getenv(env_var) or google_key
    return os.getenv(env_var) or openrouter_key or openai_key


def _agent_base_url(provider: str, gemini_url: str, openrouter_url: str) -> str:
    return gemini_url if provider == "google" else openrouter_url


class Config:
    # ── LLM providers ────────────────────────────────────────────────────
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    GEMINI_API_KEY: str = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("PLANNER_API_KEY")
        or os.getenv("WRITER_API_KEY")
        or os.getenv("API")
        or ""
    )

    MODEL_NAME: str = os.getenv("MODEL_NAME", "models/gemini-flash-latest")
    DEFAULT_LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "google").lower()
    DEFAULT_LLM_MODEL: str = (
        _normalize_gemini_model(os.getenv("MODEL_NAME", "models/gemini-flash-latest"))
        if os.getenv("LLM_PROVIDER", "google").lower() == "google"
        else _normalize_non_google_model(os.getenv("LLM_MODEL", os.getenv("MODEL_NAME", "models/gemini-flash-latest")))
    )
    DEFAULT_LLM_API_KEY: str = (
        (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "")
        if os.getenv("LLM_PROVIDER", "google").lower() == "google"
        else (os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or "")
    )

    # ── Qdrant ───────────────────────────────────────────────────────────
    QDRANT_URL: str = os.getenv("QDRANT_URL", "")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "aeo_knowledge_base")

    # ── Researcher agent (always Google/Gemini) ───────────────────────────
    RESEARCHER_PROVIDER: str = "google"
    RESEARCHER_MODEL: str = _normalize_gemini_model(
        os.getenv("RESEARCHER_MODEL", os.getenv("MODEL_NAME", "models/gemini-flash-latest"))
    )
    RESEARCHER_API_KEY: str = os.getenv("RESEARCHER_API_KEY") or (
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    )
    RESEARCHER_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    # ── Planner agent ─────────────────────────────────────────────────────
    PLANNER_PROVIDER: str = os.getenv("PLANNER_PROVIDER", os.getenv("LLM_PROVIDER", "google")).lower()
    PLANNER_MODEL: str = _agent_model(
        "PLANNER_MODEL",
        os.getenv("MODEL_NAME", "models/gemini-flash-latest"),
        os.getenv("PLANNER_PROVIDER", os.getenv("LLM_PROVIDER", "google")).lower(),
    )
    PLANNER_API_KEY: str = _agent_key(
        "PLANNER_API_KEY",
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "",
        os.getenv("OPENROUTER_API_KEY") or "",
        os.getenv("OPENAI_API_KEY") or "",
        os.getenv("PLANNER_PROVIDER", os.getenv("LLM_PROVIDER", "google")).lower(),
    )
    PLANNER_BASE_URL: str = _agent_base_url(
        os.getenv("PLANNER_PROVIDER", os.getenv("LLM_PROVIDER", "google")).lower(),
        "https://generativelanguage.googleapis.com/v1beta/openai/",
        os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    )

    # ── Writer agent ──────────────────────────────────────────────────────
    WRITER_PROVIDER: str = os.getenv("WRITER_PROVIDER", os.getenv("LLM_PROVIDER", "google")).lower()
    WRITER_MODEL: str = _agent_model(
        "WRITER_MODEL",
        os.getenv("MODEL_NAME", "models/gemini-flash-latest"),
        os.getenv("WRITER_PROVIDER", os.getenv("LLM_PROVIDER", "google")).lower(),
    )
    WRITER_API_KEY: str = _agent_key(
        "WRITER_API_KEY",
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "",
        os.getenv("OPENROUTER_API_KEY") or "",
        os.getenv("OPENAI_API_KEY") or "",
        os.getenv("WRITER_PROVIDER", os.getenv("LLM_PROVIDER", "google")).lower(),
    )
    WRITER_BASE_URL: str = _agent_base_url(
        os.getenv("WRITER_PROVIDER", os.getenv("LLM_PROVIDER", "google")).lower(),
        "https://generativelanguage.googleapis.com/v1beta/openai/",
        os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    )

    # ── Optimizer agent ───────────────────────────────────────────────────
    OPTIMIZER_PROVIDER: str = os.getenv("OPTIMIZER_PROVIDER", os.getenv("LLM_PROVIDER", "google")).lower()
    OPTIMIZER_MODEL: str = _agent_model(
        "OPTIMIZER_MODEL",
        os.getenv("MODEL_NAME", "models/gemini-flash-latest"),
        os.getenv("OPTIMIZER_PROVIDER", os.getenv("LLM_PROVIDER", "google")).lower(),
    )
    OPTIMIZER_API_KEY: str = _agent_key(
        "OPTIMIZER_API_KEY",
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "",
        os.getenv("OPENROUTER_API_KEY") or "",
        os.getenv("OPENAI_API_KEY") or "",
        os.getenv("OPTIMIZER_PROVIDER", os.getenv("LLM_PROVIDER", "google")).lower(),
    )
    OPTIMIZER_BASE_URL: str = _agent_base_url(
        os.getenv("OPTIMIZER_PROVIDER", os.getenv("LLM_PROVIDER", "google")).lower(),
        "https://generativelanguage.googleapis.com/v1beta/openai/",
        os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    )

    # ── QA agent ──────────────────────────────────────────────────────────
    QA_PROVIDER: str = os.getenv("QA_PROVIDER", os.getenv("LLM_PROVIDER", "google")).lower()
    QA_MODEL: str = _agent_model(
        "QA_MODEL",
        os.getenv("MODEL_NAME", "models/gemini-flash-latest"),
        os.getenv("QA_PROVIDER", os.getenv("LLM_PROVIDER", "google")).lower(),
    )
    QA_API_KEY: str = _agent_key(
        "QA_API_KEY",
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "",
        os.getenv("OPENROUTER_API_KEY") or "",
        os.getenv("OPENAI_API_KEY") or "",
        os.getenv("QA_PROVIDER", os.getenv("LLM_PROVIDER", "google")).lower(),
    )
    QA_BASE_URL: str = _agent_base_url(
        os.getenv("QA_PROVIDER", os.getenv("LLM_PROVIDER", "google")).lower(),
        "https://generativelanguage.googleapis.com/v1beta/openai/",
        os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    )


def validate_config() -> None:
    """
    Validate required environment variables at startup.
    Raises EnvironmentError with a clear message for any missing required var.
    """
    required = {
        "GEMINI_API_KEY": Config.GEMINI_API_KEY,
        "QDRANT_URL": Config.QDRANT_URL,
        "QDRANT_API_KEY": Config.QDRANT_API_KEY,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise EnvironmentError(
            f"\n[Neo Scripting] Startup failed — missing required environment variables:\n"
            + "\n".join(f"  - {name}" for name in missing)
            + "\n\nSet them in your .env file. See .env.example for reference."
        )

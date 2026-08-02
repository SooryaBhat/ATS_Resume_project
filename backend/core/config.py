import os
from pathlib import Path

# Load .env from the project root (two levels up from this file) explicitly —
# load_dotenv() with no args relies on caller-frame inspection that can fail
# silently under uvicorn reload, leaving env vars unset.
try:
    from dotenv import load_dotenv
    _ENV_PATH = Path(__file__).resolve().parents[2] / '.env'
    load_dotenv(_ENV_PATH)
except ImportError:
    pass

# ── App Metadata ──────────────────────────────────────────────────────────────
APP_TITLE       = 'TalentMatch AI API'
APP_VERSION     = '2.0.0'
APP_DESCRIPTION = 'AI-powered resume analysis and ATS scoring — TalentMatch AI'

# ── CORS Origins ──────────────────────────────────────────────────────────────
# Includes localhost ports used by the HTML/CSS/JS frontend during development.
ALLOWED_ORIGINS = [
    'https://talentmatchai-three.vercel.app',                        # Primary Vercel Production Deployment
    'https://talentmatchai-three.vercel.app',  # Vercel Deployment
    'https://talentmatch-ai-grv6.onrender.com',                      # Render Production Backend
    'http://localhost:3000',        # common Node dev server
    'http://127.0.0.1:3000',
    'http://localhost:5500',        # VS Code Live Server (default)
    'http://127.0.0.1:5500',        # VS Code Live Server (alternate)
    'http://localhost:5501',        # VS Code Live Server (second instance)
    'http://127.0.0.1:5501',
    'http://localhost:8080',        # Python http.server / other local servers
    'http://127.0.0.1:8080',
    'http://localhost:8000',        # FastAPI itself (Swagger UI / self-calls)
    'http://127.0.0.1:8000',
    'http://localhost:4200',        # Angular dev server
    'http://localhost:5173',        # Vite dev server
    'http://127.0.0.1:5173',
    'null',                         # file:// protocol (browser sends Origin: null)
    '*',                            # Production fallback for Vercel preview URLs
]

# ── File Upload Limits ────────────────────────────────────────────────────────
MAX_FILE_SIZE_MB    = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Supported MIME types and their short names
SUPPORTED_MIME_TYPES = {
    'application/pdf':    'pdf',
    'application/msword': 'doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
}
SUPPORTED_EXTENSIONS = {'.pdf', '.doc', '.docx'}

# ── NLP Models ────────────────────────────────────────────────────────────────
SPACY_MODEL_PRIMARY   = os.getenv('SPACY_MODEL_PRIMARY', 'en_core_web_sm')
SPACY_MODEL_SECONDARY = 'en_core_web_sm'

SENTENCE_TRANSFORMER_MODEL = os.getenv(
    'SENTENCE_TRANSFORMER_MODEL', 'all-MiniLM-L6-v2'
)

# ── Score Component Weights (business logic treated as config) ────────────────
SCORE_WEIGHTS = {
    'formatting': 20, 'keywords': 25, 'content': 25,
    'skill_validation': 15, 'ats_compatibility': 15,
}

JD_KEYWORD_WEIGHT  = 0.6
JD_SEMANTIC_WEIGHT = 0.4

# ── External Service Keys ─────────────────────────────────────────────────────
SUPABASE_URL        = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY        = os.getenv('SUPABASE_KEY', '')         # service_role — DB writes (bypasses RLS)
SUPABASE_ANON_KEY   = os.getenv('SUPABASE_ANON_KEY', '')    # public anon — safe to expose to frontend
SUPABASE_JWT_SECRET = os.getenv('SUPABASE_JWT_SECRET', '')  # used by backend to verify access tokens

GEMINI_API_KEY      = os.getenv('GEMINI_API_KEY', '')       # Google Gemini API key



import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import (
    ALLOWED_ORIGINS,
    APP_DESCRIPTION,
    APP_TITLE,
    APP_VERSION,
    SPACY_MODEL_PRIMARY,
    SPACY_MODEL_SECONDARY,
    SENTENCE_TRANSFORMER_MODEL,
)
from backend.api.routes import router

logger = logging.getLogger('ats_resume_scorer')


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info('Starting TalentMatch AI API...')

    logger.info(f'Loading spaCy NLP model: {SPACY_MODEL_PRIMARY}')
    import spacy
    try:
        app.state.nlp = spacy.load(SPACY_MODEL_PRIMARY)
        logger.info(f'Loaded {SPACY_MODEL_PRIMARY}')
    except OSError:
        logger.warning(f'{SPACY_MODEL_PRIMARY} not found — trying fallback {SPACY_MODEL_SECONDARY}')
        try:
            app.state.nlp = spacy.load(SPACY_MODEL_SECONDARY)
            logger.info(f'Loaded {SPACY_MODEL_SECONDARY} (fallback)')
        except OSError:
            logger.warning("Neither spacy model found — initializing spacy.blank('en')")
            app.state.nlp = spacy.blank('en')
            logger.info("Loaded spacy.blank('en') (emergency fallback)")


    logger.info(f'Loading SentenceTransformer: {SENTENCE_TRANSFORMER_MODEL}')
    from sentence_transformers import SentenceTransformer
    app.state.embedder = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)
    logger.info(f'Loaded {SENTENCE_TRANSFORMER_MODEL}')

    logger.info('All models loaded. TalentMatch AI API is ready.')

    yield

    logger.info('Shutting down TalentMatch AI API.')


app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url='/docs',
    redoc_url='/redoc',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(router)


@app.get('/')
async def root():
    return {
        'name':    'TalentMatch AI API',
        'version': '2.1.0',
        'llm':     'gemini-2.5-flash',
        'docs':    '/docs',
        'feature_groups': {
            'config_health':    ['GET /api/v1/config', 'GET /api/v1/health'],
            'analysis':         ['POST /api/v1/analyze-resume'],
            'history':          ['GET /api/v1/history', 'GET /api/v1/history/:id', 'PATCH /api/v1/history/:id', 'DELETE /api/v1/history/:id', 'DELETE /api/v1/history'],
            'reports':          ['POST /api/v1/generate-pdf', 'GET /api/v1/history/:id/pdf', 'GET /api/v1/reports', 'DELETE /api/v1/reports/:id'],
            'auth_profile':     ['GET /api/v1/auth/me', 'PATCH /api/v1/auth/profile'],
            'dashboard':        ['GET /api/v1/dashboard/stats'],
            'chat':             ['POST /api/v1/chat/sessions', 'GET /api/v1/chat/sessions', 'GET /api/v1/chat/sessions/:id/messages', 'POST /api/v1/chat/sessions/:id/message', 'DELETE /api/v1/chat/sessions/:id'],
            'job_descriptions': ['POST /api/v1/job-descriptions', 'GET /api/v1/job-descriptions', 'GET /api/v1/job-descriptions/:id', 'DELETE /api/v1/job-descriptions/:id', 'POST /api/v1/job-descriptions/:id/match', 'GET /api/v1/job-descriptions/matches'],
            'skill_gap':        ['POST /api/v1/skill-gap/generate', 'GET /api/v1/skill-gap', 'PATCH /api/v1/skill-gap/:id', 'DELETE /api/v1/skill-gap/:id'],
            'comparison':       ['POST /api/v1/compare', 'GET /api/v1/compare', 'DELETE /api/v1/compare/:id'],
            'tailoring':        ['POST /api/v1/tailor'],
            'notifications':    ['GET /api/v1/notifications', 'PATCH /api/v1/notifications/:id/read', 'GET /api/v1/activity'],
        },
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(
        'backend.main:app',
        host='0.0.0.0',
        port=8000,
        reload=True,
    )


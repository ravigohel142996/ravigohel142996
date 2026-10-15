"""Single source of truth for profile copy used by the artwork and the tests.

Project facts were checked against each repository's README, requirements and
source tree. Keep claims modest: link to source, never invent outcomes.
"""
from __future__ import annotations

from dataclasses import dataclass

from forge_svg import BLUE, CYAN, LAVENDER, MINT, PINK, VIOLET_SOFT

GITHUB = 'https://github.com/ravigohel142996'
LINKEDIN = 'https://www.linkedin.com/in/ravi-gohel/'
PORTFOLIO = 'https://portfolioravigohel.netlify.app/'
EMAIL = 'ravi.n.gohel811@gmail.com'


@dataclass(frozen=True)
class Section:
    number: str
    anchor: str
    title: str
    short: str
    codename: str
    subtitle: str
    accent: str


SECTIONS = (
    Section('01', 'the-human', 'The human behind the system', 'HUMAN', 'ORIGIN',
            '// who I am · what I build · where I am headed', CYAN),
    Section('02', 'build-archive', 'The build archive', 'ARCHIVE', 'ARCHIVE',
            '// six builds · every card opens its source code', VIOLET_SOFT),
    Section('03', 'tools-of-the-trade', 'Tools of the trade', 'TOOLS', 'ARSENAL',
            '// tools I use vs. frontiers I am exploring', BLUE),
    Section('04', 'proof-of-work', 'Proof of work', 'PROOF', 'EVIDENCE',
            '// real GitHub data · a dated snapshot, not live', LAVENDER),
    Section('05', 'next-mission', 'Next mission: let’s build', 'MISSION', 'MISSION',
            '// internships · jobs · hackathons · collaboration', PINK),
)


@dataclass(frozen=True)
class Project:
    slug: str
    name: str
    repo: str
    kicker: str
    focus: str
    description: str
    stack: tuple
    accent: str
    diagram: str

    @property
    def url(self) -> str:
        return f'{GITHUB}/{self.repo}'


PROJECTS = (
    Project('neurocore-ai', 'NeuroCore AI', 'NeuroCore-AI-The-Autonomous-Decision-Engine-for-Businesses',
            'DECISION INTELLIGENCE', 'Business forecasting, anomalies and decision intelligence.',
            'Revenue forecasts, churn prediction, cost-anomaly detection and decision simulation in a Streamlit dashboard.',
            ('Python', 'scikit-learn', 'Prophet', 'Streamlit'), CYAN, 'forecast'),
    Project('orbital-sentinel', 'Orbital Sentinel', 'Orbital-Sentinel-Earth-AI',
            'EARTH-RISK INTELLIGENCE', 'Earth-risk intelligence, data streams and AI reasoning.',
            'Multi-agent risk prediction for fires, floods, earthquakes and storms, with map views and voice alerts.',
            ('FastAPI', 'Kafka', 'Gemini', 'Streamlit'), BLUE, 'orbit'),
    Project('guardianvision-ai', 'GuardianVision AI', 'GuardianVision-AI',
            'COMPUTER VISION · SAFETY', 'Computer vision for PPE violations and workplace safety.',
            'Watches CCTV streams, detects missing PPE with a YOLO11 model, tracks workers and alerts safety teams.',
            ('YOLO11', 'OpenCV', 'FastAPI', 'Docker'), PINK, 'vision'),
    Project('loanguardian-ai', 'LoanGuardian AI', 'LoanGuardian-AI',
            'LENDING RISK · COMPLIANCE', 'Lending risk, compliance and origination.',
            'Credit-risk scoring, KYC/AML compliance checks and loan monitoring in one Streamlit workflow.',
            ('Python', 'Streamlit', 'Risk scoring', 'KYC/AML'), LAVENDER, 'gauge'),
    Project('enterprise-rag-os', 'Enterprise RAG OS', 'enterprise-rag-os',
            'RETRIEVAL-AUGMENTED GENERATION', 'Retrieval-augmented generation and Groq workflows.',
            'Chunks and embeds documents into ChromaDB, retrieves top-k context and answers with LLaMA 3 via Groq.',
            ('ChromaDB', 'Groq', 'LLaMA 3', 'Jupyter'), VIOLET_SOFT, 'retrieval'),
    Project('relief-mate-ai', 'Relief Mate AI', 'Relief_mate_ai',
            'AI FOR DISASTER SUPPORT', 'Disaster-support information and assistance.',
            'Gemini-powered summaries, request triage and multilingual help, with a React + Tailwind landing page.',
            ('Gemini', 'Streamlit', 'React', 'Tailwind'), MINT, 'relief'),
)

# Hands-on tools, kept separate from topics still being explored.
TOOLS = (
    ('Python', 'LANGUAGE', 'py'),
    ('JavaScript', 'LANGUAGE', 'js'),
    ('HTML / CSS', 'MARKUP · STYLE', 'html'),
    ('React', 'FRONTEND', 'react'),
    ('Node.js', 'RUNTIME', 'node'),
    ('Streamlit', 'DATA APPS', 'stream'),
    ('MySQL', 'DATABASE', 'db'),
    ('Jupyter', 'NOTEBOOKS', 'jupyter'),
    ('Git / GitHub', 'VERSION CONTROL', 'git'),
    ('Linux', 'OPERATING SYSTEM', 'terminal'),
    ('VS Code', 'EDITOR', 'editor'),
)
EXPLORING = (
    ('Machine learning', 'models · evaluation · real data', 'ml'),
    ('Computer vision', 'detection · tracking · safety', 'cv'),
    ('GenAI / RAG', 'retrieval · grounding · LLM apps', 'genai'),
)
INTERESTS = ('PRACTICAL AI', 'MACHINE LEARNING', 'COMPUTER VISION', 'GENAI', 'RAG', 'AUTOMATION', 'FULL-STACK')

CONTACTS = (
    ('linkedin', 'LinkedIn', LINKEDIN, 'linkedin.com/in/ravi-gohel', 'CONNECT', CYAN),
    ('portfolio', 'Portfolio', PORTFOLIO, 'portfolioravigohel.netlify.app', 'VISIT', VIOLET_SOFT),
    ('email', 'Email', f'mailto:{EMAIL}', EMAIL, 'WRITE', PINK),
)

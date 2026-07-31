# 🚀 TalentMatch AI
### AI-Powered Resume Analysis, ATS Optimization & Career Intelligence Platform

TalentMatch AI is a full-stack AI-powered web application that helps job seekers optimize their resumes for Applicant Tracking Systems (ATS), compare resumes against job descriptions, identify skill gaps, generate personalized career roadmaps, tailor resumes for specific roles, and receive AI-powered career guidance.

Built using **FastAPI**, **Supabase**, **Google Gemini AI**, **spaCy**, and **Sentence Transformers**, the platform combines Natural Language Processing (NLP), Semantic Search, and Generative AI to deliver intelligent resume insights.

---
# 🚀 Live Links

| Service | Link |
|---------|------|
| 🌐 Web App | https://talentmatchai-three.vercel.app |
| ⚙️ Backend API | https://talentmatch-ai-grv6.onrender.com |
| 📖 API Docs | https://talentmatch-ai-grv6.onrender.com/docs |

## 🌟 Features

### 👤 Authentication
- Secure User Registration & Login
- JWT Authentication
- Password Reset
- Profile Management
- Protected Routes

### 📄 Resume Analysis
- Upload Resume (PDF, DOC, DOCX)
- Resume Parsing
- ATS Compatibility Analysis
- Resume Quality Evaluation
- Section Completeness Check
- Keyword Optimization
- AI-Based Suggestions

### 🎯 ATS Score Engine
- Overall ATS Score
- Detailed Score Breakdown
- Formatting Analysis
- Keyword Analysis
- Content Evaluation
- ATS Compatibility Score
- Improvement Recommendations

### 💼 Job Description Matching
- Paste or Upload Job Description
- Required Skill Extraction
- Resume vs JD Matching
- Match Percentage
- Missing Skills Detection
- Semantic Similarity Analysis

### 📚 Skill Gap Analysis
- Current Skill Assessment
- Missing Skills Identification
- Personalized Learning Roadmap
- Recommended Projects
- Estimated Learning Timeline

### 📝 Resume Tailoring
- AI Resume Optimization
- Job-Specific Resume Suggestions
- ATS Keyword Enhancement
- Improved Resume Summary
- Better Experience Descriptions

### 🤖 AI Career Assistant
- Resume Guidance
- Career Advice
- Interview Preparation
- Learning Recommendations
- Resume Improvement Suggestions

### 📊 Dashboard
- Resume Analysis History
- ATS Score Trends
- Job Match History
- Skill Progress
- Notifications
- Activity Timeline

### 📄 PDF Report Generation
Generate professional reports containing:
- ATS Score
- Resume Summary
- Skill Analysis
- Job Match Report
- AI Suggestions
- Career Roadmap

---

# 🧠 AI Pipeline

```
Resume Upload
        │
        ▼
Document Parsing
        │
        ▼
Text Cleaning & Preprocessing
        │
        ▼
spaCy NLP Processing
        │
        ▼
Sentence Transformer Embeddings
        │
        ▼
ATS Scoring Engine
        │
        ▼
Gemini AI Analysis
        │
        ▼
Recommendations & Reports
        │
        ▼
Dashboard & PDF Export
```

---

# 🏗️ System Architecture

```
                   User
                     │
                     ▼
      HTML • CSS • JavaScript Frontend
                     │
                     ▼
             FastAPI REST API
                     │
     ┌───────────────┼────────────────┐
     │               │                │
     ▼               ▼                ▼
 Supabase      Gemini AI        NLP Engine
(PostgreSQL)                  spaCy + Sentence
                                 Transformers
     │               │                │
     └───────────────┼────────────────┘
                     ▼
             ATS Scoring Engine
                     ▼
       Dashboard • Reports • History
```

---

# 🛠 Tech Stack

## Frontend
- HTML5
- CSS3
- JavaScript (ES6)
- Chart.js
- Fetch API

## Backend
- FastAPI
- Python
- Uvicorn
- Pydantic
- JWT Authentication

## Artificial Intelligence
- Google Gemini 2.5 Flash
- spaCy
- Sentence Transformers
- NLP
- Semantic Search

## Database & Authentication
- Supabase PostgreSQL
- Supabase Auth
- Supabase Storage

## File Processing
- PyPDF2
- python-docx
- ReportLab

## Cloud Deployment
- Vercel
- Render
- Supabase

## Development Tools
- Git
- GitHub
- VS Code
- Postman
- Jupyter Notebook

---

# 📂 Project Structure

```
TalentMatch-AI/
│
├── backend/
│   ├── api/
│   ├── services/
│   ├── models/
│   ├── core/
│   ├── utils/
│   └── main.py
│
├── frontend/
│   ├── css/
│   ├── js/
│   ├── assets/
│   └── index.html
│
├── notebooks/
│
├── uploads/
│
├── reports/
│
├── requirements.txt
│
└── README.md
```

---

# ⚙️ Installation

## Clone Repository

```bash
git clone https://github.com/yourusername/TalentMatch-AI.git

cd TalentMatch-AI
```

## Backend Setup

```bash
python -m venv venv

source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file

```env
SUPABASE_URL=YOUR_SUPABASE_URL
SUPABASE_KEY=YOUR_SUPABASE_SERVICE_KEY
SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
SUPABASE_JWT_SECRET=YOUR_JWT_SECRET

GEMINI_API_KEY=YOUR_GEMINI_API_KEY
```

Start Backend

```bash
uvicorn backend.main:app --reload
```

---

## Frontend

Simply open

```
index.html
```

or use

```bash
python -m http.server
```

---

# 📡 API Modules

- Authentication
- Resume Analysis
- ATS Scoring
- Job Description Matching
- Resume Comparison
- Skill Gap Analysis
- Resume Tailoring
- Dashboard
- History
- Reports
- Notifications
- AI Chat

---

# 🔒 Security

- JWT Authentication
- Protected Routes
- Secure API Access
- Environment Variables
- Input Validation
- File Validation
- Password Hashing
- CORS Protection

---

# 🚀 Deployment

| Service | Platform |
|----------|----------|
| Frontend | Vercel |
| Backend | Render |
| Database | Supabase PostgreSQL |
| Authentication | Supabase Auth |
| Storage | Supabase Storage |

---

# 📈 Future Improvements

- Multi-language Resume Support
- Recruiter Dashboard
- Company Job Portal Integration
- Resume Version Control
- AI Interview Simulator
- LinkedIn Profile Analysis
- GitHub Portfolio Analysis
- Real-Time Job Recommendations

---

# 🤝 Contributing

Contributions, feature requests, and suggestions are welcome!

1. Fork the repository
2. Create a new branch
3. Commit your changes
4. Push your branch
5. Open a Pull Request

---

# 📜 License

This project is licensed under the MIT License.

---

# 👨‍💻 Developer

**Soorya Vighneshwar Bhat**

AI & Data Science Engineering Student

Interested in:
- Artificial Intelligence
- Machine Learning
- NLP
- Data Science
- Generative AI
- Computer Vision
- Full-Stack AI Applications

---

⭐ If you found this project useful, consider giving it a **Star** on GitHub!

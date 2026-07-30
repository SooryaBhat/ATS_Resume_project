/* ==========================================================================
   TalentMatch AI - Comprehensive Mock Datasets (Frontend ONLY)
   ========================================================================== */

const MockData = {
  // User Profile Data
  user: {
    name: "Alex Morgan",
    email: "alex.morgan@talentmatch.ai",
    avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=256&q=80",
    role: "Senior Full Stack Engineer",
    targetRole: "Lead AI Systems Architect",
    plan: "Pro Analyst",
    scansRemaining: 24,
    scansLimit: 30,
    skills: ["Python", "TypeScript", "React", "FastAPI", "PyTorch", "PostgreSQL", "Docker", "AWS"]
  },

  // Notification Alerts List (Top Nav Dropdown)
  notifications: [
    { id: 1, title: "Resume Analyzed", desc: "Alex_Morgan_AI_Engineer.pdf scored 94/100", time: "10m ago", icon: "fa-circle-check", type: "success" },
    { id: 2, title: "Skill Gap Alert", desc: "Missing Kubernetes & Terraform for Google Target Role", time: "1h ago", icon: "fa-triangle-exclamation", type: "warning" },
    { id: 3, title: "Report Ready", desc: "PDF Summary ready for download", time: "3h ago", icon: "fa-file-pdf", type: "info" }
  ],

  // Activity Feed (Dashboard)
  activityFeed: [
    { title: "Analyzed Resume Version 2.0", time: "Today at 18:45", icon: "fa-file-circle-check", desc: "Overall score improved from 84 to 89" },
    { title: "Ran JD Match Engine against Google DeepMind", time: "Yesterday at 14:20", icon: "fa-bullseye", desc: "Achieved 92% semantic match score" },
    { title: "Exported Full PDF Analysis Report", time: "2 days ago", icon: "fa-file-pdf", desc: "Downloaded talentmatch_report_v2.pdf" }
  ],

  // Overview Dashboard Metrics
  dashboardMetrics: {
    overallAtsAvg: 89,
    healthIndex: 94,
    scansCompleted: 18,
    targetMatchPercentage: 91,
    recentResumesCount: 5
  },

  // ATS Score History Trend Chart Data
  scoreTrend: {
    labels: ["v1.0 Baseline", "v1.1 Added Quant", "v1.2 Fixed Keywords", "v1.3 Skill Align", "v2.0 TalentMatch Optimized"],
    scores: [62, 71, 79, 84, 92]
  },

  // Component Radar Scores
  componentBreakdown: {
    labels: ["Formatting", "Keywords & Skills", "Content Quality", "Skill Validation", "ATS Compatibility"],
    scores: [18.5, 23.0, 22.5, 13.5, 14.5], // Maxes out of 20, 25, 25, 15, 15
    percentages: [92.5, 92.0, 90.0, 90.0, 96.6]
  },

  // Keyword Distribution Doughnut Chart
  keywordDistribution: {
    labels: ["Technical Stack", "Domain Expertise", "Soft Skills / Leadership", "Tools & Infrastructure"],
    counts: [14, 8, 5, 7]
  },

  // Sample Single Resume Analysis (Detailed Output)
  sampleAnalysis: {
    ats_score: 89,
    filename: "Alex_Morgan_Senior_FullStack_Resume.pdf",
    uploaded_at: "2026-07-29 18:45 UTC",
    interpretation: "Excellent! Your resume exhibits top-tier ATS compatibility and strong metric-driven accomplishments.",
    job_title: "Senior Full-Stack & AI Engineer",
    component_scores: {
      formatting: 18.5,
      keywords: 23.0,
      content: 22.0,
      skill_validation: 13.5,
      ats_compatibility: 14.5
    },
    skills: [
      "Python", "FastAPI", "TypeScript", "React", "Next.js", "Docker",
      "PostgreSQL", "PyTorch", "Groq API", "spaCy", "Sentence-Transformers",
      "TailwindCSS", "Git", "CI/CD", "AWS Lambda"
    ],
    matched_keywords: [
      "FastAPI", "Python", "TypeScript", "React", "PostgreSQL",
      "Docker", "PyTorch", "REST APIs", "CI/CD", "AWS", "Microservices"
    ],
    missing_keywords: [
      "Kubernetes", "GraphQL", "Redis Caching", "Terraform"
    ],
    strengths: [
      "Explicit quantified bullet points with measurable impact (+45% latency reduction).",
      "Dedicated Projects section with live GitHub repository URLs.",
      "Clean single-column ATS layout with standardized section headers.",
      "91% of claimed technical skills are validated by project evidence."
    ],
    detailed_feedback: [
      {
        issue_title: "Missing Cloud Infrastructure Keywords",
        severity_level: "Medium",
        ats_impact: "-4 Points on Keyword Density",
        explanation: "The job target frequently highlights Kubernetes and Terraform for DevOps deployment.",
        where_it_appears: "Skills & Technical Stack section",
        how_to_fix: "Add Terraform or Kubernetes under Infrastructure/DevOps if you have hands-on experience.",
        action_items: [
          "List Kubernetes under DevOps skills",
          "Mention container orchestration in your second work experience bullet point"
        ]
      },
      {
        issue_title: "Unvalidated Skill: GraphQL",
        severity_level: "Low",
        ats_impact: "-1.5 Points on Skill Validation",
        explanation: "GraphQL is listed under Skills but not referenced in any project bullet point.",
        where_it_appears: "Skills section",
        how_to_fix: "Tie GraphQL to a project or remove it to maintain 100% skill validation integrity.",
        action_items: [
          "Add a project bullet: 'Implemented GraphQL API for real-time analytics panel'"
        ]
      }
    ],
    recommendations: [
      {
        title: "Incorporate Container Orchestration Keywords",
        description: "Add Kubernetes and Helm charts to your DevOps skills list to match Senior AI Lead requirements.",
        priority_label: "High Priority",
        priority_value: "high",
        priority_icon: "🟠",
        impact_score: 5.0,
        category: "keywords",
        action_items: [
          "Include 'Kubernetes (K8s)' in Skills section",
          "Highlight Docker & Kubernetes container deployment in Project #1"
        ]
      },
      {
        title: "Standardize Phone Number Formatting",
        description: "Format phone number in standard international format (+1 xxx-xxx-xxxx) to prevent parsing errors.",
        priority_label: "Low Priority",
        priority_value: "low",
        priority_icon: "🟢",
        impact_score: 1.5,
        category: "formatting",
        action_items: ["Use standard international format (+1-555-019-2831)"]
      }
    ]
  },

  // Multi-Resume Comparison Dataset
  resumeComparison: [
    {
      name: "Version A - FullStack Focus",
      atsScore: 89,
      formatting: 18.5,
      keywords: 23.0,
      content: 22.0,
      skillValidation: 13.5,
      atsCompatibility: 14.5,
      wordCount: 485,
      skillsCount: 15,
      verdict: "Best overall for Web/SaaS roles"
    },
    {
      name: "Version B - AI/ML Focused",
      atsScore: 94,
      formatting: 19.0,
      keywords: 24.5,
      content: 23.5,
      skillValidation: 14.0,
      atsCompatibility: 14.8,
      wordCount: 520,
      skillsCount: 18,
      verdict: "Recommended for AI Architect roles"
    },
    {
      name: "Version C - Generalist Tech Lead",
      atsScore: 78,
      formatting: 16.0,
      keywords: 19.5,
      content: 20.0,
      skillValidation: 11.0,
      atsCompatibility: 13.0,
      wordCount: 410,
      skillsCount: 11,
      verdict: "Needs keyword enhancement"
    }
  ],

  // Job Description Matching Dataset (One Resume vs Multiple JDs)
  jdMatchList: [
    {
      company: "Google / DeepMind Target",
      role: "Senior AI Applications Engineer",
      matchScore: 92,
      semanticSim: 0.89,
      matchedCount: 14,
      missingCount: 2,
      missingKeywords: ["JAX", "TPU optimization"],
      status: "Highly Qualified"
    },
    {
      company: "Stripe",
      role: "Staff Backend Engineer (Python/API)",
      matchScore: 88,
      semanticSim: 0.84,
      matchedCount: 12,
      missingCount: 3,
      missingKeywords: ["Ruby", "Distributed Locking", "gRPC"],
      status: "Strong Match"
    },
    {
      company: "OpenAI",
      role: "Full Stack AI Developer",
      matchScore: 95,
      semanticSim: 0.94,
      matchedCount: 16,
      missingCount: 1,
      missingKeywords: ["Triton"],
      status: "Top Match"
    }
  ],

  // Skill Gap Roadmap Dataset
  skillGapRoadmap: [
    {
      skill: "Kubernetes & Helm",
      priority: "Critical",
      category: "DevOps",
      estimatedHours: "15 Hours",
      status: "In Progress",
      roadmap: [
        "Module 1: Docker Container Multi-stage Builds",
        "Module 2: Pods, Services, and Deployments in K8s",
        "Module 3: Deploying FastAPI Microservices with Helm Charts"
      ]
    },
    {
      skill: "Redis Distributed Caching",
      priority: "High",
      category: "Backend Performance",
      estimatedHours: "8 Hours",
      status: "Not Started",
      roadmap: [
        "Module 1: Redis Key-Value Store & Memory Policies",
        "Module 2: Caching FastAPI Endpoint Responses with Redis"
      ]
    },
    {
      skill: "GraphQL with Strawberry Python",
      priority: "Medium",
      category: "API Architecture",
      estimatedHours: "10 Hours",
      status: "Not Started",
      roadmap: [
        "Module 1: GraphQL Schemas, Queries, and Mutations",
        "Module 2: Integrating GraphQL subgraphs into FastAPI"
      ]
    }
  ],

  // AI Resume Assistant Chat Presets & Sample Chat History
  chatHistory: [
    {
      sender: "assistant",
      text: "Hello Alex! I am your **TalentMatch AI Assistant**. I can help you reword bullet points, optimize your summary for specific job descriptions, or answer any ATS formatting questions. How can I assist your job search today?"
    }
  ],

  chatPresets: [
    "🚀 Rewrite my summary for an AI Lead role at Google",
    "📊 Generate 3 high-impact bullet points with metrics",
    "🔑 What missing keywords should I add for Staff Engineer?",
    "⚡ Convert passive verbs into strong action verbs"
  ],

  // Saved Analyses History List
  historyList: [
    {
      id: "an_99812",
      filename: "Alex_Morgan_AI_Engineer_2026.pdf",
      date: "2026-07-29",
      atsScore: 94,
      jobTitle: "Senior AI Engineer",
      matchedKeywords: 18,
      status: "Optimized"
    },
    {
      id: "an_99811",
      filename: "Alex_Morgan_FullStack_Resume_v2.pdf",
      date: "2026-07-27",
      atsScore: 89,
      jobTitle: "Full Stack Engineer",
      matchedKeywords: 14,
      status: "Good"
    },
    {
      id: "an_99810",
      filename: "Alex_Morgan_Draft_Jul2026.pdf",
      date: "2026-07-20",
      atsScore: 76,
      jobTitle: "Backend Software Engineer",
      matchedKeywords: 9,
      status: "Needs Work"
    }
  ]
};

// Freeze object to protect mock integrity
Object.freeze(MockData);

# TalentMatch AI — Portfolio & SaaS Showcase Landing Page

An ultra-modern, dark glassmorphism SaaS showcase website for **TalentMatch AI** — an AI-Powered Resume Analysis, ATS Optimization & Career Intelligence Platform.

Designed with inspiration from Stripe, Linear, Vercel, Notion AI, and OpenAI.

---

## 🚀 Live Links

- 🌐 **Live Web Application**: [https://talentmatchai-three.vercel.app](https://talentmatchai-three.vercel.app)
- ⚡ **Backend API**: [https://talentmatch-ai-grv6.onrender.com](https://talentmatch-ai-grv6.onrender.com)
- 🐙 **GitHub Repository**: [https://github.com/SooryaBhat/ATS_Resume_project.git](https://github.com/SooryaBhat/ATS_Resume_project.git)
- 👤 **Developer Profile**: [Soorya Bhat GitHub](https://github.com/SooryaBhat) | [LinkedIn Profile](https://www.linkedin.com/in/sooryabhat)

---

## 🛠️ Technology Stack

- **Frontend Core**: Vanilla HTML5, CSS3, JavaScript (ES6+)
- **Styling**: Modern CSS Custom Properties, Dark Glassmorphism, Responsive Grid & Flexbox
- **Animations**: Intersection Observer, Keyframe Physics, Custom Mouse Glow & 3D Card Tilt Effects
- **Mockups**: Apple-style Safari MacBook Browser Frames showcasing real application screenshots

---

## 📦 Project Structure

```
TalentMatch-Landing/
├── index.html
├── assets/
│   ├── css/
│   │   ├── variables.css      # Design tokens (colors, gradients, typography)
│   │   ├── main.css           # Resets, navbar, buttons & global layout
│   │   ├── components.css     # Glass cards, mockups, architecture flowchart
│   │   └── animations.css     # Keyframes & scroll reveal classes
│   ├── js/
│   │   ├── main.js            # Navbar scroll blur, mobile menu, button event routing
│   │   ├── animations.js      # Scroll reveal observer & metric counter logic
│   │   └── glass-effects.js   # Mouse-follow glow & 3D tilt micro-interactions
│   └── screenshots/           # Application UI screenshots
└── README.md
```

---

## 💻 Running Locally

Simply serve the folder using any HTTP server, or open `index.html` directly in your browser:

```bash
# Using Python
cd TalentMatch-Landing
python -m http.server 3000

# Or using npx serve
npx serve .
```

Open `http://localhost:3000` in your browser.

---

## ⚡ Deploying to Vercel

1. Push `TalentMatch-Landing` to a GitHub repository or subfolder.
2. Go to [Vercel Dashboard](https://vercel.com/dashboard) ➔ **Add New Project**.
3. Select the repository and set the root directory to `TalentMatch-Landing`.
4. Click **Deploy**! (Zero build configuration required since it uses pure HTML/CSS/JS).

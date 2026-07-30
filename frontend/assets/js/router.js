/* ==========================================================================
   TalentMatch AI - SPA Hash Router & View Switcher (App-First Flow)
   ========================================================================== */

const Router = {
  routes: [
    'dashboard', 'analyze', 'compare', 'jd-match',
    'skill-gap', 'chat', 'history', 'profile',
    'login', 'register'
  ],

  init() {
    window.addEventListener('hashchange', () => this.handleRoute());
    this.handleRoute(); // Initial route on page load
  },

  handleRoute() {
    const rawHash = window.location.hash.replace('#', '') || 'dashboard';
    const route = this.routes.includes(rawHash) ? rawHash : 'dashboard';

    // Hide all view sections
    document.querySelectorAll('.page-view').forEach(view => {
      view.classList.remove('active');
    });

    // Show target active view
    const activeView = document.getElementById(`view-${route}`);
    if (activeView) {
      activeView.classList.add('active');
    }

    // Toggle Auth vs App Layout (Sidebar & Header display)
    const isAuth = ['login', 'register'].includes(route);
    const appSidebar = document.querySelector('.app-sidebar');
    const appHeader = document.querySelector('.app-header');

    if (isAuth) {
      if (appSidebar) appSidebar.style.display = 'none';
      if (appHeader) appHeader.style.display = 'none';
    } else {
      if (appSidebar) appSidebar.style.display = 'flex';
      if (appHeader) appHeader.style.display = 'flex';
    }

    // Update active state in Sidebar Links
    document.querySelectorAll('.sidebar-link').forEach(link => {
      const targetHash = link.getAttribute('href')?.replace('#', '');
      if (targetHash === route) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });

    // Update Top Header Page Title
    const headerTitle = document.getElementById('header-page-title');
    if (headerTitle) {
      const titles = {
        dashboard: "Dashboard Overview",
        analyze: "Resume Analysis & Scoring",
        compare: "Multi-Resume Comparison",
        "jd-match": "Job Description Matching",
        "skill-gap": "Skill Gap & Learning Roadmap",
        chat: "AI Resume Assistant",
        history: "Analysis History",
        profile: "Account Profile & Settings"
      };
      headerTitle.textContent = titles[route] || "TalentMatch AI";
    }

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Initialize View Specific Logic / Charts
    this.onViewLoaded(route);
  },

  onViewLoaded(route) {
    if (route === 'dashboard') {
      setTimeout(() => ChartEngine.rebuildCharts(), 100);
    } else if (route === 'compare') {
      setTimeout(() => ChartEngine.initComparisonBarChart('comparisonBarChart', MockData.resumeComparison), 100);
    }
  },

  navigate(route) {
    window.location.hash = `#${route}`;
  }
};

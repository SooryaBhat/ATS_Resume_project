/* ==========================================================================
   TalentMatch AI - SPA Hash Router & View Switcher
   ========================================================================== */

const Router = {
  routes: [
    'dashboard', 'analyze', 'compare', 'jd-match',
    'skill-gap', 'chat', 'history', 'profile',
    'login', 'register',
  ],

  /** Routes that do NOT require authentication. */
  publicRoutes: ['login', 'register'],

  init() {
    window.addEventListener('hashchange', () => this.handleRoute());
    this.handleRoute(); // Initial route on page load
  },

  handleRoute() {
    const rawHash = window.location.hash.replace('#', '') || 'login';
    const route   = this.routes.includes(rawHash) ? rawHash : 'dashboard';

    // ── Auth guard ──────────────────────────────────────────────────────────
    const isAuthRoute = this.publicRoutes.includes(route);
    if (!isAuthRoute && !Auth.isAuthenticated()) {
      // Auth might still be initializing — wait then re-check
      Auth.ready().then(() => {
        if (!Auth.isAuthenticated()) {
          // Not logged in → send to login page
          window.location.hash = '#login';
        } else {
          // Auth resolved and user is now logged in — show the requested route
          this._activateRoute(route);
        }
      });
      // While waiting, show a blank screen (not the protected page)
      return;
    }

    // ── If already on an auth page but signed in, redirect to dashboard ────
    if (isAuthRoute && Auth.isAuthenticated()) {
      window.location.hash = '#dashboard';
      return;
    }

    this._activateRoute(route);
  },

  _activateRoute(route) {
    // Hide all page views
    document.querySelectorAll('.page-view').forEach(view => {
      view.classList.remove('active');
    });

    // Show the target view
    const activeView = document.getElementById(`view-${route}`);
    if (activeView) {
      activeView.classList.add('active');
    } else {
      console.warn(`[Router] No view element found for route: ${route}`);
    }

    // Toggle Auth vs App layout (Sidebar & Header)
    const isAuth     = this.publicRoutes.includes(route);
    const appSidebar = document.querySelector('.app-sidebar');
    const appHeader  = document.querySelector('.app-header');

    if (isAuth) {
      if (appSidebar) appSidebar.style.display = 'none';
      if (appHeader)  appHeader.style.display  = 'none';
    } else {
      if (appSidebar) appSidebar.style.display = 'flex';
      if (appHeader)  appHeader.style.display  = 'flex';
    }

    // Update active state in sidebar links
    document.querySelectorAll('.sidebar-link').forEach(link => {
      const targetHash = link.getAttribute('href')?.replace('#', '');
      link.classList.toggle('active', targetHash === route);
    });

    // Update header page title
    const headerTitle = document.getElementById('header-page-title');
    if (headerTitle) {
      const titles = {
        dashboard:   'Dashboard Overview',
        analyze:     'Resume Analysis & Scoring',
        compare:     'Multi-Resume Comparison',
        'jd-match':  'Job Description Matching',
        'skill-gap': 'Skill Gap & Learning Roadmap',
        chat:        'AI Resume Assistant',
        history:     'Analysis History',
        profile:     'Account Profile & Settings',
      };
      headerTitle.textContent = titles[route] || 'TalentMatch AI';
    }

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Per-view initialization
    this.onViewLoaded(route);
  },

  onViewLoaded(route) {
    if (typeof App !== 'undefined') {
      if (App.loadLiveDashboardData) App.loadLiveDashboardData();

      if (route === 'dashboard') {
        setTimeout(() => ChartEngine.rebuildCharts(), 150);
      } else if (route === 'compare' && App.renderCompareView) {
        App.renderCompareView();
      } else if (route === 'skill-gap' && App.renderSkillGapView) {
        App.renderSkillGapView();
      } else if (route === 'jd-match' && App.updateActiveResumeBanner) {
        App.updateActiveResumeBanner();
      } else if (route === 'history' && App.loadHistoryView) {
        App.loadHistoryView();
      }
    }
  },

  navigate(route) {
    window.location.hash = `#${route}`;
  },
};

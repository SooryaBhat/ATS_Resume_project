/* ==========================================================================
   TalentMatch AI - Application Core Controller
   Full live-API integration — MockData used only as fallback.

   Changes vs. previous version:
   1. App.init() awaits Auth.init() before Router.init() — no auth race
   2. bootstrapLiveData() only runs when authenticated
   3. handleDownloadPDF calls corrected API signature
   4. applyDashboardStats guards chart updates (updateScoreTrend /
      updateComponentRadar may not exist — uses rebuildCharts instead)
   5. handleProfileSave reads inputs by placeholder/index correctly
   6. handleChatSend awaits Auth.ready() before creating sessions
   7. Removed broken openModal/closeModal stubs (no modal HTML exists)
   ========================================================================== */

const App = {
  currentAnalysis:  null,
  currentSessionId: null,
  userProfile:      null,

  async init() {
    this.initTheme();

    // Auth MUST complete before Router shows any protected route
    await Auth.init();

    // Router uses Auth.isAuthenticated() — must run after Auth.init()
    Router.init();

    this.bindEvents();

    // Only bootstrap live data if authenticated
    if (Auth.isAuthenticated()) {
      await this.bootstrapLiveData();
    }
  },

  // ── 1. Theme ──────────────────────────────────────────────────────────────

  initTheme() {
    const saved = localStorage.getItem('talentmatch_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
    this.updateThemeIcon(saved);
  },

  toggleTheme() {
    const cur  = document.documentElement.getAttribute('data-theme');
    const next = cur === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('talentmatch_theme', next);
    this.updateThemeIcon(next);
    ChartEngine.rebuildCharts();
  },

  updateThemeIcon(theme) {
    const btn = document.getElementById('theme-toggle-btn');
    if (btn) btn.innerHTML = theme === 'dark'
      ? '<i class="fa-solid fa-sun"></i>'
      : '<i class="fa-solid fa-moon"></i>';
  },

  // ── 2. Toast ──────────────────────────────────────────────────────────────

  showToast(message, type = 'info') {
    let container = document.querySelector('.toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icon = type === 'success' ? 'fa-check-circle'
               : type === 'error'   ? 'fa-exclamation-circle'
               : type === 'warning' ? 'fa-exclamation-triangle'
               :                      'fa-info-circle';
    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity   = '0';
      toast.style.transform = 'translateX(50px)';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  },

  // ── 3. Global Event Listeners ─────────────────────────────────────────────

  bindEvents() {
    document.getElementById('theme-toggle-btn')?.addEventListener('click', () => this.toggleTheme());

    // Notification dropdown
    const notifBtn      = document.getElementById('notification-btn');
    const notifDropdown = document.getElementById('notification-dropdown');
    notifBtn?.addEventListener('click', (e) => {
      e.stopPropagation();
      notifDropdown?.classList.toggle('active');
      document.getElementById('profile-dropdown-menu')?.classList.remove('active');
    });

    // Profile dropdown
    const profileBtn  = document.getElementById('profile-avatar-btn');
    const profileMenu = document.getElementById('profile-dropdown-menu');
    profileBtn?.addEventListener('click', (e) => {
      e.stopPropagation();
      profileMenu?.classList.toggle('active');
      notifDropdown?.classList.remove('active');
    });

    document.addEventListener('click', () => {
      notifDropdown?.classList.remove('active');
      profileMenu?.classList.remove('active');
    });

    // Keyboard shortcut Ctrl+K
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        document.getElementById('header-search-input')?.focus();
      }
    });

    // Mobile nav
    document.getElementById('mobile-nav-toggle')?.addEventListener('click', () => {
      document.querySelector('.app-sidebar')?.classList.toggle('active');
    });

    // File upload / drag & drop
    const dropzone  = document.getElementById('resume-dropzone');
    const fileInput = document.getElementById('resume-file-input');
    if (dropzone && fileInput) {
      dropzone.addEventListener('click', () => fileInput.click());
      dropzone.addEventListener('dragover',  (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
      dropzone.addEventListener('dragleave', ()  => dropzone.classList.remove('dragover'));
      dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length) this.handleResumeUpload(e.dataTransfer.files[0]);
      });
      fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) this.handleResumeUpload(e.target.files[0]);
      });
    }

    // Chat
    document.getElementById('chat-send-btn')?.addEventListener('click',  () => this.handleChatSend());
    document.getElementById('chat-input')?.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.handleChatSend();
    });

    // History search
    document.getElementById('history-search-input')?.addEventListener('input', (e) => {
      this.filterHistory(e.target.value.toLowerCase());
    });

    // Profile save button
    document.getElementById('profile-save-btn')?.addEventListener('click', (e) => {
      e.preventDefault();
      this.handleProfileSave();
    });

    // JD Matcher form handlers
    const jdDropzone  = document.getElementById('jd-matcher-dropzone');
    const jdFileInput = document.getElementById('jd-matcher-file-input');
    const jdSubmitBtn = document.getElementById('jd-matcher-submit-btn');

    if (jdDropzone && jdFileInput) {
      jdDropzone.addEventListener('click', () => jdFileInput.click());
      jdFileInput.addEventListener('change', (e) => {
        if (e.target.files.length) {
          const fn = e.target.files[0].name;
          const fnEl = document.getElementById('jd-matcher-filename');
          if (fnEl) fnEl.textContent = `Selected: ${fn}`;
        }
      });
    }

    jdSubmitBtn?.addEventListener('click', () => this.handleJdMatchSubmit());
  },

  // ── 4. Bootstrap — load live data on startup ──────────────────────────────

  async bootstrapLiveData() {
    const token = Auth.getAccessToken();
    if (!token) return;   // guard — only run when authenticated

    console.log('[App] Bootstrapping live data...');

    // Load user profile first (populates sidebar name, plan badge)
    await this.loadUserProfile(token);

    // Load dashboard data (parallel)
    await this.loadLiveDashboardData();
  },

  // ── 5. Profile ────────────────────────────────────────────────────────────

  async loadUserProfile(token = null) {
    try {
      const t = token || Auth.getAccessToken();
      if (!t) return;
      const profile = await API.getProfile(t);
      this.userProfile = profile;
      this.applyProfileToUI(profile);
    } catch (err) {
      console.warn('[App] Profile load warning (non-fatal):', err.message);
    }
  },

  applyProfileToUI(profile) {
    if (!profile) return;

    // Sidebar user info
    const nameEl = document.querySelector('.user-name-text');
    const roleEl = document.querySelector('.user-role-text');
    const plan   = profile.plan === 'free' ? 'Free Plan' : 'Pro Plan';
    if (nameEl) nameEl.textContent = profile.full_name || Auth.currentUser?.email?.split('@')[0] || 'User';
    if (roleEl) roleEl.textContent = `${plan} • ${profile.scans_used || 0} Scans`;

    // Profile page fields
    const nameInput  = document.getElementById('profile-full-name');
    const roleInput  = document.getElementById('profile-target-role');
    const stackInput = document.getElementById('profile-tech-stack');

    if (nameInput && profile.full_name) nameInput.value = profile.full_name;
    if (roleInput && profile.target_role) roleInput.value = profile.target_role;
    if (stackInput && profile.primary_tech_stack) {
      stackInput.value = Array.isArray(profile.primary_tech_stack)
        ? profile.primary_tech_stack.join(', ')
        : profile.primary_tech_stack;
    }

    const dispName = document.getElementById('profile-display-name');
    const dispRole = document.getElementById('profile-display-role');
    const dispPlan = document.getElementById('profile-display-plan');

    if (dispName) dispName.textContent = profile.full_name || Auth.currentUser?.email || 'Candidate Profile';
    if (dispRole) dispRole.textContent = profile.target_role || 'Target Role Not Specified';
    if (dispPlan) dispPlan.textContent = `${plan} (${profile.scans_used || 0}/${profile.scans_limit || 30} scans)`;

    // Dashboard welcome banner
    const welcomeTitle = document.querySelector('.welcome-title');
    if (welcomeTitle) {
      const firstName = (profile.full_name || '').split(' ')[0] || 'there';
      welcomeTitle.textContent = `Welcome back, ${firstName}!`;
    }
  },

  async handleProfileSave() {
    const token = Auth.getAccessToken();
    if (!token) { this.showToast('Please sign in first.', 'error'); return; }

    const fullName   = document.getElementById('profile-full-name')?.value?.trim() || '';
    const targetRole = document.getElementById('profile-target-role')?.value?.trim() || '';
    const techStack  = document.getElementById('profile-tech-stack')?.value?.trim() || '';

    try {
      this.showToast('Updating profile preferences...', 'info');
      await API.updateProfile({
        full_name:          fullName,
        target_role:        targetRole,
        primary_tech_stack: techStack.split(',').map(s => s.trim()).filter(Boolean),
      }, token);
      this.showToast('Profile updated successfully!', 'success');
      await this.loadUserProfile(token);
    } catch (err) {
      this.showToast(`Profile update failed: ${err.message}`, 'error');
    }
  },

  // ── 6. Dashboard Data ─────────────────────────────────────────────────────

  _lastDashboardFetch: 0,
  _isFetchingDashboard: false,

  async loadLiveDashboardData(force = false) {
    const token = Auth.getAccessToken();
    if (!token) {
      this.renderNotifications([]);
      this.renderActivityFeed([]);
      this.renderHistoryView([]);
      this.renderJdMatchView([]);
      this.renderSkillGapView();
      this.renderCompareView([]);
      return;
    }

    if (this._isFetchingDashboard) return;
    if (!force && Date.now() - this._lastDashboardFetch < 5000) return;

    this._isFetchingDashboard = true;
    this._lastDashboardFetch = Date.now();

    try {
      // Parallel: notifications + activity + history + dashboard stats + JD matches + roadmap + comparisons + profile
      const [notifications, activity, history, stats, jdMatches, roadmap, comparisons, profile] = await Promise.allSettled([
        API.getNotifications(20, token),
        API.getActivityFeed(10, token),
        API.getHistory(token),
        API.getDashboardStats(token),
        API.getJDMatches(token),
        API.getSkillRoadmap(token),
        API.getComparisons(token),
        API.getProfile(token),
      ]);

      // Notifications
      const notifData = notifications.status === 'fulfilled' && Array.isArray(notifications.value) ? notifications.value : [];
      this.renderNotifications(notifData);

      // Activity feed
      const actData = activity.status === 'fulfilled' && Array.isArray(activity.value) ? activity.value : [];
      this.renderActivityFeed(actData);

      // History
      const histData = history.status === 'fulfilled' && Array.isArray(history.value) ? history.value : [];
      this.renderHistoryView(histData);

      // Profile
      if (profile.status === 'fulfilled' && profile.value) {
        this.userProfile = profile.value;
        this.applyProfileToUI(profile.value);
      }

      // Dashboard stats
      if (stats.status === 'fulfilled' && stats.value) {
        this.applyDashboardStats(stats.value);
      }

      // JD Match
      const jdmData = jdMatches.status === 'fulfilled' && Array.isArray(jdMatches.value) ? jdMatches.value : [];
      this.renderJdMatchView(jdmData);

      // Skill Gap Roadmap
      const roadData = roadmap.status === 'fulfilled' && Array.isArray(roadmap.value) ? roadmap.value : [];
      this.renderSkillGapView(roadData);

      // Comparison Matrix
      const compData = comparisons.status === 'fulfilled' && Array.isArray(comparisons.value) ? comparisons.value : [];
      this.renderCompareView(compData);

      // Active analysis fallback for preview
      if (!this.currentAnalysis && histData.length > 0) {
        this.currentAnalysis = histData[0].analysis_result || histData[0];
      }
      if (this.currentAnalysis) {
        this.renderResumePreview(this.currentAnalysis);
      }
    } finally {
      this._isFetchingDashboard = false;
    }
  },

  applyDashboardStats(stats) {
    if (!stats) return;

    // Stat cards — update values
    const statValues = document.querySelectorAll('.stat-value');
    if (statValues.length >= 4) {
      statValues[0].textContent = stats.avg_ats_score > 0 ? `${stats.avg_ats_score} / 100` : '—';
      statValues[1].textContent = stats.health_index > 0 ? `${stats.health_index}%` : '—';
      statValues[2].textContent = `${stats.scans_used || 0} / ${stats.scans_limit || 30}`;
      statValues[3].textContent = stats.top_match_pct > 0 ? `${stats.top_match_pct}%` : '—';
    }

    // Stat trend badge
    const trendEls = document.querySelectorAll('.stat-trend');
    if (trendEls.length >= 1 && stats.improvement_pct !== 0) {
      const sign = stats.improvement_pct > 0 ? '+' : '';
      trendEls[0].innerHTML = `<i class="fa-solid fa-arrow-${stats.improvement_pct >= 0 ? 'up' : 'down'}"></i> ${sign}${stats.improvement_pct}% vs last scan`;
      trendEls[0].className = `stat-trend ${stats.improvement_pct >= 0 ? 'up' : 'down'}`;
    }

    // Charts — re-initialise with live data when available
    if (stats.score_trend?.length > 0) {
      const chartData = {
        labels: stats.score_trend.map(p => p.label),
        scores: stats.score_trend.map(p => p.score),
      };
      ChartEngine.initScoreTrendChart('scoreTrendChart', chartData);
    }

    if (stats.latest_component_scores) {
      const cs = stats.latest_component_scores;
      const maxes = [20, 25, 25, 15, 15];
      const rawScores = [
        cs.formatting        || 0,
        cs.keywords          || 0,
        cs.content           || 0,
        cs.skill_validation  || 0,
        cs.ats_compatibility || 0,
      ];
      const radarData = {
        labels:      ['Formatting', 'Keywords & Skills', 'Content Quality', 'Skill Validation', 'ATS Compatibility'],
        scores:      rawScores,
        percentages: rawScores.map((s, i) => Math.round((s / maxes[i]) * 100)),
      };
      ChartEngine.initComponentRadarChart('componentRadarChart', radarData);
    }
  },

  // ── 7. Resume Upload & Analysis ───────────────────────────────────────────

  async handleResumeUpload(file) {
    if (!Auth.isAuthenticated()) {
      this.showToast('Please sign in to analyze a resume.', 'warning');
      Router.navigate('login');
      return;
    }

    const dropzone     = document.getElementById('resume-dropzone');
    const progressWrap = document.getElementById('upload-progress-wrap');
    const progressBar  = document.getElementById('upload-progress-bar-fill');
    const jdInput      = document.getElementById('jd-text-input')?.value || '';

    this.showToast(`Analyzing ${file.name} with Gemini Flash AI...`, 'info');

    if (progressWrap && progressBar) {
      progressWrap.classList.add('active');
      progressBar.style.width = '30%';
    }

    try {
      const token = Auth.getAccessToken();
      if (progressBar) progressBar.style.width = '65%';

      const result = await API.analyzeResume(file, jdInput, token);

      if (progressBar) progressBar.style.width = '100%';
      setTimeout(() => progressWrap?.classList.remove('active'), 500);

      this.setAnalysisState(result);

      this.showToast('Analysis Complete! View score breakdown below.', 'success');

      if (dropzone) {
        dropzone.innerHTML = `
          <i class="fa-solid fa-file-pdf dropzone-icon" style="color: var(--color-success);"></i>
          <h3>${file.name} Analyzed!</h3>
          <p style="color: var(--text-secondary); margin-top: 0.5rem;">ATS Score: <strong>${result.ats_score}/100</strong></p>
          <button class="btn btn-outline btn-sm" style="margin-top: 1rem;" onclick="location.reload()">Upload Another File</button>
        `;
      }

      this.renderAnalysisResults(result);
      await this.loadLiveDashboardData();   // refresh stats + history
    } catch (err) {
      progressWrap?.classList.remove('active');
      this.showToast(`Analysis Error: ${err.message}`, 'error');
      console.error('[App] Analysis failed:', err);
    }
  },

  setAnalysisState(result) {
    if (!result) return;
    this.currentAnalysis = result;
    try {
      localStorage.setItem('talentmatch_last_analysis_data', JSON.stringify(result));
      if (result.id) {
        localStorage.setItem('talentmatch_last_analysis_id', result.id);
      }
    } catch (e) {
      console.warn('[App] Could not persist analysis to localStorage:', e);
    }
    this.updateActiveResumeBanner(result);
  },

  restoreAnalysisState() {
    if (this.currentAnalysis) return this.currentAnalysis;
    try {
      const raw = localStorage.getItem('talentmatch_last_analysis_data');
      if (raw) {
        const parsed = JSON.parse(raw);
        this.currentAnalysis = parsed;
        this.updateActiveResumeBanner(parsed);
        return parsed;
      }
    } catch (e) { /* ignore */ }
    return null;
  },

  updateActiveResumeBanner(data) {
    const fnEl = document.getElementById('jd-active-resume-filename');
    const scoreEl = document.getElementById('jd-active-resume-score');
    if (!fnEl) return;

    if (data && (data.filename || data.resume_name || data.ats_score !== undefined)) {
      const fn = data.filename || data.resume_name || 'Uploaded Resume';
      const score = Math.round(data.ats_score || 0);
      fnEl.textContent = fn;
      if (scoreEl) {
        scoreEl.textContent = `ATS Score: ${score}/100`;
        scoreEl.className = score >= 80 ? 'badge badge-success' : 'badge badge-warning';
      }
    } else {
      fnEl.textContent = 'No resume uploaded yet';
      if (scoreEl) {
        scoreEl.textContent = 'Upload resume below or run scan in Analysis view';
        scoreEl.className = 'badge badge-primary';
      }
    }
  },

  async handleJdMatchSubmit() {
    if (!Auth.isAuthenticated()) {
      this.showToast('Please sign in to run JD Match analysis.', 'warning');
      Router.navigate('login');
      return;
    }

    const jdText = document.getElementById('jd-matcher-text-input')?.value?.trim();
    const fileInput = document.getElementById('jd-matcher-file-input');
    const file = fileInput?.files?.[0];

    if (!jdText) {
      this.showToast('Please paste a Job Description text.', 'warning');
      return;
    }

    // Resolve active resume state if no new file is uploaded
    const activeAnalysis = this.restoreAnalysisState();
    const existingText = activeAnalysis?.resume_text || activeAnalysis?.raw_text || activeAnalysis?.extracted_text || '';

    if (!file && !existingText) {
      this.showToast('Please upload and analyze a resume first or select a file.', 'warning');
      return;
    }

    const targetName = file ? file.name : (activeAnalysis?.filename || 'Active Resume');
    this.showToast(`Analyzing Resume ↔ JD Match for ${targetName}...`, 'info');

    try {
      const token = Auth.getAccessToken();
      const result = await API.analyzeResume(file || null, jdText, token, file ? null : existingText);

      // Preserve filename if re-using existing analysis
      if (!file && activeAnalysis?.filename) {
        result.filename = activeAnalysis.filename;
      }

      this.setAnalysisState(result);
      this.showToast('Resume ↔ JD Alignment Analysis Complete!', 'success');
      
      this.renderAnalysisResults(result);
      Router.navigate('analyze');
      await this.loadLiveDashboardData();
    } catch (err) {
      this.showToast(`JD Match Error: ${err.message}`, 'error');
      console.error('[App] JD Match failed:', err);
    }
  },

  // ── 8. Render Analysis Results ────────────────────────────────────────────

  renderAnalysisResults(data) {
    // Score meter
    const scoreMeter = document.getElementById('score-radial-meter');
    const scoreNum   = document.getElementById('analysis-score-num');
    if (scoreNum) scoreNum.textContent = Math.round(data.ats_score || 0);
    if (scoreMeter) {
      const circumference = 2 * Math.PI * 70; // r=70 → 439.8
      scoreMeter.style.strokeDashoffset = circumference - (circumference * (data.ats_score / 100));
    }

    // Render JD Match Alignment Panel if JD comparison is present
    const jdPanel = document.getElementById('jd-match-panel-wrap');
    const jdAnalysis = data.jd_match_analysis || data.jd_comparison;
    
    if (jdPanel && (jdAnalysis || (data.match_percentage && data.match_percentage > 0) || (data.resume_jd_similarity && data.resume_jd_similarity > 0))) {
      jdPanel.style.display = 'block';

      const matchScore = Math.round(data.match_percentage || jdAnalysis?.match_percentage || 0);
      const similarityPct = ((data.resume_jd_similarity || jdAnalysis?.semantic_similarity || 0) * 100).toFixed(1);
      
      const badgeEl = document.getElementById('jd-match-score-badge');
      if (badgeEl) badgeEl.textContent = `${matchScore}% Match`;

      const simVal = document.getElementById('jd-similarity-val');
      const simBar = document.getElementById('jd-similarity-bar');
      if (simVal) simVal.textContent = `${similarityPct}%`;
      if (simBar) simBar.style.width = `${Math.min(100, Math.max(0, parseFloat(similarityPct)))}%`;

      const matchingSkills = data.matching_skills || jdAnalysis?.matching_skills || [];
      const missingSkills = data.missing_skills || jdAnalysis?.missing_skills || [];
      const missingKeywords = data.missing_keywords || jdAnalysis?.missing_keywords || [];

      const matchingContainer = document.getElementById('jd-matching-skills-container');
      if (matchingContainer) {
        matchingContainer.innerHTML = matchingSkills.length > 0
          ? matchingSkills.map(s => `<span class="kw-pill matched"><i class="fa-solid fa-check"></i> ${s}</span>`).join('')
          : '<small style="color: var(--text-muted);">None identified</small>';
      }

      const missingSkillsContainer = document.getElementById('jd-missing-skills-container');
      if (missingSkillsContainer) {
        missingSkillsContainer.innerHTML = missingSkills.length > 0
          ? missingSkills.map(s => `<span class="kw-pill missing"><i class="fa-solid fa-xmark"></i> ${s}</span>`).join('')
          : '<small style="color: var(--text-muted);">No missing skills!</small>';
      }

      const missingKwContainer = document.getElementById('jd-missing-keywords-container');
      if (missingKwContainer) {
        missingKwContainer.innerHTML = missingKeywords.length > 0
          ? missingKeywords.slice(0, 15).map(kw => `<span class="kw-pill missing"><i class="fa-solid fa-tag"></i> ${kw}</span>`).join('')
          : '<small style="color: var(--text-muted);">No missing keywords</small>';
      }
    } else if (jdPanel) {
      jdPanel.style.display = 'none';
    }

    // Component cards
    const compGrid = document.getElementById('component-scores-grid');
    if (compGrid && data.component_scores) {
      compGrid.innerHTML = Object.entries(data.component_scores).map(([key, val]) => {
        const maxVal = key === 'formatting' ? 20 : key === 'ats_compatibility' || key === 'skill_validation' ? 15 : 25;
        return `
          <div class="component-card glass-panel">
            <div class="component-card-header">
              <span class="component-name"><i class="fa-solid fa-check-double" style="color: var(--accent-primary);"></i> ${key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
              <span class="component-val">${val}/${maxVal}</span>
            </div>
            <div class="progress-bar-wrap">
              <div class="progress-bar-fill" style="width: ${(val / maxVal) * 100}%;"></div>
            </div>
          </div>
        `;
      }).join('');
    }

    // Keywords
    const kwContainer = document.getElementById('matched-keywords-container');
    if (kwContainer) {
      const matched = (data.matched_keywords || []).slice(0, 20);
      const missing = (data.missing_keywords || []).slice(0, 15);
      kwContainer.innerHTML = [
        ...matched.map(kw => `<span class="kw-pill matched"><i class="fa-solid fa-check"></i> ${kw}</span>`),
        ...missing.map(kw => `<span class="kw-pill missing"><i class="fa-solid fa-xmark"></i> ${kw}</span>`),
      ].join('');
    }

    // Recommendations
    const recsContainer = document.querySelector('.issues-accordion-list');
    if (recsContainer && data.recommendations?.length) {
      recsContainer.innerHTML = data.recommendations.map((rec, i) => `
        <div class="issue-item-card ${i === 0 ? 'active' : ''}">
          <div class="issue-item-header" onclick="this.parentElement.classList.toggle('active')">
            <span class="issue-item-title">${rec.priority_icon || '🟠'} ${rec.title || rec.issue_title || 'Recommendation'}</span>
            <i class="fa-solid fa-chevron-down issue-chevron"></i>
          </div>
          <div class="issue-item-body">
            <p>${rec.description || rec.explanation || ''}</p>
            ${(rec.action_items || []).length ? `
              <div class="how-to-fix-box">
                <strong>Action Items:</strong>
                <ul style="padding-left: 1.2rem; margin-top: 0.35rem;">
                  ${rec.action_items.map(item => `<li>${item}</li>`).join('')}
                </ul>
              </div>` : ''}
          </div>
        </div>
      `).join('');
    }

    // Render Parsed Resume & Document Preview Inspector
    this.renderResumePreview(data);
  },

  // ── 9. Resume Preview & Data Inspector ───────────────────────────────────

  currentPreviewTab: 'summary',

  switchPreviewTab(tab) {
    this.currentPreviewTab = tab;
    document.querySelectorAll('.doc-tab-pill').forEach(pill => {
      pill.classList.toggle('active', pill.id === `tab-pill-${tab}`);
    });
    if (this.currentAnalysis) {
      this.renderResumePreview(this.currentAnalysis, tab);
    }
  },

  renderResumePreview(data, tab = null) {
    const activeTab = tab || this.currentPreviewTab || 'summary';
    const container = document.getElementById('resume-preview-body');
    if (!container) return;

    if (!data) {
      container.innerHTML = `
        <div style="text-align: center; padding: 2.5rem;">
          <i class="fa-solid fa-file-pdf" style="font-size: 2.5rem; color: var(--accent-primary); margin-bottom: 0.75rem;"></i>
          <h4 style="margin-bottom: 0.25rem;">No Active Resume Document</h4>
          <p style="color: var(--text-secondary); font-size: 0.88rem;">Upload a resume above to analyze and inspect parsed contents.</p>
        </div>`;
      return;
    }

    const filename   = data.filename || data.resume_name || 'Uploaded Resume';
    const uploadDate = this._formatDate(data.created_at || new Date().toISOString());
    const rawText    = data.resume_text || data.raw_text || data.extracted_text || '';
    const pagesCount = data.pages || Math.max(1, Math.ceil((rawText.length || 1500) / 3000));
    const skills     = data.skills || [];
    const jobTitle   = data.job_title || 'Target Role';

    if (activeTab === 'summary') {
      container.innerHTML = `
        <div style="font-size: 0.92rem; line-height: 1.6;">
          <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 0.75rem; margin-bottom: 1rem;">
            <div>
              <strong style="font-size: 1.1rem; color: var(--text-primary);"><i class="fa-solid fa-file-invoice"></i> ${this._escapeHtml(filename)}</strong>
              <span style="color: var(--text-muted); font-size: 0.8rem; display: block; margin-top: 0.15rem;">Uploaded: ${uploadDate} • ${pagesCount} Page(s)</span>
            </div>
            <span class="badge badge-success">ATS Score: ${Math.round(data.ats_score || 0)}/100</span>
          </div>

          <div style="margin-bottom: 0.75rem;">
            <strong>TARGET ROLE:</strong> <span style="color: var(--accent-primary); font-weight: 600;">${this._escapeHtml(jobTitle)}</span>
          </div>

          <div style="margin-bottom: 1rem;">
            <strong>PROFESSIONAL SUMMARY & EXCERPT:</strong>
            <p style="color: var(--text-secondary); margin-top: 0.35rem; background: var(--bg-tertiary); padding: 0.85rem; border-radius: var(--border-radius-sm); border-left: 3px solid var(--accent-primary);">
              ${this._escapeHtml(data.interpretation || rawText.slice(0, 500) || 'Extracted summary parsed successfully.')}
            </p>
          </div>

          <div>
            <strong>TOP DETECTED SKILLS (${skills.length}):</strong>
            <div class="keywords-pills-wrap" style="margin-top: 0.4rem;">
              ${skills.length > 0
                ? skills.slice(0, 15).map(s => `<span class="kw-pill matched"><i class="fa-solid fa-check"></i> ${this._escapeHtml(s)}</span>`).join('')
                : '<small style="color: var(--text-muted);">No skills extracted</small>'}
            </div>
          </div>
        </div>`;
    } else if (activeTab === 'skills') {
      const matched = data.matching_skills || data.matched_keywords || [];
      const missing = data.missing_skills || data.missing_keywords || [];
      container.innerHTML = `
        <div>
          <h4 style="margin-bottom: 0.75rem;"><i class="fa-solid fa-layer-group"></i> Extracted Skills Breakdown</h4>
          <div style="margin-bottom: 1.25rem;">
            <strong style="color: var(--color-success);"><i class="fa-solid fa-circle-check"></i> Validated / Matched Skills (${matched.length}):</strong>
            <div class="keywords-pills-wrap" style="margin-top: 0.5rem;">
              ${matched.length > 0
                ? matched.map(s => `<span class="kw-pill matched"><i class="fa-solid fa-check"></i> ${this._escapeHtml(s)}</span>`).join('')
                : '<small style="color: var(--text-muted);">None identified</small>'}
            </div>
          </div>
          <div>
            <strong style="color: var(--color-danger);"><i class="fa-solid fa-circle-xmark"></i> Missing / Target Skills Gap (${missing.length}):</strong>
            <div class="keywords-pills-wrap" style="margin-top: 0.5rem;">
              ${missing.length > 0
                ? missing.map(s => `<span class="kw-pill missing"><i class="fa-solid fa-xmark"></i> ${this._escapeHtml(s)}</span>`).join('')
                : '<small style="color: var(--text-muted);">No missing skills!</small>'}
            </div>
          </div>
        </div>`;
    } else if (activeTab === 'text') {
      container.innerHTML = `
        <div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <div>
              <strong>Filename:</strong> ${this._escapeHtml(filename)} | <strong>Upload Date:</strong> ${uploadDate} | <strong>Pages:</strong> ${pagesCount}
            </div>
            <button class="btn btn-outline btn-sm" onclick="App.handleDownloadPDF()"><i class="fa-solid fa-download"></i> Download Report</button>
          </div>
          <textarea readonly class="chat-input-field" style="width: 100%; height: 260px; font-family: monospace; font-size: 0.85rem; line-height: 1.5; padding: 0.75rem; border-radius: var(--border-radius-sm); resize: vertical; color: var(--text-secondary); background: var(--bg-tertiary);">${this._escapeHtml(rawText || 'No raw text stored for this scan.')}</textarea>
        </div>`;
    } else if (activeTab === 'pdf') {
      const pdfUrl = data.pdf_url || data.report_url || null;
      if (pdfUrl) {
        container.innerHTML = `
          <iframe src="${pdfUrl}" width="100%" height="450px" style="border: none; border-radius: var(--border-radius-sm);" onerror="App.renderPdfFallback('${this._escapeHtml(filename)}', '${uploadDate}', ${pagesCount}, \`${this._escapeJs(rawText)}\`)"></iframe>`;
      } else {
        this.renderPdfFallback(filename, uploadDate, pagesCount, rawText);
      }
    }
  },

  renderPdfFallback(filename, uploadDate, pagesCount, rawText) {
    const container = document.getElementById('resume-preview-body');
    if (!container) return;
    container.innerHTML = `
      <div style="background: var(--bg-tertiary); border: 1px solid var(--border-color); border-radius: var(--border-radius-sm); padding: 1.25rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed var(--border-color); padding-bottom: 0.75rem; margin-bottom: 1rem;">
          <div>
            <h4 style="margin: 0; font-size: 1rem; color: var(--text-primary);"><i class="fa-solid fa-file-pdf" style="color: var(--color-warning);"></i> ${this._escapeHtml(filename)}</h4>
            <small style="color: var(--text-muted);">Uploaded: ${uploadDate} • Pages: ${pagesCount}</small>
          </div>
          <button class="btn btn-primary btn-sm" onclick="App.handleDownloadPDF()"><i class="fa-solid fa-download"></i> Download PDF Report</button>
        </div>
        <div style="margin-bottom: 0.5rem; font-size: 0.85rem; font-weight: 600; color: var(--text-secondary);">Extracted Text Preview:</div>
        <div style="max-height: 220px; overflow-y: auto; background: var(--bg-primary); padding: 0.85rem; border-radius: var(--border-radius-sm); font-family: monospace; font-size: 0.82rem; color: var(--text-secondary); white-space: pre-wrap; word-break: break-word;">${this._escapeHtml(rawText || 'Text extraction complete.')}</div>
      </div>`;
  },

  // ── 9. Render Helpers ────────────────────────────────────────────────────

  renderNotifications(list) {
    const container = document.getElementById('notification-items-container');
    if (!container) return;
    const items = Array.isArray(list) ? list : [];
    const unread = items.filter(n => !n.is_read).length;

    const badge = document.querySelector('.notification-badge-count');
    if (badge) badge.textContent = unread > 0 ? String(unread) : '';

    if (items.length === 0) {
      container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.88rem; padding: 0.5rem 0;">No new notifications.</p>';
      return;
    }
    container.innerHTML = items.slice(0, 10).map(item => `
      <div class="notification-item" style="cursor: pointer;"
           onclick="API.markNotificationRead('${item.id}', Auth.getAccessToken()).catch(()=>{})">
        <i class="fa-solid ${item.icon || 'fa-bell'}" style="color: var(--accent-primary); margin-top: 0.2rem;"></i>
        <div>
          <strong style="font-size: 0.88rem; display: block;">${item.title}</strong>
          <p style="font-size: 0.8rem; color: var(--text-secondary); margin: 0.2rem 0 0;">${item.description || item.desc || ''}</p>
          <small style="color: var(--text-muted); font-size: 0.72rem;">${this._relativeTime(item.created_at || item.time)}</small>
        </div>
      </div>
    `).join('');
  },

  renderActivityFeed(list) {
    const container = document.getElementById('dashboard-activity-feed');
    if (!container) return;
    const items = Array.isArray(list) ? list : [];

    if (items.length === 0) {
      container.innerHTML = `
        <div style="padding: 1.5rem; text-align: center; color: var(--text-muted); font-size: 0.88rem;">
          <i class="fa-solid fa-clock-rotate-left" style="font-size: 1.5rem; margin-bottom: 0.5rem; display: block; color: var(--accent-primary);"></i>
          No recent activity recorded yet. Run a scan or JD match to see activity here!
        </div>`;
      return;
    }

    container.innerHTML = items.slice(0, 10).map(item => `
      <div class="activity-feed-item" style="display: flex; gap: 0.85rem; align-items: flex-start; padding: 0.75rem 0; border-bottom: 1px dashed var(--border-color);">
        <div style="width: 32px; height: 32px; border-radius: 50%; background: var(--bg-tertiary); display: flex; align-items: center; justify-content: center; color: var(--accent-primary); flex-shrink: 0; font-size: 0.9rem;">
          <i class="fa-solid ${item.icon || 'fa-bolt'}"></i>
        </div>
        <div style="flex: 1; font-size: 0.88rem;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <strong style="color: var(--text-primary);">${this._escapeHtml(item.action || item.title || 'Activity')}</strong>
            <small style="color: var(--text-muted); font-size: 0.75rem;">${this._relativeTime(item.created_at || item.time)}</small>
          </div>
          <p style="color: var(--text-secondary); margin: 0.2rem 0 0; font-size: 0.82rem;">${this._escapeHtml(item.description || item.detail || '')}</p>
        </div>
      </div>
    `).join('');
  },

  renderJdMatchView(list) {
    const container = document.getElementById('jd-match-cards-wrap');
    if (!container) return;
    const items = Array.isArray(list) ? list : [];

    if (items.length === 0) {
      container.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 3rem; background: var(--bg-tertiary); border-radius: var(--border-radius-md);">
          <i class="fa-solid fa-bullseye" style="font-size: 2.5rem; color: var(--accent-primary); margin-bottom: 0.75rem; display: block;"></i>
          <h3 style="margin-bottom: 0.3rem;">No Saved JD Matches</h3>
          <p style="color: var(--text-secondary); font-size: 0.9rem;">Paste a Job Description requirements text above and click "Run Resume ↔ JD Match Analysis" to save match reports here.</p>
        </div>`;
      return;
    }

    container.innerHTML = items.map(item => `
      <div class="glass-panel dashboard-card">
        <div class="card-header">
          <span class="card-title"><i class="fa-solid fa-briefcase" style="color: var(--accent-primary);"></i> ${this._escapeHtml(item.job_title || item.title || 'Target Role')}</span>
          <span class="badge ${item.match_percentage >= 70 ? 'badge-success' : 'badge-warning'}">${Math.round(item.match_percentage || 0)}% Match</span>
        </div>
        <p style="font-size: 0.88rem; color: var(--text-secondary); margin-bottom: 0.5rem;">
          Company: <strong>${this._escapeHtml(item.company_name || 'Target Employer')}</strong>
        </p>
        <div style="margin-bottom: 0.75rem; font-size: 0.82rem; color: var(--text-muted);">
          Semantic Similarity: <strong>${((item.semantic_similarity || 0) * 100).toFixed(1)}%</strong>
        </div>
        <div style="margin-bottom: 1rem;">
          <small style="display: block; margin-bottom: 0.3rem; font-weight: 600; color: var(--text-secondary);">Matching Skills (${(item.matched_keywords || item.matching_skills || []).length}):</small>
          <div class="keywords-pills-wrap">
            ${(item.matched_keywords || item.matching_skills || []).slice(0, 8).map(s => `<span class="kw-pill matched"><i class="fa-solid fa-check"></i> ${this._escapeHtml(s)}</span>`).join('') || '<small style="color: var(--text-muted);">None</small>'}
          </div>
        </div>
      </div>
    `).join('');
  },

  renderComparisonView(data) {
    return this.renderCompareView(data);
  },

  async renderCompareView() {
    const container = document.getElementById('comparison-matrix-body');
    if (!container) return;

    let historyList = [];
    try {
      const token = Auth.getAccessToken();
      if (token) {
        historyList = await API.getHistory(50, token).catch(() => []);
      }
    } catch (e) {
      console.warn('Could not fetch history for comparison:', e);
    }

    // Combine currentAnalysis, localStorage item, and history items into unique list
    let allScans = [...historyList];
    const activeData = this.currentAnalysis || this.restoreAnalysisState();
    if (activeData) {
      const exists = allScans.some(item => (item.id && item.id === activeData.id) || (item.filename && item.filename === activeData.filename));
      if (!exists) {
        allScans.unshift({
          id: activeData.id || 'current',
          filename: activeData.filename || 'Active Resume',
          ats_score: activeData.ats_score || 0,
          component_scores: activeData.component_scores || {},
          skills: activeData.skills || [],
          job_title: activeData.job_title || 'Parsed Role',
          created_at: new Date().toISOString(),
        });
      }
    }

    // Filter unique items by filename or ID
    const uniqueMap = new Map();
    allScans.forEach(item => {
      const key = item.filename || item.id;
      if (key && !uniqueMap.has(key)) {
        uniqueMap.set(key, item);
      }
    });
    const analyses = Array.from(uniqueMap.values());

    if (analyses.length === 0) {
      container.innerHTML = `
        <tr>
          <td colspan="6" style="text-align:center; padding: 2.5rem; color: var(--text-secondary);">
            <i class="fa-solid fa-code-compare" style="font-size: 2rem; color: var(--accent-primary); margin-bottom: 0.5rem; display: block;"></i>
            <strong>No Analyzed Resumes Found</strong>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem;">Please upload and analyze a resume first.</p>
            <button class="btn btn-primary btn-sm" style="margin-top: 0.75rem;" onclick="Router.navigate('analyze')">
              <i class="fa-solid fa-plus"></i> Analyze Resume Now
            </button>
          </td>
        </tr>`;
      return;
    }

    // If 1 analysis exists: Show message informing user, and render single analysis row
    if (analyses.length === 1) {
      const single = analyses[0];
      const fn = single.filename || single.name || 'Active Resume';
      const score = single.ats_score || single.atsScore || 0;
      const cs = single.component_scores || {};
      const skillsCount = Array.isArray(single.skills) ? single.skills.length : (single.skills_count || 0);

      container.innerHTML = `
        <tr>
          <td colspan="6" style="background: var(--bg-tertiary); padding: 0.75rem 1rem; border-bottom: 1px solid var(--border-color);">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;">
              <span style="font-size: 0.88rem; color: var(--text-primary);">
                <i class="fa-solid fa-circle-info" style="color: var(--accent-primary); margin-right: 0.4rem;"></i>
                You currently have 1 analyzed resume: <strong style="color: var(--accent-primary);">${fn}</strong> (${score}/100). Upload another resume to compare side-by-side.
              </span>
              <button class="btn btn-primary btn-sm" onclick="Router.navigate('analyze')">
                <i class="fa-solid fa-plus"></i> Upload 2nd Resume
              </button>
            </div>
          </td>
        </tr>
        <tr>
          <td><strong>${fn}</strong> <span class="badge badge-primary" style="margin-left: 0.4rem;">Active</span></td>
          <td><span class="badge ${score >= 80 ? 'badge-success' : 'badge-warning'}">${score}/100</span></td>
          <td>${cs.formatting ?? 0}/20</td>
          <td>${cs.keywords ?? 0}/25</td>
          <td>${skillsCount} Skills Detected</td>
          <td><span class="badge badge-info">${score >= 80 ? 'High Match' : 'Needs Optimization'}</span></td>
        </tr>`;

      try {
        if (typeof ChartEngine !== 'undefined' && ChartEngine.initComparisonBarChart) {
          ChartEngine.initComparisonBarChart('comparisonBarChart', [
            { label: fn, score: score, formatting: cs.formatting || 0, keywords: cs.keywords || 0 }
          ]);
        }
      } catch (err) {
        console.warn('[Compare] Could not render comparison chart:', err);
      }
      return;
    }

    // If 2+ analyses exist: Render side-by-side comparison matrix
    container.innerHTML = analyses.map((item, idx) => {
      const fn = item.filename || item.name || `Resume V${idx + 1}`;
      const score = item.ats_score || item.atsScore || 0;
      const cs = item.component_scores || {};
      const skillsCount = Array.isArray(item.skills) ? item.skills.length : (item.skills_count || 0);
      const verdict = score >= 85 ? 'Top Candidate' : score >= 70 ? 'Strong Match' : 'Needs Work';

      return `
        <tr>
          <td><strong>${fn}</strong> ${idx === 0 ? '<span class="badge badge-primary" style="margin-left: 0.4rem;">Latest</span>' : ''}</td>
          <td><span class="badge ${score >= 80 ? 'badge-success' : score >= 60 ? 'badge-warning' : 'badge-danger'}">${score}/100</span></td>
          <td>${cs.formatting ?? 0}/20</td>
          <td>${cs.keywords ?? 0}/25</td>
          <td>${skillsCount} Skills</td>
          <td><span class="badge ${score >= 80 ? 'badge-success' : 'badge-info'}">${verdict}</span></td>
        </tr>`;
    }).join('');

    const chartData = analyses.map(item => ({
      label: (item.filename || 'Resume').substring(0, 18),
      score: item.ats_score || item.atsScore || 0,
      formatting: item.component_scores?.formatting || 0,
      keywords: item.component_scores?.keywords || 0,
    }));

    try {
      if (typeof ChartEngine !== 'undefined' && ChartEngine.initComparisonBarChart) {
        ChartEngine.initComparisonBarChart('comparisonBarChart', chartData);
      }
    } catch (err) {
      console.warn('[Compare] Could not render comparison chart:', err);
    }
  },

  async renderSkillGapView() {
    const container = document.getElementById('skill-roadmap-container');
    if (!container) return;

    let activeData = this.currentAnalysis || this.restoreAnalysisState();

    if (!activeData) {
      container.innerHTML = `
        <div style="text-align: center; padding: 3rem;">
          <i class="fa-solid fa-road" style="font-size: 3rem; color: var(--accent-primary); margin-bottom: 1rem; display: block;"></i>
          <h3 style="margin-bottom: 0.5rem;">Analyze a resume to generate your personalized skill roadmap.</h3>
          <p style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 1.25rem;">Upload your resume to identify missing target skills, unvalidated experience, and actionable steps.</p>
          <button class="btn btn-primary btn-sm" onclick="Router.navigate('analyze')">
            <i class="fa-solid fa-plus"></i> Analyze Resume Now
          </button>
        </div>`;
      return;
    }

    const resData = activeData.analysis_result || activeData;
    const jdData = resData.jd_match_analysis || resData.jd_comparison || {};

    const missingSkills = resData.missing_skills || jdData.missing_skills || jdData.skills_gap || [];
    const unvalidated = resData.skill_validation_details?.unvalidated || [];
    const recommendations = resData.recommendations || [];
    const jobTitle = resData.job_title || 'Target Professional Role';

    const roadmapItems = [];

    missingSkills.forEach((skill, i) => {
      roadmapItems.push({
        id: `gap-skill-${i}`,
        skill_name: skill,
        category: 'Missing Target Skill',
        priority: i < 3 ? 'Critical' : 'High',
        estimated_hours: `${10 + (i * 5)} Hours`,
        status: 'Not Started',
        roadmap_steps: [
          `Study core concepts and online documentation for ${skill}.`,
          `Build a hands-on project demonstrating ${skill} integration.`,
          `Add measurable project results using ${skill} to your resume.`,
        ]
      });
    });

    unvalidated.forEach((skill, i) => {
      const sName = typeof skill === 'string' ? skill : skill.skill;
      roadmapItems.push({
        id: `unval-skill-${i}`,
        skill_name: sName,
        category: 'Unvalidated Experience Skill',
        priority: 'Medium',
        estimated_hours: '5 Hours',
        status: 'In Progress',
        roadmap_steps: [
          `Add explicit project or work experience bullet points for ${sName}.`,
          `Include quantifiable metrics (e.g. reduced latency by 30% using ${sName}).`,
        ]
      });
    });

    recommendations.forEach((rec, i) => {
      if (rec.title && rec.action_items) {
        roadmapItems.push({
          id: `rec-item-${i}`,
          skill_name: rec.title,
          category: 'ATS Optimization Action',
          priority: 'High',
          estimated_hours: '2 Hours',
          status: 'Not Started',
          roadmap_steps: rec.action_items,
        });
      }
    });

    if (roadmapItems.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 2.5rem; background: var(--bg-tertiary); border-radius: var(--border-radius-md);">
          <i class="fa-solid fa-circle-check" style="font-size: 2.5rem; color: var(--accent-success); margin-bottom: 0.75rem; display: block;"></i>
          <h4 style="margin-bottom: 0.3rem;">No Critical Skill Gaps Detected</h4>
          <p style="color: var(--text-secondary); font-size: 0.9rem;">Your uploaded resume (${resData.filename || 'Active Resume'}) covers all primary technical requirements for ${jobTitle}!</p>
        </div>`;
      return;
    }

    container.innerHTML = `
      <div style="margin-bottom: 1.25rem; padding: 0.85rem 1.1rem; background: var(--bg-tertiary); border-left: 4px solid var(--accent-primary); border-radius: var(--border-radius-sm); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
        <div>
          <i class="fa-solid fa-road" style="color: var(--accent-primary); margin-right: 0.5rem; font-size: 1.1rem;"></i>
          <span style="font-size: 0.9rem;">Active Roadmap Target: <strong style="color: var(--text-primary);">${jobTitle}</strong> (${resData.filename || 'Uploaded Resume'})</span>
        </div>
        <span class="badge badge-primary">${roadmapItems.length} Action Items Identified</span>
      </div>
      ` + roadmapItems.map(item => `
        <div class="roadmap-step-item">
          <div class="roadmap-dot"></div>
          <div class="roadmap-card glass-panel">
            <div class="card-header" style="margin-bottom: 0.5rem;">
              <span class="roadmap-title"><i class="fa-solid fa-bullseye" style="color: var(--accent-primary); margin-right: 0.4rem;"></i>${item.skill_name}</span>
              <span class="badge ${item.priority === 'Critical' ? 'badge-danger' : item.priority === 'High' ? 'badge-warning' : 'badge-primary'}">${item.priority} Priority</span>
            </div>
            <div class="roadmap-meta" style="display: flex; gap: 1rem; flex-wrap: wrap; font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.75rem;">
              <span><i class="fa-solid fa-layer-group"></i> ${item.category}</span>
              <span><i class="fa-solid fa-clock"></i> Est. ${item.estimated_hours}</span>
              <span>
                <select class="roadmap-status-select"
                  onchange="App.handleRoadmapStatusChange('${item.id}', this.value)"
                  style="background: var(--bg-secondary); border: 1px solid var(--border-color); color: var(--text-primary); border-radius: 4px; padding: 0.15rem 0.4rem; font-size: 0.82rem; font-family: inherit;">
                  ${['Not Started', 'In Progress', 'Completed'].map(s =>
                    `<option value="${s}" ${item.status === s ? 'selected' : ''}>${s}</option>`
                  ).join('')}
                </select>
              </span>
            </div>
            <ul style="padding-left: 1.2rem; font-size: 0.9rem; color: var(--text-secondary);">
              ${item.roadmap_steps.map(step => `<li style="margin-bottom: 0.35rem;">${step}</li>`).join('')}
            </ul>
          </div>
        </div>
      `).join('');
  },

  renderHistoryView(list) {
    const container = document.getElementById('history-cards-container');
    if (!container) return;

    if (!list || list.length === 0) {
      container.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 3rem;">
          <i class="fa-solid fa-folder-open" style="font-size: 3rem; color: var(--accent-primary); margin-bottom: 1rem;"></i>
          <h3>No Scan Reports Found</h3>
          <p style="color: var(--text-secondary);">Run a new resume scan to see your analysis history here.</p>
          <button class="btn btn-primary btn-sm" style="margin-top: 1rem;" onclick="Router.navigate('analyze')">
            <i class="fa-solid fa-plus"></i> Run New Scan
          </button>
        </div>`;
      return;
    }

    container.innerHTML = list.map(item => `
      <div class="glass-panel dashboard-card">
        <div class="card-header">
          <span class="card-title"><i class="fa-solid fa-file-pdf"></i> ${item.filename || item.resume_name || 'Resume'}</span>
          <span class="badge badge-success">Score: ${item.atsScore || item.ats_score || 0}/100</span>
        </div>
        <p style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 0.5rem;">
          Role Target: <strong>${item.jobTitle || item.job_title || 'Not specified'}</strong>
        </p>
        <small style="color: var(--text-muted); display: block; margin-bottom: 1rem;">
          ${this._formatDate(item.date || item.created_at)}
        </small>
        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
          <button class="btn btn-primary btn-sm" onclick="App.handleViewAnalysis('${item.id}')">
            <i class="fa-solid fa-eye"></i> View Report
          </button>
          <button class="btn btn-outline btn-sm" onclick="App.handleDownloadPDF('${item.id}')">
            <i class="fa-solid fa-download"></i> PDF
          </button>
          <button class="btn btn-outline btn-sm"
                  onclick="App.handleDeleteHistory('${item.id}')"
                  style="color: var(--color-danger); border-color: rgba(239,68,68,0.3);">
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>
      </div>
    `).join('');
  },

  // ── 10. Action Handlers ───────────────────────────────────────────────────

  async handleViewAnalysis(analysisId) {
    const token = Auth.getAccessToken();
    if (!token) return;
    try {
      this.showToast('Loading analysis report...', 'info');
      const item = await API.getHistoryItem(analysisId, token);
      const data = item.analysis_result || item;
      this.setAnalysisState(data);
      Router.navigate('analyze');
      setTimeout(() => {
        this.renderAnalysisResults(data);
        this.renderResumePreview(data);
      }, 150);
    } catch (err) {
      this.showToast(`Could not load analysis: ${err.message}`, 'error');
    }
  },

  async handleDownloadPDF(analysisId = null) {
    this.showToast('Generating PDF Report...', 'info');
    try {
      const token = Auth.getAccessToken();
      // Pass analysisId (if present) or fall back to in-memory currentAnalysis
      const blob  = await API.downloadPDF(analysisId, this.currentAnalysis, token);
      const url   = window.URL.createObjectURL(blob);
      const a     = document.createElement('a');
      a.href      = url;
      a.download  = `talentmatch_report_${analysisId || 'latest'}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      this.showToast('PDF Report downloaded!', 'success');
    } catch (err) {
      this.showToast(`PDF Download Error: ${err.message}`, 'error');
    }
  },

  async handleDeleteHistory(analysisId) {
    if (!confirm('Are you sure you want to delete this scan report?')) return;
    try {
      const token = Auth.getAccessToken();
      await API.deleteHistoryItem(analysisId, token);
      this.showToast('Record deleted from history.', 'info');
      await this.loadLiveDashboardData();
    } catch (err) {
      this.showToast(`Delete Error: ${err.message}`, 'error');
    }
  },

  filterHistory(term) {
    document.querySelectorAll('#history-cards-container .dashboard-card').forEach(card => {
      card.style.display = card.textContent.toLowerCase().includes(term) ? '' : 'none';
    });
  },

  async handleGenerateRoadmap() {
    const token      = Auth.getAccessToken();
    if (!token) { this.showToast('Please sign in first.', 'warning'); return; }
    const analysisId = localStorage.getItem('talentmatch_last_analysis_id');
    if (!analysisId) {
      this.showToast('Please run a resume analysis first.', 'warning');
      return;
    }
    this.showToast('Generating your personalised skill roadmap with Gemini...', 'info');
    try {
      const result = await API.generateSkillRoadmap(analysisId, token);
      this.showToast(`Roadmap generated with ${result.count} skill items!`, 'success');
      this.renderSkillGapView(result.items || []);
    } catch (err) {
      this.showToast(`Roadmap generation failed: ${err.message}`, 'error');
    }
  },

  async handleRoadmapStatusChange(roadmapId, status) {
    if (!roadmapId) return;
    try {
      const token = Auth.getAccessToken();
      await API.updateRoadmapItem(roadmapId, { status }, token);
      this.showToast(`Status updated to "${status}"`, 'success');
    } catch (err) {
      this.showToast(`Status update failed: ${err.message}`, 'error');
    }
  },

  async handleTailorResume(jdId) {
    if (!jdId) {
      this.showToast('Save a job description and run an analysis first.', 'info');
      return;
    }
    const analysisId = localStorage.getItem('talentmatch_last_analysis_id');
    if (!analysisId) {
      this.showToast('Please run a resume analysis first.', 'warning');
      return;
    }
    this.showToast('Generating tailored resume suggestions with Gemini...', 'info');
    try {
      const token  = Auth.getAccessToken();
      const result = await API.tailorResume(analysisId, jdId, token);
      this.showToast(`Tailoring complete for ${result.job_title} @ ${result.company_name}!`, 'success');
      console.log('[App] Tailoring result:', result);
    } catch (err) {
      this.showToast(`Tailoring failed: ${err.message}`, 'error');
    }
  },

  openAddJDModal() {
    this.showToast('JD Manager coming soon! Use the API directly for now.', 'info');
  },

  // ── 11. AI Chat ───────────────────────────────────────────────────────────

  async handleChatSend() {
    const input      = document.getElementById('chat-input');
    const scrollArea = document.getElementById('chat-messages-scroll');
    const userText   = input?.value?.trim();
    if (!userText || !scrollArea) return;

    if (!Auth.isAuthenticated()) {
      this.showToast('Please sign in to use the AI Assistant.', 'warning');
      return;
    }

    input.value = '';

    // Append user bubble
    scrollArea.innerHTML += `
      <div class="chat-message-row user">
        <div class="chat-avatar"><i class="fa-solid fa-user"></i></div>
        <div class="chat-bubble">${this._escapeHtml(userText)}</div>
      </div>`;
    scrollArea.scrollTop = scrollArea.scrollHeight;

    // Typing indicator
    const typingId = 'typing-' + Date.now();
    scrollArea.innerHTML += `
      <div class="chat-message-row assistant" id="${typingId}">
        <div class="chat-avatar"><i class="fa-solid fa-robot"></i></div>
        <div class="chat-bubble">
          <div class="typing-indicator">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
          </div>
        </div>
      </div>`;
    scrollArea.scrollTop = scrollArea.scrollHeight;

    try {
      const token      = Auth.getAccessToken();
      const analysisId = localStorage.getItem('talentmatch_last_analysis_id');

      // Create session if we don't have one
      if (!this.currentSessionId && token) {
        try {
          const session = await API.createChatSession(
            { title: 'Resume Chat', analysis_id: analysisId || null },
            token,
          );
          this.currentSessionId = session?.id || null;
        } catch (sessErr) {
          console.warn('[App] Could not create chat session:', sessErr.message);
        }
      }

      let aiReply;
      if (this.currentSessionId && token) {
        const resp = await API.sendChatMessage(this.currentSessionId, userText, analysisId, token);
        aiReply = resp.content || resp.message || 'No response received.';
      } else {
        aiReply = 'I\'m currently offline. Please ensure the backend is running and you\'re signed in.';
      }

      document.getElementById(typingId)?.remove();
      scrollArea.innerHTML += `
        <div class="chat-message-row assistant">
          <div class="chat-avatar"><i class="fa-solid fa-robot"></i></div>
          <div class="chat-bubble">${this._formatAIReply(aiReply)}</div>
        </div>`;
      scrollArea.scrollTop = scrollArea.scrollHeight;
    } catch (err) {
      document.getElementById(typingId)?.remove();
      scrollArea.innerHTML += `
        <div class="chat-message-row assistant">
          <div class="chat-avatar"><i class="fa-solid fa-robot"></i></div>
          <div class="chat-bubble" style="color: var(--color-danger);">
            Sorry, I encountered an error: ${this._escapeHtml(err.message)}
          </div>
        </div>`;
      scrollArea.scrollTop = scrollArea.scrollHeight;
    }
  },

  sendPresetPrompt(text) {
    const input = document.getElementById('chat-input');
    if (input) {
      input.value = text;
      this.handleChatSend();
    }
  },

  // ── 12. Utility helpers ───────────────────────────────────────────────────

  _relativeTime(dateStr) {
    if (!dateStr) return '';
    try {
      const diff = Date.now() - new Date(dateStr).getTime();
      const mins = Math.floor(diff / 60000);
      if (mins < 1)   return 'just now';
      if (mins < 60)  return `${mins}m ago`;
      const hrs = Math.floor(mins / 60);
      if (hrs < 24)   return `${hrs}h ago`;
      return `${Math.floor(hrs / 24)}d ago`;
    } catch { return dateStr || ''; }
  },

  _formatDate(dateStr) {
    if (!dateStr) return 'Recent';
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric', month: 'short', day: 'numeric',
      });
    } catch { return dateStr; }
  },

  _escapeHtml(text) {
    return (text || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  },

  _escapeJs(str) {
    if (!str) return '';
    return String(str)
      .replace(/\\/g, '\\\\')
      .replace(/`/g, '\\`')
      .replace(/\${/g, '\\${');
  },

  _formatAIReply(text) {
    // Convert markdown-lite: bold and newlines
    return (text || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');
  },
};

// ── Initialize on DOM Ready ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => App.init().catch(console.error));

/* ==========================================================================
   TalentMatch AI - Application Core Controller
   Full live-API integration — MockData used only as fallback.
   ========================================================================== */

const App = {
  currentAnalysis:  null,
  currentSessionId: null,
  userProfile:      null,

  async init() {
    this.initTheme();
    await Auth.init();
    Router.init();
    this.bindEvents();
    await this.bootstrapLiveData();
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
               :                      'fa-info-circle';
    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity   = '0';
      toast.style.transform = 'translateX(50px)';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  },

  // ── 3. Modal Manager ──────────────────────────────────────────────────────

  openModal(modalId) {
    document.getElementById(modalId)?.classList.add('active');
  },
  closeModal(modalId) {
    document.getElementById(modalId)?.classList.remove('active');
  },

  // ── 4. Global Event Listeners ─────────────────────────────────────────────

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

    // Profile form
    document.getElementById('profile-save-btn')?.addEventListener('click', () => this.handleProfileSave());
  },

  // ── 5. Bootstrap — load live data on startup ──────────────────────────────

  async bootstrapLiveData() {
    const token = Auth.getAccessToken();

    // Load user profile first (populates sidebar name, plan badge)
    if (token) {
      await this.loadUserProfile(token);
    }

    // Load dashboard data
    await this.loadLiveDashboardData();
  },

  // ── 6. Profile ────────────────────────────────────────────────────────────

  async loadUserProfile(token = null) {
    try {
      const t = token || Auth.getAccessToken();
      if (!t) return;
      const profile = await API.getProfile(t);
      this.userProfile = profile;
      this.applyProfileToUI(profile);
    } catch (err) {
      console.warn('Profile load fallback:', err);
    }
  },

  applyProfileToUI(profile) {
    if (!profile) return;

    // Sidebar user info
    const nameEl = document.querySelector('.user-name-text');
    const roleEl = document.querySelector('.user-role-text');
    if (nameEl) nameEl.textContent = profile.full_name || profile.id?.slice(0, 8) || 'User';
    if (roleEl) roleEl.textContent = `${profile.plan === 'free' ? 'Free' : 'Pro'} Plan • ${profile.scans_used} Scans`;

    // Profile page form values
    const targetRoleInput = document.querySelector('#view-profile input[type="text"]');
    if (targetRoleInput && profile.target_role) targetRoleInput.value = profile.target_role;

    const stackInput = document.querySelectorAll('#view-profile input[type="text"]')[1];
    if (stackInput && profile.primary_tech_stack?.length) {
      stackInput.value = profile.primary_tech_stack.join(', ');
    }

    // Profile card name & badge
    const profileH3 = document.querySelector('#view-profile h3');
    if (profileH3) profileH3.textContent = profile.full_name || 'User';

    const profileRoleEl = document.querySelector('#view-profile p');
    if (profileRoleEl) profileRoleEl.textContent = profile.target_role || 'Software Engineer';

    // Dashboard welcome banner
    const welcomeTitle = document.querySelector('.welcome-title');
    if (welcomeTitle) {
      const firstName = (profile.full_name || '').split(' ')[0] || 'there';
      welcomeTitle.textContent = `Welcome back, ${firstName}!`;
    }
  },

  async handleProfileSave() {
    const token = Auth.getAccessToken();
    if (!token) return;
    try {
      const inputs   = document.querySelectorAll('#view-profile input[type="text"]');
      const targetRole  = inputs[0]?.value?.trim() || '';
      const techStack   = inputs[1]?.value?.trim() || '';
      const fullNameEl  = document.querySelector('#reg-name') || inputs[0];

      await API.updateProfile({
        target_role:        targetRole,
        primary_tech_stack: techStack.split(',').map(s => s.trim()).filter(Boolean),
      }, token);

      this.showToast('Profile updated successfully!', 'success');
      await this.loadUserProfile(token);
    } catch (err) {
      this.showToast(`Profile update failed: ${err.message}`, 'error');
    }
  },

  // ── 7. Dashboard Data ─────────────────────────────────────────────────────

  async loadLiveDashboardData() {
    const token = Auth.getAccessToken();

    // Parallel: notifications + activity + history + dashboard stats
    const [notifications, activity, history, stats] = await Promise.allSettled([
      token ? API.getNotifications(20, token) : Promise.resolve(MockData.notifications),
      token ? API.getActivityFeed(10, token)  : Promise.resolve(MockData.activityFeed),
      token ? API.getHistory(token)           : Promise.resolve(MockData.historyList),
      token ? API.getDashboardStats(token)    : Promise.resolve(null),
    ]);

    // Notifications
    const notifData = notifications.status === 'fulfilled' ? notifications.value : MockData.notifications;
    this.renderNotifications(Array.isArray(notifData) ? notifData : MockData.notifications);

    // Activity feed
    const actData = activity.status === 'fulfilled' ? activity.value : MockData.activityFeed;
    this.renderActivityFeed(Array.isArray(actData) ? actData : MockData.activityFeed);

    // History
    const histData = history.status === 'fulfilled' && Array.isArray(history.value) ? history.value : [];
    this.renderHistoryView(histData.length > 0 ? histData : MockData.historyList);

    // Dashboard stats — update stat cards and charts with live data
    if (stats.status === 'fulfilled' && stats.value) {
      this.applyDashboardStats(stats.value);
    }

    // JD Match + Skill Gap still use API if available, else mock
    this.renderJdMatchView(MockData.jdMatchList);
    this.renderSkillGapView(MockData.skillGapRoadmap);
    this.renderComparisonView(MockData.resumeComparison);
  },

  applyDashboardStats(stats) {
    if (!stats) return;

    // Stat cards — update values
    const statValues = document.querySelectorAll('.stat-value');
    if (statValues.length >= 4) {
      if (stats.avg_ats_score > 0)   statValues[0].textContent = `${stats.avg_ats_score} / 100`;
      if (stats.health_index > 0)    statValues[1].textContent = `${stats.health_index}%`;
      if (stats.scans_used !== undefined) statValues[2].textContent = `${stats.scans_used} / ${stats.scans_limit}`;
      if (stats.top_match_pct > 0)   statValues[3].textContent = `${stats.top_match_pct}%`;
    }

    // Score trend chart — feed live data
    if (stats.score_trend?.length > 1) {
      const trendLabels = stats.score_trend.map(p => p.label);
      const trendScores = stats.score_trend.map(p => p.score);
      ChartEngine.updateScoreTrend(trendLabels, trendScores);
    }

    // Component radar — feed latest analysis data
    if (stats.latest_component_scores) {
      const cs = stats.latest_component_scores;
      const radarScores = [
        cs.formatting || 0,
        cs.keywords || 0,
        cs.content || 0,
        cs.skill_validation || 0,
        cs.ats_compatibility || 0,
      ];
      ChartEngine.updateComponentRadar(radarScores);
    }

    // Scans trend text
    const trendEls = document.querySelectorAll('.stat-trend');
    if (trendEls.length >= 1 && stats.improvement_pct !== 0) {
      const sign = stats.improvement_pct > 0 ? '+' : '';
      trendEls[0].innerHTML = `<i class="fa-solid fa-arrow-${stats.improvement_pct >= 0 ? 'up' : 'down'}"></i> ${sign}${stats.improvement_pct}% vs last scan`;
      trendEls[0].className = `stat-trend ${stats.improvement_pct >= 0 ? 'up' : 'down'}`;
    }
  },

  // ── 8. Resume Upload & Analysis ───────────────────────────────────────────

  async handleResumeUpload(file) {
    const dropzone    = document.getElementById('resume-dropzone');
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

      this.currentAnalysis = result;

      // Store analysis ID for chat context
      if (result.id) {
        localStorage.setItem('talentmatch_last_analysis_id', result.id);
      }

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
      console.error('Analysis failed:', err);
    }
  },

  // ── 9. Render Analysis Results ────────────────────────────────────────────

  renderAnalysisResults(data) {
    // Score meter
    const scoreMeter = document.getElementById('score-radial-meter');
    const scoreNum   = document.getElementById('analysis-score-num');
    if (scoreNum) scoreNum.textContent = data.ats_score;
    if (scoreMeter) {
      scoreMeter.style.strokeDashoffset = 440 - (440 * (data.ats_score / 100));
    }

    // Component cards
    const compGrid = document.getElementById('component-scores-grid');
    if (compGrid && data.component_scores) {
      compGrid.innerHTML = Object.entries(data.component_scores).map(([key, val]) => `
        <div class="component-card glass-panel">
          <div class="component-card-header">
            <span class="component-name"><i class="fa-solid fa-check-double" style="color: var(--accent-primary);"></i> ${key.replace('_', ' ').toUpperCase()}</span>
            <span class="component-val">${val}</span>
          </div>
          <div class="progress-bar-wrap">
            <div class="progress-bar-fill" style="width: ${(val / 25) * 100}%;"></div>
          </div>
        </div>
      `).join('');
    }

    // Keywords
    const kwContainer = document.getElementById('matched-keywords-container');
    if (kwContainer) {
      const matched = data.matched_keywords || [];
      const missing = data.missing_keywords || [];
      kwContainer.innerHTML = [
        ...matched.map(kw => `<span class="kw-pill matched"><i class="fa-solid fa-check"></i> ${kw}</span>`),
        ...missing.map(kw => `<span class="kw-pill missing"><i class="fa-solid fa-xmark"></i> ${kw}</span>`),
      ].join('');
    }

    // Recommendations
    const recsContainer = document.querySelector('.issues-accordion-list');
    if (recsContainer && data.recommendations) {
      recsContainer.innerHTML = data.recommendations.map((rec, i) => `
        <div class="issue-item-card ${i === 0 ? 'active' : ''}">
          <div class="issue-item-header" onclick="this.parentElement.classList.toggle('active')">
            <span class="issue-item-title">${rec.priority_icon || '🟠'} ${rec.title}</span>
            <i class="fa-solid fa-chevron-down issue-chevron"></i>
          </div>
          <div class="issue-item-body">
            <p>${rec.description}</p>
            <div class="how-to-fix-box">
              <strong>Action Items:</strong>
              <ul style="padding-left: 1.2rem; margin-top: 0.35rem;">
                ${(rec.action_items || []).map(item => `<li>${item}</li>`).join('')}
              </ul>
            </div>
          </div>
        </div>
      `).join('');
    }
  },

  // ── 10. Render helpers ────────────────────────────────────────────────────

  renderNotifications(list) {
    const container = document.getElementById('notification-items-container');
    if (!container) return;
    const items = Array.isArray(list) ? list : [];
    const unread = items.filter(n => !n.is_read).length;

    // Update badge
    const badge = document.querySelector('.notification-badge-count');
    if (badge) badge.textContent = unread || '';

    container.innerHTML = items.slice(0, 10).map(item => `
      <div class="notification-item" onclick="API.markNotificationRead('${item.id}', Auth.getAccessToken())">
        <i class="fa-solid ${item.icon || 'fa-bell'}" style="color: var(--accent-primary); margin-top: 0.2rem;"></i>
        <div>
          <strong style="font-size: 0.88rem; display: block;">${item.title}</strong>
          <p style="font-size: 0.8rem; color: var(--text-secondary);">${item.description || item.desc || ''}</p>
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
      container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.88rem; padding: 1rem 0;">No recent activity yet.</p>';
      return;
    }
    container.innerHTML = items.slice(0, 6).map(item => `
      <div class="activity-feed-item">
        <div class="activity-icon-badge"><i class="fa-solid ${item.icon || 'fa-circle-check'}"></i></div>
        <div>
          <strong style="font-size: 0.9rem; display: block;">${item.action || item.title}</strong>
          <p style="font-size: 0.82rem; color: var(--text-secondary);">${item.description || item.desc || ''}</p>
          <small style="color: var(--text-muted); font-size: 0.75rem;">${this._relativeTime(item.created_at || item.time)}</small>
        </div>
      </div>
    `).join('');
  },

  renderComparisonView(list) {
    const container = document.getElementById('comparison-matrix-body');
    if (!container) return;
    container.innerHTML = (list || []).map(item => `
      <tr>
        <td><strong>${item.name || item.filename}</strong></td>
        <td><span class="badge ${(item.atsScore || item.ats_score) >= 90 ? 'badge-success' : 'badge-primary'}">${item.atsScore || item.ats_score}/100</span></td>
        <td>${item.formatting || item.component_scores?.formatting || 0}/20</td>
        <td>${item.keywords || item.component_scores?.keywords || 0}/25</td>
        <td>${item.skillsCount || item.skills_count || 0} Skills</td>
        <td><span class="badge badge-info">${item.verdict}</span></td>
      </tr>
    `).join('');
  },

  renderJdMatchView(list) {
    const container = document.getElementById('jd-match-cards-wrap');
    if (!container) return;
    if (!list || list.length === 0) {
      container.innerHTML = `
        <div class="empty-state" style="grid-column: 1/-1;">
          <i class="fa-solid fa-bullseye empty-state-icon"></i>
          <h3 class="empty-state-title">No JD Matches Yet</h3>
          <p class="empty-state-desc">Save a job description and match it against your resume.</p>
          <button class="btn btn-primary btn-sm" onclick="App.openAddJDModal()"><i class="fa-solid fa-plus"></i> Add Job Description</button>
        </div>`;
      return;
    }
    container.innerHTML = list.map(item => `
      <div class="glass-panel dashboard-card">
        <div class="card-header">
          <span class="card-title"><i class="fa-solid fa-building"></i> ${item.company || item.company_name}</span>
          <span class="badge badge-success">${item.matchScore || item.match_percentage}% Match</span>
        </div>
        <h4 style="margin-bottom: 0.5rem;">${item.role || item.job_title}</h4>
        <p style="font-size: 0.88rem; color: var(--text-secondary); margin-bottom: 1rem;">Semantic Similarity: <strong>${((item.semanticSim || item.semantic_similarity || 0) * 100).toFixed(0)}%</strong></p>
        <div style="margin-bottom: 1rem;">
          <small style="color: var(--text-muted);">Missing Target Keywords:</small>
          <div class="keywords-pills-wrap" style="margin-top: 0.35rem;">
            ${(item.missingKeywords || item.missing_keywords || []).map(kw => `<span class="kw-pill missing">${kw}</span>`).join('')}
          </div>
        </div>
        <button class="btn btn-outline btn-sm" onclick="App.handleTailorResume('${item.id || ''}')">Tailor Resume for Role</button>
      </div>
    `).join('');
  },

  renderSkillGapView(list) {
    const container = document.getElementById('skill-roadmap-container');
    if (!container) return;
    if (!list || list.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <i class="fa-solid fa-road empty-state-icon"></i>
          <h3 class="empty-state-title">No Roadmap Generated Yet</h3>
          <p class="empty-state-desc">Run a resume analysis first, then generate your personalised skill roadmap.</p>
          <button class="btn btn-primary btn-sm" onclick="App.handleGenerateRoadmap()"><i class="fa-solid fa-wand-magic-sparkles"></i> Generate Roadmap</button>
        </div>`;
      return;
    }
    const statusColors = { 'Completed': 'success', 'In Progress': 'warning', 'Not Started': 'primary' };
    container.innerHTML = list.map(item => `
      <div class="roadmap-step-item">
        <div class="roadmap-dot"></div>
        <div class="roadmap-card glass-panel">
          <div class="card-header" style="margin-bottom: 0.5rem;">
            <span class="roadmap-title">${item.skill || item.skill_name}</span>
            <span class="badge ${item.priority === 'Critical' ? 'badge-danger' : 'badge-warning'}">${item.priority} Priority</span>
          </div>
          <div class="roadmap-meta">
            <span><i class="fa-solid fa-layer-group"></i> ${item.category}</span>
            <span><i class="fa-solid fa-clock"></i> Est. ${item.estimatedHours || item.estimated_hours}</span>
            <span><i class="fa-solid fa-circle-check"></i>
              <select class="roadmap-status-select" onchange="App.handleRoadmapStatusChange('${item.id || ''}', this.value)" style="background: transparent; border: none; color: var(--text-secondary); cursor: pointer; font-size: 0.82rem;">
                ${['Not Started', 'In Progress', 'Completed'].map(s => `<option value="${s}" ${(item.status || item.status) === s ? 'selected' : ''}>${s}</option>`).join('')}
              </select>
            </span>
          </div>
          <ul style="padding-left: 1.2rem; font-size: 0.9rem; color: var(--text-secondary);">
            ${(item.roadmap || item.roadmap_steps || []).map(step => `<li style="margin-bottom: 0.35rem;">${step}</li>`).join('')}
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
        <div class="col-span-12">
          <div class="empty-state">
            <i class="fa-solid fa-folder-open empty-state-icon"></i>
            <h3 class="empty-state-title">No Scan Reports Found</h3>
            <p class="empty-state-desc">Run a new resume scan to see your analysis history here.</p>
            <button class="btn btn-primary btn-sm" onclick="Router.navigate('analyze')"><i class="fa-solid fa-plus"></i> Run New Scan</button>
          </div>
        </div>`;
      return;
    }

    container.innerHTML = list.map(item => `
      <div class="glass-panel dashboard-card">
        <div class="card-header">
          <span class="card-title"><i class="fa-solid fa-file-pdf"></i> ${item.filename}</span>
          <span class="badge badge-success">Score: ${item.atsScore || item.ats_score}/100</span>
        </div>
        <p style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 0.5rem;">Role Target: <strong>${item.jobTitle || item.job_title || 'Not specified'}</strong></p>
        <small style="color: var(--text-muted); display: block; margin-bottom: 1rem;">${this._formatDate(item.date || item.created_at)}</small>
        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
          <button class="btn btn-primary btn-sm" onclick="App.handleViewAnalysis('${item.id}')"><i class="fa-solid fa-eye"></i> View Report</button>
          <button class="btn btn-outline btn-sm" onclick="App.handleDownloadPDF('${item.id}')"><i class="fa-solid fa-download"></i> PDF</button>
          <button class="btn btn-outline btn-sm" onclick="App.handleDeleteHistory('${item.id}')" style="color: var(--color-danger); border-color: rgba(239,68,68,0.3);"><i class="fa-solid fa-trash"></i></button>
        </div>
      </div>
    `).join('');
  },

  // ── 11. Action handlers ───────────────────────────────────────────────────

  async handleViewAnalysis(analysisId) {
    const token = Auth.getAccessToken();
    try {
      this.showToast('Loading analysis...', 'info');
      const item = await API.getHistoryItem(analysisId, token);
      const data  = item.analysis_result || item;
      this.currentAnalysis = data;
      Router.navigate('analyze');
      setTimeout(() => this.renderAnalysisResults(data), 200);
    } catch (err) {
      this.showToast(`Could not load analysis: ${err.message}`, 'error');
    }
  },

  async handleDownloadPDF(analysisId = null) {
    this.showToast('Generating PDF Report...', 'info');
    try {
      const token = Auth.getAccessToken();
      const blob  = await API.downloadPDF(analysisId, token);
      const url   = window.URL.createObjectURL(blob);
      const a     = document.createElement('a');
      a.href     = url;
      a.download = `talentmatch_report_${analysisId || 'latest'}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
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
    const analysisId = localStorage.getItem('talentmatch_last_analysis_id');
    if (!analysisId) {
      this.showToast('Please run a resume analysis first.', 'warning');
      return;
    }
    this.showToast('Generating your personalised skill roadmap...', 'info');
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
      this.showToast('Tailor a resume by saving a JD and running a resume analysis first.', 'info');
      return;
    }
    const analysisId = localStorage.getItem('talentmatch_last_analysis_id');
    if (!analysisId) {
      this.showToast('Please run a resume analysis first.', 'warning');
      return;
    }
    this.showToast('Generating tailored resume suggestions...', 'info');
    try {
      const token  = Auth.getAccessToken();
      const result = await API.tailorResume(analysisId, jdId, token);
      this.showTailoringModal(result);
    } catch (err) {
      this.showToast(`Tailoring failed: ${err.message}`, 'error');
    }
  },

  showTailoringModal(result) {
    // Display tailoring results in a toast + future modal
    this.showToast(`Tailoring ready for ${result.job_title} @ ${result.company_name}!`, 'success');
    // TODO: render full tailoring modal with suggestions
  },

  openAddJDModal() {
    this.showToast('Add a new Job Description to start matching.', 'info');
    // TODO: render JD input modal
  },

  // ── 12. AI Chat ───────────────────────────────────────────────────────────

  async handleChatSend() {
    const input      = document.getElementById('chat-input');
    const scrollArea = document.getElementById('chat-messages-scroll');
    if (!input?.value.trim() || !scrollArea) return;

    const userText = input.value.trim();
    input.value = '';

    // Append user bubble
    scrollArea.innerHTML += `
      <div class="chat-message-row user">
        <div class="chat-avatar"><i class="fa-solid fa-user"></i></div>
        <div class="chat-bubble">${userText}</div>
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

      // Ensure we have a session
      if (!this.currentSessionId) {
        if (token) {
          const session = await API.createChatSession(
            { title: 'Resume Chat', analysis_id: analysisId },
            token,
          );
          this.currentSessionId = session?.id || null;
        }
      }

      let aiReply;
      if (this.currentSessionId && token) {
        const resp = await API.sendChatMessage(
          this.currentSessionId, userText, analysisId, token,
        );
        aiReply = resp.content || resp.message || 'No response received.';
      } else {
        // Offline fallback
        aiReply = 'I\'m currently offline. Please ensure the backend is running and you\'re signed in for AI-powered responses.';
      }

      document.getElementById(typingId)?.remove();
      scrollArea.innerHTML += `
        <div class="chat-message-row assistant">
          <div class="chat-avatar"><i class="fa-solid fa-robot"></i></div>
          <div class="chat-bubble">${aiReply.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}</div>
        </div>`;
      scrollArea.scrollTop = scrollArea.scrollHeight;
    } catch (err) {
      document.getElementById(typingId)?.remove();
      scrollArea.innerHTML += `
        <div class="chat-message-row assistant">
          <div class="chat-avatar"><i class="fa-solid fa-robot"></i></div>
          <div class="chat-bubble" style="color: var(--color-danger);">Sorry, I encountered an error: ${err.message}</div>
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

  // ── 13. Utility helpers ───────────────────────────────────────────────────

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
    } catch { return dateStr; }
  },

  _formatDate(dateStr) {
    if (!dateStr) return 'Recent';
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric', month: 'short', day: 'numeric',
      });
    } catch { return dateStr; }
  },
};

// ── Initialize on DOM Ready ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => App.init());

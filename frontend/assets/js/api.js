/* ==========================================================================
   TalentMatch AI - Frontend API Client (FastAPI Integration)
   Complete client covering all 35+ backend endpoints.
   ========================================================================== */

const API_BASE_URL = 'http://localhost:8000/api/v1';

const API = {

  // ── Internal helper ───────────────────────────────────────────────────────
  _headers(token = null) {
    const h = { 'Content-Type': 'application/json' };
    if (token) h['Authorization'] = `Bearer ${token}`;
    return h;
  },

  async _json(resp) {
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: `HTTP ${resp.status}` }));
      throw new Error(err.detail || `Request failed (${resp.status})`);
    }
    return resp.json();
  },

  async _jsonOrNull(resp) {
    if (!resp.ok) return null;
    return resp.json().catch(() => null);
  },

  // ── Public config & health ────────────────────────────────────────────────

  async fetchConfig() {
    try {
      const resp = await fetch(`${API_BASE_URL}/config`);
      return resp.ok ? await resp.json() : null;
    } catch { return null; }
  },

  async checkHealth() {
    try {
      const resp = await fetch(`${API_BASE_URL}/health`);
      return await resp.json();
    } catch { return { status: 'unreachable' }; }
  },

  // ── Resume Analysis ───────────────────────────────────────────────────────

  async analyzeResume(file, jobDescription = '', token = null) {
    const formData = new FormData();
    formData.append('resume', file);
    if (jobDescription) formData.append('job_description', jobDescription);

    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const resp = await fetch(`${API_BASE_URL}/analyze-resume`, {
      method: 'POST',
      headers,
      body: formData,
    });
    return this._json(resp);
  },

  // ── History ───────────────────────────────────────────────────────────────

  async getHistory(token = null) {
    const resp = await fetch(`${API_BASE_URL}/history`, {
      headers: this._headers(token),
    });
    return this._json(resp);
  },

  async getHistoryItem(analysisId, token = null) {
    const resp = await fetch(`${API_BASE_URL}/history/${analysisId}`, {
      headers: this._headers(token),
    });
    return this._json(resp);
  },

  async updateHistoryItem(analysisId, data, token = null) {
    const resp = await fetch(`${API_BASE_URL}/history/${analysisId}`, {
      method: 'PATCH',
      headers: this._headers(token),
      body: JSON.stringify(data),
    });
    return this._json(resp);
  },

  async deleteHistoryItem(analysisId, token = null) {
    const resp = await fetch(`${API_BASE_URL}/history/${analysisId}`, {
      method: 'DELETE',
      headers: this._headers(token),
    });
    return this._json(resp);
  },

  async bulkDeleteHistory(ids, token = null) {
    const resp = await fetch(`${API_BASE_URL}/history`, {
      method: 'DELETE',
      headers: this._headers(token),
      body: JSON.stringify({ ids }),
    });
    return this._json(resp);
  },

  // ── PDF Reports ───────────────────────────────────────────────────────────

  async downloadPDF(analysisId = null, token = null) {
    const url = analysisId
      ? `${API_BASE_URL}/history/${analysisId}/pdf`
      : `${API_BASE_URL}/generate-pdf`;
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(url, { method: 'GET', headers });
    if (!resp.ok) throw new Error('Failed to download PDF report');
    return resp.blob();
  },

  async getReports(token = null) {
    const resp = await fetch(`${API_BASE_URL}/reports`, {
      headers: this._headers(token),
    });
    return this._json(resp);
  },

  async deleteReport(reportId, token = null) {
    const resp = await fetch(`${API_BASE_URL}/reports/${reportId}`, {
      method: 'DELETE',
      headers: this._headers(token),
    });
    return this._json(resp);
  },

  // ── Auth / Profile ────────────────────────────────────────────────────────

  async getProfile(token = null) {
    const resp = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: this._headers(token),
    });
    return this._json(resp);
  },

  async updateProfile(data, token = null) {
    const resp = await fetch(`${API_BASE_URL}/auth/profile`, {
      method: 'PATCH',
      headers: this._headers(token),
      body: JSON.stringify(data),
    });
    return this._json(resp);
  },

  // ── Dashboard Stats ───────────────────────────────────────────────────────

  async getDashboardStats(token = null) {
    const resp = await fetch(`${API_BASE_URL}/dashboard/stats`, {
      headers: this._headers(token),
    });
    return this._json(resp);
  },

  // ── AI Chat ───────────────────────────────────────────────────────────────

  async createChatSession(data = {}, token = null) {
    const resp = await fetch(`${API_BASE_URL}/chat/sessions`, {
      method: 'POST',
      headers: this._headers(token),
      body: JSON.stringify(data),
    });
    return this._json(resp);
  },

  async getChatSessions(token = null) {
    const resp = await fetch(`${API_BASE_URL}/chat/sessions`, {
      headers: this._headers(token),
    });
    return this._json(resp);
  },

  async getSessionMessages(sessionId, token = null) {
    const resp = await fetch(`${API_BASE_URL}/chat/sessions/${sessionId}/messages`, {
      headers: this._headers(token),
    });
    return this._json(resp);
  },

  async sendChatMessage(sessionId, message, analysisId = null, token = null) {
    const body = { message };
    if (analysisId) body.analysis_id = analysisId;
    const resp = await fetch(`${API_BASE_URL}/chat/sessions/${sessionId}/message`, {
      method: 'POST',
      headers: this._headers(token),
      body: JSON.stringify(body),
    });
    return this._json(resp);
  },

  async deleteChatSession(sessionId, token = null) {
    const resp = await fetch(`${API_BASE_URL}/chat/sessions/${sessionId}`, {
      method: 'DELETE',
      headers: this._headers(token),
    });
    return this._json(resp);
  },

  // ── Job Descriptions ──────────────────────────────────────────────────────

  async createJobDescription(data, token = null) {
    const resp = await fetch(`${API_BASE_URL}/job-descriptions`, {
      method: 'POST',
      headers: this._headers(token),
      body: JSON.stringify(data),
    });
    return this._json(resp);
  },

  async getJobDescriptions(token = null) {
    const resp = await fetch(`${API_BASE_URL}/job-descriptions`, {
      headers: this._headers(token),
    });
    return this._json(resp);
  },

  async getJobDescription(jdId, token = null) {
    const resp = await fetch(`${API_BASE_URL}/job-descriptions/${jdId}`, {
      headers: this._headers(token),
    });
    return this._json(resp);
  },

  async deleteJobDescription(jdId, token = null) {
    const resp = await fetch(`${API_BASE_URL}/job-descriptions/${jdId}`, {
      method: 'DELETE',
      headers: this._headers(token),
    });
    return this._json(resp);
  },

  async matchJD(jdId, analysisId, token = null) {
    const resp = await fetch(`${API_BASE_URL}/job-descriptions/${jdId}/match`, {
      method: 'POST',
      headers: this._headers(token),
      body: JSON.stringify({ analysis_id: analysisId }),
    });
    return this._json(resp);
  },

  async getJDMatches(token = null) {
    const resp = await fetch(`${API_BASE_URL}/job-descriptions/matches`, {
      headers: this._headers(token),
    });
    return this._json(resp);
  },

  // ── Skill Gap Roadmap ─────────────────────────────────────────────────────

  async generateSkillRoadmap(analysisId, token = null) {
    const resp = await fetch(`${API_BASE_URL}/skill-gap/generate`, {
      method: 'POST',
      headers: this._headers(token),
      body: JSON.stringify({ analysis_id: analysisId }),
    });
    return this._json(resp);
  },

  async getSkillRoadmap(token = null) {
    const resp = await fetch(`${API_BASE_URL}/skill-gap`, {
      headers: this._headers(token),
    });
    return this._json(resp);
  },

  async updateRoadmapItem(roadmapId, data, token = null) {
    const resp = await fetch(`${API_BASE_URL}/skill-gap/${roadmapId}`, {
      method: 'PATCH',
      headers: this._headers(token),
      body: JSON.stringify(data),
    });
    return this._json(resp);
  },

  async deleteRoadmapItem(roadmapId, token = null) {
    const resp = await fetch(`${API_BASE_URL}/skill-gap/${roadmapId}`, {
      method: 'DELETE',
      headers: this._headers(token),
    });
    return this._json(resp);
  },

  // ── Resume Comparison ─────────────────────────────────────────────────────

  async compareResumes(analysisIds, name = 'Resume Comparison', token = null) {
    const resp = await fetch(`${API_BASE_URL}/compare`, {
      method: 'POST',
      headers: this._headers(token),
      body: JSON.stringify({ analysis_ids: analysisIds, name }),
    });
    return this._json(resp);
  },

  async getComparisons(token = null) {
    const resp = await fetch(`${API_BASE_URL}/compare`, {
      headers: this._headers(token),
    });
    return this._json(resp);
  },

  async deleteComparison(comparisonId, token = null) {
    const resp = await fetch(`${API_BASE_URL}/compare/${comparisonId}`, {
      method: 'DELETE',
      headers: this._headers(token),
    });
    return this._json(resp);
  },

  // ── Resume Tailoring ──────────────────────────────────────────────────────

  async tailorResume(analysisId, jdId, token = null) {
    const resp = await fetch(`${API_BASE_URL}/tailor`, {
      method: 'POST',
      headers: this._headers(token),
      body: JSON.stringify({ analysis_id: analysisId, jd_id: jdId }),
    });
    return this._json(resp);
  },

  // ── Notifications & Activity ──────────────────────────────────────────────

  async getNotifications(limit = 20, token = null) {
    const resp = await fetch(`${API_BASE_URL}/notifications?limit=${limit}`, {
      headers: this._headers(token),
    });
    return this._json(resp);
  },

  async markNotificationRead(notifId, token = null) {
    const resp = await fetch(`${API_BASE_URL}/notifications/${notifId}/read`, {
      method: 'PATCH',
      headers: this._headers(token),
    });
    return this._json(resp);
  },

  async getActivityFeed(limit = 10, token = null) {
    const resp = await fetch(`${API_BASE_URL}/activity?limit=${limit}`, {
      headers: this._headers(token),
    });
    return this._json(resp);
  },
};

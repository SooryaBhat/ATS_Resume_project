/* ==========================================================================
   TalentMatch AI - Frontend API Client (FastAPI Integration)
   Centralized, production-ready client covering all backend endpoints.
   ========================================================================== */

const API_BASE_URL = 'https://talentmatch-ai-grv6.onrender.com/api/v1';

let _cachedConfig = null;

const API = {

  // ── Centralized HTTP & Auth Request Helper ────────────────────────────────

  async _request(endpoint, options = {}, token = null) {
    const url = `${API_BASE_URL}${endpoint}`;
    const opts = { ...options };
    const isFormData = opts.body instanceof FormData;
    const headers = opts.headers ? { ...opts.headers } : {};

    if (!isFormData && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    const validToken = (token && typeof token === 'string' && token !== 'undefined' && token !== 'null' && token.trim())
      ? token.trim()
      : (typeof Auth !== 'undefined' ? Auth.getAccessToken() : null);

    if (validToken && validToken !== 'undefined' && validToken !== 'null') {
      headers['Authorization'] = `Bearer ${validToken}`;
    }

    opts.headers = headers;

    try {
      const resp = await fetch(url, opts);
      if (!resp.ok) {
        let msg = `Request failed (${resp.status})`;
        try {
          const errJson = await resp.json();
          msg = errJson.detail || errJson.message || msg;
        } catch (_) {}

        if (resp.status === 401) {
          msg = 'Session expired. Please sign in again.';
        } else if (resp.status === 422) {
          msg = msg || 'Invalid request input. Please check your data and try again.';
        } else if (resp.status >= 500) {
          msg = 'Service temporarily unavailable. Please try again.';
        }
        throw new Error(msg);
      }
      return resp;
    } catch (err) {
      if (err.name === 'TypeError' || err.message.includes('fetch')) {
        throw new Error('Network unavailable. Please check your internet connection.');
      }
      throw err;
    }
  },

  async _json(endpoint, options = {}, token = null) {
    const resp = await this._request(endpoint, options, token);
    return resp.json();
  },

  // ── Public config & health ────────────────────────────────────────────────

  async fetchConfig() {
    if (_cachedConfig) return _cachedConfig;
    try {
      const resp = await this._request('/config');
      _cachedConfig = await resp.json();
      return _cachedConfig;
    } catch (_) {
      return null;
    }
  },

  async checkHealth() {
    try {
      const resp = await this._request('/health');
      return await resp.json();
    } catch (_) {
      return { status: 'unreachable' };
    }
  },

  // ── Resume Analysis ───────────────────────────────────────────────────────

  async analyzeResume(file = null, jobDescription = '', token = null, resumeText = null) {
    const formData = new FormData();
    if (file) formData.append('resume', file);
    if (resumeText) formData.append('resume_text', resumeText);
    if (jobDescription) formData.append('job_description', jobDescription);

    return this._json('/analyze-resume', { method: 'POST', body: formData }, token);
  },

  // ── History ───────────────────────────────────────────────────────────────

  async getHistory(token = null) {
    return this._json('/history', { method: 'GET' }, token);
  },

  async getHistoryItem(analysisId, token = null) {
    return this._json(`/history/${analysisId}`, { method: 'GET' }, token);
  },

  async updateHistoryItem(analysisId, data, token = null) {
    return this._json(`/history/${analysisId}`, { method: 'PATCH', body: JSON.stringify(data) }, token);
  },

  async deleteHistoryItem(analysisId, token = null) {
    return this._json(`/history/${analysisId}`, { method: 'DELETE' }, token);
  },

  async bulkDeleteHistory(ids, token = null) {
    return this._json('/history', { method: 'DELETE', body: JSON.stringify({ ids }) }, token);
  },

  async downloadPDF(analysisId = null, analysisData = null, token = null) {
    if (analysisId) {
      const resp = await this._request(`/history/${analysisId}/pdf`, { method: 'GET' }, token);
      return resp.blob();
    }
    if (analysisData) {
      const resp = await this._request('/generate-pdf', { method: 'POST', body: JSON.stringify(analysisData) }, token);
      return resp.blob();
    }
    throw new Error('PDF generation requires an analysis ID or analysis data.');
  },

  async getReports(token = null) {
    return this._json('/reports', { method: 'GET' }, token);
  },

  async deleteReport(reportId, token = null) {
    return this._json(`/reports/${reportId}`, { method: 'DELETE' }, token);
  },

  // ── Auth / Profile ────────────────────────────────────────────────────────

  async getProfile(token = null) {
    return this._json('/auth/me', { method: 'GET' }, token);
  },

  async updateProfile(data, token = null) {
    return this._json('/auth/profile', { method: 'PATCH', body: JSON.stringify(data) }, token);
  },

  // ── Dashboard Stats ───────────────────────────────────────────────────────

  async getDashboardStats(token = null) {
    return this._json('/dashboard/stats', { method: 'GET' }, token);
  },

  // ── AI Chat ───────────────────────────────────────────────────────────────

  async createChatSession(data = {}, token = null) {
    return this._json('/chat/sessions', { method: 'POST', body: JSON.stringify(data) }, token);
  },

  async getChatSessions(token = null) {
    return this._json('/chat/sessions', { method: 'GET' }, token);
  },

  async getSessionMessages(sessionId, token = null) {
    return this._json(`/chat/sessions/${sessionId}/messages`, { method: 'GET' }, token);
  },

  async sendChatMessage(sessionId, message, analysisId = null, token = null) {
    const body = { message };
    if (analysisId) body.analysis_id = analysisId;
    return this._json(`/chat/sessions/${sessionId}/message`, { method: 'POST', body: JSON.stringify(body) }, token);
  },

  async deleteChatSession(sessionId, token = null) {
    return this._json(`/chat/sessions/${sessionId}`, { method: 'DELETE' }, token);
  },

  // ── Job Descriptions ──────────────────────────────────────────────────────

  async createJobDescription(data, token = null) {
    return this._json('/job-descriptions', { method: 'POST', body: JSON.stringify(data) }, token);
  },

  async getJobDescriptions(token = null) {
    return this._json('/job-descriptions', { method: 'GET' }, token);
  },

  async getJobDescription(jdId, token = null) {
    return this._json(`/job-descriptions/${jdId}`, { method: 'GET' }, token);
  },

  async deleteJobDescription(jdId, token = null) {
    return this._json(`/job-descriptions/${jdId}`, { method: 'DELETE' }, token);
  },

  async matchJD(jdId, analysisId, token = null) {
    return this._json(`/job-descriptions/${jdId}/match`, { method: 'POST', body: JSON.stringify({ analysis_id: analysisId }) }, token);
  },

  async getJDMatches(token = null) {
    return this._json('/job-descriptions/matches', { method: 'GET' }, token);
  },

  // ── Skill Gap Roadmap ─────────────────────────────────────────────────────

  async generateSkillRoadmap(analysisId, token = null) {
    return this._json('/skill-gap/generate', { method: 'POST', body: JSON.stringify({ analysis_id: analysisId }) }, token);
  },

  async getSkillRoadmap(token = null) {
    return this._json('/skill-gap', { method: 'GET' }, token);
  },

  async updateRoadmapItem(roadmapId, data, token = null) {
    return this._json(`/skill-gap/${roadmapId}`, { method: 'PATCH', body: JSON.stringify(data) }, token);
  },

  async deleteRoadmapItem(roadmapId, data, token = null) {
    return this._json(`/skill-gap/${roadmapId}`, { method: 'DELETE' }, token);
  },

  // ── Resume Comparison ─────────────────────────────────────────────────────

  async compareResumes(analysisIds, name = 'Resume Comparison', token = null) {
    return this._json('/compare', { method: 'POST', body: JSON.stringify({ analysis_ids: analysisIds, name }) }, token);
  },

  async getComparisons(token = null) {
    return this._json('/compare', { method: 'GET' }, token);
  },

  async deleteComparison(comparisonId, token = null) {
    return this._json(`/compare/${comparisonId}`, { method: 'DELETE' }, token);
  },

  // ── Resume Tailoring ──────────────────────────────────────────────────────

  async tailorResume(analysisId, jdId, token = null) {
    return this._json('/tailor', { method: 'POST', body: JSON.stringify({ analysis_id: analysisId, jd_id: jdId }) }, token);
  },

  // ── Notifications & Activity ──────────────────────────────────────────────

  async getNotifications(limit = 20, token = null) {
    return this._json(`/notifications?limit=${limit}`, { method: 'GET' }, token);
  },

  async markNotificationRead(notifId, token = null) {
    return this._json(`/notifications/${notifId}/read`, { method: 'PATCH' }, token);
  },

  async getActivityFeed(limit = 10, token = null) {
    return this._json(`/activity?limit=${limit}`, { method: 'GET' }, token);
  },
};

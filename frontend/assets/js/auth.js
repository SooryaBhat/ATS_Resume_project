/* ==========================================================================
   TalentMatch AI - Supabase Auth Manager (Direct REST API — No SDK Required)

   ROOT CAUSE of original failure:
   @supabase/supabase-js v2.111.0 (the latest) does NOT ship a UMD/browser
   bundle. The CDN tag loaded a Node.js CJS file that does nothing in a browser,
   so window.supabase was never defined, and supabaseClient remained null.

   SOLUTION:
   We call the Supabase Auth REST API directly using fetch(). This requires
   zero external dependencies and works in any browser.

   Supabase Auth REST endpoints used:
     POST /auth/v1/signup              — Create account
     POST /auth/v1/token?grant_type=password — Sign in
     POST /auth/v1/logout              — Sign out
     GET  /auth/v1/user                — Get current user (with JWT)

   Session persistence: stored in localStorage under 'talentmatch_session'.
   ========================================================================== */

const Auth = {
  currentUser:  null,
  accessToken:  null,
  refreshToken: null,

  _initPromise: null,
  _config:      null,   // { supabase_url, supabase_anon_key }

  // ── Entry point ──────────────────────────────────────────────────────────

  async init() {
    if (this._initPromise) return this._initPromise;
    this._initPromise = this._doInit();
    return this._initPromise;
  },

  ready() {
    return this._initPromise || Promise.resolve();
  },

  async _doInit() {
    console.log('[Auth] ① Starting initialization…');

    // Step 1: fetch config from FastAPI backend
    this._config = await this._fetchConfig();

    if (!this._config) {
      console.error(
        '[Auth] ✗ Could not reach backend /api/v1/config endpoint\n' +
        '  → Ensure backend server is running and accessible.'
      );
      return;
    }
    console.log('[Auth] ② Config loaded ✓', {
      url:     this._config.supabase_url,
      anonKey: this._config.supabase_anon_key?.slice(0, 20) + '…',
    });

    // Step 2: restore persisted session from localStorage
    const stored = this._loadStoredSession();
    if (stored) {
      console.log('[Auth] ③ Found stored session, validating…');
      await this._applyAndValidateSession(stored);
    } else {
      console.log('[Auth] ③ No stored session — user is logged out.');
    }

    console.log('[Auth] ④ Init complete ✓ | isAuthenticated:', this.isAuthenticated());
  },

  // ── Supabase Auth REST calls ─────────────────────────────────────────────

  /**
   * Returns the base URL for Supabase Auth API calls.
   */
  _authUrl(path) {
    return `${this._config.supabase_url}/auth/v1${path}`;
  },

  /**
   * Common headers for anon-level requests (signup, signin).
   */
  _anonHeaders() {
    return {
      'Content-Type':  'application/json',
      'apikey':        this._config.supabase_anon_key,
    };
  },

  /**
   * Common headers for authenticated requests (getUser, signOut).
   */
  _authedHeaders() {
    return {
      'Content-Type':   'application/json',
      'apikey':         this._config.supabase_anon_key,
      'Authorization':  `Bearer ${this.accessToken}`,
    };
  },

  // ── Public auth operations ───────────────────────────────────────────────

  async signUp(email, password, fullName = '') {
    console.log('[Auth] signUp() called — awaiting ready()…');
    await this.ready();
    console.log('[Auth] signUp() — ready. Config exists:', !!this._config);

    if (!this._config) {
      App.showToast('Backend is unreachable. Is the FastAPI server running on port 8000?', 'error');
      return;
    }

    const btn = document.querySelector('#view-register button[type="submit"]');
    this._setButtonLoading(btn, true, 'Creating Account…');

    try {
      console.log('[Auth] signUp() → calling Supabase Auth REST API…');

      const resp = await fetch(this._authUrl('/signup'), {
        method:  'POST',
        headers: this._anonHeaders(),
        body:    JSON.stringify({
          email,
          password,
          data: { full_name: fullName },
        }),
      });

      const json = await resp.json();
      console.log('[Auth] signUp() ← Supabase response status:', resp.status, json);

      if (!resp.ok) {
        // Supabase returns { error: "...", message: "..." }
        const msg = json.error_description || json.message || json.error || `HTTP ${resp.status}`;
        throw new Error(msg);
      }

      // Response shape: { access_token, refresh_token, user, ... }
      //  OR (if email confirm required): { id, email, confirmation_sent_at, ... }
      if (json.access_token) {
        // Auto-confirmed — session returned immediately
        await this._applyTokenResponse(json);
        App.showToast('Account created and signed in! Welcome!', 'success');
        Router.navigate('dashboard');
        if (window.App) App.bootstrapLiveData().catch(console.warn);
      } else if (json.id || json.email) {
        // Email confirmation required — Supabase returns user object, no session yet
        App.showToast(
          '✅ Account created! Check your email for a confirmation link, then sign in.',
          'success',
        );
        Router.navigate('login');
      } else {
        // Unexpected response
        throw new Error('Unexpected signup response from Supabase. Check console.');
      }

      return json;
    } catch (err) {
      console.error('[Auth] signUp() failed:', err);
      App.showToast(`Sign Up Failed: ${err.message}`, 'error');
    } finally {
      this._setButtonLoading(btn, false, 'Create Account');
    }
  },

  async signIn(email, password) {
    console.log('[Auth] signIn() called — awaiting ready()…');
    await this.ready();

    if (!this._config) {
      App.showToast('Backend is unreachable. Is the FastAPI server running on port 8000?', 'error');
      return;
    }

    const btn = document.querySelector('#view-login button[type="submit"]');
    this._setButtonLoading(btn, true, 'Signing In…');

    try {
      const resp = await fetch(
        this._authUrl('/token?grant_type=password'),
        {
          method:  'POST',
          headers: this._anonHeaders(),
          body:    JSON.stringify({ email, password }),
        }
      );

      const json = await resp.json();
      console.log('[Auth] signIn() ← Supabase response status:', resp.status);

      if (!resp.ok) {
        const msg = json.error_description || json.message || json.error || `HTTP ${resp.status}`;
        throw new Error(msg);
      }

      await this._applyTokenResponse(json);
      App.showToast('Signed in successfully!', 'success');
      Router.navigate('dashboard');
      if (window.App) App.bootstrapLiveData().catch(console.warn);
      return json;
    } catch (err) {
      console.error('[Auth] signIn() failed:', err);
      App.showToast(`Sign In Failed: ${err.message}`, 'error');
    } finally {
      this._setButtonLoading(btn, false, 'Sign In');
    }
  },

  async signOut() {
    if (this.accessToken && this._config) {
      try {
        await fetch(this._authUrl('/logout'), {
          method:  'POST',
          headers: this._authedHeaders(),
        });
      } catch (err) {
        console.warn('[Auth] signOut REST call failed (non-fatal):', err.message);
      }
    }
    this._clearSession();
    App.showToast('Signed out successfully.', 'info');
    Router.navigate('login');
  },

  // ── Session management ───────────────────────────────────────────────────

  async _applyTokenResponse(json) {
    // Supabase returns: access_token, refresh_token, expires_in, user
    this.accessToken  = json.access_token;
    this.refreshToken = json.refresh_token;
    this.currentUser  = json.user;
    this._saveSession(json);
    this._updateUserUI(json.user);
    console.log('[Auth] Session applied for:', json.user?.email);
  },

  async _applyAndValidateSession(stored) {
    this.accessToken  = stored.access_token;
    this.refreshToken = stored.refresh_token;
    this.currentUser  = stored.user;
    this._updateUserUI(stored.user);
    console.log('[Auth] Restored session for:', stored.user?.email);
    // Validate token is still good
    const ok = await this._validateToken();
    if (!ok) {
      console.warn('[Auth] Stored session expired — attempting token refresh…');
      const refreshed = await this._refreshSession();
      if (!refreshed) {
        console.warn('[Auth] Token refresh failed — logging out.');
        this._clearSession();
      }
    }
  },

  async _validateToken() {
    if (!this.accessToken || !this._config) return false;
    try {
      const resp = await fetch(this._authUrl('/user'), {
        headers: this._authedHeaders(),
      });
      return resp.ok;
    } catch {
      return false;
    }
  },

  async _refreshSession() {
    if (!this.refreshToken || !this._config) return false;
    try {
      const resp = await fetch(
        this._authUrl('/token?grant_type=refresh_token'),
        {
          method:  'POST',
          headers: this._anonHeaders(),
          body:    JSON.stringify({ refresh_token: this.refreshToken }),
        }
      );
      if (!resp.ok) return false;
      const json = await resp.json();
      await this._applyTokenResponse(json);
      return true;
    } catch {
      return false;
    }
  },

  _saveSession(json) {
    try {
      localStorage.setItem('talentmatch_session', JSON.stringify({
        access_token:  json.access_token,
        refresh_token: json.refresh_token,
        user:          json.user,
        expires_at:    Date.now() + (json.expires_in || 3600) * 1000,
      }));
    } catch { /* localStorage unavailable */ }
  },

  _loadStoredSession() {
    try {
      const raw = localStorage.getItem('talentmatch_session');
      if (!raw) return null;
      const stored = JSON.parse(raw);
      // Discard obviously expired sessions (token itself may still be valid
      // up to grace period, _validateToken() will confirm)
      if (Date.now() > stored.expires_at + 300_000) {
        localStorage.removeItem('talentmatch_session');
        return null;
      }
      return stored;
    } catch {
      return null;
    }
  },

  _clearSession() {
    this.accessToken  = null;
    this.refreshToken = null;
    this.currentUser  = null;
    try { localStorage.removeItem('talentmatch_session'); } catch { /* */ }
  },

  _updateUserUI(user) {
    if (!user) return;
    const displayName = user.user_metadata?.full_name || user.email?.split('@')[0] || 'User';
    const nameEl = document.querySelector('.user-name-text');
    if (nameEl) nameEl.textContent = displayName;
  },

  // ── Public helpers ───────────────────────────────────────────────────────

  getAccessToken() { return this.accessToken; },
  isAuthenticated() { return !!this.currentUser && !!this.accessToken; },

  // ── Config fetch ─────────────────────────────────────────────────────────

  async _fetchConfig() {
    if (this._config) return this._config;
    try {
      const controller = new AbortController();
      const timeoutId  = setTimeout(() => controller.abort(), 5000);
      const baseUrl    = typeof API_BASE_URL !== 'undefined' ? API_BASE_URL : 'https://talentmatch-ai-grv6.onrender.com/api/v1';
      const resp       = await fetch(`${baseUrl}/config`, {
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      if (!resp.ok) {
        console.error('[Auth] /api/v1/config returned HTTP', resp.status);
        return null;
      }
      const cfg = await resp.json();
      if (!cfg.supabase_url || !cfg.supabase_anon_key) {
        console.error('[Auth] Config payload missing required fields:', cfg);
        return null;
      }
      return cfg;
    } catch (err) {
      if (err.name === 'AbortError') {
        console.error('[Auth] Config fetch timed out after 5s — check backend connectivity');
      } else {
        console.error('[Auth] Config fetch failed:', err.message);
      }
      return null;
    }
  },

  // ── UI helpers ────────────────────────────────────────────────────────────

  _setButtonLoading(btn, loading, text) {
    if (!btn) return;
    btn.disabled    = loading;
    btn.textContent = text;
    btn.style.opacity = loading ? '0.7' : '';
  },
};

/* ==========================================================================
   TalentMatch AI - Supabase Auth & Session Manager
   ========================================================================== */

const Auth = {
  supabaseClient: null,
  currentUser: null,
  accessToken: null,

  async init() {
    // 1. Fetch public config from backend
    const config = await API.fetchConfig();
    
    if (config && config.supabase_url && config.supabase_anon_key && window.supabase) {
      try {
        this.supabaseClient = window.supabase.createClient(
          config.supabase_url,
          config.supabase_anon_key
        );
        console.log('Supabase JS Client initialized successfully');

        // Check active session
        const { data: { session } } = await this.supabaseClient.auth.getSession();
        if (session) {
          this.setSession(session);
        }

        // Listen for Auth changes
        this.supabaseClient.auth.onAuthStateChange((_event, session) => {
          this.setSession(session);
        });
      } catch (err) {
        console.warn('Supabase Auth init warning:', err);
      }
    }
  },

  setSession(session) {
    if (session) {
      this.currentUser = session.user;
      this.accessToken = session.access_token;
      this.updateUserUI(session.user);
    } else {
      this.currentUser = null;
      this.accessToken = null;
    }
  },

  updateUserUI(user) {
    const nameText = document.querySelector('.user-name-text');
    if (nameText && user.email) {
      nameText.textContent = user.user_metadata?.full_name || user.email.split('@')[0];
    }
  },

  getAccessToken() {
    return this.accessToken;
  },

  // Auth Operations
  async signUp(email, password, fullName = '') {
    if (!this.supabaseClient) {
      throw new Error('Auth client not configured. Check Supabase keys.');
    }

    const { data, error } = await this.supabaseClient.auth.signUp({
      email,
      password,
      options: {
        data: { full_name: fullName }
      }
    });

    if (error) throw error;
    return data;
  },

  async signIn(email, password) {
    if (!this.supabaseClient) {
      // Fallback for offline demo mode
      App.showToast('Signing in (Demo Mode)...', 'success');
      Router.navigate('dashboard');
      return;
    }

    const { data, error } = await this.supabaseClient.auth.signInWithPassword({
      email,
      password
    });

    if (error) throw error;
    this.setSession(data.session);
    App.showToast('Signed in successfully!', 'success');
    Router.navigate('dashboard');
    return data;
  },

  async signOut() {
    if (this.supabaseClient) {
      await this.supabaseClient.auth.signOut();
    }
    this.setSession(null);
    App.showToast('Signed out.', 'info');
    Router.navigate('login');
  }
};

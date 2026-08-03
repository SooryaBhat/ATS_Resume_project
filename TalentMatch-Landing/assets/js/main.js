/* ==========================================================================
   TalentMatch AI - Main Application Logic & Event Handlers
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initNavbarScroll();
  initMobileMenu();
  initActionButtons();
});

/**
 * Adds dark glass background to navbar on scroll
 */
function initNavbarScroll() {
  const navbar = document.querySelector('.navbar');
  if (!navbar) return;

  window.addEventListener('scroll', () => {
    if (window.scrollY > 40) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  });
}

/**
 * Mobile Navigation Toggle
 */
function initMobileMenu() {
  const toggleBtn = document.querySelector('.mobile-toggle');
  const navMenu = document.querySelector('.nav-menu');

  if (toggleBtn && navMenu) {
    toggleBtn.addEventListener('click', () => {
      navMenu.classList.toggle('active');
    });

    // Close menu when clicking links
    document.querySelectorAll('.nav-link').forEach(link => {
      link.addEventListener('click', () => {
        navMenu.classList.remove('active');
      });
    });
  }
}

/**
 * Action Buttons Click Routing
 * Seamlessly routes interactive button clicks to target live endpoints
 */
function initActionButtons() {
  const linkMappings = {
    'btn-demo': 'https://talentmatchai-three.vercel.app',
    'btn-github': 'https://github.com/SooryaBhat/ATS_Resume_project.git',
    'btn-backend': 'https://talentmatch-ai-grv6.onrender.com',
    'btn-profile': 'https://github.com/SooryaBhat',
    'btn-linkedin': 'https://www.linkedin.com/in/sooryabhat'
  };

  Object.keys(linkMappings).forEach(classOrId => {
    const buttons = document.querySelectorAll(`.${classOrId}, #${classOrId}`);
    buttons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        // If button has an explicit href attribute, respect it, otherwise open target URL
        const targetUrl = linkMappings[classOrId];
        if (targetUrl) {
          window.open(targetUrl, '_blank', 'noopener,noreferrer');
        }
      });
    });
  });
}

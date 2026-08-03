/* ==========================================================================
   TalentMatch AI - Scroll Animations & Stat Counters
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initScrollObserver();
  initStatCounters();
});

/**
 * Initialize Intersection Observer for Scroll Animations
 */
function initScrollObserver() {
  const revealElements = document.querySelectorAll('.reveal-fade, .reveal-slide-left, .reveal-slide-right, .reveal-zoom');
  
  const observerOptions = {
    root: null,
    rootMargin: '0px 0px -100px 0px',
    threshold: 0.15
  };

  const observer = new IntersectionObserver((entries, obs) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('active');
        // Unobserve after animating once for performance
        obs.unobserve(entry.target);
      }
    });
  }, observerOptions);

  revealElements.forEach(el => observer.observe(el));
}

/**
 * Animated Stat Counter when scrolled into view
 */
function initStatCounters() {
  const statNumbers = document.querySelectorAll('.stat-number');
  
  const observerOptions = {
    threshold: 0.5
  };

  const observer = new IntersectionObserver((entries, obs) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el = entry.target;
        const targetValue = parseInt(el.getAttribute('data-target') || '0', 10);
        const prefix = el.getAttribute('data-prefix') || '';
        const suffix = el.getAttribute('data-suffix') || '';
        
        animateCounter(el, targetValue, prefix, suffix);
        obs.unobserve(el);
      }
    });
  }, observerOptions);

  statNumbers.forEach(num => observer.observe(num));
}

/**
 * Helper function to run numeric count animation
 */
function animateCounter(element, target, prefix, suffix) {
  let start = 0;
  const duration = 2000;
  const startTime = performance.now();

  function updateCounter(currentTime) {
    const elapsedTime = currentTime - startTime;
    const progress = Math.min(elapsedTime / duration, 1);
    
    // EaseOutCubic timing function
    const easeProgress = 1 - Math.pow(1 - progress, 3);
    const currentValue = Math.floor(easeProgress * target);

    element.textContent = `${prefix}${currentValue.toLocaleString()}${suffix}`;

    if (progress < 1) {
      requestAnimationFrame(updateCounter);
    } else {
      element.textContent = `${prefix}${target.toLocaleString()}${suffix}`;
    }
  }

  requestAnimationFrame(updateCounter);
}

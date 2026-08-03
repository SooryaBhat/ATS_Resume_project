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
        obs.unobserve(entry.target);
      }
    });
  }, observerOptions);

  revealElements.forEach(el => observer.observe(el));
}

/**
 * Animated Highlights & Verifiable Project Metrics
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
        const targetAttr = el.getAttribute('data-target') || '';
        const prefix = el.getAttribute('data-prefix') || '';
        const suffix = el.getAttribute('data-suffix') || '';
        
        const numericVal = parseFloat(targetAttr);
        if (!isNaN(numericVal) && isFinite(numericVal)) {
          animateCounter(el, numericVal, prefix, suffix);
        } else {
          el.textContent = `${prefix}${targetAttr}${suffix}`;
        }
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
  const duration = 1800;
  const startTime = performance.now();
  const isDecimal = target % 1 !== 0;

  function updateCounter(currentTime) {
    const elapsedTime = currentTime - startTime;
    const progress = Math.min(elapsedTime / duration, 1);
    
    // EaseOutCubic timing function
    const easeProgress = 1 - Math.pow(1 - progress, 3);
    const currentValue = easeProgress * target;

    const formattedValue = isDecimal ? currentValue.toFixed(1) : Math.floor(currentValue);
    element.textContent = `${prefix}${formattedValue}${suffix}`;

    if (progress < 1) {
      requestAnimationFrame(updateCounter);
    } else {
      element.textContent = `${prefix}${isDecimal ? target.toFixed(1) : target}${suffix}`;
    }
  }

  requestAnimationFrame(updateCounter);
}

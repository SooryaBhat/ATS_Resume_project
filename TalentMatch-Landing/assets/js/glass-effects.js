/* ==========================================================================
   TalentMatch AI - Glassmorphism & Card Micro-Interactions
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initGlassGlowEffect();
  initTiltEffect();
});

/**
 * Creates dynamic mouse-follow glow effect on glass cards
 */
function initGlassGlowEffect() {
  const cards = document.querySelectorAll('.glass-card, .overview-card, .tech-card, .macbook-mockup');
  
  cards.forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      
      card.style.setProperty('--mouse-x', `${x}px`);
      card.style.setProperty('--mouse-y', `${y}px`);
    });
  });
}

/**
 * 3D subtle card tilt on hover
 */
function initTiltEffect() {
  const tiltCards = document.querySelectorAll('.overview-card, .tech-card');
  
  tiltCards.forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      
      const rotateX = (centerY - y) / 20;
      const rotateY = (x - centerX) / 20;
      
      card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-4px)`;
    });
    
    card.addEventListener('mouseleave', () => {
      card.style.transform = `perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0px)`;
    });
  });
}

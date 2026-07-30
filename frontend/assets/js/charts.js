/* ==========================================================================
   TalentMatch AI - Chart.js Visualizations (Radar, Line, Bar, Doughnut)
   ========================================================================== */

const ChartEngine = {
  instances: {},

  // Get CSS Variables for Theme Support
  getThemeColors() {
    const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
    return {
      textPrimary: isDark ? '#f8fafc' : '#0f172a',
      textSecondary: isDark ? '#94a3b8' : '#64748b',
      gridColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.08)',
      primary: '#6366f1',
      secondary: '#a855f7',
      tertiary: '#ec4899',
      success: '#10b981',
      warning: '#f59e0b'
    };
  },

  // 1. Dashboard Score Trend Line Chart
  initScoreTrendChart(canvasId, trendData) {
    if (!document.getElementById(canvasId)) return;
    if (this.instances[canvasId]) this.instances[canvasId].destroy();

    const colors = this.getThemeColors();
    const ctx = document.getElementById(canvasId).getContext('2d');

    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, 'rgba(99, 102, 241, 0.4)');
    gradient.addColorStop(1, 'rgba(99, 102, 241, 0.0)');

    this.instances[canvasId] = new Chart(ctx, {
      type: 'line',
      data: {
        labels: trendData.labels,
        datasets: [{
          label: 'ATS Overall Score',
          data: trendData.scores,
          borderColor: colors.primary,
          borderWidth: 3,
          backgroundColor: gradient,
          fill: true,
          tension: 0.4,
          pointBackgroundColor: colors.secondary,
          pointBorderColor: '#ffffff',
          pointBorderWidth: 2,
          pointRadius: 6,
          pointHoverRadius: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#1f293d',
            titleColor: '#ffffff',
            bodyColor: '#f8fafc',
            borderColor: colors.primary,
            borderWidth: 1,
            padding: 12,
            displayColors: false
          }
        },
        scales: {
          x: {
            grid: { color: colors.gridColor },
            ticks: { color: colors.textSecondary, font: { family: 'Plus Jakarta Sans' } }
          },
          y: {
            min: 50,
            max: 100,
            grid: { color: colors.gridColor },
            ticks: { color: colors.textSecondary, font: { family: 'Plus Jakarta Sans' } }
          }
        }
      }
    });
  },

  // 2. Component Score Radar Chart
  initComponentRadarChart(canvasId, radarData) {
    if (!document.getElementById(canvasId)) return;
    if (this.instances[canvasId]) this.instances[canvasId].destroy();

    const colors = this.getThemeColors();
    const ctx = document.getElementById(canvasId).getContext('2d');

    this.instances[canvasId] = new Chart(ctx, {
      type: 'radar',
      data: {
        labels: radarData.labels,
        datasets: [{
          label: 'Component Rating (%)',
          data: radarData.percentages,
          backgroundColor: 'rgba(168, 85, 247, 0.25)',
          borderColor: colors.secondary,
          borderWidth: 2,
          pointBackgroundColor: colors.primary,
          pointBorderColor: '#ffffff',
          pointRadius: 5
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        },
        scales: {
          r: {
            angleLines: { color: colors.gridColor },
            grid: { color: colors.gridColor },
            pointLabels: {
              color: colors.textPrimary,
              font: { family: 'Plus Jakarta Sans', size: 12, weight: '600' }
            },
            ticks: { display: false, min: 0, max: 100 }
          }
        }
      }
    });
  },

  // 3. Keyword Distribution Doughnut Chart
  initKeywordDoughnutChart(canvasId, kwData) {
    if (!document.getElementById(canvasId)) return;
    if (this.instances[canvasId]) this.instances[canvasId].destroy();

    const colors = this.getThemeColors();
    const ctx = document.getElementById(canvasId).getContext('2d');

    this.instances[canvasId] = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: kwData.labels,
        datasets: [{
          data: kwData.counts,
          backgroundColor: [colors.primary, colors.secondary, colors.tertiary, colors.success],
          borderWidth: 2,
          borderColor: colors.gridColor
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: colors.textPrimary, font: { family: 'Plus Jakarta Sans', size: 11 } }
          }
        },
        cutout: '70%'
      }
    });
  },

  // 4. Multi-Resume Comparison Bar Chart
  initComparisonBarChart(canvasId, comparisonData) {
    if (!document.getElementById(canvasId)) return;
    if (this.instances[canvasId]) this.instances[canvasId].destroy();

    const colors = this.getThemeColors();
    const ctx = document.getElementById(canvasId).getContext('2d');

    this.instances[canvasId] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: comparisonData.map(item => item.name),
        datasets: [{
          label: 'ATS Score',
          data: comparisonData.map(item => item.atsScore),
          backgroundColor: [colors.primary, colors.secondary, colors.tertiary],
          borderRadius: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: colors.textPrimary, font: { family: 'Plus Jakarta Sans' } }
          },
          y: {
            min: 0,
            max: 100,
            grid: { color: colors.gridColor },
            ticks: { color: colors.textSecondary }
          }
        }
      }
    });
  },

  // Destroy all instances on theme change to force re-color
  rebuildCharts() {
    Object.keys(this.instances).forEach(id => {
      if (this.instances[id]) this.instances[id].destroy();
    });
    this.instances = {};

    // Re-render if elements exist
    this.initScoreTrendChart('scoreTrendChart', MockData.scoreTrend);
    this.initComponentRadarChart('componentRadarChart', MockData.componentBreakdown);
    this.initKeywordDoughnutChart('keywordDoughnutChart', MockData.keywordDistribution);
    this.initComparisonBarChart('comparisonBarChart', MockData.resumeComparison);
  }
};

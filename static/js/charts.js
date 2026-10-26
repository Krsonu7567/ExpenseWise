/**
 * charts.js - Chart.js Visualizations for ExpenseWise
 * 
 * Renders:
 * 1. Category Expense Breakdown (Doughnut Chart)
 * 2. Monthly Income vs Expense Trend (Grouped Bar Chart)
 */

document.addEventListener('DOMContentLoaded', function () {
  initDashboardCharts();
});

function initDashboardCharts() {
  const categoryCanvas = document.getElementById('categoryDoughnutChart');
  const trendCanvas = document.getElementById('monthlyTrendBarChart');

  // If chart canvases do not exist on the current page, skip initialization
  if (!categoryCanvas && !trendCanvas) {
    return;
  }

  // Curated harmonious color palette for categories
  const chartColors = [
    '#4f46e5', // Indigo
    '#06b6d4', // Cyan
    '#f59e0b', // Amber
    '#10b981', // Emerald
    '#ec4899', // Pink
    '#8b5cf6', // Violet
    '#3b82f6', // Blue
    '#f97316', // Orange
    '#14b8a6', // Teal
    '#64748b'  // Slate
  ];

  // =========================================================================
  // 1. Category Breakdown Doughnut Chart
  // =========================================================================
  if (categoryCanvas) {
    const rawData = categoryCanvas.getAttribute('data-chart-data');
    let categories = [];
    
    try {
      categories = rawData ? JSON.parse(rawData) : [];
    } catch (e) {
      console.error('Error parsing category chart data:', e);
    }

    const emptyMsg = document.getElementById('categoryChartEmpty');

    if (!categories || categories.length === 0) {
      if (emptyMsg) emptyMsg.classList.remove('d-none');
      categoryCanvas.classList.add('d-none');
    } else {
      if (emptyMsg) emptyMsg.classList.add('d-none');
      categoryCanvas.classList.remove('d-none');

      const labels = categories.map(c => c.category);
      const dataValues = categories.map(c => c.total_rupees);

      new Chart(categoryCanvas, {
        type: 'doughnut',
        data: {
          labels: labels,
          datasets: [{
            data: dataValues,
            backgroundColor: chartColors.slice(0, labels.length),
            borderWidth: 2,
            borderColor: '#ffffff',
            hoverOffset: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: {
                boxWidth: 12,
                padding: 14,
                font: {
                  family: "'Plus Jakarta Sans', sans-serif",
                  size: 12,
                  weight: '600'
                }
              }
            },
            tooltip: {
              callbacks: {
                label: function (context) {
                  const label = context.label || '';
                  const value = context.parsed || 0;
                  const total = context.dataset.data.reduce((a, b) => a + b, 0);
                  const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                  return ` ${label}: ₹${value.toLocaleString('en-IN', { minimumFractionDigits: 2 })} (${percentage}%)`;
                }
              }
            }
          },
          cutout: '65%'
        }
      });
    }
  }

  // =========================================================================
  // 2. Monthly Trend (Income vs Expense) Bar Chart
  // =========================================================================
  if (trendCanvas) {
    const rawTrend = trendCanvas.getAttribute('data-chart-data');
    let trendData = [];

    try {
      trendData = rawTrend ? JSON.parse(rawTrend) : [];
    } catch (e) {
      console.error('Error parsing trend chart data:', e);
    }

    const trendEmptyMsg = document.getElementById('trendChartEmpty');

    if (!trendData || trendData.length === 0) {
      if (trendEmptyMsg) trendEmptyMsg.classList.remove('d-none');
      trendCanvas.classList.add('d-none');
    } else {
      if (trendEmptyMsg) trendEmptyMsg.classList.add('d-none');
      trendCanvas.classList.remove('d-none');

      // Format month strings e.g. "2026-10" -> "Oct 2026"
      const labels = trendData.map(item => {
        const parts = item.month.split('-');
        if (parts.length === 2) {
          const d = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, 1);
          return d.toLocaleDateString('en-IN', { month: 'short', year: 'numeric' });
        }
        return item.month;
      });

      const incomeValues = trendData.map(item => item.income_rupees);
      const expenseValues = trendData.map(item => item.expense_rupees);

      new Chart(trendCanvas, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [
            {
              label: 'Income',
              data: incomeValues,
              backgroundColor: 'rgba(16, 185, 129, 0.85)',
              borderColor: '#10b981',
              borderWidth: 1,
              borderRadius: 6,
              barPercentage: 0.6,
              categoryPercentage: 0.7
            },
            {
              label: 'Expense',
              data: expenseValues,
              backgroundColor: 'rgba(239, 68, 68, 0.85)',
              borderColor: '#ef4444',
              borderWidth: 1,
              borderRadius: 6,
              barPercentage: 0.6,
              categoryPercentage: 0.7
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'top',
              align: 'end',
              labels: {
                boxWidth: 14,
                font: {
                  family: "'Plus Jakarta Sans', sans-serif",
                  size: 12,
                  weight: '600'
                }
              }
            },
            tooltip: {
              callbacks: {
                label: function (context) {
                  const label = context.dataset.label || '';
                  const val = context.parsed.y || 0;
                  return ` ${label}: ₹${val.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
                }
              }
            }
          },
          scales: {
            x: {
              grid: {
                display: false
              },
              ticks: {
                font: {
                  family: "'Plus Jakarta Sans', sans-serif",
                  size: 11
                }
              }
            },
            y: {
              beginAtZero: true,
              grid: {
                color: '#f1f5f9'
              },
              ticks: {
                font: {
                  family: "'Plus Jakarta Sans', sans-serif",
                  size: 11
                },
                callback: function (value) {
                  return '₹' + value.toLocaleString('en-IN');
                }
              }
            }
          }
        }
      });
    }
  }
}

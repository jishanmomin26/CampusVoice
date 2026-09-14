import React from 'react';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from 'recharts';
import './DashboardCharts.css';

// Semantic color constants aligned with CampusVoice design system
const SENTIMENT_COLORS = {
  Positive: '#10b981',
  Neutral: '#3b82f6',
  Negative: '#ef4444',
  Unclassified: '#6b7280',
};

const PRIORITY_COLORS = {
  High: '#ef4444',
  Medium: '#f59e0b',
  Low: '#10b981',
  Unclassified: '#6b7280',
};

const CATEGORY_PALETTE = [
  '#8b5cf6',
  '#ec4899',
  '#3b82f6',
  '#10b981',
  '#f59e0b',
  '#6366f1',
  '#14b8a6',
  '#a855f7',
];

/**
 * Custom dark glassmorphic tooltip for Recharts visualizations
 */
function CustomChartTooltip({ active, payload, label, denominator, denominatorLabel }) {
  if (!active || !payload || !payload.length) {
    return null;
  }

  const item = payload[0];
  const name = item.name || label || item.payload?.name;
  const count = item.value ?? item.payload?.count ?? 0;
  const percent =
    denominator && denominator > 0
      ? `${((count / denominator) * 100).toFixed(1)}%`
      : '0.0%';

  return (
    <div className="custom-chart-tooltip" role="tooltip">
      <p className="tooltip-item-name">{name}</p>
      <div className="tooltip-metrics">
        <span className="tooltip-count">
          <strong>{count}</strong> {count === 1 ? 'submission' : 'submissions'}
        </span>
        <span className="tooltip-share">
          ({percent} of {denominatorLabel || 'total'})
        </span>
      </div>
    </div>
  );
}

/**
 * 1. SentimentChart — Donut/Pie Chart
 */
export function SentimentChart({ sentiment = {}, total = 0 }) {
  const data = [
    { name: 'Positive', count: sentiment.positive ?? 0, color: SENTIMENT_COLORS.Positive },
    { name: 'Neutral', count: sentiment.neutral ?? 0, color: SENTIMENT_COLORS.Neutral },
    { name: 'Negative', count: sentiment.negative ?? 0, color: SENTIMENT_COLORS.Negative },
    { name: 'Unclassified', count: sentiment.unclassified ?? 0, color: SENTIMENT_COLORS.Unclassified },
  ];

  // Filter for segments with positive values to render clean donut slices
  const chartData = data.filter((d) => d.count > 0);
  const hasData = chartData.length > 0;

  if (!hasData) {
    return (
      <div className="chart-empty-container">
        <p className="chart-empty-text">No sentiment data available to visualize.</p>
      </div>
    );
  }

  return (
    <div className="chart-wrapper">
      <div className="chart-responsive-box">
        <ResponsiveContainer width="100%" height={240}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={85}
              paddingAngle={3}
              dataKey="count"
              nameKey="name"
              stroke="rgba(11, 15, 25, 0.8)"
              strokeWidth={2}
            >
              {chartData.map((entry) => (
                <Cell key={`cell-${entry.name}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              content={
                <CustomChartTooltip
                  denominator={total}
                  denominatorLabel="all feedback"
                />
              }
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Accessible custom legend */}
      <div className="chart-custom-legend" aria-label="Sentiment Chart Legend">
        {data.map((d) => (
          <div key={d.name} className="legend-badge-item">
            <span
              className="legend-color-dot"
              style={{ backgroundColor: d.color }}
              aria-hidden="true"
            />
            <span className="legend-label">{d.name}:</span>
            <span className="legend-count">{d.count}</span>
            <span className="legend-pct" title="% of all feedback">
              ({total > 0 ? ((d.count / total) * 100).toFixed(0) : 0}% of all)
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * 2. PriorityChart — Bar Chart
 */
export function PriorityChart({ priority = {}, total = 0 }) {
  const data = [
    { name: 'High', count: priority.high ?? 0, color: PRIORITY_COLORS.High },
    { name: 'Medium', count: priority.medium ?? 0, color: PRIORITY_COLORS.Medium },
    { name: 'Low', count: priority.low ?? 0, color: PRIORITY_COLORS.Low },
    { name: 'Unclassified', count: priority.unclassified ?? 0, color: PRIORITY_COLORS.Unclassified },
  ];

  const hasData = data.some((d) => d.count > 0);

  if (!hasData) {
    return (
      <div className="chart-empty-container">
        <p className="chart-empty-text">No priority data available to visualize.</p>
      </div>
    );
  }

  return (
    <div className="chart-wrapper">
      <div className="chart-responsive-box">
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={data} margin={{ top: 15, right: 15, left: -10, bottom: 5 }}>
            <XAxis
              dataKey="name"
              stroke="#9ca3af"
              fontSize={12}
              tickLine={false}
              axisLine={{ stroke: 'rgba(255, 255, 255, 0.1)' }}
            />
            <YAxis
              allowDecimals={false}
              stroke="#9ca3af"
              fontSize={12}
              tickLine={false}
              axisLine={{ stroke: 'rgba(255, 255, 255, 0.1)' }}
            />
            <Tooltip
              cursor={{ fill: 'rgba(255, 255, 255, 0.04)' }}
              content={
                <CustomChartTooltip
                  denominator={total}
                  denominatorLabel="all feedback"
                />
              }
            />
            <Bar dataKey="count" radius={[6, 6, 0, 0]}>
              {data.map((entry) => (
                <Cell key={`bar-${entry.name}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Accessible custom legend */}
      <div className="chart-custom-legend" aria-label="Priority Chart Legend">
        {data.map((d) => (
          <div key={d.name} className="legend-badge-item">
            <span
              className="legend-color-dot"
              style={{ backgroundColor: d.color }}
              aria-hidden="true"
            />
            <span className="legend-label">{d.name}:</span>
            <span className="legend-count">{d.count}</span>
            <span className="legend-pct" title="% of all feedback">
              ({total > 0 ? ((d.count / total) * 100).toFixed(0) : 0}% of all)
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * 3. CategoryChart — Dynamic Horizontal Bar Chart
 * Zero hardcoded category names; dynamically renders whatever backend returns.
 */
export function CategoryChart({ categories = {}, total = 0 }) {
  const data = Object.entries(categories)
    .map(([name, count], index) => ({
      name,
      count,
      color: CATEGORY_PALETTE[index % CATEGORY_PALETTE.length],
    }))
    .sort((a, b) => b.count - a.count);

  if (!data.length) {
    return (
      <div className="chart-empty-container">
        <p className="chart-empty-text">No categorized feedback available yet.</p>
      </div>
    );
  }

  // Dynamic height calculation based on number of categories so labels never get cramped
  const chartHeight = Math.max(220, data.length * 48);

  return (
    <div className="chart-wrapper category-chart-wrapper">
      <div className="chart-responsive-box" style={{ height: `${chartHeight}px` }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            layout="vertical"
            data={data}
            margin={{ top: 10, right: 25, left: 10, bottom: 5 }}
          >
            <XAxis
              type="number"
              allowDecimals={false}
              stroke="#9ca3af"
              fontSize={12}
              tickLine={false}
              axisLine={{ stroke: 'rgba(255, 255, 255, 0.1)' }}
            />
            <YAxis
              type="category"
              dataKey="name"
              stroke="#e5e7eb"
              fontSize={12}
              tickLine={false}
              axisLine={{ stroke: 'rgba(255, 255, 255, 0.1)' }}
              width={125}
            />
            <Tooltip
              cursor={{ fill: 'rgba(255, 255, 255, 0.04)' }}
              content={
                <CustomChartTooltip
                  denominator={total}
                  denominatorLabel="all feedback"
                />
              }
            />
            <Bar dataKey="count" radius={[0, 6, 6, 0]}>
              {data.map((entry) => (
                <Cell key={`cat-bar-${entry.name}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

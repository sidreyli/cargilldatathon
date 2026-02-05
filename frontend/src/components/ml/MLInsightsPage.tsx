import { motion } from 'framer-motion';
import { Brain, Activity, Calendar, Award, Gauge } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { mockModelInfo, mockPortDelays, mockSeasonalEvents } from '../../data/mockData';
import { useModelInfo, usePortDelays } from '../../api/hooks';
import { congestionColor } from '../../utils/formatters';

const featureLabels: Record<string, string> = {
  portcalls_dry_bulk_rolling7_mean: '7d Port Calls (mean)',
  port_capacity_ratio: 'Port Capacity Ratio',
  portcalls_dry_bulk_rolling30_mean: '30d Port Calls (mean)',
  portcalls_dry_bulk_rolling14_mean: '14d Port Calls (mean)',
  import_dry_bulk_rolling7_mean: '7d Imports (mean)',
  import_dry_bulk_rolling7_sum: '7d Imports (sum)',
  import_dry_bulk_rolling30_sum: '30d Imports (sum)',
  portcalls_dry_bulk_rolling30_std: '30d Port Calls (std)',
  cny_proximity_days: 'CNY Proximity',
  import_dry_bulk_momentum: 'Import Momentum',
  is_china: 'China Port',
  portcalls_dry_bulk_rolling14_std: '14d Port Calls (std)',
  portcalls_dry_bulk_rolling7_std: '7d Port Calls (std)',
  portcalls_dry_bulk_lag7: '7d Port Calls (lag)',
  is_india: 'India Port',
};

const excludedFeatures = new Set([
  'feat_week_of_year', 'portcalls_dry_bulk_lag30', 'feat_month',
  'portcalls_dry_bulk_lag14', 'feat_day_of_week', 'is_cny',
  'is_monsoon_india', 'feat_quarter', 'feat_is_weekend',
  'is_golden_week', 'is_diwali',
]);

const impactColors: Record<string, string> = { high: '#E74C5E', medium: '#F5A623', low: '#0FA67F' };

const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function getMonthIndex(dateStr: string): number {
  return new Date(dateStr).getMonth();
}

function getMonthSpan(start: string, end: string): [number, number] {
  return [getMonthIndex(start), getMonthIndex(end)];
}

export default function MLInsightsPage() {
  const { data: apiModelInfo } = useModelInfo();
  const { data: apiPortDelays } = usePortDelays();
  const modelInfo = apiModelInfo || mockModelInfo;
  const portDelays = apiPortDelays || mockPortDelays;

  const shapData = modelInfo.feature_importance
    .filter((f: { feature: string; importance: number }) => !excludedFeatures.has(f.feature))
    .map((f: { feature: string; importance: number }) => ({
      name: featureLabels[f.feature] || f.feature,
      importance: f.importance,
    }));
  return (
    <div className="space-y-5 max-w-[1280px]">
      {/* Model metrics row */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'MAE', value: `${Number(modelInfo.metrics.mae).toFixed(4)} days`, sub: '~6.1 hours', icon: <Activity className="w-4 h-4" />, color: '#0FA67F' },
          { label: 'RMSE', value: `${Number(modelInfo.metrics.rmse).toFixed(4)} days`, sub: '~3 hours', icon: <Gauge className="w-4 h-4" />, color: '#1B6CA8' },
          { label: 'Within 1 Day', value: `${(modelInfo.metrics.within_1_day * 100).toFixed(2)}%`, sub: 'accuracy', icon: <Award className="w-4 h-4" />, color: '#0FA67F' },
          { label: 'Model', value: modelInfo.model_type, sub: `Trained ${modelInfo.training_date}`, icon: <Brain className="w-4 h-4" />, color: '#134074' },
        ].map((m, i) => (
          <motion.div key={m.label} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: i * 0.08 }}
            className="bg-white rounded-xl border border-[#DCE3ED] shadow-card p-4 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-[3px]" style={{ background: m.color }} />
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-text-secondary">{m.label}</span>
              <span style={{ color: m.color }}>{m.icon}</span>
            </div>
            <p className="text-xl font-bold text-navy-900">{m.value}</p>
            <p className="text-[10px] text-text-secondary mt-0.5">{m.sub}</p>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-5 gap-5">
        {/* SHAP chart - 3 cols */}
        <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          className="col-span-3 bg-white rounded-xl border border-[#DCE3ED] shadow-card p-5">
          <h3 className="text-sm font-semibold text-navy-900 mb-3">SHAP Feature Importance</h3>
          <ResponsiveContainer width="100%" height={340}>
            <BarChart data={shapData} layout="vertical" margin={{ top: 10, right: 20, bottom: 10, left: 30 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#DCE3ED" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 10, fill: '#6B7B8D' }} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: '#0B2545' }} width={170} interval={0} />
              <Tooltip formatter={(v: number) => v.toFixed(3)} />
              <Bar dataKey="importance" radius={[0, 4, 4, 0]} barSize={18}>
                {shapData.map((_: unknown, i: number) => (
                  <Cell key={i} fill={i === 0 ? '#0FA67F' : i === 1 ? '#1B6CA8' : '#48A9E6'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="text-[10px] text-text-secondary mt-2">
            7-day rolling port call mean dominates predictions (SHAP 0.894). Port capacity ratio is secondary.
          </p>
        </motion.div>

        {/* Port delay cards - 2 cols */}
        <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}
          className="col-span-2 bg-white rounded-xl border border-[#DCE3ED] shadow-card p-5 flex flex-col">
          <h3 className="text-sm font-semibold text-navy-900 mb-3">Predicted Port Delays</h3>
          <div className="flex-1 space-y-2.5 overflow-y-auto">
            {portDelays.sort((a, b) => b.predicted_delay_days - a.predicted_delay_days).map((pd) => {
              const pct = Math.min(pd.predicted_delay_days / 6, 1);
              return (
                <div key={pd.port} className="group">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-navy-900">{pd.port}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold font-mono" style={{ color: congestionColor(pd.congestion_level) }}>
                        {pd.predicted_delay_days.toFixed(1)}d
                      </span>
                      <span className="text-[9px] px-1.5 py-0.5 rounded-full font-semibold uppercase"
                        style={{
                          color: congestionColor(pd.congestion_level),
                          backgroundColor: `${congestionColor(pd.congestion_level)}15`,
                        }}>
                        {pd.congestion_level}
                      </span>
                    </div>
                  </div>
                  <div className="h-2 bg-cloud rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${pct * 100}%` }}
                      transition={{ duration: 0.8, delay: 0.3 }}
                      className="h-full rounded-full"
                      style={{ backgroundColor: congestionColor(pd.congestion_level) }}
                    />
                  </div>
                  <div className="flex justify-between text-[9px] text-text-secondary mt-0.5">
                    <span>CI: {pd.confidence_lower.toFixed(1)}d</span>
                    <span>{pd.confidence_upper.toFixed(1)}d</span>
                  </div>
                </div>
              );
            })}
          </div>
        </motion.div>
      </div>

      {/* Seasonal calendar */}
      <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
        className="bg-white rounded-xl border border-[#DCE3ED] shadow-card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Calendar className="w-4 h-4 text-ocean-500" />
          <h3 className="text-sm font-semibold text-navy-900">Seasonal Risk Calendar (2026)</h3>
        </div>
        {/* Month header */}
        <div className="grid grid-cols-[140px_repeat(12,1fr)] gap-0 mb-1">
          <div />
          {months.map(m => (
            <div key={m} className="text-[10px] text-text-secondary font-medium text-center">{m}</div>
          ))}
        </div>
        {/* Event rows */}
        <div className="space-y-1.5">
          {mockSeasonalEvents.map((evt) => {
            const [s, e] = getMonthSpan(evt.start, evt.end);
            return (
              <div key={evt.name} className="grid grid-cols-[140px_repeat(12,1fr)] gap-0 items-center">
                <div className="text-[11px] font-medium text-navy-900 pr-2 truncate" title={evt.name}>{evt.name}</div>
                {months.map((_, mi) => {
                  const inRange = s <= e ? (mi >= s && mi <= e) : (mi >= s || mi <= e);
                  return (
                    <div key={mi} className="h-7 flex items-center justify-center">
                      {inRange ? (
                        <div
                          className="w-full h-5 rounded-sm mx-px"
                          style={{ backgroundColor: `${impactColors[evt.impact]}22`, borderLeft: mi === s ? `3px solid ${impactColors[evt.impact]}` : 'none' }}
                          title={evt.description}
                        />
                      ) : (
                        <div className="w-full h-5 mx-px" />
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
        <div className="flex gap-4 mt-3 text-[10px] text-text-secondary">
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-coral-500/20 inline-block" /> High Impact</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-amber-500/20 inline-block" /> Medium</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-teal-500/20 inline-block" /> Low</span>
        </div>
      </motion.div>
    </div>
  );
}

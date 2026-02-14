import { useState } from 'react';
import { motion } from 'framer-motion';
import { Fuel, Clock, AlertTriangle, TrendingDown, ArrowRight, TrendingUp } from 'lucide-react';
import {
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine, Area, ComposedChart, Line,
} from 'recharts';
import Plot from 'react-plotly.js';
import {
  mockBunkerSensitivity, mockPortDelaySensitivity, mockTippingPoints,
  mockTippingPointsExtended, mockChinaDelaySensitivity, mockChinaTippingPoint,
  CHINA_PORTS,
} from '../../data/mockData';
import { useBunkerSensitivity, useDelaySensitivity, useChinaDelaySensitivity, useTippingPoints } from '../../api/hooks';
import { formatCurrency, formatCurrencyFull } from '../../utils/formatters';
import type { TippingPointExtended, AssignmentDetail } from '../../types';
import ExpandableTippingPointCard from './ExpandableTippingPointCard';

export default function ScenariosPage() {
  const { data: apiBunker, isLoading: bunkerLoading } = useBunkerSensitivity();
  const { data: apiChinaDelay, isLoading: chinaDelayLoading } = useChinaDelaySensitivity();
  const { data: apiTipping, isLoading: tippingLoading } = useTippingPoints();
  const bunkerSensitivity = apiBunker || mockBunkerSensitivity;
  const chinadelaySensitivity = apiChinaDelay || mockChinaDelaySensitivity;
  const tippingPoints = apiTipping || mockTippingPoints;

  const [bunkerMult, setBunkerMult] = useState(1.0);
  const [chinaDelayDays, setChinaDelayDays] = useState(0);

  // Show loading or error state if data is not available
  if (!bunkerSensitivity || bunkerSensitivity.length === 0 ||
      !chinadelaySensitivity || chinadelaySensitivity.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-ocean-500 mx-auto mb-4"></div>
          <p className="text-text-secondary">Loading scenario data...</p>
        </div>
      </div>
    );
  }

  // Interpolate values from sensitivity data
  const interpBunker = (mult: number) => {
    const d = bunkerSensitivity;
    const idx = d.findIndex(p => p.parameter_value >= mult);
    if (idx <= 0) return d[0];
    const prev = d[idx - 1], next = d[idx];
    const t = (mult - prev.parameter_value) / (next.parameter_value - prev.parameter_value);
    return {
      parameter_value: mult,
      total_profit: Math.round(prev.total_profit + t * (next.total_profit - prev.total_profit)),
      avg_tce: Math.round(prev.avg_tce + t * (next.avg_tce - prev.avg_tce)),
      assignments: t < 0.5 ? prev.assignments : next.assignments,
    };
  };

  const interpChinaDelay = (days: number) => {
    const d = chinadelaySensitivity;
    const idx = d.findIndex(p => p.parameter_value >= days);
    if (idx <= 0) return d[0];
    if (idx >= d.length) return d[d.length - 1];
    const prev = d[idx - 1], next = d[idx];
    const t = (days - prev.parameter_value) / (next.parameter_value - prev.parameter_value);
    return {
      parameter_value: days,
      total_profit: Math.round(prev.total_profit + t * (next.total_profit - prev.total_profit)),
      avg_tce: Math.round(prev.avg_tce + t * (next.avg_tce - prev.avg_tce)),
      assignments: t < 0.5 ? prev.assignments : next.assignments,
    };
  };

  const bCurrent = interpBunker(bunkerMult);
  const chinaCurrent = interpChinaDelay(chinaDelayDays);

  // 2D heatmap data: bunker x china delay -> profit
  const bunkerRange = [0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5];
  const chinaDelayRange = [0, 2, 4, 6, 8, 10, 12, 15];
  const baseProfit = bunkerSensitivity.find(p => p.parameter_value === 1.0)?.total_profit || bunkerSensitivity[0]?.total_profit || 5803558;
  const heatZ = bunkerRange.map(b => chinaDelayRange.map(d => {
    const bp = interpBunker(b);
    const dp = interpChinaDelay(d);
    const bRatio = bp.total_profit / baseProfit;
    const dRatio = dp.total_profit / baseProfit;
    return Math.round(baseProfit * bRatio * dRatio / baseProfit);
  }));

  // Get tipping points from API or fallback to mock
  const bunkerTippingPoint = apiTipping?.bunker || mockTippingPointsExtended.bunker;
  const chinaTippingPointRaw = apiTipping?.china_delay || mockChinaTippingPoint;

  // Map china_delay fields to match the component's expected interface
  const chinaTippingPoint = chinaTippingPointRaw ? {
    parameter: chinaTippingPointRaw.parameter || 'Port Delay (China)',
    value: chinaTippingPointRaw.value || 46,
    description: chinaTippingPointRaw.description || 'Tipping point for China port delays',
    profit_before: chinaTippingPointRaw.baseline_profit_no_delay || chinaTippingPointRaw.profit_before || 5803558,
    profit_after: chinaTippingPointRaw.baseline_profit_with_delay || chinaTippingPointRaw.profit_after || 2340945,
    portfolio_before: chinaTippingPointRaw.portfolio_baseline || chinaTippingPointRaw.portfolio_before,
    portfolio_after: chinaTippingPointRaw.portfolio_alternative || chinaTippingPointRaw.portfolio_after,
    ports_affected: chinaTippingPointRaw.ports_affected || [],
  } : mockChinaTippingPoint;

  return (
    <div className="space-y-5 max-w-[1280px]">
      {/* Split View: Bunker (Left) | China Delay (Right) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* LEFT COLUMN - BUNKER PRICE SENSITIVITY */}
        <div className="space-y-5">
          {/* Bunker Price Slider */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
            className="bg-white rounded-xl border border-[#DCE3ED] shadow-card p-5">
            <div className="flex items-center gap-2 mb-4">
              <Fuel className="w-4 h-4 text-ocean-500" />
              <h3 className="text-sm font-semibold text-navy-900">Bunker Price Sensitivity</h3>
            </div>
            <div className="flex items-center gap-4 mb-2">
              <input type="range" min={80} max={150} step={1} value={bunkerMult * 100}
                onChange={e => setBunkerMult(Number(e.target.value) / 100)}
                className="flex-1 h-2 rounded-lg appearance-none bg-sky-100 accent-ocean-500" />
              <span className="text-lg font-bold text-navy-900 w-16 text-right font-mono">{Math.round(bunkerMult * 100)}%</span>
            </div>
            <div className="flex justify-between text-[10px] text-text-secondary mb-4"><span>80%</span><span>100%</span><span>150%</span></div>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-cloud rounded-lg p-3">
                <p className="text-[10px] text-text-secondary uppercase tracking-wide">Profit</p>
                <p className={`text-lg font-bold font-mono ${bCurrent.total_profit < 1000000 ? 'text-coral-500' : 'text-teal-500'}`}>
                  {formatCurrency(bCurrent.total_profit)}
                </p>
              </div>
              <div className="bg-cloud rounded-lg p-3">
                <p className="text-[10px] text-text-secondary uppercase tracking-wide">Avg TCE</p>
                <p className="text-lg font-bold font-mono text-ocean-600">{formatCurrencyFull(bCurrent.avg_tce)}/d</p>
              </div>
            </div>
          </motion.div>

          {/* Bunker Price Chart */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
            className="bg-white rounded-xl border border-[#DCE3ED] shadow-card p-5">
            <h3 className="text-sm font-semibold text-navy-900 mb-3">Profit vs Bunker Price</h3>
            <ResponsiveContainer width="100%" height={240}>
              <ComposedChart data={bunkerSensitivity}>
                <CartesianGrid strokeDasharray="3 3" stroke="#DCE3ED" />
                <XAxis dataKey="parameter_value" tickFormatter={(v: number) => `${Math.round(v * 100)}%`} tick={{ fontSize: 10, fill: '#6B7B8D' }} />
                <YAxis tickFormatter={(v: number) => formatCurrency(v)} tick={{ fontSize: 10, fill: '#6B7B8D' }} />
                <Tooltip formatter={(v: number) => formatCurrencyFull(v)} labelFormatter={(l: number) => `${Math.round(l * 100)}% of base`} />
                <Area dataKey="total_profit" fill="#D6EAF8" stroke="none" fillOpacity={0.5} />
                <Line dataKey="total_profit" stroke="#1B6CA8" strokeWidth={2.5} dot={false} name="Profit" />
                <ReferenceLine x={1.18} stroke="#E74C5E" strokeDasharray="4 4" label={{ value: 'Tipping', position: 'top', fontSize: 9, fill: '#E74C5E' }} />
                <ReferenceLine x={bunkerMult} stroke="#0B2545" strokeWidth={2} />
              </ComposedChart>
            </ResponsiveContainer>
          </motion.div>

          {/* Bunker Tipping Point Card */}
          {bunkerTippingPoint && (
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
              <ExpandableTippingPointCard
                type="bunker"
                parameter={bunkerTippingPoint.parameter}
                value={bunkerTippingPoint.value}
                description={bunkerTippingPoint.description}
                profit_before={bunkerTippingPoint.profit_before}
                profit_after={bunkerTippingPoint.profit_after}
                portfolio_before={bunkerTippingPoint.portfolio_before}
                portfolio_after={bunkerTippingPoint.portfolio_after}
                ports_affected={bunkerTippingPoint.ports_affected}
              />
            </motion.div>
          )}
        </div>

        {/* RIGHT COLUMN - CHINA PORT DELAY SENSITIVITY */}
        <div className="space-y-5">
          {/* China Port Delay Slider */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="bg-white rounded-xl border border-[#DCE3ED] shadow-card p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-coral-500" />
                <h3 className="text-sm font-semibold text-navy-900">Port Delay Sensitivity (China)</h3>
              </div>
              <p className="text-xs text-[#6B7B8D]">
                Affects: {CHINA_PORTS.slice(0, 4).map(p => p.charAt(0) + p.slice(1).toLowerCase()).join(', ')}...
              </p>
            </div>
            <div className="flex items-center gap-4 mb-2">
              <input
                type="range"
                min={0}
                max={15}
                step={0.5}
                value={chinaDelayDays}
                onChange={e => setChinaDelayDays(Number(e.target.value))}
                className="flex-1 h-2 rounded-lg appearance-none accent-coral-500"
                style={{
                  background: `linear-gradient(to right, #FECACA 0%, #FECACA ${(chinaDelayDays / 15) * 100}%, #FEE2E2 ${(chinaDelayDays / 15) * 100}%, #FEE2E2 100%)`
                }}
              />
              <span className="text-lg font-bold text-navy-900 w-16 text-right font-mono">+{chinaDelayDays}d</span>
            </div>
            <div className="flex justify-between text-[10px] text-text-secondary mb-4">
              <span>0 days</span><span>7.5</span><span>15 days</span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-coral-50 rounded-lg p-3">
                <p className="text-[10px] text-text-secondary uppercase tracking-wide">Profit</p>
                <p className={`text-lg font-bold font-mono ${chinaCurrent.total_profit < 1500000 ? 'text-coral-500' : 'text-teal-500'}`}>
                  {formatCurrency(chinaCurrent.total_profit)}
                </p>
              </div>
              <div className="bg-coral-50 rounded-lg p-3">
                <p className="text-[10px] text-text-secondary uppercase tracking-wide">Avg TCE</p>
                <p className="text-lg font-bold font-mono text-ocean-600">{formatCurrencyFull(chinaCurrent.avg_tce)}/d</p>
              </div>
            </div>
          </motion.div>

          {/* China Delay Chart */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
            className="bg-white rounded-xl border border-[#DCE3ED] shadow-card p-5">
            <h3 className="text-sm font-semibold text-navy-900 mb-3">Profit vs China Port Delay</h3>
            <ResponsiveContainer width="100%" height={240}>
              <ComposedChart data={chinadelaySensitivity}>
                <CartesianGrid strokeDasharray="3 3" stroke="#DCE3ED" />
                <XAxis
                  dataKey="parameter_value"
                  tickFormatter={(v: number) => `+${v}d`}
                  tick={{ fontSize: 10, fill: '#6B7B8D' }}
                />
                <YAxis
                  tickFormatter={(v: number) => formatCurrency(v)}
                  tick={{ fontSize: 10, fill: '#6B7B8D' }}
                />
                <Tooltip
                  formatter={(v: number) => formatCurrencyFull(v)}
                  labelFormatter={(l: number) => `+${l} days delay (China)`}
                />
                <Area dataKey="total_profit" fill="#FECACA" stroke="none" fillOpacity={0.4} />
                <Line dataKey="total_profit" stroke="#E57373" strokeWidth={2.5} dot={false} name="Profit" />
                {chinaTippingPoint && (
                  <ReferenceLine
                    x={chinaTippingPoint.value}
                    stroke="#E74C5E"
                    strokeDasharray="4 4"
                    label={{ value: 'Tipping', position: 'top', fontSize: 9, fill: '#E74C5E' }}
                  />
                )}
                <ReferenceLine x={chinaDelayDays} stroke="#0B2545" strokeWidth={2} />
              </ComposedChart>
            </ResponsiveContainer>
          </motion.div>

          {/* China Tipping Point Card */}
          {chinaTippingPoint && (
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
              <ExpandableTippingPointCard
                type="delay"
                parameter={chinaTippingPoint.parameter}
                value={chinaTippingPoint.value}
                description={chinaTippingPoint.description}
                profit_before={chinaTippingPoint.profit_before}
                profit_after={chinaTippingPoint.profit_after}
                portfolio_before={chinaTippingPoint.portfolio_before}
                portfolio_after={chinaTippingPoint.portfolio_after}
                ports_affected={chinaTippingPoint.ports_affected}
              />
            </motion.div>
          )}
        </div>
      </div>

      {/* 2D scenario heatmap */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}
        className="bg-white rounded-xl border border-[#DCE3ED] shadow-card p-5">
        <h3 className="text-sm font-semibold text-navy-900 mb-3">2D Scenario Heatmap: Bunker Price x China Port Delay</h3>
        <Plot
          data={[{
            z: heatZ,
            x: chinaDelayRange.map(d => `+${d}d`),
            y: bunkerRange.map(b => `${Math.round(b * 100)}%`),
            type: 'heatmap',
            colorscale: [[0, '#E74C5E'], [0.3, '#F5A623'], [0.6, '#48A9E6'], [1, '#0FA67F']],
            hovertemplate: 'Bunker: %{y}<br>China Delay: %{x}<br>Profit: $%{z:,.0f}<extra></extra>',
            showscale: true,
            colorbar: {
              title: { text: 'Profit ($)', font: { size: 10, color: '#6B7B8D' } },
              thickness: 12,
              tickformat: '$,.0f',
              tickfont: { size: 9, color: '#6B7B8D' },
              outlinewidth: 0,
            },
          }]}
          layout={{
            height: 300,
            margin: { l: 60, r: 30, t: 10, b: 40 },
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            font: { family: 'Inter, system-ui, sans-serif', size: 11, color: '#0B2545' },
            xaxis: { title: { text: 'China Port Delay', font: { size: 10, color: '#6B7B8D' } }, tickfont: { size: 9, color: '#6B7B8D' } },
            yaxis: { title: { text: 'Bunker Price', font: { size: 10, color: '#6B7B8D' } }, tickfont: { size: 9, color: '#6B7B8D' } },
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: '100%' }}
        />
      </motion.div>
    </div>
  );
}

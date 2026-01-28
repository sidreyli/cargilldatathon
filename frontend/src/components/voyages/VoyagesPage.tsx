import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowUpDown, ArrowUp, ArrowDown, GitCompareArrows, X, Loader2 } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
} from 'recharts';
import { mockAllVoyages, mockPortfolio } from '../../data/mockData';
import { useAllVoyages, usePortfolio } from '../../api/hooks';
import { formatCurrencyFull, formatCurrency } from '../../utils/formatters';

type SortKey = 'vessel' | 'cargo' | 'tce' | 'net_profit' | 'total_days' | 'can_make_laycan';
type SortDir = 'asc' | 'desc';

export default function VoyagesPage() {
  const { data: apiVoyages, isLoading: loadingVoyages, isFetching } = useAllVoyages();
  const { data: apiPortfolio } = usePortfolio();
  const allVoyages = apiVoyages && apiVoyages.length > 0 ? apiVoyages : mockAllVoyages;
  const portfolio = apiPortfolio || mockPortfolio;
  const optSet = new Set(portfolio.assignments?.map((a: any) => `${a.vessel}|${a.cargo}`) || []);
  const [sortKey, setSortKey] = useState<SortKey>('tce');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [selected, setSelected] = useState<string[]>([]);

  const toggle = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('desc'); }
  };

  const sorted = useMemo(() => {
    const arr = [...allVoyages];
    arr.sort((a, b) => {
      let va: number | string = a[sortKey] as number | string;
      let vb: number | string = b[sortKey] as number | string;
      if (typeof va === 'boolean') { va = va ? 1 : 0; vb = (vb as unknown as boolean) ? 1 : 0; }
      if (typeof va === 'string') return sortDir === 'asc' ? (va as string).localeCompare(vb as string) : (vb as string).localeCompare(va as string);
      return sortDir === 'asc' ? (va as number) - (vb as number) : (vb as number) - (va as number);
    });
    return arr;
  }, [allVoyages, sortKey, sortDir]);

  const selVoyages = allVoyages.filter(v => selected.includes(`${v.vessel}|${v.cargo}`));

  const SortIcon = ({ k }: { k: SortKey }) => {
    if (sortKey !== k) return <ArrowUpDown className="w-3 h-3 opacity-30" />;
    return sortDir === 'asc' ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />;
  };

  const radarData = selVoyages.length === 2 ? [
    { metric: 'TCE', A: selVoyages[0].tce / 400, B: selVoyages[1].tce / 400 },
    { metric: 'Profit', A: selVoyages[0].net_profit / 25000, B: selVoyages[1].net_profit / 25000 },
    { metric: 'Speed', A: (100 - selVoyages[0].total_days), B: (100 - selVoyages[1].total_days) },
    { metric: 'Fuel Eff.', A: (2200 - selVoyages[0].vlsfo_consumed) / 10, B: (2200 - selVoyages[1].vlsfo_consumed) / 10 },
    { metric: 'Margin', A: Math.max(0, selVoyages[0].days_margin * 10), B: Math.max(0, selVoyages[1].days_margin * 10) },
  ] : [];

  const waterfallData = selVoyages.map(v => ({
    name: `${v.vessel.split(' ')[0]}→${v.cargo.split(' ')[0]}`,
    Bunker: v.total_bunker_cost,
    Hire: v.hire_cost,
    'Port Costs': v.port_costs,
    Misc: v.misc_costs,
    Commission: v.commission_cost,
  }));

  if (loadingVoyages) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-ocean-500" />
        <span className="ml-3 text-text-secondary">Loading voyages...</span>
      </div>
    );
  }

  return (
    <div className="space-y-5 max-w-[1280px]">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <div className="bg-white rounded-xl border border-[#DCE3ED] shadow-card overflow-hidden">
          <div className="px-5 py-3 border-b border-border flex items-center justify-between">
            <h3 className="text-sm font-semibold text-navy-900">All Voyage Combinations ({allVoyages.length} total)</h3>
            {selected.length > 0 && (
              <button onClick={() => setSelected([])} className="text-xs text-text-secondary hover:text-coral-500 flex items-center gap-1">
                <X className="w-3 h-3" /> Clear selection
              </button>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-cloud text-[11px] uppercase tracking-wide text-text-secondary">
                  <th className="px-4 py-2.5 text-left w-8" />
                  {([['vessel','Vessel'],['cargo','Cargo'],['tce','TCE'],['net_profit','Profit'],['total_days','Days'],['can_make_laycan','Feasible']] as [SortKey,string][]).map(([k,label]) => (
                    <th key={k} className="px-3 py-2.5 text-left cursor-pointer hover:text-navy-700 transition-colors" onClick={() => toggle(k)}>
                      <span className="flex items-center gap-1">{label} <SortIcon k={k} /></span>
                    </th>
                  ))}
                  <th className="px-3 py-2.5 text-left">Bunker Port</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((v, i) => {
                  const key = `${v.vessel}|${v.cargo}`;
                  const isOpt = optSet.has(key);
                  const isSel = selected.includes(key);
                  const isMarketVessel = v.vessel_type === 'market';
                  const isMarketCargo = v.cargo_type === 'market';
                  return (
                    <tr
                      key={i}
                      className={`border-b border-border/50 transition-colors cursor-pointer ${isSel ? 'bg-sky-100/40' : isOpt ? 'bg-teal-500/[0.04]' : isMarketVessel ? 'bg-amber-50/40' : 'hover:bg-cloud/60'}`}
                      onClick={() => {
                        setSelected(s => {
                          if (s.includes(key)) return s.filter(x => x !== key);
                          if (s.length >= 2) return [s[1], key];
                          return [...s, key];
                        });
                      }}
                    >
                      <td className="px-4 py-2.5">
                        <div className={`w-4 h-4 rounded border-2 flex items-center justify-center ${isSel ? 'bg-ocean-500 border-ocean-500' : 'border-border'}`}>
                          {isSel && <div className="w-1.5 h-1.5 bg-white rounded-sm" />}
                        </div>
                      </td>
                      <td className="px-3 py-2.5 font-medium text-navy-900">
                        <span className="flex items-center gap-1.5">
                          {v.vessel}
                          {isOpt && <span className="text-[10px] text-teal-500 font-semibold bg-teal-500/10 px-1.5 py-0.5 rounded">OPT</span>}
                          {isMarketVessel && <span className="text-[10px] text-amber-600 font-semibold bg-amber-100 px-1.5 py-0.5 rounded">MKT</span>}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-text-secondary">
                        <span className="flex items-center gap-1.5">
                          {v.cargo}
                          {isMarketCargo && <span className="text-[10px] text-blue-600 font-semibold bg-blue-100 px-1.5 py-0.5 rounded">MKT</span>}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 font-mono font-semibold" style={{ color: v.tce >= 25000 ? '#0FA67F' : v.tce >= 18000 ? '#1B6CA8' : '#F5A623' }}>
                        {formatCurrencyFull(v.tce)}
                      </td>
                      <td className={`px-3 py-2.5 font-mono ${v.net_profit > 0 ? 'text-teal-500' : 'text-coral-500'}`}>
                        {formatCurrency(v.net_profit)}
                      </td>
                      <td className="px-3 py-2.5 text-text-secondary">{v.total_days.toFixed(1)}d</td>
                      <td className="px-3 py-2.5">
                        {v.can_make_laycan
                          ? <span className="text-[11px] font-semibold text-teal-500 bg-teal-500/10 px-2 py-0.5 rounded-full">+{v.days_margin}d</span>
                          : <span className="text-[11px] font-semibold text-coral-500 bg-coral-500/10 px-2 py-0.5 rounded-full">{v.days_margin}d</span>}
                      </td>
                      <td className="px-3 py-2.5 text-text-secondary text-xs">{v.bunker_port || '—'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </motion.div>

      {/* Comparison panel */}
      <AnimatePresence>
        {selVoyages.length === 2 && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 16 }}
            className="grid grid-cols-2 gap-5"
          >
            {/* Radar */}
            <div className="bg-white rounded-xl border border-[#DCE3ED] shadow-card p-5">
              <div className="flex items-center gap-2 mb-3">
                <GitCompareArrows className="w-4 h-4 text-ocean-500" />
                <h3 className="text-sm font-semibold text-navy-900">Performance Comparison</h3>
              </div>
              <ResponsiveContainer width="100%" height={260}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#DCE3ED" />
                  <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11, fill: '#6B7B8D' }} />
                  <PolarRadiusAxis tick={false} axisLine={false} />
                  <Radar name={selVoyages[0].vessel} dataKey="A" stroke="#1B6CA8" fill="#1B6CA8" fillOpacity={0.15} strokeWidth={2} />
                  <Radar name={selVoyages[1].vessel} dataKey="B" stroke="#0FA67F" fill="#0FA67F" fillOpacity={0.15} strokeWidth={2} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>

            {/* Cost waterfall */}
            <div className="bg-white rounded-xl border border-[#DCE3ED] shadow-card p-5">
              <h3 className="text-sm font-semibold text-navy-900 mb-3">Cost Breakdown</h3>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={waterfallData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#DCE3ED" />
                  <XAxis type="number" tickFormatter={(v: number) => formatCurrency(v)} tick={{ fontSize: 10, fill: '#6B7B8D' }} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: '#0B2545' }} width={90} />
                  <Tooltip formatter={(v: number) => formatCurrencyFull(v)} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="Bunker" stackId="a" fill="#134074" radius={[0, 0, 0, 0]} />
                  <Bar dataKey="Hire" stackId="a" fill="#1B6CA8" />
                  <Bar dataKey="Port Costs" stackId="a" fill="#48A9E6" />
                  <Bar dataKey="Commission" stackId="a" fill="#F5A623" />
                  <Bar dataKey="Misc" stackId="a" fill="#6B7B8D" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {selected.length === 1 && (
        <p className="text-xs text-text-secondary text-center">Select one more voyage to compare side-by-side</p>
      )}
    </div>
  );
}

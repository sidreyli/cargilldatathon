import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import {
  TrendingUp,
  DollarSign,
  Ship,
  Package,
  Lightbulb,
  Loader2,
  Anchor,
  ArrowRight,
} from 'lucide-react';
import { usePortfolio, useVessels, useCargoes } from '../../api/hooks';
import {
  mockPortfolio,
  mockPortfolios,
  mockCargoes,
  mockVessels,
} from '../../data/mockData';
import { formatCurrency, formatCurrencyFull } from '../../utils/formatters';

/* ── animated counter hook ─────────────────────────────────── */
function useCounter(end: number, duration = 1400, delay = 0) {
  const [value, setValue] = useState(0);
  const raf = useRef<number>();

  useEffect(() => {
    let start: number | null = null;
    const timeout = setTimeout(() => {
      const step = (ts: number) => {
        if (!start) start = ts;
        const progress = Math.min((ts - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        setValue(Math.round(eased * end));
        if (progress < 1) raf.current = requestAnimationFrame(step);
      };
      raf.current = requestAnimationFrame(step);
    }, delay);

    return () => {
      clearTimeout(timeout);
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, [end, duration, delay]);

  return value;
}

/* ── KPI card ──────────────────────────────────────────────── */
interface KPIProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  accent: string;
  idx: number;
}

function KPICard({ icon, label, value, sub, accent, idx }: KPIProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: idx * 0.1, ease: [0.22, 1, 0.36, 1] }}
      className="bg-white rounded-xl border border-[#DCE3ED] shadow-[0_1px_3px_rgba(11,37,69,0.08)] p-5 flex flex-col gap-3 relative overflow-hidden group hover:shadow-[0_4px_12px_rgba(11,37,69,0.12)] transition-shadow"
    >
      <div className="absolute top-0 left-0 right-0 h-[3px]" style={{ background: accent }} />
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold tracking-wide uppercase text-[#6B7B8D]">{label}</span>
        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: `${accent}14` }}>
          <span style={{ color: accent }}>{icon}</span>
        </div>
      </div>
      <div>
        <span className="text-[28px] font-bold tracking-tight leading-none" style={{ color: '#0B2545' }}>{value}</span>
        {sub && <span className="ml-1.5 text-sm font-medium text-[#6B7B8D]">{sub}</span>}
      </div>
    </motion.div>
  );
}

/* ── Assignment Card ──────────────────────────────────────── */
interface AssignmentCardProps {
  vessel: string;
  cargo: string;
  vesselType: 'cargill' | 'market';
  cargoType: 'cargill' | 'market';
  profit?: number;
  tce?: number;
  days?: number;
  hireRate?: number;
  idx: number;
}

function AssignmentCard({ vessel, cargo, vesselType, cargoType, profit, tce, days, hireRate, idx }: AssignmentCardProps) {
  const isCargillVessel = vesselType === 'cargill';
  const isMarketCargo = cargoType === 'market';
  
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: idx * 0.08 }}
      className="bg-white rounded-xl border border-[#DCE3ED] shadow-[0_1px_3px_rgba(11,37,69,0.08)] p-4 hover:shadow-[0_4px_12px_rgba(11,37,69,0.12)] transition-shadow"
    >
      <div className="flex items-center gap-3">
        {/* Vessel */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <div className={`w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0 ${isCargillVessel ? 'bg-[#134074]/10' : 'bg-[#F5A623]/10'}`}>
              {isCargillVessel ? (
                <Ship className="w-3.5 h-3.5 text-[#134074]" />
              ) : (
                <Anchor className="w-3.5 h-3.5 text-[#F5A623]" />
              )}
            </div>
            <span className={`text-[10px] font-semibold uppercase tracking-wide ${isCargillVessel ? 'text-[#134074]' : 'text-[#F5A623]'}`}>
              {isCargillVessel ? 'Cargill Fleet' : 'Market Hire'}
            </span>
          </div>
          <p className="text-sm font-bold text-[#0B2545] truncate">{vessel}</p>
        </div>

        {/* Arrow */}
        <div className="flex-shrink-0">
          <ArrowRight className="w-5 h-5 text-[#0FA67F]" />
        </div>

        {/* Cargo */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <div className={`w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0 ${isMarketCargo ? 'bg-[#1B6CA8]/10' : 'bg-[#0FA67F]/10'}`}>
              <Package className={`w-3.5 h-3.5 ${isMarketCargo ? 'text-[#1B6CA8]' : 'text-[#0FA67F]'}`} />
            </div>
            <span className={`text-[10px] font-semibold uppercase tracking-wide ${isMarketCargo ? 'text-[#1B6CA8]' : 'text-[#0FA67F]'}`}>
              {isMarketCargo ? 'Market Cargo' : 'Cargill Cargo'}
            </span>
          </div>
          <p className="text-sm font-bold text-[#0B2545] truncate" title={cargo}>{cargo.split('(')[0].trim()}</p>
          <p className="text-[10px] text-[#6B7B8D] truncate">{cargo.includes('(') ? cargo.match(/\(([^)]+)\)/)?.[1] : ''}</p>
        </div>

        {/* Metrics */}
        {profit !== undefined && (
          <div className="flex-shrink-0 text-right pl-3 border-l border-[#DCE3ED]">
            <p className="text-xs text-[#6B7B8D]">Profit</p>
            <p className="text-sm font-bold text-[#0FA67F]">{formatCurrency(profit)}</p>
            {tce !== undefined && (
              <p className="text-[10px] text-[#6B7B8D]">${tce.toLocaleString()}/day</p>
            )}
          </div>
        )}
        {days !== undefined && profit === undefined && (
          <div className="flex-shrink-0 text-right pl-3 border-l border-[#DCE3ED]">
            <p className="text-xs text-[#6B7B8D]">Duration</p>
            <p className="text-sm font-bold text-[#1B6CA8]">{Math.round(days)} days</p>
            {hireRate !== undefined && hireRate > 100 && (
              <p className="text-[10px] text-[#6B7B8D]">${hireRate.toLocaleString()}/day</p>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}

interface DashboardPageProps {
  useMLDelays?: boolean;
}

export default function DashboardPage({ useMLDelays = false }: DashboardPageProps) {
  // Portfolio rank selection (0 = best, 1 = second best, 2 = third best)
  const [selectedRank, setSelectedRank] = useState(0);

  // Reset selectedRank when ML mode changes
  useEffect(() => {
    setSelectedRank(0);
  }, [useMLDelays]);

  // Fetch from API
  const { data: apiPortfolios, isLoading: loadingPortfolio } = usePortfolio(useMLDelays);
  const { data: apiVessels } = useVessels();
  const { data: apiCargoes } = useCargoes();

  // Use API data if available, otherwise fall back to mock
  const portfolios = apiPortfolios || mockPortfolios;
  const portfolio = portfolios[selectedRank] || portfolios[0] || mockPortfolio;
  const vessels = apiVessels || mockVessels;
  const cargoes = apiCargoes || mockCargoes;

  // Separate assignments by type
  const cargillVesselAssignments = portfolio.assignments?.filter((a: any) =>
    a.vessel_type === 'cargill' || a.voyage?.vessel_type === 'cargill'
  ) || portfolio.assignments || [];

  const marketVesselHires = portfolio.market_vessel_hires || [];

  const profit = useCounter(portfolio.total_profit || 0, 1400, 100);
  const tce = useCounter(portfolio.avg_tce || 0, 1400, 200);
  const cargillAssignments = useCounter(cargillVesselAssignments.length, 800, 300);
  const marketHires = useCounter(marketVesselHires.length, 800, 400);

  if (loadingPortfolio) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-ocean-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-[1400px]">
      {/* Portfolio Selection Toggle */}
      {portfolios.length > 1 && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-xl border border-[#DCE3ED] shadow-[0_1px_3px_rgba(11,37,69,0.08)] p-3"
        >
          <div className="flex flex-col md:flex-row md:items-center gap-2 md:gap-4">
            <span className="text-xs font-semibold uppercase tracking-wide text-[#6B7B8D] whitespace-nowrap">
              Portfolio Options
            </span>
            <div className="flex flex-wrap gap-1 bg-[#F1F5F9] rounded-lg p-1 flex-1">
              {portfolios.map((p: any, i: number) => (
                <button
                  key={i}
                  onClick={() => setSelectedRank(i)}
                  className={`flex-1 px-4 py-2 rounded-md text-sm font-medium transition-all flex items-center justify-center gap-2 ${
                    selectedRank === i
                      ? 'bg-white shadow-sm text-[#134074] border border-[#1B6CA8]/20'
                      : 'text-[#6B7B8D] hover:text-[#0B2545] hover:bg-white/50'
                  }`}
                >
                  <span className={`text-xs font-bold ${selectedRank === i ? 'text-[#1B6CA8]' : 'opacity-60'}`}>
                    #{i + 1}
                  </span>
                  <span className={`font-semibold ${selectedRank === i ? 'text-[#0FA67F]' : ''}`}>
                    ${((p.total_profit || 0) / 1e6).toFixed(2)}M
                  </span>
                  {i === 0 && (
                    <span className="text-[9px] font-bold uppercase bg-[#0FA67F]/10 text-[#0FA67F] px-1.5 py-0.5 rounded">
                      Best
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        </motion.div>
      )}

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
        <KPICard idx={0} icon={<TrendingUp className="w-4 h-4" />} label="Total Portfolio Profit" value={formatCurrency(profit)} accent="#0FA67F" />
        <KPICard idx={1} icon={<DollarSign className="w-4 h-4" />} label="Avg TCE" value={formatCurrencyFull(tce)} sub="/day" accent="#1B6CA8" />
        <KPICard idx={2} icon={<Ship className="w-4 h-4" />} label="Cargill Fleet Deployed" value={`${cargillAssignments}`} sub="vessels" accent="#134074" />
        <KPICard idx={3} icon={<Anchor className="w-4 h-4" />} label="Market Vessels Hired" value={`${marketHires}`} sub="vessels" accent="#F5A623" />
      </div>

      {/* Strategy Overview */}
      <motion.div 
        initial={{ opacity: 0, y: 16 }} 
        animate={{ opacity: 1, y: 0 }} 
        transition={{ duration: 0.5, delay: 0.2 }}
        className="bg-gradient-to-r from-[#134074] to-[#1B6CA8] rounded-xl p-6 text-white shadow-lg"
      >
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-white/10 flex items-center justify-center flex-shrink-0">
            <Lightbulb className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-bold mb-2">Optimal Portfolio Strategy</h3>
            <p className="text-sm opacity-90 leading-relaxed">
              <strong>Key Insight:</strong> All {cargillVesselAssignments.length} Cargill vessels are assigned to higher-profit{' '}
              <span className="text-[#48A9E6] font-semibold">market cargoes</span>, 
              generating {formatCurrency(portfolio.total_profit || 0)} in total profit. 
              {marketVesselHires.length > 0 && (
                <>
                  {' '}The {marketVesselHires.length} committed Cargill cargoes are fulfilled by hiring{' '}
                  <span className="text-[#F5A623] font-semibold">market vessels</span> at competitive rates,
                  ensuring all contractual obligations are met while maximizing returns.
                </>
              )}
            </p>
          </div>
        </div>
      </motion.div>

      {/* Two Column Layout: Cargill Fleet + Market Hires */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
        {/* Cargill Fleet Assignments */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }} 
          animate={{ opacity: 1, y: 0 }} 
          transition={{ duration: 0.5, delay: 0.3 }}
          className="bg-white rounded-xl border border-[#DCE3ED] shadow-[0_1px_3px_rgba(11,37,69,0.08)] overflow-hidden"
        >
          <div className="px-5 py-4 border-b border-[#DCE3ED] bg-gradient-to-r from-[#134074]/5 to-transparent">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-[#134074]/10 flex items-center justify-center">
                <Ship className="w-5 h-5 text-[#134074]" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-[#0B2545]">Cargill Fleet Assignments</h3>
                <p className="text-xs text-[#6B7B8D]">Our vessels deployed to market cargo opportunities</p>
              </div>
            </div>
          </div>
          <div className="p-4 space-y-3 max-h-[400px] overflow-y-auto">
            {cargillVesselAssignments.length > 0 ? (
              cargillVesselAssignments.map((a: any, i: number) => (
                <AssignmentCard
                  key={i}
                  vessel={a.vessel}
                  cargo={a.cargo}
                  vesselType="cargill"
                  cargoType={a.cargo_type || a.voyage?.cargo_type || 'market'}
                  profit={a.net_profit || a.voyage?.net_profit}
                  tce={a.tce || a.voyage?.tce}
                  days={a.total_days || a.voyage?.total_days}
                  idx={i}
                />
              ))
            ) : (
              <p className="text-sm text-[#6B7B8D] text-center py-4">No assignments</p>
            )}
          </div>
          <div className="px-5 py-3 border-t border-[#DCE3ED] bg-[#F8FAFC]">
            <div className="flex justify-between items-center">
              <span className="text-xs text-[#6B7B8D]">Total Cargill Fleet Profit</span>
              <span className="text-sm font-bold text-[#0FA67F]">
                {formatCurrency(cargillVesselAssignments.reduce((sum: number, a: any) => 
                  sum + (a.net_profit || a.voyage?.net_profit || 0), 0
                ))}
              </span>
            </div>
          </div>
        </motion.div>

        {/* Market Vessel Hires */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }} 
          animate={{ opacity: 1, y: 0 }} 
          transition={{ duration: 0.5, delay: 0.4 }}
          className="bg-white rounded-xl border border-[#DCE3ED] shadow-[0_1px_3px_rgba(11,37,69,0.08)] overflow-hidden"
        >
          <div className="px-5 py-4 border-b border-[#DCE3ED] bg-gradient-to-r from-[#F5A623]/5 to-transparent">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-[#F5A623]/10 flex items-center justify-center">
                <Anchor className="w-5 h-5 text-[#F5A623]" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-[#0B2545]">Market Vessel Hires</h3>
                <p className="text-xs text-[#6B7B8D]">Hired vessels to fulfill Cargill cargo commitments</p>
              </div>
            </div>
          </div>
          <div className="p-4 space-y-3 max-h-[400px] overflow-y-auto">
            {marketVesselHires.length > 0 ? (
              marketVesselHires.map((h: any, i: number) => (
                <AssignmentCard
                  key={i}
                  vessel={h.vessel}
                  cargo={h.cargo}
                  vesselType="market"
                  cargoType="cargill"
                  profit={h.net_profit}
                  tce={h.tce}
                  days={h.duration_days}
                  hireRate={h.recommended_hire_rate}
                  idx={i}
                />
              ))
            ) : (
              <p className="text-sm text-[#6B7B8D] text-center py-4">No market hires needed</p>
            )}
          </div>
          <div className="px-5 py-3 border-t border-[#DCE3ED] bg-[#F8FAFC]">
            <div className="flex justify-between items-center">
              <span className="text-xs text-[#6B7B8D]">Cargill Cargoes Covered by Market</span>
              <span className="text-sm font-bold text-[#0FA67F]">
                {marketVesselHires.length} / {cargoes.length} cargoes
              </span>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Summary Table */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }} 
        animate={{ opacity: 1, y: 0 }} 
        transition={{ duration: 0.5, delay: 0.5 }}
        className="bg-white rounded-xl border border-[#DCE3ED] shadow-[0_1px_3px_rgba(11,37,69,0.08)] overflow-hidden"
      >
        <div className="px-5 py-4 border-b border-[#DCE3ED]">
          <h3 className="text-sm font-bold text-[#0B2545]">Complete Assignment Matrix</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs md:text-sm">
            <thead className="bg-[#F8FAFC]">
              <tr className="border-b border-[#DCE3ED]">
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7B8D] uppercase tracking-wide">Vessel</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7B8D] uppercase tracking-wide">Type</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7B8D] uppercase tracking-wide">Cargo</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7B8D] uppercase tracking-wide">Route</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-[#6B7B8D] uppercase tracking-wide">Duration</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-[#6B7B8D] uppercase tracking-wide">TCE</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-[#6B7B8D] uppercase tracking-wide">Profit</th>
              </tr>
            </thead>
            <tbody>
              {cargillVesselAssignments.map((a: any, i: number) => {
                const cargoName = a.cargo?.split('(')[0]?.trim() || a.cargo;
                const route = a.cargo?.includes('(') ? a.cargo.match(/\(([^)]+)\)/)?.[1] : '';
                const voyageData = a.voyage || a;
                return (
                  <tr key={`cargill-${i}`} className="border-b border-[#DCE3ED] hover:bg-[#F8FAFC]">
                    <td className="px-4 py-3 font-medium text-[#0B2545]">{a.vessel}</td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#134074]/10 text-[#134074]">
                        <Ship className="w-3 h-3" /> Cargill
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[#0B2545]">{cargoName}</td>
                    <td className="px-4 py-3 text-[#6B7B8D]">{route}</td>
                    <td className="px-4 py-3 text-right text-[#0B2545]">{Math.round(voyageData.total_days || 0)}d</td>
                    <td className="px-4 py-3 text-right text-[#1B6CA8] font-medium">${(voyageData.tce || 0).toLocaleString()}</td>
                    <td className="px-4 py-3 text-right text-[#0FA67F] font-bold">{formatCurrency(voyageData.net_profit || 0)}</td>
                  </tr>
                );
              })}
              {marketVesselHires.map((h: any, i: number) => {
                const cargoName = h.cargo?.split('(')[0]?.trim() || h.cargo;
                const route = h.cargo?.includes('(') ? h.cargo.match(/\(([^)]+)\)/)?.[1] : '';
                return (
                  <tr key={`market-${i}`} className="border-b border-[#DCE3ED] hover:bg-[#FEF9E7]/50 bg-[#FEF9E7]/20">
                    <td className="px-4 py-3 font-medium text-[#0B2545]">{h.vessel}</td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#F5A623]/10 text-[#F5A623]">
                        <Anchor className="w-3 h-3" /> Hired
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[#0B2545]">{cargoName}</td>
                    <td className="px-4 py-3 text-[#6B7B8D]">{route}</td>
                    <td className="px-4 py-3 text-right text-[#0B2545]">{Math.round(h.duration_days || 0)}d</td>
                    <td className="px-4 py-3 text-right text-[#1B6CA8] font-medium">
                      {h.tce ? `$${h.tce.toLocaleString()}` : (h.recommended_hire_rate > 100 ? `$${h.recommended_hire_rate.toLocaleString()}` : '—')}
                    </td>
                    <td className="px-4 py-3 text-right text-[#0FA67F] font-bold">
                      {h.net_profit ? formatCurrency(h.net_profit) : '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot className="bg-[#F8FAFC]">
              <tr>
                <td colSpan={5} className="px-4 py-3 text-right text-xs font-semibold text-[#6B7B8D] uppercase">Total Portfolio</td>
                <td className="px-4 py-3 text-right text-[#1B6CA8] font-bold">${(portfolio.avg_tce || 0).toLocaleString()}/d</td>
                <td className="px-4 py-3 text-right text-[#0FA67F] font-bold text-base">{formatCurrency(portfolio.total_profit || 0)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </motion.div>
    </div>
  );
}

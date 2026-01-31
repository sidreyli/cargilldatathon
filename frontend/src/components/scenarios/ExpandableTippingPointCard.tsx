import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Fuel, Clock, Ship, Anchor, TrendingDown, TrendingUp, AlertTriangle } from 'lucide-react';
import { formatCurrency, formatCurrencyFull } from '../../utils/formatters';

interface VesselAssignment {
  vessel: string;
  cargo: string;
  vessel_type: 'cargill' | 'market';
  cargo_type: 'cargill' | 'market';
  tce: number;
  profit: number;
  hire_rate?: number;
}

interface PortfolioDetails {
  cargill_assignments: VesselAssignment[];
  market_hires: VesselAssignment[];
  unassigned_vessels: string[];
  unassigned_cargoes: string[];
  total_profit: number;
  total_tce: number;
  avg_tce: number;
}

interface ExpandableTippingPointCardProps {
  type: 'bunker' | 'delay';
  parameter: string;
  value: number;
  description: string;
  profit_before: number;
  profit_after: number;
  portfolio_before?: PortfolioDetails;
  portfolio_after?: PortfolioDetails;
  ports_affected?: string[];
}

export default function ExpandableTippingPointCard({
  type,
  parameter,
  value,
  description,
  profit_before,
  profit_after,
  portfolio_before,
  portfolio_after,
  ports_affected,
}: ExpandableTippingPointCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Theme configuration
  const theme = type === 'bunker' ? {
    primary: '#1B6CA8',
    secondary: '#134074',
    light: '#D6EAF8',
    accent: '#48A9E6',
    glow: 'rgba(27, 108, 168, 0.15)',
    icon: Fuel,
  } : {
    primary: '#E57373',
    secondary: '#C62828',
    light: '#FECACA',
    accent: '#EF5350',
    glow: 'rgba(229, 115, 115, 0.15)',
    icon: Clock,
  };

  const Icon = theme.icon;
  const valueDisplay = type === 'bunker' ? `${Math.round(value * 100)}%` : `+${value}d`;
  const profitDelta = profit_after - profit_before;
  const profitDeltaPct = ((profitDelta / profit_before) * 100).toFixed(1);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative group"
      style={{
        transformStyle: 'preserve-3d',
      }}
    >
      {/* Ambient glow effect */}
      <div
        className="absolute -inset-2 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-xl"
        style={{ background: `radial-gradient(circle at 50% 50%, ${theme.glow}, transparent 70%)` }}
      />

      {/* Main card */}
      <motion.div
        layout
        className="relative bg-white rounded-xl overflow-hidden border-2 transition-all duration-300"
        style={{
          borderColor: isExpanded ? theme.primary : '#DCE3ED',
          boxShadow: isExpanded
            ? `0 20px 60px -15px ${theme.glow}, 0 0 0 1px ${theme.primary}20`
            : '0 4px 12px rgba(0, 0, 0, 0.08)',
        }}
      >
        {/* Top accent bar with animated shimmer */}
        <div className="absolute top-0 left-0 right-0 h-1 overflow-hidden">
          <motion.div
            className="h-full w-full"
            style={{
              background: `linear-gradient(90deg, ${theme.secondary}, ${theme.primary}, ${theme.accent}, ${theme.primary}, ${theme.secondary})`,
              backgroundSize: '200% 100%',
            }}
            animate={{
              backgroundPosition: ['0% 0%', '200% 0%'],
            }}
            transition={{
              duration: 3,
              repeat: Infinity,
              ease: 'linear',
            }}
          />
        </div>

        {/* Collapsed state */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full p-6 text-left focus:outline-none focus:ring-2 focus:ring-offset-2 transition-all"
          style={{
            ['--tw-ring-color' as any]: theme.primary,
          }}
        >
          <div className="flex items-start gap-4">
            {/* Icon with rotating effect on expand */}
            <motion.div
              animate={{ rotate: isExpanded ? 360 : 0 }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
              className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center relative overflow-hidden"
              style={{ backgroundColor: `${theme.primary}15` }}
            >
              <motion.div
                className="absolute inset-0 opacity-0"
                animate={{ opacity: isExpanded ? [0, 0.3, 0] : 0 }}
                transition={{ duration: 1, repeat: Infinity }}
                style={{ background: `radial-gradient(circle at center, ${theme.primary}40, transparent)` }}
              />
              <Icon className="w-6 h-6 relative z-10" style={{ color: theme.primary }} />
            </motion.div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 mb-2">
                <h3 className="text-base font-bold text-navy-900" style={{ fontFamily: "'Barlow', sans-serif" }}>
                  {parameter} Tipping Point
                </h3>
                <motion.span
                  className="px-3 py-1 rounded-full text-sm font-bold"
                  style={{
                    backgroundColor: `${theme.primary}20`,
                    color: theme.primary,
                  }}
                  whileHover={{ scale: 1.05 }}
                >
                  {valueDisplay}
                </motion.span>
              </div>

              <p className="text-sm text-text-secondary mb-3 leading-relaxed">
                {description}
              </p>

              {ports_affected && ports_affected.length > 0 && (
                <div className="flex items-center gap-2 mb-3">
                  <Anchor className="w-3.5 h-3.5 text-text-secondary" />
                  <p className="text-xs text-text-secondary">
                    {ports_affected.slice(0, 3).join(', ')}{ports_affected.length > 3 && '...'}
                  </p>
                </div>
              )}

              {/* Profit comparison - always visible */}
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-teal-500" />
                  <div>
                    <p className="text-xs text-text-secondary">Before</p>
                    <p className="text-sm font-bold font-mono text-teal-600">
                      {formatCurrency(profit_before)}
                    </p>
                  </div>
                </div>

                <motion.div
                  animate={{ x: [0, 4, 0] }}
                  transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                >
                  <TrendingDown className="w-5 h-5 text-coral-500" />
                </motion.div>

                <div className="flex items-center gap-2">
                  <div>
                    <p className="text-xs text-text-secondary">After</p>
                    <p className="text-sm font-bold font-mono text-coral-500">
                      {formatCurrency(profit_after)}
                    </p>
                  </div>
                </div>

                <div className="ml-auto">
                  <p className="text-xs text-text-secondary">Impact</p>
                  <p className="text-sm font-bold font-mono text-coral-600">
                    {profitDeltaPct}%
                  </p>
                </div>
              </div>
            </div>

            {/* Expand/collapse button */}
            <motion.div
              animate={{ rotate: isExpanded ? 180 : 0 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
              style={{
                backgroundColor: isExpanded ? `${theme.primary}15` : '#F8FAFC',
                color: isExpanded ? theme.primary : '#6B7B8D',
              }}
            >
              <ChevronDown className="w-5 h-5" />
            </motion.div>
          </div>
        </button>

        {/* Expanded state */}
        <AnimatePresence>
          {isExpanded && portfolio_before && portfolio_after && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
              className="overflow-hidden"
            >
              <div className="px-6 pb-6 pt-2 space-y-4">
                {/* Divider with wave pattern */}
                <div className="relative h-px">
                  <div
                    className="absolute inset-0 opacity-20"
                    style={{
                      background: `repeating-linear-gradient(90deg, ${theme.primary} 0px, transparent 4px, transparent 8px)`,
                    }}
                  />
                </div>

                {/* Portfolio comparison */}
                <div className="grid grid-cols-2 gap-4">
                  {/* Before portfolio */}
                  <PortfolioView
                    title="Before Tipping Point"
                    portfolio={portfolio_before}
                    theme={theme}
                    variant="before"
                  />

                  {/* After portfolio */}
                  <PortfolioView
                    title="After Tipping Point"
                    portfolio={portfolio_after}
                    theme={theme}
                    variant="after"
                  />
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </motion.div>
  );
}

// Portfolio view component
function PortfolioView({
  title,
  portfolio,
  theme,
  variant
}: {
  title: string;
  portfolio: PortfolioDetails;
  theme: any;
  variant: 'before' | 'after';
}) {
  return (
    <div
      className="rounded-lg p-4 space-y-3"
      style={{
        backgroundColor: variant === 'before' ? '#F8FAF8' : `${theme.light}40`,
        border: `1px solid ${variant === 'before' ? '#E5E7EB' : theme.primary}30`,
      }}
    >
      <h4 className="text-xs font-bold uppercase tracking-wider" style={{ color: theme.primary }}>
        {title}
      </h4>

      {/* Cargill assignments */}
      {portfolio.cargill_assignments.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Ship className="w-3.5 h-3.5 text-teal-600" />
            <p className="text-xs font-semibold text-navy-900">Cargill Fleet</p>
          </div>
          <div className="space-y-1.5">
            {portfolio.cargill_assignments.map((a, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="text-xs bg-white rounded-md p-2 border border-gray-200"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-navy-900 truncate" title={a.vessel}>
                    {a.vessel.length > 15 ? a.vessel.substring(0, 15) + '...' : a.vessel}
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 bg-teal-50 text-teal-700 rounded font-medium">
                    {a.cargo_type === 'market' ? 'MKT' : 'CGO'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-text-secondary truncate" title={a.cargo}>
                    → {a.cargo.length > 18 ? a.cargo.substring(0, 18) + '...' : a.cargo}
                  </span>
                  <span className="font-mono font-semibold text-teal-600">
                    {formatCurrency(a.profit)}
                  </span>
                </div>
                <div className="text-[10px] text-text-secondary mt-0.5">
                  TCE: ${a.tce.toLocaleString()}/d
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Market hires */}
      {portfolio.market_hires.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Anchor className="w-3.5 h-3.5 text-amber-600" />
            <p className="text-xs font-semibold text-navy-900">Market Hires</p>
          </div>
          <div className="space-y-1.5">
            {portfolio.market_hires.map((a, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: (portfolio.cargill_assignments.length + i) * 0.05 }}
                className="text-xs bg-amber-50 rounded-md p-2 border border-amber-200"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-navy-900 truncate" title={a.vessel}>
                    {a.vessel.length > 15 ? a.vessel.substring(0, 15) + '...' : a.vessel}
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded font-medium">
                    HIRE
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-text-secondary truncate" title={a.cargo}>
                    → {a.cargo.length > 18 ? a.cargo.substring(0, 18) + '...' : a.cargo}
                  </span>
                  <span className="font-mono font-semibold text-amber-600">
                    {formatCurrency(a.profit)}
                  </span>
                </div>
                {a.hire_rate && (
                  <div className="text-[10px] text-text-secondary mt-0.5">
                    Hire: ${a.hire_rate.toLocaleString()}/d
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Unassigned warnings */}
      {(portfolio.unassigned_vessels.length > 0 || portfolio.unassigned_cargoes.length > 0) && (
        <div className="space-y-1.5 pt-2 border-t border-gray-200">
          {portfolio.unassigned_vessels.length > 0 && (
            <div className="text-xs">
              <span className="text-text-secondary">Idle Vessels: </span>
              <span className="text-navy-900 font-medium">{portfolio.unassigned_vessels.length}</span>
            </div>
          )}
          {portfolio.unassigned_cargoes.length > 0 && (
            <div className="flex items-center gap-1 text-xs">
              <AlertTriangle className="w-3 h-3 text-coral-500" />
              <span className="text-coral-600 font-medium">
                {portfolio.unassigned_cargoes.length} uncovered cargo(es)
              </span>
            </div>
          )}
        </div>
      )}

      {/* Summary metrics */}
      <div
        className="rounded-md p-2.5 space-y-1.5"
        style={{ backgroundColor: `${theme.primary}08` }}
      >
        <div className="flex items-center justify-between text-xs">
          <span className="text-text-secondary">Total Profit</span>
          <span className="font-mono font-bold" style={{ color: theme.primary }}>
            {formatCurrency(portfolio.total_profit)}
          </span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-text-secondary">Avg TCE</span>
          <span className="font-mono font-semibold text-ocean-600">
            {formatCurrencyFull(portfolio.avg_tce)}/d
          </span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-text-secondary">Assignments</span>
          <span className="font-semibold text-navy-900">
            {portfolio.cargill_assignments.length + portfolio.market_hires.length}
          </span>
        </div>
      </div>
    </div>
  );
}

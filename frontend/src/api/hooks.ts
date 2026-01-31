import { useQuery } from '@tanstack/react-query';
import { api } from './client';

export function useVessels() {
  return useQuery({
    queryKey: ['vessels'],
    queryFn: api.getVessels,
    staleTime: Infinity,
  });
}

export function useCargoes() {
  return useQuery({
    queryKey: ['cargoes'],
    queryFn: api.getCargoes,
    staleTime: Infinity,
  });
}

export function usePortfolio(useMLDelays: boolean = false) {
  return useQuery({
    queryKey: ['portfolio', useMLDelays],
    queryFn: async () => {
      const raw = await api.getPortfolio(useMLDelays);
      // Handle both old format (single portfolio) and new format (list of portfolios)
      const portfolios = raw.portfolios || [raw];

      const normalizePortfolio = (p: any) => ({
        assignments: p.assignments?.map((a: any) => ({
          vessel: a.vessel,
          cargo: a.cargo,
          vessel_type: a.voyage?.vessel_type || 'cargill',
          cargo_type: a.voyage?.cargo_type || 'cargill',
          ...(a.voyage || {}),
        })) || [],
        market_vessel_hires: p.market_vessel_hires || [],
        unassigned_vessels: p.unassigned_vessels || [],
        unassigned_cargoes: p.unassigned_cargoes || [],
        total_profit: p.total_profit || 0,
        avg_tce: p.avg_tce || 0,
      });

      return portfolios.map(normalizePortfolio);
    },
    staleTime: 5 * 60 * 1000, // 5 min - data is pre-computed at startup
    gcTime: 10 * 60 * 1000,
  });
}

export function useAllVoyages() {
  return useQuery({
    queryKey: ['allVoyages'],
    queryFn: api.getAllVoyages,
    staleTime: 5 * 60 * 1000, // 5 min - data is pre-computed at startup
    gcTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
}

export function useBunkerSensitivity() {
  return useQuery({
    queryKey: ['bunkerSensitivity'],
    queryFn: async () => {
      const raw = await api.getBunkerSensitivity();
      // Normalize: API returns bunker_multiplier, frontend expects parameter_value
      return raw.map((d: any) => ({
        parameter_value: d.bunker_multiplier,
        total_profit: d.total_profit,
        avg_tce: d.avg_tce,
        assignments: d.assignments,
      }));
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useDelaySensitivity() {
  return useQuery({
    queryKey: ['delaySensitivity'],
    queryFn: async () => {
      const raw = await api.getDelaySensitivity();
      // Normalize: API returns port_delay_days, frontend expects parameter_value
      return raw.map((d: any) => ({
        parameter_value: d.port_delay_days,
        total_profit: d.total_profit,
        avg_tce: d.avg_tce,
        assignments: d.assignments,
      }));
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useTippingPoints() {
  return useQuery({
    queryKey: ['tippingPoints'],
    queryFn: async () => {
      const raw = await api.getTippingPoints();
      // Normalize: API returns { bunker: {...}, port_delay: {...} }
      const points: any[] = [];
      if (raw.bunker) {
        points.push({
          parameter: 'Bunker Price',
          value: raw.bunker.multiplier,
          description: raw.bunker.description || `At ${Math.round(raw.bunker.change_pct)}% increase, assignment changes occur.`,
          profit_before: raw.bunker.profit_before || 0,
          profit_after: raw.bunker.profit_after || 0,
          current_best_assignments: raw.bunker.current_best_assignments || [],
          next_best_assignments: raw.bunker.next_best_assignments || [],
        });
      }
      if (raw.port_delay) {
        points.push({
          parameter: 'Port Delay in China',
          value: raw.port_delay.days || raw.port_delay.value,
          description: raw.port_delay.description || `At +${raw.port_delay.days || raw.port_delay.value} days delay in China, assignment changes occur.`,
          profit_before: raw.port_delay.profit_before || 0,
          profit_after: raw.port_delay.profit_after || 0,
          region: raw.port_delay.region || 'china',
          ports_affected: raw.port_delay.ports_affected || [],
          current_best_assignments: raw.port_delay.current_best_assignments || [],
          next_best_assignments: raw.port_delay.next_best_assignments || [],
        });
      }
      return points.length > 0 ? points : null;
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function usePortDelays() {
  return useQuery({
    queryKey: ['portDelays'],
    queryFn: async () => {
      const raw = await api.getPortDelays();
      // Normalize: API returns predicted_delay, frontend expects predicted_delay_days
      return raw.map((d: any) => ({
        port: d.port,
        predicted_delay_days: d.predicted_delay ?? d.predicted_delay_days ?? 0,
        confidence_lower: d.confidence_lower ?? 0,
        confidence_upper: d.confidence_upper ?? 0,
        congestion_level: d.congestion_level || 'low',
      }));
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useModelInfo() {
  return useQuery({
    queryKey: ['modelInfo'],
    queryFn: async () => {
      const raw = await api.getModelInfo();
      // If empty object, return null so fallback to mock kicks in
      if (!raw || Object.keys(raw).length === 0) return null;
      return raw;
    },
    staleTime: Infinity,
  });
}

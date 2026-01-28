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

export function usePortfolio() {
  return useQuery({
    queryKey: ['portfolio'],
    queryFn: async () => {
      const raw = await api.getPortfolio();
      // Normalize: API returns { assignments: [{vessel, cargo, voyage:{...}}], market_vessel_hires, unassigned_vessels, unassigned_cargoes, total_profit, avg_tce }
      return {
        assignments: raw.assignments?.map((a: any) => ({
          vessel: a.vessel,
          cargo: a.cargo,
          vessel_type: a.voyage?.vessel_type || 'cargill',
          cargo_type: a.voyage?.cargo_type || 'cargill',
          ...(a.voyage || {}),
        })) || [],
        market_vessel_hires: raw.market_vessel_hires || [],
        unassigned_vessels: raw.unassigned_vessels || [],
        unassigned_cargoes: raw.unassigned_cargoes || [],
        total_profit: raw.total_profit || 0,
        avg_tce: raw.avg_tce || 0,
      };
    },
    staleTime: 0, // Don't cache - always fetch fresh data
    gcTime: 0, // Immediately garbage collect old data
  });
}

export function useAllVoyages() {
  return useQuery({
    queryKey: ['allVoyages'],
    queryFn: api.getAllVoyages,
    staleTime: 0, // Always refetch
    gcTime: 5 * 60 * 1000, // Keep in cache for 5 min
    refetchOnMount: true,
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
          description: `At ${Math.round(raw.bunker.change_pct)}% increase, assignment changes occur.`,
          profit_before: 0,
          profit_after: 0,
        });
      }
      if (raw.port_delay) {
        points.push({
          parameter: 'Port Delay',
          value: raw.port_delay.days || raw.port_delay.value,
          description: `At +${raw.port_delay.days || raw.port_delay.value} days delay, assignment changes occur.`,
          profit_before: 0,
          profit_after: 0,
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

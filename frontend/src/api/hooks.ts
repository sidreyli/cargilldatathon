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

export function useAllVoyages(useMLDelays: boolean = false) {
  return useQuery({
    queryKey: ['allVoyages', useMLDelays],  // Include useMLDelays in cache key
    queryFn: () => api.getAllVoyages(useMLDelays),
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

export function useChinaDelaySensitivity() {
  return useQuery({
    queryKey: ['chinaDelaySensitivity'],
    queryFn: async () => {
      const raw = await api.getChinaDelaySensitivity();
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
      // Return raw API response with all fields including portfolio data
      return await api.getTippingPoints();
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

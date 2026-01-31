export interface Vessel {
  name: string;
  dwt: number;
  hire_rate: number;
  speed_laden: number;
  speed_laden_eco: number;
  speed_ballast: number;
  speed_ballast_eco: number;
  current_port: string;
  etd: string;
  bunker_rob_vlsfo: number;
  bunker_rob_mgo: number;
  is_cargill: boolean;
}

export interface Cargo {
  name: string;
  customer: string;
  commodity: string;
  quantity: number;
  quantity_tolerance: number;
  laycan_start: string;
  laycan_end: string;
  freight_rate: number;
  load_port: string;
  discharge_port: string;
  load_rate: number;
  discharge_rate: number;
  port_cost_load: number;
  port_cost_discharge: number;
  commission: number;
  is_cargill: boolean;
}

export interface VoyageResult {
  vessel: string;
  cargo: string;
  speed_type: string;
  can_make_laycan: boolean;
  arrival_date: string;
  laycan_end: string;
  days_margin: number;
  total_days: number;
  ballast_days: number;
  laden_days: number;
  load_days: number;
  discharge_days: number;
  waiting_days: number;
  cargo_qty: number;
  gross_freight: number;
  net_freight: number;
  commission_cost: number;
  total_bunker_cost: number;
  bunker_cost_vlsfo: number;
  bunker_cost_mgo: number;
  hire_cost: number;
  port_costs: number;
  misc_costs: number;
  net_profit: number;
  tce: number;
  vlsfo_consumed: number;
  mgo_consumed: number;
  bunker_port: string | null;
  bunker_savings: number;
  vessel_type?: string;
  cargo_type?: string;
}

export interface Assignment {
  vessel: string;
  cargo: string;
  voyage: VoyageResult;
}

export interface PortfolioResult {
  assignments: Assignment[];
  unassigned_vessels: string[];
  unassigned_cargoes: string[];
  total_profit: number;
  total_tce: number;
  avg_tce: number;
  market_vessel_hires?: Assignment[];
}

export interface PortfolioResponse {
  portfolios: PortfolioResult[];
  best: PortfolioResult | null;
}

export interface ScenarioPoint {
  parameter_value: number;
  total_profit: number;
  avg_tce: number;
  assignments: string[];
}

export interface TippingPoint {
  parameter: string;
  value: number;
  description: string;
  profit_before: number;
  profit_after: number;
}

export interface AssignmentDetail {
  vessel: string;
  cargo: string;
  profit: number;
  tce: number;
  vessel_type?: 'cargill' | 'market';
  cargo_type?: 'cargill' | 'market';
  hire_rate?: number;
}

export interface PortfolioDetails {
  cargill_assignments: AssignmentDetail[];
  market_hires: AssignmentDetail[];
  unassigned_vessels: string[];
  unassigned_cargoes: string[];
  total_profit: number;
  total_tce: number;
  avg_tce: number;
}

export interface TippingPointExtended extends TippingPoint {
  region?: string;
  ports_affected?: string[];
  current_best_assignments?: AssignmentDetail[];
  next_best_assignments?: AssignmentDetail[];
  portfolio_before?: PortfolioDetails;
  portfolio_after?: PortfolioDetails;
}

export interface PortDelay {
  port: string;
  predicted_delay_days: number;
  confidence_lower: number;
  confidence_upper: number;
  congestion_level: 'low' | 'medium' | 'high';
  model_used: string;
}

export interface ModelInfo {
  model_type: string;
  training_date: string;
  metrics: {
    mae: number;
    rmse: number;
    within_1_day: number;
    within_2_days: number;
  };
  feature_importance: { feature: string; importance: number }[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isToolCall?: boolean;
  toolName?: string;
}

export type TabId = 'dashboard' | 'voyages' | 'scenarios' | 'ml';

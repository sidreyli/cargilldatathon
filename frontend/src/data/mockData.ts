import type {
  Vessel, Cargo, VoyageResult, Assignment, PortfolioResult,
  ScenarioPoint, TippingPoint, TippingPointExtended, AssignmentDetail,
  PortDelay, ModelInfo, ChatMessage
} from '../types';

// ─── China Ports ──────────────────────────────────────────────
export const CHINA_PORTS = [
  'QINGDAO', 'RIZHAO', 'CAOFEIDIAN', 'FANGCHENG',
  'LIANYUNGANG', 'SHANGHAI', 'TIANJIN', 'DALIAN'
];

// ─── Vessels ───────────────────────────────────────────────
export const mockVessels: Vessel[] = [
  { name: 'Ann Bell', dwt: 180803, hire_rate: 11750, speed_laden: 13.5, speed_laden_eco: 12.0, speed_ballast: 14.5, speed_ballast_eco: 12.5, current_port: 'Qingdao', etd: '25 Feb 2026', bunker_rob_vlsfo: 401.3, bunker_rob_mgo: 45.1, is_cargill: true },
  { name: 'Ocean Horizon', dwt: 181550, hire_rate: 15750, speed_laden: 13.8, speed_laden_eco: 12.3, speed_ballast: 14.8, speed_ballast_eco: 12.8, current_port: 'Map Ta Phut', etd: '1 Mar 2026', bunker_rob_vlsfo: 265.8, bunker_rob_mgo: 64.3, is_cargill: true },
  { name: 'Pacific Glory', dwt: 182320, hire_rate: 14800, speed_laden: 13.5, speed_laden_eco: 12.2, speed_ballast: 14.2, speed_ballast_eco: 12.7, current_port: 'Gwangyang', etd: '10 Mar 2026', bunker_rob_vlsfo: 601.9, bunker_rob_mgo: 98.1, is_cargill: true },
  { name: 'Golden Ascent', dwt: 179965, hire_rate: 13950, speed_laden: 13.0, speed_laden_eco: 11.8, speed_ballast: 14.0, speed_ballast_eco: 12.3, current_port: 'Fangcheng', etd: '8 Mar 2026', bunker_rob_vlsfo: 793.3, bunker_rob_mgo: 17.1, is_cargill: true },
];

// ─── Cargoes (Cargill committed) ───────────────────────────
export const mockCargoes: Cargo[] = [
  { name: 'EGA Bauxite', customer: 'EGA', commodity: 'Bauxite', quantity: 180000, quantity_tolerance: 0.10, laycan_start: '2 Apr 2026', laycan_end: '10 Apr 2026', freight_rate: 23.0, load_port: 'Kamsar', discharge_port: 'Qingdao', load_rate: 30000, discharge_rate: 25000, port_cost_load: 0, port_cost_discharge: 0, commission: 0.0125, is_cargill: true },
  { name: 'BHP Iron Ore', customer: 'BHP', commodity: 'Iron Ore', quantity: 160000, quantity_tolerance: 0.10, laycan_start: '7 Mar 2026', laycan_end: '11 Mar 2026', freight_rate: 9.0, load_port: 'Port Hedland', discharge_port: 'Lianyungang', load_rate: 80000, discharge_rate: 30000, port_cost_load: 260000, port_cost_discharge: 120000, commission: 0.0375, is_cargill: true },
  { name: 'CSN Iron Ore', customer: 'CSN', commodity: 'Iron Ore', quantity: 180000, quantity_tolerance: 0.10, laycan_start: '1 Apr 2026', laycan_end: '8 Apr 2026', freight_rate: 22.30, load_port: 'Itaguai', discharge_port: 'Qingdao', load_rate: 60000, discharge_rate: 30000, port_cost_load: 75000, port_cost_discharge: 90000, commission: 0.0375, is_cargill: true },
];

// ─── Market Cargoes ────────────────────────────────────────
export const mockMarketCargoes: Cargo[] = [
  { name: 'Vale Malaysia Iron Ore', customer: 'Vale', commodity: 'Iron Ore', quantity: 170000, quantity_tolerance: 0.10, laycan_start: '15 Mar 2026', laycan_end: '22 Mar 2026', freight_rate: 18.5, load_port: 'Tubarao', discharge_port: 'Port Klang', load_rate: 70000, discharge_rate: 35000, port_cost_load: 85000, port_cost_discharge: 65000, commission: 0.035, is_cargill: false },
  { name: 'BHP Iron Ore (S.Korea)', customer: 'BHP', commodity: 'Iron Ore', quantity: 165000, quantity_tolerance: 0.10, laycan_start: '10 Mar 2026', laycan_end: '18 Mar 2026', freight_rate: 10.5, load_port: 'Port Hedland', discharge_port: 'Gwangyang', load_rate: 80000, discharge_rate: 40000, port_cost_load: 260000, port_cost_discharge: 95000, commission: 0.0375, is_cargill: false },
  { name: 'Teck Coking Coal', customer: 'Teck', commodity: 'Coking Coal', quantity: 155000, quantity_tolerance: 0.10, laycan_start: '20 Mar 2026', laycan_end: '28 Mar 2026', freight_rate: 28.0, load_port: 'Vancouver', discharge_port: 'Qingdao', load_rate: 25000, discharge_rate: 30000, port_cost_load: 95000, port_cost_discharge: 90000, commission: 0.03, is_cargill: false },
  { name: 'Adaro Coal', customer: 'Adaro', commodity: 'Thermal Coal', quantity: 175000, quantity_tolerance: 0.10, laycan_start: '12 Mar 2026', laycan_end: '20 Mar 2026', freight_rate: 12.0, load_port: 'Taboneo', discharge_port: 'Mundra', load_rate: 45000, discharge_rate: 35000, port_cost_load: 55000, port_cost_discharge: 70000, commission: 0.025, is_cargill: false },
];

// ─── Market Vessels (hired for Cargill cargoes) ────────────
export const mockMarketVessels: Vessel[] = [
  { name: 'Iron Century', dwt: 182100, hire_rate: 20784, speed_laden: 13.2, speed_laden_eco: 11.8, speed_ballast: 14.0, speed_ballast_eco: 12.5, current_port: 'Singapore', etd: '28 Feb 2026', bunker_rob_vlsfo: 350.0, bunker_rob_mgo: 55.0, is_cargill: false },
  { name: 'Pacific Vanguard', dwt: 179500, hire_rate: 18000, speed_laden: 13.5, speed_laden_eco: 12.0, speed_ballast: 14.2, speed_ballast_eco: 12.6, current_port: 'Hong Kong', etd: '2 Mar 2026', bunker_rob_vlsfo: 420.0, bunker_rob_mgo: 62.0, is_cargill: false },
  { name: 'Coral Emperor', dwt: 181200, hire_rate: 13376, speed_laden: 13.0, speed_laden_eco: 11.5, speed_ballast: 13.8, speed_ballast_eco: 12.2, current_port: 'Durban', etd: '5 Mar 2026', bunker_rob_vlsfo: 380.0, bunker_rob_mgo: 48.0, is_cargill: false },
];

// ─── All Voyage Results (matrix) ───────────────────────────
export const mockAllVoyages: VoyageResult[] = [
  // Ann Bell
  { vessel: 'Ann Bell', cargo: 'EGA Bauxite', speed_type: 'eco', can_make_laycan: true, arrival_date: '2026-04-04', laycan_end: '2026-04-10', days_margin: 6.0, total_days: 56.2, ballast_days: 18.3, laden_days: 22.1, load_days: 6.6, discharge_days: 7.3, waiting_days: 0, cargo_qty: 177303, gross_freight: 4077969, net_freight: 4027000, commission_cost: 50969, total_bunker_cost: 887400, bunker_cost_vlsfo: 742300, bunker_cost_mgo: 145100, hire_cost: 660350, port_costs: 0, misc_costs: 15000, net_profit: 2464250, tce: 38120, vlsfo_consumed: 1514, mgo_consumed: 224, bunker_port: 'Fujairah', bunker_savings: 48200 },
  { vessel: 'Ann Bell', cargo: 'BHP Iron Ore', speed_type: 'eco', can_make_laycan: true, arrival_date: '2026-03-09', laycan_end: '2026-03-11', days_margin: 2.0, total_days: 32.5, ballast_days: 8.1, laden_days: 14.6, load_days: 2.2, discharge_days: 5.9, waiting_days: 0, cargo_qty: 176000, gross_freight: 1584000, net_freight: 1524600, commission_cost: 59400, total_bunker_cost: 498700, bunker_cost_vlsfo: 418200, bunker_cost_mgo: 80500, hire_cost: 381875, port_costs: 380000, misc_costs: 15000, net_profit: 249025, tce: 19920, vlsfo_consumed: 854, mgo_consumed: 124, bunker_port: 'Singapore', bunker_savings: 21400 },
  { vessel: 'Ann Bell', cargo: 'CSN Iron Ore', speed_type: 'eco', can_make_laycan: false, arrival_date: '2026-04-14', laycan_end: '2026-04-08', days_margin: -6.0, total_days: 72.8, ballast_days: 28.4, laden_days: 30.1, load_days: 3.3, discharge_days: 6.5, waiting_days: 0, cargo_qty: 177303, gross_freight: 3953858, net_freight: 3805592, commission_cost: 148267, total_bunker_cost: 1142300, bunker_cost_vlsfo: 958200, bunker_cost_mgo: 184100, hire_cost: 855400, port_costs: 165000, misc_costs: 15000, net_profit: 1627892, tce: 37200, vlsfo_consumed: 1956, mgo_consumed: 284, bunker_port: 'Gibraltar', bunker_savings: 62100 },
  // Ocean Horizon
  { vessel: 'Ocean Horizon', cargo: 'EGA Bauxite', speed_type: 'eco', can_make_laycan: true, arrival_date: '2026-04-06', laycan_end: '2026-04-10', days_margin: 4.0, total_days: 55.8, ballast_days: 17.9, laden_days: 21.6, load_days: 6.6, discharge_days: 7.3, waiting_days: 0, cargo_qty: 178050, gross_freight: 4095150, net_freight: 4043966, commission_cost: 51184, total_bunker_cost: 912100, bunker_cost_vlsfo: 764800, bunker_cost_mgo: 147300, hire_cost: 878850, port_costs: 0, misc_costs: 15000, net_profit: 2238016, tce: 34780, vlsfo_consumed: 1560, mgo_consumed: 227, bunker_port: 'Fujairah', bunker_savings: 44800 },
  { vessel: 'Ocean Horizon', cargo: 'BHP Iron Ore', speed_type: 'eco', can_make_laycan: true, arrival_date: '2026-03-10', laycan_end: '2026-03-11', days_margin: 1.0, total_days: 30.2, ballast_days: 6.4, laden_days: 14.1, load_days: 2.2, discharge_days: 5.8, waiting_days: 0, cargo_qty: 176000, gross_freight: 1584000, net_freight: 1524600, commission_cost: 59400, total_bunker_cost: 478200, bunker_cost_vlsfo: 400800, bunker_cost_mgo: 77400, hire_cost: 475650, port_costs: 380000, misc_costs: 15000, net_profit: 175750, tce: 18440, vlsfo_consumed: 818, mgo_consumed: 119, bunker_port: 'Singapore', bunker_savings: 18700 },
  { vessel: 'Ocean Horizon', cargo: 'CSN Iron Ore', speed_type: 'eco', can_make_laycan: true, arrival_date: '2026-04-05', laycan_end: '2026-04-08', days_margin: 3.0, total_days: 68.4, ballast_days: 24.8, laden_days: 29.6, load_days: 3.3, discharge_days: 6.5, waiting_days: 0, cargo_qty: 178050, gross_freight: 3970515, net_freight: 3821633, commission_cost: 148882, total_bunker_cost: 1098400, bunker_cost_vlsfo: 921600, bunker_cost_mgo: 176800, hire_cost: 1077300, port_costs: 165000, misc_costs: 15000, net_profit: 1465933, tce: 33290, vlsfo_consumed: 1882, mgo_consumed: 273, bunker_port: 'Gibraltar', bunker_savings: 57300 },
  // Pacific Glory
  { vessel: 'Pacific Glory', cargo: 'EGA Bauxite', speed_type: 'eco', can_make_laycan: true, arrival_date: '2026-04-07', laycan_end: '2026-04-10', days_margin: 3.0, total_days: 53.1, ballast_days: 16.2, laden_days: 21.8, load_days: 6.6, discharge_days: 7.3, waiting_days: 0, cargo_qty: 178820, gross_freight: 4112860, net_freight: 4061278, commission_cost: 51582, total_bunker_cost: 878600, bunker_cost_vlsfo: 736400, bunker_cost_mgo: 142200, hire_cost: 785880, port_costs: 0, misc_costs: 15000, net_profit: 2381798, tce: 38920, vlsfo_consumed: 1502, mgo_consumed: 219, bunker_port: 'Fujairah', bunker_savings: 41200 },
  { vessel: 'Pacific Glory', cargo: 'BHP Iron Ore', speed_type: 'eco', can_make_laycan: true, arrival_date: '2026-03-11', laycan_end: '2026-03-11', days_margin: 0.0, total_days: 29.8, ballast_days: 5.8, laden_days: 14.3, load_days: 2.2, discharge_days: 5.9, waiting_days: 0, cargo_qty: 176000, gross_freight: 1584000, net_freight: 1524600, commission_cost: 59400, total_bunker_cost: 465300, bunker_cost_vlsfo: 390200, bunker_cost_mgo: 75100, hire_cost: 441040, port_costs: 380000, misc_costs: 15000, net_profit: 223260, tce: 20180, vlsfo_consumed: 796, mgo_consumed: 116, bunker_port: 'Singapore', bunker_savings: 16900 },
  { vessel: 'Pacific Glory', cargo: 'CSN Iron Ore', speed_type: 'eco', can_make_laycan: false, arrival_date: '2026-04-12', laycan_end: '2026-04-08', days_margin: -4.0, total_days: 66.9, ballast_days: 23.1, laden_days: 29.8, load_days: 3.3, discharge_days: 6.5, waiting_days: 0, cargo_qty: 178820, gross_freight: 3987676, net_freight: 3838142, commission_cost: 149534, total_bunker_cost: 1068200, bunker_cost_vlsfo: 896400, bunker_cost_mgo: 171800, hire_cost: 990120, port_costs: 165000, misc_costs: 15000, net_profit: 1599822, tce: 36120, vlsfo_consumed: 1828, mgo_consumed: 265, bunker_port: 'Gibraltar', bunker_savings: 54200 },
  // Golden Ascent
  { vessel: 'Golden Ascent', cargo: 'EGA Bauxite', speed_type: 'eco', can_make_laycan: true, arrival_date: '2026-04-08', laycan_end: '2026-04-10', days_margin: 2.0, total_days: 58.6, ballast_days: 20.1, laden_days: 23.4, load_days: 6.8, discharge_days: 7.1, waiting_days: 0, cargo_qty: 176465, gross_freight: 4058695, net_freight: 4007961, commission_cost: 50734, total_bunker_cost: 842500, bunker_cost_vlsfo: 706100, bunker_cost_mgo: 136400, hire_cost: 817470, port_costs: 0, misc_costs: 15000, net_profit: 2332991, tce: 35910, vlsfo_consumed: 1440, mgo_consumed: 210, bunker_port: 'Fujairah', bunker_savings: 38400 },
  { vessel: 'Golden Ascent', cargo: 'BHP Iron Ore', speed_type: 'eco', can_make_laycan: true, arrival_date: '2026-03-10', laycan_end: '2026-03-11', days_margin: 1.0, total_days: 33.8, ballast_days: 9.4, laden_days: 15.2, load_days: 2.2, discharge_days: 5.9, waiting_days: 0, cargo_qty: 176000, gross_freight: 1584000, net_freight: 1524600, commission_cost: 59400, total_bunker_cost: 512800, bunker_cost_vlsfo: 430200, bunker_cost_mgo: 82600, hire_cost: 471540, port_costs: 380000, misc_costs: 15000, net_profit: 145260, tce: 16230, vlsfo_consumed: 878, mgo_consumed: 127, bunker_port: 'Singapore', bunker_savings: 19800 },
  { vessel: 'Golden Ascent', cargo: 'CSN Iron Ore', speed_type: 'eco', can_make_laycan: true, arrival_date: '2026-04-07', laycan_end: '2026-04-08', days_margin: 1.0, total_days: 71.2, ballast_days: 27.1, laden_days: 30.8, load_days: 3.4, discharge_days: 6.8, waiting_days: 0, cargo_qty: 176465, gross_freight: 3935174, net_freight: 3787581, commission_cost: 147593, total_bunker_cost: 1012600, bunker_cost_vlsfo: 849400, bunker_cost_mgo: 163200, hire_cost: 993240, port_costs: 165000, misc_costs: 15000, net_profit: 1601741, tce: 34280, vlsfo_consumed: 1734, mgo_consumed: 252, bunker_port: 'Gibraltar', bunker_savings: 52800 },
];

// ─── Cargill Vessels on Market Cargoes (optimized assignments) ───
export const mockMarketCargoVoyages: VoyageResult[] = [
  // Ann Bell → Vale Malaysia Iron Ore
  { vessel: 'Ann Bell', cargo: 'Vale Malaysia Iron Ore (Brazil-Malaysia)', speed_type: 'eco', can_make_laycan: true, arrival_date: '2026-03-18', laycan_end: '2026-03-22', days_margin: 4.0, total_days: 48.5, ballast_days: 12.2, laden_days: 24.8, load_days: 2.7, discharge_days: 5.4, waiting_days: 0, cargo_qty: 167000, gross_freight: 3089500, net_freight: 2981270, commission_cost: 108230, total_bunker_cost: 762400, bunker_cost_vlsfo: 638200, bunker_cost_mgo: 124200, hire_cost: 570125, port_costs: 150000, misc_costs: 15000, net_profit: 915509, tce: 22614, vlsfo_consumed: 1302, mgo_consumed: 191, bunker_port: 'Gibraltar', bunker_savings: 38500, vessel_type: 'cargill', cargo_type: 'market' },
  // Ocean Horizon → BHP Iron Ore (S.Korea)
  { vessel: 'Ocean Horizon', cargo: 'BHP Iron Ore (Australia-S.Korea)', speed_type: 'eco', can_make_laycan: true, arrival_date: '2026-03-14', laycan_end: '2026-03-18', days_margin: 4.0, total_days: 26.8, ballast_days: 5.2, laden_days: 12.4, load_days: 2.3, discharge_days: 4.6, waiting_days: 0, cargo_qty: 162000, gross_freight: 1701000, net_freight: 1637213, commission_cost: 63788, total_bunker_cost: 398600, bunker_cost_vlsfo: 334200, bunker_cost_mgo: 64400, hire_cost: 422100, port_costs: 355000, misc_costs: 15000, net_profit: 350978, tce: 27036, vlsfo_consumed: 682, mgo_consumed: 99, bunker_port: 'Singapore', bunker_savings: 15200, vessel_type: 'cargill', cargo_type: 'market' },
  // Pacific Glory → Teck Coking Coal
  { vessel: 'Pacific Glory', cargo: 'Teck Coking Coal (Canada-China)', speed_type: 'eco', can_make_laycan: true, arrival_date: '2026-03-24', laycan_end: '2026-03-28', days_margin: 4.0, total_days: 42.3, ballast_days: 8.6, laden_days: 21.2, load_days: 6.9, discharge_days: 5.8, waiting_days: 0, cargo_qty: 152000, gross_freight: 4256000, net_freight: 4128320, commission_cost: 127680, total_bunker_cost: 685200, bunker_cost_vlsfo: 574400, bunker_cost_mgo: 110800, hire_cost: 626040, port_costs: 185000, misc_costs: 15000, net_profit: 708408, tce: 29426, vlsfo_consumed: 1172, mgo_consumed: 171, bunker_port: 'Panama', bunker_savings: 28400, vessel_type: 'cargill', cargo_type: 'market' },
  // Golden Ascent → Adaro Coal
  { vessel: 'Golden Ascent', cargo: 'Adaro Coal (Indonesia-India)', speed_type: 'eco', can_make_laycan: true, arrival_date: '2026-03-16', laycan_end: '2026-03-20', days_margin: 4.0, total_days: 38.2, ballast_days: 9.8, laden_days: 16.4, load_days: 4.3, discharge_days: 5.6, waiting_days: 0, cargo_qty: 172000, gross_freight: 2064000, net_freight: 2012400, commission_cost: 51600, total_bunker_cost: 412800, bunker_cost_vlsfo: 346100, bunker_cost_mgo: 66700, hire_cost: 532890, port_costs: 125000, misc_costs: 15000, net_profit: 1169745, tce: 35181, vlsfo_consumed: 706, mgo_consumed: 103, bunker_port: 'Singapore', bunker_savings: 18900, vessel_type: 'cargill', cargo_type: 'market' },
];

// ─── Market Vessels on Cargill Cargoes (hired to cover commitments) ───
export const mockMarketVesselVoyages: VoyageResult[] = [
  // Iron Century → EGA Bauxite (hired at ~$20,784/day)
  { vessel: 'Iron Century', cargo: 'EGA Bauxite (Guinea-China)', speed_type: 'eco', can_make_laycan: true, arrival_date: '2026-04-05', laycan_end: '2026-04-10', days_margin: 5.0, total_days: 54.8, ballast_days: 17.5, laden_days: 21.8, load_days: 6.6, discharge_days: 7.2, waiting_days: 0, cargo_qty: 178500, gross_freight: 4105500, net_freight: 4054182, commission_cost: 51318, total_bunker_cost: 868200, bunker_cost_vlsfo: 727600, bunker_cost_mgo: 140600, hire_cost: 1138963, port_costs: 0, misc_costs: 15000, net_profit: 2032019, tce: 38782, vlsfo_consumed: 1485, mgo_consumed: 217, bunker_port: 'Fujairah', bunker_savings: 42100, vessel_type: 'market', cargo_type: 'cargill' },
  // Pacific Vanguard → BHP Iron Ore China (hired at FFA ~$18,000/day)
  { vessel: 'Pacific Vanguard', cargo: 'BHP Iron Ore (Australia-China)', speed_type: 'eco', can_make_laycan: true, arrival_date: '2026-03-09', laycan_end: '2026-03-11', days_margin: 2.0, total_days: 31.4, ballast_days: 7.2, laden_days: 14.5, load_days: 2.2, discharge_days: 5.8, waiting_days: 0, cargo_qty: 176000, gross_freight: 1584000, net_freight: 1524600, commission_cost: 59400, total_bunker_cost: 485600, bunker_cost_vlsfo: 407100, bunker_cost_mgo: 78500, hire_cost: 565200, port_costs: 380000, misc_costs: 15000, net_profit: 78800, tce: 16661, vlsfo_consumed: 831, mgo_consumed: 121, bunker_port: 'Singapore', bunker_savings: 19800, vessel_type: 'market', cargo_type: 'cargill' },
  // Coral Emperor → CSN Iron Ore (hired at ~$13,376/day)
  { vessel: 'Coral Emperor', cargo: 'CSN Iron Ore (Brazil-China)', speed_type: 'eco', can_make_laycan: true, arrival_date: '2026-04-06', laycan_end: '2026-04-08', days_margin: 2.0, total_days: 67.5, ballast_days: 24.2, laden_days: 29.4, load_days: 3.3, discharge_days: 6.5, waiting_days: 0, cargo_qty: 177600, gross_freight: 3960480, net_freight: 3811962, commission_cost: 148518, total_bunker_cost: 1052400, bunker_cost_vlsfo: 882900, bunker_cost_mgo: 169500, hire_cost: 902880, port_costs: 165000, misc_costs: 15000, net_profit: 1675682, tce: 31375, vlsfo_consumed: 1802, mgo_consumed: 261, bunker_port: 'Gibraltar', bunker_savings: 55200, vessel_type: 'market', cargo_type: 'cargill' },
];

// ─── Optimal Portfolio (Rank #1) ──────────────────────────────
export const mockPortfolio: PortfolioResult = {
  // Cargill vessels assigned to market cargoes (arbitrage strategy)
  assignments: [
    { vessel: 'ANN BELL', cargo: 'Vale Malaysia Iron Ore (Brazil-Malaysia)', voyage: mockMarketCargoVoyages[0] },
    { vessel: 'OCEAN HORIZON', cargo: 'BHP Iron Ore (Australia-S.Korea)', voyage: mockMarketCargoVoyages[1] },
    { vessel: 'PACIFIC GLORY', cargo: 'Teck Coking Coal (Canada-China)', voyage: mockMarketCargoVoyages[2] },
    { vessel: 'GOLDEN ASCENT', cargo: 'Adaro Coal (Indonesia-India)', voyage: mockMarketCargoVoyages[3] },
  ],
  // Market vessels hired to cover Cargill committed cargoes
  market_vessel_hires: [
    { vessel: 'IRON CENTURY', cargo: 'EGA Bauxite (Guinea-China)', voyage: mockMarketVesselVoyages[0] },
    { vessel: 'PACIFIC VANGUARD', cargo: 'BHP Iron Ore (Australia-China)', voyage: mockMarketVesselVoyages[1] },
    { vessel: 'CORAL EMPEROR', cargo: 'CSN Iron Ore (Brazil-China)', voyage: mockMarketVesselVoyages[2] },
  ],
  unassigned_vessels: [],
  unassigned_cargoes: [],
  total_profit: 5754425,
  total_tce: 201075,
  avg_tce: 28725,
};

// ─── Alternative Portfolio (Rank #2) ──────────────────────────
const mockPortfolio2: PortfolioResult = {
  // Different assignment strategy: ANN BELL on Cargill cargo directly
  assignments: [
    { vessel: 'ANN BELL', cargo: 'EGA Bauxite (Guinea-China)', voyage: mockAllVoyages[0] },
    { vessel: 'OCEAN HORIZON', cargo: 'BHP Iron Ore (Australia-S.Korea)', voyage: mockMarketCargoVoyages[1] },
    { vessel: 'PACIFIC GLORY', cargo: 'Teck Coking Coal (Canada-China)', voyage: mockMarketCargoVoyages[2] },
    { vessel: 'GOLDEN ASCENT', cargo: 'Adaro Coal (Indonesia-India)', voyage: mockMarketCargoVoyages[3] },
  ],
  market_vessel_hires: [
    { vessel: 'PACIFIC VANGUARD', cargo: 'BHP Iron Ore (Australia-China)', voyage: mockMarketVesselVoyages[1] },
    { vessel: 'CORAL EMPEROR', cargo: 'CSN Iron Ore (Brazil-China)', voyage: mockMarketVesselVoyages[2] },
  ],
  unassigned_vessels: [],
  unassigned_cargoes: [],
  total_profit: 5412890,
  total_tce: 189400,
  avg_tce: 27062,
};

// ─── Alternative Portfolio (Rank #3) ──────────────────────────
const mockPortfolio3: PortfolioResult = {
  // Conservative strategy: More Cargill vessels on Cargill cargoes
  assignments: [
    { vessel: 'ANN BELL', cargo: 'EGA Bauxite (Guinea-China)', voyage: mockAllVoyages[0] },
    { vessel: 'OCEAN HORIZON', cargo: 'CSN Iron Ore (Brazil-China)', voyage: mockAllVoyages[5] },
    { vessel: 'PACIFIC GLORY', cargo: 'Teck Coking Coal (Canada-China)', voyage: mockMarketCargoVoyages[2] },
    { vessel: 'GOLDEN ASCENT', cargo: 'BHP Iron Ore (Australia-China)', voyage: mockAllVoyages[10] },
  ],
  market_vessel_hires: [],
  unassigned_vessels: [],
  unassigned_cargoes: [],
  total_profit: 4986320,
  total_tce: 174520,
  avg_tce: 24934,
};

// ─── Top 3 Portfolios Array ──────────────────────────────────
export const mockPortfolios: PortfolioResult[] = [
  mockPortfolio,   // Rank #1
  mockPortfolio2,  // Rank #2
  mockPortfolio3,  // Rank #3
];

// ─── Bunker Sensitivity ────────────────────────────────────
export const mockBunkerSensitivity: ScenarioPoint[] = [
  { parameter_value: 0.80, total_profit: 6603000, avg_tce: 32100, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 0.85, total_profit: 6403000, avg_tce: 31200, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 0.90, total_profit: 6203000, avg_tce: 30300, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 0.95, total_profit: 6003000, avg_tce: 29400, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 1.00, total_profit: 5803558, avg_tce: 28725, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 1.05, total_profit: 5603000, avg_tce: 28100, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 1.10, total_profit: 5403000, avg_tce: 27000, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 1.15, total_profit: 5203000, avg_tce: 25900, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 1.20, total_profit: 5003000, avg_tce: 24800, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 1.25, total_profit: 4803000, avg_tce: 23700, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 1.30, total_profit: 4603000, avg_tce: 22600, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 1.35, total_profit: 4403000, avg_tce: 21500, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 1.40, total_profit: 4203000, avg_tce: 20400, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 1.50, total_profit: 3803000, avg_tce: 18200, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
];

// ─── Port Delay Sensitivity ────────────────────────────────
export const mockPortDelaySensitivity: ScenarioPoint[] = [
  { parameter_value: 0, total_profit: 5803558, avg_tce: 28725, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 1, total_profit: 5703000, avg_tce: 28200, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 2, total_profit: 5603000, avg_tce: 27600, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 3, total_profit: 5503000, avg_tce: 27000, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 4, total_profit: 5403000, avg_tce: 26400, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 5, total_profit: 5303000, avg_tce: 25800, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 6, total_profit: 5203000, avg_tce: 25200, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 7, total_profit: 5103000, avg_tce: 24600, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 8, total_profit: 5003000, avg_tce: 24000, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 10, total_profit: 4803000, avg_tce: 22800, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 12, total_profit: 4603000, avg_tce: 21600, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 15, total_profit: 4303000, avg_tce: 20000, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
];

// ─── Tipping Points ────────────────────────────────────────
export const mockTippingPoints: TippingPoint[] = [
  { parameter: 'Bunker Price', value: 1.18, description: 'At 118% of current bunker prices, the arbitrage strategy becomes less profitable due to increased fuel costs.', profit_before: 5803558, profit_after: 5103000 },
  { parameter: 'Port Delay', value: 5.5, description: 'At 5.5 extra days of port delay, extended waiting times reduce overall portfolio profitability.', profit_before: 5803558, profit_after: 5253000 },
];

// ─── Extended Tipping Points (with assignment details) ─────────
export const mockTippingPointsExtended: Record<string, TippingPointExtended> = {
  bunker: {
    parameter: 'Bunker Price',
    value: 1.18,
    description: 'At 118% of current bunker prices, increased fuel costs reduce arbitrage profitability.',
    profit_before: 5803558,
    profit_after: 5103000,
    current_best_assignments: [
      { vessel: 'Ann Bell', cargo: 'Vale Malaysia Iron Ore', profit: 915509, tce: 22614 },
      { vessel: 'Ocean Horizon', cargo: 'BHP Iron Ore (S.Korea)', profit: 350978, tce: 27036 },
      { vessel: 'Pacific Glory', cargo: 'Teck Coking Coal', profit: 708408, tce: 29426 },
      { vessel: 'Golden Ascent', cargo: 'Adaro Coal', profit: 1169745, tce: 35181 },
    ],
    next_best_assignments: [
      { vessel: 'Ann Bell', cargo: 'Vale Malaysia Iron Ore', profit: 815000, tce: 20100 },
      { vessel: 'Ocean Horizon', cargo: 'BHP Iron Ore (S.Korea)', profit: 280000, tce: 24500 },
      { vessel: 'Pacific Glory', cargo: 'Teck Coking Coal', profit: 608000, tce: 26900 },
      { vessel: 'Golden Ascent', cargo: 'Adaro Coal', profit: 1070000, tce: 32600 },
    ],
  },
  port_delay: {
    parameter: 'Port Delay',
    value: 5.5,
    description: 'At +5.5 days delay, extended waiting times reduce overall portfolio profitability.',
    profit_before: 5803558,
    profit_after: 5253000,
    current_best_assignments: [
      { vessel: 'Ann Bell', cargo: 'Vale Malaysia Iron Ore', profit: 915509, tce: 22614 },
      { vessel: 'Ocean Horizon', cargo: 'BHP Iron Ore (S.Korea)', profit: 350978, tce: 27036 },
      { vessel: 'Pacific Glory', cargo: 'Teck Coking Coal', profit: 708408, tce: 29426 },
      { vessel: 'Golden Ascent', cargo: 'Adaro Coal', profit: 1169745, tce: 35181 },
    ],
    next_best_assignments: [
      { vessel: 'Ann Bell', cargo: 'Vale Malaysia Iron Ore', profit: 815000, tce: 20100 },
      { vessel: 'Ocean Horizon', cargo: 'BHP Iron Ore (S.Korea)', profit: 300000, tce: 25000 },
      { vessel: 'Pacific Glory', cargo: 'Teck Coking Coal', profit: 650000, tce: 27500 },
      { vessel: 'Golden Ascent', cargo: 'Adaro Coal', profit: 1100000, tce: 33500 },
    ],
  },
};

// ─── China-Specific Port Delay Sensitivity ────────────────────
export const mockChinaDelaySensitivity: ScenarioPoint[] = [
  { parameter_value: 0, total_profit: 5803558, avg_tce: 28725, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 0.5, total_profit: 5753000, avg_tce: 28450, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 1, total_profit: 5703000, avg_tce: 28175, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 1.5, total_profit: 5653000, avg_tce: 27900, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 2, total_profit: 5603000, avg_tce: 27625, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 2.5, total_profit: 5553000, avg_tce: 27350, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 3, total_profit: 5503000, avg_tce: 27075, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 3.5, total_profit: 5453000, avg_tce: 26800, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 4, total_profit: 5403000, avg_tce: 26525, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 4.5, total_profit: 5353000, avg_tce: 26250, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 5, total_profit: 5303000, avg_tce: 25975, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 5.5, total_profit: 5253000, avg_tce: 25700, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 6, total_profit: 5203000, avg_tce: 25425, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 7, total_profit: 5103000, avg_tce: 24875, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 8, total_profit: 5003000, avg_tce: 24325, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 9, total_profit: 4903000, avg_tce: 23775, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 10, total_profit: 4803000, avg_tce: 23225, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 12, total_profit: 4603000, avg_tce: 22125, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
  { parameter_value: 15, total_profit: 4303000, avg_tce: 20475, assignments: ['Ann Bell→Vale', 'Ocean Horizon→BHP', 'Pacific Glory→Teck', 'Golden Ascent→Adaro'] },
];

// ─── China-Specific Tipping Point ──────────────────────────────
export const mockChinaTippingPoint: TippingPointExtended = {
  parameter: 'Port Delay (China)',
  value: 4.5,
  description: 'At +4.5 days delay in Chinese ports, extended waiting times increase costs and reduce profitability.',
  profit_before: 5803558,
  profit_after: 5353000,
  region: 'China',
  ports_affected: ['Qingdao', 'Lianyungang'],
  current_best_assignments: [
    { vessel: 'Ann Bell', cargo: 'Vale Malaysia Iron Ore', profit: 915509, tce: 22614 },
    { vessel: 'Ocean Horizon', cargo: 'BHP Iron Ore (S.Korea)', profit: 350978, tce: 27036 },
    { vessel: 'Pacific Glory', cargo: 'Teck Coking Coal', profit: 708408, tce: 29426 },
    { vessel: 'Golden Ascent', cargo: 'Adaro Coal', profit: 1169745, tce: 35181 },
  ],
  next_best_assignments: [
    { vessel: 'Ann Bell', cargo: 'Vale Malaysia Iron Ore', profit: 850000, tce: 21000 },
    { vessel: 'Ocean Horizon', cargo: 'BHP Iron Ore (S.Korea)', profit: 310000, tce: 25500 },
    { vessel: 'Pacific Glory', cargo: 'Teck Coking Coal', profit: 660000, tce: 27800 },
    { vessel: 'Golden Ascent', cargo: 'Adaro Coal', profit: 1100000, tce: 33500 },
  ],
};

// ─── Port Delays (ML predictions) ──────────────────────────
export const mockPortDelays: PortDelay[] = [
  { port: 'Qingdao', predicted_delay_days: 3.2, confidence_lower: 1.8, confidence_upper: 4.6, congestion_level: 'medium', model_used: 'ml_model' },
  { port: 'Rizhao', predicted_delay_days: 2.1, confidence_lower: 1.2, confidence_upper: 3.0, congestion_level: 'low', model_used: 'ml_model' },
  { port: 'Caofeidian', predicted_delay_days: 4.5, confidence_lower: 3.1, confidence_upper: 5.9, congestion_level: 'high', model_used: 'ml_model' },
  { port: 'Fangcheng', predicted_delay_days: 2.8, confidence_lower: 1.5, confidence_upper: 4.1, congestion_level: 'medium', model_used: 'ml_model' },
  { port: 'Mundra', predicted_delay_days: 1.4, confidence_lower: 0.8, confidence_upper: 2.0, congestion_level: 'low', model_used: 'ml_model' },
  { port: 'Vizag', predicted_delay_days: 2.6, confidence_lower: 1.4, confidence_upper: 3.8, congestion_level: 'medium', model_used: 'ml_model' },
  { port: 'Lianyungang', predicted_delay_days: 3.0, confidence_lower: 1.6, confidence_upper: 4.4, congestion_level: 'medium', model_used: 'ml_model' },
  { port: 'Port Hedland', predicted_delay_days: 0.8, confidence_lower: 0.3, confidence_upper: 1.3, congestion_level: 'low', model_used: 'ml_model' },
];

// ─── Model Info ────────────────────────────────────────────
export const mockModelInfo: ModelInfo = {
  model_type: 'LightGBM',
  training_date: '2026-01-26',
  metrics: { mae: 0.064, rmse: 0.124, within_1_day: 0.9974, within_2_days: 1.0 },
  feature_importance: [
    { feature: 'portcalls_dry_bulk_rolling7_mean', importance: 0.894 },
    { feature: 'port_capacity_ratio', importance: 0.500 },
    { feature: 'portcalls_dry_bulk_rolling30_mean', importance: 0.070 },
    { feature: 'portcalls_dry_bulk_rolling14_mean', importance: 0.063 },
    { feature: 'import_dry_bulk_rolling7_mean', importance: 0.044 },
    { feature: 'import_dry_bulk_rolling7_sum', importance: 0.028 },
    { feature: 'import_dry_bulk_rolling30_sum', importance: 0.021 },
    { feature: 'portcalls_dry_bulk_rolling30_std', importance: 0.013 },
    { feature: 'cny_proximity_days', importance: 0.011 },
    { feature: 'import_dry_bulk_momentum', importance: 0.009 },
  ],
};

// ─── Heatmap data (vessel x cargo TCE matrix) ──────────────
export const mockHeatmapData = {
  vessels: ['Ann Bell', 'Ocean Horizon', 'Pacific Glory', 'Golden Ascent'],
  cargoes: ['EGA Bauxite', 'BHP Iron Ore', 'CSN Iron Ore'],
  tce: [
    [38120, 19920, 37200],
    [34780, 18440, 33290],
    [38920, 20180, 36120],
    [35910, 16230, 34280],
  ],
  profit: [
    [2464250, 249025, 1627892],
    [2238016, 175750, 1465933],
    [2381798, 223260, 1599822],
    [2332991, 145260, 1601741],
  ],
  feasible: [
    [true, true, false],
    [true, true, true],
    [true, true, false],
    [true, true, true],
  ],
};

// ─── Laycan feasibility grid ───────────────────────────────
export const mockLaycanGrid = mockVessels.map((v, vi) =>
  mockCargoes.map((c, ci) => ({
    vessel: v.name,
    cargo: c.name,
    feasible: mockHeatmapData.feasible[vi][ci],
    arrival: mockAllVoyages[vi * 3 + ci].arrival_date,
    laycan_end: mockAllVoyages[vi * 3 + ci].laycan_end,
    margin: mockAllVoyages[vi * 3 + ci].days_margin,
  }))
);

// ─── Chat mock messages ────────────────────────────────────
export const mockChatMessages: ChatMessage[] = [
  {
    id: '1',
    role: 'assistant',
    content: "Welcome! I'm your maritime analytics assistant. I can help you analyze vessel assignments, run scenario analyses, compare voyages, and explore port congestion predictions. What would you like to know?",
    timestamp: new Date('2026-01-28T10:00:00'),
  },
];

// ─── Seasonal calendar data ────────────────────────────────
export const mockSeasonalEvents = [
  { name: 'Chinese New Year', start: '2026-02-07', end: '2026-02-21', impact: 'high', region: 'China', description: 'Pre-rush congestion 2 weeks before, slowdown during CNY' },
  { name: 'Golden Week', start: '2026-10-01', end: '2026-10-07', impact: 'medium', region: 'China', description: 'Port congestion spike before and after holiday' },
  { name: 'SW Monsoon', start: '2026-06-01', end: '2026-09-30', impact: 'high', region: 'India', description: 'West coast ports (Mundra) see increased delays' },
  { name: 'Typhoon Season', start: '2026-07-01', end: '2026-10-31', impact: 'high', region: 'East Asia', description: 'Port closures and delays across China, Korea, Japan' },
  { name: 'Winter North China', start: '2026-12-01', end: '2027-02-28', impact: 'medium', region: 'North China', description: 'Ice conditions increase delays at Caofeidian, Rizhao' },
  { name: 'Diwali', start: '2026-10-20', end: '2026-10-24', impact: 'low', region: 'India', description: 'Minor port slowdowns in Indian ports' },
];

// ─── Route map data (port coordinates for SVG map) ─────────
export const portCoordinates: Record<string, { lat: number; lng: number }> = {
  'Qingdao': { lat: 36.07, lng: 120.38 },
  'Gwangyang': { lat: 34.93, lng: 127.70 },
  'Fangcheng': { lat: 21.69, lng: 108.35 },
  'Map Ta Phut': { lat: 12.71, lng: 101.15 },
  'Kamsar': { lat: 10.65, lng: -14.60 },
  'Port Hedland': { lat: -20.31, lng: 118.58 },
  'Itaguai': { lat: -22.86, lng: -43.77 },
  'Lianyungang': { lat: 34.60, lng: 119.22 },
  'Singapore': { lat: 1.29, lng: 103.85 },
  'Fujairah': { lat: 25.12, lng: 56.33 },
  'Rotterdam': { lat: 51.92, lng: 4.48 },
  'Gibraltar': { lat: 36.14, lng: -5.35 },
  'Durban': { lat: -29.88, lng: 31.05 },
  'Mundra': { lat: 22.84, lng: 69.72 },
  'Vizag': { lat: 17.69, lng: 83.22 },
  'Caofeidian': { lat: 39.22, lng: 118.53 },
  'Rizhao': { lat: 35.38, lng: 119.53 },
  // Market cargo ports
  'Tubarao': { lat: -20.28, lng: -40.25 },
  'Port Klang': { lat: 3.00, lng: 101.39 },
  'Vancouver': { lat: 49.29, lng: -123.11 },
  'Taboneo': { lat: -3.52, lng: 114.55 },
  'Hong Kong': { lat: 22.30, lng: 114.17 },
  'Panama': { lat: 9.00, lng: -79.52 },
};

// ─── Suggested chatbot prompts ─────────────────────────────
export const suggestedPrompts = [
  'What is the optimal vessel assignment?',
  'Explain the arbitrage strategy',
  'What if bunker prices rise 20%?',
  'Compare vessels for EGA Bauxite',
  'Which ports have highest congestion?',
  'What are the tipping points?',
];

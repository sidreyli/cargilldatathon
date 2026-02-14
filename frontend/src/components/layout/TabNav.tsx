import { LayoutDashboard, Ship, SlidersHorizontal, Brain } from 'lucide-react';
import type { TabId } from '../../types';

interface TabNavProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  useMLDelays: boolean;
  onToggleMLDelays: (value: boolean) => void;
}

const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard className="w-4 h-4" /> },
  { id: 'voyages', label: 'Voyages', icon: <Ship className="w-4 h-4" /> },
  { id: 'scenarios', label: 'Scenarios', icon: <SlidersHorizontal className="w-4 h-4" /> },
  { id: 'ml', label: 'ML Insights', icon: <Brain className="w-4 h-4" /> },
];

export default function TabNav({ activeTab, onTabChange, useMLDelays, onToggleMLDelays }: TabNavProps) {
  return (
    <nav className="border-b border-border bg-white px-3 md:px-6">
      <div className="flex flex-wrap gap-1 items-center overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`flex items-center gap-1.5 md:gap-2 px-2.5 md:px-4 py-2.5 md:py-3 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === tab.id
                ? 'text-ocean-600 border-ocean-500'
                : 'text-text-secondary border-transparent hover:text-navy-700 hover:border-border'
            }`}
          >
            {tab.icon}
            <span className="hidden md:inline">{tab.label}</span>
          </button>
        ))}

        {/* ML Port Disruption Toggle */}
        <div className="ml-2 md:ml-4 flex items-center gap-2 md:gap-3 py-2">
          <span className="text-xs font-medium text-[#6B7B8D] hidden md:inline">Port Disruption</span>
          <button
            role="switch"
            aria-checked={useMLDelays}
            aria-label="Toggle ML-predicted port delays"
            onClick={() => onToggleMLDelays(!useMLDelays)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 ${
              useMLDelays
                ? 'bg-[#E57373] focus:ring-[#E57373]'
                : 'bg-gray-300 focus:ring-gray-400'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform ${
                useMLDelays ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
          {useMLDelays && (
            <span className="text-xs font-semibold text-[#E57373] bg-[#E57373]/10 px-2 py-0.5 rounded hidden sm:inline">
              ML Active
            </span>
          )}
        </div>
      </div>
    </nav>
  );
}

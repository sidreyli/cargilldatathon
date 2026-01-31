import { LayoutDashboard, Ship, SlidersHorizontal, Brain } from 'lucide-react';
import type { TabId } from '../../types';

interface TabNavProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  portDisruption: boolean;
  onPortDisruptionChange: (value: boolean) => void;
}

const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard className="w-4 h-4" /> },
  { id: 'voyages', label: 'Voyages', icon: <Ship className="w-4 h-4" /> },
  { id: 'scenarios', label: 'Scenarios', icon: <SlidersHorizontal className="w-4 h-4" /> },
  { id: 'ml', label: 'ML Insights', icon: <Brain className="w-4 h-4" /> },
];

export default function TabNav({ activeTab, onTabChange, portDisruption, onPortDisruptionChange }: TabNavProps) {
  return (
    <nav className="border-b border-border bg-white px-6">
      <div className="flex items-center gap-6">
        {/* Tabs */}
        <div className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors border-b-2 -mb-px ${
                activeTab === tab.id
                  ? 'text-ocean-600 border-ocean-500'
                  : 'text-text-secondary border-transparent hover:text-navy-700 hover:border-border'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {/* Port Disruption Toggle - right beside ML Insights */}
        <div className="flex items-center gap-2 pl-2 border-l border-gray-200">
          <span className="text-xs font-medium text-[#6B7B8D]">Port Disruption</span>
          <button
            onClick={() => onPortDisruptionChange(!portDisruption)}
            className={`relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
              portDisruption ? 'bg-[#E57373]' : 'bg-gray-300'
            }`}
            role="switch"
            aria-checked={portDisruption}
            aria-label="Toggle port disruption mode"
          >
            <span
              className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                portDisruption ? 'translate-x-4' : 'translate-x-0'
              }`}
            />
          </button>
          {portDisruption && (
            <span className="text-xs text-[#E57373] font-medium">Active</span>
          )}
        </div>
      </div>
    </nav>
  );
}

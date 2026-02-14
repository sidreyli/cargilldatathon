import { useState, useEffect } from 'react';
import { MessageSquare, X } from 'lucide-react';
import Header from './components/layout/Header';
import TabNav from './components/layout/TabNav';
import DashboardPage from './components/dashboard/DashboardPage';
import VoyagesPage from './components/voyages/VoyagesPage';
import ScenariosPage from './components/scenarios/ScenariosPage';
import MLInsightsPage from './components/ml/MLInsightsPage';
import ChatPanel from './components/chat/ChatPanel';
import type { TabId } from './types';

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>('dashboard');
  const [useMLDelays, setUseMLDelays] = useState(false);
  const [selectedPortfolioIndex, setSelectedPortfolioIndex] = useState(0);
  const [isChatOpen, setIsChatOpen] = useState(false);

  // Reset portfolio selection when ML mode changes
  useEffect(() => {
    setSelectedPortfolioIndex(0);
  }, [useMLDelays]);

  const renderPage = () => {
    switch (activeTab) {
      case 'dashboard':
        return <DashboardPage useMLDelays={useMLDelays} />;
      case 'voyages':
        return <VoyagesPage useMLDelays={useMLDelays} />;
      case 'scenarios':
        return <ScenariosPage />;
      case 'ml':
        return <MLInsightsPage />;
    }
  };

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Header />
      <TabNav
        activeTab={activeTab}
        onTabChange={setActiveTab}
        useMLDelays={useMLDelays}
        onToggleMLDelays={setUseMLDelays}
      />
      <div className="flex flex-1 overflow-hidden">
        <main className="flex-1 overflow-y-auto bg-cloud p-3 md:p-6">
          {renderPage()}
        </main>
        {/* Desktop: always visible sidebar */}
        <div className="hidden md:flex">
          <ChatPanel />
        </div>
        {/* Mobile: full-screen overlay */}
        {isChatOpen && (
          <div className="fixed inset-0 z-40 md:hidden">
            <div className="absolute inset-0 bg-black/40" onClick={() => setIsChatOpen(false)} />
            <div className="absolute inset-0 z-10">
              <ChatPanel onClose={() => setIsChatOpen(false)} />
            </div>
          </div>
        )}
      </div>
      {/* Mobile FAB */}
      <button
        onClick={() => setIsChatOpen(o => !o)}
        className="md:hidden fixed bottom-4 right-4 z-50 w-14 h-14 rounded-full bg-ocean-500 text-white shadow-lg flex items-center justify-center hover:bg-ocean-600 transition-colors"
        aria-label="Toggle chat"
      >
        {isChatOpen ? <X className="w-6 h-6" /> : <MessageSquare className="w-6 h-6" />}
      </button>
    </div>
  );
}

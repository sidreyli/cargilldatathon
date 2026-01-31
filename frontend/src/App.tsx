import { useState, useEffect } from 'react';
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
        <main className="flex-1 overflow-y-auto bg-cloud p-6">
          {renderPage()}
        </main>
        <ChatPanel />
      </div>
    </div>
  );
}

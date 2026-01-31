import { useState } from 'react';
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
  const [portDisruption, setPortDisruption] = useState(false);

  const renderPage = () => {
    switch (activeTab) {
      case 'dashboard':
        return <DashboardPage portDisruption={portDisruption} />;
      case 'voyages':
        return <VoyagesPage />;
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
        portDisruption={portDisruption}
        onPortDisruptionChange={setPortDisruption}
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

import React, { useState, useEffect, useContext } from 'react';
import { TabId, TabItem } from './types';
import OverviewRating from './free/OverviewRating';
import AdvancedSettingsManager from './premium/AdvancedSettingsManager';
import ProfileEditor from './free/ProfileEditor';
import AppearanceRating from './premium/AppearanceRating';
import axios from 'axios';
import { toast } from 'react-hot-toast';
import { SidebarContext } from '../../App';

export default function RatingContainer() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [isPremium, setIsPremium] = useState<boolean>(false);
  const [isWalletLocked, setIsWalletLocked] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const { setIsExpanded } = useContext(SidebarContext);

  // Fetch premium status on component mount
  useEffect(() => {
    checkPremiumStatus();
  }, []);

  // Effect to hide sidebar when on Appearance tab
  useEffect(() => {
    // إخفاء السايدبار عند الانتقال إلى علامة التبويب Appearance
    if (activeTab === 'appearance') {
      document.body.classList.add('hide-sidebar');
      // تغيير حالة السايدبار في سياق التطبيق
      const appElement = document.getElementById('root');
      if (appElement) {
        appElement.classList.add('hide-layout');
      }
    } else {
      document.body.classList.remove('hide-sidebar');
      // إعادة حالة السايدبار في سياق التطبيق
      const appElement = document.getElementById('root');
      if (appElement) {
        appElement.classList.remove('hide-layout');
      }
    }

    // تنظيف عند إزالة المكون
    return () => {
      document.body.classList.remove('hide-sidebar');
      const appElement = document.getElementById('root');
      if (appElement) {
        appElement.classList.remove('hide-layout');
      }
    };
  }, [activeTab]);

  // Check if user has premium access
  const checkPremiumStatus = async () => {
    try {
      setIsLoading(true);
      const response = await axios.get('/api/premium/check');
      if (response.data) {
        setIsPremium(response.data.premium);
        setIsWalletLocked(response.data.wallet_lock);
      }
    } catch (error) {
      console.error('Error checking premium status:', error);
      toast.error('Failed to verify premium status');
    } finally {
      setIsLoading(false);
    }
  };

  const tabs: TabItem[] = [
    { id: 'overview', label: 'Overview', isPremium: false },
    { id: 'profile', label: 'Profile', isPremium: false },
    { id: 'advanced', label: 'Advanced Settings', isPremium: true },
    { id: 'appearance', label: 'Appearance', isPremium: true },
  ];

  // تغيير علامة التبويب النشطة مع إضافة منطق إخفاء/إظهار السايدبار
  const handleTabChange = (tabId: TabId) => {
    setActiveTab(tabId);
  };

  const renderTabContent = () => {
    // Show loading state
    if (isLoading) {
      return <LoadingState />;
    }
    
    // Show wallet locked message if wallet is locked
    if (isWalletLocked) {
      return <WalletLockedMessage />;
    }

    // Render appropriate tab content
    switch (activeTab) {
      case 'overview':
        return <OverviewRating />;
      case 'profile':
        return <ProfileEditor />;
      case 'advanced':
        return isPremium ? <AdvancedSettingsManager /> : <PremiumLockMessage />;
      case 'appearance':
        return isPremium ? <AppearanceRating /> : <PremiumLockMessage />;
      default:
        return <OverviewRating />;
    }
  };

  return (
    <div className="min-h-screen bg-[#262626]">
      <div className="container mx-auto px-4 py-6">
        {/* Tab Navigation */}
        <div className="mb-6">
          <div className="border-b border-[#393939]">
            {/* On larger screens, all tabs in one row */}
            <div className="hidden min-[551px]:flex">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => handleTabChange(tab.id)}
                  className={`flex items-center justify-center gap-2 py-4 px-5 text-base font-medium relative ${
                    activeTab === tab.id
                      ? 'text-blue-500'
                      : 'text-gray-400 hover:text-blue-400'
                  }`}
                  disabled={isLoading || (isWalletLocked && tab.id !== 'overview')}
                >
                  <span>{tab.label}</span>
                  {tab.isPremium && (
                    <span className="ml-1 px-1.5 py-0.5 bg-gradient-to-r from-amber-500 to-yellow-700 text-white text-[10px] font-bold rounded-full">
                      PRO
                    </span>
                  )}
                  {activeTab === tab.id && (
                    <div className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-500"></div>
                  )}
                </button>
              ))}
            </div>

            {/* On smaller screens (< 550px), two rows */}
            <div className="flex flex-col max-[550px]:flex min-[551px]:hidden">
              {/* First row */}
              <div className="flex">
                {tabs.slice(0, 2).map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => handleTabChange(tab.id)}
                    className={`flex items-center justify-center gap-2 py-4 px-5 text-base font-medium relative flex-1 ${
                      activeTab === tab.id
                        ? 'text-blue-500'
                        : 'text-gray-400 hover:text-blue-400'
                    }`}
                    disabled={isLoading || (isWalletLocked && tab.id !== 'overview')}
                  >
                    <span>{tab.label}</span>
                    {tab.isPremium && (
                      <span className="ml-1 px-1.5 py-0.5 bg-gradient-to-r from-amber-500 to-yellow-700 text-white text-[10px] font-bold rounded-full">
                        PRO
                      </span>
                    )}
                    {activeTab === tab.id && (
                      <div className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-500"></div>
                    )}
                  </button>
                ))}
              </div>

              {/* Second row */}
              <div className="flex">
                {tabs.slice(2).map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => handleTabChange(tab.id)}
                    className={`flex items-center justify-center gap-2 py-4 px-5 text-base font-medium relative flex-1 ${
                      activeTab === tab.id
                        ? 'text-blue-500'
                        : 'text-gray-400 hover:text-blue-400'
                    }`}
                    disabled={isLoading || (isWalletLocked && tab.id !== 'overview')}
                  >
                    <span>{tab.label}</span>
                    {tab.isPremium && (
                      <span className="ml-1 px-1.5 py-0.5 bg-gradient-to-r from-amber-500 to-yellow-700 text-white text-[10px] font-bold rounded-full">
                        PRO
                      </span>
                    )}
                    {activeTab === tab.id && (
                      <div className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-500"></div>
                    )}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Tab Content */}
        <div>
          {renderTabContent()}
        </div>
      </div>
    </div>
  );
}

// Loading state component
function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="animate-pulse flex flex-col items-center">
        <div className="h-12 w-12 bg-blue-500/20 rounded-full mb-4"></div>
        <div className="h-4 w-32 bg-gray-700 rounded mb-3"></div>
        <div className="h-3 w-48 bg-gray-600 rounded"></div>
      </div>
    </div>
  );
}

// Wallet locked message component
function WalletLockedMessage() {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="bg-red-500/20 p-3 rounded-full mb-4">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#EF4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
          <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
        </svg>
      </div>
      <h3 className="text-xl font-bold text-white mb-2">Wallet Locked</h3>
      <p className="text-gray-400 text-center max-w-md mb-6">
        Your wallet is currently locked. Please unlock your wallet to access ratings features.
      </p>
      <button className="bg-red-500 hover:bg-red-600 text-white font-medium py-2 px-6 rounded-lg transition-colors">
        Unlock Wallet
      </button>
    </div>
  );
}

// Premium lock message component
function PremiumLockMessage() {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="bg-blue-500/20 p-3 rounded-full mb-4">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
          <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
        </svg>
      </div>
      <h3 className="text-xl font-bold text-white mb-2">Premium Feature</h3>
      <p className="text-gray-400 text-center max-w-md mb-6">
        This feature is only available to premium users. Upgrade your account to access advanced settings.
      </p>
      <button className="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-6 rounded-lg transition-colors">
        Upgrade to Premium
      </button>
    </div>
  );
} 
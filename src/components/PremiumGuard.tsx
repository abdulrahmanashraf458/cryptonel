import React, { useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { usePremium } from '../contexts/PremiumContext';
import { Lock } from 'lucide-react';

interface PremiumGuardProps {
  children: React.ReactNode;
}

/**
 * Component that guards premium routes and redirects non-premium users
 * يحمي الصفحات البريميوم ويوجه المستخدمين غير البريميوم لصفحة الترقية
 */
const PremiumGuard: React.FC<PremiumGuardProps> = ({ children }) => {
  const { isPremium, isWalletLocked, isLoading } = usePremium();
  const location = useLocation();

  // If still loading, show a loading spinner
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-10 h-10 border-4 border-[#8875FF] border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  // If wallet is locked, redirect to overview
  if (isWalletLocked) {
    return (
      <Navigate 
        to="/overview" 
        state={{ from: location, walletLocked: true }} 
        replace 
      />
    );
  }

  // If not premium, show upgrade message
  if (!isPremium) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-4">
        <div className="flex flex-col items-center bg-[#333333] rounded-lg p-6 max-w-md w-full shadow-lg border border-[#444444]">
          <div className="w-16 h-16 bg-amber-500/20 rounded-full flex items-center justify-center mb-4">
            <Lock size={32} className="text-amber-500" />
          </div>
          
          <h2 className="text-xl font-bold mb-2 text-white">Premium Feature</h2>
          
          <p className="text-center text-[#BBBBBB] mb-4">
            This feature is only available for Premium members.
            Upgrade your account to access this and other exclusive features.
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full mt-2">
            <button 
              onClick={() => window.history.back()}
              className="px-4 py-2 bg-[#444444] hover:bg-[#555555] text-white rounded-lg transition-colors"
            >
              Go Back
            </button>
            
            <button 
              onClick={() => window.location.href = '/wallet/settings?tab=premium'}
              className="px-4 py-2 bg-gradient-to-r from-amber-500 to-amber-700 hover:from-amber-600 hover:to-amber-800 text-white rounded-lg transition-colors font-medium"
            >
              Upgrade Now
            </button>
          </div>
        </div>
      </div>
    );
  }

  // If premium, render the children
  return <>{children}</>;
};

export default PremiumGuard; 
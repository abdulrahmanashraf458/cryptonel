import React, { createContext, useContext, ReactNode } from 'react';
import usePremiumStatus, { PremiumStatus } from '../hooks/usePremiumStatus';

// Default context value
const defaultContextValue: PremiumStatus & { refreshStatus: () => Promise<void> } = {
  isPremium: false,
  isWalletLocked: false,
  membership: 'standard',
  accountType: 'Standard User',
  isLoading: true,
  error: null,
  refreshStatus: async () => {},
};

// Create context
export const PremiumContext = createContext(defaultContextValue);

// Premium provider component
interface PremiumProviderProps {
  children: ReactNode;
}

export const PremiumProvider: React.FC<PremiumProviderProps> = ({ children }) => {
  // Use the hook to get premium status with strict boolean checking
  const premiumStatus = usePremiumStatus();
  
  return (
    <PremiumContext.Provider value={premiumStatus}>
      {children}
    </PremiumContext.Provider>
  );
};

// Custom hook to use premium context
export const usePremium = () => useContext(PremiumContext);

// Helper hook to check if user has premium access
export const usePremiumAccess = () => {
  const { isPremium, isLoading, error } = usePremium();
  return {
    // Strict boolean check to ensure premium is exactly true
    hasPremium: isPremium === true,
    isLoading,
    error
  };
};

export default PremiumProvider; 
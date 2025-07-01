import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

export interface PremiumStatus {
  isPremium: boolean;
  isWalletLocked: boolean; // Refers to wallet_lock status only, not frozen status
  membership: string;
  accountType: string;
  isLoading: boolean;
  error: string | null;
}

/**
 * Hook to check and manage premium status
 * IMPORTANT: This hook strictly uses the premium boolean field as the source of truth
 */
export default function usePremiumStatus(): PremiumStatus & { refreshStatus: () => Promise<void> } {
  const [status, setStatus] = useState<PremiumStatus>({
    isPremium: false,
    isWalletLocked: false,
    membership: 'standard',
    accountType: 'Standard User',
    isLoading: true,
    error: null
  });

  const checkPremiumStatus = useCallback(async () => {
    try {
      setStatus(prev => ({ ...prev, isLoading: true, error: null }));
      
      const response = await axios.get('/api/premium/check', {
        headers: {
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache',
          'Expires': '0'
        }
      });
      
      if (response.data.success) {
        // Store premium status in session storage
        sessionStorage.setItem('premium_status', JSON.stringify({
          isPremium: response.data.premium === true, // Strict boolean check
          membershipType: response.data.membership,
          lastChecked: new Date().toISOString()
        }));
        
        // Update state with the response
        setStatus({
          isPremium: response.data.premium === true, // Strict boolean check
          isWalletLocked: response.data.wallet_lock === true, // Only wallet_lock, not frozen
          membership: response.data.membership || 'standard',
          accountType: response.data.account_type || 'Standard User',
          isLoading: false,
          error: null
        });
        
        // If settings were reset due to premium status change, log it
        if (response.data.settings_reset) {
          console.log("Premium settings were reset due to status change");
        }
      } else {
        throw new Error(response.data.message || 'Failed to check premium status');
      }
    } catch (error) {
      console.error("Error checking premium status:", error);
      
      // Try to get from session storage as fallback
      const cachedStatus = sessionStorage.getItem('premium_status');
      if (cachedStatus) {
        try {
          const parsed = JSON.parse(cachedStatus);
          setStatus({
            isPremium: parsed.isPremium === true, // Strict boolean check
            isWalletLocked: false, // Default to false when using cached data
            membership: parsed.membershipType || 'standard',
            accountType: 'Standard User',
            isLoading: false,
            error: 'Using cached data due to API error'
          });
          return;
        } catch (e) {
          // Ignore parse errors
        }
      }
      
      setStatus(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Unknown error checking premium status'
      }));
    }
  }, []);

  // Check premium status on mount
  useEffect(() => {
    checkPremiumStatus();
  }, [checkPremiumStatus]);

  // Return current status and refresh function
  return {
    ...status,
    refreshStatus: checkPremiumStatus
  };
} 
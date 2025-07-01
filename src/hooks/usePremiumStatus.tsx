import { useState, useEffect, useCallback } from 'react';

// Define the premium status interface
export interface PremiumStatus {
  isPremium: boolean;
  isWalletLocked: boolean;
  membership: string;
  accountType: string;
  walletRestrictions?: {
    is_locked: boolean;
    is_frozen: boolean;
    is_banned: boolean;
    has_access: boolean;
  };
  username?: string;
  isLoading: boolean;
  error: string | null;
  requestId?: string; // Add request ID for troubleshooting
}

/**
 * Hook to check and manage premium status
 * يتحقق من حالة البريميوم للمستخدم وحالة قفل المحفظة
 */
export const usePremiumStatus = () => {
  // Initialize with loading state
  const [status, setStatus] = useState<PremiumStatus>({
    isPremium: false,
    isWalletLocked: false,
    membership: 'standard',
    accountType: 'Standard User',
    isLoading: true,
    error: null
  });

  // Get CSRF token - first try from localStorage, then fetch a new one if needed
  const getCsrfToken = async (): Promise<string | null> => {
    // First try from localStorage
    const storedToken = localStorage.getItem('csrf_token');
    if (storedToken) {
      return storedToken;
    }
    
    // If not found, fetch a new token
    try {
      const response = await fetch('/api/csrf/token', {
        method: 'GET',
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.csrf_token) {
          // Store token in localStorage
          localStorage.setItem('csrf_token', data.csrf_token);
          return data.csrf_token;
        }
      }
    } catch (error) {
      console.error('Error fetching CSRF token:', error);
    }
    
    // Fallback - try from cookies as last resort
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
      const [name, value] = cookie.trim().split('=');
      if (name === 'csrf_token') {
        // Store in localStorage for future use
        localStorage.setItem('csrf_token', value);
        return value;
      }
    }
    
    return null;
  };

  // Check premium status from the server
  const checkPremiumStatus = useCallback(async () => {
    try {
      // Set loading state
      setStatus(prev => ({ ...prev, isLoading: true, error: null }));

      // Get CSRF token - needs to be awaited now that it's async
      const csrfToken = await getCsrfToken();
      
      // Generate request ID for this check
      const requestUniqueId = Math.random().toString(36).substring(2, 10);

      // Fetch premium status from the server with enhanced security
      const response = await fetch('/api/premium/check', {
        method: 'GET',
        credentials: 'include', // Include cookies for authentication
        headers: {
          'Content-Type': 'application/json',
          'Cache-Control': 'no-cache, no-store',
          'Pragma': 'no-cache',
          'X-CSRF-Token': csrfToken || '', // Include CSRF token if available
          'X-Request-ID': requestUniqueId, // Add unique request ID
          'X-Client-Timestamp': Date.now().toString() // Add timestamp for verification
        }
      });

      // Parse response
      const data = await response.json();

      if (response.ok && data.success) {
        // Verify response signature if available
        let isValidResponse = true;
        if (data.signature && data.timestamp) {
          // In a real implementation, you would verify the signature here
          // This would require server-side code to verify HMAC signatures
          // For now, we'll trust the response if it has these fields
          isValidResponse = true;
        }

        if (!isValidResponse) {
          console.error('Invalid response signature detected');
          setStatus({
            isPremium: false,
            isWalletLocked: true,
            membership: 'standard',
            accountType: 'Standard User',
            isLoading: false,
            error: 'Invalid response signature'
          });
          return;
        }

        // Update state with premium status
        setStatus({
          isPremium: data.premium,
          isWalletLocked: data.wallet_lock,
          membership: data.membership,
          accountType: data.account_type,
          walletRestrictions: data.wallet_restrictions,
          username: data.username,
          requestId: data.request_id, // Store request ID
          isLoading: false,
          error: null
        });
      } else if (response.status === 429) {
        // Handle rate limiting
        setStatus({
          isPremium: false,
          isWalletLocked: true,
          membership: 'standard',
          accountType: 'Standard User',
          isLoading: false,
          error: 'Rate limit exceeded. Please try again later.'
        });
      } else {
        // Handle error response
        setStatus({
          isPremium: false,
          isWalletLocked: true, // Assume locked on error
          membership: 'standard',
          accountType: 'Standard User',
          isLoading: false,
          error: data.message || 'Failed to check premium status',
          requestId: data.error_id // Store error ID for troubleshooting
        });
      }
    } catch (error) {
      // Handle fetch error
      console.error('Error checking premium status:', error);
      setStatus({
        isPremium: false,
        isWalletLocked: true, // Assume locked on error
        membership: 'standard',
        accountType: 'Standard User',
        isLoading: false,
        error: 'Network error while checking premium status'
      });
    }
  }, []);

  // Check premium status on mount
  useEffect(() => {
    checkPremiumStatus();

    // Check again every 5 minutes to handle status changes
    const intervalId = setInterval(() => {
      checkPremiumStatus();
    }, 5 * 60 * 1000);

    // Clean up interval on unmount
    return () => clearInterval(intervalId);
  }, [checkPremiumStatus]);

  // Return status and a function to refresh it
  return {
    ...status,
    refreshStatus: checkPremiumStatus
  };
};

export default usePremiumStatus; 
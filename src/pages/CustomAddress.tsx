import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  AlertCircle, 
  CheckCircle, 
  Edit, 
  Lock, 
  RefreshCw, 
  Shield, 
  AtSign, 
  Copy, 
  Check,
  Info,
  XCircle,
  Bell
} from 'lucide-react';
import { toast, Toaster } from 'react-hot-toast';

interface CustomAddressState {
  currentAddress: string;
  newAddress: string;
  isLoading: boolean;
  isSubmitting: boolean;
  canChange: boolean;
  error: string;
  success: string;
  cooldownDays: number;
  copied: boolean;
  showAddressUpdateAnimation: boolean;
}

const CustomAddress: React.FC = () => {
  const [state, setState] = useState<CustomAddressState>({
    currentAddress: '',
    newAddress: '',
    isLoading: true,
    isSubmitting: false,
    canChange: false,
    error: '',
    success: '',
    cooldownDays: 0,
    copied: false,
    showAddressUpdateAnimation: false
  });
  const [animate, setAnimate] = useState(false);
  const [csrfToken, setCsrfToken] = useState<string>('');
  
  // Add shimmer animation class
  const shimmer = "relative overflow-hidden before:absolute before:inset-0 before:-translate-x-full before:animate-shimmer before:bg-gradient-to-r before:from-transparent before:via-white/10 before:to-transparent";

  // Load current address data
  useEffect(() => {
    // Fetch CSRF token first
    const fetchCsrfToken = async () => {
      try {
        console.log('Fetching CSRF token...');
        const response = await fetch('/api/csrf-token', {
          credentials: 'include'
        });
        
        console.log('CSRF token response status:', response.status);
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('CSRF token response data:', data);
        
        if (data.success && data.csrf_token) {
          console.log('CSRF token received successfully');
          setCsrfToken(data.csrf_token);
        } else {
          console.error('CSRF token fetch failed:', data.error || 'Unknown error');
          showErrorToast('Security token initialization failed. Please refresh.');
        }
      } catch (error) {
        console.error('CSRF token fetch error:', error);
        showErrorToast('Security token initialization failed. Please refresh.');
      }
    };

    const initializeData = async () => {
      await fetchCsrfToken();
      await fetchAddressInfo();
    };

    initializeData();
    
    // Add animation after loading
    setTimeout(() => {
      setAnimate(true);
    }, 100);
  }, []);

  const fetchAddressInfo = async () => {
    setState(prev => ({ ...prev, isLoading: true, error: '' }));
    try {
      const response = await fetch('/api/custom-address/info', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        credentials: 'include'
      });

      const data = await response.json();
      
      if (response.ok && data.success) {
        setState(prev => ({
          ...prev, 
          currentAddress: data.current_address || '',
          canChange: data.can_change || false,
          cooldownDays: data.cooldown_days || 0,
          isLoading: false
        }));
      } else {
        setState(prev => ({ 
          ...prev, 
          error: data.message || 'Failed to load address information', 
          isLoading: false 
        }));
        showErrorToast('Failed to load address information');
      }
    } catch (error) {
      setState(prev => ({ 
        ...prev, 
        error: 'Network error. Please try again later.', 
        isLoading: false 
      }));
      showErrorToast('Network error. Please try again later.');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Check if CSRF token is available
    if (!csrfToken) {
      console.error('CSRF token not available');
      setState(prev => ({ ...prev, error: 'Security token not available. Please refresh the page and try again.' }));
      showErrorToast('Security token not available. Please refresh the page and try again.');
      return;
    }
    
    console.log('Submitting with CSRF token:', csrfToken.substring(0, 20) + '...');
    
    // Basic validation
    if (!state.newAddress || state.newAddress.trim() === '') {
      setState(prev => ({ ...prev, error: 'Please enter a new address' }));
      return;
    }

    // Validate lowercase English letters only
    if (!/^[a-z]{3,32}$/.test(state.newAddress)) {
      setState(prev => ({ 
        ...prev, 
        error: 'Address must contain only lowercase English letters (a-z), be 3-32 characters long, and cannot contain spaces or special characters.' 
      }));
      return;
    }

    // Prevent changing to the same address
    if (state.newAddress === state.currentAddress) {
      setState(prev => ({ ...prev, error: 'New address must be different from current address' }));
      return;
    }

    setState(prev => ({ ...prev, isSubmitting: true, error: '', success: '' }));
    
    try {
      console.log('Sending update request...');
      const response = await fetch('/api/custom-address/update', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'X-CSRF-Token': csrfToken
        },
        body: JSON.stringify({ new_address: state.newAddress }),
        credentials: 'include'
      });

      console.log('Update response status:', response.status);
      const data = await response.json();
      console.log('Update response data:', data);
      
      if (response.ok && data.success) {
        // Set animation state for updated address
        setState(prev => ({
          ...prev,
          isSubmitting: false,
          canChange: false,
          success: 'Your private address has been successfully updated!',
          error: '',
          showAddressUpdateAnimation: true
        }));
        
        // Show animation then update address after a delay
        setTimeout(() => {
          setState(prev => ({
            ...prev,
            currentAddress: state.newAddress,
            newAddress: '',
            showAddressUpdateAnimation: false
          }));
        }, 1500);
      } else {
        // Handle specific error cases
        let errorMessage = data.message || 'Failed to update address';
        
        // Handle CSRF-related errors
        if (response.status === 403) {
          if (data.error && data.error.includes('CSRF')) {
            errorMessage = 'Security validation failed. Please refresh the page and try again.';
            // Clear the invalid token
            setCsrfToken('');
            
            // Try to refresh the token automatically
            const tokenRefreshed = await refreshCsrfToken();
            if (tokenRefreshed) {
              // Retry the request with the new token
              setState(prev => ({ ...prev, isSubmitting: true, error: '' }));
              
              try {
                const retryResponse = await fetch('/api/custom-address/update', {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                    'X-CSRF-Token': csrfToken
                  },
                  body: JSON.stringify({ new_address: state.newAddress }),
                  credentials: 'include'
                });

                const retryData = await retryResponse.json();
                
                if (retryResponse.ok && retryData.success) {
                  // Success on retry
                  setState(prev => ({
                    ...prev,
                    isSubmitting: false,
                    canChange: false,
                    success: 'Your private address has been successfully updated!',
                    error: '',
                    showAddressUpdateAnimation: true
                  }));
                  
                  setTimeout(() => {
                    setState(prev => ({
                      ...prev,
                      currentAddress: state.newAddress,
                      newAddress: '',
                      showAddressUpdateAnimation: false
                    }));
                  }, 1500);
                  return; // Exit early on success
                } else {
                  // Still failed on retry
                  errorMessage = retryData.message || 'Failed to update address after retry';
                }
              } catch (retryError) {
                errorMessage = 'Network error during retry. Please try again later.';
              }
            }
          }
        }
        
        // Handle race condition (409 Conflict)
        if (response.status === 409) {
          errorMessage = data.message || 'This address was just claimed by another user. Please choose a different one.';
        }
        
        setState(prev => ({ 
          ...prev, 
          error: errorMessage, 
          isSubmitting: false 
        }));
        
        // Only show toast for errors if there's no visible error message
        if (!state.error) {
          showErrorToast(errorMessage);
        }
      }
    } catch (error) {
      console.error('Network error during update:', error);
      setState(prev => ({ 
        ...prev, 
        error: 'Network error. Please try again later.', 
        isSubmitting: false 
      }));
      // Only show toast for errors if there's no visible error message
      if (!state.error) {
        showErrorToast('Network error. Please try again later.');
      }
    }
  };

  const showErrorToast = (message: string) => {
    toast.custom((t) => (
      <div className={`${
        t.visible ? 'animate-enter' : 'animate-leave'
      } max-w-md w-full bg-[#2d1f24] border border-red-500/30 shadow-lg rounded-lg pointer-events-auto flex ring-1 ring-black ring-opacity-5 p-4`}>
        <div className="flex-1 w-0 flex items-center">
          <div className="flex-shrink-0 bg-red-600 p-1 rounded-full">
            <AlertCircle className="h-5 w-5 text-white" />
          </div>
          <div className="ml-3 flex-1">
            <p className="text-sm font-medium text-red-100">
              {message}
            </p>
          </div>
          <button
            onClick={() => toast.dismiss(t.id)}
            className="bg-red-700/50 rounded-full p-1 text-red-100 hover:bg-red-600/50 focus:outline-none"
          >
            <XCircle className="h-4 w-4" />
          </button>
        </div>
      </div>
    ), { duration: 4000 });
  };

  const refreshCsrfToken = async () => {
    try {
      console.log('Refreshing CSRF token...');
      const response = await fetch('/api/csrf-token', {
        credentials: 'include'
      });
      
      console.log('Refresh token response status:', response.status);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('Refresh token response data:', data);
      
      if (data.success && data.csrf_token) {
        console.log('CSRF token refreshed successfully');
        setCsrfToken(data.csrf_token);
        return true;
      } else {
        console.error('Failed to refresh CSRF token:', data.error || 'Unknown error');
        return false;
      }
    } catch (error) {
      console.error('Error refreshing CSRF token:', error);
      return false;
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(state.currentAddress);
    setState(prev => ({ ...prev, copied: true }));
    
    // Reset copied state after 2 seconds
    setTimeout(() => {
      setState(prev => ({ ...prev, copied: false }));
    }, 2000);
    
    toast.custom((t) => (
      <div className={`${
        t.visible ? 'animate-enter' : 'animate-leave'
      } max-w-md w-full bg-[#252F3F] border border-indigo-500/30 shadow-lg rounded-lg pointer-events-auto flex ring-1 ring-black ring-opacity-5 p-4`}>
        <div className="flex-1 w-0 flex items-center">
          <div className="flex-shrink-0 bg-indigo-600 p-1 rounded-full">
            <Copy className="h-5 w-5 text-white" />
          </div>
          <div className="ml-3 flex-1">
            <p className="text-sm font-medium text-indigo-100">
              Address copied to clipboard
            </p>
          </div>
          <button
            onClick={() => toast.dismiss(t.id)}
            className="bg-indigo-700/50 rounded-full p-1 text-indigo-100 hover:bg-indigo-600/50 focus:outline-none"
          >
            <XCircle className="h-4 w-4" />
          </button>
        </div>
      </div>
    ), { duration: 2000 });
  };

  return (
    <div className="bg-[#262626] min-h-screen text-white">
      <Toaster position="top-right" />
      <div className="max-w-3xl mx-auto px-4 py-6">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className={`transition-all duration-700 ${animate ? 'translate-y-0 opacity-100' : 'translate-y-10 opacity-0'}`}
        >
          <div className="flex items-start mb-6">
            <div className="bg-[#8B5CF6]/20 p-2 rounded-lg mr-3">
              <AtSign className="w-5 h-5 text-[#9D8DFF]" strokeWidth={2} />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-white">Custom Address</h1>
              <div className="flex items-center mt-1">
                <span className="mr-2 px-1.5 py-0.5 bg-gradient-to-r from-amber-500 to-yellow-700 text-white text-[10px] font-bold rounded-full">
                  PRO
                </span>
                <p className="text-[#C4C4C7] text-sm">
                  Personalize your private address with a unique identifier
                </p>
              </div>
            </div>
          </div>

          {state.isLoading ? (
            <div className="space-y-6">
              {/* Current Address Card Skeleton */}
              <div className={`bg-[#2b2b2b] rounded-2xl p-6 mb-8 border border-[#3A3A3E] shadow-lg`}>
                <div className={`h-5 w-52 bg-[#323234] rounded-md ${shimmer} mb-4`}></div>
                
                {/* Current Address Field Skeleton */}
                <div className={`h-14 bg-[#323234] rounded-xl border border-[#3A3A3E] ${shimmer} mb-6`}></div>
                
                {/* Change Address Section Skeleton */}
                <div className={`h-5 w-60 bg-[#323234] rounded-md ${shimmer} mb-4`}></div>
                
                {/* Address Info Box Skeletons */}
                <div className={`p-4 rounded-xl ${shimmer} mb-4 bg-gradient-to-r from-[#323234] to-[#2d2d2d] border border-[#3A3A3E]`}>
                  <div className="flex items-start">
                    <div className={`w-4 h-4 rounded-full bg-[#3A3A3E] mr-2`}></div>
                    <div className={`h-4 w-40 bg-[#3A3A3E] rounded-md`}></div>
                  </div>
                </div>
                <div className={`p-4 rounded-xl ${shimmer} mb-4 bg-gradient-to-r from-[#323234] to-[#2d2d2d] border border-[#3A3A3E]`}>
                  <div className="flex items-start">
                    <div className={`w-4 h-4 rounded-full bg-[#3A3A3E] mr-2`}></div>
                    <div className={`h-4 w-48 bg-[#3A3A3E] rounded-md`}></div>
                  </div>
                </div>
                
                {/* Input Field Skeleton */}
                <div className={`h-14 bg-[#323234] rounded-xl ${shimmer} mb-4`}></div>
                
                {/* Button Skeleton */}
                <div className={`h-12 bg-[#323234] rounded-xl ${shimmer} mb-6`}></div>
                
                {/* About Section Title Skeleton */}
                <div className={`h-5 w-40 bg-[#323234] rounded-md ${shimmer} mt-8 mb-4`}></div>
                
                {/* Info Cards Skeleton */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className={`p-4 bg-[#323234] rounded-xl border border-[#3A3A3E] ${shimmer}`}>
                      <div className={`w-10 h-10 rounded-lg bg-[#3A3A3E]/60 mb-3 flex items-center justify-center`}>
                        <div className={`w-5 h-5 rounded-full bg-[#8B5CF6]/40`}></div>
                      </div>
                      <div className={`h-4 w-24 bg-[#3A3A3E] rounded-md mb-2`}></div>
                      <div className={`h-3 w-full bg-[#3A3A3E] rounded-md mb-1`}></div>
                      <div className={`h-3 w-2/3 bg-[#3A3A3E] rounded-md`}></div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="bg-[#2b2b2b] rounded-2xl p-6 mb-8 border border-[#3A3A3E] shadow-lg"
            >
              <AnimatePresence>
                {state.error && (
                  <motion.div 
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="mb-4 p-4 bg-gradient-to-r from-red-900/80 to-red-800/50 border border-red-700 rounded-xl flex items-start shadow-md"
                  >
                    <AlertCircle className="text-red-400 mr-2 flex-shrink-0 mt-0.5" size={20} />
                    <p className="text-red-100 text-sm font-medium">{state.error}</p>
                  </motion.div>
                )}

                {state.success && (
                  <motion.div 
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.4, ease: "easeOut" }}
                    className="mb-4 p-4 bg-[#1c3a25] border border-[#28a745]/30 rounded-xl flex items-center shadow-md"
                  >
                    <div className="bg-[#28a745] rounded-full p-1 flex-shrink-0 mr-3">
                      <CheckCircle className="text-white h-5 w-5" />
                    </div>
                    <p className="text-[#baffcd] text-sm font-medium">{state.success}</p>
                  </motion.div>
                )}
              </AnimatePresence>

              <div>
                <h3 className="text-md font-semibold text-[#E5E5E5] mb-3">Your Current Private Address</h3>
                <div className="flex items-center justify-between bg-[#323234] rounded-xl p-4 border border-[#3A3A3E] relative overflow-hidden">
                  {state.showAddressUpdateAnimation && (
                    <motion.div 
                      initial={{ width: 0, opacity: 0.7 }}
                      animate={{ 
                        width: "100%", 
                        opacity: [0.5, 0.8, 0.5],
                        x: ["-5%", "0%"] 
                      }}
                      exit={{ width: 0, opacity: 0 }}
                      transition={{ 
                        duration: 1.2,
                        ease: "easeInOut" 
                      }}
                      className="absolute inset-0 bg-gradient-to-r from-[#28a745]/20 via-[#28a745]/40 to-[#28a745]/10 border-l-4 border-[#28a745] h-full"
                      style={{ 
                        boxShadow: "0 0 20px 5px rgba(40, 167, 69, 0.3)",
                        left: 0,
                        top: 0
                      }}
                    />
                  )}
                  <AnimatePresence mode="wait">
                    <motion.p 
                      key={state.currentAddress}
                      initial={{ opacity: 0, y: -20 }}
                      animate={{ 
                        opacity: 1, 
                        y: 0,
                        scale: state.showAddressUpdateAnimation ? [1, 1.03, 1] : 1
                      }}
                      exit={{ opacity: 0, y: 20 }}
                      transition={{ 
                        duration: 0.5,
                        scale: {
                          duration: 0.8,
                          times: [0, 0.5, 1]
                        }
                      }}
                      className="font-mono text-[#FFFFFF] flex-1 truncate pr-2"
                    >
                      {state.currentAddress}
                    </motion.p>
                  </AnimatePresence>
                  <button 
                    onClick={copyToClipboard}
                    className="p-2 hover:bg-[#3A3A3E] rounded-lg transition-colors ml-2 relative z-20"
                    aria-label="Copy address"
                  >
                    <AnimatePresence mode="wait">
                      {state.copied ? (
                        <motion.div
                          initial={{ scale: 0.5, opacity: 0 }}
                          animate={{ scale: 1, opacity: 1 }}
                          exit={{ scale: 0.5, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                        >
                          <Check className="w-5 h-5 text-green-500" />
                        </motion.div>
                      ) : (
                        <motion.div
                          initial={{ scale: 0.5, opacity: 0 }}
                          animate={{ scale: 1, opacity: 1 }}
                          exit={{ scale: 0.5, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                        >
                          <Copy className="w-5 h-5 text-[#C4C4C7]" />
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </button>
                </div>
              </div>

              {state.canChange && (
                <form onSubmit={handleSubmit}>
                  <div className="mb-6 mt-6">
                    <h3 className="text-md font-semibold text-[#E5E5E5] mb-3">Change Your Private Address</h3>
                    <div className="mb-4">
                      <div className="p-4 bg-gradient-to-r from-yellow-900/30 to-amber-900/20 border border-yellow-800/40 rounded-xl mb-4 shadow-md">
                        <p className="text-yellow-200 text-sm flex items-start">
                          <Bell size={16} className="mr-2 flex-shrink-0 mt-0.5 animate-pulse" />
                          <span>Important: You can only change your private address once. After changing, it will be permanently locked.</span>
                        </p>
                      </div>
                      
                      <div className="p-4 bg-gradient-to-r from-blue-900/30 to-indigo-900/20 border border-blue-800/40 rounded-xl mb-4 shadow-md">
                        <p className="text-blue-200 text-sm flex items-start">
                          <Info size={16} className="mr-2 flex-shrink-0 mt-0.5" />
                          <span>Your address must contain only lowercase English letters (a-z), be between 3-32 characters long, and cannot contain spaces or special characters.</span>
                        </p>
                      </div>
                      
                      <input
                        type="text"
                        value={state.newAddress}
                        onChange={(e) => setState(prev => ({ ...prev, newAddress: e.target.value.toLowerCase(), error: '' }))}
                        placeholder="Enter new private address"
                        className="w-full bg-[#323234] border border-[#3A3A3E] rounded-xl px-4 py-3 text-white placeholder-[#6C6C70] focus:outline-none focus:ring-2 focus:ring-[#8B5CF6] focus:border-transparent"
                      />
                    </div>
                    
                    <motion.button
                      type="submit"
                      disabled={state.isSubmitting || !state.newAddress}
                      whileHover={{ scale: state.isSubmitting || !state.newAddress ? 1 : 1.02 }}
                      whileTap={{ scale: state.isSubmitting || !state.newAddress ? 1 : 0.98 }}
                      className={`w-full rounded-xl px-4 py-3 text-white font-medium flex items-center justify-center
                        ${state.isSubmitting || !state.newAddress 
                          ? 'bg-[#525252] cursor-not-allowed' 
                          : 'bg-gradient-to-r from-[#8B5CF6] to-[#6366F1] hover:opacity-90 transition-all shadow-lg shadow-purple-900/20'}`}
                    >
                      {state.isSubmitting ? (
                        <>
                          <RefreshCw className="animate-spin mr-2" size={18} />
                          Updating Address...
                        </>
                      ) : (
                        <>
                          <Edit className="mr-2" size={18} />
                          Update Private Address
                        </>
                      )}
                    </motion.button>
                  </div>
                </form>
              )}
              
              {!state.canChange && state.cooldownDays > 0 && (
                <div className="mb-6 mt-6">
                  <h3 className="text-md font-semibold text-[#E5E5E5] mb-3">Change Your Private Address</h3>
                  <div className="p-4 bg-gray-800 rounded-xl border border-[#3A3A3E] text-center">
                    <Lock className="h-8 w-8 mx-auto mb-2 text-[#8B5CF6]" />
                    <p className="text-[#C4C4C7] mb-1">Your address is temporarily locked</p>
                    <p className="text-sm text-[#8B8B8B]">You can change your address in {state.cooldownDays} days</p>
                  </div>
                </div>
              )}
              
              {!state.canChange && state.cooldownDays === 0 && (
                <div className="mb-6 mt-6">
                  <h3 className="text-md font-semibold text-[#E5E5E5] mb-3">Change Your Private Address</h3>
                  <div className="p-4 bg-gray-800 rounded-xl border border-[#3A3A3E] text-center">
                    <Lock className="h-8 w-8 mx-auto mb-2 text-[#8B5CF6]" />
                    <p className="text-[#C4C4C7] mb-1">Your address is permanently locked</p>
                    <p className="text-sm text-[#8B8B8B]">You've already changed your private address</p>
                  </div>
                </div>
              )}

              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2, duration: 0.3 }}
                className="mt-8 border-t border-[#3A3A3E] pt-4"
              >
                <h3 className="text-md font-semibold text-[#E5E5E5] mb-3">About Custom Private Addresses</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-[#323234] p-4 rounded-xl border border-[#3A3A3E] hover:bg-[#38383E] transition-colors">
                    <div className="bg-[#8B5CF6]/20 p-2 rounded-lg w-10 h-10 flex items-center justify-center mb-3">
                      <Shield className="text-[#9D8DFF]" size={20} />
                    </div>
                    <h4 className="text-[#E5E5E5] font-medium mb-2">Secure Transfers</h4>
                    <p className="text-sm text-[#C4C4C7]">Your private address is used for secure peer-to-peer transfers within the Cryptonel network.</p>
                  </div>
                  
                  <div className="bg-[#323234] p-4 rounded-xl border border-[#3A3A3E] hover:bg-[#38383E] transition-colors">
                    <div className="bg-[#8B5CF6]/20 p-2 rounded-lg w-10 h-10 flex items-center justify-center mb-3">
                      <AtSign className="text-[#9D8DFF]" size={20} />
                    </div>
                    <h4 className="text-[#E5E5E5] font-medium mb-2">Unique Identifier</h4>
                    <p className="text-sm text-[#C4C4C7]">Custom addresses must be unique across the entire network, making yours one-of-a-kind.</p>
                  </div>
                  
                  <div className="bg-[#323234] p-4 rounded-xl border border-[#3A3A3E] hover:bg-[#38383E] transition-colors">
                    <div className="bg-[#8B5CF6]/20 p-2 rounded-lg w-10 h-10 flex items-center justify-center mb-3">
                      <Lock className="text-[#9D8DFF]" size={20} />
                    </div>
                    <h4 className="text-[#E5E5E5] font-medium mb-2">Permanent Choice</h4>
                    <p className="text-sm text-[#C4C4C7]">Choose your address carefully. Once changed, it will be permanently locked to prevent identity confusion.</p>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )}
        </motion.div>
      </div>
    </div>
  );
};

export default CustomAddress; 
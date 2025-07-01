import React, { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Sparkles, ArrowRight } from "lucide-react";
import axios from "axios";

// Apply static check counter to prevent repeated checks
let hasCheckedSession = false;
let hasPremiumCheck = false;

// Global API throttling - this will block any repeated API calls
const API_THROTTLE = {
  apiCalls: {} as Record<string, number>,
  inProgress: {} as Record<string, boolean>,
  
  canCall: function(endpoint: string, throttleMs = 10000): boolean {
    const now = Date.now();
    const lastCall = this.apiCalls[endpoint] || 0;
    const inProgress = this.inProgress[endpoint] || false;
    
    if (inProgress || (now - lastCall < throttleMs)) {
      console.log(`API call to ${endpoint} throttled. Last call: ${new Date(lastCall).toISOString()}`);
      return false;
    }
    
    this.apiCalls[endpoint] = now;
    this.inProgress[endpoint] = true;
    return true;
  },
  
  finishCall: function(endpoint: string): void {
    this.inProgress[endpoint] = false;
  }
};

// Safe fetch function with throttling
async function safeFetch(url: string, options?: RequestInit): Promise<Response> {
  if (!API_THROTTLE.canCall(url)) {
    // Return cached response if available
    const cachedAuth = sessionStorage.getItem('auth_state');
    if (cachedAuth && url.includes('/api/auth/check-session')) {
      const authState = JSON.parse(cachedAuth);
      const mockResponse = new Response(
        JSON.stringify({
          authenticated: authState.isAuthenticated, 
          user_id: authState.userId,
          has_wallet: true
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      );
      return Promise.resolve(mockResponse);
    }
    
    return Promise.reject(new Error('API call throttled'));
  }
  
  try {
    const response = await fetch(url, options);
    API_THROTTLE.finishCall(url);
    return response;
  } catch (error) {
    API_THROTTLE.finishCall(url);
    throw error;
  }
}

// Custom hook for stars background with subtle animation effect
const useStarsBackground = () => {
  const [stars, setStars] = useState<{x: number; y: number; size: number; opacity: number; animationDelay: number}[]>([]);
  
  useEffect(() => {
    // Create stars with different sizes and positions
    const newStars = Array.from({ length: 150 }).map(() => ({
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: Math.random() * 2 + 0.5,
      opacity: Math.random() * 0.7 + 0.3,
      animationDelay: Math.random() * 5 // Random animation delay
    }));
    
    setStars(newStars);
  }, []);
  
  return stars;
};

// Function to check premium status and reset settings if needed
async function checkPremiumStatus() {
  try {
    // Only check once per session to avoid multiple API calls
    if (hasPremiumCheck) return;
    hasPremiumCheck = true;
    
    // Call the premium check API
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
        isPremium: response.data.premium,
        membershipType: response.data.membership,
        lastChecked: new Date().toISOString()
      }));
      
      console.log("Premium status checked:", response.data.premium);
      
      // If settings were reset due to premium status change, log it
      if (response.data.settings_reset) {
        console.log("Premium settings were reset due to status change");
        // Could notify the user here if needed
      }
    }
  } catch (error) {
    console.error("Error checking premium status:", error);
  }
}

const DashboardSelect: React.FC = () => {
  const [isChecking, setIsChecking] = useState(true);
  const navigate = useNavigate();
  const stars = useStarsBackground();
  const checkSessionRef = useRef<boolean>(false); // Add a ref to track if we've already checked

  // Override the global fetch function to use our throttled version
  useEffect(() => {
    const originalFetch = window.fetch;
    
    window.fetch = function(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
      let url = '';
      
      if (typeof input === 'string') {
        url = input;
      } else if (input instanceof Request) {
        url = input.url;
      } else {
        // Handle URL object
        url = input.toString();
      }
      
      // Only throttle auth endpoints and let others pass through
      if (url.includes('/api/auth/check-session') || url.includes('/api/auth/check-rate-limit')) {
        return safeFetch(url, init);
      }
      
      return originalFetch(input, init);
    };
    
    return () => {
      window.fetch = originalFetch;  // Restore original fetch on unmount
    };
  }, []);

  useEffect(() => {
    // CRITICAL FIX: Use module-level flag to prevent multiple session checks
    // This prevents any recursion between components
    if (hasCheckedSession) {
      // If we've already checked in any component, just stop
      setIsChecking(false);
      return;
    }
    
    // Prevent multiple simultaneous session checks
    if (checkSessionRef.current) return;
    checkSessionRef.current = true;
    
    // Check if user is already authenticated
    const checkSession = async () => {
      try {
        // Set global flag to prevent any future checks
        hasCheckedSession = true;
        
        // First check local storage for tokens
        const hasAccessToken = localStorage.getItem('access_token');
        const cachedAuthState = sessionStorage.getItem('auth_state');
        
        // If we have a cached auth state that says we're authenticated, use that first
        if (cachedAuthState) {
          try {
            const authState = JSON.parse(cachedAuthState);
            if (authState.isAuthenticated) {
              // Check premium status before redirecting
              await checkPremiumStatus();
              navigate("/dashboard");
              return;
            }
          } catch (e) {
            // If JSON parse fails, clear the invalid cached state
            sessionStorage.removeItem('auth_state');
          }
        }
        
        // If we have a token, try to go to dashboard directly to avoid unnecessary API calls
        if (hasAccessToken) {
          // Check premium status before redirecting
          await checkPremiumStatus();
          navigate("/dashboard");
          return;
        }
        
        // Only if we don't have local tokens, check with the server once
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000); // Set timeout
        
        try {
          const response = await safeFetch("/api/auth/check-session", {
            signal: controller.signal,
            headers: {
              'Cache-Control': 'no-cache, no-store, must-revalidate',
              'Pragma': 'no-cache',
              'Expires': '0'
            }
          });
          
          clearTimeout(timeoutId);
          
          if (response.ok) {
            const data = await response.json();
            if (data.authenticated) {
              // User is already authenticated
              // Check premium status before redirecting
              await checkPremiumStatus();
              // Redirect to dashboard instead of login page
              navigate("/dashboard");
              return;
            }
          }
        } catch (fetchError) {
          console.error("Error in fetch:", fetchError);
          // On error, continue to show login options
        } finally {
          clearTimeout(timeoutId);
        }
        
        // User is not authenticated, show login options
        setIsChecking(false);
      } catch (error) {
        console.error("Error checking session:", error);
        setIsChecking(false);
      } finally {
        // No need to release the flag - we want to prevent any future checks
      }
    };

    // Short delay before the first check
    const timer = setTimeout(checkSession, 100);
    return () => {
      clearTimeout(timer);
    };
  }, [navigate]);

  // Handle Discord login - prevent repeated API calls
  const handleDiscordLogin = (e: React.MouseEvent) => {
    e.preventDefault();
    window.location.href = "/api/auth/discord";
  };

  if (isChecking) {
    return (
      <div className="fixed inset-0 flex items-center justify-center p-4 z-50">
        {/* Backdrop with animated stars - SuperGrok style */}
        <div className="fixed inset-0 bg-black overflow-hidden">
          {stars.map((star, i) => (
            <div
              key={i}
              className={`absolute rounded-full bg-white ${i % 3 === 0 ? 'animate-twinkle' : ''}`}
              style={{
                left: `${star.x}%`,
                top: `${star.y}%`,
                width: `${star.size}px`,
                height: `${star.size}px`,
                opacity: star.opacity,
                animationDuration: `${3 + star.animationDelay * 0.5}s`,
                animationDelay: `${star.animationDelay}s`,
              }}
            />
          ))}
          
          {/* Gradient overlay for depth */}
          <div className="absolute inset-0 bg-gradient-radial from-[#1B1E2A]/30 via-[#111827]/20 to-transparent"></div>
        </div>
        
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#D4D5F4] mx-auto mb-4"></div>
          <p className="text-[#D4D5F4]/70">Checking authentication...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 flex items-center justify-center p-4 z-50">
      {/* Backdrop with animated stars - SuperGrok style */}
      <div className="fixed inset-0 bg-black overflow-hidden">
        {/* Fixed stars */}
        {stars.map((star, i) => (
          <div
            key={i}
            className={`absolute rounded-full bg-white ${i % 3 === 0 ? 'animate-twinkle' : ''}`}
            style={{
              left: `${star.x}%`,
              top: `${star.y}%`,
              width: `${star.size}px`,
              height: `${star.size}px`,
              opacity: star.opacity,
              animationDuration: `${3 + star.animationDelay * 0.5}s`,
              animationDelay: `${star.animationDelay}s`,
            }}
          />
        ))}
        
        {/* Gradient overlay for depth */}
        <div className="absolute inset-0 bg-gradient-radial from-[#1B1E2A]/30 via-[#111827]/20 to-transparent"></div>
      </div>
      
      {/* Login container with SuperGrok style */}
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        transition={{ type: "spring", bounce: 0.2, duration: 0.7 }}
        className="relative w-full max-w-md backdrop-blur-lg rounded-2xl overflow-hidden shadow-xl"
        style={{ 
          background: 'linear-gradient(135deg, rgba(23, 23, 29, 0.9) 0%, rgba(26, 27, 34, 0.9) 25%, rgba(16, 16, 22, 0.9) 50%, rgba(20, 22, 27, 0.9) 100%)',
          boxShadow: '0 0 40px rgba(74, 85, 144, 0.1)'
        }}
      >
        {/* SuperGrok style glowing border */}
        <div className="absolute inset-0 p-px rounded-2xl overflow-hidden pointer-events-none">
          <div className="absolute inset-0 rounded-2xl" 
            style={{
              background: 'linear-gradient(135deg, rgba(90, 100, 255, 0.1), rgba(41, 46, 117, 0.03), rgba(60, 100, 180, 0.1))',
              opacity: 0.3
            }}
          ></div>
        </div>
        
        {/* Subtle glow effect - enhanced for SuperGrok style */}
        <div className="absolute inset-0"
          style={{
            background: 'radial-gradient(circle at 30% 40%, rgba(62, 76, 179, 0.03) 0%, transparent 60%), radial-gradient(circle at 70% 60%, rgba(65, 96, 179, 0.02) 0%, transparent 60%)'
          }}
        ></div>
        
        {/* Moving subtle pattern to create animation like SuperGrok */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute inset-0 opacity-5 animate-slow-pulse"
            style={{
              backgroundImage: `
                radial-gradient(circle at 20% 30%, rgba(255, 255, 255, 0.15) 0%, transparent 10%),
                radial-gradient(circle at 80% 70%, rgba(255, 255, 255, 0.15) 0%, transparent 10%)
              `,
              backgroundSize: '120% 120%',
              backgroundPosition: 'center'
            }}
          ></div>
        </div>
        
        {/* Subtle grid pattern */}
        <div className="absolute inset-0 opacity-3" 
          style={{
            backgroundImage: `
              linear-gradient(to right, rgba(255, 255, 255, 0.05) 1px, transparent 1px),
              linear-gradient(to bottom, rgba(255, 255, 255, 0.05) 1px, transparent 1px)
            `,
            backgroundSize: '30px 30px'
          }}
        ></div>
        
        <div className="p-8 relative z-10">
          {/* Header with title */}
          <div className="mb-10">
            <motion.div 
              initial={{ y: -20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="flex items-center justify-center space-x-2 mb-2"
            >
              <div className="w-10 h-10 bg-[#0d1117] rounded-full flex items-center justify-center border border-[#D4D5F4]/30">
                <Sparkles className="w-5 h-5 text-[#D4D5F4]" />
              </div>
              <h2 className="grok-gradient-text text-2xl font-bold">Cryptonel Wallet</h2>
            </motion.div>
          </div>
          
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            <h1 className="text-2xl font-bold text-center mb-6 text-white">Welcome to Cryptonel Wallet</h1>
            
            <p className="text-[#D4D5F4]/70 mb-8 text-center">
              Please log in with Discord to access your account
            </p>
            
            <div className="space-y-4">
              <button
                onClick={handleDiscordLogin}
                className="w-full flex items-center justify-center bg-indigo-600 text-white py-3 px-4 rounded-md hover:bg-indigo-700 transition-all group relative overflow-hidden"
              >
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-r from-[#D4D5F4]/30 to-transparent"></div>
                
                <svg 
                  className="w-6 h-6 mr-2" 
                  xmlns="http://www.w3.org/2000/svg" 
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515a.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0a12.64 12.64 0 0 0-.617-1.25a.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057a19.9 19.9 0 0 0 5.993 3.03a.078.078 0 0 0 .084-.028a14.09 14.09 0 0 0 1.226-1.994a.076.076 0 0 0-.041-.106a13.107 13.107 0 0 1-1.872-.892a.077.077 0 0 1-.008-.128a10.2 10.2 0 0 0 .372-.292a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127a12.299 12.299 0 0 1-1.873.892a.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028a19.839 19.839 0 0 0 6.002-3.03a.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.956-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.419c0 1.334-.956 2.419-2.157 2.419zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.955-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.419c0 1.334-.946 2.419-2.157 2.419z"/>
                </svg>
                <span className="font-medium">Continue with Discord</span>
                <ArrowRight className="w-5 h-5 ml-2 text-[#D4D5F4]" />
              </button>
            </div>
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
};

export default DashboardSelect; 
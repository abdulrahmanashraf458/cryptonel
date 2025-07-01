import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Eye, EyeOff, Lock, Mail, ArrowRight, X, RotateCcw, Sparkles, User, 
  Fingerprint, AlertTriangle, Shield, ShieldCheck, XCircle, Key, Code, ChevronLeft,
  Clock, Globe, CheckCircle
} from 'lucide-react';
import { useNavigate, useLocation, Location } from "react-router-dom";

// Add custom CSS for animations
import '../Login.css';

// Custom hook for particle system
const useParticles = (count = 50) => {
  // Return empty array instead of creating particles, but keep the hook for structure
  return [];
};

// Interactive orbit component
const OrbitSystem = ({ children }: { children: React.ReactNode }) => {
  const [rotation, setRotation] = useState(0);
  
  useEffect(() => {
    const interval = setInterval(() => {
      setRotation(prev => (prev + 0.2) % 360);
    }, 50);
    
    return () => clearInterval(interval);
  }, []);
  
  return (
    <div className="relative w-full h-full">
      {/* Central element */}
      <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-10">
        {children}
      </div>
      
      {/* Orbiting elements */}
      {Array.from({ length: 5 }).map((_, i) => {
        const angle = (rotation + (i * 72)) * (Math.PI / 180);
        const distance = 140;
        const x = Math.cos(angle) * distance;
        const y = Math.sin(angle) * distance;
        const size = 20 - i * 2;
        
        return (
          <div 
            key={i}
            className="absolute rounded-full bg-[#D4D5F4]/20 backdrop-blur-sm border border-[#D4D5F4]/30"
            style={{
              width: `${size}px`,
              height: `${size}px`,
              top: `calc(50% - ${size/2}px + ${y}px)`,
              left: `calc(50% - ${size/2}px + ${x}px)`,
              transition: 'all 0.2s ease-out'
            }}
          />
        );
      })}
      
      {/* Orbit paths */}
      <div className="absolute top-1/2 left-1/2 w-[280px] h-[280px] rounded-full border border-dashed border-[#D4D5F4]/10 transform -translate-x-1/2 -translate-y-1/2"></div>
    </div>
  );
};

// Creative input field
const InnovativeInput = ({ 
  type = 'text', 
  placeholder, 
  value, 
  onChange, 
  icon: Icon,
  error = false,
  disabled = false
}: { 
  type?: string;
  placeholder: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  icon: React.ElementType;
  error?: boolean;
  disabled?: boolean;
}) => {
  const [focused, setFocused] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const actualType = type === 'password' && showPassword ? 'text' : type;
  
  return (
    <div 
      className={`
        relative rounded-lg overflow-hidden transition-all duration-300
        ${focused ? 'shadow-lg shadow-[#D4D5F4]/20' : ''}
        ${error ? 'shadow-red-500/30' : ''}
        ${disabled ? 'opacity-70' : ''}
      `}
    >
      {/* Background elements */}
      <div className="absolute inset-0 bg-gradient-to-r from-[#0d1117]/90 to-[#0a192f]/80 backdrop-blur-md"></div>
      <div 
        className={`
          absolute left-0 top-0 bottom-0 w-1 transition-all duration-300 
          ${focused ? 'bg-[#D4D5F4]' : 'bg-[#D4D5F4]/30'}
          ${error ? '!bg-red-500' : ''}
          ${disabled ? 'bg-gray-500/30' : ''}
        `}
      ></div>
      
      <div className="relative flex items-center">
        <div className="flex-shrink-0 pl-4">
          <Icon className={`w-5 h-5 ${focused ? 'text-[#D4D5F4]' : 'text-[#D4D5F4]/50'} ${error ? '!text-red-500' : ''} ${disabled ? 'text-gray-500/50' : ''}`} />
        </div>
        
        <input
          type={actualType}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          disabled={disabled}
          className="w-full bg-transparent text-white border-none outline-none py-4 px-4 placeholder-[#D4D5F4]/30 disabled:cursor-not-allowed"
        />
        
        {type === 'password' && (
          <button 
            type="button" 
            onClick={() => setShowPassword(!showPassword)}
            disabled={disabled}
            className="flex-shrink-0 pr-4 text-[#D4D5F4]/50 hover:text-[#D4D5F4] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
          </button>
        )}
      </div>
    </div>
  );
};

// OTP Input component
const OtpInput = ({ value, onChange, error = false, disabled = false }: { 
  value: string; 
  onChange: (value: string) => void;
  error?: boolean;
  disabled?: boolean;
}) => {
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const [focused, setFocused] = useState<number | null>(null);
  
  // Initialize refs array
  useEffect(() => {
    inputRefs.current = inputRefs.current.slice(0, 6);
  }, []);
  
  // Handle input change
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>, index: number) => {
    const val = e.target.value;
    
    // Only accept numbers
    if (!/^\d*$/.test(val)) {
      return;
    }
    
    // If multiple characters were pasted, distribute them
    if (val.length > 1) {
      // Only take what we need to fill the boxes
      const chars = val.split('').slice(0, 6 - index);
      
      // Create new value with what we already have plus the new chars
      let newValue = value.slice(0, index);
      for (let i = 0; i < chars.length; i++) {
        if (index + i < 6) {
          newValue += chars[i];
        }
      }
      
      // Pad to maintain the same length if we didn't fill all boxes
      newValue = newValue.padEnd(value.length, value.slice(newValue.length));
      
      // Update the value
      onChange(newValue.slice(0, 6));
      
      // Focus the appropriate input
      const nextIndex = Math.min(index + chars.length, 5);
      setTimeout(() => {
        inputRefs.current[nextIndex]?.focus();
      }, 0);
      
      return;
    }
    
    // Create new value
    const newValue = value.split('');
    newValue[index] = val.slice(-1); // Only take the last character
    const joinedValue = newValue.join('');
    
    // Update the parent state
    onChange(joinedValue);
    
    // Auto-focus next input if we typed something
    if (val !== '' && index < 5) {
      setTimeout(() => {
        inputRefs.current[index + 1]?.focus();
      }, 0);
    }
  };
  
  // Handle backspace
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>, index: number) => {
    if (e.key === 'Backspace') {
      if (index > 0 && !value[index]) {
        // If current box is empty, focus previous box
        inputRefs.current[index - 1]?.focus();
      }
    } else if (e.key === 'ArrowLeft' && index > 0) {
      // Arrow navigation
      inputRefs.current[index - 1]?.focus();
      e.preventDefault();
    } else if (e.key === 'ArrowRight' && index < 5) {
      inputRefs.current[index + 1]?.focus();
      e.preventDefault();
    }
  };
  
  // Handle paste event
  const handlePaste = (e: React.ClipboardEvent, index: number) => {
    e.preventDefault();
    const pasteData = e.clipboardData.getData('text').trim();
    
    // Only process if it looks like a valid OTP
    if (!/^\d+$/.test(pasteData)) {
      return;
    }
    
    handleChange(
      {
        target: { value: pasteData },
      } as React.ChangeEvent<HTMLInputElement>,
      index
    );
  };
  
  return (
    <div className="flex justify-between space-x-3">
      {Array.from({ length: 6 }).map((_, index) => (
        <div
          key={index}
          className={`
            relative w-12 h-14 rounded-xl overflow-hidden transition-all duration-300
            ${focused === index ? 'ring-2 ring-[#D4D5F4]/60 shadow-lg shadow-[#D4D5F4]/20 transform scale-105' : ''}
            ${error ? 'ring-2 ring-red-500/50' : ''}
            ${disabled ? 'opacity-70' : ''}
            ${value[index] ? 'bg-[#1a2e4c]' : 'bg-[#131e2e]'}
            backdrop-blur-lg border border-[#D4D5F4]/20
            group
          `}
        >
          {/* Glow effect when focused */}
          {focused === index && (
            <div className="absolute inset-0 bg-[#D4D5F4]/5 animate-pulse"></div>
          )}
          
          {/* Input */}
          <input
            ref={(el) => (inputRefs.current[index] = el)}
            type="text"
            value={value[index] || ''}
            onChange={(e) => handleChange(e, index)}
            onKeyDown={(e) => handleKeyDown(e, index)}
            onFocus={() => setFocused(index)}
            onBlur={() => setFocused(null)}
            onPaste={(e) => handlePaste(e, index)}
            className="w-full h-full bg-transparent text-white border-none outline-none text-center font-bold text-2xl disabled:cursor-not-allowed group-hover:text-[#D4D5F4]"
            maxLength={1}
            disabled={disabled}
            autoComplete="one-time-code"
            inputMode="numeric"
            pattern="\d*"
          />
        </div>
      ))}
    </div>
  );
};

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

// Define the location state interface
interface LocationState {
  from?: Location;
  intendedDestination?: string;
}

const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [secretWord, setSecretWord] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [loginPhase, setLoginPhase] = useState<'idle' | 'connecting' | 'connected' | 'error' | 'verifying' | '2fa' | 'secret_word'>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [errorType, setErrorType] = useState<'credentials' | 'permission' | 'rate_limit' | 'server' | 'banned' | 'security_restriction' | null>(null);
  const [showFingerprint, setShowFingerprint] = useState(false);
  const [fingerprintScanLines, setFingerprintScanLines] = useState(false);
  const [fingerprintMatched, setFingerprintMatched] = useState(false);
  const [loginBlocked, setLoginBlocked] = useState(false);
  const [accountBanned, setAccountBanned] = useState(() => {
    // Don't use localStorage for ban state initially - we'll check with the server first
    return false;
  });
  const [loginBlockedUntil, setLoginBlockedUntil] = useState<Date | null>(null);
  const [requires2FA, setRequires2FA] = useState(false);
  const [requiresSecretWord, setRequiresSecretWord] = useState(false);
  const [partialAuthData, setPartialAuthData] = useState<{userId?: string}>({});
  const containerRef = useRef<HTMLDivElement>(null);
  const particles = useParticles(80);
  const navigate = useNavigate();
  const loginTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [discordAuthenticated, setDiscordAuthenticated] = useState(false);
  const [hasWallet, setHasWallet] = useState(() => {
    return sessionStorage.getItem('has_wallet') === 'true';
  });
  const stars = useStarsBackground();
  const location = useLocation();
  const locationState = location.state as { intendedDestination?: string } || {};

  // Check if user is authenticated with Discord first
  useEffect(() => {
    // If account is banned, no need to check authentication
    if (accountBanned) {
      return;
    }
    
    const checkDiscordAuth = async () => {
      try {
        const response = await fetch("/api/auth/check-session", {
          method: "GET",
          credentials: "include",
          headers: {
            "Accept": "application/json",
          }
        });
        
        if (!response.ok) {
          throw new Error(`Server returned ${response.status}`);
        }

        const data = await response.json();
        console.log("Session check result:", data);

        // Check if the user is banned
        if (data.banned === true) {
          setAccountBanned(true);
          return;
        } else {
          // If the server explicitly says the user is not banned, remove the ban flag
          localStorage.removeItem('account_banned');
        }

        if (data.authenticated === true) {
          navigate("/dashboard");
          return;
        } else if (data.discord_authenticated === true) {
          setDiscordAuthenticated(true);
          
          // Update hasWallet variable based on server response
          const userHasWallet = !!data.has_wallet;
          console.log("User has wallet?", userHasWallet);
          setHasWallet(userHasWallet);
          
          // Store in sessionStorage
          if (userHasWallet) {
            sessionStorage.setItem('has_wallet', 'true');
            // Don't prefill username field to ensure user enters it themselves
          } else {
            sessionStorage.removeItem('has_wallet');
          }
          
          fetchCsrfToken();
        } else {
          navigate("/dashboardselect");
        }
      } catch (error) {
        console.error("Error checking Discord authentication:", error);
        navigate("/dashboardselect");
      }
    };

    checkDiscordAuth();
    
    // Cleanup on unmount
    return () => {
      if (loginTimeoutRef.current) {
        clearTimeout(loginTimeoutRef.current);
      }
    };
  }, [navigate, accountBanned]);

  // CSRF token state
  const [csrfToken, setCsrfToken] = useState('');
  
  // Function to fetch CSRF token
  const fetchCsrfToken = async (): Promise<string | null> => {
    try {
      console.log('Fetching CSRF token...');
      const response = await fetch("/api/csrf-token", {
        method: "GET",
        credentials: "include",
        headers: {
          "Accept": "application/json",
        }
      });

      console.log('CSRF token response status:', response.status);
      
      if (response.ok) {
        const data = await response.json();
        console.log('CSRF token response data:', data);
        
        if (data.success && data.csrf_token) {
          console.log("CSRF token fetched successfully");
          setCsrfToken(data.csrf_token);
          return data.csrf_token;
        } else {
          console.error('CSRF token fetch failed:', data.error || 'Unknown error');
          setErrorMessage("Security token initialization failed. Please refresh the page.");
          setErrorType('server');
          return null;
        }
      } else {
        console.error("Failed to fetch CSRF token:", response.status);
        setErrorMessage("Failed to establish a secure connection. Please refresh the page.");
        setErrorType('server');
        return null;
      }
    } catch (error) {
      console.error("Error fetching CSRF token:", error);
      setErrorMessage("Failed to establish a secure connection. Please refresh the page.");
      setErrorType('server');
      return null;
    }
  };
  
  // Improved checkAuthMethods function to check user authentication requirements
  const checkAuthMethods = async () => {
    if (!username.trim()) {
      return;
    }

    try {
      console.log('Checking auth methods for username:', username.trim());
      console.log('Using CSRF token:', csrfToken ? csrfToken.substring(0, 20) + '...' : 'none');
      
      // Request available auth methods for this username
      const response = await fetch("/api/login/auth-methods", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
          "X-CSRF-Token": csrfToken
        },
        body: JSON.stringify({ username: username.trim() })
      });

      console.log('Auth methods response status:', response.status);

      if (response.status === 403) {
        // CSRF token error - try to refresh and retry
        console.log('CSRF token error, attempting to refresh...');
        const newCsrfToken = await fetchCsrfToken();
        
        // Retry with new token if available
        if (newCsrfToken) {
          console.log('Retrying login with fresh CSRF token...');
          const retryResponse = await fetch("/api/login", {
            method: "POST",
            credentials: "include",
            headers: {
              "Content-Type": "application/json",
              "Accept": "application/json",
              "X-CSRF-Token": newCsrfToken
            },
            body: JSON.stringify({ username: username.trim() }),
          });
          
          if (retryResponse.ok) {
            const retryData = await retryResponse.json();
            console.log("Login retry successful:", JSON.stringify(retryData));
            
            // Process the successful retry response
            if (retryData.partial_auth) {
              // Handle partial auth as before
              setFingerprintScanLines(false);
              setFingerprintMatched(true);
              
              await new Promise(resolve => setTimeout(resolve, 1500));
              
              setShowFingerprint(false);
              setFingerprintMatched(false);
              
              setPartialAuthData({
                userId: retryData.user_id
              });

              if (retryData.requires_2fa) {
                console.log("2FA required, transitioning to 2FA input");
                setLoginPhase('2fa');
                return;
              } else if (retryData.requires_secret_word) {
                console.log("Secret word required, transitioning to secret word input");
                setLoginPhase('secret_word');
                return;
              }
            }
            
            // Complete authentication process
            setFingerprintScanLines(false);
            setFingerprintMatched(true);
            setLoginPhase('connected');
            
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Process successful login
            localStorage.removeItem('server_lockout');
            localStorage.setItem('access_token', retryData.access_token);
            if (retryData.refresh_token) {
              localStorage.setItem('refresh_token', retryData.refresh_token);
            }
            
            // Set cookies
            let accessExpiry = rememberMe ? 30 * 24 * 60 * 60 : 15 * 60;
            let refreshExpiry = rememberMe ? 90 * 24 * 60 * 60 : 7 * 24 * 60 * 60;
            
            document.cookie = `access_token=${retryData.access_token}; path=/; max-age=${accessExpiry}; SameSite=Lax`;
            if (retryData.refresh_token) {
              document.cookie = `refresh_token=${retryData.refresh_token}; path=/; max-age=${refreshExpiry}; SameSite=Lax`;
            }
            
            // Update session storage
            sessionStorage.setItem('auth_state', JSON.stringify({
              isAuthenticated: true,
              isLocked: false
            }));
            
            // Navigate to intended destination or dashboard
            const intendedDestination = location.state?.intendedDestination || '/dashboard';
            navigate(intendedDestination, { replace: true });
            return;
          }
        }
        
        // If retry failed, show error
        setLoginPhase('error');
        setErrorMessage('Security validation failed. Please refresh the page and try again.');
        setErrorType('server');
        return;
      }

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const data = await response.json();
      
      // Update state with required auth methods
      console.log("Auth methods for user:", data);
      setRequires2FA(data.requires_2fa || false);
      setRequiresSecretWord(data.requires_secret_word || false);
      
    } catch (error) {
      console.error("Error checking auth methods:", error);
      // Don't show error to user for auth methods check - it's not critical
    }
  };

  // Effect to check auth methods when username changes
  useEffect(() => {
    // Only check if username is not empty and CSRF token is available
    if (username && csrfToken) {
      checkAuthMethods();
    }
  }, [username]);
  
  // حذف منطق الريت ليمت المحلي واستبداله بفحص فقط
  useEffect(() => {
    // فحص إذا كان الخادم قد أرسل معلومات حظر سابقا
    const lockoutData = localStorage.getItem('server_lockout');
    if (lockoutData) {
      try {
        const { until } = JSON.parse(lockoutData);
        const lockoutUntil = new Date(until);
        const now = new Date();
        
        if (now < lockoutUntil) {
          setLoginBlocked(true);
          setLoginBlockedUntil(lockoutUntil);
          const minutesLeft = Math.round((lockoutUntil.getTime() - now.getTime()) / (1000 * 60));
          setErrorMessage(`Too many login attempts. Please try again in ${minutesLeft} minutes.`);
          setErrorType('rate_limit');
          
          // تحديث كل دقيقة
          const checkBlockStatus = setInterval(() => {
            const now = new Date();
            if (now > lockoutUntil) {
              setLoginBlocked(false);
              setErrorMessage('');
              setErrorType(null);
              localStorage.removeItem('server_lockout');
              clearInterval(checkBlockStatus);
            } else {
              const minutesLeft = Math.round((lockoutUntil.getTime() - now.getTime()) / (1000 * 60));
              setErrorMessage(`Too many login attempts. Please try again in ${minutesLeft} minutes.`);
            }
          }, 60000);
          
          return () => clearInterval(checkBlockStatus);
        } else {
          localStorage.removeItem('server_lockout');
        }
      } catch (err) {
        localStorage.removeItem('server_lockout');
      }
    }
  }, []);
  
  // Gravity effect on mouse move
  useEffect(() => {
    // تم تعطيل تأثير الماوس المتحرك
    // لا يوجد أي كود هنا بعد الآن
  }, []);
  
  const resetAuthStates = () => {
    setRequires2FA(false);
    setRequiresSecretWord(false);
    setVerificationCode('');
    setSecretWord('');
    setPartialAuthData({});
    setLoginPhase('idle');
    // Do not reset accountBanned state here
    if (!accountBanned) {
      setErrorMessage('');
      setErrorType(null);
    }
    
    // Clear any login timeout if it exists
    if (loginTimeoutRef.current) {
      clearTimeout(loginTimeoutRef.current);
      loginTimeoutRef.current = null;
    }
  };
  
  // Improve the error handling and state reset in input change handlers
  useEffect(() => {
    if (username || password) {
      // Reset error message immediately when input changes
      resetErrorState();
    }
  }, [username, password]);
  
  useEffect(() => {
    if (verificationCode) {
      resetErrorState();
    }
  }, [verificationCode]);
  
  useEffect(() => {
    if (secretWord) {
      resetErrorState();
    }
  }, [secretWord]);
  
  // Add a function to reset error state
  const resetErrorState = () => {
    if (!accountBanned && !loginBlocked) {
      setErrorMessage('');
      setErrorType(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Don't proceed if login is blocked or account is banned
    if (loginBlocked || accountBanned) {
      return;
    }
    
    // Always reset error state and phase when submitting
    setErrorMessage('');
    setErrorType(null);
    
    // Set the appropriate phase based on current state
    if (loginPhase !== '2fa' && loginPhase !== 'secret_word') {
      setLoginPhase('connecting'); // Set connecting for initial login
    } else {
      // Set verifying state for 2FA and secret_word phases
      setLoginPhase('verifying');
    }
    
    // Reset banned state on new submission
    setAccountBanned(false);
    
    // Validate input data based on current phase
    if (loginPhase === 'idle' && (!username || !password)) {
      setLoginPhase('error');
      setErrorMessage('Invalid credentials');
      setErrorType('credentials');
      
      // Reset state back to idle after a delay
      if (loginTimeoutRef.current) clearTimeout(loginTimeoutRef.current);
      loginTimeoutRef.current = setTimeout(() => {
        setLoginPhase('idle');
        setErrorMessage('');
        setErrorType(null);
      }, 2000);
      return;
    }

    // Additional validation
    if (username.length > 50 || password.length > 100) {
      setLoginPhase('error');
      setErrorMessage('Invalid credentials');
      setErrorType('credentials');
      
      // Reset state back to idle after a delay
      if (loginTimeoutRef.current) clearTimeout(loginTimeoutRef.current);
      loginTimeoutRef.current = setTimeout(() => {
        setLoginPhase('idle');
        setErrorMessage('');
        setErrorType(null);
      }, 2000);
      return;
    }

    // If we're in 2FA phase, require verification code
    if (loginPhase === '2fa' && !verificationCode) {
      setLoginPhase('error');
      setErrorMessage('Verification code is required');
      setErrorType('credentials');
      
      // Reset state back to appropriate phase after a delay
      if (loginTimeoutRef.current) clearTimeout(loginTimeoutRef.current);
      loginTimeoutRef.current = setTimeout(() => {
        setLoginPhase('2fa');
        setErrorMessage('');
        setErrorType(null);
      }, 2000);
      return;
    }

    // If we're in secret word phase, require secret word
    if (loginPhase === 'secret_word' && !secretWord) {
      setLoginPhase('error');
      setErrorMessage('Secret word is required');
      setErrorType('credentials');
      
      // Reset state back to appropriate phase after a delay
      if (loginTimeoutRef.current) clearTimeout(loginTimeoutRef.current);
      loginTimeoutRef.current = setTimeout(() => {
        setLoginPhase('secret_word');
        setErrorMessage('');
        setErrorType(null);
      }, 2000);
      return;
    }
    
    try {
      // Show fingerprint animation for all phases - including 2FA and secret_word
      // This will show processing is happening
      await new Promise(resolve => setTimeout(resolve, 300)); // shorter delay for 2FA/secret_word
      
      // Show fingerprint verification overlay
      setShowFingerprint(true);
      setFingerprintScanLines(true);
      
      // Shorter fingerprint verification process for 2FA/secret_word phases
      const scanDelay = (loginPhase === '2fa' || loginPhase === 'secret_word') ? 500 : 700;
      await new Promise(resolve => setTimeout(resolve, scanDelay));
      
      // Verify user through API
      // Add CSRF token to request headers
      console.log("Using CSRF token:", csrfToken ? csrfToken.substring(0, 20) + "..." : "No token!");
      
      const requestBody: any = { 
        username: username.trim(),
        password,
        remember_me: rememberMe
      };

      // Add verification code or secret word ONLY if we're in that specific phase
      if (loginPhase === '2fa') {
        requestBody.verification_code = verificationCode;
        console.log("Including 2FA code in request");
      }

      if (loginPhase === 'secret_word') {
        requestBody.secret_word = secretWord;
        console.log("Including secret word in request");
      }

      console.log("Login phase:", loginPhase);
      console.log("Sending request with body:", JSON.stringify(requestBody).replace(/"password":"[^"]*"/, '"password":"***"'));

      const response = await fetch("/api/login", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
          "X-CSRF-Token": csrfToken
        },
        body: JSON.stringify(requestBody),
      });

      console.log("Login response status:", response.status);

      // Handle CSRF token errors
      if (response.status === 403) {
        const errorData = await response.json();
        if (errorData.error && errorData.error.includes('CSRF')) {
          console.log('CSRF token error, attempting to refresh...');
          const newCsrfToken = await fetchCsrfToken();
          
          // Retry with new token if available
          if (newCsrfToken) {
            console.log('Retrying login with fresh CSRF token...');
            const retryResponse = await fetch("/api/login", {
              method: "POST",
              credentials: "include",
              headers: {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-CSRF-Token": newCsrfToken
              },
              body: JSON.stringify(requestBody),
            });
            
            if (retryResponse.ok) {
              const retryData = await retryResponse.json();
              console.log("Login retry successful:", JSON.stringify(retryData));
              
              // Process the successful retry response
              if (retryData.partial_auth) {
                setFingerprintScanLines(false);
                setFingerprintMatched(true);
                
                await new Promise(resolve => setTimeout(resolve, 1500));
                
                setShowFingerprint(false);
                setFingerprintMatched(false);
                
                setPartialAuthData({
                  userId: retryData.user_id
                });

                if (retryData.requires_2fa) {
                  console.log("2FA required, transitioning to 2FA input");
                  setLoginPhase('2fa');
                  return;
                } else if (retryData.requires_secret_word) {
                  console.log("Secret word required, transitioning to secret word input");
                  setLoginPhase('secret_word');
                  return;
                }
              }
              
              // Complete authentication process
              setFingerprintScanLines(false);
              setFingerprintMatched(true);
              setLoginPhase('connected');
              
              await new Promise(resolve => setTimeout(resolve, 500));
              
              // Process successful login
              localStorage.removeItem('server_lockout');
              localStorage.setItem('access_token', retryData.access_token);
              if (retryData.refresh_token) {
                localStorage.setItem('refresh_token', retryData.refresh_token);
              }
              
              // Set cookies
              let accessExpiry = 15 * 60; // 15 minutes default
              let refreshExpiry = 7 * 24 * 60 * 60; // 7 days default
              if (rememberMe) {
                accessExpiry = 30 * 24 * 60 * 60; // 30 days
                refreshExpiry = 90 * 24 * 60 * 60; // 90 days
              }

              // Set cookies with proper expiration
              document.cookie = `access_token=${retryData.access_token}; path=/; max-age=${accessExpiry}; SameSite=Lax`;
              if (retryData.refresh_token) {
                document.cookie = `refresh_token=${retryData.refresh_token}; path=/; max-age=${refreshExpiry}; SameSite=Lax`;
              }
              
              // Also update the session storage to cache auth state
              sessionStorage.setItem('auth_state', JSON.stringify({
                isAuthenticated: true,
                isLocked: false
              }));
              sessionStorage.setItem('last_auth_check', Date.now().toString());
              
              // Then navigate to dashboard with special state
              console.log("Authentication successful, navigating to dashboard...");
              
              // Always go directly to dashboard
              navigate('/dashboard', { 
                state: { 
                  forceAuthCheck: true,
                  freshLogin: true
                } 
              });
            }
          }
          
          // If retry failed, show error
          setLoginPhase('error');
          setErrorMessage('Security validation failed. Please refresh the page and try again.');
          setErrorType('server');
          return;
        }
      }

      const data = await response.json();
      console.log("Login response:", JSON.stringify(data));
      
      // If login was successful
      if (response.ok) {
        // Check if additional authentication is required
        if (data.partial_auth) {
          // Show success fingerprint for first stage verification
          setFingerprintScanLines(false);
          setFingerprintMatched(true);
          
          // Delay to show green success fingerprint before transitioning
          await new Promise(resolve => setTimeout(resolve, 1500));
          
          // Clear fingerprint overlay but PRESERVE the current username/password
          setShowFingerprint(false);
          setFingerprintMatched(false);
          
          // Save partial auth data
          setPartialAuthData({
            userId: data.user_id
          });

          // Set the appropriate phase based on what's required
          if (data.requires_2fa) {
            console.log("2FA required, transitioning to 2FA input");
            setLoginPhase('2fa');
            return;
          } else if (data.requires_secret_word) {
            console.log("Secret word required, transitioning to secret word input");
            setLoginPhase('secret_word');
            return;
          }
        }
        
        // Complete authentication process - show success
        setFingerprintScanLines(false);
        setFingerprintMatched(true);
        setLoginPhase('connected');
        
        // تقليل تأخير التوجيه من 1500 إلى 500 مللي ثانية
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Remove any lockout information
        localStorage.removeItem('server_lockout');
        
        // Store authentication tokens in localStorage
        localStorage.setItem('access_token', data.access_token);
        if (data.refresh_token) {
          localStorage.setItem('refresh_token', data.refresh_token);
        }
        
        // Also store tokens in cookies for better persistence
        // Get expiration times from token or use defaults
        let accessExpiry = 15 * 60; // 15 minutes default
        let refreshExpiry = 7 * 24 * 60 * 60; // 7 days default
        if (rememberMe) {
          accessExpiry = 30 * 24 * 60 * 60; // 30 days
          refreshExpiry = 90 * 24 * 60 * 60; // 90 days
        }

        // Set cookies with proper expiration
        document.cookie = `access_token=${data.access_token}; path=/; max-age=${accessExpiry}; SameSite=Lax`;
        if (data.refresh_token) {
          document.cookie = `refresh_token=${data.refresh_token}; path=/; max-age=${refreshExpiry}; SameSite=Lax`;
        }
        
        // Also update the session storage to cache auth state
        sessionStorage.setItem('auth_state', JSON.stringify({
          isAuthenticated: true,
          isLocked: false
        }));
        sessionStorage.setItem('last_auth_check', Date.now().toString());
        
        // Then navigate to dashboard with special state
        console.log("Authentication successful, navigating to dashboard...");
        
        // Always go directly to dashboard
        navigate('/dashboard', { 
          state: { 
            forceAuthCheck: true,
            freshLogin: true
          } 
        });
      } else {
        // Handle banned account
        if (response.status === 403 && data.error?.includes("account has been temporarily suspended")) {
          setFingerprintScanLines(false);
          setShowFingerprint(false);
          setLoginPhase('idle'); // Important: Reset to idle state
          setAccountBanned(true);
          setErrorMessage(data.error || "This account has been temporarily suspended. Please contact support.");
          setErrorType('banned');
          // Store banned status in localStorage to persist after refresh
          localStorage.setItem('account_banned', 'true');
          return;
        }
        
        // Rate limit exceeded (429 status)
        if (response.status === 429) {
          const retryAfter = data.retry_after || 900; // Default 15 minutes in seconds
          const blockUntil = new Date();
          blockUntil.setSeconds(blockUntil.getSeconds() + retryAfter);
          setLoginBlockedUntil(blockUntil);
          setLoginBlocked(true);
          
          // Store server lockout information - only store server response
          localStorage.setItem('server_lockout', JSON.stringify({
            until: blockUntil.getTime()
          }));
          
          setFingerprintScanLines(false);
          setShowFingerprint(false);
          setLoginPhase('idle'); // Important: Reset to idle state
          setErrorMessage(`Too many failed attempts. Please try again in ${Math.ceil(retryAfter / 60)} minutes.`);
          setErrorType('rate_limit');
          
          // Set a timeout to check and clear the rate limit message after the specified time
          const rateCheckInterval = setInterval(() => {
            const now = new Date();
            if (loginBlockedUntil && now > loginBlockedUntil) {
              setLoginBlocked(false);
              setLoginBlockedUntil(null);
              localStorage.removeItem('server_lockout');
              setErrorMessage('');
              setErrorType(null);
              clearInterval(rateCheckInterval);
            }
          }, 30000); // Check every 30 seconds
          
          return;
        }
        
        // Handle security restriction access denied (time-based, geo-lock, IP whitelist)
        if (response.status === 403 && data.error?.includes("Access denied")) {
          setFingerprintScanLines(false);
          setShowFingerprint(false);
          setLoginPhase('idle'); // Important: Reset to idle state
          setErrorType('security_restriction');
          
          // Set specific error message based on the restriction type
          if (data.error.includes("time-based") || data.error.includes("between")) {
            setErrorMessage(data.error || "Access denied due to time-based restrictions");
          } else if (data.error.includes("geo") || data.error.includes("country") || data.error.includes("location")) {
            setErrorMessage(data.error || "Access denied due to geo-location restrictions");
          } else if (data.error.includes("IP") || data.error.includes("whitelist")) {
            setErrorMessage(data.error || "Access denied: Your IP address is not whitelisted");
          } else {
            setErrorMessage(data.error || "Access denied due to security restrictions");
          }
          return;
        }
        
        // Handle all other errors - maintain phase for 2FA and secret_word
        setFingerprintScanLines(false);
        setShowFingerprint(false);
        
        if (loginPhase === '2fa') {
          // Stay in 2FA phase but show error
          setErrorMessage(data.error || "Invalid verification code");
          setErrorType('credentials');
        } else if (loginPhase === 'secret_word') {
          // Stay in secret_word phase but show error
          setErrorMessage(data.error || "Invalid secret word");
          setErrorType('credentials');
        } else {
          // For username/password phase, reset to idle
          setLoginPhase('idle');
          setErrorMessage(data.error || "Invalid username or password");
          setErrorType('credentials');
        }
      }
    } catch (error) {
      console.error('Login error:', error);
      
      setFingerprintScanLines(false);
      setShowFingerprint(false);
      
      // Maintain phase for 2FA and secret_word on network errors
      if (loginPhase !== '2fa' && loginPhase !== 'secret_word') {
        setLoginPhase('idle');
      }
      
      setErrorType('server');
      setErrorMessage("An unexpected error occurred. Please try again.");
    }
  };
  
  // Calculate remaining time for login block
  const getRemainingBlockTime = () => {
    if (!loginBlockedUntil) return '';
    
    const now = new Date();
    const diffMs = loginBlockedUntil.getTime() - now.getTime();
    if (diffMs <= 0) return '';
    
    const diffMins = Math.ceil(diffMs / (1000 * 60));
    return `(${diffMins} minutes)`;
  };

  // Render login form fields based on current phase
  const renderFormFields = () => {
    // If account is banned, don't render any input fields
    if (accountBanned) {
      return (
        <div className="space-y-5">
          <div className="mb-4 text-center">
            <h3 className="text-lg font-medium text-white">Account Suspended</h3>
            <p className="text-sm text-gray-400">This account has been temporarily suspended.</p>
            <p className="text-sm text-gray-400 mt-2">Please contact support for assistance.</p>
          </div>
        </div>
      );
    }

    if (loginPhase === '2fa') {
      return (
        <div className="space-y-5">
          <div className="mb-4 text-center">
            <h3 className="text-lg font-medium text-white">Two-Factor Authentication</h3>
            <p className="text-sm text-gray-400">Enter the verification code from your authenticator app</p>
          </div>
          <div>
            <OtpInput 
              value={verificationCode}
              onChange={setVerificationCode}
              error={!!errorMessage}
              disabled={loginBlocked}
            />
          </div>
          <div className="flex justify-between items-center">
            <button
              type="button"
              onClick={resetAuthStates}
              className="text-sm text-[#D4D5F4]/70 hover:text-[#D4D5F4] transition-colors"
            >
              &larr; Back
            </button>
          </div>
        </div>
      );
    } else if (loginPhase === 'secret_word') {
      return (
        <div className="space-y-5">
          <div className="mb-4 text-center">
            <h3 className="text-lg font-medium text-white">Secret Word Verification</h3>
            <p className="text-sm text-gray-400">Enter your personal secret word</p>
          </div>
          <div>
            <InnovativeInput 
              type="password"
              placeholder="Enter your secret word"
              value={secretWord}
              onChange={(e) => setSecretWord(e.target.value)}
              icon={Key}
              error={!!errorMessage}
              disabled={loginBlocked}
            />
          </div>
          <div className="flex justify-between items-center">
            <button
              type="button"
              onClick={resetAuthStates}
              className="text-sm text-[#D4D5F4]/70 hover:text-[#D4D5F4] transition-colors"
            >
              &larr; Back
            </button>
          </div>
        </div>
      );
    } else {
      // Default username/password form
      return (
        <div className="space-y-5">
          <div>
            <InnovativeInput 
              type="text"
              placeholder="Enter your username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              icon={User}
              error={loginPhase === 'error' && (errorType === 'credentials' || errorType === 'permission')}
              disabled={loginBlocked || loginPhase === 'connecting' || loginPhase === 'connected' || accountBanned}
            />
          </div>
          
          <div>
            <InnovativeInput 
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              icon={Lock}
              error={loginPhase === 'error' && (errorType === 'credentials' || errorType === 'permission')}
              disabled={loginBlocked || loginPhase === 'connecting' || loginPhase === 'connected' || accountBanned}
            />
          </div>
          
          {/* Remember me checkbox */}
          <div className="flex items-center mt-3">
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                id="remember-me"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                disabled={loginBlocked || loginPhase === 'connecting' || loginPhase === 'connected' || accountBanned}
                className="sr-only peer"
              />
              <div className="w-5 h-5 bg-[#0d1117]/80 border border-[#D4D5F4]/30 rounded transition-all duration-200 
                peer-checked:bg-[#6C5DD3]/30 peer-checked:border-[#6C5DD3] 
                peer-focus:ring-2 peer-focus:ring-[#6C5DD3]/30 relative">
                {rememberMe && (
                  <motion.div 
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="absolute inset-0 flex items-center justify-center"
                  >
                    <svg className="w-3 h-3 text-[#D4D5F4]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  </motion.div>
                )}
              </div>
              <span className="ml-2 text-sm text-[#D4D5F4]/80 hover:text-[#D4D5F4] transition-colors duration-200">
                Remember me
              </span>
            </label>
          </div>
        </div>
      );
    }
  };

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
        ref={containerRef}
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        transition={{ type: "spring", bounce: 0.2, duration: 0.7 }}
        className={`relative w-full max-w-md backdrop-blur-lg rounded-2xl overflow-hidden shadow-xl ${accountBanned ? 'border-2 border-red-800' : ''}`}
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

          {/* Login form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {renderFormFields()}
            
            {/* Ban message */}
            {accountBanned && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center text-sm px-4 py-3 rounded-lg bg-red-500/20 text-red-300 border border-red-500/30"
              >
                <div className="flex items-center justify-center">
                  <XCircle className="w-5 h-5 mr-2" />
                  <span className="font-semibold">This account has been temporarily suspended. Please contact support.</span>
                </div>
              </motion.div>
            )}
            
            {/* Add error message display with animation */}
            {errorMessage && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3 }}
                className={`
                  flex items-center text-sm bg-opacity-25 rounded-md p-3 mb-4
                  ${errorType === 'credentials' ? 'bg-red-500/20 text-red-400' : ''}
                  ${errorType === 'server' ? 'bg-yellow-500/20 text-yellow-400' : ''}
                  ${errorType === 'permission' ? 'bg-red-500/20 text-red-400' : ''}
                  ${errorType === 'security_restriction' ? 'bg-indigo-500/20 text-indigo-400' : ''}
                  ${errorType === 'rate_limit' ? 'bg-yellow-500/20 text-yellow-400 rate-limit-message' : 'error-message'}
                  ${errorType === 'banned' ? 'bg-red-500/20 text-red-400' : ''}
                `}
              >
                <div className="flex items-center">
                  {errorType === 'credentials' ? (
                    <AlertTriangle className="w-4 h-4 mr-2" />
                  ) : errorType === 'server' ? (
                    <AlertTriangle className="w-4 h-4 mr-2" />
                  ) : errorType === 'security_restriction' ? (
                    errorMessage.includes("time-based") ? (
                      <Clock className="w-4 h-4 mr-2" />
                    ) : errorMessage.includes("geo") || errorMessage.includes("country") ? (
                      <Globe className="w-4 h-4 mr-2" />
                    ) : errorMessage.includes("IP") ? (
                      <Shield className="w-4 h-4 mr-2" />
                    ) : (
                      <Lock className="w-4 h-4 mr-2" />
                    )
                  ) : (
                    <AlertTriangle className="w-4 h-4 mr-2" />
                  )}
                  <span>{errorMessage}</span>
                </div>
                {errorType === 'rate_limit' && getRemainingBlockTime() && (
                  <div className="text-xs mt-1 text-yellow-300/70">
                    {getRemainingBlockTime()}
                  </div>
                )}
                {errorType === 'security_restriction' && (
                  <div className="text-xs mt-2 text-indigo-300/70 bg-indigo-500/10 p-2 rounded">
                    {errorMessage.includes("time-based") 
                      ? "Your wallet is only accessible during specified hours." 
                      : errorMessage.includes("geo") || errorMessage.includes("country")
                      ? (errorMessage.includes("Your wallet is only accessible from") && errorMessage.includes("country"))
                        ? `Your wallet is only accessible from your registered country. ${errorMessage.split("from ")[1] || ""}`
                        : "Your wallet is only accessible from your specified location."
                      : errorMessage.includes("IP") 
                      ? errorMessage.includes("Your IP address (") 
                        ? "Please add your current IP address to your whitelist."
                        : "Your wallet is only accessible from whitelisted IP addresses."
                      : "Your wallet access is restricted due to security settings."
                    }
                  </div>
                )}
              </motion.div>
            )}
            
            <div className="pt-4">
              <motion.button
                type="submit"
                disabled={loginBlocked || loginPhase === 'connecting' || loginPhase === 'connected' || loginPhase === 'verifying' || accountBanned}
                className={`
                  relative w-full py-4 rounded-lg overflow-hidden group
                  ${accountBanned 
                    ? 'bg-red-800/30 cursor-not-allowed' 
                    : loginPhase === 'error' 
                    ? 'bg-red-500/20' 
                    : loginBlocked 
                    ? 'bg-yellow-500/20' 
                    : loginPhase === 'verifying'
                    ? 'bg-[#6A6EE5]/20'
                    : 'bg-[#D4D5F4]/20'
                  }
                  disabled:opacity-70 disabled:cursor-not-allowed
                `}
                whileHover={{ 
                  scale: loginBlocked || loginPhase === 'connecting' || loginPhase === 'connected' || loginPhase === 'verifying' || accountBanned ? 1 : 1.03,
                  backgroundColor: loginPhase === '2fa' || loginPhase === 'secret_word' ? 'rgba(106, 110, 229, 0.3)' : ''
                }}
                whileTap={{ 
                  scale: loginBlocked || loginPhase === 'connecting' || loginPhase === 'connected' || loginPhase === 'verifying' || accountBanned ? 1 : 0.98 
                }}
                transition={{ 
                  type: 'spring', 
                  stiffness: 400, 
                  damping: 17 
                }}
              >
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-r from-[#D4D5F4]/30 to-transparent"></div>
                
                {accountBanned ? (
                  <div className="flex items-center justify-center space-x-2">
                    <span className="text-white font-medium">Account Suspended</span>
                    <X className="w-5 h-5 text-white" />
                  </div>
                ) : (loginPhase === 'idle' || loginPhase === '2fa' || loginPhase === 'secret_word') && !loginBlocked ? (
                  <motion.div 
                    className="flex items-center justify-center space-x-2"
                    animate={{}}
                    whileHover={{ 
                      scale: 1.05,
                      transition: { duration: 0.2 }
                    }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <span className="text-white font-medium">
                      {loginPhase === 'idle' ? 'Connect to Wallet' : 
                       loginPhase === '2fa' ? 'Verify Code' : 'Verify Secret Word'}
                    </span>
                    {loginPhase === 'idle' ? (
                      <ArrowRight className="w-5 h-5 text-[#D4D5F4]" />
                    ) : loginPhase === '2fa' ? (
                      <Code className="w-5 h-5 text-[#D4D5F4]" />
                    ) : (
                      <Key className="w-5 h-5 text-[#D4D5F4]" />
                    )}
                  </motion.div>
                ) : loginPhase === 'connecting' || loginPhase === 'verifying' ? (
                  <div className="flex items-center justify-center space-x-2">
                    <RotateCcw className="w-5 h-5 text-[#D4D5F4] animate-spin" />
                    <span className="text-white font-medium">
                      {loginPhase === 'connecting' ? 'Connecting...' : 
                        loginPhase === 'verifying' && verificationCode ? 'Verifying Code...' : 'Verifying...'}
                    </span>
                  </div>
                ) : loginPhase === 'connected' ? (
                  <div className="flex items-center justify-center space-x-2">
                    <span className="text-white font-medium">Connected!</span>
                    <CheckCircle className="w-5 h-5 text-green-400 animate-pulse" />
                  </div>
                ) : loginPhase === 'error' ? (
                  <div className="flex items-center justify-center space-x-2">
                    <span className="text-white font-medium">Connection Failed</span>
                    <X className="w-5 h-5 text-white" />
                  </div>
                ) : loginBlocked && (
                  <div className="flex items-center justify-center space-x-2">
                    <Lock className="w-5 h-5 text-yellow-300" />
                    <span className="text-yellow-300 font-medium">Try Again Later</span>
                  </div>
                )}
              </motion.button>
            </div>
            
            {/* Show forgot password link ALWAYS when we're in the username/password phase */}
            {(loginPhase === 'idle' || errorType !== 'rate_limit') && !accountBanned && hasWallet && (
              <div className="mt-2 text-center">
                <a href="/reset-password" className="text-[#D4D5F4]/70 hover:text-[#D4D5F4] text-sm hover:underline">
                  Forgot password?
                </a>
              </div>
            )}
            
            {/* Add signup link - only if not banned and user doesn't have a wallet */}
            {loginPhase === 'idle' && !hasWallet && !accountBanned && (
              <div className="mt-6 text-center">
                <p className="text-[#D4D5F4]/70">
                  Don't have a wallet? <a href="/signup" className="text-[#D4D5F4] hover:underline">Create one</a>
                </p>
              </div>
            )}
          </form>
          
          {/* Empty space where the orbit system was */}
          <div className="mt-10 h-10"></div>
        </div>
      </motion.div>
      
      {/* Fingerprint verification overlay */}
      <AnimatePresence>
        {showFingerprint && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 flex items-center justify-center bg-black/80 backdrop-blur-lg z-50"
          >
            <motion.div 
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              transition={{ type: "spring", stiffness: 500, damping: 30 }}
              className="bg-[#0a0e1a]/90 rounded-xl p-8 shadow-2xl border border-[#D4D5F4]/20 max-w-sm w-full"
            >
              <div className="text-center">
                <div className="relative mx-auto w-24 h-24 mb-5">
                  {/* Pulsating background */}
                  <motion.div
                    animate={{ 
                      scale: [1, 1.1, 1],
                      opacity: [0.5, 0.8, 0.5]
                    }}
                    transition={{ 
                      repeat: Infinity, 
                      duration: 2,
                      ease: "easeInOut"
                    }}
                    className="absolute inset-0 rounded-full bg-[#D4D5F4]/20"
                  />
                  
                  {/* Fingerprint container */}
                  <div className="absolute inset-0 rounded-full bg-[#D4D5F4]/10 flex items-center justify-center overflow-hidden border border-[#D4D5F4]/30">
                    {/* Scan line animation */}
                    {fingerprintScanLines && (
                      <motion.div 
                        initial={{ y: -140 }}
                        animate={{ y: 140 }}
                        transition={{
                          duration: 1.5,
                          ease: "linear",
                          repeat: Infinity,
                        }}
                        className="absolute w-full h-1 bg-gradient-to-r from-transparent via-[#D4D5F4]/80 to-transparent"
                      />
                    )}
                    
                    {/* Success/Error effect when matched */}
                    {fingerprintMatched && (
                <motion.div
                        initial={{ scale: 0, opacity: 0 }}
                        animate={{ scale: [0, 1.2, 1], opacity: [0, 1, 1] }}
                        transition={{ duration: 0.5 }}
                        className={`absolute inset-0 ${errorType === 'credentials' ? 'bg-yellow-500/20' : errorType === 'server' ? 'bg-yellow-500/20' : errorType === 'permission' ? 'bg-yellow-500/20' : 'bg-green-500/20'} rounded-full flex items-center justify-center`}
                      >
                        <motion.div
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          transition={{ delay: 0.2, type: "spring" }}
                          className={`${
                            errorType === 'credentials' 
                              ? 'bg-yellow-500/90' 
                              : errorType === 'server' 
                              ? 'bg-yellow-500/90' 
                              : errorType === 'permission' 
                              ? 'bg-yellow-500/90' 
                              : 'bg-green-500/90'
                          } text-white rounded-full p-2`}
                        >
                          <motion.div
                            animate={{ rotate: [0, 10, 0] }}
                            transition={{ duration: 0.3, delay: 0.3 }}
                          >
                            {errorType === 'credentials' && <AlertTriangle size={24} />}
                            {errorType === 'permission' && <AlertTriangle size={24} />}
                            {errorType === 'server' && <AlertTriangle size={24} />}
                            {(!errorType || errorType === null) && <ShieldCheck size={24} />}
                          </motion.div>
                        </motion.div>
                      </motion.div>
                    )}
                    
                    {/* Fingerprint icon */}
                    <motion.div
                      animate={{
                        opacity: fingerprintMatched ? 0.3 : [0.8, 1, 0.8],
                        scale: fingerprintMatched ? 0.9 : 1
                      }}
                      transition={{
                        duration: 2,
                        repeat: fingerprintMatched ? 0 : Infinity,
                      }}
                    >
                      <Fingerprint className={`${
                        fingerprintMatched 
                          ? (errorType === 'credentials' 
                            ? 'text-yellow-300' 
                            : errorType === 'permission'
                            ? 'text-yellow-300'
                            : errorType === 'server'
                            ? 'text-yellow-300'
                            : 'text-green-300')
                          : 'text-[#D4D5F4]'
                      }`} size={76} />
                    </motion.div>
                      </div>
                    </div>

                <h3 className="text-white text-xl font-semibold mb-2 relative z-10">
                  {fingerprintMatched 
                    ? (errorType ? 'Invalid Credentials' : 'Verification Success')
                    : 'Verifying'
                  }
                </h3>
                
                <p className="text-gray-400 text-sm text-center relative z-10 max-w-xs mx-auto">
                  {fingerprintMatched 
                    ? (errorType ? 'Invalid credentials' : 'Identity verified successfully. Preparing dashboard...')
                    : 'Verifying your identity and access permissions...'
                  }
                </p>
                
                {/* Loading dots */}
                <div className="flex justify-center space-x-2 mt-4">
                  <motion.div
                    animate={{ scale: [0.5, 1, 0.5], opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 1, repeat: Infinity, delay: 0 }}
                    className={`w-2 h-2 rounded-full ${errorType ? 'bg-yellow-400' : 'bg-[#D4D5F4]'}`}
                  />
                  <motion.div
                    animate={{ scale: [0.5, 1, 0.5], opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 1, repeat: Infinity, delay: 0.2 }}
                    className={`w-2 h-2 rounded-full ${errorType ? 'bg-yellow-400' : 'bg-[#D4D5F4]'}`}
                  />
                  <motion.div
                    animate={{ scale: [0.5, 1, 0.5], opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 1, repeat: Infinity, delay: 0.4 }}
                    className={`w-2 h-2 rounded-full ${errorType ? 'bg-yellow-400' : 'bg-[#D4D5F4]'}`}
                        />
                      </div>
                    </div>
            </motion.div>
                </motion.div>
              )}
            </AnimatePresence>
    </div>
  );
};

export default Login;

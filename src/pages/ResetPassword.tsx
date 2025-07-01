import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Eye, EyeOff, Lock, Mail, ArrowRight, X, RotateCcw, Sparkles, AlertTriangle, 
  ShieldCheck, XCircle, Key, ChevronLeft, CheckCircle
} from 'lucide-react';
import { useNavigate, useLocation } from "react-router-dom";
import '../Login.css';

// Import components we'll reuse from Login.tsx
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

const ResetPassword: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const stars = useStarsBackground();
  
  // Parse token from query parameters
  const queryParams = new URLSearchParams(location.search);
  const tokenFromQuery = queryParams.get('token');
  
  // State variables
  const [email, setEmail] = useState('');
  const [resetToken, setResetToken] = useState(tokenFromQuery || '');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [resetPhase, setResetPhase] = useState<'request' | 'verify' | 'reset' | 'success' | 'error'>(
    tokenFromQuery ? 'verify' : 'request'
  );
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  
  // CSRF token state
  const [csrfToken, setCsrfToken] = useState<string>('');
  
  // Fetch CSRF token (نفس أسلوب Transfers.tsx)
  const fetchCsrfToken = async () => {
    try {
      const response = await fetch('/api/csrf-token', {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.csrf_token) {
          setCsrfToken(data.csrf_token);
          return data.csrf_token;
        }
      }
    } catch (error) {
      console.error('Error fetching CSRF token:', error);
    }
    return null;
  };
  
  // جلب التوكن عند أول تحميل
  useEffect(() => {
    fetchCsrfToken();
  }, []);
  
  // Validate token when component loads if token is in URL
  useEffect(() => {
    if (tokenFromQuery) {
      validateToken(tokenFromQuery);
    }
  }, [tokenFromQuery, csrfToken]);
  
  // Validate the reset token
  const validateToken = async (token: string) => {
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch('/api/password/validate-token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfToken || '',
        },
        body: JSON.stringify({ token }),
      });
      
      const data = await response.json();
      
      if (response.ok && data.valid) {
        // Token is valid, proceed to reset password phase
        setResetPhase('reset');
      } else {
        // Token is invalid, expired, or already used
        setError(data.error || 'This reset link is no longer valid. Please request a new password reset.');
        setResetPhase('error');
      }
    } catch (error) {
      console.error('Error validating token:', error);
      setError('Failed to validate token. Please try again.');
      setResetPhase('error');
    } finally {
      setLoading(false);
    }
  };
  
  // Handle password reset request
  const handleRequestReset = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email.trim()) {
      setError('Please enter your email address.');
      return;
    }
    
    setLoading(true);
    setError('');
    
    // إذا لم يوجد التوكن، جلبه ثم أعد المحاولة
    if (!csrfToken) {
      const token = await fetchCsrfToken();
      if (token) {
        setCsrfToken(token);
        // أعد المحاولة بعد جلب التوكن
        setTimeout(() => handleRequestReset(e), 100);
      } else {
        setError('Failed to get security token. Please refresh the page.');
        setLoading(false);
      }
      return;
    }
    
    try {
      const response = await fetch('/api/password/request-reset', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfToken,
        },
        body: JSON.stringify({ email: email.trim() }),
      });
      
      const data = await response.json();
      
      if (response.ok) {
        // Check if there's a wait time in the response (rate limiting)
        if (data.wait_time) {
          const minutes = Math.ceil(data.wait_time / 60);
          setError(`Please wait ${minutes} minutes before requesting another password reset.`);
          setLoading(false);
        } else {
          setMessage(data.message || 'If your email is registered, you will receive password reset instructions.');
          setResetPhase('success');
        }
      } else {
        setError(data.error || 'Failed to process your request. Please try again.');
      }
    } catch (error) {
      console.error('Error requesting password reset:', error);
      setError('An unexpected error occurred. Please try again later.');
    } finally {
      setLoading(false);
    }
  };
  
  // Handle password reset form submission
  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate passwords
    if (!password) {
      setError('Please enter a new password.');
      return;
    }
    
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    
    // Basic password length check (minimum 8 characters)
    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }
    
    // Basic client-side password strength validation
    const hasUppercase = /[A-Z]/.test(password);
    const hasLowercase = /[a-z]/.test(password);
    const hasDigits = /\d/.test(password);
    const hasSpecialChars = /[!@#$%^&*()_\-+=<>?/\[\]{}]/.test(password);
    
    // Create a message about what's missing
    const missing = [];
    if (!hasUppercase) missing.push("uppercase letter");
    if (!hasLowercase) missing.push("lowercase letter");
    if (!hasDigits) missing.push("number");
    if (!hasSpecialChars) missing.push("special character");
    
    if (missing.length > 0) {
      setError(`Password must include at least one ${missing.join(', one ')}.`);
      return;
    }
    
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch('/api/password/reset', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfToken || '',
        },
        body: JSON.stringify({
          token: resetToken,
          new_password: password,
        }),
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setMessage(data.message || 'Password has been reset successfully. You can now log in with your new password.');
        setResetPhase('success');
      } else {
        // Check if token was already used or expired
        if (data.error && (data.error.includes("already been used") || data.error.includes("expired"))) {
          setError(data.error);
          setResetPhase('error');
        } else {
          setError(data.error || 'Failed to reset password. Please try again.');
        }
      }
    } catch (error) {
      console.error('Error resetting password:', error);
      setError('An unexpected error occurred. Please try again later.');
    } finally {
      setLoading(false);
    }
  };
  
  // Render different forms based on current phase
  const renderForm = () => {
    switch (resetPhase) {
      case 'request':
        return (
          <form onSubmit={handleRequestReset} className="space-y-5">
            <div className="mb-6 text-center">
              <h2 className="text-xl text-white font-semibold">Reset Your Password</h2>
              <p className="text-[#D4D5F4]/70 mt-2">
                Enter your email address and we'll send you a link to reset your password.
              </p>
              <p className="text-[#D4D5F4]/60 mt-2 text-sm">
                <AlertTriangle className="w-3 h-3 inline-block mr-1" />
                Password reset is only available for users with existing wallets.
              </p>
              <p className="text-[#D4D5F4]/50 mt-1 text-xs">
                Note: You can only request a password reset once every 5 minutes.
              </p>
            </div>
            
            <div>
              <InnovativeInput 
                type="email"
                placeholder="Enter your email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                icon={Mail}
                error={!!error}
                disabled={loading}
              />
            </div>
            
            {error && (
              <div className="text-red-500 text-sm bg-red-500/10 border border-red-500/20 rounded-lg p-2 flex items-center">
                <AlertTriangle className="w-4 h-4 mr-2 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}
            
            <div className="pt-4">
              <button
                type="submit"
                disabled={loading || !csrfToken}
                className={`
                  relative w-full py-4 rounded-lg overflow-hidden group
                  ${loading ? 'bg-[#D4D5F4]/10' : 'bg-[#D4D5F4]/20'}
                  disabled:opacity-70 disabled:cursor-not-allowed
                `}
              >
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-r from-[#D4D5F4]/30 to-transparent"></div>
                
                {loading ? (
                  <div className="flex items-center justify-center space-x-2">
                    <RotateCcw className="w-5 h-5 text-[#D4D5F4] animate-spin" />
                    <span className="text-white font-medium">Sending...</span>
                  </div>
                ) : (
                  <div className="flex items-center justify-center space-x-2">
                    <span className="text-white font-medium">Send Reset Link</span>
                    <ArrowRight className="w-5 h-5 text-[#D4D5F4]" />
                  </div>
                )}
              </button>
            </div>
            
            <div className="mt-6 text-center">
              <button 
                type="button" 
                onClick={() => navigate('/login')}
                className="text-[#D4D5F4]/70 hover:text-[#D4D5F4] inline-flex items-center"
              >
                <ChevronLeft className="w-4 h-4 mr-1" />
                Back to Login
              </button>
            </div>
          </form>
        );
        
      case 'reset':
        return (
          <form onSubmit={handleResetPassword} className="space-y-5">
            <div className="mb-6 text-center">
              <h2 className="text-xl text-white font-semibold">Create New Password</h2>
              <p className="text-[#D4D5F4]/70 mt-2">
                Enter your new password below.
              </p>
            </div>
            
            <div>
              <InnovativeInput 
                type="password"
                placeholder="Enter new password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                icon={Lock}
                error={!!error}
                disabled={loading}
              />
              <div className="mt-2 text-xs text-[#D4D5F4]/60 pl-2">
                <p>Password must:</p>
                <ul className="list-disc pl-5 space-y-1 mt-1">
                  <li className={password.length >= 8 ? "text-green-500/70" : ""}>Be at least 8 characters</li>
                  <li className={/[A-Z]/.test(password) ? "text-green-500/70" : ""}>Include at least one uppercase letter</li>
                  <li className={/[a-z]/.test(password) ? "text-green-500/70" : ""}>Include at least one lowercase letter</li>
                  <li className={/\d/.test(password) ? "text-green-500/70" : ""}>Include at least one number</li>
                  <li className={/[!@#$%^&*()_\-+=<>?/[\]{}]/.test(password) ? "text-green-500/70" : ""}>Include at least one special character</li>
                </ul>
              </div>
            </div>
            
            <div>
              <InnovativeInput 
                type="password"
                placeholder="Confirm new password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                icon={Lock}
                error={!!error}
                disabled={loading}
              />
              {password && confirmPassword && (
                <div className="mt-2 text-xs pl-2">
                  {password === confirmPassword ? (
                    <span className="text-green-500">Passwords match</span>
                  ) : (
                    <span className="text-red-500">Passwords do not match</span>
                  )}
                </div>
              )}
            </div>
            
            {error && (
              <div className="text-red-500 text-sm bg-red-500/10 border border-red-500/20 rounded-lg p-2 flex items-center">
                <AlertTriangle className="w-4 h-4 mr-2 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}
            
            <div className="pt-4">
              <button
                type="submit"
                disabled={loading || !csrfToken}
                className={`
                  relative w-full py-4 rounded-lg overflow-hidden group
                  ${loading ? 'bg-[#D4D5F4]/10' : 'bg-[#D4D5F4]/20'}
                  disabled:opacity-70 disabled:cursor-not-allowed
                `}
              >
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-r from-[#D4D5F4]/30 to-transparent"></div>
                
                {loading ? (
                  <div className="flex items-center justify-center space-x-2">
                    <RotateCcw className="w-5 h-5 text-[#D4D5F4] animate-spin" />
                    <span className="text-white font-medium">Updating...</span>
                  </div>
                ) : (
                  <div className="flex items-center justify-center space-x-2">
                    <span className="text-white font-medium">Reset Password</span>
                    <Key className="w-5 h-5 text-[#D4D5F4]" />
                  </div>
                )}
              </button>
            </div>
          </form>
        );
        
      case 'success':
        return (
          <div className="space-y-5 text-center">
            <div className="flex justify-center">
              <div className="bg-green-500/20 p-4 rounded-full">
                <CheckCircle className="w-12 h-12 text-green-500" />
              </div>
            </div>
            
            <h2 className="text-xl text-white font-semibold">Success!</h2>
            
            <p className="text-[#D4D5F4]/70">
              {message || "Password reset request processed successfully."}
            </p>
            
            <div className="pt-6">
              <button
                type="button"
                onClick={() => navigate('/login')}
                className="relative py-3 px-8 rounded-lg overflow-hidden group bg-[#D4D5F4]/20 hover:bg-[#D4D5F4]/30 transition-colors"
              >
                <span className="text-white font-medium">Return to Login</span>
              </button>
            </div>
          </div>
        );
        
      case 'error':
        return (
          <div className="space-y-5 text-center">
            <div className="flex justify-center">
              <div className="bg-red-500/20 p-4 rounded-full">
                <XCircle className="w-12 h-12 text-red-500" />
              </div>
            </div>
            
            <h2 className="text-xl text-white font-semibold">Something Went Wrong</h2>
            
            <p className="text-[#D4D5F4]/70">
              {error || "We encountered an error processing your request."}
            </p>
            
            <div className="pt-6 flex justify-center space-x-4">
              <button
                type="button"
                onClick={() => setResetPhase('request')}
                className="relative py-3 px-6 rounded-lg overflow-hidden group bg-[#D4D5F4]/20 hover:bg-[#D4D5F4]/30 transition-colors"
              >
                <span className="text-white font-medium">Try Again</span>
              </button>
              
              <button
                type="button"
                onClick={() => navigate('/login')}
                className="relative py-3 px-6 rounded-lg overflow-hidden group bg-transparent border border-[#D4D5F4]/20 hover:border-[#D4D5F4]/40 transition-colors"
              >
                <span className="text-[#D4D5F4]/80 font-medium">Return to Login</span>
              </button>
            </div>
          </div>
        );
        
      case 'verify':
        return (
          <div className="space-y-5 text-center">
            <div className="flex justify-center">
              <div className="p-4">
                <RotateCcw className="w-10 h-10 text-[#D4D5F4] animate-spin" />
              </div>
            </div>
            
            <h2 className="text-xl text-white font-semibold">Verifying Reset Link</h2>
            
            <p className="text-[#D4D5F4]/70">
              Please wait while we verify your password reset link...
            </p>
          </div>
        );
        
      default:
        return null;
    }
  };
  
  return (
    <div className="fixed inset-0 flex items-center justify-center p-4 z-50">
      {/* Backdrop with animated stars - same style as Login.tsx */}
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
      
      {/* Reset password container with style consistent with Login.tsx */}
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
        {/* Glowing border */}
        <div className="absolute inset-0 p-px rounded-2xl overflow-hidden pointer-events-none">
          <div className="absolute inset-0 rounded-2xl" 
            style={{
              background: 'linear-gradient(135deg, rgba(90, 100, 255, 0.1), rgba(41, 46, 117, 0.03), rgba(60, 100, 180, 0.1))',
              opacity: 0.3
            }}
          ></div>
        </div>
        
        {/* Subtle glow effect */}
        <div className="absolute inset-0"
          style={{
            background: 'radial-gradient(circle at 30% 40%, rgba(62, 76, 179, 0.03) 0%, transparent 60%), radial-gradient(circle at 70% 60%, rgba(65, 96, 179, 0.02) 0%, transparent 60%)'
          }}
        ></div>
        
        {/* Moving subtle pattern */}
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

          {/* Form content */}
          {renderForm()}
        </div>
      </motion.div>
    </div>
  );
};

export default ResetPassword; 
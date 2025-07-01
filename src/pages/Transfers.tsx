import React, { useState, useEffect } from 'react';
import { 
  ArrowRight,
  Shield,
  AlertCircle,
  Info,
  Download,
  CheckCircle,
  ArrowRightCircle,
  TrendingUp,
  Clock,
  Send,
  Settings,
  Cog,
  Hammer,
  Star,
  MessageCircle,
  User,
  SnowflakeIcon,
  Check
} from 'lucide-react';
import clsx from 'clsx';
import jsPDF from 'jspdf';
// Remove the autoTable extension for now
// import 'jspdf-autotable';

// Remove the type extension

// Define interface for rating component props
interface RatingStarsProps {
  rating: number;
  setRating: (rating: number) => void;
  size?: number;
  disabled?: boolean;
  animate?: boolean;
}

// Rating Component
const RatingStars = ({ 
  rating, 
  setRating, 
  size = 32, 
  disabled = false,
  animate = true
}: RatingStarsProps) => {
  const [hover, setHover] = useState(0);
  
  return (
    <div className="flex items-center">
      {[1, 2, 3, 4, 5].map((star) => (
        <Star
          key={star}
          size={size}
          onClick={() => !disabled && setRating(star)}
          onMouseEnter={() => !disabled && setHover(star)}
          onMouseLeave={() => !disabled && setHover(0)}
          className={clsx(
            'cursor-pointer transition-all duration-200',
            animate && 'hover:scale-110',
            (hover || rating) >= star 
              ? 'text-yellow-400 fill-yellow-400'
              : 'text-gray-300',
            disabled && 'cursor-default opacity-80'
          )}
        />
      ))}
    </div>
  );
};

const MaintenanceScreen = () => {
  return (
    <div className="max-w-3xl mx-auto bg-gray-800 p-6 sm:p-10 rounded-3xl shadow-lg border border-gray-700 transition-all duration-500 animate-fadeIn">
      <div className="flex flex-col items-center text-center">
        <div className="relative w-28 h-28 sm:w-40 sm:h-40 mb-6">
          {/* Large rotating cog */}
          <Cog 
            size={80} 
            className="absolute text-[#8875FF] opacity-80 animate-spin-slow left-4 top-6 sm:left-4 sm:top-6" 
          />
          
          {/* Smaller counter-rotating cog */}
          <Cog 
            size={48} 
            className="absolute text-indigo-400 opacity-90 animate-spin-reverse left-12 top-2 sm:left-16 sm:top-2" 
          />
          
          {/* Hammer animation */}
          <Hammer 
            size={48} 
            className="absolute text-gray-400 right-0 bottom-0 animate-hammer" 
          />
        </div>
        
        <h2 className="text-3xl font-bold text-gray-300 mb-3">System Maintenance</h2>
        
        <p className="text-gray-400 text-lg mb-4">
          We're currently performing maintenance on our transfer system.
        </p>
        
        <p className="text-gray-500">
          Please check back shortly.
        </p>
      </div>
    </div>
  );
};

// Define interface for rating modal props
interface RatingModalProps {
  isOpen: boolean;
  onClose: () => void;
  recipientId: string;
  recipientUsername: string;
  onRatingSubmitted: () => void;
  csrfToken: string | null;
  fetchCsrfToken: () => Promise<string | null>;
}

// Rating Modal Component
const RatingModal = ({ 
  isOpen, 
  onClose, 
  recipientId, 
  recipientUsername, 
  onRatingSubmitted,
  csrfToken,
  fetchCsrfToken
}: RatingModalProps) => {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  
  // Maximum comment length
  const MAX_COMMENT_LENGTH = 300;
  
  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setRating(0);
      setComment('');
      setError('');
      setSuccess(false);
    }
  }, [isOpen]);
  
  const handleSubmit = async () => {
    if (rating === 0) {
      setError('Please select a rating');
      return;
    }
    
    // Validate comment length
    if (comment.length > MAX_COMMENT_LENGTH) {
      setError(`Comment cannot exceed ${MAX_COMMENT_LENGTH} characters`);
      return;
    }
    
    setIsSubmitting(true);
    setError('');
    
    try {
      // Get CSRF token - ensure we have a fresh token
      let token = csrfToken;
      if (!token) {
        token = await fetchCsrfToken();
      }
      
      // If still no token, try to submit without it (rating endpoints are exempt)
      const headers: Record<string, string> = {
        'Content-Type': 'application/json'
      };
      
      if (token) {
        headers['X-CSRF-Token'] = token;
      }
      
      const response = await fetch('/api/ratings/submit', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          recipient_id: recipientId,
          stars: rating,
          comment: comment.trim() || null
        }),
        credentials: 'include'
      });
      
      if (response.ok) {
        setSuccess(true);
        setTimeout(() => {
          onRatingSubmitted();
          onClose();
        }, 1500);
      } else if (response.status === 403) {
        // If CSRF token is invalid, try to get a new one and retry once
        const newToken = await fetchCsrfToken();
        if (newToken) {
          headers['X-CSRF-Token'] = newToken;
          const retryResponse = await fetch('/api/ratings/submit', {
            method: 'POST',
            headers,
            body: JSON.stringify({
              recipient_id: recipientId,
              stars: rating,
              comment: comment.trim() || null
            }),
            credentials: 'include'
          });
          
          if (retryResponse.ok) {
            setSuccess(true);
            setTimeout(() => {
              onRatingSubmitted();
              onClose();
            }, 1500);
          } else {
            const data = await retryResponse.json();
            setError(data.error || 'Failed to submit rating after retry');
          }
        } else {
          setError('Security token expired. Please refresh the page and try again.');
        }
      } else {
        const data = await response.json();
        setError(data.error || 'Failed to submit rating');
      }
    } catch (error) {
      console.error('Error submitting rating:', error);
      setError('An error occurred. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const handleCommentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newComment = e.target.value;
    setComment(newComment);
    
    // Clear error message if previous error was about comment length
    if (error.includes('characters') && newComment.length <= MAX_COMMENT_LENGTH) {
      setError('');
    }
  };
  
  const getCharCountColor = () => {
    const remaining = MAX_COMMENT_LENGTH - comment.length;
    if (remaining < 0) return 'text-red-400';
    if (remaining < 20) return 'text-yellow-400';
    return 'text-gray-400';
  };
  
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 flex items-center justify-center z-50 px-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black bg-opacity-60 backdrop-blur-sm" 
        onClick={onClose}
      ></div>
      
      {/* Modal */}
      <div className="bg-gray-800 rounded-3xl p-6 sm:p-8 shadow-xl max-w-md w-full relative z-10 animate-scaleIn border border-gray-700">
        {/* Close Button */}
        <button 
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-300 p-1 rounded-full transition-colors"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        
        {/* Header */}
        <div className="text-center mb-6">
          <h3 className="text-xl sm:text-2xl font-bold text-gray-300 mb-1">Rate Transaction</h3>
          <p className="text-gray-400 text-sm">
            {recipientUsername 
              ? `How was your experience transferring to ${recipientUsername}?`
              : 'How was your experience with this transaction?'
            }
          </p>
        </div>
        
        {success ? (
          /* Success Message */
          <div className="text-center py-6">
            <div className="w-16 h-16 mx-auto mb-4 bg-green-900/30 rounded-full flex items-center justify-center">
              <CheckCircle size={32} className="text-green-400" />
            </div>
            <h4 className="text-lg font-medium text-gray-300 mb-2">Rating Submitted</h4>
            <p className="text-gray-400">Thank you for your feedback!</p>
          </div>
        ) : (
          /* Rating Form */
          <div className="space-y-6">
            {/* Star Rating */}
            <div className="flex flex-col items-center gap-3">
              <label className="text-sm font-medium text-gray-300">Your Rating</label>
              <RatingStars 
                rating={rating} 
                setRating={setRating} 
                size={36}
              />
              {error && error.includes('rating') && (
                <p className="text-red-400 text-sm mt-1">{error}</p>
              )}
            </div>
            
            {/* Comment */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-sm font-medium text-gray-300">Comment (Optional)</label>
                <span className={`text-xs ${getCharCountColor()}`}>
                  {MAX_COMMENT_LENGTH - comment.length} characters left
                </span>
              </div>
              <textarea 
                value={comment}
                onChange={handleCommentChange}
                className={`w-full bg-gray-700 text-gray-300 border rounded-xl p-3 resize-none focus:outline-none focus:ring-2 focus:ring-[#8875FF] ${
                  error && error.includes('characters') ? 'border-red-400' : 'border-gray-600'
                }`}
                rows={4}
                placeholder="Share your thoughts about this transaction..."
              ></textarea>
              {error && error.includes('characters') && (
                <p className="text-red-400 text-sm mt-1">{error}</p>
              )}
            </div>
            
            {/* Error message */}
            {error && !error.includes('rating') && !error.includes('characters') && (
              <div className="p-3 bg-red-900/30 border border-red-800/50 rounded-lg text-sm text-red-400">
                {error}
              </div>
            )}
            
            {/* Submit Button */}
            <button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className={`w-full py-3 bg-gradient-to-r from-[#7865FF] to-[#8875FF] text-white rounded-xl hover:shadow-lg transition-all duration-300 flex items-center justify-center gap-2 ${
                isSubmitting ? 'opacity-70 cursor-wait' : ''
              }`}
            >
              {isSubmitting ? (
                <>
                  <span className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                  <span>Submitting...</span>
                </>
              ) : (
                'Submit Rating'
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

// Interface for rating data
interface RatingData {
  user_id: string;
  total_ratings: number;
  average_rating: number;
  current_user_rating?: {
    stars: number;
    comment?: string;
  };
  ratings: Array<{
    rater_id: string;
    rater_username: string;
    stars: number;
    comment?: string;
    timestamp: string;
  }>;
}

// Interface for badge props
interface UserRatingBadgeProps {
  userId: string;
  size?: "small" | "medium" | "large";
}

// User Rating Badge Component
const UserRatingBadge = ({ userId, size = "small" }: UserRatingBadgeProps) => {
  const [ratingData, setRatingData] = useState<RatingData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    const fetchRating = async () => {
      if (!userId) return;
      
      try {
        setIsLoading(true);
        const response = await fetch(`/api/ratings/user/${userId}`);
        
        if (response.ok) {
          const data = await response.json();
          setRatingData(data);
        } else {
          console.error('Failed to fetch user rating');
        }
      } catch (error) {
        console.error('Error fetching rating:', error);
        setError('Failed to load rating');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchRating();
  }, [userId]);
  
  if (!userId || isLoading) {
    return (
      <div className={clsx(
        "flex items-center gap-1 text-gray-400",
        size === "small" ? "text-xs" : "text-sm"
      )}>
        <Star size={size === "small" ? 12 : 16} />
        <span>-.-</span>
      </div>
    );
  }
  
  if (error || !ratingData) {
    return (
      <div className={clsx(
        "flex items-center gap-1 text-gray-400",
        size === "small" ? "text-xs" : "text-sm"
      )}>
        <Star size={size === "small" ? 12 : 16} />
        <span>N/A</span>
      </div>
    );
  }
  
  const { average_rating, total_ratings } = ratingData;
  
  // No ratings yet
  if (total_ratings === 0) {
    return (
      <div className={clsx(
        "flex items-center gap-1 text-gray-400",
        size === "small" ? "text-xs" : "text-sm"
      )}>
        <Star size={size === "small" ? 12 : 16} />
        <span>Not rated</span>
      </div>
    );
  }
  
  // Rating color based on score
  const getRatingColor = (rating: number): string => {
    if (rating >= 4.5) return "text-green-500";
    if (rating >= 3.5) return "text-blue-500";
    if (rating >= 2.5) return "text-yellow-500";
    return "text-orange-500";
  };
  
  return (
    <div className={clsx(
      "flex items-center gap-1",
      getRatingColor(average_rating),
      size === "small" ? "text-xs" : "text-sm"
    )}>
      <Star size={size === "small" ? 12 : 16} className="fill-current" />
      <span className="font-medium">{average_rating.toFixed(1)}</span>
      <span className="text-gray-500">({total_ratings})</span>
    </div>
  );
};

// Interface for transaction object
interface Transaction {
  id: string;
  status: string;
  amountBeforeFee: string;
  amountBeforeFeePrecise: string;
  networkFee: string;
  amountAfterFee: string;
  totalAmount: string;
  dateTime: string;
  from: string;
  fromPublicAddress: string;
  to: string;
  toPublicAddress: string;
  reason: string;
  recipient?: string;  // Added for rating system
  recipientUsername?: string;  // Added for rating system
}

// Define TransferBlockedScreen component
const TransferBlockedScreen = () => {
  return (
    <div className="max-w-3xl mx-auto bg-gray-800 p-10 rounded-3xl shadow-lg border border-red-800 transition-all duration-500 animate-fadeIn">
      <div className="flex items-center justify-center mb-6">
        <div className="w-20 h-20 bg-red-900 rounded-full flex items-center justify-center">
          <AlertCircle size={40} className="text-red-400" />
        </div>
      </div>
      
      <h2 className="text-2xl font-bold text-center text-gray-300 mb-4">
        Transfers Blocked
      </h2>
      
      <div className="bg-red-900 border border-red-800 rounded-xl p-6 mb-6">
        <p className="text-red-300 text-center">
          Your account has outgoing transfer restrictions.
          All transfers have been temporarily disabled.
        </p>
      </div>
      
      <div className="bg-gray-700 p-6 rounded-xl mb-6">
        <h3 className="font-medium text-gray-300 mb-3">What this means:</h3>
        <ul className="space-y-2 text-gray-400">
          <li className="flex items-start gap-2">
            <span className="mt-1">•</span>
            <span>You cannot send funds to other users</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1">•</span>
            <span>Incoming transfers are not affected</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1">•</span>
            <span>Your current balance and transaction history are still accessible</span>
          </li>
        </ul>
      </div>
      
      <div className="bg-red-900 p-6 rounded-xl mb-6">
        <h3 className="font-medium text-red-300 mb-3">Possible reasons:</h3>
        <ul className="space-y-1 text-gray-300">
          <li className="flex items-start gap-2">
            <span className="mt-1">•</span>
            <span>Suspicious transfer activity detected</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1">•</span>
            <span>Multiple transfer attempts to restricted accounts</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1">•</span>
            <span>Security verification pending</span>
          </li>
        </ul>
      </div>
      
      <div className="text-center">
        <p className="text-gray-400 mb-4">Please contact support to address this issue.</p>
        <button 
          onClick={() => window.location.href = '/support'}
          className="px-6 py-3 bg-gradient-to-r from-[#7865FF] to-[#8875FF] text-white rounded-xl hover:shadow-lg transition-all duration-300"
        >
          Contact Support
        </button>
      </div>
    </div>
  );
};

// Right after TransferBlockedScreen component, add FrozenWalletScreen component
const FrozenWalletScreen = () => {
  return (
    <div className="max-w-3xl mx-auto bg-gray-800 p-10 rounded-3xl shadow-lg border border-blue-800 transition-all duration-500 animate-fadeIn">
      <div className="flex items-center justify-center mb-6">
        <div className="w-20 h-20 bg-blue-900 rounded-full flex items-center justify-center">
          <SnowflakeIcon size={40} className="text-blue-400" />
        </div>
      </div>
      
      <h2 className="text-2xl font-bold text-center text-gray-300 mb-4">
        Wallet Frozen
      </h2>
      
      <div className="bg-blue-900 border border-blue-800 rounded-xl p-6 mb-6">
        <p className="text-blue-300 text-center">
          Your wallet is currently frozen. All transfers are disabled until you unfreeze your wallet.
        </p>
      </div>
      
      <div className="bg-gray-700 p-6 rounded-xl mb-6">
        <h3 className="font-medium text-gray-300 mb-3">What this means:</h3>
        <ul className="space-y-2 text-gray-400">
          <li className="flex items-start gap-2">
            <span className="mt-1">•</span>
            <span>You cannot send funds to other users</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1">•</span>
            <span>You cannot receive transfers from other users</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1">•</span>
            <span>Your current balance and transaction history are not affected</span>
          </li>
        </ul>
      </div>
      
      <div className="bg-blue-900 p-6 rounded-xl mb-6">
        <h3 className="font-medium text-blue-300 mb-3">How to unfreeze your wallet:</h3>
        <p className="text-gray-300">
          You can unfreeze your wallet at any time by going to your Wallet Security settings and toggling off the "Wallet Frozen" option.
        </p>
      </div>
      
      <div className="text-center">
        <button 
          onClick={() => window.location.href = '/wallet/security'}
          className="px-6 py-3 bg-gradient-to-r from-[#7865FF] to-[#8875FF] text-white rounded-xl hover:shadow-lg transition-all duration-300"
        >
          Go to Security Settings
        </button>
      </div>
    </div>
  );
};

const Transfers = () => {
  const [step, setStep] = useState(1);
  const [amount, setAmount] = useState('');
  const [address, setAddress] = useState('');
  const [code2FA, setCode2FA] = useState('');
  const [secretWord, setSecretWord] = useState('');  // New state for secret word
  const [showReceipt, setShowReceipt] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [animateBalance, setAnimateBalance] = useState(false);
  const [userBalance, setUserBalance] = useState('0');
  const [limitInfo, setLimitInfo] = useState({
    has_limit: false,
    limit_amount: null,
    remaining_limit: null,
    today_used: 0,
    last_reset: null
  });
  const [transaction, setTransaction] = useState<Transaction>({
    id: '',
    status: '',
    amountBeforeFee: '',
    amountBeforeFeePrecise: '',
    networkFee: '',
    amountAfterFee: '',
    totalAmount: '',
    dateTime: '',
    from: '',
    fromPublicAddress: '',
    to: '',
    toPublicAddress: '',
    reason: ''
  });
  const [transferError, setTransferError] = useState('');
  const [addressValid, setAddressValid] = useState(false);
  const [validating, setValidating] = useState(false);
  const [taxSettings, setTaxSettings] = useState({
    tax_rate: "0.05",
    tax_enabled: true,
    maintenance_mode: false,
    min_amount: null,
    max_amount: null,
    is_premium: false,
    membership: "Standard",
    premium_enabled: false,
    premium_settings: {
      tax_exempt: false,
      tax_exempt_enabled: false,
      cooldown_reduction: 0,
      cooldown_reduction_enabled: false
    }
  });
  const [isMaintenanceMode, setIsMaintenanceMode] = useState(false);
  const [amountError, setAmountError] = useState<string | null>(null);
  const [addressErrorMessage, setAddressErrorMessage] = useState<string | null>(null);
  const [validationAttempted, setValidationAttempted] = useState(false);
  const [addressAttempts, setAddressAttempts] = useState(0);
  const [isRateLimited, setIsRateLimited] = useState(false);
  const [rateLimitCountdown, setRateLimitCountdown] = useState(0);
  const [is2FARequired, setIs2FARequired] = useState(false);
  const [has2FAEnabled, setHas2FAEnabled] = useState(false);
  const [code2FAError, setCode2FAError] = useState<string | null>(null);
  const [code2FAAttempts, setCode2FAAttempts] = useState(0);
  const [is2FARateLimited, setIs2FARateLimited] = useState(false);
  const [code2FARateLimitCountdown, setCode2FARateLimitCountdown] = useState(0);
  const [isInCooldown, setIsInCooldown] = useState(false);
  const [cooldownSeconds, setCooldownSeconds] = useState(0);
  const [cooldownMinutes, setCooldownMinutes] = useState(0);
  const [transferReason, setTransferReason] = useState('');
  const [reasonError, setReasonError] = useState<string | null>(null);

  // New state variables for rating system
  const [showRatingModal, setShowRatingModal] = useState(false);
  const [ratingSubmitted, setRatingSubmitted] = useState(false);
  const [recipientRating, setRecipientRating] = useState<RatingData | null>(null);
  
  // Account restriction state
  const [transferRestricted, setTransferRestricted] = useState(false);
  const [restrictedAttempts, setRestrictedAttempts] = useState(0);
  const [isRestrictedRateLimited, setIsRestrictedRateLimited] = useState(false);
  const [restrictedRateLimitCountdown, setRestrictedRateLimitCountdown] = useState(0);

  const [isTransferBlocked, setIsTransferBlocked] = useState(false);
  const [isWalletFrozen, setIsWalletFrozen] = useState(false);  // Add state for wallet frozen

  const [transferPassword, setTransferPassword] = useState(''); // كلمة مرور التحويل
  const [transferPasswordError, setTransferPasswordError] = useState<string | null>(null);
  const [transferAuthMethod, setTransferAuthMethod] = useState({
    password: false,
    "2fa": false,
    secret_word: true
  });

  // CSRF token state
  const [csrfToken, setCsrfToken] = useState<string>('');

  // For animating balance on mount
  useEffect(() => {
    setAnimateBalance(true);
  }, []);

  // Fetch CSRF token
  const fetchCsrfToken = async () => {
    try {
      const response = await fetch('/api/csrf-token', {
        method: 'GET',
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.csrf_token) {
          setCsrfToken(data.csrf_token);
          return data.csrf_token;
        }
      }
      
      // If failed, try one more time after a short delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      const retryResponse = await fetch('/api/csrf-token', {
        method: 'GET',
        credentials: 'include'
      });
      
      if (retryResponse.ok) {
        const data = await retryResponse.json();
        if (data.success && data.csrf_token) {
          setCsrfToken(data.csrf_token);
          return data.csrf_token;
        }
      }
      
      return null;
    } catch (error) {
      console.error('Error fetching CSRF token:', error);
      return null;
    }
  };

  // Add fetchBalance function
  const fetchBalance = async () => {
    try {
      const response = await fetch('/api/wallet/balance', {
        headers: {
          'X-CSRF-Token': csrfToken || ''
        },
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setUserBalance(data.balance);
      }
    } catch (error) {
      console.error('Error fetching balance:', error);
    }
  };

  // Add check2FAStatus function
  const check2FAStatus = async () => {
    try {
      const response = await fetch('/api/user/2fa-status', {
        headers: {
          'X-CSRF-Token': csrfToken || ''
        },
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setHas2FAEnabled(data['2fa_enabled']);
      }
    } catch (error) {
      console.error('Error fetching 2FA status:', error);
    }
  };

  // Add checkCooldownStatus function
  const checkCooldownStatus = async () => {
    try {
      const response = await fetch('/api/transfers/cooldown-status', {
        headers: {
          'X-CSRF-Token': csrfToken || ''
        },
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        if (data.in_cooldown) {
          setIsInCooldown(true);
          setCooldownSeconds(data.seconds_remaining);
          // Calculate minutes and seconds for display
          const minutes = Math.floor(data.seconds_remaining / 60);
          const seconds = data.seconds_remaining % 60;
          setCooldownMinutes(minutes);
        } else {
          setIsInCooldown(false);
          setCooldownSeconds(0);
          setCooldownMinutes(0);
        }
      }
    } catch (error) {
      console.error('Error checking cooldown status:', error);
    }
  };

  // Add back the checkWalletFrozenStatus function before the useEffect
  const checkWalletFrozenStatus = async () => {
    try {
      const response = await fetch('/api/wallet/frozen-status', {
        headers: {
          'X-CSRF-Token': csrfToken || ''
        },
        credentials: 'include'
      });
      if (!response.ok) {
        console.error('Failed to fetch wallet frozen status');
        return;
      }
      
      const data = await response.json();
      setIsWalletFrozen(data.is_frozen);
    } catch (error) {
      console.error('Error checking wallet frozen status:', error);
    }
  };

  // Update useEffect to call all required functions
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        // Loading state
        setIsLoading(true);
        
        // Fetch CSRF token first
        await fetchCsrfToken();
        
        // First check maintenance mode before fetching other data
        const taxResponse = await fetch('/api/transfers/tax-settings', {
          headers: {
            'X-CSRF-Token': csrfToken || ''
          },
          credentials: 'include'
        });
        if (taxResponse.ok) {
          const taxData = await taxResponse.json();
          setTaxSettings(taxData);
          setIsMaintenanceMode(taxData.maintenance_mode === true);
          
          if (!taxData.maintenance_mode) {
            // اضافة الـ API الجديد
            await Promise.all([
              fetch('/api/wallet/balance', {
                headers: {
                  'X-CSRF-Token': csrfToken || ''
                },
                credentials: 'include'
              }).then(res => res.json()).then(data => setUserBalance(data.balance)),
              fetch('/api/wallet/limit', {
                headers: {
                  'X-CSRF-Token': csrfToken || ''
                },
                credentials: 'include'
              }).then(res => res.json()).then(data => setLimitInfo(data)),
              fetch('/api/transfers/auth-method', {
                headers: {
                  'X-CSRF-Token': csrfToken || ''
                },
                credentials: 'include'
              }).then(res => {
                if (res.ok) {
                  return res.json();
                } else {
                  // Log error but use default values
                  console.error('Error fetching auth method, using defaults');
                  return { transfer_auth: { password: false, '2fa': false, secret_word: true } };
                }
              }).then(data => {
                console.log('User transfer auth method:', data.transfer_auth);
                // Ensure we have a valid object with all fields
                const authMethod = data.transfer_auth || { password: false, '2fa': false, secret_word: true };
                // Add any missing fields with defaults
                if (typeof authMethod.password === 'undefined') authMethod.password = false;
                if (typeof authMethod['2fa'] === 'undefined') authMethod['2fa'] = false;
                if (typeof authMethod.secret_word === 'undefined') authMethod.secret_word = true;
                
                setTransferAuthMethod(authMethod);
              }),
              check2FAStatus(),
              checkCooldownStatus(),
              checkWalletFrozenStatus()
            ]);
          }
        }
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        // إضافة تأخير قبل إزالة حالة التحميل للتأكد من تحميل جميع البيانات
        setTimeout(() => {
          setIsLoading(false);
        }, 500);
      }
    };

    fetchInitialData();
    
    // Animate balance after loading
    setTimeout(() => {
      setAnimateBalance(true);
    }, 500);
  }, []);

  // Add fetchLimitInfo function
  const fetchLimitInfo = async () => {
    try {
      const response = await fetch('/api/wallet/limit', {
        headers: {
          'X-CSRF-Token': csrfToken || ''
        },
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        console.log('Updated limit info:', data);
        setLimitInfo(data);
      }
    } catch (error) {
      console.error('Error fetching limit info:', error);
    }
  };

  // Add countdown timer effect for rate limiting
  useEffect(() => {
    let timer: NodeJS.Timeout;
    
    if (isRateLimited && rateLimitCountdown > 0) {
      timer = setInterval(() => {
        setRateLimitCountdown(prev => {
          if (prev <= 1) {
            setIsRateLimited(false);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isRateLimited, rateLimitCountdown]);

  // Add effect for 2FA rate limit countdown
  useEffect(() => {
    let timer: NodeJS.Timeout;
    
    if (is2FARateLimited && code2FARateLimitCountdown > 0) {
      timer = setInterval(() => {
        setCode2FARateLimitCountdown(prev => {
          if (prev <= 1) {
            setIs2FARateLimited(false);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [is2FARateLimited, code2FARateLimitCountdown]);

  // Add cooldown timer effect
  useEffect(() => {
    let timer: NodeJS.Timeout;
    
    if (isInCooldown && cooldownSeconds > 0) {
      timer = setInterval(() => {
        setCooldownSeconds(prev => {
          if (prev <= 1) {
            setIsInCooldown(false);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isInCooldown, cooldownSeconds]);
  
  // Add effect to check cooldown status on component mount and after successful transfer
  useEffect(() => {
    const checkCooldownStatus = async () => {
      try {
        const response = await fetch('/api/transfers/cooldown-status', {
          headers: {
            'X-CSRF-Token': csrfToken || ''
          },
          credentials: 'include'
        });
        if (response.ok) {
          const data = await response.json();
          setIsInCooldown(data.in_cooldown);
          setCooldownSeconds(data.seconds_remaining);
          setCooldownMinutes(data.cooldown_minutes);
        }
      } catch (error) {
        console.error('Error checking cooldown status:', error);
      }
    };
    
    checkCooldownStatus();
    
    // Also check cooldown status whenever receipt is shown (after transfer)
    if (showReceipt) {
      checkCooldownStatus();
    }
  }, [showReceipt]);

  // Add effect for restricted account rate limit countdown
  useEffect(() => {
    let timer: NodeJS.Timeout;
    
    if (isRestrictedRateLimited && restrictedRateLimitCountdown > 0) {
      timer = setInterval(() => {
        setRestrictedRateLimitCountdown(prev => {
          if (prev <= 1) {
            setIsRestrictedRateLimited(false);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isRestrictedRateLimited, restrictedRateLimitCountdown]);

  // Handle continue button click with validation
  const handleContinueClick = async () => {
    if (!address.trim() || isRateLimited) return;
    
    setValidating(true);
    setValidationAttempted(true);
    await validateAddress(address);
    setValidating(false);
    
    // Check if address is valid after validation
    if (addressValid) {
      // Reset attempts on success
      setAddressAttempts(0);
      setStep(2);
    } else {
      // Increment failed attempts
      const newAttempts = addressAttempts + 1;
      setAddressAttempts(newAttempts);
      
      // Check if rate limit should be applied
      if (newAttempts >= 5) {
        setIsRateLimited(true);
        setRateLimitCountdown(60); // 60 seconds rate limit
        setAddressAttempts(0); // Reset counter for next time
      }
    }
  };

  // Update validateAddress function to handle recipient_frozen flag
  const validateAddress = async (address: string) => {
    if (!address.trim()) {
      setAddressValid(false);
      setAddressErrorMessage(null);
      return;
    }

    setValidating(true);
    setAddressErrorMessage(null);

    try {
      // Get CSRF token if not available
      let token = csrfToken;
      if (!token) {
        token = await fetchCsrfToken();
      }

      const response = await fetch('/api/transfers/validate-address', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': token || ''
        },
        body: JSON.stringify({ privateAddress: address }),
        credentials: 'include'
      });

      const data = await response.json();

      if (!response.ok) {
        // Handle specific error cases for new transfer frequency protection
        if (data.permanently_banned) {
          setAddressValid(false);
          setAddressErrorMessage("Your account has been permanently banned for excessive transfers. Contact support for assistance.");
          // Redirect to login after 5 seconds
          setTimeout(() => {
            window.location.href = '/login';
          }, 5000);
          return;
        }
        
        if (data.transfer_blocked) {
          setAddressValid(false);
          setAddressErrorMessage("Your transfer privileges have been temporarily blocked due to excessive activity. Please try again later.");
          // Refresh user data to get updated status
          fetchBalance();
          fetchLimitInfo();
          checkCooldownStatus();
          checkWalletFrozenStatus();
          return;
        }
        
        if (data.transfer_blocked) {
          setAddressValid(false);
          setAddressErrorMessage("Your account has outgoing transfer restrictions. You cannot send funds at this time.");
          return;
        }

        if (data.wallet_frozen) {
          setAddressValid(false);
          setAddressErrorMessage("Your wallet is currently frozen. You cannot send or receive transfers while your wallet is frozen.");
          return;
        }

        if (data.rate_limited) {
          setAddressValid(false);
          setAddressErrorMessage(data.error || "Rate limit exceeded. Please try again later.");
          setAddressAttempts(prev => prev + 1);
          
          // Update rate limit state
          if (data.seconds_remaining) {
            setIsRateLimited(true);
            setRateLimitCountdown(data.seconds_remaining);
          }
          return;
        }

        if (data.restricted) {
          setAddressValid(false);
          setAddressErrorMessage(data.error || "Transfer not allowed to this recipient.");
          setRestrictedAttempts(prev => prev + 1);
          
          // Update restricted rate limit state
          if (data.restricted_attempts_remaining !== undefined) {
            if (data.restricted_attempts_remaining <= 0) {
              setIsRestrictedRateLimited(true);
              setRestrictedRateLimitCountdown(120); // 2 minutes
            }
          }
          return;
        }

        // Handle other validation errors
        setAddressValid(false);
        setAddressErrorMessage(data.error || "Invalid address");
        setAddressAttempts(prev => prev + 1);
        
        // Show attempts remaining if available
        if (data.attempts_remaining !== undefined) {
          setAddressErrorMessage(`${data.error || "Invalid address"}. ${data.attempts_remaining} attempts remaining.`);
        }
        
        return;
      }

      // Success case
      setAddressValid(true);
      setAddressErrorMessage(null);
      setAddressAttempts(0); // Reset attempts on success
      setValidationAttempted(true);

    } catch (error) {
      console.error('Error validating address:', error);
      setAddressValid(false);
      setAddressErrorMessage('Network error. Please try again.');
    } finally {
      setValidating(false);
    }
  };

  // Calculate fee based on tax settings
  const calculateFee = (amountValue: string): { fee: number, amountAfterFee: number } => {
    const amountNum = parseFloat(amountValue || '0');
    
    // Premium users pay no fees if tax exemption is enabled
    if (taxSettings.is_premium && 
        taxSettings.premium_enabled && 
        taxSettings.premium_settings.tax_exempt_enabled && 
        taxSettings.premium_settings.tax_exempt) {
      return {
        fee: 0,
        amountAfterFee: amountNum
      };
    }
    
    // Only apply fee if tax is enabled for non-premium users or premium without exemption
    if (taxSettings.tax_enabled) {
      const taxRate = parseFloat(taxSettings.tax_rate);
      const fee = amountNum * taxRate;
      return {
        fee: fee,
        amountAfterFee: amountNum - fee
      };
    } else {
      // No fee if tax is disabled
      return {
        fee: 0,
        amountAfterFee: amountNum
      };
    }
  };

  const handleConfirmTransfer = async () => {
    if (!address || !amount || !transferReason.trim()) {
      setTransferError("Please fill in all required fields");
      return;
    }

    if (isLoading) return;

    setIsLoading(true);
    setTransferError('');
    setCode2FAError(null);
    setTransferPasswordError(null);
    
    // Verify transfer reason is provided
    if (!transferReason.trim()) {
      setReasonError('Please provide a reason for this transfer');
      setIsLoading(false);
      return;
    } else {
      setReasonError(null);
    }
    
    try {
      // Get CSRF token if not available
      let token = csrfToken;
      if (!token) {
        token = await fetchCsrfToken();
      }
      
      // بناء بيانات الطلب بناءً على طريقة المصادقة
      const requestData: any = {
        toAddress: address,
        amount: amount,
        transferReason: transferReason.trim()
      };

      // إضافة طرق المصادقة المناسبة حسب الإعدادات
      if (transferAuthMethod['2fa']) {
        requestData.verificationCode = code2FA;
      } else if (transferAuthMethod.secret_word) {
        requestData.secretWord = secretWord;
      } else if (transferAuthMethod.password) {
        requestData.transferPassword = transferPassword;
      }

      // Make API call to send transfer
      const response = await fetch('/api/transfers/send', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': token || ''
        },
        body: JSON.stringify(requestData),
        credentials: 'include'
      });

      const data = await response.json();

      if (!response.ok) {
        // Handle specific error cases for new transfer frequency protection
        if (data.permanently_banned) {
          setTransferError("Your account has been permanently banned for excessive transfers. Contact support for assistance.");
          // Redirect to login or show banned screen
          setTimeout(() => {
            window.location.href = '/login';
          }, 5000);
          setIsLoading(false);
          return;
        }
        
        if (data.transfer_blocked) {
          setTransferError("Your transfer privileges have been temporarily blocked due to excessive activity. Please try again later.");
          // Refresh user data to get updated status
          fetchBalance();
          fetchLimitInfo();
          checkCooldownStatus();
          checkWalletFrozenStatus();
          setIsLoading(false);
          return;
        }
        
        
        // Check if the error is related to cooldown
        if (data.in_cooldown) {
          setIsInCooldown(true);
          setCooldownSeconds(data.seconds_remaining);
          setTransferError(data.error || 'You must wait before making another transfer');
          setIsLoading(false);
          return;
        }
        
        // Check if the error is wallet frozen related
        if (data.wallet_frozen) {
          setIsWalletFrozen(true);
          setTransferError(data.error || 'Your wallet is frozen. Transfers are disabled.');
          setIsLoading(false);
          return;
        }
        
        // التحقق من نوع الخطأ بناءً على استجابة API
        if (data.requires_2fa) {
          // أخطاء 2FA
          setCode2FAError(data.error || 'Invalid 2FA code');
          setIs2FARequired(true);
          
          // Handle 2FA rate limiting
          const newAttempts = code2FAAttempts + 1;
          setCode2FAAttempts(newAttempts);
          
          // Check if rate limit should be applied
          if (newAttempts >= 5) {
            setIs2FARateLimited(true);
            setCode2FARateLimitCountdown(60); // 60 seconds rate limit
            setCode2FAAttempts(0); // Reset counter for next time
            setCode2FAError(`Too many failed attempts. Please try again in 60 seconds.`);
          } else {
            setCode2FAError(`Invalid 2FA code. You have ${5 - newAttempts} attempts remaining.`);
          }
        } else if (data.requires_secret_word) {
          // أخطاء الكلمة السرية
          setTransferError(data.error || 'Invalid secret word');
        } else if (data.requires_transfer_password) {
          // أخطاء كلمة مرور التحويل
          setTransferPasswordError(data.error || 'Invalid transfer password');
        } else {
          // Handle account restriction errors with more prominence
          const errorMessage = data.error || 'Transfer failed';
          setTransferError(errorMessage);
          
          // Display more prominent error for account restrictions
          if (errorMessage.includes('banned') || 
              errorMessage.includes('wallet is locked') || 
              errorMessage.includes('transfers are currently disabled') || 
              errorMessage.includes('wallet is frozen')) {
            // Set to state to potentially style differently
            setTransferRestricted(true);
            
            // Check if this is a frozen wallet error
            if (errorMessage.includes('wallet is frozen')) {
              setIsWalletFrozen(true);
            }
          }
        }
        setIsLoading(false);
        return;
      }

      // Reset 2FA attempts on success
      setCode2FAAttempts(0);
      
      // Transaction successful
      const txDetails = data.transaction;
      
      // Debug log to see transaction details from backend
      console.log('Transaction details from backend:', txDetails);
      console.log('Premium settings:', taxSettings);
      
      // Update limit info after successful transaction
      fetchLimitInfo();
      
      // Calculate fee based on tax settings
      const amountNum = parseFloat(amount);
      // Make sure we use our frontend premium user check which might be more up-to-date
      const isPremiumExempt = taxSettings.is_premium && 
                            taxSettings.premium_enabled && 
                            taxSettings.premium_settings.tax_exempt_enabled && 
                            taxSettings.premium_settings.tax_exempt;
      
      // Force fee to be 0 for premium exempt users
      let fee = 0;
      let amountAfterFee = amountNum;

      if (!isPremiumExempt && taxSettings.tax_enabled) {
        fee = amountNum * parseFloat(taxSettings.tax_rate);
        amountAfterFee = amountNum - fee;
      }

      const feeStr = fee.toFixed(8);
      const amountAfterFeeStr = amountAfterFee.toFixed(8);
      
      // Create transaction object for receipt
      const newTransaction = {
        id: txDetails.id,
        status: 'COMPLETED',
        amountBeforeFee: txDetails.amount_simple || amount,
        amountBeforeFeePrecise: txDetails.amount,
        networkFee: feeStr,
        amountAfterFee: amountAfterFeeStr,
        totalAmount: amount,
        dateTime: txDetails.timestamp,
        from: txDetails.sender,
        fromPublicAddress: txDetails.sender_public_address || "Unknown",
        to: address,
        toPublicAddress: txDetails.recipient_public_address || "Unknown",
        recipient: txDetails.recipient || "",
        recipientUsername: txDetails.recipient_username || "User",
        reason: transferReason.trim()
      };
      
      // Set transaction data
      setTransaction(newTransaction);
      
      // Update balance after successful transfer
      setUserBalance((prevBalance) => {
        const newBalance = (parseFloat(prevBalance) - amountNum).toFixed(8);
        return newBalance;
      });
      
      // Reset 2FA states
      setIs2FARequired(false);
      setCode2FAError(null);
      
      // Stop loading and show receipt
      setIsLoading(false);
      setShowReceipt(true);
      
      // Add this: Fetch recipient rating after successful transaction
      if (txDetails.recipient) {
        try {
          const ratingResponse = await fetch(`/api/ratings/user/${txDetails.recipient}`, {
            headers: {
              'X-CSRF-Token': token || ''
            },
            credentials: 'include'
          });
          if (ratingResponse.ok) {
            const ratingData = await ratingResponse.json();
            setRecipientRating(ratingData);
          }
        } catch (error) {
          console.error('Error fetching recipient rating:', error);
        }
      }
      
    } catch (error) {
      console.error('Error processing transfer:', error);
      setTransferError('An error occurred. Please try again.');
      setIsLoading(false);
    }
  };

  const handleDownloadPDF = () => {
    try {
      console.log('Starting PDF generation...');
      
      // Create a simple PDF document
      const doc = new jsPDF();
      
      // Add blue header
      doc.setFillColor(44, 99, 235);
      doc.rect(0, 0, 210, 40, "F");
      
      // Add company name in white
      doc.setTextColor(255, 255, 255);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(24);
      doc.text("CRYPTONEL", 105, 20, { align: "center" });
      doc.setFontSize(12);
      doc.text("Transaction Receipt", 105, 30, { align: "center" });
      
      // Add transaction ID
      doc.setTextColor(0, 0, 0);
      doc.setFontSize(12);
      doc.text("Transaction ID: " + transaction.id, 20, 50);
      
      // Add transaction details
      doc.setFont("helvetica", "normal");
      doc.setFontSize(10);
      
      let y = 60;
      const lineHeight = 8;
      
      // Add line function
      const addLine = (label: string, value: string) => {
        doc.text(label, 20, y);
        doc.text(value || "N/A", 100, y);
        y += lineHeight;
      };
      
      // Add transaction details
      addLine("Amount Sent:", transaction.amountBeforeFee + " CRN");
      addLine("Precise Amount:", transaction.amountBeforeFeePrecise + " CRN");
      addLine("Network Fee:", transaction.networkFee + " CRN");
      addLine("Recipient Received:", transaction.amountAfterFee + " CRN");
      
      // Format date
      const date = new Date(transaction.dateTime || new Date());
      const formattedDate = date.toLocaleDateString() + " " + date.toLocaleTimeString();
      
      addLine("Date & Time:", formattedDate);
      addLine("From:", transaction.fromPublicAddress || "Unknown");
      addLine("To:", transaction.toPublicAddress || "Unknown");
      addLine("Reason:", transaction.reason || "Not specified");
      
      // Add verified badge
      y += 10;
      doc.setFillColor(230, 240, 255);
      doc.rect(20, y, 170, 20, "F");
      
      doc.setFont("helvetica", "bold");
      doc.setTextColor(44, 99, 235);
      doc.text("TRANSACTION VERIFIED", 30, y + 10);
      
      // Save the PDF
      doc.save("Cryptonel_Transaction.pdf");
      console.log('PDF generated successfully');
    } catch (error) {
      console.error('Error generating PDF:', error);
      alert('Unable to generate PDF. Please try again.');
    }
  };

  // Reset to start a new transfer
  const handleNewTransfer = () => {
    setShowReceipt(false);
    setStep(1);
    setAmount('');
    setAddress('');
    setCode2FA('');
    setSecretWord('');
    setTransferError('');
    setTransferReason('');
    setRatingSubmitted(false);
    setRecipientRating(null);
    setTransferRestricted(false);
  };

  // Format the remaining limit for display
  const formatRemainingLimit = () => {
    if (!limitInfo.has_limit || limitInfo.remaining_limit === null) {
      return 'Not Set';
    }
    return `${limitInfo.remaining_limit} CRN`;
  };
  
  // Get fee percentage text
  const getFeePercentage = () => {
    // Premium users with tax exemption pay no fees
    if (taxSettings.is_premium && 
        taxSettings.premium_enabled && 
        taxSettings.premium_settings.tax_exempt_enabled && 
        taxSettings.premium_settings.tax_exempt) {
      return '0%';
    }
    
    if (!taxSettings.tax_enabled) {
      return '0%';
    }
    return `${(parseFloat(taxSettings.tax_rate) * 100).toFixed(0)}%`;
  };

  // Get fee rate text
  const getFeeRateText = () => {
    // Premium users with tax exemption pay no fees
    if (taxSettings.is_premium && 
        taxSettings.premium_enabled && 
        taxSettings.premium_settings.tax_exempt_enabled && 
        taxSettings.premium_settings.tax_exempt) {
      return 'Premium Member (No Fee)';
    }
    
    if (!taxSettings.tax_enabled) {
      return 'No Fee';
    }
    return `Network Fee (${getFeePercentage()})`;
  };

  // Format cooldown time for display
  const formatCooldownTime = () => {
    const minutes = Math.floor(cooldownSeconds / 60);
    const seconds = cooldownSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  // Global styles to add
  const additionalStyles = `
    @keyframes spin-reverse {
      from { transform: rotate(0deg); }
      to { transform: rotate(-360deg); }
    }
    .animate-spin-reverse {
      animation: spin-reverse 7s linear infinite;
    }
    
    @keyframes hammer {
      0%, 100% { transform: rotate(0deg); }
      50% { transform: rotate(-30deg); }
    }
    .animate-hammer {
      animation: hammer 1.2s ease-in-out infinite;
      transform-origin: bottom right;
    }

    @keyframes scaleIn {
      from { transform: scale(0.95); opacity: 0; }
      to { transform: scale(1); opacity: 1; }
    }
    .animate-scaleIn {
      animation: scaleIn 0.3s ease-out forwards;
    }
    
    @keyframes pulse-subtle {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.85; }
    }
    .animate-pulse-subtle {
      animation: pulse-subtle 2s ease-in-out infinite;
    }

    /* Mobile optimizations */
    @media (max-width: 640px) {
      .rounded-3xl {
        border-radius: 1rem;
      }
      .p-10 {
        padding: 1.5rem;
      }
      input, button, textarea {
        font-size: 16px; /* Prevents iOS zoom on focus */
      }
    }
  `;

  // If in maintenance mode, show maintenance screen
  if (isMaintenanceMode) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 py-10 px-4">
        <MaintenanceScreen />
        
        {/* Add the new animations to global styles */}
        <style>{`
          ${additionalStyles}
          
          @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
          }
          .animate-fadeIn {
            animation: fadeIn 0.5s ease-out forwards;
          }
          
          @keyframes spin-slow {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
          .animate-spin-slow {
            animation: spin-slow 10s linear infinite;
          }
        `}</style>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="bg-[#262626] min-h-screen flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-gray-700 border-t-[#8875FF] rounded-full animate-spin"></div>
      </div>
    );
  }

  // Fix validateAmount function to check remaining limit properly
  const validateAmount = (inputAmount: string): { valid: boolean; message: string | null } => {
    if (!inputAmount) {
      return { valid: false, message: null };
    }
    
    const amount = parseFloat(inputAmount);
    
    // Check minimum amount if it exists
    if (taxSettings.min_amount !== null && amount < parseFloat(taxSettings.min_amount)) {
      return { 
        valid: false, 
        message: `Amount must be at least ${taxSettings.min_amount} CRN` 
      };
    }
    
    // Check maximum amount if it exists
    if (taxSettings.max_amount !== null && amount > parseFloat(taxSettings.max_amount)) {
      return { 
        valid: false, 
        message: `Amount cannot exceed ${taxSettings.max_amount} CRN` 
      };
    }
    
    // Check if amount exceeds user balance
    if (amount > parseFloat(userBalance)) {
      return {
        valid: false,
        message: `Insufficient balance. Your current balance is ${userBalance} CRN`
      };
    }
    
    // IMPORTANT: Always check daily limit regardless of active status
    if (limitInfo.limit_amount !== null) {
      // Calculate what would be available based on current usage
      const currentUsage = limitInfo.today_used || 0;
      const limitAmount = typeof limitInfo.limit_amount === 'number' ? 
        limitInfo.limit_amount : parseFloat(limitInfo.limit_amount as string);
      const availableLimit = limitAmount - currentUsage;
      
      console.log("Daily limit check:", { 
        limitAmount, 
        currentUsage, 
        availableLimit, 
        attemptAmount: amount 
      });
      
      if (amount > availableLimit) {
        return {
          valid: false,
          message: `Cannot exceed wallet limit (${availableLimit} CRN remaining of ${limitAmount} CRN)`
        };
      }
    }
    
    return { valid: true, message: null };
  };
  
  const handleAmountChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    
    // Rules:
    // 1. Allow empty string
    // 2. Allow a single "0"
    // 3. Allow decimal numbers like "0.x" 
    // 4. Don't allow numbers that start with 0 followed by digits (like "01234")
    // 5. Allow normal numbers that don't start with 0
    // 6. Restrict to 8 decimal places
    
    // Check if the input matches our allowed patterns
    const validInput = 
      newValue === '' || 
      newValue === '0' || 
      /^0\.\d{0,8}$/.test(newValue) || 
      /^[1-9]\d*\.?\d{0,8}$/.test(newValue);
    
    if (validInput) {
      setAmount(newValue);
      
      // Validate the amount against min/max limits
      const validation = validateAmount(newValue);
      setAmountError(validation.message);
    }
  };

  // Fix the 2FA input handler to clear error when user types
  const handle2FAInput = (index: number, value: string) => {
    // Clear error message when user starts typing again
    if (code2FAError) {
      setCode2FAError(null);
    }
    
    if (value.length > 1) {
      // Handle paste of full code
      const digits = value.slice(0, 6).split('');
      const newCode = [...code2FA].slice(0, index);
      digits.forEach((digit, i) => {
        if (index + i < 6) {
          newCode[index + i] = digit;
        }
      });
      setCode2FA(newCode.join('').padEnd(6, ' ').trim());
      
      // Focus last input or next input if there are more digits to input
      const inputs = document.querySelectorAll('input[type="text"][maxlength="1"]');
      const focusIndex = Math.min(index + digits.length, 5);
      (inputs[focusIndex] as HTMLInputElement)?.focus();
    } else {
      // Handle single digit input
      const newCode = code2FA.split('');
      newCode[index] = value;
      setCode2FA(newCode.join(''));
      
      // Auto focus to next input
      if (value && index < 5) {
        const nextInput = document.querySelector(`input[type="text"][maxlength="1"]:nth-of-type(${index + 2})`) as HTMLInputElement;
        if (nextInput) nextInput.focus();
      }

      // On mobile, when deleting and input is empty, focus previous input
      if (value === '' && index > 0) {
        const prevInput = document.querySelector(`input[type="text"][maxlength="1"]:nth-of-type(${index})`) as HTMLInputElement;
        if (prevInput) prevInput.focus();
      }
    }
  };

  // Function to handle backspace in 2FA input for better mobile experience
  const handle2FAKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && index > 0 && (e.target as HTMLInputElement).value === '') {
      // Focus previous input when backspace is pressed on an empty input
      const prevInput = document.querySelector(`input[type="text"][maxlength="1"]:nth-of-type(${index})`) as HTMLInputElement;
      if (prevInput) prevInput.focus();
    }
  };

  // Function to open rating modal after transaction
  const handleOpenRatingModal = () => {
    setShowRatingModal(true);
  };
  
  // Function called after rating is submitted
  const handleRatingSubmitted = () => {
    setRatingSubmitted(true);
    setShowRatingModal(false);
    
    // Fetch updated user rating
    fetchRecipientRating();
  };
  
  // Function to fetch recipient's rating data
  const fetchRecipientRating = async () => {
    if (!transaction.recipient) return;
    
    try {
      // Get CSRF token if not available
      let token = csrfToken;
      if (!token) {
        token = await fetchCsrfToken();
      }
      
      const response = await fetch(`/api/ratings/user/${transaction.recipient}`, {
        headers: {
          'X-CSRF-Token': token || ''
        },
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setRecipientRating(data);
      }
    } catch (error) {
      console.error('Error fetching recipient rating:', error);
    }
  };

  return (
    <div className="bg-[#262626] min-h-screen p-4 sm:p-6 pb-[120px] md:pb-6">
      <div className="max-w-7xl mx-auto">
        {!showReceipt ? (
          <div className="space-y-6">
            {/* Header */}
            <div className="text-center mb-6 sm:mb-8">
              <h1 className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-[#7865FF] to-[#8875FF] text-transparent bg-clip-text mb-2">CRYPTONEL</h1>
              <p className="text-gray-400 text-sm sm:text-base">Secure Transfers • Instant Confirmation • Global Network</p>
            </div>
            
            {/* Cooldown Full Screen Blocker - Show when user is in cooldown */}
            {isInCooldown ? (
              <div className="bg-gray-800 rounded-3xl shadow-lg border border-orange-800 p-6 sm:p-8 text-center animate-fadeIn">
                <div className="w-16 h-16 sm:w-20 sm:h-20 mx-auto mb-4 rounded-full bg-orange-900 flex items-center justify-center">
                  <Clock className="text-orange-400" size={32} />
                </div>
                <h2 className="text-xl sm:text-2xl font-bold text-gray-300 mb-3">Transfer Cooldown Period</h2>
                <div className="text-3xl sm:text-5xl font-bold text-orange-400 my-4 sm:my-6 bg-orange-900/30 py-3 sm:py-4 rounded-xl">
                  {Math.floor(cooldownSeconds / 60)}:{(cooldownSeconds % 60).toString().padStart(2, '0')}
                </div>
                <p className="text-gray-400 mb-6 text-sm sm:text-base">
                  For security reasons, you need to wait before making another transfer.
                  {cooldownMinutes && (
                    <span className="block mt-2 text-xs sm:text-sm">
                      Your account has a cooldown period of 
                      <span className="font-semibold text-gray-300"> {cooldownMinutes} {cooldownMinutes === 1 ? 'minute' : 'minutes'} </span> 
                      between transfers.
                    </span>
                  )}
                </p>
                <div className="w-full bg-gray-700 rounded-full h-2 mb-6 overflow-hidden">
                  <div 
                    className="bg-gradient-to-r from-orange-500 to-red-500 h-full rounded-full transition-all duration-1000 animate-pulse" 
                    style={{ 
                      width: `${Math.max(5, ((cooldownMinutes * 60 - cooldownSeconds) / (cooldownMinutes * 60)) * 100)}%` 
                    }}
                  ></div>
                </div>
              </div>
            ) : (
              <div className="flex flex-col lg:flex-row gap-6 lg:gap-8">
                {/* Left Panel - Balance Info */}
                <div className="w-full lg:w-96 space-y-4 sm:space-y-6">
                  {/* Balance Card */}
                  <div className="bg-gradient-to-br from-gray-800 to-gray-900 p-5 sm:p-8 rounded-3xl shadow-lg border border-gray-700 transition-all duration-500 hover:shadow-xl">
                    <div>
                      <div className="flex items-center gap-2 mb-3 sm:mb-4">
                        <div className="w-3 h-3 bg-green-500 rounded-full relative">
                          <span className="absolute inset-0 w-full h-full bg-green-500 rounded-full animate-ping opacity-75"></span>
                        </div>
                        <span className="text-xs sm:text-sm text-gray-400 font-medium">Live Balance</span>
                      </div>
                      <div className="relative overflow-hidden">
                        <h2 className={`text-3xl sm:text-5xl font-bold transition-all duration-1000 text-gray-200 ${animateBalance ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'}`}>{parseFloat(userBalance).toFixed(2)}</h2>
                        <span className="text-[#8875FF] font-medium text-lg sm:text-xl">CRN</span>
                      </div>
                      <div className="mt-4 sm:mt-6 pt-4 sm:pt-6 border-t border-gray-700">
                        <div className="flex justify-between text-xs sm:text-sm">
                          <span className="text-gray-400 flex items-center gap-1">
                            <Clock size={14} />
                            Daily Limit
                          </span>
                          {limitInfo.limit_amount !== null ? (
                            <span className={`text-gray-300 font-semibold px-2 sm:px-3 py-1 ${limitInfo.has_limit ? 'bg-[#8875FF]/20' : 'bg-gray-700'} rounded-full text-xs`}>
                              {limitInfo.has_limit 
                                ? `${limitInfo.remaining_limit} / ${limitInfo.limit_amount} CRN` 
                                : `${limitInfo.limit_amount} CRN (Not Active)`}
                            </span>
                          ) : (
                            <span className="text-gray-300 font-semibold bg-gray-700 px-2 sm:px-3 py-1 rounded-full text-xs">
                              Not Set
                            </span>
                          )}
                        </div>

                        {/* Display daily spending progress bar */}
                        {limitInfo.limit_amount !== null && (
                          <div className="mt-2 w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                !limitInfo.remaining_limit || limitInfo.remaining_limit === 0
                                  ? 'bg-red-500'
                                  : limitInfo.remaining_limit < limitInfo.limit_amount * 0.2
                                  ? 'bg-orange-500'
                                  : 'bg-green-500'
                              }`}
                              style={{
                                width: `${(
                                  limitInfo.today_used / limitInfo.limit_amount * 100
                                )}%`,
                              }}
                            ></div>
                          </div>
                        )}

                        {/* Add daily limit reset information */}
                        {limitInfo.limit_amount !== null && limitInfo.last_reset && (
                          <div className="mt-2 text-xs text-gray-500">
                            Today's usage: {limitInfo.today_used} CRN
                            <span className="block">Resets after 24 hours</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  {/* Transfer Fee Options */}
                  <div className="bg-gray-800 p-5 sm:p-6 rounded-3xl shadow-lg border border-gray-700 transition-all duration-300 hover:shadow-xl">
                    <h3 className="font-medium mb-4 flex items-center gap-2 text-sm sm:text-base text-gray-300">
                      <Send size={18} className="text-gray-400" />
                      Transfer Fee Options
                    </h3>
                    <div className={`p-4 sm:p-5 border rounded-2xl ${taxSettings.is_premium ? 'bg-[#8875FF]/10 border-[#8875FF]/30' : 'bg-gray-700/50 border-gray-600'} transition-all duration-300 hover:shadow-md`}>
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-medium text-sm sm:text-base text-gray-300">{taxSettings.is_premium ? 'Premium' : 'Standard'}</span>
                        <span className={`text-xs px-2 sm:px-3 py-0.5 sm:py-1 ${taxSettings.is_premium ? 'bg-gradient-to-r from-[#7865FF] to-[#8875FF]' : 'bg-gradient-to-r from-gray-600 to-gray-700'} text-white rounded-full shadow-sm`}>
                          {taxSettings.is_premium ? 'Premium' : 'Default'}
                        </span>
                      </div>
                      <div className="flex justify-between items-end">
                        <span className={`text-xl sm:text-2xl font-bold text-transparent bg-clip-text ${taxSettings.is_premium ? 'bg-gradient-to-r from-[#7865FF] to-[#8875FF]' : 'bg-gradient-to-r from-gray-300 to-gray-400'}`}>
                          {getFeePercentage()}
                        </span>
                        <span className="text-xs sm:text-sm text-gray-500">Transfer Fee</span>
                      </div>
                    </div>
                    
                    {taxSettings.is_premium && taxSettings.premium_enabled && (
                      <div className="mt-4 p-4 bg-[#8875FF]/10 rounded-xl border border-[#8875FF]/20">
                        <h4 className="text-sm font-medium text-[#8875FF] mb-2">Premium Benefits</h4>
                        <ul className="space-y-2">
                          {taxSettings.premium_settings.tax_exempt_enabled && (
                            <li className="flex items-center gap-2 text-xs text-gray-300">
                              <div className="w-4 h-4 rounded-full bg-[#8875FF]/20 flex items-center justify-center">
                                <CheckCircle size={12} className="text-[#8875FF]" />
                              </div>
                              No transfer fees on all transactions
                            </li>
                          )}
                          {taxSettings.premium_settings.cooldown_reduction_enabled && (
                            <li className="flex items-center gap-2 text-xs text-gray-300">
                              <div className="w-4 h-4 rounded-full bg-[#8875FF]/20 flex items-center justify-center">
                                <Clock size={12} className="text-[#8875FF]" />
                              </div>
                              {taxSettings.premium_settings.cooldown_reduction}% reduced cooldown between transfers
                            </li>
                          )}
                        </ul>
                      </div>
                    )}
                    
                    {!taxSettings.is_premium && (
                      <>
                        <button className="w-full mt-4 text-sm text-[#8875FF] flex items-center justify-center gap-2 py-3 rounded-xl border border-[#8875FF]/30 bg-[#8875FF]/10 hover:bg-[#8875FF]/20 transition-all duration-300">
                          Upgrade to Premium
                          <ArrowRight size={16} />
                        </button>
                        <p className="text-xs text-center text-gray-500 mt-2">to get 0% fees</p>
                      </>
                    )}
                  </div>

                  {/* Cooldown Info Box */}
                  {cooldownMinutes > 0 && !(taxSettings.is_premium && 
                        taxSettings.premium_enabled && 
                        taxSettings.premium_settings.cooldown_reduction_enabled && 
                        taxSettings.premium_settings.cooldown_reduction === 0) && (
                    <div className="bg-gray-800 p-6 rounded-3xl shadow-lg border border-gray-700 transition-all duration-300 hover:shadow-xl">
                      <div className="flex items-center gap-3 mb-4">
                        <Clock className="text-gray-400" size={20} />
                        <h3 className="font-medium text-gray-300">Cooldown Information</h3>
                      </div>
                      <p className="text-sm text-gray-400 mb-3">
                        Your account has a cooldown period between transfers.
                      </p>
                      <div className="p-3 rounded-xl bg-orange-900/20 border border-orange-800/30">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm text-gray-400">Current cooldown:</span>
                          <span className="text-sm font-medium text-gray-300">{cooldownMinutes} minutes</span>
                        </div>
                        {taxSettings.is_premium && 
                         taxSettings.premium_enabled && 
                         taxSettings.premium_settings.cooldown_reduction_enabled && 
                         taxSettings.premium_settings.cooldown_reduction > 0 && (
                          <div className="text-xs text-orange-400 mt-1">
                            <span className="bg-orange-900/40 px-2 py-0.5 rounded text-orange-300">Premium Benefit:</span> {taxSettings.premium_settings.cooldown_reduction}% reduced cooldown
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {/* Security Info - MOVED DOWN */}
                  <div className="bg-gray-800 p-6 rounded-3xl shadow-lg border border-gray-700 transition-all duration-300 hover:shadow-xl">
                    <div className="flex items-center gap-3 mb-4">
                      <Shield className="text-gray-400" size={20} />
                      <h3 className="font-medium text-gray-300">Transfer Security</h3>
                    </div>
                    <div className="space-y-4">
                      <div className="flex items-center gap-3 p-3 rounded-xl bg-green-900/20 border border-green-800/30">
                        <div className="w-8 h-8 rounded-full bg-green-900/30 flex items-center justify-center text-green-400">
                          <CheckCircle size={16} />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-300">Verified Instantly</p>
                          <p className="text-xs text-gray-500">Secured on the Cryptonel System</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 p-3 rounded-xl bg-blue-900/20 border border-blue-800/30">
                        <div className="w-8 h-8 rounded-full bg-blue-900/30 flex items-center justify-center text-blue-400">
                          <Shield size={16} />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-300">Advanced Security</p>
                          <p className="text-xs text-gray-500">Military-grade encryption</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Right Panel - Transfer Form */}
                <div className="flex-1 bg-gray-800 rounded-3xl shadow-lg border border-gray-700 p-6 sm:p-8 transition-all duration-300 hover:shadow-xl">
                  {isMaintenanceMode ? (
                    <MaintenanceScreen />
                  ) : isTransferBlocked ? (
                    <TransferBlockedScreen />
                  ) : isWalletFrozen ? (
                    <FrozenWalletScreen />
                  ) : (
                    <>
                      {/* Steps Indicator */}
                      <div className="flex items-center justify-center gap-2 sm:gap-4 mb-6 sm:mb-10">
                        {[
                          { num: 1, label: 'Address' },
                          { num: 2, label: 'Amount' },
                          { num: 3, label: 'Verify' }
                        ].map((s, i) => (
                          <React.Fragment key={s.num}>
                            <div className="flex flex-col items-center gap-1 sm:gap-2">
                              <div className={clsx(
                                'w-10 h-10 sm:w-14 sm:h-14 rounded-full flex items-center justify-center text-base sm:text-lg font-medium transition-all duration-500 shadow-md',
                                step === s.num ? 'bg-gradient-to-r from-[#7865FF] to-[#8875FF] text-white scale-110' : 
                                step > s.num ? 'bg-gradient-to-r from-green-500 to-emerald-500 text-white' : 
                                'bg-gray-700 text-gray-400'
                              )}>
                                {s.num}
                              </div>
                              <span className={clsx(
                                'text-xs sm:text-sm font-medium transition-all duration-300',
                                step === s.num ? 'text-gray-300 scale-105' : 'text-gray-500'
                              )}>{s.label}</span>
                            </div>
                            {i < 2 && (
                              <div className="w-16 sm:w-32 h-[3px] bg-gray-700 rounded-full">
                                <div className={clsx(
                                  'h-full rounded-full transition-all duration-1000 ease-out',
                                  step > i + 1 ? 'bg-gradient-to-r from-green-500 to-emerald-500 w-full' : 'w-0'
                                )} />
                              </div>
                            )}
                          </React.Fragment>
                        ))}
                      </div>

                      {step === 1 && (
                        <div className="animate-fadeIn">
                          <h3 className="text-xl sm:text-2xl font-bold mb-1 sm:mb-2 text-gray-300">Transfer Details</h3>
                          <p className="text-gray-400 text-sm sm:text-base mb-6 sm:mb-8">Enter the receiver's private address to start a transfer</p>
                          
                          <div className="space-y-4 sm:space-y-6 mb-16 sm:mb-0">
                            <div>
                              <label className="block text-sm font-medium text-gray-300 mb-2">
                                Private Address
                              </label>
                              <div className="relative">
                                <input
                                  type="text"
                                  value={address}
                                  onChange={(e) => setAddress(e.target.value)}
                                  className={`w-full px-4 sm:px-5 py-3 sm:py-4 border ${addressValid ? 'border-green-500' : 'border-gray-600'} rounded-2xl focus:ring-2 focus:ring-[#8875FF] focus:border-[#8875FF] shadow-sm transition-all duration-300 hover:shadow-md text-sm sm:text-base bg-gray-700 text-gray-300`}
                                  placeholder="Enter private address for transfer"
                                />
                                {validating && (
                                  <span className="absolute right-4 top-1/2 transform -translate-y-1/2 text-[#8875FF]">
                                    <div className="w-5 h-5 border-2 border-[#8875FF] border-t-transparent rounded-full animate-spin"></div>
                                  </span>
                                )}
                                {validationAttempted && !validating && (
                                  <span className="absolute right-4 top-1/2 transform -translate-y-1/2">
                                    {addressValid ? (
                                      <CheckCircle size={20} className="text-green-500" />
                                    ) : (
                                      <AlertCircle size={20} className="text-red-500" />
                                    )}
                                  </span>
                                )}
                              </div>
                              {validationAttempted && address && !addressValid && !validating && !isRateLimited && (
                                <div>
                                  <p className={clsx(
                                    "mt-2 text-sm",
                                    transferRestricted 
                                      ? "text-red-400 font-semibold" 
                                      : "text-red-400"
                                  )}>
                                    {addressErrorMessage || "Invalid private address. Please enter a valid address."}
                                  </p>
                                  
                                  {transferRestricted ? (
                                    <div className="mt-2 p-4 bg-red-900/40 border border-red-800 rounded-xl text-red-300 text-sm">
                                      <div className="flex items-start gap-2">
                                        <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
                                        <div>
                                          <p className="font-medium">
                                            {addressErrorMessage?.includes("frozen") 
                                              ? "Recipient's Wallet Frozen" 
                                              : "Transfer Not Allowed"}
                                          </p>
                                          <p className="opacity-80 mt-1">
                                            {addressErrorMessage?.includes("banned") 
                                              ? "This recipient's account has been banned. Transfers to this account are not permitted."
                                              : addressErrorMessage?.includes("locked")
                                                ? "This recipient's wallet is currently locked. Transfers to this wallet are not permitted."
                                                : addressErrorMessage?.includes("frozen")
                                                  ? "This recipient has frozen their wallet and cannot receive transfers at this time. They must unfreeze their wallet to receive transfers."
                                                  : "Transfers to this address are restricted. Please contact support if you need assistance."}
                                          </p>
                                          {restrictedAttempts > 0 && (
                                            <p className="mt-2 font-medium text-red-400">
                                              You've made {restrictedAttempts} attempt{restrictedAttempts !== 1 ? 's' : ''} to restricted accounts. 
                                              {restrictedAttempts >= 2 ? ' Further attempts may be rate limited.' : ' After 3 attempts, you will be temporarily rate limited.'}
                                            </p>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  ) : (
                                    <p className="mt-1 text-sm text-yellow-400">
                                      {addressAttempts === 1 
                                        ? "You made 1 wrong attempt. You have 4 attempts remaining."
                                        : `You made ${addressAttempts} wrong attempts. You have ${5 - addressAttempts} attempts remaining.`
                                      }
                                    </p>
                                  )}
                                </div>
                              )}
                              {isRateLimited && (
                                <p className="mt-2 text-sm text-orange-400 font-semibold">
                                  Too many failed attempts. Please try again in {rateLimitCountdown} seconds.
                                </p>
                              )}
                              {isRestrictedRateLimited && (
                                <p className="mt-2 text-sm text-orange-400 font-semibold">
                                  Too many attempts to restricted accounts. Please wait {restrictedRateLimitCountdown} seconds before trying again.
                                </p>
                              )}
                            </div>
                            <div className="flex items-start gap-3 text-[#8875FF] bg-[#8875FF]/10 p-5 rounded-2xl border border-[#8875FF]/30">
                              <Info size={20} className="mt-0.5 flex-shrink-0" />
                              <p className="text-sm">
                                Double-check the private address before proceeding
                              </p>
                            </div>
                            <div className="pb-6 md:pb-0">
                              <button
                                onClick={handleContinueClick}
                                disabled={!address || validating || isRateLimited || isRestrictedRateLimited || isTransferBlocked || isWalletFrozen}
                                className="w-full px-6 py-4 bg-gradient-to-r from-[#7865FF] to-[#8875FF] text-white rounded-2xl hover:shadow-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-medium text-sm sm:text-base"
                              >
                                {validating ? (
                                  <>
                                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                                    Validating Address...
                                  </>
                                ) : isRateLimited ? (
                                  <>
                                    Try again in {rateLimitCountdown} seconds
                                  </>
                                ) : isRestrictedRateLimited ? (
                                  <>
                                    Too many restricted attempts. Try again in {restrictedRateLimitCountdown} seconds
                                  </>
                                ) : isTransferBlocked ? (
                                  <>
                                    Transfers Blocked
                                  </>
                                ) : isWalletFrozen ? (
                                  <>
                                    Wallet Frozen
                                  </>
                                ) : (
                                  <>
                                    Validate and Continue
                                    <ArrowRightCircle size={18} />
                                  </>
                                )}
                              </button>
                            </div>
                          </div>
                        </div>
                      )}

                      {step === 2 && (
                        <div className="animate-fadeIn">
                          <h3 className="text-xl sm:text-2xl font-bold mb-1 sm:mb-2 text-gray-300">Transfer Amount</h3>
                          <p className="text-gray-400 text-sm sm:text-base mb-6 sm:mb-8">Specify how much CRN you want to transfer</p>
                          
                          <div className="space-y-4 sm:space-y-6">
                            <div>
                              <label className="block text-sm font-medium text-gray-300 mb-2">
                                Amount (CRN)
                              </label>
                              <div className="relative">
                                <input
                                  type="text"
                                  value={amount}
                                  onChange={handleAmountChange}
                                  className="w-full px-4 sm:px-5 py-3 sm:py-4 border border-gray-600 rounded-2xl focus:ring-2 focus:ring-[#8875FF] focus:border-[#8875FF] shadow-sm text-base sm:text-lg font-bold transition-all hover:shadow-md bg-gray-700 text-gray-200"
                                  placeholder="0.00000000"
                                  inputMode="decimal"
                                />
                              </div>
                              {amountError && (
                                <p className="mt-2 text-sm text-red-400">
                                  {amountError}
                                </p>
                              )}
                            </div>
                            <div className="text-xs sm:text-sm text-gray-400 flex items-center gap-1.5">
                              <Info size={16} className="text-gray-500" />
                              Available: {parseFloat(userBalance).toFixed(8)} CRN
                            </div>

                            {/* Summary Card */}
                            <div className="p-5 sm:p-6 bg-gray-800 rounded-2xl border border-gray-700 mt-6">
                              <div className="text-sm sm:text-base space-y-3 sm:space-y-4">
                                <div className="flex justify-between items-center">
                                  <span className="text-gray-400">Total Amount (You Send)</span>
                                  <span className="text-lg sm:text-xl font-bold text-white">{amount || "0.00000000"} CRN</span>
                                </div>
                                
                                <div className="flex justify-between items-center">
                                  <span className="text-gray-400">{getFeeRateText()}</span>
                                  <span className="text-gray-200">{
                                    taxSettings.is_premium && 
                                    taxSettings.premium_settings.tax_exempt_enabled && 
                                    taxSettings.premium_settings.tax_exempt
                                      ? "0.00000000 CRN"
                                      : taxSettings.tax_enabled 
                                        ? (parseFloat(amount || "0") * parseFloat(taxSettings.tax_rate)).toFixed(8) + " CRN"
                                        : "0.00000000 CRN"
                                  }</span>
                                </div>

                                <div className="pt-2 border-t border-gray-700">
                                  <div className="flex justify-between items-center">
                                    <span className="text-gray-300">Recipient Gets</span>
                                    <span className="text-lg sm:text-xl font-bold text-[#8875FF]">
                                      {taxSettings.is_premium && 
                                       taxSettings.premium_enabled && 
                                       taxSettings.premium_settings.tax_exempt_enabled && 
                                       taxSettings.premium_settings.tax_exempt 
                                         ? parseFloat(amount || "0").toFixed(8)
                                         : taxSettings.tax_enabled 
                                           ? (parseFloat(amount || "0") * (1 - parseFloat(taxSettings.tax_rate))).toFixed(8)
                                           : parseFloat(amount || "0").toFixed(8)} CRN
                                    </span>
                                  </div>
                                </div>
                              </div>
                            </div>

                            <div className="flex gap-3 sm:gap-4 mt-6">
                              <button
                                onClick={() => setStep(1)}
                                className="w-full px-4 sm:px-6 py-3 sm:py-4 border border-gray-600 bg-gray-800 text-gray-300 rounded-2xl hover:bg-gray-700 transition-all duration-300 font-medium text-sm sm:text-base"
                              >
                                Back
                              </button>
                              <button
                                onClick={() => setStep(3)}
                                disabled={!amount || parseFloat(amount) <= 0 || amountError !== null}
                                className="w-full px-4 sm:px-6 py-3 sm:py-4 bg-gradient-to-r from-[#7865FF] to-[#8875FF] text-white rounded-2xl hover:shadow-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed text-sm sm:text-base"
                              >
                                Continue
                              </button>
                            </div>
                          </div>
                        </div>
                      )}
                      {step === 3 && (
                        <div className="animate-fadeIn">
                          <h3 className="text-xl sm:text-2xl font-bold mb-1 sm:mb-2 text-gray-300">Verify Transfer</h3>
                          <p className="text-gray-400 text-sm sm:text-base mb-6 sm:mb-8">Please review the transaction details before confirming</p>
                          
                          <div className="space-y-6">
                            {/* Transaction Summary */}
                            <div className="p-4 sm:p-5 bg-gray-700 rounded-2xl border border-gray-600 text-sm">
                              <h4 className="text-xs sm:text-sm text-gray-400 mb-3">Transaction Summary</h4>
                              <div className="space-y-3">
                                <div className="flex justify-between">
                                  <span className="text-gray-400">To</span>
                                  <span className="font-medium truncate max-w-[150px] sm:max-w-[250px] text-gray-200" dir="rtl">{address}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-400">Amount (You Send)</span>
                                  <div className="text-right">
                                    <span className="font-medium text-gray-200">{amount} CRN</span>
                                    <span className="block text-xs sm:text-sm text-gray-400">{parseFloat(amount).toFixed(8)} CRN</span>
                                  </div>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-400">{getFeeRateText()} (Deducted)</span>
                                  <span className="font-medium text-gray-200">{transaction.networkFee} CRN</span>
                                </div>
                                <div className="flex justify-between pt-2 border-t border-gray-600">
                                  <span className="font-medium text-gray-300">Recipient Gets</span>
                                  <span className="text-base sm:text-lg font-bold text-[#8875FF]">
                                    {taxSettings.is_premium && 
                                     taxSettings.premium_enabled && 
                                     taxSettings.premium_settings.tax_exempt_enabled && 
                                     taxSettings.premium_settings.tax_exempt 
                                       ? parseFloat(amount).toFixed(8)
                                       : taxSettings.tax_enabled 
                                         ? (parseFloat(amount) * (1 - parseFloat(taxSettings.tax_rate))).toFixed(8) 
                                         : parseFloat(amount).toFixed(8)} CRN
                                  </span>
                                </div>
                              </div>
                            </div>
                            
                            <div>
                              <label className="block text-sm font-medium text-gray-300 mb-2">
                                Reason for Transfer <span className="text-xs text-red-400 ml-1">(Required)</span>
                              </label>
                              <div className="relative">
                                <input
                                  type="text"
                                  value={transferReason}
                                  onChange={(e) => setTransferReason(e.target.value)}
                                  className={`w-full px-4 sm:px-5 py-3 sm:py-4 border ${reasonError ? 'border-red-500' : 'border-gray-600'} rounded-2xl focus:ring-2 focus:ring-[#8875FF] focus:border-[#8875FF] shadow-sm transition-all duration-300 hover:shadow-md text-sm sm:text-base bg-gray-700 text-gray-200`}
                                  placeholder="e.g., Payment for services, Gift, etc."
                                />
                              </div>
                              {reasonError && (
                                <p className="mt-2 text-xs sm:text-sm text-red-400">
                                  {reasonError}
                                </p>
                              )}
                            </div>

                            {/* Authentication methods - shown based on user settings */}
                            {transferAuthMethod['2fa'] && (
                              <div>
                                <label className="block text-sm font-medium text-gray-300 mb-3 sm:mb-4">
                                  2FA Authentication <span className="text-xs text-red-400 ml-1">(Required)</span>
                                </label>
                                {is2FARateLimited ? (
                                  <div className="p-3 sm:p-4 bg-gray-700 border border-orange-600 rounded-xl mb-4 text-center">
                                    <p className="text-orange-400 font-medium text-xs sm:text-sm">
                                      Too many failed attempts. Please try again in {code2FARateLimitCountdown} seconds.
                                    </p>
                                  </div>
                                ) : (
                                  <div className="flex gap-2 sm:gap-3 justify-center">
                                    {Array.from({ length: 6 }).map((_, i) => (
                                      <input
                                        key={i}
                                        type="text"
                                        inputMode="numeric"
                                        pattern="[0-9]*"
                                        maxLength={1}
                                        className={`w-10 h-10 sm:w-14 sm:h-14 text-center border ${code2FAError ? 'border-red-500' : 'border-gray-600'} rounded-xl focus:ring-2 focus:ring-[#8875FF] focus:border-[#8875FF] text-base sm:text-xl font-bold shadow-sm transition-all duration-300 hover:shadow-md bg-gray-700 text-gray-200`}
                                        value={code2FA[i] || ''}
                                        onChange={(e) => handle2FAInput(i, e.target.value)}
                                        onKeyDown={(e) => handle2FAKeyDown(i, e)}
                                        onPaste={(e) => {
                                          e.preventDefault();
                                          const pastedData = e.clipboardData.getData('text');
                                          handle2FAInput(i, pastedData);
                                        }}
                                        disabled={is2FARateLimited}
                                      />
                                    ))}
                                  </div>
                                )}
                                {code2FAError && !is2FARateLimited && (
                                  <p className="mt-2 text-xs sm:text-sm text-red-400 text-center">
                                    {code2FAError}
                                  </p>
                                )}
                              </div>
                            )}
                            
                            {/* Secret word authentication */}
                            {transferAuthMethod.secret_word && (
                              <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2 sm:mb-4">
                                  Secret Word <span className="text-xs text-red-400 ml-1">(Required)</span>
                                </label>
                                <div className="relative">
                                  <input
                                    type="password"
                                    value={secretWord}
                                    onChange={(e) => setSecretWord(e.target.value)}
                                    className={`w-full px-4 sm:px-5 py-3 sm:py-4 border ${transferError && transferError.includes('secret word') ? 'border-red-500' : 'border-gray-600'} rounded-2xl focus:ring-2 focus:ring-[#8875FF] focus:border-[#8875FF] shadow-sm transition-all duration-300 hover:shadow-md text-base sm:text-lg bg-gray-700 text-gray-200`}
                                    placeholder="Enter your secret word"
                                  />
                                </div>
                              </div>
                            )}
                            
                            {/* Transfer password authentication */}
                            {transferAuthMethod.password && (
                              <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2 sm:mb-4">
                                  Transfer Password <span className="text-xs text-red-400 ml-1">(Required)</span>
                                </label>
                                <div className="relative">
                                  <input
                                    type="password"
                                    value={transferPassword}
                                    onChange={(e) => setTransferPassword(e.target.value)}
                                    className={`w-full px-4 sm:px-5 py-3 sm:py-4 border ${transferPasswordError ? 'border-red-500' : 'border-gray-600'} rounded-2xl focus:ring-2 focus:ring-[#8875FF] focus:border-[#8875FF] shadow-sm transition-all duration-300 hover:shadow-md text-base sm:text-lg bg-gray-700 text-gray-200`}
                                    placeholder="Enter your transfer password"
                                  />
                                </div>
                                {transferPasswordError && (
                                  <p className="mt-2 text-xs sm:text-sm text-red-400">
                                    {transferPasswordError}
                                  </p>
                                )}
                              </div>
                            )}

                            <div className="flex items-start gap-3 text-yellow-400 bg-yellow-900/30 p-4 sm:p-5 rounded-2xl border border-yellow-800/50 text-xs sm:text-sm">
                              <AlertCircle size={18} className="mt-0.5 flex-shrink-0" />
                              <p>
                                This action cannot be undone. Please make sure the recipient address is correct before confirming.
                              </p>
                            </div>

                            {transferError && (
                              <div className={clsx(
                                "flex items-start gap-3 p-4 sm:p-5 rounded-2xl border text-xs sm:text-sm",
                                transferRestricted 
                                  ? "bg-orange-900/30 text-orange-400 border-orange-800/50" 
                                  : "bg-red-900/30 text-red-400 border-red-800/50"
                              )}>
                                <AlertCircle size={18} className="mt-0.5 flex-shrink-0" />
                                <div>
                                  <p className="font-medium">{transferError}</p>
                                  {transferRestricted && (
                                    <p className="text-xs mt-1 opacity-80">
                                      This restriction affects your ability to make transfers. 
                                      Please contact support for assistance.
                                    </p>
                                  )}
                                </div>
                              </div>
                            )}

                            <div className="flex gap-3 sm:gap-4 mb-16 sm:mb-0">
                              <button
                                onClick={() => setStep(2)}
                                className="w-full px-4 sm:px-6 py-3 sm:py-4 border border-gray-600 bg-gray-800 rounded-2xl hover:bg-gray-700 transition-all duration-300 font-medium text-sm sm:text-base text-gray-300"
                              >
                                Back
                              </button>
                              <button
                                onClick={handleConfirmTransfer}
                                disabled={
                                  (transferAuthMethod['2fa'] && code2FA.length !== 6) || 
                                  (transferAuthMethod.secret_word && !secretWord.trim()) ||
                                  (transferAuthMethod.password && !transferPassword.trim()) ||
                                  isLoading || 
                                  is2FARateLimited || 
                                  !transferReason.trim() ||
                                  (transferAuthMethod['2fa'] && code2FAError !== null)
                                }
                                className="w-full px-4 sm:px-6 py-3 sm:py-4 bg-gradient-to-r from-[#7865FF] to-[#8875FF] text-white rounded-2xl hover:shadow-lg transition-all duration-300 disabled:opacity-50 font-medium flex items-center justify-center gap-2 text-sm sm:text-base"
                              >
                                {isLoading ? (
                                  <>
                                    <span className="w-5 h-5 rounded-full border-2 border-white border-t-transparent animate-spin"></span>
                                    <span className="ml-1">Processing...</span>
                                  </>
                                ) : is2FARateLimited ? (
                                  <>Try again in {code2FARateLimitCountdown}s</>
                                ) : (
                                  <>Confirm Transfer</>
                                )}
                              </button>
                            </div>
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            )}
          </div>
        ) : (
          // Transaction Receipt View with Rating with dark theme
          <div className="max-w-3xl mx-auto bg-gray-800 p-6 sm:p-10 rounded-3xl shadow-lg border border-gray-700 transition-all duration-500 hover:shadow-xl animate-fadeIn">
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center mb-6 gap-4">
              <div>
                <h2 className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-[#7865FF] to-[#8875FF] text-transparent bg-clip-text">Transaction Receipt</h2>
                <p className="text-gray-400 text-sm sm:text-base">Keep this information for your records</p>
              </div>
              <button 
                onClick={handleDownloadPDF}
                className="flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-[#7865FF] to-[#8875FF] text-white rounded-xl hover:shadow-lg transition-all duration-300"
              >
                <Download size={18} />
                <span>Download PDF</span>
              </button>
            </div>
            
            <div className="bg-gray-700 rounded-2xl overflow-hidden shadow-lg border border-gray-600 mb-6">
              <div className="p-5 flex justify-between items-center border-b border-gray-600">
                <h3 className="font-bold text-gray-200">Transaction Summary</h3>
                <span className="text-green-400 bg-green-900/40 px-3 py-1 rounded-full text-sm font-medium border border-green-800/50">{transaction.status}</span>
              </div>
              
              <div className="divide-y divide-gray-600">
                <div className="flex justify-between p-5 bg-gray-700 hover:bg-gray-600 transition-all">
                  <span className="text-gray-400">Transaction ID</span>
                  <span className="font-medium text-[#8875FF]">{transaction.id}</span>
                </div>
                
                <div className="flex justify-between p-5 bg-gray-700 hover:bg-gray-600 transition-all">
                  <span className="text-gray-400">Amount You Sent</span>
                  <div className="text-right">
                    <span className="font-medium text-gray-200">{transaction.amountBeforeFee} CRN</span>
                    <span className="block text-sm text-gray-400">{transaction.amountBeforeFeePrecise} CRN</span>
                  </div>
                </div>
                
                <div className="flex justify-between p-5 bg-gray-700 hover:bg-gray-600 transition-all">
                  <span className="text-gray-400">{getFeeRateText()} (Deducted)</span>
                  <span className="font-medium text-gray-200">{transaction.networkFee} CRN</span>
                </div>
                
                <div className="flex justify-between p-5 bg-gray-700 hover:bg-gray-600 transition-all">
                  <span className="font-medium text-gray-300">Recipient Received</span>
                  <span className="text-lg font-bold text-[#8875FF]">
                    {transaction.amountAfterFee} CRN
                  </span>
                </div>
                
                <div className="flex justify-between p-5 bg-gray-700 hover:bg-gray-600 transition-all">
                  <span className="text-gray-400">Date & Time</span>
                  <span className="font-medium text-gray-200">
                    {new Date(transaction.dateTime).toLocaleString('en-GB', {
                      day: '2-digit',
                      month: '2-digit',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit'
                    })}
                  </span>
                </div>
                
                <div className="flex justify-between p-5 bg-gray-700 hover:bg-gray-600 transition-all">
                  <span className="text-gray-400">From (Public Address):</span>
                  <span className="font-medium text-gray-200 text-right max-w-[300px] break-all">{transaction.fromPublicAddress}</span>
                </div>
                
                <div className="flex justify-between p-5 bg-gray-700 hover:bg-gray-600 transition-all">
                  <span className="text-gray-400">To (Public Address):</span>
                  <div className="flex flex-col items-end">
                    <span className="font-medium text-gray-200 text-right max-w-[300px] break-all">{transaction.toPublicAddress}</span>
                  </div>
                </div>
                
                <div className="flex justify-between p-5 bg-gray-700 hover:bg-gray-600 transition-all">
                  <span className="text-gray-400">Reason</span>
                  <span className="font-medium text-gray-200">{transaction.reason}</span>
                </div>
              </div>
            </div>
            
            {/* Rating Card - Show if not yet rated */}
            {!ratingSubmitted && (
              <div className="bg-gradient-to-r from-[#8875FF]/20 to-[#7865FF]/20 p-6 rounded-2xl border border-[#8875FF]/30 mb-8 animate-fadeIn">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 bg-gradient-to-r from-[#7865FF] to-[#8875FF] rounded-full flex items-center justify-center text-white">
                    <Star size={24} />
                  </div>
                  <div>
                    <h3 className="font-bold text-gray-200">Rate Your Experience</h3>
                    <p className="text-sm text-gray-400">Let others know about your transaction experience</p>
                  </div>
                </div>
                
                <button
                  onClick={handleOpenRatingModal}
                  className="w-full py-3 bg-gradient-to-r from-[#7865FF] to-[#8875FF] text-white rounded-xl hover:shadow-lg transition-all duration-300 flex items-center justify-center gap-2"
                >
                  <Star size={18} />
                  Rate This Transaction
                </button>
              </div>
            )}
            
            {/* Rating Submitted Confirmation */}
            {ratingSubmitted && recipientRating && (
              <div className="bg-gradient-to-r from-green-900/20 to-emerald-900/20 p-6 rounded-2xl border border-green-700/30 mb-8 animate-fadeIn">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-gradient-to-r from-green-700 to-emerald-700 rounded-full flex items-center justify-center text-white">
                    <CheckCircle size={24} />
                  </div>
                  <div>
                    <h3 className="font-bold text-gray-200">Rating Submitted</h3>
                    <p className="text-sm text-gray-400">Thank you for rating your transaction experience</p>
                  </div>
                </div>
                
                <div className="mt-4 p-4 bg-gray-800/50 rounded-xl">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-300">Your Rating:</span>
                    <div className="flex items-center">
                      <RatingStars 
                        rating={recipientRating.current_user_rating?.stars || 0} 
                        setRating={() => {}} 
                        size={20} 
                        disabled={true}
                        animate={false}
                      />
                    </div>
                  </div>
                  {recipientRating.current_user_rating?.comment && (
                    <div className="mt-2 text-sm text-gray-400 italic">
                      "{recipientRating.current_user_rating.comment}"
                    </div>
                  )}
                </div>
              </div>
            )}
            
            <div className="bg-gradient-to-r from-blue-900/20 to-indigo-900/20 p-5 rounded-2xl flex items-start gap-3 border border-blue-700/30">
              <CheckCircle className="text-blue-400 mt-0.5 flex-shrink-0" size={20} />
              <div className="text-sm text-blue-300">
                <p className="font-medium">This transaction has been recorded on the Cryptonel System.</p>
                <p className="mt-1 text-blue-400/80">Transaction timestamp: {new Date(transaction.dateTime).toISOString()}</p>
              </div>
            </div>
            
            {/* Show cooldown info in receipt if applicable */}
            {isInCooldown && !(taxSettings.is_premium && 
                 taxSettings.premium_enabled && 
                 taxSettings.premium_settings.cooldown_reduction_enabled && 
                 taxSettings.premium_settings.cooldown_reduction === 0) && (
              <div className="mt-6 bg-orange-900/20 p-5 rounded-2xl flex items-start gap-3 border border-orange-700/30">
                <Clock className="text-orange-400 mt-0.5 flex-shrink-0" size={20} />
                <div className="text-sm text-orange-300">
                  <p className="font-medium">Transfer Cooldown Period</p>
                  <p className="mt-1">You can make another transfer in {formatCooldownTime()}</p>
                </div>
              </div>
            )}
            
            <div className="mt-10 text-center">
              <button
                onClick={handleNewTransfer}
                className="px-8 py-4 bg-gradient-to-r from-[#7865FF] to-[#8875FF] text-white rounded-2xl hover:shadow-lg transition-all duration-300 font-medium"
              >
                New Transfer
              </button>
            </div>
          </div>
        )}
      </div>
      
      {/* Fixed mobile action bar - Only show for step 1 on mobile */}
      {!showReceipt && !isInCooldown && step === 1 && (
        <div className="fixed bottom-0 left-0 right-0 p-4 bg-gray-900 border-t border-gray-700 z-40 md:hidden">
          <button
            onClick={handleContinueClick}
            disabled={!address || validating || isRateLimited || isRestrictedRateLimited || isTransferBlocked || isWalletFrozen}
            className="w-full px-6 py-3 bg-gradient-to-r from-[#7865FF] to-[#8875FF] text-white rounded-xl hover:shadow-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-medium text-sm"
          >
            {validating ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                Validating Address...
              </>
            ) : isRateLimited ? (
              <>
                Try again in {rateLimitCountdown} seconds
              </>
            ) : isRestrictedRateLimited ? (
              <>
                Too many restricted attempts. Try again in {restrictedRateLimitCountdown} seconds
              </>
            ) : isTransferBlocked ? (
              <>
                Transfers Blocked
              </>
            ) : isWalletFrozen ? (
              <>
                Wallet Frozen
              </>
            ) : (
              <>
                Validate and Continue
                <ArrowRightCircle size={18} />
              </>
            )}
          </button>
        </div>
      )}
      
      {/* Keep the existing fixed mobile action bar for step 3 */}
      {!showReceipt && !isInCooldown && step === 3 && (
        <div className="fixed bottom-0 left-0 right-0 p-4 bg-gray-900 border-t border-gray-700 z-40 flex gap-3 md:hidden">
          <button
            onClick={() => setStep(2)}
            className="w-full px-4 py-3 border border-gray-600 bg-gray-800 rounded-xl hover:bg-gray-700 transition-all duration-300 font-medium text-sm text-gray-300"
          >
            Back
          </button>
          <button
            onClick={handleConfirmTransfer}
            disabled={
              (transferAuthMethod['2fa'] && code2FA.length !== 6) || 
              (transferAuthMethod.secret_word && !secretWord.trim()) ||
              (transferAuthMethod.password && !transferPassword.trim()) ||
              isLoading || 
              is2FARateLimited || 
              !transferReason.trim() ||
              (transferAuthMethod['2fa'] && code2FAError !== null)
            }
            className="w-full px-4 py-3 bg-gradient-to-r from-[#7865FF] to-[#8875FF] text-white rounded-xl hover:shadow-lg transition-all duration-300 disabled:opacity-50 font-medium flex items-center justify-center gap-2 text-sm"
          >
            {isLoading ? (
              <>
                <span className="w-5 h-5 rounded-full border-2 border-white border-t-transparent animate-spin"></span>
                <span className="ml-1">Processing...</span>
              </>
            ) : is2FARateLimited ? (
              <>Try again in {code2FARateLimitCountdown}s</>
            ) : (
              <>Confirm Transfer</>
            )}
          </button>
        </div>
      )}
      
      {/* Rating Modal */}
      <RatingModal 
        isOpen={showRatingModal} 
        onClose={() => setShowRatingModal(false)} 
        recipientId={transaction.recipient || ''}
        recipientUsername={transaction.recipientUsername || ''}
        onRatingSubmitted={handleRatingSubmitted}
        csrfToken={csrfToken}
        fetchCsrfToken={fetchCsrfToken}
      />
      
      {/* Global Styles */}
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fadeIn {
          animation: fadeIn 0.5s ease-out forwards;
        }
        
        @keyframes scaleIn {
          from { opacity: 0; transform: scale(0.95); }
          to { opacity: 1; transform: scale(1); }
        }
        .animate-scaleIn {
          animation: scaleIn 0.3s ease-out forwards;
        }
        
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .animate-spin-slow {
          animation: spin-slow 10s linear infinite;
        }
        
        /* Glowing effect for purple items */
        .shadow-purple-glow {
          box-shadow: 0 0 15px rgba(136, 117, 255, 0.6);
        }
        
        /* Mobile optimizations */
        @media (max-width: 640px) {
          body {
            padding-bottom: env(safe-area-inset-bottom);
          }
          
          input, select, textarea {
            font-size: 16px !important; /* Prevents iOS zoom on input focus */
          }
          
          .fixed-bottom-padding {
            padding-bottom: 100px;
          }
        }
      `}</style>
    </div>
  );
};

export default Transfers;


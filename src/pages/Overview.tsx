import {
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  Copy,
  CreditCard,
  Key,
  Shield,
  CheckCircle,
  Crown,
  TrendingUp,
  TrendingDown,
  Activity,
  Eye,
  Lock,
  Star,
  ArrowRightLeft,
  LineChart as LineChartIcon,
  Calendar,
  Quote,
  Users,
  Trophy,
  ArrowDown,
  ArrowUp,
  MoreVertical,
  Wallet,
  CheckCircle2,
  ActivitySquare,
  Check,
  Info,
  EyeOff,
  Download,
  HelpCircle,
  LogIn,
  Diamond,
} from "lucide-react";
import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
} from "recharts";

// Import framer-motion for animations
import { motion, AnimatePresence } from "framer-motion";
import { Toaster, toast as hotToast } from "react-hot-toast";
import "../styles/cards.css"; // Import new CSS file

// Add memo imports at the top of the file
import React, { memo } from 'react';

// Add mobile optimization component
const MobileOptimization = memo(() => {
  useEffect(() => {
    // Add viewport meta tag
    let meta = document.querySelector(
      'meta[name="viewport"]'
    ) as HTMLMetaElement;
    if (!meta) {
      meta = document.createElement("meta");
      meta.setAttribute("name", "viewport");
      document.head.appendChild(meta);
    }
    meta.setAttribute(
      "content",
      "width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"
    );

    // Add mobile-specific CSS class to body
    document.body.classList.add("mobile-optimized");

    return () => {
      document.body.classList.remove("mobile-optimized");
    };
  }, []);

  return null;
});

interface Transaction {
  type: string;
  amount: number;
  address: string;
  date: string;
  tx_id: string; // Add tx_id field
  recipientId?: string; // Optional recipient ID
  counterparty_id?: string; // Counterparty ID
  counterparty_username?: string; // Counterparty username
}

interface WalletAddress {
  public: string;
  private: string;
}

interface SecurityInfo {
  twoFA: boolean;
  recoveryEmail: string;
  recoveryVerified: boolean;
  lastLogin: string;
  walletFrozen: boolean;
  dailyTransferLimit: number;
  dailyLimitUsed: number;
  transferAuth: {
    password: boolean;
    "2fa": boolean;
    secret_word: boolean;
  };
  loginAuth: {
    none: boolean;
    "2fa": boolean;
    secret_word: boolean;
  };
}

interface TransactionStats {
  highest: {
    amount: number;
    change: string;
  };
  lowest: {
    amount: number;
    change: string;
  };
  total: {
    count: number;
    sent: number;
    received: number;
  };
}

interface WalletData {
  username: string;
  accountType: string;
  balance: string;
  growth: string | null;
  last_updated: string;
  walletId: string;
  createdAt: string;
  verified: boolean;
  adminVerified: boolean;
  premium: boolean;
  membership: string;
  publicVisible: boolean;
  active: boolean;
  locked: boolean;
  vip: boolean;
  leaderboard: {
    rank: number;
    total_users: number;
    percentile: number;
    trend: "up" | "down";
  };
  address: WalletAddress;
  security: SecurityInfo;
  transactions: Transaction[];
  stats: TransactionStats;
  ratings: {
    average_rating: number;
    total_ratings: number;
    distribution: { stars: number; percentage: number }[];
    featured_quote: { text: string; author: string; stars: number };
  };
}

interface RatingDistribution {
  stars: number;
  percentage: number;
}

interface AdvancedRatingCardProps {
  averageRating: number;
  totalRatings: number;
  distribution: RatingDistribution[];
  satisfactionRate: number;
  featuredQuote: {
    text: string;
    author: string;
    stars: number;
  };
}

// Add new design components
interface BadgeProps {
  text: string;
  variant: "blue" | "yellow" | "gray" | "green" | "purple" | "red";
  className?: string; // Add optional className prop
}

const Badge = memo<BadgeProps>(({ text, variant, className = "" }) => {
  const baseClasses =
    "px-3 py-1 rounded-full text-sm font-medium transition-all duration-300 hover:scale-105 cursor-default backdrop-blur-sm";
  const variantClasses = {
    blue: "bg-blue-800/40 text-blue-400",
    yellow: "bg-yellow-800/40 text-yellow-400",
    gray: "bg-gray-800/40 text-gray-400",
    green: "bg-green-800/40 text-green-400",
    purple: "bg-purple-800/40 text-purple-400",
    red: "bg-red-800/40 text-red-400",
  };

  return (
    <span className={`${baseClasses} ${variantClasses[variant]} ${className}`}>
      {text}
    </span>
  );
});

// 5 Stars rating component
const StarsRating = memo<{ rating: number; size?: "sm" | "md" | "lg" }>(({
  rating,
  size = "sm",
}) => {
  const sizeClasses = {
    sm: "w-3 h-3",
    md: "w-4 h-4",
    lg: "w-5 h-5",
  };

  return (
    <div className="flex">
      {[1, 2, 3, 4, 5].map((star) => (
        <Star
          key={star}
          className={`${sizeClasses[size]} ${
            star <= rating
              ? "text-yellow-400 fill-yellow-400"
              : "text-gray-300 stroke-gray-300 stroke-[1px]"
          }`}
        />
      ))}
    </div>
  );
});

const AdvancedRatingCard = memo<AdvancedRatingCardProps>(({
  averageRating = 0,
  totalRatings,
  distribution,
  featuredQuote = { text: "", author: "", stars: 0 },
}) => {
  // Форматировать рейтинг до 1 знака после запятой
  const formattedRating = Number(averageRating).toFixed(1);

  return (
    <div className="h-full flex flex-col">
      {/* рأس البطاقة */}
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-2.5">
          <div className="bg-yellow-50 p-2 rounded-lg mr-3">
            <Star
              className="w-5 h-5 text-yellow-400 fill-yellow-400"
              strokeWidth={2.5}
            />
          </div>
          <h4 className="text-lg font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent">
            User Ratings
          </h4>
        </div>
      </div>

      <div className="flex-1">
        {/* نظرة عامة على التقييم */}
        <div className="flex items-center gap-6 mb-6">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
            className={`relative flex-shrink-0 w-20 h-20 rounded-2xl flex items-center justify-center shadow-sm ${
              averageRating > 3.7
                ? "bg-gradient-to-br from-emerald-50 to-emerald-100"
                : averageRating < 2
                ? "bg-gradient-to-br from-rose-50 to-rose-100"
                : "bg-gradient-to-br from-yellow-50 to-yellow-100"
            }`}
          >
            <div className="text-center">
              <div
                className={`text-2xl font-bold ${
                  averageRating > 3.7
                    ? "text-emerald-600"
                    : averageRating < 2
                    ? "text-rose-600"
                    : "text-yellow-600"
                }`}
              >
                {formattedRating}
              </div>
              <div
                className={`text-xs font-medium ${
                  averageRating > 3.7
                    ? "text-emerald-500"
                    : averageRating < 2
                    ? "text-rose-500"
                    : "text-yellow-500"
                }`}
              >
                out of 5
              </div>
            </div>
          </motion.div>
          <div className="space-y-2.5">
            <div className="flex items-center mb-1">
              <div className="flex">
                <StarsRating rating={Math.round(averageRating)} size="lg" />
              </div>
            </div>
            <div className="flex items-center text-gray-500 text-xs bg-gray-50 px-2.5 py-1 rounded-lg w-fit">
              <Users className="w-3.5 h-3.5 mr-1.5 text-gray-400" />
              <span className="font-medium">
                {new Intl.NumberFormat("en-US").format(totalRatings)} ratings
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* توزيع التقييمات */}
      <div className="space-y-3 mb-6 bg-gray-50/50 rounded-xl p-4">
        <div className="text-xs font-medium text-gray-500 mb-3">
          Rating Distribution
        </div>
        {distribution && distribution.length > 0 ? (
          distribution.map((item) => (
            <motion.div
              key={item.stars}
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: "100%", opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.4 }}
              className="space-y-1.5"
            >
              <div className="flex justify-between text-xs text-gray-600">
                <div className="flex items-center">
                  <StarsRating rating={item.stars} size="sm" />
                </div>
                <span className="font-medium">{item.percentage}%</span>
              </div>
              <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${item.percentage}%` }}
                  transition={{ duration: 0.8, delay: 0.6 }}
                  className={`h-full rounded-full ${
                    item.stars > 3.7
                      ? "bg-emerald-400"
                      : item.stars < 2
                      ? "bg-rose-400"
                      : "bg-yellow-400"
                  }`}
                />
              </div>
            </motion.div>
          ))
        ) : (
          <div className="text-center text-gray-500 py-2">No ratings yet</div>
        )}
      </div>

      {/* Fallback for no ratings */}
      {(!featuredQuote || !featuredQuote.text) && (
        <div className="mt-auto text-center py-4 bg-gray-50 rounded-xl">
          <p className="text-gray-500 text-sm">No ratings yet</p>
        </div>
      )}

      {/* الاقتباس المميز في الأسفل */}
      {featuredQuote && featuredQuote.text && (
        <div className="bg-gradient-to-br from-gray-50 to-gray-100/50 rounded-xl p-4 relative mt-auto border border-gray-100/50">
          <Quote className="w-6 h-6 text-yellow-300 absolute -top-2 -left-2 bg-white rounded-full p-1 shadow-sm" />
          <p className="text-gray-600 text-sm italic mb-3 leading-relaxed">
            "{featuredQuote.text}"
          </p>
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-yellow-600">
              — {featuredQuote.author || "Anonymous"}
            </p>
            <div className="flex justify-center gap-1">
              <StarsRating rating={featuredQuote.stars} size="md" />
            </div>
          </div>
        </div>
      )}
    </div>
  );
});

// إضافة مكون للعد
const Counter = memo(({
  end,
  duration = 1500,
  decimals = 0,
  formatter = (value: number) => value.toString(),
  animateToDecimal = true,
  showOnlyInteger = false,
}: {
  end: number;
  duration?: number;
  decimals?: number;
  formatter?: (value: number) => string;
  animateToDecimal?: boolean;
  showOnlyInteger?: boolean;
}) => {
  const [count, setCount] = useState(0);
  const countRef = useRef<number>(0);
  const startTimeRef = useRef<number | null>(null);
  const requestRef = useRef<number>();

  useEffect(() => {
    const animate = (timestamp: number) => {
      if (startTimeRef.current === null) {
        startTimeRef.current = timestamp;
      }

      const progress = timestamp - startTimeRef.current;
      const percentage = Math.min(progress / duration, 1);

      // تحسين معادلة الحركة للانتقال بشكل أكثر سلاسة وجمالاً
      // استخدام منحنى أكثر تطوراً للحركة (cubic bezier)
      const easingFactor = 1 - Math.pow(1 - percentage, 3);

      countRef.current = percentage === 1 ? end : easingFactor * end;

      setCount(countRef.current);

      if (percentage < 1) {
        requestRef.current = requestAnimationFrame(animate);
      }
    };

    requestRef.current = requestAnimationFrame(animate);
    return () => {
      if (requestRef.current) {
        cancelAnimationFrame(requestRef.current);
      }
    };
  }, [end, duration]);

  // إذا كان المطلوب عرض الجزء الصحيح فقط
  if (showOnlyInteger) {
    return <>{Math.floor(count)}</>;
  }

  // استخدام التنسيق المناسب للرقم
  if (!animateToDecimal && decimals > 0) {
    // فصل الجزء الصحيح عن الجزء العشري
    const integerPart = Math.floor(count);
    const decimalPart = end.toString().split(".")[1] || "";

    // عرض الجزء الصحيح مع الحركة والجزء العشري بدون حركة
    return (
      <>
        {integerPart}.{decimalPart}
      </>
    );
  }

  const formattedValue = formatter(Number(count.toFixed(decimals)));
  return <>{formattedValue}</>;
});

// نضيف تعريف RatingStarsProps
interface RatingStarsProps {
  rating: number;
  setRating: (rating: number) => void;
  size?: number;
  disabled?: boolean;
  animate?: boolean;
}

// نضيف تعريف RatingModalProps
interface RatingModalProps {
  isOpen: boolean;
  onClose: () => void;
  recipientId: string;
  recipientUsername: string;
  onRatingSubmitted: () => void;
}

// نضيف مكون RatingStars للتعامل مع النجوم
const RatingStars = memo<RatingStarsProps>(({
  rating,
  setRating,
  size = 32,
  disabled = false,
  animate = true,
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
          className={`cursor-pointer transition-all duration-200 ${
            animate && "hover:scale-110"
          } ${
            (hover || rating) >= star
              ? "text-yellow-400 fill-yellow-400"
              : "text-gray-300"
          } ${disabled && "cursor-default opacity-80"}`}
        />
      ))}
    </div>
  );
});

// نضيف مكون RatingModal للتعامل مع نافذة التقييم
const RatingModal = memo(({
  isOpen,
  onClose,
  recipientId,
  recipientUsername,
  onRatingSubmitted,
}: RatingModalProps) => {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  // Maximum comment length
  const MAX_COMMENT_LENGTH = 300;

  // تمكين التمرير في الصفحة
  const enableScroll = () => {
    document.body.style.overflow = "auto";
    document.body.style.paddingRight = "0";
  };

  // تعطيل التمرير في الصفحة
  const disableScroll = () => {
    const scrollbarWidth =
      window.innerWidth - document.documentElement.clientWidth;
    document.body.style.overflow = "hidden";
    document.body.style.paddingRight = `${scrollbarWidth}px`;
  };

  // Handle close modal with scroll restoration
  const handleClose = () => {
    enableScroll();
    onClose();
  };

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setRating(0);
      setComment("");
      setError("");
      setSuccess(false);
      disableScroll(); // تعطيل التمرير عند فتح النافذة
    }
  }, [isOpen]);

  const handleSubmit = async () => {
    if (rating === 0) {
      setError("Please select a rating");
      return;
    }
    if (comment.length > MAX_COMMENT_LENGTH) {
      setError(`Comment cannot exceed ${MAX_COMMENT_LENGTH} characters`);
      return;
    }
    setIsSubmitting(true);
    setError("");
    try {
      const response = await fetch("/api/ratings/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          recipient_id: recipientId,
          stars: rating,
          comment: comment.trim() || null,
        }),
      });
      if (response.ok) {
        setSuccess(true);
        setTimeout(() => {
          enableScroll(); // إعادة تمكين التمرير عند الإغلاق
          onRatingSubmitted();
          onClose();
        }, 1500);
      } else {
        const data = await response.json();
        setError(data.error || "Failed to submit rating");
      }
    } catch (error) {
      setError("An error occurred. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCommentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newComment = e.target.value;
    setComment(newComment);
    if (
      error.includes("character") &&
      newComment.length <= MAX_COMMENT_LENGTH
    ) {
      setError("");
    }
  };

  const getCharCountColor = () => {
    const remaining = MAX_COMMENT_LENGTH - comment.length;
    if (remaining <= 0) return "text-red-600";
    if (remaining < 50) return "text-orange-500";
    return "text-gray-500";
  };

  if (!isOpen) return null;

  return (
    <div className="bg-black bg-opacity-60 flex items-center justify-center p-4 animate-fadeIn w-full h-full">
      <div className="bg-[#23262F] rounded-2xl shadow-2xl w-full max-w-md overflow-hidden border border-[#34343A] relative animate-scaleIn">
        {/* Header */}
        <div className="flex items-center gap-3 px-6 pt-6 pb-2">
          <div className="bg-yellow-400/10 p-2 rounded-lg mr-3">
            <Star
              className="w-5 h-5 text-yellow-400 fill-yellow-400"
              strokeWidth={2.5}
            />
          </div>
          <h2 className="text-white text-xl font-bold">Rate Your Experience</h2>
          <button
            className="ml-auto text-gray-400 hover:text-white text-xl"
            onClick={handleClose}
          >
            ×
          </button>
        </div>
        {/* Info */}
        <div className="bg-green-500/10 border border-green-600/30 text-green-400 flex items-center gap-2 px-6 py-3 mx-6 mt-3 rounded-lg text-sm">
          <Info className="w-5 h-5" />
          How was your transaction with {recipientUsername || "this user"}?
        </div>
        {/* Fields */}
        <div className="px-6 py-6">
          <label className="block text-gray-300 font-medium mb-2 text-base">
            Rating
          </label>
          <div className="flex items-center justify-center mb-5">
            <RatingStars
              rating={rating}
              setRating={setRating}
              size={32}
              animate={true}
            />
          </div>
          <label className="block text-gray-300 font-medium mb-2 text-base">
            Comment <span className="text-gray-400 text-xs">(Optional)</span>
          </label>
          <div className="flex items-center bg-[#2A2A2E] border border-[#34343A] rounded-lg px-4 py-3 mb-2">
            <textarea
              value={comment}
              onChange={handleCommentChange}
              placeholder="Share your experience..."
              className="bg-transparent outline-none text-white flex-1 text-base placeholder-gray-500 resize-none min-h-[60px]"
              rows={3}
              maxLength={MAX_COMMENT_LENGTH}
            />
          </div>
          <div className={`text-xs ${getCharCountColor()} text-right mb-2`}>
            {comment.length}/{MAX_COMMENT_LENGTH} characters
          </div>
          {error && (
            <div className="bg-red-900/20 border border-red-700 text-red-400 px-3 py-2 rounded-lg mb-4 text-sm flex items-start">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-5 w-5 mr-2 flex-shrink-0 mt-0.5"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
              {error}
            </div>
          )}
          {success ? (
            <div className="flex flex-col items-center justify-center py-6">
              <div className="w-14 h-14 bg-green-100 rounded-full flex items-center justify-center mb-4">
                <CheckCircle size={28} className="text-green-500" />
              </div>
              <h4 className="text-lg font-bold text-green-400 mb-2">
                Thank you!
              </h4>
              <p className="text-center text-gray-300 text-sm">
                Your rating has been submitted successfully.
              </p>
            </div>
          ) : (
            <div className="flex gap-3 mt-6">
              <button
                className="flex-1 py-3 rounded-xl bg-[#313131] text-white font-semibold hover:bg-[#393939] transition"
                onClick={handleClose}
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                className="flex-1 py-3 rounded-xl bg-gradient-to-r from-green-500 to-emerald-600 text-white font-bold hover:opacity-90 transition disabled:opacity-50"
                onClick={handleSubmit}
                disabled={
                  isSubmitting ||
                  rating === 0 ||
                  comment.length > MAX_COMMENT_LENGTH
                }
              >
                {isSubmitting ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin inline-block mr-2"></span>
                    Submitting...
                  </>
                ) : (
                  <>Submit Rating</>
                )}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

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

// Format transaction date prettier
const formatTransactionDate = (dateStr: string): string => {
  if (!dateStr || dateStr === "Unknown date") return dateStr;
  
  try {
    // Parse the date string (format: YYYY-MM-DD HH:MM)
    const date = new Date(dateStr);
    
    // Check if date is valid
    if (isNaN(date.getTime())) return dateStr;
    
    // Get today and yesterday for comparison
    const today = new Date();
    const yesterday = new Date();
    yesterday.setDate(today.getDate() - 1);
    
    // Format the date based on how recent it is
    const isToday = date.toDateString() === today.toDateString();
    const isYesterday = date.toDateString() === yesterday.toDateString();
    
    if (isToday) {
      // For today's transactions, show "Today, HH:MM"
      return `Today, ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } else if (isYesterday) {
      // For yesterday's transactions, show "Yesterday, HH:MM"
      return `Yesterday, ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } else {
      // For older transactions, show "MMM DD, YYYY HH:MM"
      return date.toLocaleString([], { 
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    }
  } catch (e) {
    // Return the original string if any error occurs
    return dateStr;
  }
};

const Overview: React.FC = () => {
  const navigate = useNavigate();

  // State for wallet data
  const [walletData, setWalletData] = useState<WalletData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  // Add polling interval for real-time updates
  const [isPolling, setIsPolling] = useState<boolean>(false); // Changed from true to false
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // إضافة مرجع للبطاقة
  const transactionCardRef = useRef<HTMLDivElement>(null);

  // متغيرات للتحكم في نافذة التقييم
  const [showRatingModal, setShowRatingModal] = useState<boolean>(false);
  const [currentRatingTransaction, setCurrentRatingTransaction] =
    useState<Transaction | null>(null);
  const [ratingSubmitted, setRatingSubmitted] = useState<boolean>(false);

  // Add viewport meta tag for mobile responsiveness
  useEffect(() => {
    // Get existing viewport meta tag
    let viewportMeta = document.querySelector('meta[name="viewport"]');

    // If it doesn't exist, create it
    if (!viewportMeta) {
      viewportMeta = document.createElement("meta");
      viewportMeta.setAttribute("name", "viewport");
      document.head.appendChild(viewportMeta);
    }

    // Set the content to optimize for mobile devices
    viewportMeta.setAttribute(
      "content",
      "width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"
    );

    // Clean up function
    return () => {
      if (
        !document.querySelector('meta[name="viewport"][data-original="true"]')
      ) {
        viewportMeta.setAttribute(
          "content",
          "width=device-width, initial-scale=1.0"
        );
      }
    };
  }, []);

  // Add responsive optimization hook for mobile devices
  useEffect(() => {
    const handleMobileOptimization = () => {
      // Apply specific styles for mobile devices
      if (window.innerWidth < 768) {
        // Make cards more compact
        document.querySelectorAll(".card-content").forEach((card) => {
          card.classList.add("card-compact");
        });

        // Adjust font sizes for better readability
        document.querySelectorAll(".text-base").forEach((text) => {
          text.classList.add("mobile-text-xs");
        });

        // Fix scroll behavior
        document.body.style.overscrollBehavior = "none";
      } else {
        // Remove mobile-specific classes when on desktop
        document.querySelectorAll(".card-compact").forEach((card) => {
          card.classList.remove("card-compact");
        });

        document.querySelectorAll(".mobile-text-xs").forEach((text) => {
          text.classList.remove("mobile-text-xs");
        });

        document.body.style.overscrollBehavior = "auto";
      }
    };

    // Run immediately and add event listener
    handleMobileOptimization();
    window.addEventListener("resize", handleMobileOptimization);

    return () => {
      window.removeEventListener("resize", handleMobileOptimization);
    };
  }, []);

  // States for new UI components
  const [timeframe, setTimeframe] = useState<"daily" | "weekly" | "monthly">(
    "daily"
  );
  const [isChartLoading, setIsChartLoading] = useState(false);
  const [chartData, setChartData] = useState([
    { name: "Week 1", value: 0 },
    { name: "Week 2", value: 0 },
    { name: "Week 3", value: 0 },
    { name: "Week 4", value: 0 },
    { name: "Week 5", value: 0 },
    { name: "Week 6", value: 0 },
  ]);
  const [chartSummary, setChartSummary] = useState<number>(0);
  const [selectedDataPoint, setSelectedDataPoint] = useState<{
    time: string;
    value: number;
  } | null>(null);
  const [inactivityHours, setInactivityHours] = useState<number | null>(null);

  // بيانات مفصلة لكل إطار زمني - will be replaced with real data
  const timeframeData = {
    daily: [
      { name: "00:00", value: 0 },
      { name: "04:00", value: 0 },
      { name: "08:00", value: 0 },
      { name: "12:00", value: 0 },
      { name: "16:00", value: 0 },
      { name: "20:00", value: 0 },
    ],
    weekly: [
      { name: "Sunday", value: 0 },
      { name: "Monday", value: 0 },
      { name: "Tuesday", value: 0 },
      { name: "Wednesday", value: 0 },
      { name: "Thursday", value: 0 },
      { name: "Friday", value: 0 },
      { name: "Saturday", value: 0 },
    ],
    monthly: [
      { name: "Week 1", value: 0 },
      { name: "Week 2", value: 0 },
      { name: "Week 3", value: 0 },
      { name: "Week 4", value: 0 },
    ],
  };

  // States for Recent Transactions component
  const [activeMenu, setActiveMenu] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: string } | null>(
    null
  );

  // Add new state variables for wallet address component
  const [activeTab, setActiveTab] = useState<"public" | "private">("public");
  const [showPublic, setShowPublic] = useState(false);
  const [showPrivate, setShowPrivate] = useState(false);

  // إضافة مستمع لإغلاق القائمة المنسدلة عند النقر في أي مكان آخر
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (activeMenu && !(event.target as Element).closest(".dropdown-menu")) {
        setActiveMenu(null);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [activeMenu]);

  // إضافة useEffect لتطبيق الصنف 'small' على البطاقات الصغيرة
  useEffect(() => {
    const handleResize = () => {
      const card = transactionCardRef.current;
      if (card) {
        if (card.offsetWidth < 200) {
          card.classList.add("small");
          // تطبيق أسلوب مباشر على عناصر العنوان
          const titleWords = card.querySelectorAll(".transaction-title-word");
          titleWords.forEach((word) => {
            (word as HTMLElement).style.display = "block";
            (word as HTMLElement).style.width = "100%";
          });
        } else {
          card.classList.remove("small");
          // إعادة تعيين الأسلوب
          const titleWords = card.querySelectorAll(".transaction-title-word");
          titleWords.forEach((word) => {
            (word as HTMLElement).style.display = "inline-block";
            (word as HTMLElement).style.width = "auto";
          });
        }
      }
    };

    // تنفيذ عند التحميل وعند تغيير الحجم
    handleResize();

    // إنشاء مراقب مقاسات لمراقبة تغييرات حجم البطاقة نفسها
    if (transactionCardRef.current) {
      const resizeObserver = new ResizeObserver(handleResize);
      resizeObserver.observe(transactionCardRef.current);

      // تنظيف عند الإزالة
      return () => {
        if (transactionCardRef.current) {
          resizeObserver.unobserve(transactionCardRef.current);
        }
        resizeObserver.disconnect();
      };
    }

    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  // استخدام useEffect لإضافة معالجة خاصة للعرض 1024-1435
  useEffect(() => {
    const handleScreenSizeForTransactions = () => {
      const transactionStats = document.querySelector(".transaction-stats");
      if (transactionStats) {
        // تطبيق التغييرات فقط في نطاق الشاشات المطلوب
        if (window.innerWidth >= 1024 && window.innerWidth <= 1435) {
          transactionStats.classList.add("vertical-stats");

          // التأكد من أن "sent" فوق "received"
          const sentStats = transactionStats.querySelector(".sent-stats");
          const receivedStats =
            transactionStats.querySelector(".received-stats");

          if (
            sentStats &&
            receivedStats &&
            transactionStats.children[0] !== sentStats
          ) {
            // إعادة ترتيب العناصر إذا لم تكن بالترتيب الصحيح
            transactionStats.appendChild(sentStats);
            transactionStats.appendChild(receivedStats);
          }
        } else {
          transactionStats.classList.remove("vertical-stats");
        }
      }
    };

    // تنفيذ الدالة مباشرة وإضافة مستمع للتغييرات
    handleScreenSizeForTransactions();
    window.addEventListener("resize", handleScreenSizeForTransactions);

    // تنظيف عند الإزالة
    return () => {
      window.removeEventListener("resize", handleScreenSizeForTransactions);
    };
  }, []);

  // Fetch wallet data function
  const fetchWalletData = useCallback(async () => {
    try {
      const response = await fetch("/api/overview");
      if (!response.ok) {
        throw new Error("Failed to fetch wallet data");
      }
      const data = await response.json();

      // إضافة معرف المستلم للمعاملات المرسلة
      if (data.transactions && Array.isArray(data.transactions)) {
        data.transactions = data.transactions.map(
          (transaction: Transaction) => {
            // إذا كانت المعاملة من نوع "sent" وتحتوي على عنوان
            if (transaction.type === "sent" && transaction.address) {
              // استخدام نفس العنوان كمعرف للمستلم مؤقتاً
              // في التطبيق الحقيقي، يجب أن يأتي هذا من الخادم
              return {
                ...transaction,
                recipientId: transaction.address,
              };
            }
            return transaction;
          }
        );
      }

      setWalletData(data);
      setLoading(false);
    } catch (error) {
      console.error("Error fetching wallet data:", error);
      setError("Failed to load wallet data. Please try again later.");
      setLoading(false);
    }
  }, []);

  // Add function to fetch growth data with improved error handling for the new system
  const fetchGrowthData = useCallback(async (period: "daily" | "weekly" | "monthly") => {
    setIsChartLoading(true);
    try {
      const response = await fetch(`/api/wallet/growth?period=${period}`);
      if (!response.ok) {
        throw new Error("Failed to fetch growth data");
      }

      const data = await response.json();

      if (data && data.data && Array.isArray(data.data)) {
        // Process data to ensure proper formatting and handle any inconsistencies
        const processedData = data.data.map((item: any) => ({
          name: item.name || "",
          value: typeof item.value === 'number' ? item.value : parseFloat(item.value || "0")
        }));
        
        setChartData(processedData);
        setChartSummary(data.total || 0);

        // Check if user was inactive (returning after a while)
        if (data.time_since_last_access) {
          setInactivityHours(data.time_since_last_access);

          // Show inactivity notification
          hotToast.success(
            `بيانات النمو محدثة. لقد مر ${data.time_since_last_access} ساعات منذ آخر زيارة.`,
            {
              duration: 5000,
              style: {
                background: "#3b82f6",
                color: "#fff",
                fontWeight: "bold",
                padding: "16px",
                borderRadius: "8px",
              },
            }
          );
        } else {
          setInactivityHours(null);
        }
        
        // If we have data about the data source, show a notification
        if (data.data_source) {
          console.log(`Growth data source: ${data.data_source}`);
        }
      } else {
        // Fallback to sample data if response format is incorrect
        setChartData(timeframeData[period]);
        setChartSummary(
          period === "daily" ? 1660 : period === "weekly" ? 3700 : 15200
        );
      }
    } catch (error) {
      console.error("Error fetching growth data:", error);
      // Fallback to sample data on error
      setChartData(timeframeData[period]);
      setChartSummary(
        period === "daily" ? 1660 : period === "weekly" ? 3700 : 15200
      );
    } finally {
      setIsChartLoading(false);
    }
  }, []);

  // Set up polling for real-time updates
  useEffect(() => {
    // Initial data fetch
    fetchWalletData();
    fetchGrowthData(timeframe);

    // Set up polling interval (every 10 seconds)
    if (isPolling) {
      pollingIntervalRef.current = setInterval(() => {
        fetchWalletData();
        fetchGrowthData(timeframe);
      }, 60000); // Changed from 10000 (10 seconds) to 60000 (1 minute)
    }

    // Clean up on unmount
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [isPolling, timeframe, fetchWalletData, fetchGrowthData]);

  // Format date for last updated display
  const formatLastUpdated = useCallback((dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }, []);

  // Refactored useEffect for timeframe changes
  useEffect(() => {
    fetchGrowthData(timeframe);
  }, [timeframe]);

  // Update copyToClipboard function
  const copyToClipboard = useCallback((text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopied(field);

    // Use react-hot-toast's toast notification
    const toastId = hotToast.custom((t) => (
      <div
        className="flex items-center gap-3"
        style={{
          position: "fixed",
          top: "55px",
          right: "2px",
          zIndex: 1001,
          background: "#2e2e2e",
          color: "#22c55e",
          fontWeight: 600,
          padding: "18px 28px",
          borderRadius: 12,
          boxShadow: "0 4px 24px 0 rgba(0,0,0,0.10)",
          border: "1px solid #2e2e2e",
          minWidth: 260,
          maxWidth: 400,
        }}
      >
        <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-green-500/10">
          <svg
            className="w-5 h-5 text-green-500"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M5 13l4 4L19 7"
            />
          </svg>
        </span>
        <span className="font-semibold text-green-500 text-base">
          Transaction ID copied
        </span>
      </div>
    ));
    setTimeout(() => hotToast.dismiss(toastId), 2000);
  }, []);

  // Re-add required functions
  const handleMenuToggle = useCallback((transactionId: string) => {
    setActiveMenu(activeMenu === transactionId ? null : transactionId);
  }, [activeMenu]);

  const handleAction = useCallback((action: string, transaction: Transaction) => {
    if (action === "Copy") {
      // Use the actual transaction ID from the transaction object
      navigator.clipboard.writeText(transaction.tx_id);
      hotToast.success("Transaction ID copied to clipboard", {
        duration: 2000,
      });
    } else if (action === "View") {
      // Navigate to transaction details page with the transaction ID
      navigate(`/transactions/${transaction.tx_id}`);
    } else if (action === "Repeat") {
      // Navigate to send page with the transaction recipient pre-filled
      navigate(`/send?recipient=${transaction.address}`);
    }

    setActiveMenu(null);
  }, [navigate, setActiveMenu]);

  // Handle rating submission
  const handleRatingSubmitted = useCallback(() => {
    setRatingSubmitted(true);
    setShowRatingModal(false);

    // Show success message
    hotToast.success("Rating submitted successfully", {
      style: {
        background: "#10b981",
        color: "#fff",
        fontWeight: "bold",
        padding: "16px",
        borderRadius: "8px",
      },
      iconTheme: {
        primary: "#fff",
        secondary: "#10b981",
      },
      duration: 3000,
    });
  }, []);

  // Fix the CustomTooltip component - replace useMemo with useCallback
  const CustomTooltip = useCallback(({ 
    active,
    payload,
    label 
  }: any) => {
    if (active && payload && payload.length) {
      // Set selected data point for highlighting
      if (payload[0].value !== undefined && label) {
        setSelectedDataPoint({
          time: label,
          value: payload[0].value,
        });
      }

      return (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-[#1C1C1E]/90 backdrop-blur-lg border border-[#3A3A3E] p-4 rounded-xl shadow-lg"
        >
          <p className="text-sm font-medium text-[#E5E5E5]">{label}</p>
          <div className="flex items-baseline space-x-1 mt-1">
            <span className="text-lg font-semibold text-[#7B61FF]">
              {payload[0].value.toFixed(2)}
            </span>
            <span className="text-sm text-[#A1A1AA]">CRN</span>
          </div>
        </motion.div>
      );
    }

    // Clear selected data point when tooltip is inactive
    if (!active) {
      setSelectedDataPoint(null);
    }

    return null;
  }, [setSelectedDataPoint]);

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mb-4"></div>
          <p className="text-gray-600">Loading wallet data...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !walletData) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center p-6 bg-red-50 rounded-lg max-w-md">
          <div className="text-red-500 text-4xl mb-4">⚠️</div>
          <h2 className="text-xl font-bold text-red-700 mb-2">
            Error Loading Data
          </h2>
          <p className="text-gray-700 mb-4">
            {error || "Unable to load wallet data. Please try again later."}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[#262626] min-h-screen pb-10 relative">
      <MobileOptimization />
      <div className="max-w-7xl mx-auto px-2 sm:px-4 py-3 sm:py-6">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-12 gap-3 sm:gap-4">
          {/* Total Balance Card */}
          <motion.div className="order-1 col-span-full md:col-span-1 xl:col-span-6 bg-[#2b2b2b] rounded-2xl p-4 sm:p-6 shadow-lg transition-all duration-300 hover:shadow-2xl">
            <div className="flex justify-between items-start">
              <div className="w-full">
                <div className="flex justify-between items-center w-full">
                  <h2 className="text-[#FFFFFF] font-semibold tracking-wide text-base">
                    Total Balance
                  </h2>
                  <div className="bg-[#8B5CF6]/10 p-2 rounded-xl block md:hidden">
                    <CreditCard
                      className="w-5 h-5 text-[#8B5CF6]"
                      strokeWidth={2}
                    />
                  </div>
                </div>
                <div className="flex items-baseline mt-3">
                  <span className="max-[315px]:text-2xl text-4xl font-bold text-white tracking-tight">
                    <Counter
                      end={Math.floor(parseFloat(walletData.balance))}
                      duration={1200}
                    />
                    <span className="text-white">
                      {walletData.balance.includes(".")
                        ? "." + walletData.balance.split(".")[1]
                        : ""}
                    </span>
                  </span>
                  <span className="max-[315px]:text-xs text-[#8B5CF6] font-medium ml-2">
                    CRN
                  </span>
                </div>
                <div className="flex items-center mt-3">
                  {walletData.growth ? (
                    <>
                      <div className="flex items-center">
                        {walletData.growth.startsWith("+") ? (
                          <TrendingUp
                            className="w-4 h-4 mr-1.5 text-green-400"
                            strokeWidth={2.5}
                          />
                        ) : (
                          <TrendingDown
                            className="w-4 h-4 mr-1.5 text-red-400"
                            strokeWidth={2.5}
                          />
                        )}
                        <span
                          className={`max-[315px]:text-xs font-semibold text-sm ${
                            walletData.growth.startsWith("+")
                              ? "text-green-400"
                              : "text-red-400"
                          }`}
                        >
                          {walletData.growth}
                        </span>
                      </div>
                      <span className="text-[#B0B0B5] text-xs mx-2">•</span>
                    </>
                  ) : null}
                  <span className="max-[315px]:text-[10px] text-[#B0B0B5] text-xs">
                    Updated {formatLastUpdated(walletData.last_updated)}
                  </span>
                </div>
              </div>
              <div className="bg-[#8B5CF6]/10 p-3 rounded-xl hidden md:block">
                <CreditCard
                  className="w-6 h-6 text-[#8B5CF6]"
                  strokeWidth={2}
                />
              </div>
            </div>
          </motion.div>

          <style>{`
            .wallet-icon-mobile {
              display: none;
            }

            .wallet-icon-desktop {
              display: block;
            }

            @media (max-width: 300px) {
              .wallet-icon-mobile {
                display: block;
              }

              .wallet-icon-desktop {
                display: none;
              }
            }
          `}</style>

          {/* Total Transactions Card */}
          <motion.div className="order-2 col-span-full md:col-span-1 xl:col-span-3 bg-[#2b2b2b] rounded-2xl p-4 sm:p-6 shadow-lg transition-all duration-300 hover:shadow-2xl">
            <div
              className="flex justify-between items-start"
              style={{ flexWrap: "nowrap" }}
            >
              <div style={{ minWidth: 0, flex: 1, marginRight: "10px" }}>
                <h4
                  className="text-[#FFFFFF] font-semibold tracking-wide text-base transaction-card-title"
                  style={{ maxWidth: "100%", wordWrap: "break-word" }}
                >
                  <span className="transaction-title-word">Total</span>{" "}
                  <span className="transaction-title-word">Transactions</span>
                </h4>
                <div className="mt-3">
                  <div className="text-4xl font-bold text-white tracking-tight">
                    <Counter
                      end={walletData.stats.total.count}
                      duration={900}
                    />
                    <span className="text-sm font-medium text-[#B0B0B5] ml-2">
                      transactions
                    </span>
                  </div>
                </div>
                {/* تم ترتيب sent أولا ثم received لضمان ظهورهما بشكل صحيح وفي النطاق 1024-1435 */}
                <div
                  className="transaction-stats flex items-center justify-between mt-3 text-sm font-medium"
                  id="transaction-stats-container"
                >
                  <div className="flex items-center gap-2 sent-stats">
                    <div className="flex items-center gap-1.5">
                      <span className="text-red-400">
                        <Counter
                          end={walletData.stats.total.sent}
                          duration={800}
                        />
                      </span>
                      <span className="text-red-400">sent</span>
                      <ArrowUpRight
                        className="w-4 h-4 text-red-400"
                        strokeWidth={2.5}
                      />
                    </div>
                  </div>
                  <div className="flex items-center gap-2 received-stats">
                    <div className="flex items-center gap-1.5">
                      <span className="text-green-400">
                        <Counter
                          end={walletData.stats.total.received}
                          duration={800}
                        />
                      </span>
                      <span className="text-green-400">received</span>
                      <ArrowDownRight
                        className="w-4 h-4 text-green-400"
                        strokeWidth={2.5}
                      />
                    </div>
                  </div>
                </div>
              </div>
              <div
                className="bg-blue-400/10 p-3 rounded-xl flex-shrink-0"
                style={{
                  width: "42px",
                  height: "42px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  position: "relative",
                }}
              >
                <ArrowRightLeft
                  className="w-6 h-6 text-blue-400"
                  strokeWidth={2}
                />
              </div>
            </div>
          </motion.div>

          {/* Leaderboard Rank Card */}
          <motion.div className="order-3 col-span-full xl:col-span-3 bg-[#2b2b2b] rounded-2xl p-6 shadow-lg transition-all duration-300 hover:shadow-2xl">
            <div className="flex justify-between items-start">
              <div>
                <h4 className="text-[#FFFFFF] font-semibold tracking-wide text-base">
                  Leaderboard Rank
                </h4>
                <div className="mt-3">
                  <div className="text-4xl font-bold text-white tracking-tight">
                    <Counter 
                      end={walletData.leaderboard.rank && walletData.leaderboard.rank > 0 ? walletData.leaderboard.rank : 1} 
                      duration={900} 
                    />
                  </div>
                </div>
                <div className="flex items-center mt-3 text-sm font-medium">
                  {walletData.leaderboard.trend === "up" ? (
                    <div className="flex items-center">
                      <TrendingUp
                        className="w-4 h-4 mr-1.5 text-green-400"
                        strokeWidth={2.5}
                      />
                      <span className="text-green-400">
                        Top {walletData.leaderboard.percentile}%
                      </span>
                    </div>
                  ) : (
                    <div className="flex items-center">
                      <TrendingDown
                        className="w-4 h-4 mr-1.5 text-red-400"
                        strokeWidth={2.5}
                      />
                      <span className="text-red-400">
                        Down {walletData.leaderboard.percentile}%
                      </span>
                    </div>
                  )}
                </div>
              </div>
              <div className="bg-yellow-400/10 p-3 rounded-xl">
                <Trophy className="w-6 h-6 text-yellow-400" strokeWidth={2} />
              </div>
            </div>
          </motion.div>

          {/* Growth Wallet Chart */}
          <motion.div className="order-4 col-span-full xl:col-span-8 bg-[#2b2b2b] rounded-2xl shadow-sm p-4 md:p-6">
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center mb-4 md:mb-8 gap-4">
              <div className="flex items-center space-x-3">
                <div className="bg-[#8B5CF6]/20 p-2 rounded-lg mr-3">
                  <LineChartIcon
                    className="w-5 h-5 text-[#9D8DFF]"
                    strokeWidth={2.5}
                  />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">
                    Growth Wallet
                  </h3>
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="text-sm text-[#C4C4C7] font-medium mt-1"
                  >
                    {timeframe === "daily"
                      ? "Daily Summary"
                      : timeframe === "weekly"
                      ? "Weekly Summary"
                      : "Monthly Summary"}
                    : {chartSummary.toFixed(2)} CRN
                    {inactivityHours && (
                      <span className="ml-2 text-[#9D8DFF]">
                        <span
                          title={`${inactivityHours} hours since last visit`}
                        >
                          <HelpCircle size={14} className="inline-block ml-1" />
                        </span>
                      </span>
                    )}
                  </motion.p>
                </div>
              </div>

              {/* قائمة منسدلة للشاشة الصغيرة */}
              <div className="self-start sm:self-center md:hidden relative w-full max-w-[180px] ml-auto">
                <select
                  value={timeframe}
                  onChange={(e) =>
                    setTimeframe(
                      e.target.value as "daily" | "weekly" | "monthly"
                    )
                  }
                  className="w-full bg-[#2A2A2E] border border-[#C4C4C7]/20 text-[#FFFFFF] py-2 px-4 pr-8 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-[#8875FF] focus:border-transparent appearance-none cursor-pointer"
                >
                  <option value="daily" className="py-2">
                    Daily
                  </option>
                  <option value="weekly" className="py-2">
                    Weekly
                  </option>
                  <option value="monthly" className="py-2">
                    Monthly
                  </option>
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-[#C4C4C7]">
                  <svg className="w-4 h-4 fill-current" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
              </div>

              {/* أزرار للشاشة الكبيرة */}
              <div className="hidden md:flex items-center ml-auto">
                {(["daily", "weekly", "monthly"] as const).map((frame) => (
                  <motion.button
                    key={frame}
                    onClick={() => setTimeframe(frame)}
                    className={`flex items-center gap-2 px-4 py-2 mx-1 rounded-lg text-sm font-medium transition-all duration-200 ${
                      timeframe === frame
                        ? "bg-[#8B5CF6] text-white shadow-sm"
                        : "bg-[#2C2C3C] text-[#9CA3AF] hover:bg-[#2E2E3E]"
                    }`}
                  >
                    <Calendar className="w-4 h-4" />
                    <span className="capitalize">{frame}</span>
                  </motion.button>
                ))}
              </div>
            </div>

            {/* Chart Container */}
            <AnimatePresence mode="wait">
              <motion.div
                key={timeframe}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.3 }}
                className="h-44 sm:h-56 md:h-72 w-full"
              >
                {isChartLoading ? (
                  <div className="h-full w-full flex items-center justify-center">
                    <div className="animate-pulse space-y-4 w-full">
                      <div className="h-4 bg-[#3A3A3E] rounded w-3/4"></div>
                      <div className="h-40 bg-[#3A3A3E] rounded"></div>
                      <div className="h-4 bg-[#3A3A3E] rounded w-1/2"></div>
                    </div>
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={chartData}
                      margin={{ top: 20, right: 20, left: 5, bottom: 20 }}
                      onMouseLeave={() => setSelectedDataPoint(null)}
                    >
                      <defs>
                        <linearGradient
                          id="colorValue"
                          x1="0"
                          y1="0"
                          x2="0"
                          y2="1"
                        >
                          <stop
                            offset="5%"
                            stopColor="#9D8DFF"
                            stopOpacity={0.2}
                          />
                          <stop
                            offset="95%"
                            stopColor="#9D8DFF"
                            stopOpacity={0}
                          />
                        </linearGradient>
                        <filter id="shadow">
                          <feDropShadow
                            dx="0"
                            dy="1"
                            stdDeviation="2"
                            floodColor="#9D8DFF"
                            floodOpacity="0.3"
                          />
                        </filter>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#2E2E3E" />
                      <XAxis
                        dataKey="name"
                        stroke="#9CA3AF"
                        fontSize={12}
                        tickLine={false}
                        axisLine={{ stroke: "#2E2E3E" }}
                      />
                      <YAxis
                        stroke="#9CA3AF"
                        fontSize={12}
                        tickLine={false}
                        axisLine={{ stroke: "#2E2E3E" }}
                        domain={[0, "auto"]}
                        tickFormatter={(value) => `${value}`}
                      />
                      <RechartsTooltip
                        content={CustomTooltip}
                        cursor={{
                          stroke: "#9D8DFF",
                          strokeWidth: 1,
                          strokeDasharray: "5 5",
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="value"
                        stroke="#8B5CF6"
                        strokeWidth={2.5}
                        dot={(props: any) => {
                          // Check if this dot corresponds to the selected data point
                          const isSelected =
                            selectedDataPoint &&
                            props.payload &&
                            props.payload.name === selectedDataPoint.time &&
                            props.payload.value === selectedDataPoint.value;

                          return isSelected ? (
                            <circle
                              cx={props.cx}
                              cy={props.cy}
                              r={8}
                              fill="#9D8DFF"
                              stroke="#fff"
                              strokeWidth={2}
                              filter="url(#shadow)"
                            />
                          ) : (
                            <circle
                              cx={props.cx}
                              cy={props.cy}
                              r={0}
                              fill="transparent"
                            />
                          );
                        }}
                        activeDot={{
                          r: 8,
                          fill: "#9D8DFF",
                          stroke: "#fff",
                          strokeWidth: 2,
                          filter: "url(#shadow)",
                        }}
                        fill="url(#colorValue)"
                        filter="url(#shadow)"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                )}
              </motion.div>
            </AnimatePresence>

            {/* بطاقات المبالغ الأعلى والأدنى */}
            <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 mt-4 sm:mt-6">
              {/* Highest Amount */}
              <div className="flex-1 bg-[#2e2e2e] rounded-xl p-3 sm:p-4 md:p-5 transition-all duration-300 hover:shadow-md shadow-sm">
                <div className="flex justify-between items-start h-full">
                  <div className="flex-1 min-w-0">
                    <h4 className="text-[#FFFFFF] font-semibold tracking-wide text-base">
                      Highest Amount
                    </h4>
                    <div className="mt-3">
                      <div className="flex items-center">
                        <div className="text-xl font-bold text-white tracking-tight truncate">
                          <Counter
                            end={Math.floor(walletData.stats.highest.amount)}
                            duration={1000}
                          />
                          <span className="text-white">
                            {String(walletData.stats.highest.amount).includes(
                              "."
                            )
                              ? "." +
                                String(walletData.stats.highest.amount)
                                  .split(".")[1]
                                  .padEnd(8, "0")
                              : ".00000000"}
                          </span>
                          <span className="text-xs font-medium text-emerald-500 ml-1">
                            CRN
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center mt-2 text-xs text-emerald-600 font-medium">
                      <TrendingUp
                        className="w-3.5 h-3.5 mr-1.5 text-emerald-500"
                        strokeWidth={2.5}
                      />
                      <span className="text-emerald-600">
                        {walletData.stats.highest.change}
                      </span>
                    </div>
                  </div>
                  <div className="bg-emerald-500/15 p-3 rounded-xl flex-shrink-0">
                    <ArrowUpRight
                      className="w-5 h-5 text-emerald-500"
                      strokeWidth={2.5}
                    />
                  </div>
                </div>
              </div>

              {/* Lowest Amount */}
              <div className="flex-1 bg-[#2e2e2e] rounded-xl p-4 md:p-5 transition-all duration-300 hover:shadow-md shadow-sm">
                <div className="flex justify-between items-start h-full">
                  <div className="flex-1 min-w-0">
                    <h4 className="text-[#FFFFFF] font-semibold tracking-wide text-base">
                      Lowest Amount
                    </h4>
                    <div className="mt-3">
                      <div className="flex items-center">
                        <div className="text-xl font-bold text-white tracking-tight truncate">
                          <Counter
                            end={Math.floor(walletData.stats.lowest.amount)}
                            duration={1000}
                          />
                          <span className="text-white">
                            {String(walletData.stats.lowest.amount).includes(
                              "."
                            )
                              ? "." +
                                String(walletData.stats.lowest.amount)
                                  .split(".")[1]
                                  .padEnd(8, "0")
                              : ".00000000"}
                          </span>
                          <span className="text-xs font-medium text-rose-500 ml-1">
                            CRN
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center mt-2 text-xs text-rose-600 font-medium">
                      <TrendingDown
                        className="w-3.5 h-3.5 mr-1.5 text-rose-500"
                        strokeWidth={2.5}
                      />
                      <span className="text-rose-600">
                        {walletData.stats.lowest.change}
                      </span>
                    </div>
                  </div>
                  <div
                    className={`bg-rose-500/15 p-3 rounded-xl flex-shrink-0`}
                  >
                    <ArrowDownRight
                      className="w-5 h-5 text-rose-500"
                      strokeWidth={2.5}
                    />
                  </div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Recent Transactions */}
          <motion.div className="order-5 col-span-full xl:col-span-8 bg-[#2b2b2b] rounded-2xl shadow-sm relative">
            {/* Toast Notification */}
            {toast && (
              <div
                className={`absolute top-4 right-4 px-4 py-2 rounded-lg text-white text-sm font-medium transform transition-all duration-500 ease-in-out ${
                  toast.type === "success" ? "bg-green-500" : "bg-red-500"
                }`}
                style={{ animation: "slideIn 0.5s ease-out" }}
              >
                {toast.message}
              </div>
            )}

            <div className="flex justify-between items-center p-3 sm:p-6 sm:pb-4 pb-2">
              <div className="flex items-center gap-2 sm:gap-2.5">
                <div className="bg-[#8B5CF6]/20 p-2 rounded-lg sm:mr-3">
                  <Activity
                    className="w-5 h-5 text-[#9D8DFF] fill-[#8B5CF6]/10"
                    strokeWidth={2.5}
                  />
                </div>
                <h3 className="text-base sm:text-lg font-bold text-white">
                  Recent Transactions
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <button
                  className="text-[#9D8DFF] hover:text-[#8C6FE6] transition-colors text-sm font-medium"
                  onClick={() => navigate("/history")}
                >
                  View All
                </button>
              </div>
            </div>

            <div className="p-3 sm:p-6 pt-2 overflow-visible space-y-3 sm:space-y-4">
              {walletData.transactions && walletData.transactions.length > 0 ? (
                <>
                  {walletData.transactions
                    .slice(0, 5)
                    .map((transaction, index) => (
                      <div
                        key={index}
                        className="flex flex-col sm:flex-row sm:items-center justify-between p-3 sm:p-4 rounded-lg bg-[#2e2e2e] hover:bg-[#323234] transition-colors duration-200"
                      >
                        <div className="flex items-center gap-3 sm:gap-4 mb-2 sm:mb-0">
                          <div
                            className={`${
                              transaction.type === "received"
                                ? "bg-green-100/10"
                                : "bg-red-100/10"
                            } p-2 rounded-full flex-shrink-0`}
                          >
                            {transaction.type === "received" ? (
                              <ArrowDown className="w-5 h-5 text-green-600" />
                            ) : (
                              <ArrowUp className="w-5 h-5 text-red-600" />
                            )}
                          </div>
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <h3 className="font-medium text-[#FFFFFF]">
                                {transaction.type === "received"
                                  ? "Received"
                                  : "Sent"}{" "}
                                CRN
                              </h3>
                            </div>
                                                          <p className="text-xs sm:text-sm text-[#C4C4C7] truncate max-w-[180px] sm:max-w-full">
                                {transaction.type === "received"
                                  ? "From: "
                                  : "To: "}
                                {transaction.address}
                              </p>
                          </div>
                        </div>

                        <div className="flex items-center justify-between sm:justify-end gap-3 sm:gap-6 mt-1 sm:mt-0">
                          <div className="text-left sm:text-right">
                            <p
                              className={`font-medium ${
                                transaction.type === "received"
                                  ? "text-green-600"
                                  : "text-red-600"
                              }`}
                            >
                              {transaction.type === "received" ? "+" : "-"}
                              {transaction.amount.toFixed(8)} CRN
                            </p>
                            <p className="text-xs sm:text-sm text-[#B0B0B5]">
                              {formatTransactionDate(transaction.date)}
                            </p>
                          </div>

                          <div className="relative dropdown-menu ml-auto sm:ml-0">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleMenuToggle(`transaction-${index}`);
                              }}
                              className="p-2 hover:bg-[#3A3A3E] rounded-full transition-colors dropdown-trigger"
                            >
                              <MoreVertical className="w-5 h-5 text-[#C4C4C7]" />
                            </button>

                            {activeMenu === `transaction-${index}` && (
                              <div
                                className="absolute right-0 sm:right-0 top-full mt-2 w-48 rounded-lg shadow-lg py-1 z-50 border border-[#2E2E3E] transform transition-all duration-200 origin-top-right"
                                style={{ background: "#313131" }}
                              >
                                <button
                                  onClick={() =>
                                    handleAction("Download", transaction)
                                  }
                                  className="w-full px-4 py-2 text-left text-sm text-[#FFFFFF] hover:bg-[#3A3A3E] flex items-center gap-2 transition-colors"
                                >
                                  <Download className="w-4 h-4" />
                                  Download PDF
                                </button>
                                <button
                                  onClick={() =>
                                    handleAction("Copy", transaction)
                                  }
                                  className="w-full px-4 py-2 text-left text-sm text-[#FFFFFF] hover:bg-[#3A3A3E] flex items-center gap-2 transition-colors"
                                >
                                  <Copy className="w-4 h-4" />
                                  Copy Transaction ID
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                </>
              ) : (
                <div className="text-center py-8">
                  <p className="text-[#C4C4C7]">No transactions found</p>
                </div>
              )}
            </div>
          </motion.div>

          {/* User Ratings Card */}
          <motion.div className="order-6 col-span-full xl:col-span-4 bg-[#2b2b2b] rounded-2xl p-4 sm:p-6 transition-all duration-300">
            <div className="h-full flex flex-col">
              {/* رأس البطاقة */}
              <div className="flex justify-between items-center mb-6">
                <div className="flex items-center gap-2.5">
                  <div className="bg-yellow-400/10 p-2 rounded-lg mr-3">
                    <Star
                      className="w-5 h-5 text-yellow-400 fill-yellow-400"
                      strokeWidth={2.5}
                    />
                  </div>
                  <h4 className="text-lg font-bold text-white">User Ratings</h4>
                </div>
              </div>

              <div className="flex-1">
                {/* نظرة عامة على التقييم */}
                <div className="flex items-center gap-6 mb-6">
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
                    className={`relative flex-shrink-0 w-20 h-20 rounded-2xl flex items-center justify-center shadow-sm ${
                      walletData.ratings.average_rating > 3.7
                        ? "bg-gradient-to-br from-emerald-900/30 to-emerald-800/20"
                        : walletData.ratings.average_rating < 2
                        ? "bg-gradient-to-br from-rose-900/30 to-rose-800/20"
                        : "bg-gradient-to-br from-yellow-900/30 to-yellow-800/20"
                    }`}
                  >
                    <div className="text-center">
                      <div
                        className={`text-2xl font-bold ${
                          walletData.ratings.average_rating > 3.7
                            ? "text-emerald-400"
                            : walletData.ratings.average_rating < 2
                            ? "text-rose-400"
                            : "text-yellow-400"
                        }`}
                      >
                        {Number(walletData.ratings.average_rating).toFixed(1)}
                      </div>
                      <div
                        className={`text-xs font-medium ${
                          walletData.ratings.average_rating > 3.7
                            ? "text-emerald-600"
                            : walletData.ratings.average_rating < 2
                            ? "text-rose-600"
                            : "text-yellow-600"
                        }`}
                      >
                        out of 5
                      </div>
                    </div>
                  </motion.div>
                  <div className="space-y-2.5">
                    <div className="flex items-center mb-1">
                      <div className="flex">
                        <StarsRating
                          rating={Math.round(walletData.ratings.average_rating)}
                          size="lg"
                        />
                      </div>
                    </div>
                    <div className="flex items-center text-[#C4C4C7] text-xs bg-[#2e2e2e] px-2.5 py-1 rounded-lg w-fit">
                      <Users className="w-3.5 h-3.5 mr-1.5 text-[#B0B0B5]" />
                      <span className="font-medium">
                        {new Intl.NumberFormat("en-US").format(
                          walletData.ratings.total_ratings
                        )}{" "}
                        ratings
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* قسم التقييمات */}
              <div className="space-y-3 mb-6 bg-[#2e2e2e] rounded-xl p-4">
                <div className="text-xs font-medium text-[#C4C4C7] mb-3">
                  Rating Distribution
                </div>
                {walletData.ratings.distribution &&
                walletData.ratings.distribution.length > 0 ? (
                  walletData.ratings.distribution.map((item) => (
                    <motion.div
                      key={item.stars}
                      initial={{ width: 0, opacity: 0 }}
                      animate={{ width: "100%", opacity: 1 }}
                      transition={{ duration: 0.8, delay: 0.4 }}
                      className="space-y-1.5"
                    >
                      <div className="flex justify-between text-xs text-[#C4C4C7]">
                        <div className="flex items-center">
                          <StarsRating rating={item.stars} size="sm" />
                        </div>
                        <span className="font-medium">{item.percentage}%</span>
                      </div>
                      <div className="h-2 bg-[#45454A] rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${item.percentage}%` }}
                          transition={{ duration: 0.8, delay: 0.6 }}
                          className={`h-full rounded-full ${
                            item.stars > 3.7
                              ? "bg-emerald-600"
                              : item.stars < 2
                              ? "bg-rose-600"
                              : "bg-yellow-600"
                          }`}
                        />
                      </div>
                    </motion.div>
                  ))
                ) : (
                  <div className="text-center text-[#C4C4C7] py-2">
                    No ratings yet
                  </div>
                )}
              </div>

              {/* حالة عدم وجود تقييمات */}
              {(!walletData.ratings.featured_quote ||
                !walletData.ratings.featured_quote.text) && (
                <div className="mt-auto text-center py-4 bg-[#3A3A3E] rounded-xl">
                  <p className="text-[#C4C4C7] text-sm">No ratings yet</p>
                </div>
              )}

              {/* عرض أحدث تقييم وصل للمستخدم مع التعليق */}
              {walletData.ratings.featured_quote &&
                walletData.ratings.featured_quote.text && (
                  <div className="bg-gradient-to-br from-[#3A3A3E] to-[#2A2A2E]/50 rounded-xl p-4 relative mt-auto border border-[#45454A]/50">
                    <Quote className="w-6 h-6 text-yellow-600 absolute -top-2 -left-2 bg-[#2A2A2E] rounded-full p-1 shadow-sm" />
                    <p className="text-[#FFFFFF] text-sm italic mb-3 leading-relaxed">
                      "{walletData.ratings.featured_quote.text}"
                    </p>
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-medium text-yellow-600">
                        — {walletData.ratings.featured_quote.author || "Anonymous"}
                      </p>
                      <div className="flex justify-center gap-1">
                        <StarsRating
                          rating={walletData.ratings.featured_quote.stars}
                          size="md"
                        />
                      </div>
                    </div>
                  </div>
                )}
            </div>
          </motion.div>

          {/* Wallet Addresses */}
          <motion.div className="order-7 col-span-full xl:col-span-8 bg-[#2b2b2b] rounded-2xl shadow-sm relative">
            <div className="h-full">
              <Toaster position="top-right" />
              <div className="w-full h-full">
                {/* Header */}
                <div className="flex items-center gap-3 sm:gap-4 p-3 sm:p-6 pb-2">
                  <div className="relative">
                    <div className="w-8 sm:w-10 h-8 sm:h-10 bg-[#8B5CF6]/20 rounded-lg flex items-center justify-center">
                      <CreditCard
                        size={16}
                        className="sm:hidden text-[#9D8DFF]"
                      />
                      <CreditCard
                        size={20}
                        className="hidden sm:block text-[#9D8DFF]"
                      />
                    </div>
                  </div>
                  <div>
                    <h1 className="text-base sm:text-lg font-bold text-white">
                      Wallet Addresses
                    </h1>
                    <p className="text-[#C4C4C7] text-xs sm:text-sm">
                      Manage your CRN credentials
                    </p>
                  </div>
                </div>

                {/* Tab Navigation - Improve mobile spacing */}
                <div className="flex gap-2 sm:gap-4 mb-3 sm:mb-4 px-3 sm:px-6">
                  {["public", "private"].map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab as "public" | "private")}
                      className={`flex-1 py-3 px-4 rounded-xl transition-all duration-300 relative overflow-hidden group focus:outline-none ${
                        activeTab === tab
                          ? "bg-gradient-to-br from-[#8B5CF6]/20 to-[#8C6FE6]/10 border border-[#8B5CF6]/30"
                          : "hover:bg-[#3A3A3E]"
                      }`}
                      aria-label={`Switch to ${tab} address`}
                      role="tab"
                      aria-selected={activeTab === tab}
                      tabIndex={0}
                    >
                      <div className="flex items-center gap-3 justify-center">
                        {tab === "public" ? (
                          <Shield
                            size={16}
                            className={`transition-colors duration-300 ${
                              activeTab === tab
                                ? "text-[#9D8DFF]"
                                : "text-[#B0B0B5]"
                            }`}
                          />
                        ) : (
                          <Key
                            size={16}
                            className={`transition-colors duration-300 ${
                              activeTab === tab
                                ? "text-[#9D8DFF]"
                                : "text-[#B0B0B5]"
                            }`}
                          />
                        )}
                        <span
                          className={`font-medium text-sm ${
                            activeTab === tab
                              ? "text-[#FFFFFF]"
                              : "text-[#C4C4C7]"
                          }`}
                        >
                          {tab.charAt(0).toUpperCase() + tab.slice(1)} Address
                        </span>
                      </div>
                      {activeTab === tab && (
                        <motion.div
                          layoutId="activeTab"
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: -10 }}
                          transition={{ type: "spring", stiffness: 300 }}
                          className="absolute bottom-0 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-[#9D8DFF] to-transparent"
                        />
                      )}
                    </button>
                  ))}
                </div>

                {/* Address Card - Fix padding for mobile */}
                <div className="relative px-3 sm:px-6">
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="relative bg-[#3A3A3E] rounded-xl p-3 sm:p-4 overflow-hidden"
                  >
                    <div className="mb-3">
                      <div className="flex items-start gap-2 mb-1">
                        <h2 className="text-base font-semibold text-[#FFFFFF] flex items-center gap-2">
                          {activeTab.charAt(0).toUpperCase() +
                            activeTab.slice(1)}{" "}
                          Address
                        </h2>
                        <div className="relative group">
                          <Info
                            size={14}
                            className="text-[#9D8DFF]/80 cursor-help mt-1"
                          />
                          <div className="absolute hidden group-hover:block left-0 top-6 bg-[#2A2A2E] text-[#FFFFFF] text-xs p-2 rounded-lg w-48 shadow-xl z-10">
                            {activeTab === "public"
                              ? "Used internally by the network to verify and process transactions"
                              : "Share this address with others to receive funds in your wallet"}
                          </div>
                        </div>
                      </div>
                      <p className="text-[#C4C4C7] text-xs">
                        {activeTab === "public"
                          ? "Used internally by the network to verify and process transactions"
                          : "Share this address with others to receive funds in your wallet"}
                      </p>
                    </div>

                    <div className="relative">
                      <div className="relative rounded-lg p-2 sm:p-3 border border-[#45454A] bg-[#2A2A2E]">
                        <div className="flex items-center justify-between gap-2">
                          <AnimatePresence mode="wait">
                            <motion.div
                              key={
                                activeTab === "public"
                                  ? showPublic
                                    ? "public-visible"
                                    : "public-hidden"
                                  : showPrivate
                                  ? "private-visible"
                                  : "private-hidden"
                              }
                              initial={{ opacity: 0 }}
                              animate={{ opacity: 1 }}
                              exit={{ opacity: 0 }}
                              className="flex-1 font-mono text-[10px] sm:text-xs truncate text-[#FFFFFF]"
                              role="textbox"
                              aria-label={`${activeTab} address ${
                                activeTab === "public"
                                  ? showPublic
                                    ? "visible"
                                    : "hidden"
                                  : showPrivate
                                  ? "visible"
                                  : "hidden"
                              }`}
                            >
                              {activeTab === "public"
                                ? showPublic
                                  ? walletData.address.public
                                  : "•".repeat(walletData.address.public.length)
                                : showPrivate
                                ? walletData.address.private
                                : "•".repeat(walletData.address.private.length)}
                            </motion.div>
                          </AnimatePresence>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() =>
                                activeTab === "public"
                                  ? setShowPublic(!showPublic)
                                  : setShowPrivate(!showPrivate)
                              }
                              className="p-1.5 rounded-lg transition-colors text-gray-400 hover:text-blue-600 hover:bg-blue-50 focus:outline-none"
                              title={`${
                                activeTab === "public"
                                  ? showPublic
                                    ? "Hide public address"
                                    : "Show public address"
                                  : showPrivate
                                  ? "Hide private address"
                                  : "Show private address"
                              }`}
                              aria-label={`${
                                activeTab === "public"
                                  ? showPublic
                                    ? "Hide public address"
                                    : "Show public address"
                                  : showPrivate
                                  ? "Hide private address"
                                  : "Show private address"
                              }`}
                            >
                              {(
                                activeTab === "public"
                                  ? showPublic
                                  : showPrivate
                              ) ? (
                                <EyeOff size={16} />
                              ) : (
                                <Eye size={16} />
                              )}
                            </button>
                            <button
                              className={`p-1.5 rounded-lg transition-all duration-300 ${
                                copied ===
                                (activeTab === "public"
                                  ? "publicAddress"
                                  : "privateAddress")
                                  ? "bg-green-100 text-green-600"
                                  : "text-gray-400 hover:text-blue-600 hover:bg-blue-50"
                              } focus:outline-none`}
                              onClick={() =>
                                copyToClipboard(
                                  activeTab === "public"
                                    ? walletData.address.public
                                    : walletData.address.private,
                                  activeTab === "public"
                                    ? "publicAddress"
                                    : "privateAddress"
                                )
                              }
                              title={
                                copied ===
                                (activeTab === "public"
                                  ? "publicAddress"
                                  : "privateAddress")
                                  ? "Copied!"
                                  : "Copy to clipboard"
                              }
                              aria-label={`Copy ${activeTab} address to clipboard`}
                              aria-live="polite"
                            >
                              {copied ===
                              (activeTab === "public"
                                ? "publicAddress"
                                : "privateAddress") ? (
                                <CheckCircle size={16} />
                              ) : (
                                <Copy size={16} />
                              )}
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Wallet Info */}
          <motion.div className="order-8 col-span-full md:col-span-1 xl:col-span-4 bg-[#2b2b2b] rounded-2xl shadow-lg relative">
            <div className="relative bg-[#2b2b2b] rounded-xl shadow-lg shadow-black/5 p-3 sm:p-6 space-y-4 sm:space-y-6 h-full">
              {/* Header */}
              <div className="flex items-center">
                <div className="bg-[#8B5CF6]/20 p-1.5 sm:p-2 rounded-lg">
                  <Wallet className="w-4 h-4 sm:w-5 sm:h-5 text-[#9D8DFF]/80" />
                </div>
                <span className="ml-2 sm:ml-3 text-base sm:text-lg font-bold text-white">
                  Wallet Info
                </span>
              </div>

              <div className="space-y-3 sm:space-y-4">
                {/* Wallet ID */}
                <div className="flex items-center justify-between group relative">
                  <div className="flex items-center">
                    <div className="bg-[#8B5CF6]/20 p-1.5 sm:p-2 rounded-lg">
                      <Wallet className="w-4 h-4 sm:w-5 sm:h-5 text-[#9D8DFF]" />
                    </div>
                    <span className="ml-2 sm:ml-3 text-sm text-[#C4C4C7]">
                      Wallet ID
                    </span>
                  </div>
                  <div className="flex items-center">
                    <span className="text-xs sm:text-sm text-[#FFFFFF] font-medium truncate-mobile">
                      {walletData.walletId}
                    </span>
                    <button
                      onClick={() =>
                        copyToClipboard(walletData.walletId, "walletId")
                      }
                      className="mobile-tap-target ml-2 text-[#B0B0B5] hover:text-[#FFFFFF] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#9D8DFF] rounded-full transition-colors duration-200"
                      aria-label="Copy wallet ID"
                    >
                      {copied === "walletId" ? (
                        <Check className="w-4 h-4 text-green-500" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Created On */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="bg-[#8C6FE6]/20 p-1.5 sm:p-2 rounded-lg">
                      <Clock className="w-4 h-4 sm:w-5 sm:h-5 text-[#8C6FE6]" />
                    </div>
                    <span className="ml-2 sm:ml-3 text-sm text-[#C4C4C7]">
                      Created On
                    </span>
                  </div>
                  <span className="text-xs sm:text-sm text-[#FFFFFF] font-medium">
                    {walletData.createdAt}
                  </span>
                </div>

                {/* Verified User */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div
                      className={`p-1.5 sm:p-2 rounded-lg ${
                        walletData.verified ? "bg-[#8B5CF6]/20" : "bg-[#3A3A3E]"
                      }`}
                    >
                      <CheckCircle2
                        className={`w-4 h-4 sm:w-5 sm:h-5 ${
                          walletData.verified
                            ? "text-[#9D8DFF]"
                            : "text-[#B0B0B5]"
                        }`}
                      />
                    </div>
                    <span className="ml-2 sm:ml-3 text-sm text-[#C4C4C7]">
                      Verified User
                    </span>
                  </div>
                  {walletData.verified ? (
                    <Badge text="Verified" variant="green" />
                  ) : (
                    <Badge text="Not Verified" variant="gray" />
                  )}
                </div>

                {/* Premium */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div
                      className={`p-1.5 sm:p-2 rounded-lg ${
                        walletData.premium ? "bg-yellow-500/10" : "bg-[#3A3A3E]"
                      }`}
                    >
                      <Crown
                        className={`w-4 h-4 sm:w-5 sm:h-5 ${
                          walletData.premium
                            ? "text-yellow-500 animate-pulse"
                            : "text-[#B0B0B5]"
                        }`}
                      />
                    </div>
                    <span className="ml-2 sm:ml-3 text-sm text-[#C4C4C7]">
                      Premium
                    </span>
                  </div>
                  {walletData.premium === true ? (
                    <Badge text="Activated" variant="yellow" />
                  ) : (
                    <Badge text="Not Active" variant="gray" />
                  )}
                </div>

                {/* Badges */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="p-1.5 sm:p-2 rounded-lg bg-[#8C6FE6]/20">
                      <ActivitySquare className="w-4 h-4 sm:w-5 sm:h-5 text-[#8C6FE6]" />
                    </div>
                    <span className="ml-2 sm:ml-3 text-sm text-[#A1A1AA]">
                      Your Badges
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge
                      text={`${
                        Number(walletData.premium) +
                          Number(walletData.verified) +
                          Number(walletData.vip) || "0"
                      } Badges`}
                      variant={
                        Number(walletData.premium) +
                          Number(walletData.verified) +
                          Number(walletData.vip) >
                        0
                          ? "purple"
                          : "gray"
                      }
                    />
                  </div>
                </div>

                {/* Public Profile */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div
                      className={`p-1.5 sm:p-2 rounded-lg ${
                        walletData.publicVisible
                          ? "bg-green-500/10"
                          : "bg-[#2A2A2D]"
                      }`}
                    >
                      <Eye
                        className={`w-4 h-4 sm:w-5 sm:h-5 ${
                          walletData.publicVisible
                            ? "text-green-500"
                            : "text-[#8E8E93]"
                        }`}
                      />
                    </div>
                    <span className="ml-2 sm:ml-3 text-sm text-[#A1A1AA]">
                      Public Profile
                    </span>
                  </div>
                  {walletData.publicVisible ? (
                    <Badge text="Public" variant="green" />
                  ) : (
                    <Badge text="Private" variant="gray" />
                  )}
                </div>

                {/* VIP Status */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div
                      className={`p-1.5 sm:p-2 rounded-lg ${
                        walletData.vip ? "bg-[#8875FF]/20" : "bg-[#2A2A2D]"
                      }`}
                    >
                      {walletData.vip ? (
                        <div className="relative">
                          <svg 
                            className="w-4 h-4 sm:w-5 sm:h-5 relative z-10" 
                            viewBox="0 0 24 24" 
                            fill="none" 
                            xmlns="http://www.w3.org/2000/svg"
                          >
                            <path 
                              d="M12 3L22 12L12 21L2 12L12 3Z" 
                              fill="#8875FF" 
                              stroke="#8875FF" 
                              strokeWidth="1" 
                            />
                            <path 
                              d="M12 8L17 12L12 16L7 12L12 8Z" 
                              fill="#FFFFFF" 
                              fillOpacity="0.3"
                            />
                          </svg>
                        </div>
                      ) : (
                        <svg 
                          className="w-4 h-4 sm:w-5 sm:h-5" 
                          viewBox="0 0 24 24" 
                          fill="none" 
                          xmlns="http://www.w3.org/2000/svg"
                        >
                          <path 
                            d="M12 3L22 12L12 21L2 12L12 3Z" 
                            fill="#8E8E93" 
                            fillOpacity="0.4"
                            stroke="#8E8E93" 
                            strokeWidth="1" 
                          />
                          <path 
                            d="M12 8L17 12L12 16L7 12L12 8Z" 
                            fill="#8E8E93" 
                            fillOpacity="0.2"
                          />
                        </svg>
                      )}
                    </div>
                    <span className="ml-2 sm:ml-3 text-sm text-[#A1A1AA]">
                      VIP Status
                    </span>
                  </div>
                  {walletData.vip ? (
                    <Badge text="VIP Member" variant="purple" />
                  ) : (
                    <Badge text="Not VIP" variant="gray" />
                  )}
                </div>

                {/* Status */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div
                      className={`p-1.5 sm:p-2 rounded-lg ${
                        walletData.active && !walletData.locked
                          ? "bg-green-500/10"
                          : "bg-[#2A2A2D]"
                      }`}
                    >
                      <ActivitySquare
                        className={`w-4 h-4 sm:w-5 sm:h-5 ${
                          walletData.active && !walletData.locked
                            ? "text-green-500"
                            : "text-[#8E8E93]"
                        }`}
                      />
                    </div>
                    <span className="ml-2 sm:ml-3 text-sm text-[#A1A1AA]">
                      Status
                    </span>
                  </div>
                  <div className="flex items-center">
                    {walletData.locked ? (
                      <>
                        <div className="w-2 h-2 bg-orange-500 rounded-full mr-2 animate-pulse"></div>
                        <span className="text-xs sm:text-sm text-orange-500 font-medium">
                          Locked
                        </span>
                      </>
                    ) : !walletData.active ? (
                      <>
                        <div className="w-2 h-2 bg-red-500 rounded-full mr-2 animate-pulse"></div>
                        <span className="text-xs sm:text-sm text-red-500 font-medium">
                          Suspended
                        </span>
                      </>
                    ) : (
                      <>
                        <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
                        <span className="text-xs sm:text-sm text-green-500 font-medium">
                          Active
                        </span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Security Wallet Info */}
          <motion.div className="order-9 col-span-full md:col-span-1 xl:col-span-4 bg-[#2b2b2b] rounded-2xl shadow-lg relative">
            <div className="relative bg-[#2b2b2b] rounded-xl shadow-lg shadow-black/5 p-3 sm:p-6 space-y-3 sm:space-y-5 h-full">
              {/* Header */}
              <div className="flex items-center">
                <div className="bg-[#6C5DD3]/20 p-1.5 sm:p-2 rounded-lg">
                  <Lock className="w-4 h-4 sm:w-5 sm:h-5 text-[#7B61FF]/80" />
                </div>
                <span className="ml-2 sm:ml-3 text-base sm:text-lg font-bold text-white">
                  Security Wallet Info
                </span>
              </div>

              <div className="space-y-3 sm:space-y-4">
                {/* 2FA Authentication */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div
                      className={`p-1.5 sm:p-2 rounded-lg ${
                        walletData.security.twoFA
                          ? "bg-[#6C5DD3]/20"
                          : "bg-[#2A2A2D]"
                      }`}
                    >
                      <Shield
                        className={`w-4 h-4 sm:w-5 sm:h-5 ${
                          walletData.security.twoFA
                            ? "text-[#7B61FF]"
                            : "text-[#8E8E93]"
                        }`}
                      />
                    </div>
                    <span className="ml-2 sm:ml-3 text-sm text-[#A1A1AA]">
                      2FA Authentication
                    </span>
                  </div>
                  {walletData.security.twoFA ? (
                    <Badge text="Enabled" variant="green" />
                  ) : (
                    <Badge text="Disabled" variant="gray" />
                  )}
                </div>

                {/* Last Login */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="bg-emerald-500/10 p-1.5 sm:p-2 rounded-lg">
                      <Clock className="w-4 h-4 sm:w-5 sm:h-5 text-emerald-500" />
                    </div>
                    <span className="ml-2 sm:ml-3 text-sm text-[#A1A1AA]">
                      Last Login
                    </span>
                  </div>
                  <span className="text-xs sm:text-sm text-[#E5E5E5] font-medium">
                    {walletData.security.lastLogin
                      .split(".")[0]
                      .slice(0, -3)
                      .replace("T", "-")}
                  </span>
                </div>

                {/* Wallet Frozen */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="bg-[#6C5DD3]/20 p-1.5 sm:p-2 rounded-lg">
                      <Lock className="w-4 h-4 sm:w-5 sm:h-5 text-[#7B61FF]" />
                    </div>
                    <span className="ml-2 sm:ml-3 text-sm text-[#A1A1AA]">
                      Wallet Frozen
                    </span>
                  </div>
                  <Badge
                    text={walletData.security.walletFrozen ? "Yes" : "No"}
                    variant={walletData.security.walletFrozen ? "red" : "green"}
                  />
                </div>

                {/* Daily Transfer Limit */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="bg-[#8C6FE6]/20 p-1.5 sm:p-2 rounded-lg">
                      <ArrowRightLeft className="w-4 h-4 sm:w-5 sm:h-5 text-[#8C6FE6]" />
                    </div>
                    <span className="ml-2 sm:ml-3 text-sm text-[#A1A1AA]">
                      Daily Transfer Limit
                    </span>
                  </div>
                  <span className="text-xs sm:text-sm text-[#E5E5E5] font-medium">
                    {walletData.security.dailyTransferLimit?.toLocaleString() ||
                      "Unlimited"}{" "}
                    CRN
                  </span>
                </div>

                {/* Transfer Security Type */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="bg-[#8C6FE6]/20 p-1.5 sm:p-2 rounded-lg">
                      <Key className="w-4 h-4 sm:w-5 sm:h-5 text-[#8C6FE6]" />
                    </div>
                    <span className="ml-2 sm:ml-3 text-sm text-[#A1A1AA]">
                      Transfer Security
                    </span>
                  </div>
                  <div className="flex flex-wrap justify-end gap-1 sm:gap-2">
                    {walletData.security.transferAuth && (
                      <>
                        {walletData.security.transferAuth["2fa"] && (
                          <Badge text="2FA" variant="blue" />
                        )}
                        {walletData.security.transferAuth.password && (
                          <Badge text="Password" variant="purple" />
                        )}
                        {walletData.security.transferAuth.secret_word && (
                          <Badge text="Secret" variant="gray" />
                        )}
                      </>
                    )}
                  </div>
                </div>

                {/* Login Security Type */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="bg-[#6C5DD3]/20 p-1.5 sm:p-2 rounded-lg">
                      <LogIn className="w-4 h-4 sm:w-5 sm:h-5 text-[#7B61FF]" />
                    </div>
                    <span className="ml-2 sm:ml-3 text-sm text-[#A1A1AA]">
                      Login Security
                    </span>
                  </div>
                  <div className="flex flex-wrap justify-end gap-1 sm:gap-2">
                    {walletData.security.loginAuth && (
                      <>
                        {walletData.security.loginAuth["2fa"] && (
                          <Badge text="2FA" variant="blue" />
                        )}
                        {walletData.security.loginAuth.none && (
                          <Badge text="Basic" variant="gray" />
                        )}
                        {walletData.security.loginAuth.secret_word && (
                          <Badge text="Secret" variant="purple" />
                        )}
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>

        <style>{`
          @media (min-width: 1070px) {
            .grid-cols-1 {
              grid-template-columns: repeat(12, minmax(0, 1fr));
            }
            
            /* First Row */
            .order-1 { order: 1; grid-column: span 6 / span 6; } /* Total Balance */
            .order-2 { order: 2; grid-column: span 3 / span 3; } /* Total Transactions */
            .order-3 { order: 3; grid-column: span 3 / span 3; } /* Leaderboard Rank */
            
            /* Second Row */
            .order-4 { order: 4; grid-column: span 8 / span 8; } /* Growth Wallet */
            .order-6 { order: 5; grid-column: span 4 / span 4; } /* User Ratings */
            
            /* Third Row */
            .order-5 { order: 6; grid-column: span 8 / span 8; } /* Recent Transactions */
            .order-8 { order: 7; grid-column: span 4 / span 4; } /* Wallet Info */
            
            /* Fourth Row */
            .order-7 { order: 8; grid-column: span 8 / span 8; } /* Wallet Addresses */
            .order-9 { order: 9; grid-column: span 4 / span 4; } /* Security Wallet Info */
          }

          @media (min-width: 650px) and (max-width: 1069px) {
            .grid-cols-1 {
              grid-template-columns: repeat(12, minmax(0, 1fr));
            }
            .order-1 { order: 1; grid-column: span 12 / span 12; }
            .order-2 { order: 2; grid-column: span 6 / span 6; }
            .order-3 { order: 3; grid-column: span 6 / span 6; }
            .order-4 { order: 4; grid-column: span 12 / span 12; }
            .order-5 { order: 5; grid-column: span 12 / span 12; }
            .order-8 { order: 6; grid-column: span 12 / span 12; }
            .order-9 { order: 7; grid-column: span 12 / span 12; }
            .order-6 { order: 8; grid-column: span 12 / span 12; }
            .order-7 { order: 9; grid-column: span 12 / span 12; }
          }

          @media (max-width: 649px) {
            .order-1 { order: 1; grid-column: span 12 / span 12; }
            .order-2 { order: 2; grid-column: span 12 / span 12; }
            .order-3 { order: 3; grid-column: span 12 / span 12; }
            .order-4 { order: 4; grid-column: span 12 / span 12; }
            .order-5 { order: 5; grid-column: span 12 / span 12; }
            .order-8 { order: 6; grid-column: span 12 / span 12; }
            .order-9 { order: 7; grid-column: span 12 / span 12; }
            .order-6 { order: 8; grid-column: span 12 / span 12; }
            .order-7 { order: 9; grid-column: span 12 / span 12; }
          }
        `}</style>
      </div>
      {/* نافذة التقييم */}
      {currentRatingTransaction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <RatingModal
            isOpen={showRatingModal}
            onClose={() => setShowRatingModal(false)}
            recipientId={currentRatingTransaction.recipientId || ""}
            recipientUsername={currentRatingTransaction.address || ""}
            onRatingSubmitted={handleRatingSubmitted}
          />
        </div>
      )}

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
      `}</style>
    </div>
  );
};

export default memo(Overview);

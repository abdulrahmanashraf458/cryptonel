import React, {
  useState,
  useEffect,
  useMemo,
  useCallback,
  useRef,
} from "react";
import {
  Shield,
  Fingerprint,
  Eye,
  EyeOff,
  Check,
  Smartphone,
  AlertTriangle,
  CheckCircle,
  X,
  Copy,
  Key,
  Lock,
  KeySquare,
  Info,
  DollarSign,
  SnowflakeIcon,
  ChevronRight,
  UserX2,
  Clock,
  ShieldCheck,
  MapPin,
  Plus,
  Crown,
  LogIn,
  Globe,
} from "lucide-react";
import clsx from "clsx";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import DevicesList from "../../components/DevicesList";
import axios from "axios";

// Format 24-hour time to 12-hour format with AM/PM
const formatTo12Hour = (time24: string): string => {
  try {
    const [hourStr, minuteStr] = time24.split(':');
    let hour = parseInt(hourStr, 10);
    const minute = parseInt(minuteStr, 10);
    const period = hour >= 12 ? 'PM' : 'AM';
    hour = hour % 12;
    hour = hour ? hour : 12; // Convert 0 to 12
    return `${hour}:${minute.toString().padStart(2, '0')} ${period}`;
  } catch (e) {
    return time24;
  }
};

// Get a list of common timezones for the dropdown
const getCommonTimezones = (): string[] => {
  return [
    'UTC',
    'America/New_York',     // Eastern Time
    'America/Chicago',      // Central Time
    'America/Denver',       // Mountain Time
    'America/Los_Angeles',  // Pacific Time
    'Europe/London',        // GMT/BST
    'Europe/Berlin',        // Central European Time
    'Europe/Moscow',        // Moscow Time
    'Africa/Cairo',         // Eastern European Time
    'Asia/Dubai',           // Gulf Time
    'Asia/Kolkata',         // Indian Time
    'Asia/Bangkok',         // Indochina Time
    'Asia/Shanghai',        // China Time
    'Asia/Tokyo',           // Japan Time
    'Australia/Sydney',     // Eastern Australia Time
    'Pacific/Auckland',     // New Zealand Time
    'Africa/Johannesburg',  // South Africa Time
    'America/Sao_Paulo',    // Brasilia Time
    'Pacific/Honolulu',     // Hawaii Time
    'Atlantic/Reykjavik',   // Greenwich Mean Time
  ];
};

// إضافة أسلوب CSS عام لإخفاء شريط التمرير ومنع التمرير الأفقي
const hideScrollbarStyle = document.createElement("style");
hideScrollbarStyle.textContent = `
  .hide-scrollbar::-webkit-scrollbar {
    display: none !important;
  }
  .hide-scrollbar {
    -ms-overflow-style: none !important;
    scrollbar-width: none !important;
  }
  
  /* منع التمرير الأفقي عالميًا */
  body {
    overflow-x: hidden !important;
    width: 100% !important;
    box-sizing: border-box !important;
  }
  
  /* تعريف breakpoint خاص للشاشات الصغيرة جدًا */
  @media (min-width: 351px) and (max-width: 639px) {
    .xs-w-48 {
      width: 12rem !important;
    }
    .xs-h-48 {
      height: 12rem !important;
    }
  }
  
  /* تحسينات للشاشات الصغيرة جدًا */
  @media (max-width: 350px) {
    /* تعديل حجم الأيقونات */
    svg {
      width: 16px !important;
      height: 16px !important;
    }
    
    /* تقليل حجم وتباعد العناصر أكثر */
    .text-3xl {
      font-size: 1.5rem !important;
    }
    
    .text-xl {
      font-size: 1.1rem !important;
    }
    
    .text-lg {
      font-size: 1rem !important;
    }
    
    .text-base {
      font-size: 0.875rem !important;
    }
    
    .text-sm {
      font-size: 0.75rem !important;
    }
    
    /* تعديل التباعد والحشو */
    .p-4, .px-4, .py-4 {
      padding: 0.5rem !important;
    }
    
    .gap-3, .gap-4 {
      gap: 0.5rem !important;
    }
    
    .mt-4, .mt-5 {
      margin-top: 0.5rem !important;
    }
    
    /* تعديل أيقونات الميزات */
    .w-10, .h-10 {
      width: 2rem !important;
      height: 2rem !important;
    }
  }
  
  /* تحسينات لعرض الجوال */
  @media (max-width: 600px) {
    html, body {
      width: 100% !important;
      overflow-x: hidden !important;
    }
    
    .px-4 {
      padding-left: 0.75rem !important;
      padding-right: 0.75rem !important;
    }
    
    .security-card {
      border-radius: 1rem !important;
    }
    
    /* تحسين عرض الأيقونات والنصوص */
    .w-12, .h-12 {
      width: 2.5rem !important;
      height: 2.5rem !important;
    }
    
    /* تحسين عرض البطاقات */
    .rounded-xl {
      border-radius: 0.75rem !important;
    }
  }

  /* ضمان التحكم في البطاقات على الشاشات الصغيرة */
  @media (max-width: 440px) {
    .security-card {
      min-width: 100% !important;
      width: 100% !important;
      max-width: 100% !important;
      margin-left: 0 !important;
      margin-right: 0 !important;
    }
    
    /* تحسين حجم العناصر على الجوال */
    .text-3xl {
      font-size: 1.75rem !important;
    }
    
    /* تعديل الهوامش والتباعد على الجوال */
    .p-4 {
      padding: 0.75rem !important;
    }
    
    .p-5 {
      padding: 1rem !important;
    }
    
    .gap-4 {
      gap: 0.75rem !important;
    }
    
    /* توسيع العناصر لتملأ المساحة المتاحة */
    .w-full {
      width: 100% !important;
    }

    /* تحسين المسافات بين العناصر */
    .mb-6 {
      margin-bottom: 1rem !important;
    }
    
    .space-y-3 > * + * {
      margin-top: 0.5rem !important;
    }
  }
  
  /* نقطة كسر مخصصة عند 900 بكسل */
  @media (min-width: 901px) {
    .layout-cols-900 {
      flex-direction: row !important;
      justify-content: space-between !important;
    }
    .layout-col-900 {
      width: 48% !important;
      max-width: 48% !important;
    }
  }
  
  @media (max-width: 900px) {
    .layout-cols-900 {
      flex-direction: column !important;
    }
    .layout-col-900 {
      width: 100% !important;
    }
  }

  /* نقطة كسر مخصصة عند 1024 بكسل */
  @media (min-width: 1025px) {
    .layout-cols-1024 {
      flex-direction: row !important;
      justify-content: space-between !important;
    }
    .layout-col-1024 {
      width: 48% !important;
      max-width: 48% !important;
    }
  }
  
  @media (max-width: 1024px) {
    .layout-cols-1024 {
      flex-direction: column !important;
    }
    .layout-col-1024 {
      width: 100% !important;
    }
  }
`;
document.head.appendChild(hideScrollbarStyle);

// استبدال الأيقونة الافتراضية لـ Leaflet
// إعادة تعريف الأيقونة لافتراضية لـ Leaflet لتفادي المشاكل المعروفة مع مسار الصور
// @ts-expect-error - Leaflet's Icon.Default uses _getIconUrl which is not in TypeScript definitions
delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

// Add cache utility hook at the top level
const useApiCache = (key: string, ttlMinutes = 5) => {
  // Cache hit counter for debugging
  const cacheHits = useRef(0);
  const cacheMisses = useRef(0);
  const lastFetchTime = useRef(0);
  
  // Fetch data with caching
  const fetchWithCache = useCallback(
    async (url: string, options: RequestInit = {}) => {
      try {
        // Check if we have cached data
        const cachedItem = localStorage.getItem(`cache_${key}`);
        const now = new Date().getTime();

        if (cachedItem) {
          try {
            const { data, timestamp } = JSON.parse(cachedItem);
            const expiryTime = timestamp + ttlMinutes * 60 * 1000;

            // If data is still valid, return it
            if (now < expiryTime) {
              cacheHits.current++;
              console.log(`[Cache] Using cached data for ${key} (Hit #${cacheHits.current})`);
              return data;
            }

            // Otherwise clear expired cache
            localStorage.removeItem(`cache_${key}`);
          } catch (e) {
            console.error(`Cache parse error for ${key}:`, e);
            localStorage.removeItem(`cache_${key}`);
          }
        }
        
        // Throttle network requests to prevent excessive API calls
        // Ensure at least 2 seconds between requests to the same endpoint
        const timeSinceLastFetch = now - lastFetchTime.current;
        if (lastFetchTime.current > 0 && timeSinceLastFetch < 2000) {
          console.log(`[Cache] Throttling request to ${url}, last fetch was ${timeSinceLastFetch}ms ago`);
          
          // If we have stale cache data, use it during throttling
          if (cachedItem) {
            try {
              const { data } = JSON.parse(cachedItem);
              console.log(`[Cache] Using stale data during throttle for ${key}`);
              return data;
            } catch (e) {
              // Continue with fetch if parsing fails
            }
          }
          
          // Wait before proceeding with fetch
          await new Promise(resolve => setTimeout(resolve, 2000 - timeSinceLastFetch));
        }
        
        // Track fetch time
        lastFetchTime.current = new Date().getTime();
        cacheMisses.current++;
        console.log(`[Cache] Fetching fresh data for ${key} (Miss #${cacheMisses.current})`);

        // Fetch fresh data
        const response = await fetch(url, options);

        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();

        // Cache the result
        localStorage.setItem(
          `cache_${key}`,
          JSON.stringify({
            data,
            timestamp: new Date().getTime(),
          })
        );

        return data;
      } catch (error) {
        console.error(`Error in cached fetch for ${key}:`, error);
        throw error;
      }
    },
    [key, ttlMinutes]
  );

  // Clear cache function
  const clearCache = useCallback(() => {
    localStorage.removeItem(`cache_${key}`);
    console.log(`[Cache] Cleared cache for ${key}`);
  }, [key]);
  
  // Force refresh function - clear cache and fetch immediately
  const forceRefresh = useCallback(async (url: string, options: RequestInit = {}) => {
    clearCache();
    return fetchWithCache(url, options);
  }, [clearCache, fetchWithCache]);

  return { fetchWithCache, clearCache, forceRefresh };
};

// بعد تعريفات الدوال المساعدة، أضف هذا المكون للدائرة التقدمية
const SecurityScoreCircle = ({ score }: { score: number }) => {
  // حساب لون ومستوى الأمان بناءً على النتيجة
  const getSecurityLevel = (score: number) => {
    if (score < 30)
      return { level: "Weak", color: "#FF6B6B", textColor: "text-red-500" };
    if (score < 50)
      return { level: "Fair", color: "#FFDE8C", textColor: "text-yellow-500" };
    if (score < 75)
      return { level: "Good", color: "#06D6A0", textColor: "text-green-500" };
    return { level: "Strong", color: "#118AB2", textColor: "text-blue-600" };
  };

  const { level, color } = getSecurityLevel(score);

  // حساب محيط الدائرة
  const radius = 85;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="relative flex items-center justify-center mx-auto my-3 sm:my-6 w-36 h-36 xs-w-48 xs-h-48 sm:w-64 sm:h-64">
      {/* الدائرة لخلفية */}
      <svg className="absolute w-full h-full" viewBox="0 0 200 200">
        <circle
          cx="100"
          cy="100"
          r={radius}
          fill="#1E1E1E"
          stroke="#333333"
          strokeWidth="15"
        />
      </svg>

      {/* الدائرة التقدمية */}
      <svg
        className="absolute w-full h-full -rotate-90 transform"
        viewBox="0 0 200 200"
      >
        <circle
          cx="100"
          cy="100"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="15"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
        />
      </svg>

      {/* المحتوى الداخلي */}
      <div className="z-10 text-center flex flex-col items-center">
        <span
          className="text-3xl sm:text-4xl md:text-6xl font-bold"
          style={{ color }}
        >
          {score}%
        </span>
        <div className="mt-1 sm:mt-2 flex items-center">
          <span
            className="text-base sm:text-lg md:text-xl font-medium"
            style={{ color }}
          >
            {level}
          </span>
          <span className="ml-2 bg-[#2A2A2A] rounded-full p-1">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-4 w-4 text-gray-400"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clipRule="evenodd"
              />
            </svg>
          </span>
        </div>
      </div>
    </div>
  );
};

// إضافة وظائف للتحقق من قوة كلمة المرور
// أضف هذه الوظيفة قبل دالة Security الرئيسية
const checkPasswordStrength = (password: string) => {
  if (!password) return { isValid: false, message: null, score: 0 };

  const hasMinLength = password.length >= 8;
  const hasUpperCase = /[A-Z]/.test(password);
  const hasSpecialChar = /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password);
  const hasNumber = /[0-9]/.test(password);

  // التحقق من صلاحية كلمة المرور حسب جميع الشروط
  const isValid = hasMinLength && hasUpperCase && hasSpecialChar && hasNumber;

  // رسالة خطأ مناسبة
  let message = null;
  if (!hasMinLength) {
    message = "Password must be at least 8 characters";
  } else if (!hasUpperCase) {
    message = "Password must contain at least one uppercase letter";
  } else if (!hasSpecialChar) {
    message = "Password must contain at least one special character";
  } else if (!hasNumber) {
    message = "Password must contain at least one number";
  }

  // حساب درجة قوة كلمة المرور
  let score = 0;
  if (hasMinLength) score += 1;
  if (hasUpperCase) score += 1;
  if (hasSpecialChar) score += 1;
  if (hasNumber) score += 1;
  if (password.length >= 12) score += 1;

  // درجة القوة من 5
  const scorePercentage = (score / 5) * 100;

  return { isValid, message, score, scorePercentage };
};

const Security = () => {
  // CSRF protection warning
  React.useEffect(() => {
    console.warn("⚠️ WARNING: CSRF protection is temporarily disabled for debugging purposes. Re-enable it after fixing the issues!");
  }, []);

  // States for interactive elements
  const [is2FAEnabled, setIs2FAEnabled] = useState(false);
  const [isWalletFrozen, setIsWalletFrozen] = useState(false);
  const [isTransferPasswordEnabled, setIsTransferPasswordEnabled] =
    useState(false);
  const [isDailyLimitEnabled, setIsDailyLimitEnabled] = useState(false);
  const [dailyLimit, setDailyLimit] = useState(100);
  
  // Add new state for security alerts dialog
  const [showSecurityAlertsDialog, setShowSecurityAlertsDialog] = useState(false);
  // Add state for devices dialog
  const [showDevicesDialog, setShowDevicesDialog] = useState(false);
  // Load acknowledged alerts from localStorage for persistence between sessions
  const [acknowledgedAlerts, setAcknowledgedAlerts] = useState<string[]>(() => {
    const saved = localStorage.getItem('acknowledgedSecurityAlerts');
    return saved ? JSON.parse(saved) : [];
  });
  // إضافة متغيرات الحالة لميزة Time-based Access
  const [isTimeBasedAccessEnabled, setIsTimeBasedAccessEnabled] =
    useState(false);
  const [timeRange, setTimeRange] = useState({
    startTime: "09:00",
    endTime: "17:00"
  });
  const [selectedTimezone, setSelectedTimezone] = useState(Intl.DateTimeFormat().resolvedOptions().timeZone);
  const [showTimeBasedAccessDialog, setShowTimeBasedAccessDialog] =
    useState(false);
  // Auto Sign-In feature states
  const [isAutoSignInEnabled, setIsAutoSignInEnabled] = useState(false);
  const [showAutoSignInDialog, setShowAutoSignInDialog] = useState(false);
  const [autoSignInDuration, setAutoSignInDuration] = useState(20); // Days to keep session active, fixed at 20 days
  // GeoLock feature states
  const [isGeoLockEnabled, setIsGeoLockEnabled] = useState(false);
  const [geoLockLocation, setGeoLockLocation] = useState("");
  const [geoLockCountry, setGeoLockCountry] = useState("");
  const [geoLockCoordinates, setGeoLockCoordinates] = useState({
    lat: 0,
    lng: 0,
  });
  const [mapZoom, setMapZoom] = useState(12);
  const [showGeoLockDialog, setShowGeoLockDialog] = useState(false);
  const [allowedCountries, setAllowedCountries] = useState<Array<{
    country_code: string;
    country_name: string;
    coordinates?: {
      lat: number;
      lng: number;
    };
  }>>([]);

  // IP Whitelist feature states
  const [isIpWhitelistEnabled, setIsIpWhitelistEnabled] = useState(false);
  const [showIpWhitelistDialog, setShowIpWhitelistDialog] = useState(false);
  const [ipWhitelist, setIpWhitelist] = useState<string[]>([]);
  const [newIpAddress, setNewIpAddress] = useState("");
  const [animateSection, setAnimateSection] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  
  // Country detection results for Geo-Lock
  const [scanResults, setScanResults] = useState<any>(null);

  // 2FA specific states
  const [show2FASetup, setShow2FASetup] = useState(false);
  const [twoFAStep, setTwoFAStep] = useState(1); // 1: choose method, 2: setup, 3: verify, 4: disable verification selection, 5: disable verification
  const [twoFACode, setTwoFACode] = useState("");
  const [twoFAVerified, setTwoFAVerified] = useState(false); // متغير للتحقق من التحقق بخطوتين
  const [showBackupCodes, setShowBackupCodes] = useState(false);
  const [copiedToClipboard, setCopiedToClipboard] = useState(false);
  const [disableVerificationMethod, setDisableVerificationMethod] =
    useState("app"); // 'app' or 'backup'
  const [backupCodeInput, setBackupCodeInput] = useState("");
  const [backupCodes, setBackupCodes] = useState<string[]>([]);

  // تم إزالة متغيرات حالة نافذة النسخ الاحتياطي

  // Added dialog states for security features
  const [showTransferPasswordDialog, setShowTransferPasswordDialog] =
    useState(false);
  const [showDailyLimitDialog, setShowDailyLimitDialog] = useState(false);
  const [showWalletFrozenDialog, setShowWalletFrozenDialog] = useState(false);
  const [isDisablingFeature, setIsDisablingFeature] = useState(false);
  const [walletPassword, setWalletPassword] = useState("");
  const [transferPassword, setTransferPassword] = useState("");
  const [confirmTransferPassword, setConfirmTransferPassword] = useState("");
  const [showTransferPasswordInput, setShowTransferPasswordInput] =
    useState(false);
  const [mnemonicPhrase, setMnemonicPhrase] = useState("");
  const [showFinalConfirmation, setShowFinalConfirmation] = useState(false);

  // Transfer Authentication dropdown states
  const [isTransferAuthDropdownOpen, setIsTransferAuthDropdownOpen] =
    useState<boolean>(false);
  const [tempTransferAuthMethod, setTempTransferAuthMethod] =
    useState<string>("secret_word");
  const [transferAuthMethod, setTransferAuthMethod] =
    useState<string>("secret_word");

  // Login Authentication dropdown states
  const [isLoginAuthDropdownOpen, setIsLoginAuthDropdownOpen] =
    useState<boolean>(false);
  const [tempLoginAuthMethod, setTempLoginAuthMethod] =
    useState<string>("none");
  const [loginAuthMethod, setLoginAuthMethod] = useState<string>("none");

  // Add these state variables to the Security component
  const [showAlert, setShowAlert] = useState(false);
  const [alertMessage, setAlertMessage] = useState("");
  const [alertType, setAlertType] = useState<"success" | "error">("success");

  // Add state for QR code and secret
  const [twoFAQRCode, setTwoFAQRCode] = useState("");
  const [twoFASecret, setTwoFASecret] = useState("");

  // Add a state to track when the copy action succeeds
  const [copiedSecret, setCopiedSecret] = useState(false);

  // Use cache hook for security settings (10 minute TTL)
  const {
    fetchWithCache: fetchCachedSettings,
    clearCache: clearSettingsCache,
  } = useApiCache("security_settings", 10);

  // State for loading and error
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  // Add state for premium status check
  const [hasPremiumCheck, setHasPremiumCheck] = useState<boolean>(false);
  
  // Check premium status on component load
  const checkPremiumStatus = async () => {
    try {
      // Check if we already validated premium status recently
      const cachedPremiumStatus = sessionStorage.getItem('premium_status');
      if (cachedPremiumStatus) {
        const premiumData = JSON.parse(cachedPremiumStatus);
        const lastChecked = new Date(premiumData.lastChecked);
        const now = new Date();
        // If we checked in the last 5 minutes, use cached data
        if ((now.getTime() - lastChecked.getTime()) < 5 * 60 * 1000) {
          console.log("Using cached premium status:", premiumData.isPremium);
          // Update wallet data with the cached premium status
          setWalletData(prevData => {
            if (!prevData) return prevData;
            return {
              ...prevData,
              premium: premiumData.isPremium
            };
          });
          setHasPremiumCheck(true);
          return;
        }
      }
      
      // Otherwise, fetch fresh premium status
      const response = await axios.get('/api/premium/check');
      
      if (response.data.success) {
        // Store premium status in session storage
        sessionStorage.setItem('premium_status', JSON.stringify({
          isPremium: response.data.premium,
          membershipType: response.data.membership,
          lastChecked: new Date().toISOString()
        }));
        
        console.log("Premium status checked:", response.data.premium);
        
        // Update wallet data with the premium status
        setWalletData(prevData => {
          if (!prevData) return prevData;
          return {
            ...prevData,
            premium: response.data.premium
          };
        });
        
        // If settings were reset due to premium status change, show notification
        if (response.data.settings_reset) {
          console.log("Premium settings were reset due to status change");
          // Show notification about settings reset
          showCustomAlert("Some premium features have been disabled because your premium status has changed.", "error");
        }
        
        setHasPremiumCheck(true);
      }
    } catch (error) {
      console.error("Error checking premium status:", error);
    }
  };
  
  // Wallet and security data
  const [walletData, setWalletData] = useState<{
    balance: string;
    premium: boolean;
    security: {
      lastLogin: string;
      deviceInfo: string;
      lastLoginIp: string;
      lastLoginLocation: string;
      lastUpdate: string;
      updateType: string;
      activeSessions: number;
      alerts: number;
      securityFeatures: string[];
    };
  } | null>(null);

  // Function to fetch wallet data from backend
  const fetchWalletData = useCallback(async () => {
    try {
      // Fetch regular wallet data
      const response = await fetch("/api/overview");
      if (!response.ok) {
        throw new Error("Failed to fetch wallet data");
      }
      const data = await response.json();
      
      // Fetch security settings for most up-to-date security info
      try {
        const securityResponse = await fetch("/api/security/settings");
        if (securityResponse.ok) {
          const securityData = await securityResponse.json();
          console.log("Direct security settings loaded:", securityData);
          
          // Preserve the full security information including security updates
          data.security = {
            ...data.security,
            deviceInfo: securityData.deviceInfo || data.security?.deviceInfo,
            lastLogin: securityData.lastLogin || data.security?.lastLogin,
            lastLoginIp: securityData.lastLoginIp || data.security?.lastLoginIp,
            lastLoginLocation: securityData.lastLoginLocation || data.security?.lastLoginLocation,
            lastUpdate: securityData.lastUpdate || data.security?.lastUpdate,
            updateType: securityData.updateType || data.security?.updateType,
            activeSessions: securityData.activeSessions || data.security?.activeSessions,
            alerts: securityData.alerts || data.security?.alerts
          };
        }
      } catch (securityError) {
        console.error("Error fetching security data:", securityError);
      }
      
      setWalletData(data);
    } catch (error) {
      console.error("Error fetching wallet data:", error);
    }
  }, []);

  // Call only clearSettingsCache, let fetchSecuritySettings handle all data loading
  useEffect(() => {
    // Clear any cached security settings to ensure fresh data
    clearSettingsCache();
  }, [clearSettingsCache]);

  // Format date for better display
  const formatDateTime = (dateString: string) => {
    if (!dateString) return "Not available";

    try {
      const date = new Date(dateString);
      return date.toLocaleString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch (e) {
      console.error("Error formatting date:", e);
      return dateString;
    }
  };

  // Animation on mount
  useEffect(() => {
    setAnimateSection(true);
  }, []);

  // Updated useEffect to use cached fetch
  useEffect(() => {
    // Initial animation on mount
    setAnimateSection(true);
    
    // Check premium status on component mount
    checkPremiumStatus();

    // Fetch all data (security + overview) with one operation
    const fetchAllSecurityData = async () => {
      try {
        // Always get fresh data on initial load and after toggling security settings
        // This ensures we have the latest settings from the database
        console.log("Fetching fresh security settings");
        
        // Check premium status to ensure we have the latest premium state
        await checkPremiumStatus();
        const data = await fetch("/api/security/settings").then(res => res.json());
        
        // Set basic security flags
        setIsTransferPasswordEnabled(data.transferPasswordEnabled || false);
        
        // Set daily limit flag based on whether wallet_limit is not null
        const hasLimitEnabled = data.dailyLimitEnabled || false;
        setIsDailyLimitEnabled(hasLimitEnabled);
        
        // Set the daily limit value if it exists
        if (hasLimitEnabled && data.dailyLimit) {
          setDailyLimit(data.dailyLimit);
        }
        
        setIs2FAEnabled(data.twoFAEnabled || false);
        setIsWalletFrozen(data.walletFrozen || false);
        
        // Log daily limit settings for debugging
        console.log("Daily limit settings from API:", {
          enabled: data.dailyLimitEnabled,
          limit: data.dailyLimit
        });
        
        // Calculate security alerts based on inactive premium features
        let securityFeatures = [];
        if (data.premium) {
          if (!data.timeBasedAccessEnabled) securityFeatures.push("Time-Based Access");
          if (!data.geoLockEnabled) securityFeatures.push("Geo-Lock");
          if (!data.ipWhitelistEnabled) securityFeatures.push("IP Whitelist");
        }
        
        // Filter out acknowledged alerts
        const filteredFeatures = securityFeatures.filter(
          feature => !acknowledgedAlerts.includes(feature)
        );
        
        // Update wallet data with consolidated information
        setWalletData({
          balance: data.balance || "0.00",
          premium: data.premium || false,
          security: {
            lastLogin: data.lastLogin || "No recent login",
            deviceInfo: data.deviceInfo || "Unknown Device",
            lastLoginIp: data.lastLoginIp || "",
            lastLoginLocation: data.lastLoginLocation || "",
            lastUpdate: data.lastUpdate || "",
            updateType: data.updateType || "",
            activeSessions: data.activeSessions || 1,
            alerts: filteredFeatures.length,
            securityFeatures: filteredFeatures
          }
        });

        // Login preferences
        setLoginAuthMethod(
          data.login2FAEnabled
            ? "2fa"
            : data.loginSecretWordEnabled
            ? "secret_word"
            : "none"
        );

        // Transfer auth preferences
        setTransferAuthMethod(
          data.secretWordEnabled ? "secret_word" : "password"
        );
        
        // Time-based access settings
        setIsTimeBasedAccessEnabled(data.timeBasedAccessEnabled || false);
        if (data.timeBasedAccessSettings) {
          setTimeRange({
            startTime: data.timeBasedAccessSettings.start_time || "09:00",
            endTime: data.timeBasedAccessSettings.end_time || "17:00"
          });
          setSelectedTimezone(data.timeBasedAccessSettings.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone);
        }
        
        // Set geo-lock settings
        setIsGeoLockEnabled(data.geoLockEnabled || false);
        if (data.geoLockSettings) {
          loadAllowedCountries(data.geoLockSettings);
          if (data.geoLockSettings.coordinates) {
            setGeoLockCoordinates(data.geoLockSettings.coordinates);
          }
        }
        
        // Set IP whitelist settings
        setIsIpWhitelistEnabled(data.ipWhitelistEnabled || false);
        if (data.ipWhitelistSettings && Array.isArray(data.ipWhitelistSettings.ips)) {
          setIpWhitelist(data.ipWhitelistSettings.ips);
          
          // Load IP details if available
          if (Array.isArray(data.ipWhitelistSettings.ip_details)) {
            setIpDetailsList(data.ipWhitelistSettings.ip_details);
          } else {
            // Create basic details from the IPs
            const basicDetails = data.ipWhitelistSettings.ips.map((ip: string) => ({
              ip_address: ip,
              country: "",
              region: "",
              city: "",
              location: "",
              timezone: "",
              provider: ""
            }));
            setIpDetailsList(basicDetails);
          }
        }
        
        // Auto Sign-In
        setIsAutoSignInEnabled(data.autoSignInEnabled || false);
        setAutoSignInDuration(data.autoSignInDuration || 20);
      } catch (error) {
        console.error("Error loading security data:", error);
      }
    };

    fetchAllSecurityData();
  }, [fetchCachedSettings, clearSettingsCache, acknowledgedAlerts]);

  // Toggle handler with animation - update to clear cache when toggling features
  const handleToggle = (
    // استخدام _ لتجاهل المعامل غير المستخدم
    _: React.Dispatch<React.SetStateAction<boolean>>,
    featureId: string
  ) => {
    return () => {
      // Check if this is a premium feature and user is not premium
      const feature = securityFeatures.find(f => f.id === featureId);
      if (feature?.isPremium && !walletData?.premium) {
        // Show premium required alert and return
        showCustomAlert("This feature requires a premium subscription.", "error");
        return; // Do nothing if premium feature and user is not premium
      }
      
      // For premium features, double-check premium status before enabling
      if (feature?.isPremium) {
        // Verify current premium status first
        checkPremiumStatus().then(() => {
          // After premium check, verify again if user is still premium
          if (!walletData?.premium) {
            showCustomAlert("Your premium subscription could not be verified.", "error");
            return;
          }
        }).catch(err => {
          console.error("Error checking premium status:", err);
          showCustomAlert("Could not verify premium status.", "error");
          return;
        });
      }

      const isCurrentlyEnabled =
        featureId === "transferPassword"
          ? isTransferPasswordEnabled
          : featureId === "dailyLimit"
          ? isDailyLimitEnabled
          : featureId === "frozen"
          ? isWalletFrozen
          : featureId === "2fa"
          ? is2FAEnabled
          : featureId === "timeBasedAccess"
          ? isTimeBasedAccessEnabled
          : featureId === "geoLock"
          ? isGeoLockEnabled
          : featureId === "autoSignIn"
          ? isAutoSignInEnabled
          : false;

      if (!isCurrentlyEnabled) {
        // Enable flow
        if (featureId === "transferPassword") {
          setShowTransferPasswordDialog(true);
          setIsDisablingFeature(false);
          disableScroll();
        } else if (featureId === "dailyLimit") {
          setShowDailyLimitDialog(true);
          setIsDisablingFeature(false);
          disableScroll();
        } else if (featureId === "frozen") {
          // Call API to freeze wallet
          freezeWallet();
        } else if (featureId === "2fa") {
          // Use the existing 2FA setup flow
          handle2FAToggle();
        } else if (featureId === "timeBasedAccess") {
          // إظهار نافذة إعداد الوصول المستند إلى الوقت
          setShowTimeBasedAccessDialog(true);
          setIsDisablingFeature(false);
          disableScroll();
        } else if (featureId === "geoLock") {
          // إظهار نافذة إعداد التثبيت الموقعي
          setShowGeoLockDialog(true);
          disableScroll();
        } else if (featureId === "ipWhitelist") {
          // إظهار نافذة إعداد قائمة IP المسموح بها
          setShowIpWhitelistDialog(true);
          setIsDisablingFeature(false);
          disableScroll();
        } else if (featureId === "autoSignIn") {
          // إظهار نافذة إعداد تسجيل الدخول التلقائي
          setShowAutoSignInDialog(true);
          setIsDisablingFeature(false);
          disableScroll();
        }
      } else {
        // Disable flow - all require wallet password
        if (featureId === "transferPassword") {
          setShowTransferPasswordDialog(true);
          setIsDisablingFeature(true);
          disableScroll();
        } else if (featureId === "dailyLimit") {
          setShowDailyLimitDialog(true);
          setIsDisablingFeature(true);
          disableScroll();
        } else if (featureId === "frozen") {
          setShowWalletFrozenDialog(true);
          disableScroll();
        } else if (featureId === "2fa") {
          // Use the existing 2FA disable flow
          handle2FAToggle();
        } else if (featureId === "timeBasedAccess") {
          // Open settings dialog in disable mode to properly disable the feature
          setShowTimeBasedAccessDialog(true);
          setIsDisablingFeature(true);
          disableScroll();
        } else if (featureId === "geoLock") {
          // Open settings dialog in disable mode to properly disable the feature
          setShowGeoLockDialog(true);
          setIsDisablingFeature(true);
          disableScroll();
        } else if (featureId === "ipWhitelist") {
          // فتح نافذة إعدادات قائمة IP المسموح بها
          setShowIpWhitelistDialog(true);
          setIsDisablingFeature(true);
          disableScroll();
        } else if (featureId === "autoSignIn") {
          // نعدل الكود لفتح نافذة الإعدادات مع تعيين isDisablingFeature إلى true
          setShowAutoSignInDialog(true);
          setIsDisablingFeature(true);
          disableScroll();
        }
      }
    };
  };

  // Function to freeze wallet - update to clear cache
  const freezeWallet = async () => {
    try {
      const response = await fetch("/api/security/freeze-wallet", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          action: "freeze",
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setIsWalletFrozen(true);
        // Clear the security settings cache since we updated a setting
        clearSettingsCache();
        showCustomAlert("Wallet frozen successfully", "success");
      } else {
        showCustomAlert(
          `Error: ${data.error || "Failed to freeze wallet"}`,
          "error"
        );
      }
    } catch (error) {
      console.error("Error freezing wallet:", error);
      showCustomAlert(
        "Failed to freeze wallet. Please try again later.",
        "error"
      );
    }
  };

  // Function to unfreeze wallet
  const confirmWalletUnfreeze = async () => {
    // Validate wallet password
    if (walletPassword.length >= 4) {
      try {
        const response = await fetch("/api/security/freeze-wallet", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            walletPassword: walletPassword,
            action: "unfreeze",
          }),
        });

        const data = await response.json();

        if (response.ok) {
          setIsWalletFrozen(false);
          setShowWalletFrozenDialog(false);
          resetDialogStates();
          // Clear cache after successful operation
          clearSettingsCache();
          showCustomAlert("Wallet unfrozen successfully", "success");
        } else {
          showCustomAlert(
            `Error: ${data.error || "Failed to unfreeze wallet"}`,
            "error"
          );
        }
      } catch (error) {
        console.error("Error unfreezing wallet:", error);
        showCustomAlert(
          "Failed to unfreeze wallet. Please try again later.",
          "error"
        );
      }
    }
  };

  // Update handle2FAToggle to fetch 2FA setup data from backend
  const handle2FAToggle = async () => {
    if (!is2FAEnabled) {
      // Enable 2FA flow - fetch setup data from backend
      try {
        const response = await fetch("/api/security/2fa/setup");

        if (response.ok) {
          const data = await response.json();
          // Store the QR code and secret for setup
          setTwoFAQRCode(data.qrCode);
          setTwoFASecret(data.secret);
          // Show 2FA setup modal
          setShow2FASetup(true);
          setTwoFAStep(1);
          disableScroll();
        } else {
          const errorData = await response.json();
          showCustomAlert(
            errorData.error || "Failed to initialize 2FA setup",
            "error"
          );
        }
      } catch (error) {
        console.error("Error setting up 2FA:", error);
        showCustomAlert(
          "Failed to initialize 2FA setup. Please try again later.",
          "error"
        );
      }
    } else {
      // Disable 2FA flow - show verification method selection
      setShow2FASetup(true);
      setTwoFAStep(4); // Step 4: choose disable verification method
      setTwoFACode("");
      setBackupCodeInput("");
      setDisableVerificationMethod("app");
      disableScroll();
    }
  };

  // Replace verifyTwoFACode with this updated version
  const verifyTwoFACode = async () => {
    // Enable flow
    if (twoFAStep === 2 && twoFACode.length === 6) {
      try {
        // Create a cryptographic challenge for additional verification
        const timestamp = Date.now();
        const codeHash = await crypto.subtle.digest(
          'SHA-256',
          new TextEncoder().encode(`${twoFACode}-${timestamp}`)
        ).then(hashBuffer => {
          // Convert the hash to a hex string
          return Array.from(new Uint8Array(hashBuffer))
            .map(b => b.toString(16).padStart(2, '0'))
            .join('');
        }).catch(() => '');

        // Create a challenge by reversing and encoding the code
        const challenge = btoa(twoFACode.split('').reverse().join(''));

        const response = await fetch("/api/security/2fa/verify", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            code: twoFACode,
            timestamp,
            codeHash,
            challenge
          }),
        });

        // Check HTTP status code first - 200 means successful verification
        if (response.ok) {
          const data = await response.json();
          
          // Enhanced security: Verify response content has expected properties
          if (!data || !data.message || !data.backupCodes || !Array.isArray(data.backupCodes)) {
            showCustomAlert("Invalid server response format", "error");
            return;
          }
          
          // Store verification token for future operations
          const verificationToken = data.verification_token;
          if (verificationToken) {
            sessionStorage.setItem('2fa_verification_token', verificationToken);
            sessionStorage.setItem('2fa_verification_timestamp', timestamp.toString());
          }
          
          // Set backup codes from response
          setBackupCodes(data.backupCodes);
          setTwoFAVerified(true);
          setTwoFAStep(3);
          setIs2FAEnabled(true);
          // Clear cache after enabling 2FA
          clearSettingsCache();
          showCustomAlert(
            "Two-factor authentication enabled successfully",
            "success"
          );
        } else {
          // For error responses, parse the error message
          const errorData = await response.json();
          showCustomAlert(errorData.error || "Failed to verify 2FA code", "error");
        }
      } catch (error) {
        console.error("Error verifying 2FA code:", error);
        showCustomAlert(
          "Failed to verify 2FA code. Please try again later.",
          "error"
        );
      }
    }
    // Disable flow with app verification
    else if (
      twoFAStep === 5 &&
      disableVerificationMethod === "app" &&
      twoFACode.length === 6
    ) {
      try {
        // Create a cryptographic challenge for additional verification
        const timestamp = Date.now();
        const codeHash = await crypto.subtle.digest(
          'SHA-256',
          new TextEncoder().encode(`${twoFACode}-${timestamp}`)
        ).then(hashBuffer => {
          // Convert the hash to a hex string
          return Array.from(new Uint8Array(hashBuffer))
            .map(b => b.toString(16).padStart(2, '0'))
            .join('');
        }).catch(() => '');

        // Create a challenge by reversing and encoding the code
        const challenge = btoa(twoFACode.split('').reverse().join(''));

        const response = await fetch("/api/security/2fa/disable", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            code: twoFACode,
            timestamp,
            codeHash,
            challenge
          }),
        });

        // Check HTTP status code first - 200 means successfully disabled
        if (response.ok) {
          const data = await response.json();
          
          // Enhanced security: Verify response content has expected properties and values
          if (!data || !data.message || typeof data.message !== 'string' || 
              !data.message.includes("disabled successfully")) {
            showCustomAlert("Invalid server response format", "error");
            return;
          }
          
          // Store verification token for future operations
          const verificationToken = data.verification_token;
          if (verificationToken) {
            sessionStorage.setItem('2fa_verification_token', verificationToken);
            sessionStorage.setItem('2fa_verification_timestamp', timestamp.toString());
          }
          
          setIs2FAEnabled(false);
          setShow2FASetup(false);
          setTwoFAStep(1);
          setTwoFACode("");
          // Clear cache after disabling 2FA
          clearSettingsCache();
          enableScroll(); // إضافة استعادة التمرير بعد نجاح العملية

          // If authentication method was updated, show a notification and update the UI
          if (data.transfer_auth_updated) {
            // Check if Transfer Password is enabled to determine new method
            const newMethod = isTransferPasswordEnabled
              ? "password"
              : "secret_word";
            setTransferAuthMethod(newMethod);
            setTempTransferAuthMethod(newMethod);
            showCustomAlert(
              `Two-factor authentication disabled successfully. Your transfer authentication method has been changed to ${getTransferAuthDisplayName(
                newMethod
              )}.`,
              "success"
            );
          } else {
            showCustomAlert(
              "Two-factor authentication disabled successfully",
              "success"
            );
          }
        } else {
          // For error responses, parse the error message
          const errorData = await response.json();
          showCustomAlert(errorData.error || "Failed to disable 2FA", "error");
        }
      } catch (error) {
        console.error("Error disabling 2FA:", error);
        showCustomAlert(
          "Failed to disable 2FA. Please try again later.",
          "error"
        );
      }
    }
    // Disable flow with backup code verification
    else if (
      twoFAStep === 5 &&
      disableVerificationMethod === "backup" &&
      backupCodeInput
    ) {
      try {
        // Create a cryptographic challenge for additional verification
        const timestamp = Date.now();
        const codeHash = await crypto.subtle.digest(
          'SHA-256',
          new TextEncoder().encode(`${backupCodeInput}-${timestamp}`)
        ).then(hashBuffer => {
          // Convert the hash to a hex string
          return Array.from(new Uint8Array(hashBuffer))
            .map(b => b.toString(16).padStart(2, '0'))
            .join('');
        }).catch(() => '');

        // Create a challenge by reversing and encoding the code
        const challenge = btoa(backupCodeInput.split('').reverse().join(''));

        const response = await fetch("/api/security/2fa/disable", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            backupCode: backupCodeInput,
            timestamp,
            codeHash,
            challenge
          }),
        });

        // Check HTTP status code first - 200 means successfully disabled
        if (response.ok) {
          const data = await response.json();
          
          // Enhanced security: Verify response content has expected properties and values
          if (!data || !data.message || typeof data.message !== 'string' || 
              !data.message.includes("disabled successfully")) {
            showCustomAlert("Invalid server response format", "error");
            return;
          }
          
          // Store verification token for future operations
          const verificationToken = data.verification_token;
          if (verificationToken) {
            sessionStorage.setItem('2fa_verification_token', verificationToken);
            sessionStorage.setItem('2fa_verification_timestamp', timestamp.toString());
          }
          
          setIs2FAEnabled(false);
          setShow2FASetup(false);
          setTwoFAStep(1);
          setBackupCodeInput("");
          // Clear cache after disabling 2FA
          clearSettingsCache();
          enableScroll(); // إضافة استعادة التمرير بعد نجاح العملية
          showCustomAlert(
            "Two-factor authentication disabled successfully",
            "success"
          );
        } else {
          // For error responses, parse the error message
          const errorData = await response.json();
          showCustomAlert(errorData.error || "Failed to disable 2FA", "error");
        }
      } catch (error) {
        console.error("Error disabling 2FA with backup code:", error);
        showCustomAlert(
          "Failed to disable 2FA. Please try again later.",
          "error"
        );
      }
    }
  };

  // Complete 2FA setup
  const completeTwoFASetup = () => {
    setShow2FASetup(false);
    setShowBackupCodes(false);
    resetDialogStates();
    // استعادة التمرير في الصفحة
    enableScroll();
  };

  // Confirm feature operations
  const confirmTransferPasswordSetup = async () => {
    console.log("Button clicked", {
      isDisablingFeature,
      transferPassword,
      confirmTransferPassword,
      passwordMatch: transferPassword === confirmTransferPassword,
      passwordLength: transferPassword?.length,
    });

    if (!isDisablingFeature) {
      // Enabling - validate new password
      const { isValid } = checkPasswordStrength(transferPassword);

      if (
        transferPassword &&
        transferPassword === confirmTransferPassword &&
        isValid
      ) {
        try {
          const response = await fetch("/api/security/transfer-password", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              transferPassword: transferPassword,
              isDisabling: false,
            }),
          });

          const data = await response.json();

          if (response.ok) {
            setIsTransferPasswordEnabled(true);
            setShowTransferPasswordDialog(false);
            resetDialogStates();
            // Clear cache after successful operation
            clearSettingsCache();
            showCustomAlert("Transfer password set successfully", "success");
          } else {
            showCustomAlert(
              `Error: ${data.error || "Failed to set transfer password"}`,
              "error"
            );
          }
        } catch (error) {
          console.error("Error setting transfer password:", error);
          showCustomAlert(
            "Failed to set transfer password. Please try again later.",
            "error"
          );
        }
      }
    } else {
      // Disabling - validate wallet password
      if (walletPassword.length >= 4) {
        try {
          const response = await fetch("/api/security/transfer-password", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              walletPassword: walletPassword,
              isDisabling: true,
            }),
          });

          const data = await response.json();

          if (response.ok) {
            setIsTransferPasswordEnabled(false);
            setShowTransferPasswordDialog(false);
            resetDialogStates();

            // If authentication method was updated, show a notification and update the UI
            if (data.transfer_auth_updated) {
              // Check if 2FA is enabled to determine new method
              const newMethod = is2FAEnabled ? "2fa" : "secret_word";
              setTransferAuthMethod(newMethod);
              setTempTransferAuthMethod(newMethod);
              showCustomAlert(
                `Transfer password disabled successfully. Your transfer authentication method has been changed to ${getTransferAuthDisplayName(
                  newMethod
                )}.`,
                "success"
              );
            } else {
              showCustomAlert(
                "Transfer password disabled successfully",
                "success"
              );
            }
          } else {
            showCustomAlert(
              `Error: ${data.error || "Failed to disable transfer password"}`,
              "error"
            );
          }
        } catch (error) {
          console.error("Error disabling transfer password:", error);
          showCustomAlert(
            "Failed to disable transfer password. Please try again later.",
            "error"
          );
        }
      }
    }
  };

  const confirmDailyLimitSetup = async () => {
    console.log("Daily Limit Button clicked", {
      isDisablingFeature,
      dailyLimit,
    });

    // نحصل على الدالة من useEffect
    const fetchAllSecurityData = async () => {
      try {
        console.log("Fetching fresh security settings after update");
        const data = await fetch("/api/security/settings").then(res => res.json());
        
        // تحديث الواجهة بناءً على البيانات الجديدة
        setIsTransferPasswordEnabled(data.transferPasswordEnabled || false);
        setIsDailyLimitEnabled(data.dailyLimitEnabled || false);
        setDailyLimit(data.dailyLimit || 100);
        setIs2FAEnabled(data.twoFAEnabled || false);
        setIsWalletFrozen(data.walletFrozen || false);
        
        console.log("Updated daily limit settings from server:", {
          enabled: data.dailyLimitEnabled,
          limit: data.dailyLimit
        });
      } catch (error) {
        console.error("Error refreshing security data:", error);
      }
    };

    if (!isDisablingFeature) {
      // Enabling - validate limit is set
      if (dailyLimit > 0) {
        try {
          const response = await fetch("/api/security/daily-limit", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              dailyLimit: dailyLimit,
              isDisabling: false,
            }),
          });

          const data = await response.json();

          if (response.ok) {
            setIsDailyLimitEnabled(true);
            setShowDailyLimitDialog(false);
            resetDialogStates();
            // Clear cache after successful operation
            clearSettingsCache();
            
            // Force a refresh of settings from the server
            try {
              const freshSettings = await fetch("/api/security/settings").then(res => res.json());
              if (freshSettings) {
                // Update directly from fresh data
                setIsDailyLimitEnabled(freshSettings.dailyLimitEnabled || false);
                setDailyLimit(freshSettings.dailyLimit || 100);
                console.log("Updated daily limit settings from server:", freshSettings.dailyLimitEnabled, freshSettings.dailyLimit);
              }
            } catch (refreshError) {
              console.error("Error refreshing settings:", refreshError);
            }
            
            showCustomAlert("Daily limit set successfully", "success");
            
            // Refresh data to ensure UI is consistent with server
            await fetchAllSecurityData();
          } else {
            showCustomAlert(
              `Error: ${data.error || "Failed to set daily limit"}`,
              "error"
            );
          }
        } catch (error) {
          console.error("Error setting daily limit:", error);
          showCustomAlert(
            "Failed to set daily limit. Please try again later.",
            "error"
          );
        }
      }
    } else {
      // Disabling - validate wallet password
      if (walletPassword.length >= 4) {
        try {
          const response = await fetch("/api/security/daily-limit", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              walletPassword: walletPassword,
              isDisabling: true,
            }),
          });

          const data = await response.json();

          if (response.ok) {
            setIsDailyLimitEnabled(false);
            setShowDailyLimitDialog(false);
            resetDialogStates();
            // Clear cache after successful operation
            clearSettingsCache();
            
            // Force a refresh of settings from the server
            try {
              const freshSettings = await fetch("/api/security/settings").then(res => res.json());
              if (freshSettings) {
                // Update directly from fresh data
                setIsDailyLimitEnabled(freshSettings.dailyLimitEnabled || false);
                console.log("Updated daily limit settings from server:", freshSettings.dailyLimitEnabled);
              }
            } catch (refreshError) {
              console.error("Error refreshing settings:", refreshError);
            }
            
            showCustomAlert("Daily limit removed successfully", "success");
            
            // Refresh data to ensure UI is consistent with server
            await fetchAllSecurityData();
          } else {
            showCustomAlert(
              `Error: ${data.error || "Failed to remove daily limit"}`,
              "error"
            );
          }
        } catch (error) {
          console.error("Error removing daily limit:", error);
          showCustomAlert(
            "Failed to remove daily limit. Please try again later.",
            "error"
          );
        }
      }
    }
  };

  // تمكين التمرير في الصفحة
  const enableScroll = useCallback(() => {
    document.body.style.overflow = "auto";
    document.body.style.paddingRight = "0";
  }, []);

  // تعطيل التمرير في الصفحة
  const disableScroll = useCallback(() => {
    const scrollbarWidth =
      window.innerWidth - document.documentElement.clientWidth;
    document.body.style.overflow = "hidden";
    document.body.style.paddingRight = `${scrollbarWidth}px`;
  }, []);

  // Reset dialog states
  const resetDialogStates = () => {
    setWalletPassword("");
    setTransferPassword("");
    setConfirmTransferPassword("");
    setIsDisablingFeature(false);
    setShowTransferPasswordInput(false);
    setTwoFACode("");
    setBackupCodeInput("");
    setShowBackupCodes(false);
    
    // إعادة تمكين التمرير في الصفحة
    enableScroll();
  };

  // Copy backup codes to clipboard
  const copyBackupCodes = () => {
    navigator.clipboard.writeText(backupCodes.join("\n"));
    setCopiedToClipboard(true);
    setTimeout(() => setCopiedToClipboard(false), 2000);
  };

  // تم إزالة دالة عرض رموز النسخ الاحتياطي
  // تم إزالة دوال التحقق وإغلاق نافذة رموز النسخ الاحتياطي

  // Security features definitions
  const securityFeatures = useMemo(
    () => [
      {
        id: "2fa",
        name: "Two-Factor Authentication",
        enabled: is2FAEnabled,
        importance: 25,
        icon: <ShieldCheck size={20} />,
        color: "blue",
        description: "Protect your account with an extra layer of security",
        enabledDescription: "Your account is protected with 2FA",
        disabledDescription: "Enable 2FA for stronger protection",
        toggle: handleToggle(setIs2FAEnabled, "2fa"),
      },
      {
        id: "transferPassword",
        name: "Transfer Password",
        enabled: isTransferPasswordEnabled,
        importance: 10,
        icon: <Fingerprint size={20} />,
        color: "purple",
        description: "Require a separate password for transaction approvals",
        enabledDescription:
          "Transaction approvals require additional verification",
        disabledDescription: "Add an extra layer of security for transactions",
        toggle: handleToggle(setIsTransferPasswordEnabled, "transferPassword"),
      },
      {
        id: "dailyLimit",
        name: "Daily Transfer Limit",
        enabled: isDailyLimitEnabled,
        importance: 8,
        icon: <DollarSign size={20} />,
        color: "green",
        description: "Set a maximum daily transaction amount",
        enabledDescription: `Daily limit: ${dailyLimit} CRN`,
        disabledDescription: "No limit on your daily transfers",
        toggle: handleToggle(setIsDailyLimitEnabled, "dailyLimit"),
      },
      {
        id: "autoSignIn",
        name: "Auto Sign-In",
        enabled: isAutoSignInEnabled,
        importance: 7,
        icon: <UserX2 size={20} />,
        color: "pink",
        description:
          "Keep you signed in without entering credentials each time",
        enabledDescription: "Remain signed in for 20 days",
        disabledDescription: "Login credentials required for each session",
        toggle: handleToggle(setIsAutoSignInEnabled, "autoSignIn"),
      },
      {
        id: "timeBasedAccess",
        name: "Time-based Access",
        enabled: isTimeBasedAccessEnabled,
        importance: 7,
        icon: <Clock size={20} />,
        color: "indigo",
        description: "Limit wallet access to specific hours of the day",
        enabledDescription: `Active between ${timeRange.startTime} and ${timeRange.endTime}`,
        disabledDescription: "Your wallet is accessible anytime",
        toggle: handleToggle(setIsTimeBasedAccessEnabled, "timeBasedAccess"),
        isPremium: true, // علامة ميزة مميزة
      },
      {
        id: "geoLock",
        name: "Geo-Lock",
        enabled: isGeoLockEnabled,
        importance: 15,
        icon: <MapPin size={20} />,
        color: "teal",
        description: "Restrict wallet access based on location",
        enabledDescription: "Wallet access is restricted to specific locations",
        disabledDescription: "Wallet access is unrestricted",
        toggle: handleToggle(setIsGeoLockEnabled, "geoLock"),
        isPremium: true, // علامة ميزة مميزة
      },
      {
        id: "ipWhitelist",
        name: "IP Whitelist",
        enabled: isIpWhitelistEnabled,
        importance: 28,
        icon: <Shield size={20} />,
        color: "purple",
        description: "Restrict wallet access to specific IP addresses",
        enabledDescription: `Wallet access is limited to ${ipWhitelist.length} approved IP address(es)`,
        disabledDescription: "Wallet access is allowed from any IP address",
        toggle: handleToggle(setIsIpWhitelistEnabled, "ipWhitelist"),
        isPremium: true,
      },
    ],
    [
      is2FAEnabled,
      isTransferPasswordEnabled,
      isDailyLimitEnabled,
      isTimeBasedAccessEnabled,
      isGeoLockEnabled,
      isAutoSignInEnabled,
      isIpWhitelistEnabled,
      timeRange,
      dailyLimit,
      autoSignInDuration,
      ipWhitelist,
      handleToggle, // إضافة handleToggle كاعتماد
    ]
  );

  // Calculate security score
  const securityScore = useMemo(() => {
    let score = 0;
    let totalImportance = 0;

    securityFeatures.forEach((feature) => {
      totalImportance += feature.importance;
      if (feature.enabled) {
        // Auto Sign-In reduces security, so only add points if disabled
        if (feature.id === "autoSignIn") {
          // Don't add points if enabled as it reduces security
        } else {
          score += feature.importance;
        }
      } else if (feature.id === "autoSignIn") {
        // Add points when Auto Sign-In is disabled (more secure)
        score += feature.importance;
      }
    });

    // Add extra points if using 2FA for transfers
    if (transferAuthMethod === "2fa" && is2FAEnabled) {
      score += 10;
      totalImportance += 10;
    }

    // Add extra points for transfer auth method
    if (transferAuthMethod === "password" && isTransferPasswordEnabled) {
      score += 5;
      totalImportance += 5;
    }

    // Add extra points for login auth method
    if (loginAuthMethod === "2fa" && is2FAEnabled) {
      score += 10;
      totalImportance += 10;
    } else if (loginAuthMethod === "secret_word") {
      score += 5;
      totalImportance += 5;
    }

    return Math.round((score / totalImportance) * 100);
  }, [
    securityFeatures,
    transferAuthMethod,
    loginAuthMethod,
    is2FAEnabled,
    isTransferPasswordEnabled,
  ]);

  // Determine security level
  const securityLevel = useMemo(() => {
    if (securityScore >= 75) return { text: "Strong", color: "green" };
    if (securityScore >= 50) return { text: "Good", color: "yellow" };
    if (securityScore >= 25) return { text: "Fair", color: "orange" };
    return { text: "Weak", color: "red" };
  }, [securityScore]);

  // تم إزالة متغير enabledFeatures لأنه غير مستخدم

  const getTransferAuthDisplayName = (method: string) => {
    switch (method) {
      case "password":
        return "Transfer Password";
      case "2fa":
        return "Two-Factor Authentication";
      case "secret_word":
        return "Secret Word";
      default:
        return "Transfer Password";
    }
  };

  // Helper function to show alerts - update to clean error messages
  const showCustomAlert = useCallback(
    (message: string, type: "success" | "error") => {
      // Remove "Error:" prefix if it exists
      if (type === "error" && message.startsWith("Error:")) {
        message = message.substring(6).trim();
      }
      // إغلاق أي alert سابق قبل عرض alert جديد
      setShowAlert(false);
      // تمكين التمرير في حال كان الإشعار السابق هو الوحيد المفتوح
      enableScroll();
      // تأخير قصير قبل عرض الرسالة الجديدة
      setTimeout(() => {
        setAlertMessage(message);
        setAlertType(type);
        setShowAlert(true);
        // منع التمرير عند عرض الإشعار
        disableScroll();
      }, 10);
    },
    [enableScroll, disableScroll]
  );

  // إضافة style لمنع التمرير الأفقي
  const noXScrollStyle = document.createElement("style");
  noXScrollStyle.textContent = `
  body {
    overflow-x: hidden !important;
  }
`;
  document.head.appendChild(noXScrollStyle);

  // Add a custom alert component - update the title
  const CustomAlert = () => {
    if (!showAlert) return null;

    return (
      <div className="fixed inset-0 bg-black bg-opacity-80 backdrop-blur-md flex items-center justify-center z-50 p-3 sm:p-4 animate-fadeIn">
        <div className="bg-[#1e2839] rounded-3xl shadow-2xl overflow-y-auto hide-scrollbar w-[95%] sm:w-full max-w-xs sm:max-w-md">
          <div
            className={clsx(
              "px-5 py-4 sm:px-6 sm:py-5 flex justify-between items-center",
              alertType === "success"
                ? "border-b border-gray-700"
                : "border-b border-gray-700"
            )}
          >
            <div className="flex items-center gap-3 sm:gap-4">
              <div
                className={clsx(
                  "p-2.5 sm:p-3 rounded-full",
                  alertType === "success"
                    ? "bg-green-100 dark:bg-green-900/40"
                    : "bg-red-100 dark:bg-red-900/40"
                )}
              >
                {alertType === "success" ? (
                  <CheckCircle className="text-green-600 dark:text-green-400 h-5 w-5 sm:h-6 sm:w-6" />
                ) : (
                  <AlertTriangle className="text-red-600 dark:text-red-400 h-5 w-5 sm:h-6 sm:w-6" />
                )}
              </div>
              <h2 className="text-lg sm:text-xl font-bold text-white">
                {alertType === "success" ? "Success" : "Warning"}
              </h2>
            </div>
            <button
              onClick={() => {
                // عند النقر على زر الإغلاق X، نغلق التنبيه فقط دون تنفيذ أي إجراء
                setShowAlert(false);
                enableScroll();
              }}
              className="text-gray-400 hover:text-white hover:bg-gray-700 rounded-full p-1.5 transition-all duration-200 transform hover:rotate-90"
            >
              <X size={22} />
            </button>
          </div>

          <div className="p-6 sm:p-7">
            <p className="text-sm sm:text-base text-gray-300 mb-6">
              {alertMessage}
            </p>

            <div className="flex justify-end">
              <button
                onClick={() => {
                  // عند النقر على زر OK، نتحقق مما إذا كان هذا تنبيهًا لتعطيل إحدى الميزات
                  if (alertMessage.includes("disable auto sign-in")) {
                    // تعطيل ميزة تسجيل الدخول التلقائي
                    setIsAutoSignInEnabled(false);
                    // إظهار رسالة نجاح جديدة
                    showCustomAlert(
                      "Auto sign-in has been disabled",
                      "success"
                    );
                  } else if (
                    alertMessage.includes("disable time-based access")
                  ) {
                    // تعطيل ميزة الوصول المستند إلى الوقت
                    setIsTimeBasedAccessEnabled(false);
                    // إظهار رسالة نجاح جديدة
                    showCustomAlert(
                      "Time-based access has been disabled",
                      "success"
                    );
                  } else if (alertMessage.includes("disable geo-lock")) {
                    // تعطيل ميزة التثبيت الجغرافي
                    setIsGeoLockEnabled(false);
                    // إظهار رسالة نجاح جديدة
                    showCustomAlert("Geo-lock has been disabled", "success");
                  } else {
                    // إغلاق التنبيه فقط
                    setShowAlert(false);
                    enableScroll();
                  }
                }}
                className={clsx(
                  "px-5 py-2.5 rounded-full transition-all duration-300 min-w-[100px] font-medium shadow-sm hover:shadow",
                  alertType === "success"
                    ? "bg-green-600 hover:bg-green-700 text-white"
                    : "bg-red-600 hover:bg-red-700 text-white"
                )}
              >
                OK
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Add function to properly copy the secret key with custom alerts
  const copySecretKey = () => {
    if (navigator.clipboard && twoFASecret) {
      navigator.clipboard
        .writeText(twoFASecret)
        .then(() => {
          setCopiedSecret(true);
          // Reset the copied state after 3 seconds
          setTimeout(() => setCopiedSecret(false), 3000);
        })
        .catch((err) => {
          console.error("Failed to copy text: ", err);
          showCustomAlert("Failed to copy secret key", "error");
        });
    } else {
      showCustomAlert("Clipboard access not available", "error");
    }
  };

  // Save transfer auth method to database
  const saveTransferAuthMethod = async () => {
    // Skip if method hasn't changed
    if (tempTransferAuthMethod === transferAuthMethod) {
      setIsTransferAuthDropdownOpen(false);
      return;
    }

    try {
      // Call API to update authentication method
      const response = await fetch("/api/security/transfer-auth-method", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          method: tempTransferAuthMethod,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // Update state with new method
        setTransferAuthMethod(tempTransferAuthMethod);
        setIsTransferAuthDropdownOpen(false);
        // Clear cache after changing auth method
        clearSettingsCache();

        // Show success message (might come from server as "No changes made" or regular success message)
        showCustomAlert(
          data.message || "Transfer authentication method updated successfully",
          "success"
        );
      } else {
        // Show error message
        if (data.error && data.error.includes("2FA must be enabled")) {
          showCustomAlert(
            "You must enable Two-Factor Authentication first to use this method",
            "error"
          );
        } else {
          showCustomAlert(
            data.error || "Failed to update transfer authentication method",
            "error"
          );
        }
      }
    } catch (error) {
      console.error("Error saving transfer auth method:", error);
      showCustomAlert(
        "Failed to update transfer authentication method. Please try again later.",
        "error"
      );
    }
  };

  const saveLoginAuthMethod = async () => {
    // Skip if method hasn't changed
    if (tempLoginAuthMethod === loginAuthMethod) {
      setIsLoginAuthDropdownOpen(false);
      return;
    }

    try {
      // Call API to update authentication method
      const response = await fetch("/api/security/login-auth-method", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          method: tempLoginAuthMethod,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // Update state with new method
        setLoginAuthMethod(tempLoginAuthMethod);
        setIsLoginAuthDropdownOpen(false);
        // Clear cache after changing auth method
        clearSettingsCache();

        // Show success message (might come from server as "No changes made" or regular success message)
        showCustomAlert(
          data.message || "Login authentication method updated successfully",
          "success"
        );
      } else {
        // Show error message
        if (data.error && data.error.includes("2FA must be enabled")) {
          showCustomAlert(
            "You must enable Two-Factor Authentication first to use this method",
            "error"
          );
        } else {
          showCustomAlert(
            data.error || "Failed to update login authentication method",
            "error"
          );
        }
      }
    } catch (error) {
      console.error("Error saving login auth method:", error);
      showCustomAlert(
        "Failed to update login authentication method. Please try again later.",
        "error"
      );
    }
  };

  // Function to handle input of mnemonic phrase
  const handleMnemonicInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMnemonicPhrase(e.target.value);
  };

  // Final confirmation function
  const confirmDeleteAccount = async () => {
    try {
      const response = await fetch("/api/security/delete-account", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          mnemonic_phrase: mnemonicPhrase,
          verify_only: false,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // Hide confirmation dialog
        setShowFinalConfirmation(false);

        // Clear all cached data before redirecting
        clearSettingsCache();

        showCustomAlert(
          "Account deleted successfully. You will be redirected to the login page.",
          "success"
        );

        // Redirect to login page after 2 seconds
        setTimeout(() => {
          window.location.href = "/login";
        }, 2000);
      } else {
        setShowFinalConfirmation(false);
        showCustomAlert(data.error || "Failed to delete account", "error");
      }
    } catch (error) {
      setShowFinalConfirmation(false);
      console.error("Error deleting account:", error);
      showCustomAlert(
        "Failed to delete account. Please try again later.",
        "error"
      );
    }
  };

  // Function to cancel deletion
  const cancelDeleteAccount = () => {
    setShowFinalConfirmation(false);
  };

  // Add dialog for final confirmation
  const FinalConfirmationDialog = () => {
    if (!showFinalConfirmation) return null;

    return (
      <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4">
        <div className="bg-red-50 rounded-2xl shadow-2xl max-w-md w-full p-6">
          <div className="text-center mb-6">
            <AlertTriangle
              size={48}
              className="text-red-600 inline-block mb-2"
            />
            <h3 className="text-xl font-bold text-gray-900">
              Confirm Account Deletion
            </h3>
            <p className="text-gray-700 mt-2">
              This action cannot be undone. Are you absolutely sure?
            </p>
          </div>

          <div className="flex justify-center gap-4">
            <button
              onClick={cancelDeleteAccount}
              className="px-5 py-2.5 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100"
            >
              Cancel
            </button>
            <button
              onClick={confirmDeleteAccount}
              className="px-5 py-2.5 bg-red-600 rounded-lg text-white hover:bg-red-700"
            >
              Delete Account
            </button>
          </div>
        </div>
      </div>
    );
  };

  // Optional security impact functions - for future use
  const getSecurityImpactClass = (score: number): string => {
    if (score >= 75) return "text-green-500";
    if (score >= 50) return "text-yellow-500";
    if (score >= 25) return "text-orange-500";
    return "text-red-500";
  };

  // وظيفة لتأكيد إعداد الوصول المستند إلى الوقت
  const confirmTimeBasedAccessSetup = () => {
    // Check if user is premium before proceeding
    if (!walletData?.premium) {
      setShowTimeBasedAccessDialog(false);
      enableScroll();
      return;
    }
    
    if (isDisablingFeature) {
      // Make API call to disable time-based access
      fetch("/api/security/time-based-access", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          enabled: false,
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.error) {
            showCustomAlert(data.error, "error");
            return;
          }
          
          // Update local state
          setIsTimeBasedAccessEnabled(false);
          setShowTimeBasedAccessDialog(false);
          setIsDisablingFeature(false);
          enableScroll();
          
          // Clear the security settings cache
          clearSettingsCache();
          
          showCustomAlert("Time-based access has been disabled.", "success");
        })
        .catch((error) => {
          console.error("Error updating time-based access:", error);
          showCustomAlert("Failed to update time-based access.", "error");
        });
    } else {
      // Make API call to enable time-based access
      fetch("/api/security/time-based-access", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          enabled: true,
          start_time: timeRange.startTime,
          end_time: timeRange.endTime,
          timezone: selectedTimezone
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.error) {
            showCustomAlert(data.error, "error");
            return;
          }
          
          // Update local state
          setIsTimeBasedAccessEnabled(true);
          setShowTimeBasedAccessDialog(false);
          enableScroll();
          
          // Clear the security settings cache
          clearSettingsCache();
          
          showCustomAlert("Time-based access activated.", "success");
        })
        .catch((error) => {
          console.error("Error updating time-based access:", error);
          showCustomAlert("Failed to update time-based access.", "error");
        });
    }
  };

  // وظيفة لتأكيد إعداد تسجيل الدخول التلقائي
  const confirmAutoSignInSetup = () => {
    // Log current state to help with debugging
    console.log("Auto Sign-In: Current state:", {
      isDisablingFeature,
      isAutoSignInEnabled,
      willBeEnabled: !isDisablingFeature
    });
    
    // Make API call to backend to save auto sign-in settings
    fetch("/api/security/auto-signin", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        enabled: !isDisablingFeature,
        duration: autoSignInDuration
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.error) {
          showCustomAlert(data.error, "error");
          return;
        }
        
        // Update local state with values from the response
        setIsAutoSignInEnabled(data.enabled);
        if (data.duration) {
          setAutoSignInDuration(data.duration);
        }
        setShowAutoSignInDialog(false);
        enableScroll();
        
        // Clear the security settings cache
        clearSettingsCache();
        
        if (isDisablingFeature) {
          showCustomAlert("Auto sign-in has been disabled.", "success");
        } else {
          showCustomAlert(`Auto sign-in activated for ${autoSignInDuration} days.`, "success");
        }
      })
      .catch((error) => {
        console.error("Error updating auto sign-in settings:", error);
        showCustomAlert("Failed to update auto sign-in settings.", "error");
      });
  };

  // Function to confirm Geo-Lock setup
  const confirmGeoLockSetup = () => {
    // Check if user is premium before proceeding
    if (!walletData?.premium) {
      setShowGeoLockDialog(false);
      enableScroll();
      return;
    }
    
    if (isDisablingFeature) {
      // Make API call to disable geo-lock
      fetch("/api/security/geo-lock", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          enabled: false,
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.error) {
            showCustomAlert(data.error, "error");
            return;
          }
          
          // Update local state
          setIsGeoLockEnabled(false);
          setShowGeoLockDialog(false);
          setIsDisablingFeature(false);
          enableScroll();
          
          // Clear the security settings cache
          clearSettingsCache();
          
          showCustomAlert("Geo-lock has been disabled.", "success");
        })
        .catch((error) => {
          console.error("Error updating geo-lock:", error);
          showCustomAlert("Failed to update geo-lock.", "error");
        });
    } else {
      // Check if we have any countries in the list
      if (allowedCountries.length === 0) {
        showCustomAlert("Please add at least one country to enable geo-lock", "error");
        return;
      }
      
      // Make API call to enable geo-lock with multiple countries support
      fetch("/api/security/geo-lock", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          enabled: true,
          countries: allowedCountries.map(c => c.country_code),
          country_details: allowedCountries
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.error) {
            showCustomAlert(data.error, "error");
            return;
          }
          
          // Update local state
          setIsGeoLockEnabled(true);
          setShowGeoLockDialog(false);
          enableScroll();
          
          // Clear the security settings cache
          clearSettingsCache();
          
          showCustomAlert("Geo-lock activated.", "success");
        })
        .catch((error) => {
          console.error("Error updating geo-lock:", error);
          showCustomAlert("Failed to update geo-lock.", "error");
        });
    }
  };

  // وظيفة لتأكيد إعداد قائمة IP المسموح بها
  const confirmIpWhitelistSetup = () => {
    // Check if user is premium before proceeding
    if (!walletData?.premium) {
      setShowIpWhitelistDialog(false);
      enableScroll();
      return;
    }
    
    if (isDisablingFeature) {
      // Make API call to disable IP whitelist
      fetch("/api/security/ip-whitelist", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          enabled: false,
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.error) {
            showCustomAlert(data.error, "error");
            return;
          }
          
          // Update local state
          setIsIpWhitelistEnabled(false);
          setShowIpWhitelistDialog(false);
          setIsDisablingFeature(false);
          enableScroll();
          
          // Clear the security settings cache
          clearSettingsCache();
          
          showCustomAlert("IP whitelist has been disabled.", "success");
        })
        .catch((error) => {
          console.error("Error updating IP whitelist:", error);
          showCustomAlert("Failed to update IP whitelist.", "error");
        });
    } else {
      // Check if there are IP addresses in the whitelist
      if (ipWhitelist.length === 0) {
        showCustomAlert("Please add at least one IP address to the whitelist.", "error");
        return;
      }
      
      // Make API call to enable IP whitelist with IP details
      fetch("/api/security/ip-whitelist", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          enabled: true,
          ips: ipWhitelist,
          ip_details: ipDetailsList
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.error) {
            showCustomAlert(data.error, "error");
            return;
          }
          
          // Update local state
          setIsIpWhitelistEnabled(true);
          setShowIpWhitelistDialog(false);
          enableScroll();
          
          // Clear the security settings cache
          clearSettingsCache();
          
          showCustomAlert("IP whitelist activated.", "success");
        })
        .catch((error) => {
          console.error("Error updating IP whitelist:", error);
          showCustomAlert("Failed to update IP whitelist.", "error");
        });
    }
  };

  // دالة للتحقق من صحة عنوان IP
  const isValidIpAddress = (ip: string): boolean => {
    // Regular expression للتحقق من صحة عنوان IP
    const ipRegex =
      /^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
    return ipRegex.test(ip);
  };

  // New state for IP scan results
  const [ipScanResults, setIpScanResults] = useState<{
    ip_address: string;
    country: string;
    region: string;
    city: string;
    location: string;
    postal: string | null;
    timezone: string;
    provider: string;
    scanning: boolean;
    showResults: boolean;
  }>({
    ip_address: "",
    country: "",
    region: "",
    city: "",
    location: "",
    postal: null,
    timezone: "",
    provider: "",
    scanning: false,
    showResults: false
  });

  // Function to scan current IP
  const scanCurrentIP = async () => {
    try {
      setIpScanResults(prev => ({ ...prev, scanning: true, showResults: false }));
      
      console.log("Starting IP scan...");
      
      // Call the backend API for IP scanning
      const response = await fetch("/api/security/ip-whitelist/scan", {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          // Add cache control to prevent cached responses
          "Cache-Control": "no-cache, no-store"
        },
      });
      
      console.log("Scan response status:", response.status);
      
      // Get response text for debugging
      const responseText = await response.text();
      console.log("Response text:", responseText);
      
      // Parse JSON
      let data;
      try {
        data = JSON.parse(responseText);
      } catch (e) {
        console.error("Failed to parse response as JSON:", e);
        throw new Error("Invalid response format");
      }
      
      if (!response.ok) {
        // If unauthorized or not premium, handle appropriately
        if (response.status === 403) {
          showCustomAlert("This feature is only available for premium users", "error");
        } else {
          const errorMessage = data.error || "Failed to fetch IP information";
          console.error("Error from server:", errorMessage);
          throw new Error(errorMessage);
        }
        setIpScanResults(prev => ({ ...prev, scanning: false }));
        return;
      }
      
      console.log("Received IP data:", data);
      
      // Process the data
      const ipData = {
        ip_address: data.ip_address || "",
        country: data.country || "",
        region: data.region || "",
        city: data.city || "",
        location: data.location || "",
        postal: data.postal || null,
        timezone: data.timezone || "",
        provider: data.provider || "",
        scanning: false,
        showResults: true
      };
      
      console.log("Processed IP data:", ipData);
      
      setIpScanResults(ipData);
      setNewIpAddress(data.ip_address); // Set the scanned IP in the input field
      showCustomAlert("IP address scanned successfully", "success");
      
    } catch (error) {
      console.error("Error scanning IP:", error);
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      showCustomAlert(`Failed to scan IP address: ${errorMessage}`, "error");
      setIpScanResults(prev => ({ ...prev, scanning: false }));
    }
  };

  // State to store IP details
  const [ipDetailsList, setIpDetailsList] = useState<Array<{
    ip_address: string;
    country: string;
    region: string;
    city: string;
    location: string;
    timezone: string;
    provider: string;
  }>>([]);
  
  // دالة لإضافة عنوان IP إلى القائمة البيضاء
  const addIpToWhitelist = () => {
    // If we have scan results, use that data
    if (ipScanResults.showResults) {
      // التحقق من عدم وجود العنوان مسبقًا في القائمة
      if (ipWhitelist.includes(ipScanResults.ip_address)) {
        showCustomAlert("This IP address is already in the whitelist", "error");
        return;
      }

      // Add IP to whitelist with full details
      setIpWhitelist([...ipWhitelist, ipScanResults.ip_address]);
      
      // Also store the detailed information
      const newIpDetails = {
        ip_address: ipScanResults.ip_address,
        country: ipScanResults.country,
        region: ipScanResults.region,
        city: ipScanResults.city,
        location: ipScanResults.location,
        timezone: ipScanResults.timezone,
        provider: ipScanResults.provider
      };
      
      setIpDetailsList([...ipDetailsList, newIpDetails]);
      setNewIpAddress(""); // إعادة تعيين حقل الإدخال
      setIpScanResults(prev => ({ ...prev, showResults: false }));
      showCustomAlert(`IP address ${ipScanResults.ip_address} added to whitelist`, "success");
      return;
    }
    
    // Fallback to manual entry
    // التحقق من صحة عنوان IP
    if (!isValidIpAddress(newIpAddress)) {
      showCustomAlert("Please enter a valid IP address", "error");
      return;
    }

    // التحقق من عدم وجود العنوان مسبقًا في القائمة
    if (ipWhitelist.includes(newIpAddress)) {
      showCustomAlert("This IP address is already in the whitelist", "error");
      return;
    }

    // إضافة العنوان إلى القائمة
    setIpWhitelist([...ipWhitelist, newIpAddress]);
    
    // Add basic details for manually entered IP
    const basicIpDetails = {
      ip_address: newIpAddress,
      country: "",
      region: "",
      city: "",
      location: "",
      timezone: "",
      provider: ""
    };
    
    setIpDetailsList([...ipDetailsList, basicIpDetails]);
    setNewIpAddress(""); // إعادة تعيين حقل الإدخال
    showCustomAlert("IP address added to whitelist", "success");
  };

  // دالة لإزالة عنوان IP من القائمة البيضاء
  const removeIpFromWhitelist = (ip: string) => {
    setIpWhitelist(ipWhitelist.filter((address) => address !== ip));
    setIpDetailsList(ipDetailsList.filter((details) => details.ip_address !== ip));
    showCustomAlert("IP address removed from whitelist", "success");
  };

  // استبدال كود الخريطة
  // Google Maps integration - replace with vanilla Leaflet
  const [isMapLoading, setIsMapLoading] = useState(false);
  const [isMapInitialized, setIsMapInitialized] = useState(false);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const leafletMapRef = useRef<L.Map | null>(null);
  const mapMarkerRef = useRef<L.Marker | null>(null);

  // تهيئة الخريطة ووضع علامة على الموقع
  const initializeMap = useCallback(() => {
    if (!mapContainerRef.current || leafletMapRef.current) return;

    try {
      setIsMapLoading(true);

      // تطبيق العناصر الأمنية في واجهة المستخدم
      getSecurityImpactClass(securityScore);

      // إنشاء خريطة جديدة
      const map = L.map(mapContainerRef.current).setView(
        [geoLockCoordinates.lat, geoLockCoordinates.lng],
        mapZoom
      );

      // إضافة طبقة الخريطة
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(map);

      // إضافة علامة على الموقع
      const marker = L.marker([
        geoLockCoordinates.lat,
        geoLockCoordinates.lng,
      ]).addTo(map);

      // معالج النقر على الخريطة
      map.on("click", (e: L.LeafletMouseEvent) => {
        const { lat, lng } = e.latlng;

        // تحديث الإحداثيات والموقع
        setGeoLockCoordinates({ lat, lng });
        setGeoLockLocation(
          `Custom Location (${lat.toFixed(4)}, ${lng.toFixed(4)})`
        );

        // تحريك العلامة
        marker.setLatLng([lat, lng]);

        showCustomAlert("Location selected successfully", "success");
      });

      // حفظ مراجع الخريطة والعلامة
      leafletMapRef.current = map;
      mapMarkerRef.current = marker;
      setIsMapInitialized(true);
      setIsMapLoading(false);

      // Invalidate map size after a short delay to ensure proper rendering
      setTimeout(() => {
        if (leafletMapRef.current) {
          leafletMapRef.current.invalidateSize();
        }
      }, 100);
    } catch (error) {
      console.error("Error initializing map:", error);
      setIsMapLoading(false);
    }
  }, [geoLockCoordinates, mapZoom, securityScore, showCustomAlert]);

  // تنظيف الخريطة عند إزالة المكون
  const cleanupMap = useCallback(() => {
    if (leafletMapRef.current) {
      leafletMapRef.current.remove();
      leafletMapRef.current = null;
      mapMarkerRef.current = null;
      setIsMapInitialized(false);
    }
  }, []);

  // تهيئة الخريطة عند فتح النافذة المنبثقة وتنظيفها عند إغلاقها
  useEffect(() => {
    if (showGeoLockDialog) {
      // تعيين التأخير قصير للتأكد من أن المكون تم تحميله بالكامل
      const mapInitTimeout = setTimeout(() => {
        initializeMap();
      }, 300);

      return () => {
        clearTimeout(mapInitTimeout);
        cleanupMap();
      };
    }
  }, [showGeoLockDialog, initializeMap, cleanupMap]);

  // تحديث موقع العلامة عند تغيير الإحداثيات
  useEffect(() => {
    if (leafletMapRef.current && mapMarkerRef.current && isMapInitialized) {
      // تحريك العلامة إلى الموقع الجديد
      mapMarkerRef.current.setLatLng([
        geoLockCoordinates.lat,
        geoLockCoordinates.lng,
      ]);

      // تحريك الخريطة إلى الموقع الجديد
      leafletMapRef.current.panTo([
        geoLockCoordinates.lat,
        geoLockCoordinates.lng,
      ]);

      // ضبط مستوى التكبير عند تحديد موقع جديد
      setMapZoom(12);
    }
  }, [geoLockCoordinates, isMapInitialized]);

  // إضافة مكون DevicesModal هنا
  // No longer needed - using the DevicesList component instead
  // const [showDevicesModal, setShowDevicesModal] = useState(false);

  // No longer needed - now using the DevicesList component
  // Removed DevicesModal component

  // Function to load allowed countries from security settings
  const loadAllowedCountries = (geoLockSettings: any) => {
    try {
      if (!geoLockSettings) return;
      
      // Check if using new multi-country format
      if (geoLockSettings.countries && Array.isArray(geoLockSettings.countries)) {
        // New format
        const countryList = geoLockSettings.countries || [];
        const countryDetails = geoLockSettings.country_details || [];
        
        // Create a map of country details for easier lookup
        const detailsMap: Record<string, any> = {};
        countryDetails.forEach((detail: any) => {
          if (detail && detail.country_code) {
            detailsMap[detail.country_code] = detail;
          }
        });
        
        // Create the allowed countries list
        const countries = countryList.map((code: string) => {
          const detail = detailsMap[code] || { country_code: code, country_name: code };
          return {
            country_code: code,
            country_name: detail.country_name || code,
            coordinates: detail.coordinates || { lat: 0, lng: 0 }
          };
        });
        
        setAllowedCountries(countries);
        
        // Set first country as current if any exist
        if (countries.length > 0) {
          const firstCountry = countries[0];
          setGeoLockCountry(firstCountry.country_code);
          setGeoLockLocation(firstCountry.country_name);
          setGeoLockCoordinates(firstCountry.coordinates || { lat: 0, lng: 0 });
        }
      } else if (geoLockSettings.country) {
        // Old format - single country
        setGeoLockCountry(geoLockSettings.country);
        
        // Create one entry in the allowed countries list
        setAllowedCountries([{
          country_code: geoLockSettings.country,
          country_name: geoLockSettings.country,
          coordinates: geoLockSettings.coordinates || { lat: 0, lng: 0 }
        }]);
      } else {
        setAllowedCountries([]);
      }
    } catch (error) {
      console.error("Error loading allowed countries:", error);
      setAllowedCountries([]);
    }
  };

  // Add function to clear security alerts
  const clearSecurityAlerts = () => {
    if (walletData?.security?.securityFeatures) {
      // Save the acknowledged alerts to localStorage for persistence
      const newAcknowledgedAlerts = [...acknowledgedAlerts, ...walletData.security.securityFeatures];
      setAcknowledgedAlerts(newAcknowledgedAlerts);
      
      // Save to localStorage for persistence between sessions
      localStorage.setItem('acknowledgedSecurityAlerts', JSON.stringify(newAcknowledgedAlerts));
      
      // Update wallet data to show 0 alerts
      setWalletData(prevData => {
        if (!prevData) return prevData;
        return {
          ...prevData,
          security: {
            ...prevData.security,
            alerts: 0,
            securityFeatures: []
          }
        };
      });
      
      // Close the dialog
      setShowSecurityAlertsDialog(false);
      
      // Show success message
      showCustomAlert("Security alerts cleared", "success");
    }
  };

  return (
    <div className="min-h-screen bg-[#262626] pl-0 pt-4 pb-16 relative overflow-x-hidden w-full">
      {/* تم إزالة زر مشاهدة رموز النسخ الاحتياطي */}
      <div className="mx-auto px-2 sm:px-4 max-w-7xl w-full">
        {/* Header - Made responsive by stacking on mobile */}
        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center mb-6 gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-[#FFFFFF] mb-1">
              Security Center
            </h1>
            <p className="text-sm sm:text-base text-gray-600">
              Protect your Cryptonel Wallet with advanced security features.
            </p>
          </div>
        </div>

        {/* Main Security Card - Improved for mobile */}
        <div
          className={clsx(
            "security-card bg-[#262626] rounded-2xl shadow-md border border-[#232323] p-4 sm:p-5 mb-6 sm:mb-8 min-w-[320px]",
            "transform transition-all duration-1000",
            animateSection
              ? "translate-y-0 opacity-100"
              : "translate-y-10 opacity-0"
          )}
        >
          <div className="flex flex-col items-start gap-6 sm:gap-8 layout-cols-1024">
            {/* Left Column - Security Status - Made responsive */}
            <div className="w-full flex flex-col items-center layout-col-1024">
              {/* Security Status Section - Updated Design */}
              <div className="w-full text-center md:text-left mb-4">
                <h2 className="text-xl font-bold text-[#FFFFFF] mb-3 flex items-center justify-center md:justify-start">
                  Security Status
                </h2>
                <p className="text-[#C4C4C7] text-sm sm:text-base">
                  Your account security level is{" "}
                  <span
                    className={`font-semibold ${
                      securityLevel.color === "red"
                        ? "text-red-600"
                        : securityLevel.color === "yellow"
                        ? "text-yellow-600"
                        : securityLevel.color === "orange"
                        ? "text-orange-600"
                        : "text-green-600"
                    }`}
                  >
                    currently {securityLevel.text}
                  </span>
                </p>
              </div>

              {/* Security Score Circle - New Design */}
              <SecurityScoreCircle score={securityScore} />

              {/* Additional Security Cards - Active Sessions & Security Alerts */}
              <div className="w-full flex flex-col sm:flex-row gap-3 mt-5">
                {/* Active Sessions Card - Improved Design */}
                <div className="flex-1 bg-[#2b2b2b] rounded-xl shadow-sm border border-[#232323] p-3 sm:p-5 transition-all hover:shadow-md">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-[#B0B0B5] text-base font-medium">
                      Active Sessions
                    </h4>
                    <div className="bg-[#2a2340] p-2.5 rounded-lg">
                      <Smartphone className="w-5 h-5 text-purple-400" />
                    </div>
                  </div>

                  <div>
                    <div className="text-3xl font-semibold text-white">
                      {walletData?.security?.activeSessions || 1}
                    </div>
                    <div className="text-[#C4C4C7] text-sm mt-1">
                      {(walletData?.security?.activeSessions || 1) > 1
                        ? "active devices"
                        : "active device"}
                    </div>
                  </div>

                  <div className="mt-4">
                    <button
                      className="text-[#8B5CF6] hover:text-[#a78bfa] text-sm flex items-center transition-colors"
                      onClick={() => setShowDevicesDialog(true)}
                    >
                      Manage Devices
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </button>
                  </div>
                </div>

                {/* Security Alerts Card - Improved Design */}
                <div className="flex-1 bg-[#2b2b2b] rounded-xl shadow-sm border border-[#232323] p-4 sm:p-5 transition-all hover:shadow-md">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-[#B0B0B5] text-base font-medium">
                      Security Alerts
                    </h4>
                    <div className={`p-2.5 rounded-lg ${(walletData?.security?.alerts || 0) > 0 ? "bg-[#2a2323]" : "bg-[#1e2a23]"}`}>
                      {(walletData?.security?.alerts || 0) > 0 ? (
                        <AlertTriangle className="w-5 h-5 text-red-400" />
                      ) : (
                        <ShieldCheck className="w-5 h-5 text-green-400" />
                      )}
                    </div>
                  </div>

                  <div>
                    <div className="text-3xl font-semibold text-white">
                      {walletData?.security?.alerts || 0}
                    </div>
                    <div className="text-[#C4C4C7] text-sm mt-1">
                      {(walletData?.security?.alerts || 0) === 1
                        ? "inactive security feature"
                        : "inactive security features"}
                    </div>
                  </div>

                  <div className="mt-4">
                    {(walletData?.security?.alerts || 0) > 0 ? (
                      <div>
                        {walletData?.premium ? (
                          <div className="text-xs text-amber-400 mb-2">
                            {walletData?.security?.securityFeatures?.map((feature, index) => (
                              <div key={index} className="mb-1 flex items-center">
                                <Shield className="w-3 h-3 mr-1" />
                                <span>{feature} not enabled</span>
                              </div>
                            ))}
                          </div>
                        ) : null}
                        <button 
                          onClick={() => setShowSecurityAlertsDialog(true)}
                          className="text-red-400 hover:text-red-500 text-sm flex items-center transition-colors"
                        >
                          View Security Features
                          <ChevronRight className="h-4 w-4 ml-1" />
                        </button>
                      </div>
                    ) : (
                      <span className="text-green-500 text-sm flex items-center">
                        <Check className="h-4 w-4 mr-1" />
                        All security features active
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Security Info Cards - Last Login & Last Security Update */}
              <div className="w-full flex flex-col sm:flex-row gap-3 mt-3">
                {/* Last Login Card - Improved Design */}
                <div className="flex-1 bg-[#2b2b2b] rounded-xl shadow-sm border border-[#232323] p-4 sm:p-5 transition-all hover:shadow-md">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-[#B0B0B5] text-base font-medium">
                      Last Login
                    </h4>
                    <div className="bg-[#23243a] p-2.5 rounded-lg">
                      <Clock className="w-5 h-5 text-blue-400" />
                    </div>
                  </div>

                  <div>
                    <div className="text-base font-medium text-white">
                      {walletData?.security?.lastLogin
                        ? formatDateTime(walletData.security.lastLogin)
                        : "No recent login"}
                    </div>
                    <div className="mt-1.5 text-xs text-[#C4C4C7]">
                      From{" "}
                      {walletData?.security?.deviceInfo || "Unknown Device"}
                    </div>
                    {walletData?.security?.lastLoginLocation && (
                      <div className="mt-1 text-xs text-[#A0A0A7]">
                        Location: {walletData.security.lastLoginLocation}
                      </div>
                    )}
                  </div>
                </div>

                {/* Last Security Update Card - Improved Design */}
                <div className="flex-1 bg-[#2b2b2b] rounded-xl shadow-sm border border-[#232323] p-4 sm:p-5 transition-all hover:shadow-md">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-[#B0B0B5] text-base font-medium">
                      Last Security Update
                    </h4>
                    <div className="bg-[#1e2a23] p-2.5 rounded-lg">
                      <ShieldCheck className="w-5 h-5 text-green-400" />
                    </div>
                  </div>

                  <div>
                    <div className="text-base font-medium text-white">
                      {walletData?.security?.lastUpdate && walletData.security.lastUpdate !== ""
                        ? formatDateTime(walletData.security.lastUpdate)
                        : "No recent updates"}
                    </div>
                    {walletData?.security?.updateType && walletData.security.updateType !== "" && (
                      <div className="mt-2">
                        <span className="text-xs px-2.5 py-1 bg-green-900 text-green-400 rounded-full font-medium">
                          {walletData.security.updateType}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Right Column - Security Features - Made responsive */}
            <div className="w-full layout-col-1024 flex flex-col">
              <h2 className="text-xl font-bold text-[#FFFFFF] mb-3 mt-4 lg:mt-0">
                Security Features
              </h2>

              <div className="space-y-3 sm:space-y-4">
                {/* Security Features List - Enhanced design */}
                {securityFeatures.map((feature) => (
                  <div
                    key={feature.id}
                    className={`group transition-all duration-300 transform ${feature.isPremium && !walletData?.premium ? 'opacity-70' : 'hover:-translate-y-1'} bg-[#2b2b2b] border border-[#232323] hover:border-blue-300 hover:shadow-md rounded-xl p-4 relative overflow-y-auto hide-scrollbar`}
                  >
                    <div className="flex items-center justify-between relative z-10">
                      <div className="flex items-center gap-2 sm:gap-3 md:gap-4">
                        <div
                          className={`flex items-center justify-center w-8 h-8 sm:w-10 sm:h-10 md:w-12 md:h-12 rounded-full transition-all duration-300 ${
                            feature.id === "transferPassword"
                              ? feature.enabled
                                ? "bg-[#2a2340] text-purple-300"
                                : "bg-[#2a2340] text-purple-300"
                              : feature.id === "dailyLimit"
                              ? feature.enabled
                                ? "bg-[#203320] text-green-300"
                                : "bg-[#203320] text-green-300"
                              : feature.id === "2fa"
                              ? feature.enabled
                                ? "bg-[#1e2142] text-blue-300"
                                : "bg-[#1e2142] text-blue-300"
                              : feature.id === "timeBasedAccess"
                              ? feature.enabled
                                ? "bg-[#2a2340] text-indigo-300"
                                : "bg-[#2a2340] text-indigo-300"
                              : feature.id === "geoLock"
                              ? feature.enabled
                                ? "bg-[#1a2f2f] text-teal-300"
                                : "bg-[#1a2f2f] text-teal-300"
                              : feature.id === "autoSignIn"
                              ? feature.enabled
                                ? "bg-[#3a1f29] text-pink-300"
                                : "bg-[#3a1f29] text-pink-300"
                              : feature.id === "ipWhitelist"
                              ? feature.enabled
                                ? "bg-[#2a2340] text-purple-300"
                                : "bg-[#2a2340] text-purple-300"
                              : feature.enabled
                              ? "bg-[#1e2142] text-blue-300"
                              : "bg-[#1e2142] text-blue-300"
                          }`}
                        >
                          {feature.icon}
                        </div>

                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <h4 className="font-semibold text-[#FFFFFF] text-base sm:text-lg">
                              {feature.name}
                            </h4>
                            {feature.isPremium && (
                              <span className="ml-1 sm:ml-2 px-1.5 py-0.5 sm:px-2.5 sm:py-1 bg-gradient-to-r from-yellow-300 to-amber-400 text-yellow-900 text-[10px] sm:text-xs rounded-full font-semibold flex items-center">
                                <Crown className="h-2 w-2 sm:h-3 sm:w-3 mr-0.5 sm:mr-1" />
                                Premium
                              </span>
                            )}
                          </div>

                          {feature.id === "dailyLimit" &&
                          isDailyLimitEnabled ? (
                            <div>
                              <p className="text-gray-500 text-xs sm:text-sm mt-1">
                                {feature.enabledDescription}
                              </p>
                              <p className="text-green-600 text-sm font-medium mt-1 flex items-center">
                                <span className="inline-block w-2 h-2 rounded-full bg-green-500 mr-2"></span>
                                <span>Limit: {dailyLimit} CRN per day</span>
                              </p>
                            </div>
                          ) : feature.id === "timeBasedAccess" &&
                            isTimeBasedAccessEnabled ? (
                            <div>
                              <p className="text-gray-500 text-xs sm:text-sm mt-1">
                                {feature.enabledDescription}
                              </p>
                              <p className="text-indigo-600 text-sm font-medium mt-1 flex items-center">
                                <span className="inline-block w-2 h-2 rounded-full bg-indigo-500 mr-2"></span>
                                <span>
                                  Active: {timeRange.startTime} - {timeRange.endTime}
                                </span>
                              </p>
                            </div>
                          ) : feature.id === "geoLock" && isGeoLockEnabled ? (
                            <div>
                              <p className="text-gray-500 text-xs sm:text-sm mt-1">
                                {feature.enabledDescription}
                              </p>
                              <p className="text-teal-600 text-sm font-medium mt-1 flex items-center">
                                <span className="inline-block w-2 h-2 rounded-full bg-teal-500 mr-2"></span>
                                <span>Location: {geoLockLocation}</span>
                              </p>
                            </div>
                          ) : feature.id === "ipWhitelist" &&
                            isIpWhitelistEnabled ? (
                            <div>
                              <p className="text-gray-500 text-xs sm:text-sm mt-1">
                                {feature.enabledDescription}
                              </p>
                              <p className="text-purple-600 text-sm font-medium mt-1 flex items-center">
                                <span className="inline-block w-2 h-2 rounded-full bg-purple-500 mr-2"></span>
                                <span>IP Addresses: {ipWhitelist.length}</span>
                              </p>
                            </div>
                          ) : (
                            <p className="text-gray-500 text-xs sm:text-sm mt-1">
                              {feature.enabled
                                ? feature.enabledDescription
                                : feature.disabledDescription}
                            </p>
                          )}
                          
                          {feature.isPremium && !walletData?.premium && (
                            <p className="text-amber-400 text-xs font-medium mt-1 flex items-center">
                              <Crown className="h-3 w-3 mr-1" />
                              Upgrade to Premium to unlock this feature
                            </p>
                          )}
                        </div>
                      </div>

                      <div className="ml-2">
                        <label className={`relative inline-flex items-center ${feature.isPremium && !walletData?.premium ? 'cursor-not-allowed' : 'cursor-pointer'}`}>
                          <input
                            type="checkbox"
                            className="sr-only peer"
                            checked={feature.enabled}
                            onChange={feature.toggle}
                            disabled={feature.isPremium && !walletData?.premium}
                          />
                          <div
                            className={`w-14 h-7 rounded-full peer transition-colors duration-300 ${
                              feature.enabled
                                ? feature.id === "transferPassword"
                                  ? "bg-purple-500 hover:bg-purple-600"
                                  : feature.id === "dailyLimit"
                                  ? "bg-green-500 hover:bg-green-600"
                                  : feature.id === "2fa"
                                  ? "bg-blue-500 hover:bg-blue-600"
                                  : feature.id === "timeBasedAccess"
                                  ? "bg-indigo-500 hover:bg-indigo-600"
                                  : feature.id === "geoLock"
                                  ? "bg-teal-500 hover:bg-teal-600"
                                  : feature.id === "autoSignIn"
                                  ? "bg-pink-500 hover:bg-pink-600"
                                  : feature.id === "ipWhitelist"
                                  ? "bg-purple-500 hover:bg-purple-600"
                                  : "bg-blue-500 hover:bg-blue-600"
                                : feature.isPremium && !walletData?.premium
                                ? "bg-gray-500 opacity-50"
                                : "bg-gray-300 hover:bg-gray-400"
                            } after:content-[''] after:absolute after:top-0.5 after:left-[4px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:shadow-sm after:transition-all peer-checked:after:translate-x-7`}
                          ></div>
                        </label>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* إضافة القوائم المنسدلة هنا */}
        {/* Login Authentication Dropdown */}
        {isLoginAuthDropdownOpen && (
          <div className="fixed inset-0 bg-black bg-opacity-20 flex items-center justify-center z-50 p-4 animate-fadeIn">
            <div className="bg-white rounded-xl shadow-xl overflow-y-auto hide-scrollbar w-full max-w-md mx-auto relative">
              <div className="px-6 py-4 bg-indigo-600 text-white flex justify-between items-center">
                <h3 className="text-lg font-bold">Login Authentication</h3>
                <button
                  onClick={() => setIsLoginAuthDropdownOpen(false)}
                  className="text-white rounded-full p-1 hover:bg-white hover:bg-opacity-20"
                >
                  <X size={20} />
                </button>
              </div>
              <div className="p-6">
                <div className="text-sm text-gray-500 mb-4">
                  Select how you want to secure your wallet login
                </div>
                <div className="space-y-3">
                  <button
                    onClick={() => setTempLoginAuthMethod("none")}
                    className="w-full text-left px-4 py-3 rounded-lg flex items-center justify-between border border-gray-200 hover:bg-gray-50"
                  >
                    <div className="flex items-center gap-3">
                      <div className="bg-gray-100 p-2 rounded-full">
                        <Lock size={18} className="text-gray-500" />
                      </div>
                      <span className="font-medium">Password Only</span>
                    </div>
                    {tempLoginAuthMethod === "none" && (
                      <Check size={18} className="text-indigo-600" />
                    )}
                  </button>

                  <button
                    onClick={() => setTempLoginAuthMethod("secret_word")}
                    className="w-full text-left px-4 py-3 rounded-lg flex items-center justify-between border border-gray-200 hover:bg-gray-50"
                  >
                    <div className="flex items-center gap-3">
                      <div className="bg-gray-100 p-2 rounded-full">
                        <KeySquare size={18} className="text-gray-500" />
                      </div>
                      <span className="font-medium">Secret Word</span>
                    </div>
                    {tempLoginAuthMethod === "secret_word" && (
                      <Check size={18} className="text-indigo-600" />
                    )}
                  </button>

                  <button
                    onClick={() =>
                      is2FAEnabled && setTempLoginAuthMethod("2fa")
                    }
                    className={`w-full text-left px-4 py-3 rounded-lg flex items-center justify-between border border-gray-200 ${
                      is2FAEnabled
                        ? "hover:bg-gray-50"
                        : "opacity-60 cursor-not-allowed"
                    }`}
                    disabled={!is2FAEnabled}
                  >
                    <div className="flex items-center gap-3">
                      <div className="bg-gray-100 p-2 rounded-full">
                        <Smartphone
                          size={18}
                          className={
                            is2FAEnabled ? "text-gray-500" : "text-gray-300"
                          }
                        />
                      </div>
                      <div>
                        <span
                          className={`font-medium ${
                            is2FAEnabled ? "" : "text-gray-400"
                          }`}
                        >
                          Two-Factor Authentication
                        </span>
                        {!is2FAEnabled && (
                          <p className="text-xs text-gray-400 mt-1">
                            Enable 2FA first to use this option
                          </p>
                        )}
                      </div>
                    </div>
                    {tempLoginAuthMethod === "2fa" && (
                      <Check size={18} className="text-indigo-600" />
                    )}
                  </button>
                </div>

                <div className="mt-6 flex justify-end gap-3">
                  <button
                    onClick={() => {
                      setTempLoginAuthMethod(loginAuthMethod);
                      setIsLoginAuthDropdownOpen(false);
                    }}
                    className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 rounded-lg transition-colors border border-gray-200"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={saveLoginAuthMethod}
                    className="px-5 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                  >
                    Save
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Transfer Authentication Dropdown */}
        {isTransferAuthDropdownOpen && (
          <div className="fixed inset-0 bg-black bg-opacity-20 flex items-center justify-center z-50 p-4 animate-fadeIn">
            <div className="bg-white rounded-xl shadow-xl overflow-y-auto hide-scrollbar w-full max-w-md mx-auto relative">
              <div className="px-6 py-4 bg-indigo-600 text-white flex justify-between items-center">
                <h3 className="text-lg font-bold">Transfer Authentication</h3>
                <button
                  onClick={() => setIsTransferAuthDropdownOpen(false)}
                  className="text-white rounded-full p-1 hover:bg-white hover:bg-opacity-20"
                >
                  <X size={20} />
                </button>
              </div>
              <div className="p-6">
                <div className="text-sm text-gray-500 mb-4">
                  Select authentication method for transfers
                </div>
                <div className="space-y-3">
                  {/* Transfer Password Option */}
                  <button
                    onClick={() =>
                      isTransferPasswordEnabled &&
                      setTempTransferAuthMethod("password")
                    }
                    className={`w-full text-left px-4 py-3 rounded-lg flex items-center justify-between border border-gray-200 ${
                      isTransferPasswordEnabled
                        ? "hover:bg-gray-50"
                        : "opacity-60 cursor-not-allowed"
                    }`}
                    disabled={!isTransferPasswordEnabled}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`bg-gray-100 p-2 rounded-full ${
                          tempTransferAuthMethod === "password" &&
                          isTransferPasswordEnabled
                            ? "bg-indigo-50"
                            : ""
                        }`}
                      >
                        {isTransferPasswordEnabled ? (
                          <Fingerprint
                            size={18}
                            className={
                              tempTransferAuthMethod === "password"
                                ? "text-indigo-600"
                                : "text-gray-500"
                            }
                          />
                        ) : (
                          <Lock size={18} className="text-gray-300" />
                        )}
                      </div>
                      <div>
                        <span
                          className={`font-medium ${
                            isTransferPasswordEnabled ? "" : "text-gray-400"
                          }`}
                        >
                          Transfer Password
                        </span>
                        {!isTransferPasswordEnabled && (
                          <p className="text-xs text-gray-400 mt-1">
                            Enable Transfer Password first to use this option
                          </p>
                        )}
                      </div>
                    </div>
                    {tempTransferAuthMethod === "password" && (
                      <Check size={18} className="text-indigo-600" />
                    )}
                  </button>

                  {/* 2FA Option */}
                  <button
                    onClick={() =>
                      is2FAEnabled && setTempTransferAuthMethod("2fa")
                    }
                    className={`w-full text-left px-4 py-3 rounded-lg flex items-center justify-between border border-gray-200 ${
                      is2FAEnabled
                        ? "hover:bg-gray-50"
                        : "opacity-60 cursor-not-allowed"
                    }`}
                    disabled={!is2FAEnabled}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`bg-gray-100 p-2 rounded-full ${
                          tempTransferAuthMethod === "2fa" && is2FAEnabled
                            ? "bg-indigo-50"
                            : ""
                        }`}
                      >
                        {is2FAEnabled ? (
                          <Smartphone
                            size={18}
                            className={
                              tempTransferAuthMethod === "2fa"
                                ? "text-indigo-600"
                                : "text-gray-500"
                            }
                          />
                        ) : (
                          <Lock size={18} className="text-gray-300" />
                        )}
                      </div>
                      <div>
                        <span
                          className={`font-medium ${
                            is2FAEnabled ? "" : "text-gray-400"
                          }`}
                        >
                          Two-Factor Authentication
                        </span>
                        {!is2FAEnabled && (
                          <p className="text-xs text-gray-400 mt-1">
                            Enable 2FA first to use this option
                          </p>
                        )}
                      </div>
                    </div>
                    {tempTransferAuthMethod === "2fa" && (
                      <Check size={18} className="text-indigo-600" />
                    )}
                  </button>

                  {/* Secret Word Option */}
                  <button
                    onClick={() => setTempTransferAuthMethod("secret_word")}
                    className="w-full text-left px-4 py-3 rounded-lg flex items-center justify-between border border-gray-200 hover:bg-gray-50"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`bg-gray-100 p-2 rounded-full ${
                          tempTransferAuthMethod === "secret_word"
                            ? "bg-indigo-50"
                            : ""
                        }`}
                      >
                        <Key
                          size={18}
                          className={
                            tempTransferAuthMethod === "secret_word"
                              ? "text-indigo-600"
                              : "text-gray-500"
                          }
                        />
                      </div>
                      <span className="font-medium">Secret Word</span>
                    </div>
                    {tempTransferAuthMethod === "secret_word" && (
                      <Check size={18} className="text-indigo-600" />
                    )}
                  </button>
                </div>

                <div className="mt-6 flex justify-end gap-3">
                  <button
                    onClick={() => {
                      setTempTransferAuthMethod(transferAuthMethod);
                      setIsTransferAuthDropdownOpen(false);
                    }}
                    className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 rounded-lg transition-colors border border-gray-200"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={saveTransferAuthMethod}
                    className={`px-5 py-2 text-sm rounded-lg ${
                      tempTransferAuthMethod === transferAuthMethod
                        ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                        : "bg-indigo-600 text-white hover:bg-indigo-700"
                    } transition-colors`}
                    disabled={tempTransferAuthMethod === transferAuthMethod}
                  >
                    Save
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 2FA Setup Modal - Enhanced for all screens */}
        {show2FASetup && (
          <div className="fixed inset-0 bg-black bg-opacity-80 backdrop-blur-md flex items-start sm:items-center justify-center z-50 p-2 sm:p-4 animate-fadeIn pt-8 sm:pt-2">
            <div className="bg-[#2b2b2b] rounded-3xl shadow-2xl overflow-y-auto hide-scrollbar w-[95%] sm:w-full max-w-md max-h-[80vh] sm:max-h-[85vh] border border-[#393939] transform transition-all duration-300 scale-100 pb-4 sm:pb-0 mb-14 sm:mb-0">
              <div className="sticky top-0 z-10 p-4 sm:p-6 flex justify-between items-center border-b border-[#393939] bg-[#2b2b2b]">
                <div className="flex items-center gap-2 sm:gap-4">
                  <div className="bg-[#1e2142] p-2 sm:p-3 rounded-full">
                    <ShieldCheck className="text-blue-300 h-5 w-5 sm:h-6 sm:w-6" />
                  </div>
                  <h2 className="text-lg sm:text-xl font-bold text-white">
                    {is2FAEnabled
                      ? "Disable Two-Factor Authentication"
                      : "Set Up Two-Factor Authentication"}
                  </h2>
                </div>
                <button
                  onClick={() => {
                    setShow2FASetup(false);
                    resetDialogStates();
                    if (is2FAEnabled) {
                      // Do not change step for disabling flow, just close
                    } else {
                      // Reset to step 1 for enabling flow
                      setTwoFAStep(1);
                    }
                    enableScroll();
                  }}
                  className="text-gray-400 hover:bg-[#393939] rounded-full p-1.5 transition-all duration-200 transform hover:rotate-90"
                >
                  <X size={22} />
                </button>
              </div>

              {/* عرض الخطوات في نافذة 2FA */}
              {twoFAStep < 4 && (
                <div className="flex items-center justify-center px-4 sm:px-6 py-4 border-b border-[#393939] bg-[#232323]">
                  <div className="w-full max-w-sm">
                    <div className="relative flex justify-between items-center pb-4">
                      {/* الخط الواصل */}
                      <div
                        className="absolute top-5 left-0 right-0 h-1 bg-gray-700"
                        style={{ zIndex: 1 }}
                      />
                      {/* الخط المتقدم */}
                      <div
                        className="absolute top-5 left-0 h-1 bg-blue-600 transition-all duration-500"
                        style={{
                          width:
                            twoFAStep === 1
                              ? "0%"
                              : twoFAStep === 2
                              ? "50%"
                              : "90%",
                          zIndex: 2,
                        }}
                      />

                      {/* الخطوة 1 */}
                      <div className="flex flex-col items-center relative z-10">
                        <div
                          className={clsx(
                            "h-10 w-10 sm:h-12 sm:w-12 rounded-full flex items-center justify-center text-white font-medium transition-colors duration-300 shadow",
                            twoFAStep === 1
                              ? "bg-blue-600"
                              : twoFAStep > 1
                              ? "bg-green-500"
                              : "bg-gray-600"
                          )}
                        >
                          <span className="text-sm sm:text-base font-bold">1</span>
                        </div>
                        <span className="text-xs sm:text-sm font-medium text-gray-300 mt-2.5 whitespace-nowrap bg-[#232323] px-1 rounded">
                          Choose
                        </span>
                      </div>

                      {/* الخطوة 2 */}
                      <div className="flex flex-col items-center relative z-10">
                        <div
                          className={clsx(
                            "h-10 w-10 sm:h-12 sm:w-12 rounded-full flex items-center justify-center text-white font-medium transition-colors duration-300 shadow",
                            twoFAStep === 2
                              ? "bg-blue-600"
                              : twoFAStep > 2
                              ? "bg-green-500"
                              : "bg-gray-600"
                          )}
                        >
                          <span className="text-sm sm:text-base font-bold">2</span>
                        </div>
                        <span className="text-xs sm:text-sm font-medium text-gray-300 mt-2.5 whitespace-nowrap bg-[#232323] px-1 rounded">
                          Setup
                        </span>
                      </div>

                      {/* الخطوة 3 */}
                      <div className="flex flex-col items-center relative z-10">
                        <div
                          className={clsx(
                            "h-10 w-10 sm:h-12 sm:w-12 rounded-full flex items-center justify-center text-white font-medium transition-colors duration-300 shadow",
                            twoFAStep === 3
                              ? "bg-blue-600"
                              : twoFAStep > 3 || twoFAVerified
                              ? "bg-green-500"
                              : "bg-gray-600"
                          )}
                        >
                          {twoFAVerified ? (
                            <Check size={16} className="sm:w-5 sm:h-5" />
                          ) : (
                            <span className="text-sm sm:text-base font-bold">3</span>
                          )}
                        </div>
                        <span className="text-xs sm:text-sm font-medium text-gray-300 mt-2.5 whitespace-nowrap bg-[#232323] px-1 rounded">
                          Complete
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Step 1 Content */}
              {twoFAStep === 1 && (
                <div className="px-4 py-4 border-t border-[#393939]">
                  <h3 className="text-lg font-medium text-white mb-4">
                    Choose Authentication Method
                  </h3>

                  <div className="border rounded-xl p-5 cursor-pointer transition-all border-blue-700 bg-[#1e2142] hover:shadow-md mb-5">
                    <div className="flex flex-col items-center text-center">
                      <div className="flex items-center justify-center mb-3">
                        <Smartphone size={24} className="text-blue-400" />
                      </div>
                      <h4 className="font-medium text-white mb-1">
                        Authenticator App
                      </h4>
                      <p className="text-sm text-gray-300">
                        Use an app like Google Authenticator or Authy
                      </p>
                    </div>
                  </div>

                  <div className="flex justify-end space-x-3 mt-4">
                    <button
                      onClick={() => {
                        setShow2FASetup(false);
                        resetDialogStates();
                      }}
                      className="px-4 py-2 border border-[#393939] text-gray-300 rounded-lg hover:bg-[#393939] transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => setTwoFAStep(2)}
                      className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      Continue
                    </button>
                  </div>
                </div>
              )}

              {/* Step 2 Content */}
              {twoFAStep === 2 && (
                <div className="px-4 sm:px-6 py-4 sm:py-5 border-t border-[#393939]">
                  <h3 className="text-base sm:text-lg font-medium text-white mb-4 sm:mb-5">
                    Set Up Authenticator App
                  </h3>

                  <div className="flex flex-col gap-5 sm:gap-6 mb-5 sm:mb-6">
                    {/* QR Code and Setup Key Section */}
                    <div className="flex flex-col items-center">
                      {/* QR Code */}
                      <div className="bg-[#232323] p-2 sm:p-3 rounded-lg border border-[#393939] shadow-sm mb-3">
                        <div className="w-40 h-40 sm:w-44 sm:h-44 mx-auto flex items-center justify-center">
                          {twoFAQRCode ? (
                            <img
                              src={twoFAQRCode}
                              alt="QR Code for 2FA Setup"
                              className="w-full h-full object-contain"
                            />
                          ) : (
                            <div className="animate-pulse bg-gray-700 w-full h-full"></div>
                          )}
                        </div>
                      </div>
                      <p className="text-xs sm:text-sm text-center text-blue-400 mb-3 sm:mb-4">
                        Scan with Google Authenticator or compatible app
                      </p>

                      {/* Setup Key - Full Width */}
                      <div className="w-full">
                        <div className="bg-[#232323] rounded-lg border border-[#393939] p-2 mb-2 w-full">
                          <div className="flex justify-between items-center w-full">
                            <code className="text-xs sm:text-sm text-white font-mono px-2 select-all whitespace-nowrap overflow-x-auto w-full max-w-[75%] sm:max-w-[85%]">
                              {twoFASecret}
                            </code>
                            <button
                              onClick={copySecretKey}
                              className="ml-2 p-1.5 text-gray-400 hover:text-white rounded-full hover:bg-[#2a2340] focus:outline-none flex-shrink-0"
                              aria-label="Copy secret key"
                            >
                              {copiedSecret ? (
                                <Check size={16} className="text-green-400" />
                              ) : (
                                <Copy size={16} />
                              )}
                            </button>
                          </div>
                        </div>
                        <p className="text-xs text-gray-400 text-center">
                          Alternative: Manually enter this key in your app
                        </p>
                      </div>
                    </div>

                    {/* Verification Section */}
                    <div className="flex flex-col">
                      <div className="bg-[#232323] p-3 sm:p-4 rounded-lg border border-[#393939] mb-3 sm:mb-4">
                        <h4 className="font-medium text-white mb-2 sm:mb-3">
                          Verify Setup
                        </h4>
                        <p className="text-xs sm:text-sm text-gray-300 mb-3">
                          Enter the 6-digit code from your authenticator app to
                          verify setup.
                        </p>
                        <div className="space-y-3">
                          <label className="text-xs sm:text-sm font-medium text-gray-300">
                            Authentication Code
                          </label>
                          <input
                            type="text"
                            placeholder="Enter 6-digit code"
                            maxLength={6}
                            value={twoFACode}
                            onChange={(e) => {
                              const value = e.target.value.replace(
                                /[^0-9]/g,
                                ""
                              );
                              setTwoFACode(value);
                            }}
                            className="w-full p-2.5 sm:p-3 px-3 sm:px-4 border border-[#393939] rounded-lg bg-[#1a1e2e] text-white text-sm sm:text-base"
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Button container with extra bottom padding for mobile */}
                  <div className="w-full pt-4 sm:pt-5 border-t border-[#393939] mt-5 sm:mt-6">
                    <div className="flex justify-between pb-10 sm:pb-0">
                      <button
                        onClick={() => setTwoFAStep(1)}
                        className="px-3 sm:px-4 py-2 sm:py-2.5 border border-[#393939] text-gray-300 rounded-lg hover:bg-[#393939] transition-colors text-sm"
                      >
                        Back
                      </button>
                      <button
                        onClick={verifyTwoFACode}
                        disabled={twoFACode.length !== 6}
                        className={clsx(
                          "px-3 sm:px-5 py-2 sm:py-2.5 rounded-lg transition-colors text-sm",
                          twoFACode.length === 6
                            ? "bg-blue-600 text-white hover:bg-blue-700"
                            : "bg-gray-600 text-white cursor-not-allowed opacity-70"
                        )}
                      >
                        Verify & Enable
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Step 3 Content */}
              {twoFAStep === 3 && (
                <div className="px-4 py-4 border-t border-[#393939]">
                  <div className="text-center mb-5 sm:mb-8">
                    <div className="inline-flex items-center justify-center h-14 w-14 sm:h-16 sm:w-16 rounded-full bg-[#232323] mb-3 sm:mb-4">
                      <CheckCircle size={28} className="sm:text-[32px] text-green-400" />
                    </div>
                    <h3 className="text-lg sm:text-xl font-bold text-white mb-2">
                      Two-Factor Authentication Enabled
                    </h3>
                    <p className="text-sm text-gray-300">
                      Your account is now protected with an additional security
                      layer.
                    </p>
                  </div>

                  {!showBackupCodes ? (
                    <div className="bg-[#232323] p-4 rounded-xl border border-[#393939] mb-6">
                      <div className="flex items-start gap-3">
                        <AlertTriangle
                          size={20}
                          className="text-yellow-400 flex-shrink-0 mt-0.5"
                        />
                        <div>
                          <h4 className="font-medium text-white mb-1">
                            Important: Save Your Backup Codes
                          </h4>
                          <p className="text-sm text-gray-300 mb-3">
                            If you lose access to your authentication device,
                            you'll need these backup codes to access your
                            account.
                          </p>
                          <button
                            onClick={() => setShowBackupCodes(true)}
                            className="px-4 py-2 bg-[#2a2340] text-yellow-300 rounded-lg hover:bg-[#352a52] transition-colors text-sm"
                          >
                            Show Backup Codes
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="mb-6">
                      <h4 className="font-medium text-white mb-3">
                        Your Backup Codes
                      </h4>
                      <p className="text-sm text-gray-300 mb-4">
                        Store these codes securely - each code can only be used
                        once.
                      </p>
                      <div className="bg-[#232323] border border-[#393939] rounded-lg p-4 mb-3">
                        <div className="grid grid-cols-2 gap-2">
                          {backupCodes.map((code, index) => (
                            <div
                              key={index}
                              className="font-mono text-sm text-white bg-[#1a1e2e] px-3 py-1.5 rounded-md select-all"
                            >
                              {code}
                            </div>
                          ))}
                        </div>
                      </div>
                      <div className="flex justify-end mb-2">
                        <button
                          onClick={copyBackupCodes}
                          className="flex items-center gap-1.5 text-sm px-3 py-1.5 border border-[#393939] rounded-lg text-gray-300 hover:bg-[#393939] transition-colors"
                        >
                          <Copy size={14} />
                          {copiedToClipboard ? "Copied" : "Copy All Codes"}
                        </button>
                      </div>
                      <div className="bg-[#232323] p-3 rounded-lg border border-[#393939]">
                        <p className="text-sm text-yellow-400 flex items-start gap-2">
                          <AlertTriangle
                            size={16}
                            className="flex-shrink-0 mt-0.5"
                          />
                          <span>
                            Without these codes, you may lose access to your
                            account if your authentication device is lost or
                            broken.
                          </span>
                        </p>
                      </div>
                    </div>
                  )}

                  <div className="flex justify-end pb-10 sm:pb-0">
                    <button
                      onClick={completeTwoFASetup}
                      className="px-4 py-2 sm:py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
                    >
                      Done
                    </button>
                  </div>
                </div>
              )}

              {/* Step 4: Choose Disable Verification Method - محسن للموبايل */}
              {twoFAStep === 4 && (
                <div className="px-4 py-4 border-t border-[#393939]">
                  <div className="text-center mb-5">
                    <div className="inline-flex items-center justify-center h-14 w-14 sm:h-16 sm:w-16 rounded-full bg-[#ff6b6b20] mb-3 sm:mb-4">
                      <AlertTriangle size={28} className="text-red-500" />
                    </div>
                    <h3 className="text-lg sm:text-xl font-bold text-white mb-2">
                      Disable Two-Factor Authentication
                    </h3>
                    <p className="text-sm text-gray-400 mb-4">
                      Please select a verification method to confirm.
                    </p>
                  </div>

                  <div className="bg-[#2d1e1e] p-3 sm:p-4 rounded-lg border border-[#4d2c2c] mb-4 sm:mb-5">
                    <div className="flex items-start gap-2 sm:gap-3">
                      <AlertTriangle
                        size={18}
                        className="text-red-400 flex-shrink-0 mt-0.5"
                      />
                      <div className="text-xs sm:text-sm text-gray-300">
                        <p className="font-medium mb-1">
                          Warning: Reduced Security
                        </p>
                        <p>
                          Disabling 2FA will make your account more vulnerable
                          to unauthorized access.
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-3 mb-4 sm:mb-5">
                    <div
                      className={clsx(
                        "border rounded-lg p-3 cursor-pointer transition-all",
                        disableVerificationMethod === "app"
                          ? "border-red-500 bg-[#2d1e1e]"
                          : "border-[#393939] hover:border-red-800 hover:bg-[#2d1e1e]/50"
                      )}
                      onClick={() => setDisableVerificationMethod("app")}
                    >
                      <div className="flex items-center gap-2 sm:gap-3">
                        <div
                          className={`flex items-center justify-center w-12 h-12 rounded-2xl ${
                            disableVerificationMethod === "app"
                              ? "bg-[#ff6b6b20] text-red-400"
                              : "bg-[#1e2839] text-gray-400"
                          }`}
                        >
                          <Smartphone size={18} className="sm:w-5 sm:h-5" />
                        </div>
                        <div>
                          <p className="font-medium text-white text-sm sm:text-base">
                            Authenticator App
                          </p>
                          <p className="text-xs sm:text-sm text-gray-400">
                            Use a 6-digit code from your authenticator app
                          </p>
                        </div>
                      </div>
                    </div>

                    <div
                      className={clsx(
                        "border rounded-lg p-3 cursor-pointer transition-all",
                        disableVerificationMethod === "backup"
                          ? "border-red-500 bg-[#2d1e1e]"
                          : "border-[#393939] hover:border-red-800 hover:bg-[#2d1e1e]/50"
                      )}
                      onClick={() => setDisableVerificationMethod("backup")}
                    >
                      <div className="flex items-center gap-2 sm:gap-3">
                        <div
                          className={`flex items-center justify-center w-12 h-12 rounded-2xl ${
                            disableVerificationMethod === "backup"
                              ? "bg-[#ff6b6b20] text-red-400"
                              : "bg-[#1e2839] text-gray-400"
                          }`}
                        >
                          <Key size={18} className="sm:w-5 sm:h-5" />
                        </div>
                        <div>
                          <p className="font-medium text-white text-sm sm:text-base">
                            Backup Code
                          </p>
                          <p className="text-xs sm:text-sm text-gray-400">
                            Use one of your recovery backup codes
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Fix buttons positioning and add proper spacing on mobile */}
                  <div className="flex justify-between mt-5 pb-10 sm:pb-0">
                    <button
                      onClick={() => {
                        setShow2FASetup(false);
                        resetDialogStates();
                      }}
                      className="px-4 py-2 border border-[#393939] text-gray-300 rounded-lg hover:bg-[#393939] transition-colors text-sm"
                    >
                      Back
                    </button>

                    <button
                      onClick={() => setTwoFAStep(5)}
                      disabled={!disableVerificationMethod}
                      className={clsx(
                        "px-3 py-2 rounded-lg transition-colors text-sm",
                        disableVerificationMethod
                          ? "bg-red-600 text-white hover:bg-red-700"
                          : "bg-gray-600 text-gray-300 cursor-not-allowed"
                      )}
                    >
                      Continue
                    </button>
                  </div>
                </div>
              )}

              {/* Step 5: Disable Verification - محسن للموبايل */}
              {twoFAStep === 5 && (
                <div className="px-4 py-4 border-t border-[#393939]">
                  <div className="text-center mb-5">
                    <div className="inline-flex items-center justify-center h-14 w-14 sm:h-16 sm:w-16 rounded-full bg-[#ff6b6b20] mb-3 sm:mb-4">
                      {disableVerificationMethod === "app" ? (
                        <Smartphone size={28} className="text-red-500" />
                      ) : (
                        <Key size={28} className="text-red-500" />
                      )}
                    </div>
                    <h3 className="text-lg sm:text-xl font-bold text-white mb-2">
                      {disableVerificationMethod === "app"
                        ? "Enter Authentication Code"
                        : "Enter Backup Code"}
                    </h3>
                    <p className="text-xs sm:text-sm text-gray-400 mb-4">
                      {disableVerificationMethod === "app"
                        ? "Please enter the 6-digit verification code from your authenticator app"
                        : "Please enter one of your backup codes (format: XXXX-XXXX-XXXX)"}
                    </p>
                  </div>

                  {disableVerificationMethod === "app" ? (
                    <div className="mb-5">
                      {/* 6-digit code input - Improved responsive sizing */}
                      <div className="flex justify-center gap-1 sm:gap-2">
                        {Array(6)
                          .fill(0)
                          .map((_, index) => (
                            <input
                              key={index}
                              type="tel"
                              inputMode="numeric"
                              maxLength={1}
                              pattern="[0-9]"
                              className="w-9 sm:w-11 h-10 sm:h-12 rounded-lg border border-[#393939] bg-[#1e2839] text-center text-base font-semibold text-white focus:border-red-500 focus:ring-1 focus:ring-red-500"
                              value={twoFACode[index] || ""}
                              onChange={(e) => {
                                // فلترة القيمة للتأكد من أنها رقم فقط
                                if (!/^\d*$/.test(e.target.value)) {
                                  return;
                                }

                                const newCode = twoFACode.split("");
                                newCode[index] = e.target.value;
                                setTwoFACode(newCode.join(""));

                                // Auto advance to next input
                                if (e.target.value && index < 5) {
                                  const element = e.target;
                                  if (
                                    element &&
                                    element instanceof HTMLInputElement &&
                                    element.parentElement
                                  ) {
                                    const parentDiv = element.parentElement;
                                    const inputs =
                                      parentDiv.querySelectorAll("input");
                                    if (inputs && inputs[index + 1]) {
                                      inputs[index + 1].focus();
                                    }
                                  }
                                }
                              }}
                              onKeyDown={(e) => {
                                // Handle backspace to go to previous input
                                if (
                                  e.key === "Backspace" &&
                                  !twoFACode[index] &&
                                  index > 0
                                ) {
                                  const element = e.target;
                                  if (
                                    element &&
                                    element instanceof HTMLInputElement &&
                                    element.parentElement
                                  ) {
                                    const parentDiv = element.parentElement;
                                    const inputs =
                                      parentDiv.querySelectorAll("input");
                                    if (inputs && inputs[index - 1]) {
                                      inputs[index - 1].focus();
                                    }
                                  }
                                }
                              }}
                              onPaste={(e) => {
                                // منع السلوك الافتراضي للصق
                                e.preventDefault();

                                // الحصول على النص الملصق
                                const pastedData =
                                  e.clipboardData.getData("text");

                                // استخراج الأرقام فقط من النص الملصق
                                const digits = pastedData
                                  .replace(/\D/g, "")
                                  .split("");

                                // تحديث الرمز مع الأرقام الملصقة وتوزيعها على الحقول
                                const newCode = [...twoFACode];

                                // تحديد عدد الأرقام المراد إدراجها
                                const remainingSlots = 6 - index;
                                const digitsToInsert = digits.slice(
                                  0,
                                  remainingSlots
                                );

                                // إدراج الأرقام
                                digitsToInsert.forEach((digit, i) => {
                                  newCode[index + i] = digit;
                                });

                                // تحديث الحالة
                                setTwoFACode(newCode.join(""));

                                // التركيز على الحقل الصحيح بعد اللصق
                                if (
                                  digits.length > 0 &&
                                  index + digits.length < 6
                                ) {
                                  const parentDiv =
                                    e.currentTarget.parentElement;
                                  if (parentDiv) {
                                    const inputs =
                                      parentDiv.querySelectorAll("input");
                                    const nextIndex = Math.min(
                                      index + digits.length,
                                      5
                                    );
                                    if (inputs && inputs[nextIndex]) {
                                      inputs[nextIndex].focus();
                                    }
                                  }
                                }
                              }}
                            />
                          ))}
                      </div>
                    </div>
                  ) : (
                    <div className="mb-5">
                      {/* Backup code input */}
                      <div className="flex justify-center">
                        <input
                          type="text"
                          placeholder="XXXX-XXXX-XXXX"
                          className="w-full max-w-xs p-2.5 sm:p-3 rounded-lg border border-[#393939] bg-[#1e2839] text-center text-base font-medium text-white focus:border-red-500 focus:ring-1 focus:ring-red-500"
                          value={backupCodeInput}
                          onClick={(e) => e.stopPropagation()}
                          onFocus={(e) => e.stopPropagation()}
                          onChange={(e) => {
                            try {
                              // Remove any non-alphanumeric characters and dashes
                              let value = e.target.value
                                .toUpperCase()
                                .replace(/[^A-Z0-9-]/g, "");

                              // Ensure dashes are in the right places
                              if (value.length > 4 && value.charAt(4) !== "-") {
                                value =
                                  value.slice(0, 4) + "-" + value.slice(4);
                              }
                              if (value.length > 9 && value.charAt(9) !== "-") {
                                value =
                                  value.slice(0, 9) + "-" + value.slice(9);
                              }

                              // Ensure the total length doesn't exceed 14 characters (XXXX-XXXX-XXXX)
                              if (value.length > 14) {
                                value = value.slice(0, 14);
                              }

                              setBackupCodeInput(value);
                            } catch (error) {
                              console.error(
                                "Error in backup code input:",
                                error
                              );
                            }
                          }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Improved button placement and accessibility */}
                  <div className="flex justify-between mt-5 mb-2 pb-10 sm:pb-0">
                    <button
                      onClick={() => {
                        setTwoFAStep(4);
                        // Reset input values when going back
                        setTwoFACode("");
                        setBackupCodeInput("");
                      }}
                      className="px-3 py-2.5 border border-[#393939] text-gray-300 rounded-lg hover:bg-[#393939] transition-colors text-sm"
                    >
                      Back
                    </button>

                    <button
                      onClick={verifyTwoFACode}
                      disabled={
                        (disableVerificationMethod === "app" &&
                          twoFACode.length !== 6) ||
                        (disableVerificationMethod === "backup" &&
                          backupCodeInput.length < 14)
                      }
                      className={clsx(
                        "px-3 py-2.5 rounded-lg transition-colors text-sm",
                        (disableVerificationMethod === "app" &&
                          twoFACode.length === 6) ||
                          (disableVerificationMethod === "backup" &&
                            backupCodeInput.length === 14)
                          ? "bg-red-600 text-white hover:bg-red-700"
                          : "bg-gray-600 text-gray-300 cursor-not-allowed"
                      )}
                    >
                      Disable 2FA
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Transfer Password Dialog - Made responsive */}
        {showTransferPasswordDialog && (
          <div className="fixed inset-0 bg-black bg-opacity-80 backdrop-blur-md flex items-center justify-center z-50 p-3 sm:p-4 animate-fadeIn">
            <div className="bg-[#2b2b2b] rounded-3xl shadow-2xl overflow-y-auto hide-scrollbar w-[95%] sm:w-full max-w-md max-h-[90vh] overflow-y-auto hide-scrollbar border border-[#393939] transform transition-all duration-300 scale-100">
              <div className="p-5 sm:p-6 flex justify-between items-center border-b border-[#393939]">
                <div className="flex items-center gap-3 sm:gap-4">
                  <div className="bg-[#2a2340] p-2.5 sm:p-3 rounded-full">
                    <Fingerprint className="text-purple-300 h-5 w-5 sm:h-6 sm:w-6" />
                  </div>
                  <h2 className="text-lg sm:text-xl font-bold text-white">
                    {isDisablingFeature
                      ? "Disable Transfer Password"
                      : "Set Transfer Password"}
                  </h2>
                </div>
                <button
                  onClick={() => {
                    setShowTransferPasswordDialog(false);
                    resetDialogStates();
                  }}
                  className="text-gray-400 hover:bg-[#393939] rounded-full p-1.5 transition-all duration-200 transform hover:rotate-90"
                >
                  <X size={22} />
                </button>
              </div>

              <div className="p-5 sm:p-6">
                {!isDisablingFeature ? (
                  // Setting up a Transfer Password
                  <div className="space-y-5">
                    <div className="bg-[#232323] p-4 rounded-xl border border-[#393939]">
                      <div className="flex items-start gap-3">
                        <Info className="text-blue-400 h-5 w-5 flex-shrink-0 mt-0.5" />
                        <p className="text-sm text-gray-300">
                          Create a separate password that will be required to
                          approve any transfer transactions.
                        </p>
                      </div>
                    </div>

                    <div className="space-y-5">
                      <div className="space-y-1.5">
                        <label className="block text-sm font-medium text-gray-300 mb-1.5">
                          Create Transfer Password
                        </label>
                        <div className="relative group">
                          <input
                            type={
                              showTransferPasswordInput ? "text" : "password"
                            }
                            placeholder="Create a strong password"
                            className="w-full p-3.5 pl-4 border border-[#393939] rounded-full bg-[#232323] focus:ring-2 focus:ring-purple-500 focus:border-purple-500 shadow-sm group-hover:shadow transition-all duration-200 text-white placeholder-gray-500"
                            value={transferPassword}
                            onChange={(e) =>
                              setTransferPassword(e.target.value)
                            }
                          />
                          <button
                            type="button"
                            onClick={() =>
                              setShowTransferPasswordInput((prev) => !prev)
                            }
                            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white p-2 touch-manipulation transition-colors duration-200"
                          >
                            {showTransferPasswordInput ? (
                              <EyeOff size={20} />
                            ) : (
                              <Eye size={20} />
                            )}
                          </button>
                        </div>
                        {transferPassword &&
                          checkPasswordStrength(transferPassword).message && (
                            <p className="mt-1.5 text-xs text-amber-400">
                              {checkPasswordStrength(transferPassword).message}
                            </p>
                          )}
                      </div>

                      <div className="space-y-1.5">
                        <label className="block text-sm font-medium text-gray-300 mb-1.5">
                          Confirm Transfer Password
                        </label>
                        <div className="relative group">
                          <input
                            type={
                              showTransferPasswordInput ? "text" : "password"
                            }
                            placeholder="Confirm password"
                            className="w-full p-3.5 pl-4 border border-[#393939] rounded-full bg-[#232323] focus:ring-2 focus:ring-purple-500 focus:border-purple-500 shadow-sm group-hover:shadow transition-all duration-200 text-white placeholder-gray-500"
                            value={confirmTransferPassword}
                            onChange={(e) =>
                              setConfirmTransferPassword(e.target.value)
                            }
                          />
                          <button
                            type="button"
                            onClick={() =>
                              setShowTransferPasswordInput((prev) => !prev)
                            }
                            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white p-2 touch-manipulation transition-colors duration-200"
                          >
                            {showTransferPasswordInput ? (
                              <EyeOff size={20} />
                            ) : (
                              <Eye size={20} />
                            )}
                          </button>
                        </div>
                        {transferPassword !== confirmTransferPassword &&
                          confirmTransferPassword && (
                            <p className="mt-1.5 text-xs text-red-400">
                              Passwords do not match
                            </p>
                          )}
                      </div>

                      <div className="pt-2">
                        <div className="relative pt-1">
                          <div className="flex mb-2 items-center justify-between">
                            <div>
                              <span className="text-xs font-semibold inline-block text-gray-400">
                                Password Strength
                              </span>
                            </div>
                            <div className="text-right">
                              <span className="text-xs font-semibold inline-block text-gray-400">
                                {!transferPassword
                                  ? "None"
                                  : checkPasswordStrength(transferPassword)
                                      .score <= 1
                                  ? "Very Weak"
                                  : checkPasswordStrength(transferPassword)
                                      .score === 2
                                  ? "Weak"
                                  : checkPasswordStrength(transferPassword)
                                      .score === 3
                                  ? "Moderate"
                                  : checkPasswordStrength(transferPassword)
                                      .score === 4
                                  ? "Good"
                                  : "Strong"}
                              </span>
                            </div>
                          </div>
                          <div className="overflow-y-auto hide-scrollbar h-2 mb-4 text-xs flex rounded-full bg-[#393939]">
                            <div
                              style={{
                                width: `${
                                  transferPassword
                                    ? checkPasswordStrength(transferPassword)
                                        .score * 20
                                    : 0
                                }%`,
                              }}
                              className={`shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center transition-all duration-500 ${
                                !transferPassword
                                  ? "bg-gray-600"
                                  : checkPasswordStrength(transferPassword)
                                      .score <= 1
                                  ? "bg-red-500"
                                  : checkPasswordStrength(transferPassword)
                                      .score === 2
                                  ? "bg-orange-500"
                                  : checkPasswordStrength(transferPassword)
                                      .score === 3
                                  ? "bg-yellow-500"
                                  : checkPasswordStrength(transferPassword)
                                      .score === 4
                                  ? "bg-green-500"
                                  : "bg-blue-500"
                              }`}
                            ></div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  // Disabling Transfer Password
                  <div className="space-y-5">
                    <div className="bg-[#2d1e1e] p-4 rounded-xl border border-[#4d2c2c]">
                      <div className="flex items-start gap-3">
                        <AlertTriangle className="text-red-400 h-5 w-5 flex-shrink-0 mt-0.5" />
                        <p className="text-sm text-gray-300">
                          To disable transfer password protection, please enter
                          your wallet password for verification.
                        </p>
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <label className="block text-sm font-medium text-gray-300 mb-1.5">
                        Wallet Password
                      </label>
                      <div className="relative group">
                        <input
                          type="password"
                          placeholder="Enter your wallet password"
                          className="w-full p-3.5 pl-4 border border-gray-700 rounded-full bg-[#1a2234] focus:ring-2 focus:ring-red-500 focus:border-red-500 shadow-sm group-hover:shadow transition-all duration-200 text-white placeholder-gray-400"
                          value={walletPassword}
                          onChange={(e) => setWalletPassword(e.target.value)}
                        />
                      </div>
                    </div>
                  </div>
                )}

                <div className="flex justify-end mt-8">
                  <button
                    onClick={() => {
                      setShowTransferPasswordDialog(false);
                      resetDialogStates();
                    }}
                    className="px-5 py-2.5 border border-gray-600 text-gray-300 rounded-xl hover:bg-gray-700 transition-colors mr-3 min-w-[100px] font-medium"
                  >
                    Cancel
                  </button>

                  <button
                    onClick={confirmTransferPasswordSetup}
                    disabled={
                      !isDisablingFeature &&
                      (!transferPassword ||
                        !confirmTransferPassword ||
                        transferPassword !== confirmTransferPassword ||
                        !checkPasswordStrength(transferPassword).isValid)
                    }
                    className={clsx(
                      "px-5 py-2.5 rounded-full transition-all duration-300 min-w-[100px] font-medium shadow-sm hover:shadow",
                      !isDisablingFeature &&
                        (!transferPassword ||
                          !confirmTransferPassword ||
                          transferPassword !== confirmTransferPassword ||
                          !checkPasswordStrength(transferPassword).isValid)
                        ? "bg-gray-600 text-white cursor-not-allowed opacity-70"
                        : isDisablingFeature
                        ? "bg-red-700 text-white hover:bg-red-800"
                        : "bg-[#6f4bff] text-white hover:bg-[#5b33ff]"
                    )}
                  >
                    {isDisablingFeature ? "Disable" : "Enable"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Daily Limit Dialog - Made responsive */}
        {showDailyLimitDialog && (
          <div className="fixed inset-0 bg-black bg-opacity-80 backdrop-blur-md flex items-center justify-center z-50 p-3 sm:p-4 animate-fadeIn">
            <div className="bg-[#2b2b2b] rounded-3xl shadow-2xl overflow-y-auto hide-scrollbar w-[95%] sm:w-full max-w-md max-h-[90vh] overflow-y-auto hide-scrollbar border border-[#393939] transform transition-all duration-300 scale-100">
              <div className="p-5 sm:p-6 flex justify-between items-center border-b border-[#393939]">
                <div className="flex items-center gap-3 sm:gap-4">
                  <div className="bg-[#203320] p-2.5 sm:p-3 rounded-full">
                    <DollarSign className="text-green-300 h-5 w-5 sm:h-6 sm:w-6" />
                  </div>
                  <h2 className="text-lg sm:text-xl font-bold text-white">
                    {isDisablingFeature
                      ? "Remove Daily Limit"
                      : "Set Daily Transfer Limit"}
                  </h2>
                </div>
                <button
                  onClick={() => {
                    setShowDailyLimitDialog(false);
                    resetDialogStates();
                  }}
                  className="text-gray-400 hover:bg-[#393939] rounded-full p-1.5 transition-all duration-200 transform hover:rotate-90"
                >
                  <X size={22} />
                </button>
              </div>

              <div className="p-6 sm:p-7">
                {!isDisablingFeature ? (
                  // Enabling Daily Limit
                  <div className="space-y-5">
                    <div className="bg-[#232323] p-4 rounded-xl border border-[#393939] mb-4">
                      <div className="flex items-start gap-3">
                        <Info className="text-green-400 h-5 w-5 flex-shrink-0 mt-0.5" />
                        <p className="text-sm text-gray-300">
                          Set a maximum amount that can be transferred from your
                          wallet in a 24-hour period.
                        </p>
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <label className="block text-sm font-medium text-gray-300 mb-1.5">
                        Daily Transfer Limit (CRN)
                      </label>
                      <div className="relative group">
                        <input
                          type="number"
                          min="1"
                          placeholder="Enter amount"
                          value={dailyLimit}
                          onChange={(e) =>
                            setDailyLimit(parseInt(e.target.value) || 0)
                          }
                          className="w-full p-3.5 pl-4 border border-[#393939] rounded-full bg-[#232323] focus:ring-2 focus:ring-green-500 focus:border-green-500 shadow-sm transition-all duration-200 text-white placeholder-gray-500"
                        />
                        <div className="absolute inset-y-0 right-4 flex items-center pointer-events-none">
                          <span className="text-gray-400 font-medium">CRN</span>
                        </div>
                      </div>
                      <p className="text-xs text-gray-400 mt-2">
                        You won't be able to exceed this limit in a 24-hour
                        period.
                      </p>
                    </div>
                  </div>
                ) : (
                  // Disabling Daily Limit
                  <div className="space-y-5">
                    <div className="bg-[#232323] p-4 rounded-xl border border-[#393939] mb-5">
                      <div className="flex items-start gap-3">
                        <AlertTriangle className="text-red-400 h-5 w-5 flex-shrink-0 mt-0.5" />
                        <p className="text-sm text-gray-300">
                          To remove your daily transfer limit, please enter your
                          wallet password for verification.
                        </p>
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <label className="block text-sm font-medium text-gray-300 mb-1.5">
                        Wallet Password
                      </label>
                      <div className="relative group">
                        <input
                          type={showCurrentPassword ? "text" : "password"}
                          placeholder="Enter your password"
                          value={walletPassword}
                          onChange={(e) => setWalletPassword(e.target.value)}
                          className="w-full p-3.5 pl-4 border border-[#393939] rounded-full bg-[#232323] focus:ring-2 focus:ring-red-500 focus:border-red-500 shadow-sm transition-all duration-200 text-white placeholder-gray-500"
                        />
                        <button
                          type="button"
                          onClick={() =>
                            setShowCurrentPassword((prev) => !prev)
                          }
                          className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white transition-all duration-200"
                        >
                          {showCurrentPassword ? (
                            <EyeOff className="h-5 w-5" />
                          ) : (
                            <Eye className="h-5 w-5" />
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                <div className="flex justify-end mt-8">
                  <button
                    onClick={() => {
                      setShowDailyLimitDialog(false);
                      resetDialogStates();
                    }}
                    className="px-5 py-2.5 border border-[#393939] text-gray-300 rounded-xl hover:bg-[#393939] transition-colors mr-3 min-w-[100px] font-medium"
                  >
                    Cancel
                  </button>

                  <button
                    onClick={confirmDailyLimitSetup}
                    disabled={!isDisablingFeature && dailyLimit <= 0}
                    className={clsx(
                      "px-5 py-2.5 rounded-xl transition-all duration-300 min-w-[100px] font-medium shadow-sm hover:shadow",
                      !isDisablingFeature && dailyLimit <= 0
                        ? "bg-gray-600 text-white cursor-not-allowed opacity-70"
                        : isDisablingFeature
                        ? "bg-red-600 text-white hover:bg-red-700"
                        : "bg-green-600 text-white hover:bg-green-700"
                    )}
                  >
                    {isDisablingFeature ? "Remove" : "Set Limit"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Wallet Frozen Dialog - Made responsive */}
        {showWalletFrozenDialog && (
          <div className="fixed inset-0 bg-black bg-opacity-80 backdrop-blur-md flex items-center justify-center z-50 p-3 sm:p-4 animate-fadeIn">
            <div className="bg-white rounded-2xl shadow-xl overflow-y-auto hide-scrollbar w-[95%] sm:w-full max-w-md max-h-[90vh] overflow-y-auto hide-scrollbar">
              <div className="bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-3 sm:px-6 sm:py-4 flex justify-between items-center">
                <div className="flex items-center gap-2 sm:gap-3">
                  <div className="bg-white bg-opacity-20 p-1.5 sm:p-2 rounded-lg">
                    <SnowflakeIcon className="text-white h-5 w-5 sm:h-6 sm:w-6" />
                  </div>
                  <h2 className="text-base sm:text-xl font-bold text-white">
                    Unfreeze Wallet
                  </h2>
                </div>
                <button
                  onClick={() => {
                    setShowWalletFrozenDialog(false);
                    resetDialogStates();
                  }}
                  className="text-white hover:bg-white hover:bg-opacity-20 rounded-full p-1"
                >
                  <X size={20} />
                </button>
              </div>

              <div className="p-6">
                <div className="space-y-4">
                  <div className="bg-cyan-50 p-4 rounded-lg border border-cyan-100 mb-4">
                    <div className="flex items-start gap-3">
                      <Key className="text-cyan-600 h-5 w-5 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-gray-700">
                        Your wallet is currently frozen. To unfreeze it and
                        resume transactions, please enter your wallet password.
                      </p>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Wallet Password
                    </label>
                    <div className="relative">
                      <input
                        type={showCurrentPassword ? "text" : "password"}
                        placeholder="Enter your wallet password"
                        className="w-full p-3.5 pl-4 border border-gray-700 rounded-full bg-[#23304a] focus:ring-2 focus:ring-purple-500 focus:border-purple-500 shadow-sm group-hover:shadow transition-all duration-200 text-white placeholder-gray-400"
                        value={walletPassword}
                        onChange={(e) => setWalletPassword(e.target.value)}
                      />
                      <button
                        type="button"
                        onClick={() => setShowCurrentPassword((prev) => !prev)}
                        className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white p-2 touch-manipulation transition-colors duration-200"
                      >
                        {showCurrentPassword ? (
                          <EyeOff size={20} />
                        ) : (
                          <Eye size={20} />
                        )}
                      </button>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end mt-6">
                  <button
                    onClick={() => {
                      setShowWalletFrozenDialog(false);
                      resetDialogStates();
                    }}
                    className="px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors mr-3 min-w-[80px]"
                  >
                    Cancel
                  </button>

                  <button
                    onClick={confirmWalletUnfreeze}
                    className="px-4 py-2.5 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors min-w-[80px]"
                  >
                    Unfreeze Wallet
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Unified Account Management Card - Replacing Feature Configuration Cards */}
        {/* Entire Account Management Section Removed */}

        {/* Additional footer notes */}
      </div>

      {/* تم إزالة نافذة رموز النسخ الاحتياطي المنبثقة */}

      {/* نافذة Time-based Access */}
      {showTimeBasedAccessDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-80 backdrop-blur-md flex items-center justify-center z-50 p-3 sm:p-4 animate-fadeIn">
          <div className="bg-[#2b2b2b] rounded-3xl shadow-2xl overflow-y-auto hide-scrollbar w-[95%] sm:w-full max-w-md max-h-[90vh] overflow-y-auto hide-scrollbar border border-[#393939] transform transition-all duration-300 scale-100">
            <div className="p-5 sm:p-6 flex justify-between items-center border-b border-[#393939]">
              <div className="flex items-center gap-3 sm:gap-4">
                <div className="bg-[#2a2340] p-2.5 sm:p-3 rounded-full">
                  <Clock className="text-indigo-300 h-5 w-5 sm:h-6 sm:w-6" />
                </div>
                <h2 className="text-lg sm:text-xl font-bold text-white">
                  {isDisablingFeature
                    ? "Disable Time-based Access"
                    : "Set Time-based Access"}
                </h2>
              </div>
              <button
                onClick={() => {
                  setShowTimeBasedAccessDialog(false);
                  resetDialogStates();
                }}
                className="text-gray-400 hover:bg-[#393939] rounded-full p-1.5 transition-all duration-200 transform hover:rotate-90"
              >
                <X size={22} />
              </button>
            </div>

            <div className="p-4 space-y-4">
              <div className="bg-[#232323] p-4 rounded-xl border border-[#393939]">
                <div className="flex items-start gap-3">
                  <Info className="text-blue-400 h-5 w-5 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-gray-300">
                    Limit wallet access to specific times during the day. Your
                    wallet will be inaccessible outside these hours.
                  </p>
                </div>
              </div>

              <div className="space-y-5">
                <div className="space-y-1.5">
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">
                    Start Time (24-hour format)
                  </label>
                  <input
                    type="time"
                    className="w-full p-3 pl-4 border border-[#393939] rounded-full bg-[#232323] focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 shadow-sm transition-all duration-200 text-white"
                    value={timeRange.startTime}
                    onChange={(e) => setTimeRange({...timeRange, startTime: e.target.value})}
                  />
                  <div className="text-xs text-gray-400 mt-1 pl-2">
                    {timeRange.startTime ? formatTo12Hour(timeRange.startTime) : ""}
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">
                    End Time (24-hour format)
                  </label>
                  <input
                    type="time"
                    className="w-full p-3 pl-4 border border-[#393939] rounded-full bg-[#232323] focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 shadow-sm transition-all duration-200 text-white"
                    value={timeRange.endTime}
                    onChange={(e) => setTimeRange({...timeRange, endTime: e.target.value})}
                  />
                  <div className="text-xs text-gray-400 mt-1 pl-2">
                    {timeRange.endTime ? formatTo12Hour(timeRange.endTime) : ""}
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">
                    Timezone
                  </label>
                  <select
                    className="w-full p-3 pl-4 border border-[#393939] rounded-full bg-[#232323] focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 shadow-sm transition-all duration-200 text-white"
                    value={selectedTimezone}
                    onChange={(e) => setSelectedTimezone(e.target.value)}
                  >
                    {getCommonTimezones().map((tz) => (
                      <option key={tz} value={tz}>
                        {tz.replace(/_/g, ' ')}
                      </option>
                    ))}
                  </select>
                  <div className="text-xs text-gray-400 mt-1 pl-2">
                    Your local timezone will be used to determine access
                  </div>
                </div>
              </div>

              <div className="flex justify-end pt-2 space-x-3">
                <button
                  onClick={() => {
                    setShowTimeBasedAccessDialog(false);
                    resetDialogStates();
                  }}
                  className="px-5 py-2.5 border border-[#393939] text-gray-300 rounded-xl hover:bg-[#393939] transition-colors min-w-[100px] font-medium"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmTimeBasedAccessSetup}
                  className="px-5 py-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition-colors min-w-[100px] font-medium"
                >
                  {isDisablingFeature ? "Disable" : "Enable"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Auto Sign-In Dialog */}
      {showAutoSignInDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-80 backdrop-blur-md flex items-center justify-center z-50 p-3 sm:p-4 animate-fadeIn">
          <div className="bg-[#2b2b2b] rounded-3xl shadow-2xl overflow-y-auto hide-scrollbar w-[95%] sm:w-full max-w-md max-h-[90vh] overflow-y-auto hide-scrollbar border border-[#393939] transform transition-all duration-300 scale-100">
            <div className="p-5 sm:p-6 flex justify-between items-center border-b border-[#393939]">
              <div className="flex items-center gap-3 sm:gap-4">
                <div className="bg-[#3a1f29] p-2.5 sm:p-3 rounded-full">
                  <LogIn className="text-pink-300 h-5 w-5 sm:h-6 sm:w-6" />
                </div>
                <h2 className="text-lg sm:text-xl font-bold text-white">
                  {isDisablingFeature
                    ? "Disable Auto Sign-In"
                    : "Set Auto Sign-In"}
                </h2>
              </div>
              <button
                onClick={() => {
                  setShowAutoSignInDialog(false);
                  resetDialogStates();
                }}
                className="text-gray-400 hover:bg-[#393939] rounded-full p-1.5 transition-all duration-200 transform hover:rotate-90"
              >
                <X size={22} />
              </button>
            </div>

            <div className="p-4 space-y-4">
              <div className="bg-[#232323] p-4 rounded-xl border border-[#393939]">
                <div className="flex items-start gap-3">
                  <Info className="text-blue-400 h-5 w-5 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-gray-300">
                    Stay signed in for a specific time period without requiring
                    authentication on each visit.
                  </p>
                </div>
              </div>

              <div className="space-y-5">
                <div className="space-y-1.5">
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">
                    Keep me signed in for:
                  </label>
                  {/* Replace fixed text with dropdown selection */}
                  <select
                    value={autoSignInDuration}
                    onChange={(e) => setAutoSignInDuration(Number(e.target.value))}
                    disabled={isDisablingFeature}
                    className="w-full p-3 pl-4 border border-[#393939] rounded-full bg-[#232323] text-white appearance-none"
                  >
                    <option value={7}>7 days</option>
                    <option value={14}>14 days</option>
                    <option value={20}>20 days</option>
                    <option value={30}>30 days</option>
                    <option value={60}>60 days</option>
                    <option value={90}>90 days</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end pt-2 space-x-3">
                <button
                  onClick={() => {
                    setShowAutoSignInDialog(false);
                    resetDialogStates();
                  }}
                  className="px-5 py-2.5 border border-[#393939] text-gray-300 rounded-xl hover:bg-[#393939] transition-colors min-w-[100px] font-medium"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmAutoSignInSetup}
                  className="px-5 py-2.5 bg-pink-600 text-white rounded-xl hover:bg-pink-700 transition-colors min-w-[100px] font-medium"
                >
                  {isDisablingFeature ? "Disable" : "Enable"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Geo-Lock Dialog */}
      {showGeoLockDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-80 backdrop-blur-md flex items-center justify-center z-50 p-3 sm:p-4 animate-fadeIn">
          <div className="bg-[#2b2b2b] rounded-3xl shadow-2xl overflow-y-auto hide-scrollbar w-[95%] sm:w-full max-w-md max-h-[90vh] overflow-y-auto hide-scrollbar border border-[#393939] transform transition-all duration-300 scale-100">
            <div className="p-5 sm:p-6 flex justify-between items-center border-b border-[#393939] sticky top-0 bg-[#2b2b2b] z-10">
              <div className="flex items-center gap-3 sm:gap-4">
                <div className="bg-[#1a2f2f] p-2.5 sm:p-3 rounded-full">
                  <MapPin className="text-teal-300 h-5 w-5 sm:h-6 sm:w-6" />
                </div>
                <h2 className="text-lg sm:text-xl font-bold text-white">
                  {isGeoLockEnabled
                    ? "Disable Geographic Restriction"
                    : "Enable Geographic Restriction"}
                </h2>
              </div>
              <button
                onClick={() => {
                  setShowGeoLockDialog(false);
                  resetDialogStates();
                }}
                className="text-gray-400 hover:bg-[#393939] rounded-full p-1.5 transition-all duration-200 transform hover:rotate-90"
              >
                <X size={22} />
              </button>
            </div>

            <div className="px-5 py-4 space-y-5 bg-[#2b2b2b]">
              <div className="bg-[#232323] p-4 rounded-xl border border-[#393939]">
                <div className="flex items-start gap-3">
                  <Info className="text-blue-400 h-5 w-5 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-gray-300">
                    Restrict wallet access to your specified country. 
                    You can access your wallet from anywhere within {geoLockCountry || 'your country'}, 
                    but attempts from other countries will be blocked.
                  </p>
                </div>
              </div>

              <div className="h-56 sm:h-64 md:h-72 lg:h-80 rounded-xl overflow-hidden border border-[#393939] relative">
                {/* Map and IP details section */}
                <div className="absolute inset-0 bg-[#1a1a1a] flex items-center justify-center">
                  {scanResults ? (
                    <div className="flex flex-col w-full h-full">
                      <div className="bg-[#232323] w-full p-3 text-center border-b border-[#393939]">
                        <div className="flex justify-between items-center">
                          <span className="text-teal-400 font-medium text-lg">{scanResults.country_name || scanResults.country}</span>
                          <button 
                            onClick={() => {
                              // Clear scan results and reset
                              setScanResults(null);
                              setGeoLockCountry("");
                              setGeoLockLocation("");
                              setGeoLockCoordinates({ lat: 0, lng: 0 });
                            }}
                            className="text-gray-400 hover:text-white"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                      
                      <div className="flex-1 overflow-y-auto p-4">
                        {/* Country Map placeholder - would be replaced with actual map in production */}
                        <div className="bg-[#232323] rounded-lg mb-4 p-3 flex items-center justify-center h-32 border border-[#393939]">
                          <Globe className="text-teal-500 w-16 h-16" />
                        </div>
                        
                                        {/* Location Details */}
                         <div className="bg-[#232323] rounded-lg p-4 border border-[#393939]">
                           <h3 className="text-white text-lg mb-3 flex items-center">
                             <Shield className="w-4 h-4 mr-2 text-teal-400" /> Location Details
                           </h3>
                           
                           <div className="space-y-3 text-sm">
                             <div className="flex justify-between">
                               <span className="text-gray-400">IP Address:</span>
                               <span className="text-white font-mono">{scanResults.ip_address}</span>
                             </div>
                             <div className="flex justify-between">
                               <span className="text-gray-400">Country:</span>
                               <span className="text-white">{scanResults.country_name || scanResults.country}</span>
                             </div>
                             <div className="flex justify-between">
                               <span className="text-gray-400">Region:</span>
                               <span className="text-white">{scanResults.region || "-"}</span>
                             </div>
                             <div className="flex justify-between">
                               <span className="text-gray-400">City:</span>
                               <span className="text-white">{scanResults.city || "-"}</span>
                             </div>
                             <div className="flex justify-between">
                               <span className="text-gray-400">Timezone:</span>
                               <span className="text-white">{scanResults.timezone || "-"}</span>
                             </div>
                             <div className="flex justify-between">
                               <span className="text-gray-400">Coordinates:</span>
                               <span className="text-white font-mono">{scanResults.location || "-"}</span>
                             </div>
                           </div>
                           
                           {/* Display existing allowed countries */}
                           {allowedCountries.length > 0 && (
                             <div className="mt-4 border-t border-[#393939] pt-4">
                               <h4 className="text-white text-sm font-medium mb-2 flex items-center">
                                 <Globe className="w-3.5 h-3.5 mr-1.5 text-teal-400" /> Allowed Countries
                               </h4>
                               <div className="space-y-2 mt-2 max-h-28 overflow-y-auto hide-scrollbar">
                                 {allowedCountries.map(country => (
                                   <div key={country.country_code} 
                                        className="flex items-center justify-between bg-[#1a1a1a] p-2 rounded">
                                     <span className="text-white text-xs">
                                       {country.country_name || country.country_code}
                                     </span>
                                     <button
                                       onClick={() => {
                                         // Call API to remove country
                                         fetch("/api/security/geo-lock/remove-country", {
                                           method: "POST",
                                           headers: {
                                             "Content-Type": "application/json"
                                           },
                                           body: JSON.stringify({
                                             country_code: country.country_code
                                           })
                                         })
                                         .then(response => response.json())
                                         .then(data => {
                                           if (data.error) {
                                             showCustomAlert(data.error, "error");
                                           } else {
                                             // Update local state
                                             const updated = allowedCountries.filter(
                                               c => c.country_code !== country.country_code
                                             );
                                             setAllowedCountries(updated);
                                             
                                             // Select another country if current was removed
                                             if (geoLockCountry === country.country_code && updated.length > 0) {
                                               const firstCountry = updated[0];
                                               setGeoLockCountry(firstCountry.country_code);
                                               setGeoLockLocation(firstCountry.country_name);
                                               setGeoLockCoordinates(firstCountry.coordinates || { lat: 0, lng: 0 });
                                             }
                                             
                                             showCustomAlert(`${country.country_name || country.country_code} removed from allowed countries`, "success");
                                           }
                                         })
                                         .catch(error => {
                                           console.error("Error removing country:", error);
                                           showCustomAlert("Failed to remove country. Please try again.", "error");
                                         });
                                       }}
                                       className="text-gray-400 hover:text-white p-1"
                                       aria-label="Remove country"
                                     >
                                       <X className="w-3.5 h-3.5" />
                                     </button>
                                   </div>
                                 ))}
                               </div>
                             </div>
                           )}
                          
                                                     {/* Add to Geo-Lock button */}
                           <button
                             onClick={() => {
                               // Prepare country data
                               const countryCode = scanResults.country || "";
                               const countryName = scanResults.country_name || scanResults.country || "";
                               let coordinates = scanResults.coordinates || { lat: 0, lng: 0 };
                               
                               if (!coordinates.lat && scanResults.location) {
                                 try {
                                   const [lat, lng] = scanResults.location.split(',').map((c: string) => parseFloat(c.trim()));
                                   coordinates = { lat, lng };
                                 } catch (error) {
                                   console.error("Error parsing coordinates:", error);
                                 }
                               }
                               
                               // Check if country already exists in list
                               const exists = allowedCountries.some(c => c.country_code === countryCode);
                               
                               if (exists) {
                                 showCustomAlert(`${countryName || countryCode} is already in your allowed countries list`, "success");
                               } else {
                                 // Add to allowed countries
                                 const newCountry = {
                                   country_code: countryCode,
                                   country_name: countryName,
                                   coordinates
                                 };
                                 
                                 // Update local state
                                 setAllowedCountries([...allowedCountries, newCountry]);
                                 setGeoLockCountry(countryCode);
                                 setGeoLockLocation(countryName);
                                 setGeoLockCoordinates(coordinates);
                                 
                                 // Call API to update on server
                                 fetch("/api/security/geo-lock/add-country", {
                                   method: "POST",
                                   headers: {
                                     "Content-Type": "application/json"
                                   },
                                   body: JSON.stringify({
                                     country_code: countryCode,
                                     country_name: countryName,
                                     coordinates
                                   })
                                 })
                                 .then(response => response.json())
                                 .then(data => {
                                   if (data.error) {
                                     showCustomAlert(data.error, "error");
                                   } else {
                                     showCustomAlert(`${countryName || countryCode} added to your allowed countries`, "success");
                                   }
                                 })
                                 .catch(error => {
                                   console.error("Error adding country:", error);
                                   showCustomAlert("Failed to add country. Please try again.", "error");
                                 });
                               }
                             }}
                             className="w-full mt-4 bg-teal-600 hover:bg-teal-700 text-white py-2 rounded-lg flex items-center justify-center"
                           >
                             <Shield className="w-4 h-4 mr-2" /> Add This Country
                           </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center">
                      <div className="text-center mb-6">
                        <Globe className="w-16 h-16 text-teal-500/50 mx-auto mb-4" />
                        <h3 className="text-white text-lg mb-2">Country-Level Protection</h3>
                        <p className="text-gray-400 text-sm max-w-xs">
                          Restrict wallet access to your country.<br/>
                          Any access attempts from other countries will be blocked.
                        </p>
                      </div>
                      
                      <button 
                        onClick={() => {
                          showCustomAlert("Detecting your location...", "success");
                          
                          // Clear any previous value
                          setGeoLockCountry("");
                          
                          // Make API call to detect country
                          fetch("/api/security/detect-country", {
                            method: "GET",
                            headers: {
                              "Content-Type": "application/json",
                              "Cache-Control": "no-cache"
                            }
                          })
                          .then(response => response.json())
                          .then(data => {
                            if (data.error) {
                              showCustomAlert(data.error, "error");
                            } else {
                              // Store full scan results
                              setScanResults(data);
                              showCustomAlert(`Location detected: ${data.country_name || data.country}`, "success");
                            }
                          })
                          .catch(error => {
                            console.error("Error detecting country:", error);
                            showCustomAlert("Failed to detect your location. Please try again.", "error");
                          });
                        }}
                        className="px-6 py-3 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors font-medium flex items-center shadow-lg"
                      >
                        <MapPin className="w-5 h-5 mr-2" /> Scan My Location
                      </button>
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Your Protected Country
                </label>
                <input
                  type="text"
                  placeholder="Country will be detected automatically"
                  className="w-full p-3.5 pl-4 border border-[#393939] rounded-full bg-[#232323] focus:ring-2 focus:ring-teal-500 focus:border-teal-500 shadow-sm transition-all duration-200 text-white placeholder-gray-500"
                  value={geoLockCountry}
                  readOnly
                />
              </div>

              <div className="flex justify-end gap-3">
                <button
                  onClick={() => {
                    setShowGeoLockDialog(false);
                    resetDialogStates();
                  }}
                  className="px-5 py-2.5 border border-[#393939] text-gray-300 rounded-full hover:bg-[#393939] transition-colors min-w-[100px] font-medium"
                >
                  Cancel
                </button>
                
                {isGeoLockEnabled && !isDisablingFeature && (
                  <button
                    onClick={() => {
                      setIsDisablingFeature(true);
                    }}
                    className="px-5 py-2.5 bg-red-600 text-white rounded-full hover:bg-red-700 transition-colors min-w-[100px] font-medium"
                  >
                    Disable
                  </button>
                )}
                
                <button
                  onClick={confirmGeoLockSetup}
                  className={clsx(
                    "px-5 py-2.5 rounded-full transition-all duration-300 min-w-[100px] font-medium shadow-sm hover:shadow",
                    isDisablingFeature
                      ? "bg-red-600 text-white hover:bg-red-700"
                      : "bg-teal-600 text-white hover:bg-teal-700"
                  )}
                  disabled={!isDisablingFeature && !geoLockCountry}
                >
                  {isDisablingFeature ? "Confirm Disable" : "Enable"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* IP Whitelist Dialog */}
      {showIpWhitelistDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-80 backdrop-blur-md flex items-center justify-center z-50 p-3 sm:p-4 animate-fadeIn">
          <div className="bg-[#2b2b2b] rounded-3xl shadow-2xl overflow-y-auto hide-scrollbar w-[95%] sm:w-full max-w-md max-h-[90vh] overflow-y-auto hide-scrollbar border border-[#393939] transform transition-all duration-300 scale-100">
            <div className="p-5 sm:p-6 flex justify-between items-center border-b border-[#393939]">
              <div className="flex items-center gap-3 sm:gap-4">
                <div
                  className={`p-2.5 sm:p-3 rounded-full ${
                    isDisablingFeature ? "bg-[#2d1e1e]" : "bg-[#2a2340]"
                  }`}
                >
                  <Shield
                    className={`h-5 w-5 sm:h-6 sm:w-6 ${
                      isDisablingFeature ? "text-red-300" : "text-purple-300"
                    }`}
                  />
                </div>
                <h2 className="text-lg sm:text-xl font-bold text-white">
                  {isDisablingFeature
                    ? "Disable IP Whitelist"
                    : "Set IP Whitelist"}
                </h2>
              </div>
              <button
                onClick={() => {
                  setShowIpWhitelistDialog(false);
                  resetDialogStates();
                }}
                className="text-gray-400 hover:bg-[#393939] rounded-full p-1.5 transition-all duration-200 transform hover:rotate-90"
              >
                <X size={22} />
              </button>
            </div>

            <div className="px-5 py-4 space-y-5 bg-[#2b2b2b]">
              <div className="bg-[#232323] p-4 rounded-xl border border-[#393939]">
                <div className="flex items-start gap-3">
                  <Info className="text-blue-400 h-5 w-5 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-gray-300">
                    Restrict wallet access to approved IP addresses only. Any
                    attempt to access your wallet from other IP addresses will
                    be blocked.
                  </p>
                </div>
              </div>

              {/* IP Scan Results */}
              {ipScanResults.showResults && (
                <div className="bg-[#242438] p-4 rounded-xl border border-[#334155] mb-4 animate-fadeIn">
                  <div className="flex justify-between items-start mb-3">
                    <h3 className="text-md font-medium text-white flex items-center">
                      <Shield className="h-4 w-4 mr-2 text-blue-400" />
                      Current IP Details
                    </h3>
                    <button 
                      onClick={() => setIpScanResults(prev => ({...prev, showResults: false}))}
                      className="text-gray-400 hover:text-white"
                    >
                      <X size={16} />
                    </button>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-gray-400 text-sm">IP Address:</span>
                      <span className="text-white font-medium text-sm">{ipScanResults.ip_address}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400 text-sm">Country:</span>
                      <span className="text-white font-medium text-sm">{ipScanResults.country}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400 text-sm">Region:</span>
                      <span className="text-white font-medium text-sm">{ipScanResults.region}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400 text-sm">City:</span>
                      <span className="text-white font-medium text-sm">{ipScanResults.city}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400 text-sm">Location:</span>
                      <span className="text-white font-medium text-sm">{ipScanResults.location}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400 text-sm">Timezone:</span>
                      <span className="text-white font-medium text-sm">{ipScanResults.timezone}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400 text-sm">Provider:</span>
                      <span className="text-white font-medium text-sm">{ipScanResults.provider}</span>
                    </div>
                  </div>
                  
                  <div className="mt-3 flex justify-end">
                    <button
                      onClick={addIpToWhitelist}
                      className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm rounded-lg flex items-center"
                    >
                      <Plus size={16} className="mr-1" />
                      Add to Whitelist
                    </button>
                  </div>
                </div>
              )}

              <div className="space-y-4">
                <div className="space-y-1.5">
                  <div className="flex justify-between items-center mb-1.5">
                    <label className="block text-sm font-medium text-gray-300">
                      Add IP Address
                    </label>
                    <button
                      onClick={scanCurrentIP}
                      disabled={ipScanResults.scanning}
                      className={`text-xs px-3 py-1 rounded-full transition-colors ${
                        ipScanResults.scanning 
                          ? "bg-gray-700 text-gray-400 cursor-wait" 
                          : "bg-blue-700 text-white hover:bg-blue-800"
                      }`}
                    >
                      {ipScanResults.scanning ? "Scanning..." : "Scan My IP"}
                    </button>
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="e.g. 169.31.178.68"
                      className="w-full p-3.5 pl-4 border border-[#393939] rounded-full bg-[#232323] focus:ring-2 focus:ring-purple-500 focus:border-purple-500 shadow-sm transition-all duration-200 text-white placeholder-gray-500"
                      value={newIpAddress}
                      onChange={(e) => setNewIpAddress(e.target.value)}
                    />
                    <button
                      onClick={addIpToWhitelist}
                      className="flex-shrink-0 bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-full w-12 h-12 flex items-center justify-center transition-colors"
                    >
                      <Plus size={20} />
                    </button>
                  </div>
                </div>

                <div className="space-y-2.5">
                  <h3 className="text-md font-medium text-white">
                    Approved IP Addresses
                  </h3>
                  {ipWhitelist.length === 0 ? (
                    <div className="text-center py-4 border border-[#393939] rounded-xl bg-[#232323]">
                      <p className="text-gray-400">No IP addresses added yet</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {ipWhitelist.map((ip) => (
                        <div
                          key={ip}
                          className="flex items-center justify-between bg-[#232323] border border-[#393939] p-3 rounded-xl"
                        >
                          <span className="text-white font-mono">{ip}</span>
                          <button
                            onClick={() => removeIpFromWhitelist(ip)}
                            className="text-gray-400 hover:text-white"
                          >
                            <X size={18} />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="bg-[#232323] p-4 rounded-xl border border-[#393939]">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="text-yellow-500 h-5 w-5 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-gray-300">
                    Make sure to add your current IP address to the list,
                    otherwise you might block yourself from accessing your
                    wallet.
                  </p>
                </div>
              </div>

              <div className="flex justify-end gap-3">
                <button
                  onClick={() => {
                    setShowIpWhitelistDialog(false);
                    setIsDisablingFeature(false);
                    resetDialogStates();
                  }}
                  className="px-5 py-2.5 border border-[#393939] text-gray-300 rounded-full hover:bg-[#393939] transition-colors min-w-[100px] font-medium"
                >
                  Cancel
                </button>
                {isIpWhitelistEnabled && !isDisablingFeature && (
                  <button
                    onClick={() => {
                      setIsDisablingFeature(true);
                    }}
                    className="px-5 py-2.5 bg-red-600 text-white rounded-full hover:bg-red-700 transition-colors min-w-[100px] font-medium"
                  >
                    Disable
                  </button>
                )}
                <button
                  onClick={confirmIpWhitelistSetup}
                  className={clsx(
                    "px-5 py-2.5 rounded-full transition-all duration-300 min-w-[100px] font-medium shadow-sm hover:shadow",
                    isDisablingFeature
                      ? "bg-red-600 text-white hover:bg-red-700"
                      : "bg-purple-600 text-white hover:bg-purple-700"
                  )}
                  disabled={!isDisablingFeature && ipWhitelist.length === 0}
                >
                  {isDisablingFeature ? "Confirm Disable" : "Enable"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <CustomAlert />
      {/* Devices management handled by separate DevicesList component */}
      <FinalConfirmationDialog />

      {/* مكون لإدخال الكلمات المعيارية - نستخدمه لتفادي خطأ عدم استخدام handleMnemonicInput */}
      {showFinalConfirmation && (
        <div className="hidden">
          <textarea onChange={handleMnemonicInput} value={mnemonicPhrase} />
        </div>
      )}

      {/* Devices List Modal */}
      <DevicesList 
        isOpen={showDevicesDialog}
        onClose={() => setShowDevicesDialog(false)}
      />

      {/* Security Alerts Dialog */}
      {showSecurityAlertsDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-80 backdrop-blur-md flex items-center justify-center z-50 p-3 sm:p-4 animate-fadeIn">
          <div className="bg-[#2b2b2b] rounded-3xl shadow-2xl overflow-y-auto hide-scrollbar w-[95%] sm:w-full max-w-md max-h-[90vh] overflow-y-auto hide-scrollbar border border-[#393939] transform transition-all duration-300 scale-100">
            <div className="p-5 sm:p-6 flex justify-between items-center border-b border-[#393939]">
              <div className="flex items-center gap-3 sm:gap-4">
                <div className="bg-[#2a2323] p-2.5 sm:p-3 rounded-full">
                  <AlertTriangle className="text-red-400 h-5 w-5 sm:h-6 sm:w-6" />
                </div>
                <h2 className="text-lg sm:text-xl font-bold text-white">
                  Security Alerts
                </h2>
              </div>
              <button
                onClick={() => setShowSecurityAlertsDialog(false)}
                className="text-gray-400 hover:bg-[#393939] rounded-full p-1.5 transition-all duration-200 transform hover:rotate-90"
              >
                <X size={22} />
              </button>
            </div>

            <div className="p-5 space-y-4">
              <div className="bg-[#232323] p-4 rounded-xl border border-[#393939]">
                <div className="flex items-start gap-3">
                  <Info className="text-blue-400 h-5 w-5 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-gray-300">
                    The following security features are recommended for premium accounts.
                    You can enable these features or clear the alerts.
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                {walletData?.security?.securityFeatures?.map((feature, index) => (
                  <div key={index} className="bg-[#232323] p-3 rounded-lg border border-[#393939] flex items-center justify-between">
                    <div className="flex items-center">
                      <Shield className="text-amber-400 h-5 w-5 mr-2" />
                      <span className="text-white">{feature}</span>
                    </div>
                    
                    {feature === "Time-Based Access" && (
                      <button
                        onClick={() => {
                          setShowSecurityAlertsDialog(false);
                          setShowTimeBasedAccessDialog(true);
                        }}
                        className="py-1 px-3 bg-indigo-600 hover:bg-indigo-700 text-white text-xs rounded-full transition-colors"
                      >
                        Enable
                      </button>
                    )}
                    
                    {feature === "Geo-Lock" && (
                      <button
                        onClick={() => {
                          setShowSecurityAlertsDialog(false);
                          setShowGeoLockDialog(true);
                        }}
                        className="py-1 px-3 bg-teal-600 hover:bg-teal-700 text-white text-xs rounded-full transition-colors"
                      >
                        Enable
                      </button>
                    )}
                    
                    {feature === "IP Whitelist" && (
                      <button
                        onClick={() => {
                          setShowSecurityAlertsDialog(false);
                          setShowIpWhitelistDialog(true);
                        }}
                        className="py-1 px-3 bg-purple-600 hover:bg-purple-700 text-white text-xs rounded-full transition-colors"
                      >
                        Enable
                      </button>
                    )}
                  </div>
                ))}
              </div>

              <div className="flex justify-end space-x-3 pt-3">
                <button
                  onClick={() => setShowSecurityAlertsDialog(false)}
                  className="px-4 py-2 border border-[#393939] text-gray-300 rounded-lg hover:bg-[#393939] transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={clearSecurityAlerts}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                >
                  Clear Alerts
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Security;


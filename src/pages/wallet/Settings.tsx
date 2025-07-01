import React, { useState, useEffect, useRef } from "react";
import {
  Database,
  Shield,
  AlertCircle,
  Info,
  CheckCircle,
  X,
  Clock,
  RefreshCw,
  FileCheck,
  Lock,
  Eye,
  EyeOff,
  Key,
  AlertTriangle,
  Copy,
  ChevronRight,
  Settings as SettingsIcon,
  UserX2,
  SnowflakeIcon,
  LockIcon,
  Smartphone,
  Fingerprint,
  Check,
  KeySquare,
} from "lucide-react";
import clsx from "clsx";
import axios from "axios";

interface BackupStatus {
  status: "up to date" | "outdated" | "critical" | "never" | "unknown";
  lastBackup: string | null;
  daysAgo: number | null;
  message: string;
  canCreateBackup: boolean;
  timeRemaining?: number;
  formattedTimeRemaining?: string;
  daysRemaining?: number;
}

interface BackupData {
  field: string;
  value: string;
  isEncrypted: boolean;
}

interface BackupResponse {
  backupData: BackupData[];
  timestamp: string;
  lastBackup: string;
}

interface RateLimitError {
  isLimited: boolean;
  message: string;
  timeRemaining: number;
  formattedTime: string;
  type: "cooldown" | "attempts";
}

const CustomAlert = ({
  showAlert,
  alertMessage,
  alertType,
  setShowAlert,
}: {
  showAlert: boolean;
  alertMessage: string;
  alertType: "success" | "error" | "info";
  setShowAlert: (value: boolean) => void;
}) => {
  // Add a safety check - return null without further processing if not showing
  if (!showAlert) return null;

  // Use a ref to prevent any unmounting issues
  const alertRef = React.useRef<HTMLDivElement>(null);
  
  // Use effect for safe cleanup - ensures proper removal of DOM elements
  React.useEffect(() => {
    if (!showAlert) return;
    
    // Auto-dismiss after 10 seconds to prevent stale UI
    const timer = setTimeout(() => {
      setShowAlert(false);
    }, 10000);
    
    return () => {
      clearTimeout(timer);
    };
  }, [showAlert, setShowAlert]);
  
  // Handle close safely
  const handleClose = React.useCallback(() => {
    // Use a safer approach to hide first, then remove
    if (alertRef.current) {
      alertRef.current.style.opacity = '0';
      setTimeout(() => setShowAlert(false), 300);
    } else {
      setShowAlert(false);
    }
  }, [setShowAlert]);

  return (
    <div 
      ref={alertRef}
      className="fixed inset-0 bg-black bg-opacity-80 backdrop-blur-md flex items-center justify-center z-50 p-3 sm:p-4 animate-fadeIn transition-opacity duration-300"
      key={`alert-${Date.now()}`} // Ensure unique key for proper mounting/unmounting
    >
      <div className="bg-[#1e2839] rounded-3xl shadow-2xl overflow-hidden w-[95%] sm:w-full max-w-xs sm:max-w-md">
        <div
          className={`px-5 py-4 sm:px-6 sm:py-5 flex justify-between items-center border-b border-gray-700`}
        >
          <div className="flex items-center gap-3 sm:gap-4">
            <div
              className={`p-2.5 sm:p-3 rounded-full ${
                alertType === "success"
                  ? "bg-green-900/40"
                  : alertType === "error"
                  ? "bg-red-900/40"
                  : "bg-blue-900/40"
              }`}
            >
              {alertType === "success" ? (
                <CheckCircle className="text-green-400 h-5 w-5 sm:h-6 sm:w-6" />
              ) : alertType === "error" ? (
                <AlertTriangle className="text-red-400 h-5 w-5 sm:h-6 sm:w-6" />
              ) : (
                <Info className="text-blue-400 h-5 w-5 sm:h-6 sm:w-6" />
              )}
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-white">
              {alertType === "success"
                ? "Success"
                : alertType === "error"
                ? "Warning"
                : "Information"}
            </h2>
          </div>
          <button
            onClick={handleClose}
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
              onClick={handleClose}
              className={`px-5 py-2.5 rounded-full transition-all duration-300 min-w-[100px] font-medium shadow-sm hover:shadow ${
                alertType === "success"
                  ? "bg-green-700 hover:bg-green-800 text-white"
                  : alertType === "error"
                  ? "bg-red-700 hover:bg-red-800 text-white"
                  : "bg-blue-700 hover:bg-blue-800 text-white"
              }`}
            >
              OK
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const Settings = () => {
  const [includeWallet, setIncludeWallet] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [fetchingStatus, setFetchingStatus] = useState(true);
  const [animateBalance, setAnimateBalance] = useState(false);
  const [animateSection, setAnimateSection] = useState(false);
  const [backupCode, setBackupCode] = useState("");
  const [countdown, setCountdown] = useState<string | null>(null);
  const countdownIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const [is2FAEnabled, setIs2FAEnabled] = useState<boolean>(false);
  const [backupStatus, setBackupStatus] = useState<BackupStatus>({
    status: "unknown",
    lastBackup: null,
    daysAgo: null,
    message: "Loading backup status...",
    canCreateBackup: false,
  });
  // Rate limit error state
  const [rateLimitError, setRateLimitError] = useState<RateLimitError>({
    isLimited: false,
    message: "",
    timeRemaining: 0,
    formattedTime: "",
    type: "attempts",
  });
  const rateLimitCountdownRef = useRef<NodeJS.Timeout | null>(null);
  const [notification, setNotification] = useState<{
    show: boolean;
    type: "success" | "error" | "info";
    message: string;
  }>({ show: false, type: "success", message: "" });

  // إضافة الحالات اللازمة لنافذة عرض رموز النسخ الاحتياطي
  const [showBackupCodesModal, setShowBackupCodesModal] = useState(false);
  const [securityPassword, setSecurityPassword] = useState("");
  const [passwordVerified, setPasswordVerified] = useState(false);
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [showAlert, setShowAlert] = useState(false);
  const [alertMessage, setAlertMessage] = useState("");
  const [alertType, setAlertType] = useState<"success" | "error" | "info">(
    "success"
  );
  const [copiedToClipboard, setCopiedToClipboard] = useState(false);

  // حالات إدارة الحساب
  const [selectedAccountOption, setSelectedAccountOption] = useState<
    "change-password" | "delete-account" | "freeze-wallet" | null
  >(null);
  const [isWalletFrozen, setIsWalletFrozen] = useState(false);
  const [walletPassword, setWalletPassword] = useState("");
  const [transferPassword, setTransferPassword] = useState("");
  const [confirmTransferPassword, setConfirmTransferPassword] = useState("");
  const [mnemonicPhrase, setMnemonicPhrase] = useState("");
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [showFinalConfirmation, setShowFinalConfirmation] = useState(false);

  // تغيير تعريف المتغيرات إلى متغيرات حالة للسماح بتحديثها من الخادم
  const [loginAuthMethod, setLoginAuthMethod] = useState("none");
  const [transferAuthMethod, setTransferAuthMethod] = useState("password");

  const [isLoginAuthDropdownOpen, setIsLoginAuthDropdownOpen] = useState(false);
  const [isTransferAuthDropdownOpen, setIsTransferAuthDropdownOpen] =
    useState(false);

  // إضافة متغير لحوار إلغاء التجميد
  const [showUnfreezeDialog, setShowUnfreezeDialog] = useState(false);

  // متغيرات مؤقتة لتخزين الإعدادات قبل حفظها
  const [tempLoginAuthMethod, setTempLoginAuthMethod] = useState("none");
  const [tempTransferAuthMethod, setTempTransferAuthMethod] =
    useState("password");

  // إضافة متغير جديد للتحقق مما إذا كانت البيانات قد تم تحميلها
  const [settingsLoaded, setSettingsLoaded] = useState(false);

  // Add isPremium state
  const [isPremium, setIsPremium] = useState<boolean>(false);

  // CSRF token state
  const [csrfToken, setCsrfToken] = useState<string>("");

  // Fetch CSRF token on mount
  useEffect(() => {
    const fetchCsrfToken = async () => {
      try {
        const response = await fetch("/api/csrf-token", { credentials: "include" });
        if (response.ok) {
          const data = await response.json();
          if (data.success && data.csrf_token) {
            setCsrfToken(data.csrf_token);
          }
        }
      } catch (error) {
        console.error("Error fetching CSRF token:", error);
      }
    };
    fetchCsrfToken();
  }, []);

  // Helper to refresh CSRF token
  const refreshCsrfToken = async () => {
    try {
      const response = await fetch("/api/csrf-token", { credentials: "include" });
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.csrf_token) {
          setCsrfToken(data.csrf_token);
          return data.csrf_token;
        }
      }
    } catch (error) {
      console.error("Error refreshing CSRF token:", error);
    }
    return null;
  };

  // Helper to wrap POST/PUT/DELETE requests with CSRF and retry logic
  const fetchWithCSRF = async (url: string, options: any, retry = true) => {
    // Always include CSRF token if available
    options.headers = {
      ...(options.headers || {}),
      'X-CSRF-Token': csrfToken || ''
    };
    options.credentials = 'include';
    let response = await fetch(url, options);
    if (response.status === 403 && retry) {
      // Try to refresh CSRF token and retry once
      const newToken = await refreshCsrfToken();
      if (newToken) {
        options.headers['X-CSRF-Token'] = newToken;
        response = await fetch(url, options);
      }
    }
    return response;
  };

  // إضافة وظيفة تحميل البيانات عند بدء التشغيل
  useEffect(() => {
    setAnimateBalance(true);

    setTimeout(() => {
      setAnimateSection(true);
    }, 300);

    // تحميل البيانات في وظيفة أسنك مستقلة عند بدء التشغيل
    async function loadInitialData() {
      setIsLoading(true);

      // تعريف دالة تحميل الإعدادات
      const loadSettings = async (retryCount = 0) => {
        try {
          console.log(
            `Attempt to load initial settings (retry: ${retryCount})`
          );
          // استخدام معامل لمنع التخزين المؤقت
          const response = await fetch(
            `/api/security/settings?nocache=${Date.now()}`
          );

          if (response.ok) {
            const data = await response.json();
            console.log("Initial security settings loaded:", data);

            // تعيين حالة المصادقة الثنائية
            setIs2FAEnabled(data.twoFAEnabled || false);
            
            // Check if user is premium
            setIsPremium(data.premium || false);

            // تحديث طرق المصادقة إذا كانت موجودة - التأكد من تحديد الخيارات الصحيحة
            if (data.loginAuthMethod) {
              const loginMethodName = Object.keys(data.loginAuthMethod).find(
                (key) => data.loginAuthMethod[key] === true
              );

              if (loginMethodName) {
                console.log(
                  "Initial load - login auth method:",
                  loginMethodName
                );
                setLoginAuthMethod(loginMethodName);
                setTempLoginAuthMethod(loginMethodName);
              } else {
                console.log(
                  "Initial load - no login auth method found, defaulting to 'none'"
                );
                setLoginAuthMethod("none");
                setTempLoginAuthMethod("none");
              }
            }

            if (data.transferAuthMethod) {
              const transferMethodName = Object.keys(
                data.transferAuthMethod
              ).find((key) => data.transferAuthMethod[key] === true);

              if (transferMethodName) {
                console.log(
                  "Initial load - transfer auth method:",
                  transferMethodName
                );
                setTransferAuthMethod(transferMethodName);
                setTempTransferAuthMethod(transferMethodName);
              } else {
                console.log(
                  "Initial load - no transfer auth method found, defaulting to 'password'"
                );
                setTransferAuthMethod("password");
                setTempTransferAuthMethod("password");
              }
            }

            // تعيين حالة تجميد المحفظة
            setIsWalletFrozen(data.walletFrozen || false);

            return true; // نجاح التحميل
          } else {
            console.error(
              "Error loading initial security settings:",
              await response.text()
            );
            return false; // فشل التحميل
          }
        } catch (error) {
          console.error(
            `Error loading initial data (retry: ${retryCount}):`,
            error
          );
          return false; // فشل التحميل
        }
      };

      // محاولة التحميل حتى 3 مرات
      let success = await loadSettings();

      if (!success && navigator.onLine) {
        // محاولة ثانية بعد 1 ثانية
        console.log("First load attempt failed, retrying in 1 second...");
        await new Promise((resolve) => setTimeout(resolve, 1000));
        success = await loadSettings(1);

        if (!success && navigator.onLine) {
          // محاولة ثالثة بعد 2 ثواني
          console.log("Second load attempt failed, retrying in 2 seconds...");
          await new Promise((resolve) => setTimeout(resolve, 2000));
          success = await loadSettings(2);
        }
      }

      try {
        // تحميل حالة النسخ الاحتياطي بشكل منفصل
        await fetchBackupStatus();
      } catch (error) {
        console.error("Error loading backup status:", error);
      } finally {
        // وضع علامة أن البيانات تم تحميلها بغض النظر عن النتيجة
        setSettingsLoaded(true);
        setIsLoading(false);

        // إذا فشلت محاولات التحميل، نعرض رسالة للمستخدم
        if (!success) {
          setAlertMessage(
            "Failed to load security settings. Please refresh the page or try again later."
          );
          setAlertType("error");
          setShowAlert(true);
        }
      }
    }

    // تشغيل وظيفة تحميل البيانات
    loadInitialData();

    // Clean up interval on component unmount
    return () => {
      if (countdownIntervalRef.current) {
        clearInterval(countdownIntervalRef.current);
      }
      if (rateLimitCountdownRef.current) {
        clearInterval(rateLimitCountdownRef.current);
      }
    };
  }, []);

  // Update countdown timer
  useEffect(() => {
    // Clear any existing interval
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
      countdownIntervalRef.current = null;
    }

    // If there's a time remaining, start a countdown
    if (backupStatus.timeRemaining && backupStatus.timeRemaining > 0) {
      let remainingSeconds = backupStatus.timeRemaining;

      // Initial countdown display
      updateCountdownDisplay(remainingSeconds);

      // Set interval to update countdown every second
      countdownIntervalRef.current = setInterval(() => {
        remainingSeconds -= 1;

        if (remainingSeconds <= 0) {
          // Time's up, clear interval and fetch fresh status
          clearInterval(countdownIntervalRef.current!);
          countdownIntervalRef.current = null;
          fetchBackupStatus();
        } else {
          // Update countdown display
          updateCountdownDisplay(remainingSeconds);
        }
      }, 1000);
    } else {
      setCountdown(null);
    }
  }, [backupStatus.timeRemaining]);

  // Update rate limit countdown timer
  useEffect(() => {
    // Clear any existing interval
    if (rateLimitCountdownRef.current) {
      clearInterval(rateLimitCountdownRef.current);
      rateLimitCountdownRef.current = null;
    }

    // If rate limited, start a countdown
    if (rateLimitError.isLimited && rateLimitError.timeRemaining > 0) {
      let remainingSecs = rateLimitError.timeRemaining;

      // Set interval to update countdown every second
      rateLimitCountdownRef.current = setInterval(() => {
        remainingSecs -= 1;

        if (remainingSecs <= 0) {
          // Time's up, clear interval and remove rate limit
          clearInterval(rateLimitCountdownRef.current!);
          rateLimitCountdownRef.current = null;
          setRateLimitError({
            isLimited: false,
            message: "",
            timeRemaining: 0,
            formattedTime: "",
            type: "attempts",
          });
        } else {
          // Update the rate limit error with new time
          setRateLimitError((prev) => ({
            ...prev,
            timeRemaining: remainingSecs,
            formattedTime: formatRateLimitTime(remainingSecs),
          }));
        }
      }, 1000);
    }

    // Cleanup on unmount
    return () => {
      if (rateLimitCountdownRef.current) {
        clearInterval(rateLimitCountdownRef.current);
      }
    };
  }, [rateLimitError.isLimited, rateLimitError.timeRemaining]);

  // Format rate limit remaining time
  const formatRateLimitTime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    return `${days}d ${hours}h ${minutes}m ${secs}s`;
  };

  // Format and update countdown display
  const updateCountdownDisplay = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    setCountdown(
      `${days}d ${hours.toString().padStart(2, "0")}h ${minutes
        .toString().padStart(2, "0")}m ${secs.toString().padStart(2, "0")}s`
    );
  };

  // Fetch backup status from the server
  const fetchBackupStatus = async () => {
    setFetchingStatus(true);
    try {
      const response = await fetch("/api/backup/status", { credentials: "include" });
      if (response.ok) {
        const data = await response.json();
        setBackupStatus(data);
        
        // Update premium status if available in the response
        if (data.isPremium !== undefined) {
          setIsPremium(data.isPremium);
        }
      } else {
        throw new Error("Failed to fetch backup status");
      }
    } catch (error) {
      console.error("Error fetching backup status:", error);
      setBackupStatus({
        status: "unknown",
        lastBackup: null,
        daysAgo: null,
        message: "Failed to load backup status",
        canCreateBackup: false,
      });
      setNotification({
        show: true,
        type: "error",
        message: "Failed to load backup status. Please try again later.",
      });
    } finally {
      setFetchingStatus(false);
    }
  };

  // تعديل وظيفة fetchLatestSettings لتستخدم نفس الطريقة في تحديث البيانات
  const fetchLatestSettings = async () => {
    try {
      console.log("Fetching latest security settings...");
      setIsLoading(true);

      // Add cache busting parameter to prevent browser caching
      const response = await fetch(`/api/security/settings?t=${Date.now()}`);

      if (response.ok) {
        const data = await response.json();
        console.log("Latest security settings response:", data);

        // Update 2FA status
        setIs2FAEnabled(data.twoFAEnabled || false);

        // طريقة محسنة لتحديد طريقة مصادقة الدخول
        if (data.loginAuthMethod) {
          const loginMethodName = Object.keys(data.loginAuthMethod).find(
            (key) => data.loginAuthMethod[key] === true
          );

          if (loginMethodName) {
            console.log("Found active login auth method:", loginMethodName);
            setLoginAuthMethod(loginMethodName);
            setTempLoginAuthMethod(loginMethodName);
          } else {
            // إذا لم نجد قيمة true، نعتمد على القيمة الافتراضية
            console.log(
              "No active login auth method found, defaulting to 'none'"
            );
            setLoginAuthMethod("none");
            setTempLoginAuthMethod("none");
          }
        }

        // طريقة محسنة لتحديد طريقة مصادقة التحويلات
        if (data.transferAuthMethod) {
          const transferMethodName = Object.keys(data.transferAuthMethod).find(
            (key) => data.transferAuthMethod[key] === true
          );

          if (transferMethodName) {
            console.log(
              "Found active transfer auth method:",
              transferMethodName
            );
            setTransferAuthMethod(transferMethodName);
            setTempTransferAuthMethod(transferMethodName);
          } else {
            // إذا لم نجد قيمة true، نعتمد على القيمة الافتراضية
            console.log(
              "No active transfer auth method found, defaulting to 'password'"
            );
            setTransferAuthMethod("password");
            setTempTransferAuthMethod("password");
          }
        }

        // تحديث حالة تحميل البيانات في حال لم تكن متحققة
        if (!settingsLoaded) {
          setSettingsLoaded(true);
        }
      } else {
        console.error(
          "Error fetching latest security settings:",
          await response.text()
        );
      }
    } catch (error) {
      console.error("Exception fetching latest security settings:", error);
    } finally {
      setIsLoading(false);
    }
  };

  // Add a refresh button to manually update settings
  const refreshSecuritySettings = async () => {
    await fetchLatestSettings();
    showCustomAlert("Security settings updated successfully", "success");
  };

  // تعديل وظيفة fetch2FAStatus للتعامل بشكل أفضل مع البيانات المستلمة
  const fetch2FAStatus = async () => {
    try {
      // أضف حالة التحميل للتغذية المرتدة
      setIsLoading(true);

      // استخدام المسار الصحيح للحصول على إعدادات الأمان
      const response = await fetch("/api/security/settings");

      if (response.ok) {
        const data = await response.json();
        console.log("Security settings response:", data);

        // التحقق من twoFAEnabled في البيانات المستلمة
        setIs2FAEnabled(data.twoFAEnabled || false);

        // طريقة محسنة لتحديد طريقة مصادقة الدخول
        if (data.loginAuthMethod) {
          const loginMethodName = Object.keys(data.loginAuthMethod).find(
            (key) => data.loginAuthMethod[key] === true
          );

          if (loginMethodName) {
            console.log("Found active login auth method:", loginMethodName);
            setLoginAuthMethod(loginMethodName);
            setTempLoginAuthMethod(loginMethodName);
          } else {
            // إذا لم نجد قيمة true، نعتمد على القيمة الافتراضية
            console.log(
              "No active login auth method found, defaulting to 'none'"
            );
            setLoginAuthMethod("none");
            setTempLoginAuthMethod("none");
          }
        }

        // طريقة محسنة لتحديد طريقة مصادقة التحويلات
        if (data.transferAuthMethod) {
          const transferMethodName = Object.keys(data.transferAuthMethod).find(
            (key) => data.transferAuthMethod[key] === true
          );

          if (transferMethodName) {
            console.log(
              "Found active transfer auth method:",
              transferMethodName
            );
            setTransferAuthMethod(transferMethodName);
            setTempTransferAuthMethod(transferMethodName);
          } else {
            // إذا لم نجد قيمة true، نعتمد على القيمة الافتراضية
            console.log(
              "No active transfer auth method found, defaulting to 'password'"
            );
            setTransferAuthMethod("password");
            setTempTransferAuthMethod("password");
          }
        }
      } else {
        console.error(
          "Error fetching security settings:",
          await response.text()
        );
        // الحفاظ على الحالة الحالية في حالة الفشل
      }
    } catch (error) {
      console.error("Error fetching 2FA status:", error);
      // لا تعيد تعيين القيمة إلى false في حالة فشل الطلب، حافظ على الحالة الحالية
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch wallet frozen status from the server
  const fetchWalletFrozenStatus = async () => {
    try {
      const response = await fetch("/api/security/settings");

      if (response.ok) {
        const data = await response.json();
        setIsWalletFrozen(data.walletFrozen || false);

        // تحديث طريقة مصادقة الدخول إذا كانت موجودة في البيانات
        if (data.loginAuthMethod) {
          const loginMethodName = Object.keys(data.loginAuthMethod).find(
            (key) => data.loginAuthMethod[key] === true
          );

          if (loginMethodName) {
            console.log(
              "Wallet frozen check - login auth method:",
              loginMethodName
            );
            setLoginAuthMethod(loginMethodName);
            setTempLoginAuthMethod(loginMethodName);
          } else {
            console.log("Wallet frozen check - no login auth method found");
            setLoginAuthMethod("none");
            setTempLoginAuthMethod("none");
          }
        }

        // تحديث طريقة مصادقة التحويلات إذا كانت موجودة في البيانات
        if (data.transferAuthMethod) {
          const transferMethodName = Object.keys(data.transferAuthMethod).find(
            (key) => data.transferAuthMethod[key] === true
          );

          if (transferMethodName) {
            console.log(
              "Wallet frozen check - transfer auth method:",
              transferMethodName
            );
            setTransferAuthMethod(transferMethodName);
            setTempTransferAuthMethod(transferMethodName);
          } else {
            console.log("Wallet frozen check - no transfer auth method found");
            setTransferAuthMethod("password");
            setTempTransferAuthMethod("password");
          }
        }
      } else {
        console.error(
          "Error fetching wallet frozen status:",
          await response.text()
        );
      }
    } catch (error) {
      console.error("Error fetching wallet frozen status:", error);
    }
  };

  // Handle backup creation and download
  const handleDownloadBackup = async () => {
    if (!backupCode.trim()) {
      setNotification({
        show: true,
        type: "error",
        message: "Please enter a backup code",
      });
      return;
    }

    if (!includeWallet) {
      setNotification({
        show: true,
        type: "error",
        message: "Please select wallet information to include in the backup",
      });
      return;
    }

    // If rate limited, don't proceed
    if (rateLimitError.isLimited) {
      return;
    }

    setIsLoading(true);

    try {
      // Create a form data object for the request - always use txt format
      const formData = {
        backupCode,
        includeWallet
      };

      // Use fetchWithCSRF to make a POST request with CSRF token
      const response = await fetchWithCSRF("/api/backup/create", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData)
      });

      if (!response.ok) {
        // Handle error response
        const errorData = await response.json();
        
        // Handle rate limit error
        if (response.status === 429) {
          setRateLimitError({
            isLimited: true,
            message: errorData.error || "Rate limited, please try again later",
            timeRemaining: errorData.time_remaining || 60,
            formattedTime: errorData.formatted_time_remaining || formatRateLimitTime(errorData.time_remaining || 60),
            type: errorData.days_remaining ? "cooldown" : "attempts",
          });
        } else {
          // Handle other errors
          setNotification({
            show: true,
            type: "error",
            message: errorData.error || "Failed to create backup file",
          });
        }
        return;
      }

      // Get the blob from the response
      const blob = await response.blob();
      
      // Create a URL for the blob
      const url = window.URL.createObjectURL(blob);
      
      // Create a temporary link element
      const link = document.createElement("a");
      link.href = url;
      
      // Generate meaningful filename with timestamp
      const timestamp = new Date().toISOString().replace(/[:.]/g, "-").substring(0, 19);
      let filename = `cryptonel_wallet_backup_${timestamp}.txt`;
      
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      
      // Clean up
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);

      // Show success notification
      setNotification({
        show: true,
        type: "success",
        message: "Wallet backup file downloaded successfully as TXT!",
      });

      // Immediately refresh the backup status to show updated last backup and cooldown
      await fetchBackupStatus();

      // Reset any rate limit errors
      setRateLimitError({
        isLimited: false,
        message: "",
        timeRemaining: 0,
        formattedTime: "",
        type: "attempts",
      });

      // Auto-hide notification after 5 seconds
      setTimeout(() => {
        setNotification((prev) => ({ ...prev, show: false }));
      }, 5000);
    } catch (error) {
      console.error("Error creating backup:", error);
      
      // Handle network errors
      setNotification({
        show: true,
        type: "error",
        message: "Failed to create backup file. Please try again later.",
      });

      // Always refresh backup status to ensure we have the latest state
      try {
        await fetchBackupStatus();
      } catch (e) {
        console.error("Error refreshing backup status after error:", e);
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Handle notification dismissal
  const dismissNotification = () => {
    setNotification((prev) => ({ ...prev, show: false }));
  };

  // Helper function to get appropriate status badge
  const getStatusBadge = (status: string) => {
    switch (status) {
      case "up to date":
        return (
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <span className="text-sm font-medium text-green-700">
              Up to date
            </span>
          </div>
        );
      case "outdated":
        return (
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
            <span className="text-sm font-medium text-yellow-700">
              Outdated
            </span>
          </div>
        );
      case "critical":
        return (
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 bg-red-500 rounded-full"></div>
            <span className="text-sm font-medium text-red-700">Critical</span>
          </div>
        );
      case "never":
        return (
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
            <span className="text-sm font-medium text-gray-700">
              Never backed up
            </span>
          </div>
        );
      default:
        return (
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
            <span className="text-sm font-medium text-blue-700">Unknown</span>
          </div>
        );
    }
  };

  // Backup security indicator component
  const BackupSecurityIndicator = () => {
    // Calculate security score based on backup status
    const getSecurityScore = (): number => {
      switch (backupStatus.status) {
        case "up to date":
          return 100;
        case "outdated":
          return 70;
        case "critical":
          return 30;
        case "never":
          return 10;
        default:
          return 0;
      }
    };

    const score = getSecurityScore();

    // Determine color based on score
    const getColor = () => {
      if (score >= 90) return "bg-green-500";
      if (score >= 60) return "bg-yellow-500";
      if (score >= 30) return "bg-orange-500";
      return "bg-red-500";
    };

    return (
      <div className="w-full mt-4">
        <div className="flex justify-between items-center mb-1">
          <span className="text-xs font-medium text-gray-600">
            Security Strength
          </span>
          <span className="text-xs font-medium text-gray-600">{score}%</span>
        </div>
        <div className="w-full h-2 bg-gray-200 rounded-full">
          <div
            className={`h-2 rounded-full transition-all duration-700 ${getColor()}`}
            style={{ width: `${score}%` }}
          ></div>
        </div>
      </div>
    );
  };

  // إضافة وظيفة عرض رموز النسخ الاحتياطي
  const viewBackupCodes = async () => {
    try {
      setIsLoading(true);
      // First check if user has 2FA and backup codes available
      const response = await fetch("/api/security/settings");
      
      if (response.ok) {
        const data = await response.json();
        if (data.twoFAEnabled) {
          // User has 2FA enabled, proceed to show the modal
    setShowBackupCodesModal(true);
    setPasswordVerified(false);
    setSecurityPassword("");
    setCopiedToClipboard(false);
        } else {
          // User doesn't have 2FA enabled
          showCustomAlert("You need to enable 2FA to have backup codes", "error");
        }
      } else {
        throw new Error("Failed to check 2FA status");
      }
    } catch (error) {
      console.error("Error checking 2FA status:", error);
      showCustomAlert("Error loading 2FA status", "error");
    } finally {
      setIsLoading(false);
    }
  };

  // وظيفة التحقق من كلمة المرور الأمنية
  const verifySecurityPassword = async () => {
    try {
      const response = await fetchWithCSRF("/api/security/2fa/backup-codes", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          secretWord: securityPassword,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        // تحديث رموز النسخ الاحتياطي من الاستجابة
        setBackupCodes(data.backupCodes);
        setPasswordVerified(true);
      } else {
        const errorData = await response.json();
        showCustomAlert(errorData.error || "Invalid Secret Word", "error");
      }
    } catch (error) {
      console.error("Error verifying Secret Word:", error);
      showCustomAlert(
        "Failed to verify Secret Word. Please try again later.",
        "error"
      );
    }
  };

  // وظيفة إغلاق نافذة رموز النسخ الاحتياطي
  const closeBackupCodesModal = () => {
    setShowBackupCodesModal(false);
    setPasswordVerified(false);
    setSecurityPassword("");
  };

  // وظيفة نسخ رموز النسخ الاحتياطي
  const copyBackupCodes = () => {
    navigator.clipboard
      .writeText(backupCodes.join("\n"))
      .then(() => {
        setCopiedToClipboard(true);
        setTimeout(() => setCopiedToClipboard(false), 3000);
      })
      .catch((err) => {
        console.error("Failed to copy backup codes:", err);
        showCustomAlert("Failed to copy backup codes to clipboard", "error");
      });
  };

  // وظيفة لعرض التنبيهات المخصصة
  const showCustomAlert = (
    message: string,
    type: "success" | "error" | "info"
  ) => {
    // إزالة بادئة "Error:" إذا كانت موجودة
    if (type === "error" && message.startsWith("Error:")) {
      message = message.substring(6).trim();
    }
    setAlertMessage(message);
    setAlertType(type === "info" ? "success" : type);
    setShowAlert(true);
  };

  // وظيفة لإعادة تعيين خيار الحساب المحدد
  const resetAccountOption = () => {
    setSelectedAccountOption(null);
    setWalletPassword("");
    setTransferPassword("");
    setConfirmTransferPassword("");
    setMnemonicPhrase("");
    setShowCurrentPassword(false);
    setShowNewPassword(false);
    setShowConfirmPassword(false);
    setShowFinalConfirmation(false);
  };

  // تعديل وظيفة handleToggle للتعامل مع تجميد المحفظة كخيار في قائمة "الإعدادات"
  const handleToggle = (
    setter: React.Dispatch<React.SetStateAction<boolean>>,
    featureId: string
  ) => {
    return () => {
      // إذا كان featureId هو "frozen"، نقوم بتعيين selectedAccountOption إلى "freeze-wallet"
      if (featureId === "frozen") {
        setSelectedAccountOption("freeze-wallet");
      } else {
        // بالنسبة للميزات الأخرى، يمكننا تنفيذ منطق مختلف أو تبديل حالتها
        setter((prev) => !prev);

        // Can display confirmation message
        setAlertMessage(`${featureId} settings changed successfully`);
        setAlertType("success");
        setShowAlert(true);
      }
    };
  };

  // تعديل وظيفة freezeWallet للتعامل مع الحالة الجديدة
  const unfreezeWallet = async () => {
    try {
      // التحقق من أن كلمة المرور ليست فارغة
      if (!walletPassword || walletPassword.trim() === "") {
        setAlertMessage("Wallet password is required to unfreeze.");
        setAlertType("error");
        setShowAlert(true);
        return;
      }

      setIsLoading(true);

      // استخدام نفس نقطة النهاية التي يستخدمها freezeWallet مع تحديد العملية كـ "unfreeze"
      const response = await fetchWithCSRF("/api/security/freeze-wallet", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ walletPassword: walletPassword, action: "unfreeze" }),
      });

      if (response.ok) {
        setIsWalletFrozen(false);
        setAlertMessage(
          "Your wallet has been successfully unfrozen. You can now make transactions."
        );
        setAlertType("success");
        setShowAlert(true);

        // إعادة تعيين selectedAccountOption لإغلاق القسم
        setSelectedAccountOption(null);

        // إعادة تعيين كلمة المرور
        setWalletPassword("");
      } else {
        const errorData = await response.json();
        setAlertMessage(
          errorData.error ||
            "Failed to unfreeze the wallet. Please check your password and try again."
        );
        setAlertType("error");
        setShowAlert(true);
      }
    } catch (error) {
      console.error("Error unfreezing wallet:", error);
      setAlertMessage(
        "An error occurred while attempting to unfreeze the wallet. Please try again later."
      );
      setAlertType("error");
      setShowAlert(true);
    } finally {
      setIsLoading(false);
    }
  };

  // إضافة وظيفة منفصلة لتجميد المحفظة
  const freezeWallet = async () => {
    try {
      setIsLoading(true);

      // استخدام نقطة النهاية مع تحديد العملية كـ "freeze"
      // لا حاجة لإرسال كلمة المرور عند التجميد
      const response = await fetchWithCSRF("/api/security/freeze-wallet", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "freeze" }),
      });

      if (response.ok) {
        setIsWalletFrozen(true);
        setAlertMessage(
          "Your wallet has been successfully frozen. All transactions are temporarily suspended."
        );
        setAlertType("success");
        setShowAlert(true);

        // إعادة تعيين selectedAccountOption لإغلاق القسم
        setSelectedAccountOption(null);
      } else {
        const errorData = await response.json();
        setAlertMessage(
          errorData.error ||
            "Failed to freeze the wallet. Please try again later."
        );
        setAlertType("error");
        setShowAlert(true);
      }
    } catch (error) {
      console.error("Error freezing wallet:", error);
      setAlertMessage(
        "An error occurred while attempting to freeze the wallet. Please try again later."
      );
      setAlertType("error");
      setShowAlert(true);
    } finally {
      setIsLoading(false);
    }
  };

  // وظيفة لتغيير كلمة مرور المحفظة
  const changeWalletPassword = async () => {
    // التحقق من تطابق كلمة المرور الجديدة وتأكيدها
    if (transferPassword !== confirmTransferPassword) {
      showCustomAlert("New password and confirm password must match", "error");
      return;
    }

    // التحقق من متطلبات كلمة المرور
    if (!isPasswordValid(transferPassword)) {
      showCustomAlert("New password does not meet the requirements", "error");
      return;
    }

    try {
      const response = await fetchWithCSRF("/api/security/change-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          currentPassword: walletPassword,
          newPassword: transferPassword,
        }),
      });
      if (response.status === 200) {
        // إعادة تعيين الحالة
        resetAccountOption();

        // إظهار رسالة نجاح
        showCustomAlert("Wallet password changed successfully", "success");
      } else {
        const data = await response.json();
        showCustomAlert(data?.error || "Failed to change wallet password", "error");
      }
    } catch (error) {
      console.error("Error changing wallet password:", error);
      showCustomAlert("Failed to change wallet password. Please try again later.", "error");
    }
  };

  // وظيفة تأكيد حذف الحساب
  const confirmDeleteAccount = async () => {
    try {
      const response = await fetchWithCSRF("/api/wallet/delete-account", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirmDelete: true }),
      });
      const data = await response.json();
      if (data.success) {
        showCustomAlert("Your wallet has been deleted successfully.", "success");
        // هنا يمكن إضافة توجيه للمستخدم إلى صفحة الخروج
        setTimeout(() => {
          window.location.href = "/logout";
        }, 2000);
      } else {
        showCustomAlert(data.message || "Failed to delete account", "error");
      }
    } catch (error) {
      console.error("Error deleting account:", error);
      showCustomAlert("An error occurred while deleting your account. Please try again later.", "error");
    }
  };

  // وظائف للحصول على اسم طريقة المصادقة
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

  const getLoginAuthDisplayName = (method: string) => {
    switch (method) {
      case "none":
        return "Password Only";
      case "2fa":
        return "Two-Factor Authentication";
      case "secret_word":
        return "Secret Word";
      default:
        return "Password Only";
    }
  };

  // حفظ طريقة مصادقة التحويل
  const saveTransferAuthMethod = async () => {
    // تخطي إذا لم تتغير الطريقة
    if (tempTransferAuthMethod === transferAuthMethod) {
      setIsTransferAuthDropdownOpen(false);
      return;
    }

    // التحقق من حالة المصادقة الثنائية مرة أخرى قبل المتابعة
    if (tempTransferAuthMethod === "2fa") {
      // تحديث حالة المصادقة الثنائية قبل المتابعة
      try {
        const response = await fetch("/api/security/settings");
        if (response.ok) {
          const data = await response.json();
          // تحديث حالة المصادقة الثنائية
          const is2faActive = data.twoFAEnabled || false;
          setIs2FAEnabled(is2faActive);

          // إذا لم تكن المصادقة الثنائية مفعلة، أظهر رسالة خطأ
          if (!is2faActive) {
            showCustomAlert(
              "Two-Factor Authentication must be enabled first. Please go to the security section to enable 2FA.",
              "error"
            );
            return;
          }
        } else {
          console.error(
            "Error fetching security settings:",
            await response.text()
          );
        }
      } catch (error) {
        console.error("Error checking 2FA status:", error);
        // استمر في التنفيذ وسيتم التعامل مع الخطأ من قبل الخادم إذا كانت المصادقة الثنائية غير مفعلة
      }
    }

    try {
      // إضافة مؤشر التحميل
      setIsLoading(true);

      // استدعاء API لتحديث طريقة المصادقة
      const response = await fetchWithCSRF("/api/security/transfer-auth-method", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ method: tempTransferAuthMethod }),
      });

      const data = await response.json();

      if (response.ok) {
        // تحديث الحالة بالطريقة الجديدة بدلاً من إعادة تحميل الصفحة
        setTransferAuthMethod(tempTransferAuthMethod);
        setIsTransferAuthDropdownOpen(false);

        // تحديث جميع الإعدادات الأمنية بعد النجاح للتأكد من أن الواجهة متزامنة مع قاعدة البيانات
        await fetchLatestSettings();

        showCustomAlert(
          data.message || "Transfer authentication method updated successfully",
          "success"
        );
      } else {
        // عرض رسالة الخطأ
        if (data.error && data.error.includes("2FA must be enabled")) {
          showCustomAlert(
            "Two-Factor Authentication must be enabled first. Please go to the security section to enable 2FA.",
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
    } finally {
      // إزالة مؤشر التحميل
      setIsLoading(false);
    }
  };

  // حفظ طريقة مصادقة الدخول
  const saveLoginAuthMethod = async () => {
    // تخطي إذا لم تتغير الطريقة
    if (tempLoginAuthMethod === loginAuthMethod) {
      setIsLoginAuthDropdownOpen(false);
      return;
    }

    // التحقق من حالة المصادقة الثنائية مرة أخرى قبل المتابعة
    if (tempLoginAuthMethod === "2fa") {
      // تحديث حالة المصادقة الثنائية قبل المتابعة
      try {
        const response = await fetch("/api/security/settings");

        if (response.ok) {
          const data = await response.json();
          // تحديث حالة المصادقة الثنائية
          const is2faActive = data.twoFAEnabled || false;
          setIs2FAEnabled(is2faActive);

          // إذا لم تكن المصادقة الثنائية مفعلة، أظهر رسالة خطأ
          if (!is2faActive) {
            showCustomAlert(
              "Two-Factor Authentication must be enabled first. Please go to the security section to enable 2FA.",
              "error"
            );
            return;
          }
        } else {
          console.error(
            "Error fetching security settings:",
            await response.text()
          );
        }
      } catch (error) {
        console.error("Error checking 2FA status:", error);
        // استمر في التنفيذ وسيتم التعامل مع الخطأ من قبل الخادم إذا كانت المصادقة الثنائية غير مفعلة
      }
    }

    try {
      // إضافة مؤشر التحميل
      setIsLoading(true);

      // استدعاء API لتحديث طريقة المصادقة
      const response = await fetchWithCSRF("/api/security/login-auth-method", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ method: tempLoginAuthMethod }),
      });

      const data = await response.json();

      if (response.ok) {
        // تحديث الحالة بالطريقة الجديدة
        setLoginAuthMethod(tempLoginAuthMethod);
        setIsLoginAuthDropdownOpen(false);

        // تحديث جميع الإعدادات الأمنية بعد النجاح للتأكد من أن الواجهة متزامنة مع قاعدة البيانات
        await fetchLatestSettings();

        showCustomAlert(
          data.message || "Login authentication method updated successfully",
          "success"
        );
      } else {
        // عرض رسالة الخطأ
        if (data.error && data.error.includes("2FA must be enabled")) {
          showCustomAlert(
            "Two-Factor Authentication must be enabled first. Please go to the security section to enable 2FA.",
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
    } finally {
      // إزالة مؤشر التحميل
      setIsLoading(false);
    }
  };

  // وظيفة للتحقق من متطلبات كلمة المرور بشكل منفصل
  const checkPasswordRequirements = (password: string) => {
    return {
      hasMinLength: password.length >= 8,
      hasUppercase: /[A-Z]/.test(password),
      hasNumber: /[0-9]/.test(password),
      hasSpecialChar: /[!@#$%^&*]/.test(password),
    };
  };

  // وظيفة للتحقق من تلبية جميع المتطلبات
  const isPasswordValid = (password: string) => {
    const { hasMinLength, hasUppercase, hasNumber, hasSpecialChar } =
      checkPasswordRequirements(password);
    return hasMinLength && hasUppercase && hasNumber && hasSpecialChar;
  };

  // وظيفة لتحديث حالة المصادقة الثنائية بشكل إجباري
  const forceRefresh2FAStatus = async () => {
    try {
      setIsLoading(true);
      showCustomAlert("Updating Two-Factor Authentication status...", "info");

      // استخدام المسار الصحيح للحصول على إعدادات الأمان
      const response = await fetch("/api/security/settings");

      if (response.ok) {
        const data = await response.json();
        console.log("Force refresh 2FA status - response:", data);

        // التحقق من twoFAEnabled في البيانات المستلمة
        const newStatus = data.twoFAEnabled || false;
        setIs2FAEnabled(newStatus);

        showCustomAlert(
          newStatus
            ? "Status updated: Two-Factor Authentication is enabled"
            : "Status updated: Two-Factor Authentication is disabled",
          newStatus ? "success" : "info"
        );
      } else {
        console.error(
          "Error fetching security settings:",
          await response.text()
        );
        showCustomAlert("Failed to update Two-Factor Authentication status", "error");
      }
    } catch (error) {
      console.error("Error in force refresh 2FA status:", error);
      showCustomAlert("Failed to update Two-Factor Authentication status", "error");
    } finally {
      setIsLoading(false);
    }
  };

  // إضافة تأثير لتعيين الاختيار المؤقت عند فتح قائمة التسجيل
  useEffect(() => {
    if (isLoginAuthDropdownOpen) {
      console.log(
        "Login dropdown opened, setting temp method:",
        loginAuthMethod
      );
      setTempLoginAuthMethod(loginAuthMethod);
    }
  }, [isLoginAuthDropdownOpen, loginAuthMethod]);

  // إضافة تأثير لتعيين الاختيار المؤقت عند فتح قائمة التحويل
  useEffect(() => {
    if (isTransferAuthDropdownOpen) {
      console.log(
        "Transfer dropdown opened, setting temp method:",
        transferAuthMethod
      );
      setTempTransferAuthMethod(transferAuthMethod);
    }
  }, [isTransferAuthDropdownOpen, transferAuthMethod]);

  // تعديل دالة فتح قائمة تسجيل الدخول
  const openLoginAuthDropdown = async () => {
    // تحديث حالة 2FA قبل فتح القائمة
    try {
      const response = await fetch("/api/security/settings");
      if (response.ok) {
        const data = await response.json();
        const is2faActive = data.twoFAEnabled || false;
        setIs2FAEnabled(is2faActive);
        console.log(
          "Updated 2FA status before opening login auth dropdown:",
          is2faActive
        );

        // تحديث القيمة المختارة بناءً على البيانات المستلمة بالطريقة المحسنة
        if (data.loginAuthMethod) {
          const loginMethodName = Object.keys(data.loginAuthMethod).find(
            (key) => data.loginAuthMethod[key] === true
          );

          if (loginMethodName) {
            console.log("Current login auth method from API:", loginMethodName);
            setLoginAuthMethod(loginMethodName);
            setTempLoginAuthMethod(loginMethodName);
          } else {
            console.log("No active login auth method found from API");
            setLoginAuthMethod("none");
            setTempLoginAuthMethod("none");
          }
        }
      } else {
        console.error(
          "Error fetching security settings:",
          await response.text()
        );
      }
    } catch (error) {
      console.error("Error checking 2FA status:", error);
    }

    // تأكد دائمًا من تعيين القيمة المؤقتة للقيمة الحالية قبل فتح القائمة
    setTempLoginAuthMethod(loginAuthMethod);

    // فتح القائمة
    setIsLoginAuthDropdownOpen(true);
    setIsTransferAuthDropdownOpen(false);
  };

  // تعديل دالة فتح قائمة مصادقة التحويل
  const openTransferAuthDropdown = async () => {
    // تحديث حالة 2FA قبل فتح القائمة
    try {
      const response = await fetch("/api/security/settings");
      if (response.ok) {
        const data = await response.json();
        const is2faActive = data.twoFAEnabled || false;
        setIs2FAEnabled(is2faActive);
        console.log(
          "Updated 2FA status before opening transfer auth dropdown:",
          is2faActive
        );

        // تحديث القيمة المختارة بناءً على البيانات المستلمة بالطريقة المحسنة
        if (data.transferAuthMethod) {
          const transferMethodName = Object.keys(data.transferAuthMethod).find(
            (key) => data.transferAuthMethod[key] === true
          );

          if (transferMethodName) {
            console.log(
              "Current transfer auth method from API:",
              transferMethodName
            );
            setTransferAuthMethod(transferMethodName);
            setTempTransferAuthMethod(transferMethodName);
          } else {
            console.log("No active transfer auth method found from API");
            setTransferAuthMethod("password");
            setTempTransferAuthMethod("password");
          }
        }
      } else {
        console.error(
          "Error fetching security settings:",
          await response.text()
        );
      }
    } catch (error) {
      console.error("Error checking 2FA status:", error);
    }

    // تأكد دائمًا من تعيين القيمة المؤقتة للقيمة الحالية قبل فتح القائمة
    setTempTransferAuthMethod(transferAuthMethod);

    // فتح القائمة
    setIsTransferAuthDropdownOpen(true);
    setIsLoginAuthDropdownOpen(false);
  };

  return (
    <div className="min-h-screen bg-[#262626] py-4 sm:py-6 px-3 sm:px-4 sm:py-10">
      <div className="container mx-auto max-w-4xl">
        {/* Header with left alignment */}
        <div className="mb-5 sm:mb-8 text-left">
          <h1
            className={clsx(
              "text-2xl sm:text-3xl font-bold text-gray-200 mb-2",
              "transition-all duration-700",
              animateBalance
                ? "translate-y-0 opacity-100"
                : "translate-y-4 opacity-0"
            )}
          >
            Wallet Settings
          </h1>
          <p
            className={clsx(
              "text-sm sm:text-base text-gray-400 transition-all duration-700 delay-200",
              animateBalance
                ? "translate-y-0 opacity-100"
                : "translate-y-4 opacity-0"
            )}
          >
            Manage, protect, and backup your wallet data
          </p>
        </div>

        {/* Notification toast */}
        {notification.show && (
          <div
            className={clsx(
              "fixed top-4 sm:top-6 right-4 sm:right-6 max-w-[90%] sm:max-w-md p-3 sm:p-4 rounded-lg shadow-lg border flex items-start gap-2 sm:gap-3 z-50 animate-scaleIn",
              notification.type === "success"
                ? "bg-green-50 border-green-200"
                : notification.type === "error"
                ? "bg-red-50 border-red-200"
                : "bg-blue-50 border-blue-200"
            )}
          >
            {notification.type === "success" ? (
              <CheckCircle className="text-green-500 shrink-0" size={16} />
            ) : notification.type === "error" ? (
              <AlertCircle className="text-red-500 shrink-0" size={16} />
            ) : (
              <Info className="text-blue-500 shrink-0" size={16} />
            )}
            <div className="flex-1">
              <p
                className={clsx(
                  "font-medium text-xs sm:text-sm",
                  notification.type === "success"
                    ? "text-green-800"
                    : notification.type === "error"
                    ? "text-red-800"
                    : "text-blue-800"
                )}
              >
                {notification.type === "success"
                  ? "Success"
                  : notification.type === "error"
                  ? "Error"
                  : "Information"}
              </p>
              <p
                className={clsx(
                  "text-xs sm:text-sm",
                  notification.type === "success"
                    ? "text-green-700"
                    : notification.type === "error"
                    ? "text-red-700"
                    : "text-blue-700"
                )}
              >
                {notification.message}
              </p>
            </div>
            <button
              onClick={dismissNotification}
              className={clsx(
                "p-1 rounded-full hover:bg-white transition-colors",
                notification.type === "success"
                  ? "text-green-700"
                  : notification.type === "error"
                  ? "text-red-700"
                  : "text-blue-700"
              )}
            >
              <X size={14} />
            </button>
          </div>
        )}

        {/* Main content with better layout */}
        <div className="grid grid-cols-1 gap-4 sm:gap-6">
          {/* Account Management Card - First card at the top, full width */}
          <div
            className={clsx(
              "bg-[#2b2b2b] rounded-xl shadow-md border border-[#393939] overflow-hidden mb-4 sm:mb-6",
              "transition-all duration-700",
              animateSection
                ? "translate-y-0 opacity-100"
                : "translate-y-10 opacity-0"
            )}
          >
            <div className="border-b border-[#393939] px-4 sm:px-6 py-4 sm:py-5">
              <h2 className="text-lg sm:text-xl font-bold text-gray-200">
                Account Management
              </h2>
            </div>

            <div className="p-4 sm:p-6">
              {!selectedAccountOption ? (
                <div className="space-y-3 sm:space-y-4 transform transition-all duration-500">
                  {/* قسم Login Authentication و Transfer Authentication */}
                  {!isLoginAuthDropdownOpen && !isTransferAuthDropdownOpen && (
                    <>
                      <div className="flex flex-col md:flex-row gap-3 sm:gap-4">
                        {/* Login Authentication */}
                        <div
                          className="flex-1 flex items-center justify-between p-3 sm:p-5 border border-[#393939] rounded-xl sm:rounded-2xl cursor-pointer hover:bg-[#1e1e2e] hover:border-blue-800 hover:shadow-md transition-all duration-300 transform hover:-translate-y-1 bg-[#232323]"
                          onClick={openLoginAuthDropdown}
                        >
                          <div className="flex items-center gap-3 sm:gap-4">
                            <div className="h-10 w-10 sm:h-12 sm:w-12 rounded-xl bg-[#1a1e2e] flex items-center justify-center text-blue-500 shadow-sm">
                              <Shield size={18} className="sm:size-[22px]" />
                            </div>
                            <div>
                              <p className="font-medium text-gray-200 text-sm sm:text-lg">
                                Login Authentication
                              </p>
                              {isLoading && !settingsLoaded ? (
                                <p className="text-xs sm:text-sm text-gray-400 flex items-center gap-1">
                                  <RefreshCw
                                    size={10}
                                    className="animate-spin sm:size-[12px]"
                                  />
                                  Loading settings...
                                </p>
                              ) : (
                                <p className="text-xs sm:text-sm text-gray-400">
                                  {getLoginAuthDisplayName(loginAuthMethod)}
                                </p>
                              )}
                            </div>
                          </div>
                          <ChevronRight
                            size={18}
                            className="text-gray-500 transform transition-transform duration-300 group-hover:translate-x-1 sm:size-[20px]"
                          />
                        </div>

                        {/* Transfer Authentication */}
                        <div
                          className="flex-1 flex items-center justify-between p-3 sm:p-5 border border-[#393939] rounded-xl sm:rounded-2xl cursor-pointer hover:bg-[#1e1e2e] hover:border-blue-800 hover:shadow-md transition-all duration-300 transform hover:-translate-y-1 bg-[#232323]"
                          onClick={openTransferAuthDropdown}
                        >
                          <div className="flex items-center gap-3 sm:gap-4">
                            <div className="h-10 w-10 sm:h-12 sm:w-12 rounded-xl bg-[#1a1e2e] flex items-center justify-center text-blue-500 shadow-sm">
                              <SettingsIcon
                                size={18}
                                className="animate-spin-slow sm:size-[22px]"
                              />
                            </div>
                            <div>
                              <p className="font-medium text-gray-200 text-sm sm:text-lg">
                                Transfer Authentication
                              </p>
                              {isLoading && !settingsLoaded ? (
                                <p className="text-xs sm:text-sm text-gray-400 flex items-center gap-1">
                                  <RefreshCw
                                    size={10}
                                    className="animate-spin sm:size-[12px]"
                                  />
                                  Loading settings...
                                </p>
                              ) : (
                                <p className="text-xs sm:text-sm text-gray-400">
                                  {getTransferAuthDisplayName(
                                    transferAuthMethod
                                  )}
                                </p>
                              )}
                            </div>
                          </div>
                          <ChevronRight
                            size={18}
                            className="text-gray-500 transform transition-transform duration-300 group-hover:translate-x-1 sm:size-[20px]"
                          />
                        </div>
                      </div>

                      {/* قسم Wallet Frozen و Change Wallet Password */}
                      <div className="flex flex-col md:flex-row gap-3 sm:gap-4">
                        {/* Wallet Frozen option */}
                        <div
                          className={`flex-1 flex items-center justify-between p-3 sm:p-5 border border-[#393939] rounded-xl sm:rounded-2xl cursor-pointer bg-[#232323] ${
                            isWalletFrozen
                              ? "bg-[#1a2e3a] border-blue-900"
                              : "hover:bg-[#1e1e2e] hover:border-blue-800"
                          } hover:shadow-md transition-all duration-300 transform hover:-translate-y-1`}
                          onClick={handleToggle(setIsWalletFrozen, "frozen")}
                        >
                          <div className="flex flex-col">
                            <div className="flex items-center gap-3 sm:gap-4">
                              <div className="h-10 w-10 sm:h-12 sm:w-12 rounded-xl bg-[#1a2e3a] flex items-center justify-center text-blue-400 shadow-sm">
                                <SnowflakeIcon size={18} className="sm:size-[22px]" />
                              </div>
                              <div>
                                <p className="font-medium text-gray-200 text-sm sm:text-lg">
                                  {isWalletFrozen
                                    ? "Wallet Frozen"
                                    : "Freeze Wallet"}
                                </p>
                                <p className="text-xs sm:text-sm text-gray-400">
                                  {isWalletFrozen
                                    ? "Your wallet is frozen - no transactions allowed"
                                    : "Temporarily disable all transactions"}
                                </p>
                                {/* Wallet Freeze/Unfreeze Instructions */}
                                <p className="text-[10px] sm:text-xs text-gray-500 italic mt-1">
                                  {isWalletFrozen
                                    ? "Click to enter your password and unfreeze your wallet"
                                    : "Click to freeze your wallet and prevent any transactions"}
                                </p>
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center">
                            <div
                              className={`px-2 py-1 sm:px-3 sm:py-1.5 rounded-full text-[10px] sm:text-xs font-medium mr-2 ${
                                isWalletFrozen
                                  ? "bg-blue-900 text-blue-300"
                                  : "bg-[#1a1a1a] text-gray-400"
                              }`}
                            >
                              {isWalletFrozen ? "Active" : "Inactive"}
                            </div>
                            <ChevronRight
                              size={18}
                              className="text-gray-500 transform transition-transform duration-300 group-hover:translate-x-1 sm:size-[20px]"
                            />
                          </div>
                        </div>

                        {/* Change Wallet Password */}
                        <div
                          className="flex-1 flex items-center justify-between p-3 sm:p-5 border border-[#393939] rounded-xl sm:rounded-2xl cursor-pointer hover:bg-[#1e1e2e] hover:border-blue-800 hover:shadow-md transition-all duration-300 transform hover:-translate-y-1 bg-[#232323]"
                          onClick={() =>
                            setSelectedAccountOption("change-password")
                          }
                        >
                          <div className="flex items-center gap-3 sm:gap-4">
                            <div className="h-10 w-10 sm:h-12 sm:w-12 rounded-xl bg-[#1a1e2e] flex items-center justify-center text-blue-500 shadow-sm">
                              <LockIcon size={18} className="sm:size-[22px]" />
                            </div>
                            <div>
                              <p className="font-medium text-gray-200 text-sm sm:text-lg">
                                Change Wallet Password
                              </p>
                              <p className="text-xs sm:text-sm text-gray-400">
                                Update your wallet security credentials
                              </p>
                            </div>
                          </div>
                          <ChevronRight
                            size={18}
                            className="text-gray-500 transform transition-transform duration-300 group-hover:translate-x-1 sm:size-[20px]"
                          />
                        </div>
                      </div>

                      {/* Delete Wallet Account - in its own row */}
                      <div
                        onClick={() =>
                          setSelectedAccountOption("delete-account")
                        }
                        className="flex items-center justify-between p-3 sm:p-5 border border-[#393939] rounded-xl sm:rounded-2xl cursor-pointer hover:bg-[#2a1a1a] hover:border-red-900 hover:shadow-md transition-all duration-300 transform hover:-translate-y-1 bg-[#232323]"
                      >
                        <div className="flex items-center gap-3 sm:gap-4">
                          <div className="h-10 w-10 sm:h-12 sm:w-12 rounded-xl bg-[#2a1a1a] flex items-center justify-center text-red-500 shadow-sm">
                            <UserX2 size={18} className="sm:size-[22px]" />
                          </div>
                          <div>
                            <p className="font-medium text-gray-200 text-sm sm:text-lg">
                              Delete Wallet Account
                            </p>
                            <p className="text-xs sm:text-sm text-gray-400">
                              Permanently remove your wallet and all data
                            </p>
                          </div>
                        </div>
                        <ChevronRight
                          size={18}
                          className="text-gray-500 transform transition-transform duration-300 group-hover:translate-x-1 sm:size-[20px]"
                        />
                      </div>
                    </>
                  )}

                  {/* القائمة المنسدلة لطرق مصادقة الدخول */}
                  {isLoginAuthDropdownOpen && (
                    <div className="animate-slideUpFade">
                      <div className="flex items-center mb-4 sm:mb-5">
                        <button
                          onClick={() => setIsLoginAuthDropdownOpen(false)}
                          className="p-1.5 sm:p-2 mr-3 rounded-full hover:bg-blue-900 transition-all duration-300 transform hover:scale-110 text-white"
                        >
                          <X size={20} className="text-blue-400 sm:size-[22px]" />
                        </button>
                        <h3 className="text-lg sm:text-xl font-bold text-gray-200">
                          Login Authentication
                        </h3>
                      </div>

                      <p className="text-xs sm:text-sm text-gray-400 mb-4 sm:mb-5">
                        Select how you want to secure your wallet login
                      </p>

                      <div className="space-y-3 mb-5 sm:mb-6">
                        {/* Password Only option */}
                        <div
                          className={`flex items-center justify-between p-3 sm:p-4 rounded-xl border transition-all duration-300 cursor-pointer transform hover:-translate-y-1 hover:shadow-md ${
                            tempLoginAuthMethod === "none"
                              ? "border-blue-800 bg-blue-900/40 shadow-sm"
                              : "border-[#393939] hover:border-blue-900 hover:bg-[#2d2d3d]"
                          }`}
                          onClick={() => setTempLoginAuthMethod("none")}
                        >
                          <div className="flex items-center gap-3 sm:gap-4">
                            <div
                              className={`w-10 h-10 sm:w-12 sm:h-12 rounded-full ${
                                tempLoginAuthMethod === "none"
                                  ? "bg-blue-900"
                                  : "bg-[#1a1a1a]"
                              } flex items-center justify-center ${
                                tempLoginAuthMethod === "none"
                                  ? "text-blue-400"
                                  : "text-gray-400"
                              } transition-all duration-300`}
                            >
                              <Lock size={18} className="sm:size-[20px]" />
                            </div>
                            <div>
                              <p className="font-medium text-gray-200 text-sm sm:text-base">
                                Password Only
                              </p>
                              <p className="text-xs sm:text-sm text-gray-400">
                                Authenticate with your wallet password only
                              </p>
                            </div>
                          </div>
                          <div
                            className={`w-5 h-5 sm:w-6 sm:h-6 rounded-full border-2 flex items-center justify-center transition-all duration-300 ${
                              tempLoginAuthMethod === "none"
                                ? "border-blue-500 bg-blue-500 scale-110"
                                : "border-gray-600"
                            }`}
                          >
                            {tempLoginAuthMethod === "none" && (
                              <Check className="text-white" size={12} />
                            )}
                          </div>
                        </div>

                        {/* Secret Word option */}
                        <div
                          className={`flex items-center justify-between p-3 sm:p-4 rounded-xl border transition-all duration-300 cursor-pointer transform hover:-translate-y-1 hover:shadow-md ${
                            tempLoginAuthMethod === "secret_word"
                              ? "border-blue-800 bg-blue-900/40 shadow-sm"
                              : "border-[#393939] hover:border-blue-900 hover:bg-[#2d2d3d]"
                          }`}
                          onClick={() => setTempLoginAuthMethod("secret_word")}
                        >
                          <div className="flex items-center gap-3 sm:gap-4">
                            <div
                              className={`w-10 h-10 sm:w-12 sm:h-12 rounded-full ${
                                tempLoginAuthMethod === "secret_word"
                                  ? "bg-blue-900"
                                  : "bg-[#1a1a1a]"
                              } flex items-center justify-center ${
                                tempLoginAuthMethod === "secret_word"
                                  ? "text-blue-400"
                                  : "text-gray-400"
                              } transition-all duration-300`}
                            >
                              <Key size={18} className="sm:size-[20px]" />
                            </div>
                            <div>
                              <p className="font-medium text-gray-200 text-sm sm:text-base">
                                Secret Word
                              </p>
                              <p className="text-xs sm:text-sm text-gray-400">
                                Use your password plus a secret word for
                                enhanced security
                              </p>
                            </div>
                          </div>
                          <div
                            className={`w-5 h-5 sm:w-6 sm:h-6 rounded-full border-2 flex items-center justify-center transition-all duration-300 ${
                              tempLoginAuthMethod === "secret_word"
                                ? "border-blue-500 bg-blue-500 scale-110"
                                : "border-gray-600"
                            }`}
                          >
                            {tempLoginAuthMethod === "secret_word" && (
                              <Check className="text-white" size={12} />
                            )}
                          </div>
                        </div>

                        {/* Two-Factor Authentication option */}
                        <div
                          className={`flex items-center justify-between p-3 sm:p-4 rounded-xl border transition-all duration-300 ${
                            !is2FAEnabled
                              ? "opacity-60 cursor-not-allowed border-[#393939]"
                              : tempLoginAuthMethod === "2fa"
                              ? "border-blue-800 bg-blue-900/40 shadow-sm cursor-pointer transform hover:-translate-y-1 hover:shadow-md"
                              : "border-[#393939] hover:border-blue-900 hover:bg-[#2d2d3d] cursor-pointer transform hover:-translate-y-1 hover:shadow-md"
                          }`}
                          onClick={() => {
                            if (is2FAEnabled) {
                              setTempLoginAuthMethod("2fa");
                            } else {
                              showCustomAlert(
                                "Two-Factor Authentication must be enabled first",
                                "error"
                              );
                            }
                          }}
                        >
                          <div className="flex items-center gap-3 sm:gap-4">
                            <div
                              className={`w-10 h-10 sm:w-12 sm:h-12 rounded-full ${
                                tempLoginAuthMethod === "2fa"
                                  ? "bg-blue-900"
                                  : "bg-[#1a1a1a]"
                              } flex items-center justify-center ${
                                tempLoginAuthMethod === "2fa"
                                  ? "text-blue-400"
                                  : "text-gray-400"
                              } transition-all duration-300`}
                            >
                              <Smartphone size={18} className="sm:size-[20px]" />
                            </div>
                            <div>
                              <p className="font-medium text-gray-200 text-sm sm:text-base">
                                Two-Factor Authentication
                              </p>
                              <p className="text-xs sm:text-sm text-gray-400">
                                Maximum security with time-based verification
                                codes
                              </p>
                            </div>
                          </div>
                          <div
                            className={`w-5 h-5 sm:w-6 sm:h-6 rounded-full border-2 flex items-center justify-center transition-all duration-300 ${
                              tempLoginAuthMethod === "2fa"
                                ? "border-blue-500 bg-blue-500 scale-110"
                                : "border-gray-600"
                            }`}
                          >
                            {tempLoginAuthMethod === "2fa" && (
                              <Check className="text-white" size={12} />
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="flex justify-end gap-2 sm:gap-3">
                        <button
                          onClick={() => setIsLoginAuthDropdownOpen(false)}
                          className="px-4 py-2 sm:px-5 sm:py-2.5 rounded-lg border border-[#393939] text-gray-300 text-xs sm:text-sm font-medium hover:bg-[#2d2d3d] transition-all transform hover:scale-105"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={saveLoginAuthMethod}
                          className="px-4 py-2 sm:px-5 sm:py-2.5 rounded-lg bg-gradient-to-r from-blue-600 to-blue-800 hover:from-blue-700 hover:to-blue-900 text-white text-xs sm:text-sm font-medium shadow-sm hover:shadow transition-all transform hover:scale-105"
                        >
                          Save
                        </button>
                      </div>
                    </div>
                  )}

                  {/* القائمة المنسدلة لطرق مصادقة التحويل */}
                  {isTransferAuthDropdownOpen && (
                    <div className="animate-slideUpFade">
                      <div className="flex items-center mb-4 sm:mb-5">
                        <button
                          onClick={() => setIsTransferAuthDropdownOpen(false)}
                          className="p-1.5 sm:p-2 mr-3 rounded-full hover:bg-blue-900 transition-all duration-300 transform hover:scale-110 text-white"
                        >
                          <X size={20} className="text-blue-400 sm:size-[22px]" />
                        </button>
                        <h3 className="text-lg sm:text-xl font-bold text-gray-200">
                          Transfer Authentication
                        </h3>
                      </div>

                      <p className="text-xs sm:text-sm text-gray-400 mb-4 sm:mb-5">
                        Select authentication method for transfers and payments
                      </p>

                      <div className="space-y-3 mb-5 sm:mb-6">
                        {/* Transfer Password option */}
                        <div
                          className={`flex items-center justify-between p-3 sm:p-4 rounded-xl border transition-all duration-300 cursor-pointer transform hover:-translate-y-1 hover:shadow-md ${
                            tempTransferAuthMethod === "password"
                              ? "border-blue-800 bg-blue-900/40 shadow-sm"
                              : "border-[#393939] hover:border-blue-900 hover:bg-[#2d2d3d]"
                          }`}
                          onClick={() => setTempTransferAuthMethod("password")}
                        >
                          <div className="flex items-center gap-3 sm:gap-4">
                            <div
                              className={`w-10 h-10 sm:w-12 sm:h-12 rounded-full ${
                                tempTransferAuthMethod === "password"
                                  ? "bg-blue-900"
                                  : "bg-[#1a1a1a]"
                              } flex items-center justify-center ${
                                tempTransferAuthMethod === "password"
                                  ? "text-blue-400"
                                  : "text-gray-400"
                              } transition-all duration-300`}
                            >
                              <Fingerprint size={18} className="sm:size-[20px]" />
                            </div>
                            <div>
                              <p className="font-medium text-gray-200 text-sm sm:text-base">
                                Transfer Password
                              </p>
                              <p className="text-xs sm:text-sm text-gray-400">
                                Secure transfers with a dedicated transaction
                                password
                              </p>
                            </div>
                          </div>
                          <div
                            className={`w-5 h-5 sm:w-6 sm:h-6 rounded-full border-2 flex items-center justify-center transition-all duration-300 ${
                              tempTransferAuthMethod === "password"
                                ? "border-blue-500 bg-blue-500 scale-110"
                                : "border-gray-600"
                            }`}
                          >
                            {tempTransferAuthMethod === "password" && (
                              <Check className="text-white" size={12} />
                            )}
                          </div>
                        </div>

                        {/* Two-Factor Authentication option */}
                        <div
                          className={`flex items-center justify-between p-3 sm:p-4 rounded-xl border transition-all duration-300 ${
                            !is2FAEnabled
                              ? "opacity-60 cursor-not-allowed border-[#393939]"
                              : tempTransferAuthMethod === "2fa"
                              ? "border-blue-800 bg-blue-900/40 shadow-sm cursor-pointer transform hover:-translate-y-1 hover:shadow-md"
                              : "border-[#393939] hover:border-blue-900 hover:bg-[#2d2d3d] cursor-pointer transform hover:-translate-y-1 hover:shadow-md"
                          }`}
                          onClick={() => {
                            if (is2FAEnabled) {
                              setTempTransferAuthMethod("2fa");
                            } else {
                              showCustomAlert(
                                "Two-Factor Authentication must be enabled first",
                                "error"
                              );
                            }
                          }}
                        >
                          <div className="flex items-center gap-3 sm:gap-4">
                            <div
                              className={`w-10 h-10 sm:w-12 sm:h-12 rounded-full ${
                                tempTransferAuthMethod === "2fa"
                                  ? "bg-blue-900"
                                  : "bg-[#1a1a1a]"
                              } flex items-center justify-center ${
                                tempTransferAuthMethod === "2fa"
                                  ? "text-blue-400"
                                  : "text-gray-400"
                              } transition-all duration-300`}
                            >
                              <Smartphone size={18} className="sm:size-[20px]" />
                            </div>
                            <div>
                              <p className="font-medium text-gray-200 text-sm sm:text-base">
                                Two-Factor Authentication
                              </p>
                              <p className="text-xs sm:text-sm text-gray-400">
                                Maximum security for transactions with
                                verification codes
                              </p>
                            </div>
                          </div>
                          <div
                            className={`w-5 h-5 sm:w-6 sm:h-6 rounded-full border-2 flex items-center justify-center transition-all duration-300 ${
                              tempTransferAuthMethod === "2fa"
                                ? "border-blue-500 bg-blue-500 scale-110"
                                : "border-gray-600"
                            }`}
                          >
                            {tempTransferAuthMethod === "2fa" && (
                              <Check className="text-white" size={12} />
                            )}
                          </div>
                        </div>

                        {/* Secret Word option */}
                        <div
                          className={`flex items-center justify-between p-3 sm:p-4 rounded-xl border transition-all duration-300 cursor-pointer transform hover:-translate-y-1 hover:shadow-md ${
                            tempTransferAuthMethod === "secret_word"
                              ? "border-blue-800 bg-blue-900/40 shadow-sm"
                              : "border-[#393939] hover:border-blue-900 hover:bg-[#2d2d3d]"
                          }`}
                          onClick={() =>
                            setTempTransferAuthMethod("secret_word")
                          }
                        >
                          <div className="flex items-center gap-3 sm:gap-4">
                            <div
                              className={`w-10 h-10 sm:w-12 sm:h-12 rounded-full ${
                                tempTransferAuthMethod === "secret_word"
                                  ? "bg-blue-900"
                                  : "bg-[#1a1a1a]"
                              } flex items-center justify-center ${
                                tempTransferAuthMethod === "secret_word"
                                  ? "text-blue-400"
                                  : "text-gray-400"
                              } transition-all duration-300`}
                            >
                              <Key size={18} className="sm:size-[20px]" />
                            </div>
                            <div>
                              <p className="font-medium text-gray-200 text-sm sm:text-base">
                                Secret Word
                              </p>
                              <p className="text-xs sm:text-sm text-gray-400">
                                Authorize transfers with your personal secret
                                phrase
                              </p>
                            </div>
                          </div>
                          <div
                            className={`w-5 h-5 sm:w-6 sm:h-6 rounded-full border-2 flex items-center justify-center transition-all duration-300 ${
                              tempTransferAuthMethod === "secret_word"
                                ? "border-blue-500 bg-blue-500 scale-110"
                                : "border-gray-600"
                            }`}
                          >
                            {tempTransferAuthMethod === "secret_word" && (
                              <Check className="text-white" size={12} />
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="flex justify-end gap-2 sm:gap-3">
                        <button
                          onClick={() => setIsTransferAuthDropdownOpen(false)}
                          className="px-4 py-2 sm:px-5 sm:py-2.5 rounded-lg border border-[#393939] text-gray-300 text-xs sm:text-sm font-medium hover:bg-[#2d2d3d] transition-all transform hover:scale-105"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={saveTransferAuthMethod}
                          className="px-4 py-2 sm:px-5 sm:py-2.5 rounded-lg bg-gradient-to-r from-blue-600 to-blue-800 hover:from-blue-700 hover:to-blue-900 text-white text-xs sm:text-sm font-medium shadow-sm hover:shadow transition-all transform hover:scale-105"
                        >
                          Save
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : selectedAccountOption === "change-password" ? (
                <div className="animate-slideUpFade">
                  <div className="flex items-center mb-4 sm:mb-5">
                    <button
                      onClick={resetAccountOption}
                      className="p-1.5 sm:p-2 mr-3 rounded-full hover:bg-blue-900 transition-all duration-300 transform hover:scale-110 text-white"
                    >
                      <X size={20} className="text-blue-400 sm:size-[22px]" />
                    </button>
                    <h3 className="text-lg sm:text-xl font-bold text-gray-200">
                      Change Wallet Password
                    </h3>
                  </div>

                  <div className="space-y-4 sm:space-y-5">
                    <div className="relative">
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Current Password
                      </label>
                      <div className="relative">
                        <input
                          type={showCurrentPassword ? "text" : "password"}
                          placeholder="Enter current password"
                          className="w-full p-3 sm:p-4 pl-4 sm:pl-5 border border-[#393939] rounded-xl bg-[#232323] focus:bg-[#2d2d3d] focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-300 text-gray-200 text-sm sm:text-base"
                          value={walletPassword}
                          onChange={(e) => setWalletPassword(e.target.value)}
                        />
                        <button
                          type="button"
                          onClick={() =>
                            setShowCurrentPassword((prev) => !prev)
                          }
                          className="absolute right-3 sm:right-4 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-blue-400 transition-colors duration-300 p-1.5 sm:p-2 touch-manipulation"
                        >
                          {showCurrentPassword ? (
                            <EyeOff size={18} className="sm:size-[20px]" />
                          ) : (
                            <Eye size={18} className="sm:size-[20px]" />
                          )}
                        </button>
                      </div>
                    </div>

                    <div className="relative">
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        New Password
                      </label>
                      <div className="relative">
                        <input
                          type={showNewPassword ? "text" : "password"}
                          placeholder="Enter new password"
                          className="w-full p-3 sm:p-4 pl-4 sm:pl-5 border border-[#393939] rounded-xl bg-[#232323] focus:bg-[#2d2d3d] focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-300 text-gray-200 text-sm sm:text-base"
                          value={transferPassword}
                          onChange={(e) => setTransferPassword(e.target.value)}
                        />
                        <button
                          type="button"
                          onClick={() => setShowNewPassword((prev) => !prev)}
                          className="absolute right-3 sm:right-4 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-blue-400 transition-colors duration-300 p-1.5 sm:p-2 touch-manipulation"
                        >
                          {showNewPassword ? (
                            <EyeOff size={18} className="sm:size-[20px]" />
                          ) : (
                            <Eye size={18} className="sm:size-[20px]" />
                          )}
                        </button>
                      </div>
                    </div>

                    <div className="relative">
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Confirm New Password
                      </label>
                      <div className="relative">
                        <input
                          type={showConfirmPassword ? "text" : "password"}
                          placeholder="Confirm new password"
                          className="w-full p-3 sm:p-4 pl-4 sm:pl-5 border border-[#393939] rounded-xl bg-[#232323] focus:bg-[#2d2d3d] focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-300 text-gray-200 text-sm sm:text-base"
                          value={confirmTransferPassword}
                          onChange={(e) =>
                            setConfirmTransferPassword(e.target.value)
                          }
                        />
                        <button
                          type="button"
                          onClick={() =>
                            setShowConfirmPassword((prev) => !prev)
                          }
                          className="absolute right-3 sm:right-4 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-blue-400 transition-colors duration-300 p-1.5 sm:p-2 touch-manipulation"
                        >
                          {showConfirmPassword ? (
                            <EyeOff size={18} className="sm:size-[20px]" />
                          ) : (
                            <Eye size={18} className="sm:size-[20px]" />
                          )}
                        </button>
                      </div>
                    </div>

                    <div className="mt-6 sm:mt-8 flex justify-end gap-2 sm:gap-3">
                      <button
                        onClick={resetAccountOption}
                        className="px-4 py-2 sm:px-5 sm:py-2.5 rounded-lg border border-[#393939] text-gray-300 text-xs sm:text-sm font-medium mr-3 hover:bg-[#2d2d3d] transition-colors duration-300"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={changeWalletPassword}
                        className="px-4 py-2 sm:px-5 sm:py-2.5 rounded-lg bg-blue-600 text-white text-xs sm:text-sm font-medium hover:bg-blue-700 transition-colors duration-300"
                      >
                        Change Password
                      </button>
                    </div>
                  </div>
                </div>
              ) : selectedAccountOption === "freeze-wallet" ? (
                <div className="animate-slideUpFade">
                  <div className="flex items-center mb-4 sm:mb-5">
                    <button
                      onClick={resetAccountOption}
                      className="p-1.5 sm:p-2 mr-3 rounded-full hover:bg-blue-900 transition-all duration-300 transform hover:scale-110 text-white"
                    >
                      <X size={20} className="text-blue-400 sm:size-[22px]" />
                    </button>
                    <h3 className="text-lg sm:text-xl font-bold text-gray-200">
                      {isWalletFrozen ? "Unfreeze Wallet" : "Freeze Wallet"}
                    </h3>
                  </div>

                  <div className="space-y-4 sm:space-y-5">
                    <div className="p-3 sm:p-4 rounded-xl bg-blue-900/30 border border-blue-800 text-blue-300">
                      <div className="flex items-start">
                        <Info className="h-4 w-4 sm:h-5 sm:w-5 text-blue-400 mt-0.5 mr-2" />
                        <p className="text-xs sm:text-sm">
                          {isWalletFrozen
                            ? "Your wallet is currently frozen. All transactions are blocked. Enter your wallet password to unfreeze it."
                            : "Freezing your wallet will temporarily block all transactions. This is useful if you suspect unauthorized access."}
                        </p>
                      </div>
                    </div>

                    {/* Only show password field when unfreezing the wallet */}
                    {isWalletFrozen && (
                      <div className="relative">
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          Wallet Password
                        </label>
                        <div className="relative">
                          <input
                            type={showCurrentPassword ? "text" : "password"}
                            placeholder="Enter wallet password"
                            className="w-full p-3 sm:p-4 pl-4 sm:pl-5 border border-[#393939] rounded-xl bg-[#232323] focus:bg-[#2d2d3d] focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-300 text-gray-200 text-sm sm:text-base"
                            value={walletPassword}
                            onChange={(e) => setWalletPassword(e.target.value)}
                          />
                          <button
                            type="button"
                            onClick={() =>
                              setShowCurrentPassword((prev) => !prev)
                            }
                            className="absolute right-3 sm:right-4 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-blue-400 transition-colors duration-300 p-1.5 sm:p-2 touch-manipulation"
                          >
                            {showCurrentPassword ? (
                              <EyeOff size={18} className="sm:size-[20px]" />
                            ) : (
                              <Eye size={18} className="sm:size-[20px]" />
                            )}
                          </button>
                        </div>
                      </div>
                    )}

                    <div className="mt-6 sm:mt-8 flex justify-end gap-2 sm:gap-3">
                      <button
                        onClick={resetAccountOption}
                        className="px-4 py-2 sm:px-5 sm:py-2.5 rounded-lg border border-[#393939] text-gray-300 text-xs sm:text-sm font-medium mr-3 hover:bg-[#2d2d3d] transition-colors duration-300"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={isWalletFrozen ? unfreezeWallet : freezeWallet}
                        className={`px-4 py-2 sm:px-5 sm:py-2.5 rounded-lg text-white text-xs sm:text-sm font-medium transition-colors duration-300 ${
                          isWalletFrozen
                            ? "bg-blue-600 hover:bg-blue-700"
                            : "bg-red-600 hover:bg-red-700"
                        }`}
                      >
                        {isWalletFrozen ? "Unfreeze Wallet" : "Freeze Wallet"}
                      </button>
                    </div>
                  </div>
                </div>
              ) : selectedAccountOption === "delete-account" ? (
                <div className="animate-slideUpFade">
                  <div className="flex items-center mb-4 sm:mb-5">
                    <button
                      onClick={resetAccountOption}
                      className="p-1.5 sm:p-2 mr-3 rounded-full hover:bg-red-900 transition-all duration-300 transform hover:scale-110 text-white"
                    >
                      <X size={20} className="text-red-400 sm:size-[22px]" />
                    </button>
                    <h3 className="text-lg sm:text-xl font-bold text-gray-200">
                      Delete Wallet Account
                    </h3>
                  </div>

                  <div className="space-y-4 sm:space-y-5">
                    <div className="p-3 sm:p-4 rounded-xl bg-red-900/20 border border-red-900/50 text-red-200">
                      <div className="flex items-start">
                        <AlertTriangle className="h-4 w-4 sm:h-5 sm:w-5 text-red-400 mt-0.5 mr-2" />
                        <div>
                          <p className="text-xs sm:text-sm font-medium mb-1 sm:mb-2">Warning: This action cannot be undone</p>
                          <p className="text-xs sm:text-sm">
                            Deleting your wallet will permanently remove all your data,
                            balances, and account information. Make sure you have backed
                            up your data before proceeding.
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Confirmation checkbox */}
                    <div className="flex items-center mt-3">
                      <input
                        type="checkbox"
                        id="confirm-delete"
                        checked={showFinalConfirmation}
                        onChange={() => setShowFinalConfirmation(!showFinalConfirmation)}
                        className="h-4 w-4 sm:h-5 sm:w-5 text-red-600 rounded border-gray-600 bg-gray-700 focus:ring-red-600"
                      />
                      <label
                        htmlFor="confirm-delete"
                        className="ml-2 sm:ml-3 text-xs sm:text-sm text-gray-300"
                      >
                        I understand this action cannot be reversed and I want to
                        permanently delete my wallet
                      </label>
                    </div>

                    <div className="mt-6 sm:mt-8 flex justify-end gap-2 sm:gap-3">
                      <button
                        onClick={resetAccountOption}
                        className="px-4 py-2 sm:px-5 sm:py-2.5 rounded-lg border border-[#393939] text-gray-300 text-xs sm:text-sm font-medium hover:bg-[#2d2d3d] transition-colors duration-300"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={confirmDeleteAccount}
                        disabled={!showFinalConfirmation}
                        className={`px-4 py-2 sm:px-5 sm:py-2.5 rounded-lg text-white text-xs sm:text-sm font-medium ${
                          showFinalConfirmation
                            ? "bg-red-600 hover:bg-red-700"
                            : "bg-red-900/50 cursor-not-allowed"
                        } transition-colors duration-300`}
                      >
                        Delete Account
                      </button>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          </div>

          {/* Two column layout for Security Status and other sections */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
            {/* Right Column - Other Content */}
            <div className="md:col-span-12">
              {/* Security Settings Card */}
              <div className="bg-[#2b2b2b] rounded-xl shadow-md border border-[#393939] overflow-hidden transition-all hover:shadow-lg mb-6">
                <div className="p-6">
                  <div className="flex-1">
                    <div className="flex justify-between items-center mb-4">
                      <h2 className="text-2xl font-bold text-gray-200">
                        Backup Codes
                      </h2>
                    </div>

                    {/* Security options - redesigned layout */}
                    <div className="space-y-4 mt-6">
                      {/* Backup Codes Card */}
                      <div className="bg-[#1a1e2e] border border-[#313b52] rounded-xl overflow-hidden">
                        <div className="flex items-center justify-between p-4">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-indigo-900 flex items-center justify-center text-indigo-400">
                              <KeySquare size={18} />
                            </div>
                            <div>
                              <p className="font-medium text-gray-200 text-base">
                                Backup Recovery Codes
                              </p>
                              <p className="text-xs text-gray-500">
                                {is2FAEnabled
                                  ? "Access your backup codes for account recovery"
                                  : "Enable 2FA to get backup recovery codes"}
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              onClick={viewBackupCodes}
                              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                                is2FAEnabled
                                  ? "bg-indigo-700 text-white hover:bg-indigo-800"
                                  : "bg-gray-700 text-gray-500 cursor-not-allowed"
                              }`}
                              disabled={!is2FAEnabled}
                            >
                              {isLoading ? (
                                <RefreshCw
                                  size={14}
                                  className="animate-spin inline mr-1"
                                />
                              ) : (
                                <Key size={14} className="inline mr-1" />
                              )}
                              View Backup Codes
                            </button>
                          </div>
                        </div>
                      </div>

                      {/* Additional information about backup codes */}
                      <div className="bg-blue-900 rounded-lg p-4 border border-blue-800">
                        <div className="flex items-start gap-3">
                          <Info className="text-blue-400 h-5 w-5 flex-shrink-0 mt-0.5" />
                          <div>
                            <p className="text-blue-200 text-sm font-medium">
                              About Backup Codes
                            </p>
                            <p className="text-xs text-blue-300 mt-1">
                              Backup codes allow you to access your account if
                              you lose your two-factor authentication device.
                              Keep these codes in a safe place. Each code can
                              only be used once.
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Custom Alert Component */}
      <CustomAlert
        showAlert={showAlert}
        alertMessage={alertMessage}
        alertType={alertType}
        setShowAlert={setShowAlert}
      />

      {/* Backup Codes Modal */}
      {showBackupCodesModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75 p-3 sm:p-4">
          <div className="bg-[#1e2839] rounded-2xl shadow-xl overflow-hidden w-[95%] sm:w-full max-w-xs sm:max-w-lg">
            <div className="p-4 sm:p-6 border-b border-gray-700 flex justify-between items-center">
              <h3 className="text-lg sm:text-xl font-bold text-white">Backup Codes</h3>
              <button
                onClick={closeBackupCodesModal}
                className="text-gray-400 hover:text-white hover:bg-gray-700 rounded-full p-1.5 transition-all duration-200 transform hover:rotate-90"
              >
                <X size={20} />
              </button>
            </div>
            <div className="p-4 sm:p-6">
              {!passwordVerified ? (
                <div className="animate-fadeIn">
                  <p className="text-sm sm:text-base text-gray-300 mb-5">
                    To view your backup codes, please enter your Secret Word for verification.
                  </p>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Secret Word
                      </label>
                      <input
                        type="password"
                        value={securityPassword}
                        onChange={(e) => setSecurityPassword(e.target.value)}
                        placeholder="Enter your Secret Word"
                        className="w-full p-3 sm:p-4 border border-[#3d4663] rounded-lg bg-[#2a2f45] text-sm sm:text-base text-gray-200 focus:ring-blue-600 focus:border-blue-600"
                      />
                    </div>
                    <button
                      onClick={verifySecurityPassword}
                      disabled={!securityPassword.trim()}
                      className={`w-full py-2.5 sm:py-3 rounded-lg font-medium text-sm sm:text-base transition-colors duration-300 ${
                        securityPassword.trim()
                          ? "bg-blue-600 hover:bg-blue-700 text-white"
                          : "bg-gray-700 text-gray-400 cursor-not-allowed"
                      }`}
                    >
                      Verify
                    </button>
                  </div>
                </div>
              ) : (
                <div className="animate-fadeIn">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="text-base sm:text-lg font-medium text-gray-200">
                      Your Backup Codes
                    </h4>
                    <button
                      onClick={copyBackupCodes}
                      className="flex items-center gap-1.5 text-xs sm:text-sm px-3 py-1.5 rounded-lg bg-blue-900/40 hover:bg-blue-800/60 text-blue-300 transition-colors duration-300"
                    >
                      <Copy size={14} className="sm:size-[16px]" />
                      {copiedToClipboard ? "Copied!" : "Copy All"}
                    </button>
                  </div>
                  <div className="bg-[#2a2f45] p-3 sm:p-4 rounded-lg border border-[#3d4663] mb-4">
                    <div className="grid grid-cols-2 gap-2 sm:gap-3">
                      {backupCodes.map((code, index) => (
                        <div
                          key={index}
                          className="p-2 sm:p-3 bg-[#1e2839] rounded-lg border border-[#3d4663] text-xs sm:text-sm text-gray-300 font-mono"
                        >
                          {code}
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="text-xs sm:text-sm text-gray-400 bg-[#2a2f45]/50 p-3 sm:p-4 rounded-lg border border-[#3d4663]">
                    <div className="flex items-start gap-2">
                      <Info className="text-blue-400 mt-0.5 h-4 w-4 sm:h-5 sm:w-5 flex-shrink-0" />
                      <p>
                        These backup codes can be used once each to access your
                        account if you lose your two-factor authentication
                        device. Keep them in a safe place.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Unfreeze Wallet Dialog */}
      {showUnfreezeDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-70 backdrop-blur-sm flex items-center justify-center z-50 p-3 sm:p-4 animate-fadeIn">
          <div className="bg-[#2b2b2b] rounded-2xl sm:rounded-3xl shadow-2xl overflow-hidden w-[95%] sm:w-full max-w-md border border-[#393939]">
            <div className="p-4 sm:p-6 flex justify-between items-center border-b border-[#393939] sticky top-0">
              <div className="flex items-center gap-2 sm:gap-4">
                <div className="p-2 sm:p-3 bg-cyan-900/40 rounded-full">
                  <SnowflakeIcon className="text-cyan-400 h-4 w-4 sm:h-6 sm:w-6" />
                </div>
                <h2 className="text-base sm:text-xl font-bold text-gray-200">
                  Unfreeze Wallet
                </h2>
              </div>
              <button
                onClick={() => setShowUnfreezeDialog(false)}
                className="text-gray-400 hover:text-gray-200 hover:bg-gray-700 rounded-full p-1 sm:p-1.5 transition-all duration-200 transform hover:rotate-90"
              >
                <X size={18} className="sm:size-[22px]" />
              </button>
            </div>

            <div className="px-4 sm:px-5 py-3 sm:py-4 space-y-3 sm:space-y-5">
              <div className="space-y-3 sm:space-y-4">
                <p className="text-gray-300 text-xs sm:text-base">
                  Enter your wallet password to unfreeze your wallet.
                </p>
                <div className="space-y-2">
                  <label
                    htmlFor="walletPassword"
                    className="block text-xs sm:text-sm font-medium text-gray-300"
                  >
                    Wallet Password
                  </label>
                  <input
                    type="password"
                    id="walletPassword"
                    value={walletPassword}
                    onChange={(e) => setWalletPassword(e.target.value)}
                    className="w-full p-2 sm:p-2.5 bg-[#232323] border border-[#393939] rounded-lg text-xs sm:text-sm text-gray-200 placeholder-gray-500 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500"
                    placeholder="Enter your wallet password"
                  />
                </div>
                <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
                  <button
                    onClick={() => setShowUnfreezeDialog(false)}
                    className="flex-1 px-3 sm:px-4 py-2 sm:py-2.5 bg-gray-700 hover:bg-gray-800 text-white text-xs sm:text-sm font-medium rounded-lg transition-colors duration-300"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => {
                      unfreezeWallet();
                    }}
                    disabled={!walletPassword.trim()}
                    className={clsx(
                      "flex-1 px-3 sm:px-4 py-2 sm:py-2.5 rounded-lg text-white text-xs sm:text-sm font-medium flex items-center justify-center gap-2 transition-colors duration-300",
                      walletPassword.trim()
                        ? "bg-cyan-700 hover:bg-cyan-800"
                        : "bg-gray-700 cursor-not-allowed"
                    )}
                  >
                    Unfreeze
                  </button>
                </div>
              </div>
            </div>
          </div>
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
        
        @keyframes slideUpFade {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-slideUpFade {
          animation: slideUpFade 0.4s ease-out forwards;
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
};

export default Settings;


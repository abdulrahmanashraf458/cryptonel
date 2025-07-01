import React, { useState, useEffect, useRef } from "react";
import {
  Database,
  AlertCircle,
  Info,
  CheckCircle,
  X,
  Clock,
  RefreshCw,
  FileCheck,
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
  if (!showAlert) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-80 backdrop-blur-md flex items-center justify-center z-50 p-2 sm:p-4 animate-fadeIn">
      <div className="bg-[#1e2839] rounded-2xl sm:rounded-3xl shadow-2xl overflow-hidden w-[95%] sm:w-full max-w-xs sm:max-w-md">
        <div
          className={clsx(
            "px-4 py-3 sm:px-6 sm:py-5 flex justify-between items-center",
            "border-b border-gray-700"
          )}
        >
          <div className="flex items-center gap-2 sm:gap-4">
            <div
              className={clsx(
                "p-2 sm:p-3 rounded-full",
                alertType === "success"
                  ? "bg-green-900/40"
                  : alertType === "error"
                  ? "bg-red-900/40"
                  : "bg-blue-900/40"
              )}
            >
              {alertType === "success" ? (
                <CheckCircle className="text-green-400 h-4 w-4 sm:h-6 sm:w-6" />
              ) : alertType === "error" ? (
                <AlertCircle className="text-red-400 h-4 w-4 sm:h-6 sm:w-6" />
              ) : (
                <Info className="text-blue-400 h-4 w-4 sm:h-6 sm:w-6" />
              )}
            </div>
            <h2 className="text-base sm:text-xl font-bold text-white">
              {alertType === "success"
                ? "Success"
                : alertType === "error"
                ? "Warning"
                : "Information"}
            </h2>
          </div>
          <button
            onClick={() => setShowAlert(false)}
            className="text-gray-400 hover:text-white hover:bg-gray-700 rounded-full p-1 sm:p-1.5 transition-all duration-200 transform hover:rotate-90"
          >
            <X size={18} className="h-4 w-4 sm:h-5 sm:w-5" />
          </button>
        </div>

        <div className="p-4 sm:p-7">
          <p className="text-xs sm:text-base text-gray-300 mb-4 sm:mb-6">
            {alertMessage}
          </p>

          <div className="flex justify-end">
            <button
              onClick={() => setShowAlert(false)}
              className={clsx(
                "px-4 py-2 sm:px-5 sm:py-2.5 rounded-full transition-all duration-300 min-w-[80px] sm:min-w-[100px] font-medium shadow-sm hover:shadow text-sm sm:text-base",
                alertType === "success"
                  ? "bg-green-700 hover:bg-green-800 text-white"
                  : alertType === "error"
                  ? "bg-red-700 hover:bg-red-800 text-white"
                  : "bg-blue-700 hover:bg-blue-800 text-white"
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

const Backup = () => {
  const [includeWallet, setIncludeWallet] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [fetchingStatus, setFetchingStatus] = useState(true);
  const [animateBalance, setAnimateBalance] = useState(false);
  const [animateSection, setAnimateSection] = useState(false);
  const [backupCode, setBackupCode] = useState("");
  const [countdown, setCountdown] = useState<string | null>(null);
  const countdownIntervalRef = useRef<NodeJS.Timeout | null>(null);
  
  // Add CSRF token state
  const [csrfToken, setCsrfToken] = useState<string>('');
  
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
  
  const [showAlert, setShowAlert] = useState(false);
  const [alertMessage, setAlertMessage] = useState("");
  const [alertType, setAlertType] = useState<"success" | "error" | "info">("success");
  
  // Always start with isPremium as false and get it from the server
  const [isPremium, setIsPremium] = useState<boolean>(false);

  // Animation and data loading effect
  useEffect(() => {
    // Always reset isPremium to false when component mounts to prevent incorrect persistence
    setIsPremium(false);
    
    setAnimateBalance(true);

    setTimeout(() => {
      setAnimateSection(true);
    }, 300);

    // Fetch CSRF token first
    const fetchCsrfToken = async () => {
      try {
        const response = await fetch('/api/csrf-token', {
          credentials: 'include'
        });
        const data = await response.json();
        if (data.success && data.csrf_token) {
          setCsrfToken(data.csrf_token);
        } else {
          console.error('Failed to fetch CSRF token:', data.error || 'Unknown error');
        }
      } catch (error) {
        console.error('CSRF token fetch error:', error);
      }
    };

    // Load initial data with force refresh
    const initializeData = async () => {
      await fetchCsrfToken();
      await fetchBackupStatus(true);
    };

    initializeData();

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
  const fetchBackupStatus = async (forceRefresh = false) => {
    setFetchingStatus(true);
    try {
      // Add cache-busting parameter when force refreshing
      const url = forceRefresh 
        ? `/api/backup/status?_=${new Date().getTime()}` 
        : "/api/backup/status";
        
      const response = await axios.get(url, {
        headers: {
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache',
          'Expires': '0',
          'X-CSRF-Token': csrfToken
        },
        withCredentials: true
      });
      
      setBackupStatus(response.data);
      
      // Update premium status if available in the response
      if (response.data.isPremium !== undefined) {
        setIsPremium(response.data.isPremium);
        console.log("Premium status set to:", response.data.isPremium);
      } else {
        // If isPremium is not in the response, default to false
        setIsPremium(false);
        console.log("Premium status not found in response, defaulting to false");
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
      // Reset premium status on error
      setIsPremium(false);
      setNotification({
        show: true,
        type: "error",
        message: "Failed to load backup status. Please try again later.",
      });
    } finally {
      setFetchingStatus(false);
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

      // Use Axios to make a POST request with responseType blob to handle file download
      const response = await axios.post("/api/backup/create", formData, {
        responseType: "blob", // Important: tells axios to handle response as binary data
        headers: {
          'X-CSRF-Token': csrfToken
        },
        withCredentials: true
      });

      // Create a URL for the blob
      const url = window.URL.createObjectURL(new Blob([response.data]));
      
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

      // Reset backup code input after successful download
      setBackupCode("");

      // Show success notification
      setNotification({
        show: true,
        type: "success",
        message: "Wallet backup file downloaded successfully as TXT!",
      });

      // Immediately refresh the backup status to show updated last backup and cooldown
      await fetchBackupStatus(true);

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

      // Handle different response types for error
      if (axios.isAxiosError(error) && error.response) {
        // If it's a blob response that contains an error
        if (error.response.data instanceof Blob && error.response.data.type === 'application/json') {
          // Convert blob to text to parse JSON error
          const text = await error.response.data.text();
          try {
            const errorData = JSON.parse(text);
            
            // Handle rate limit error
            if (error.response.status === 429) {
              setRateLimitError({
                isLimited: true,
                message: errorData.error || "Rate limited, please try again later",
                timeRemaining: errorData.time_remaining || 60,
                formattedTime: errorData.formatted_time_remaining || formatRateLimitTime(errorData.time_remaining || 60),
                type: errorData.days_remaining ? "cooldown" : "attempts",
              });
            } 
            // Handle invalid backup code error (400)
            else if (error.response.status === 400 && errorData.remaining_attempts !== undefined) {
              // This is specifically for incorrect backup code
              setNotification({
                show: true,
                type: "error",
                message: errorData.error || "Invalid backup code",
              });
              
              // Show more visible warning with custom alert
              showCustomAlert(
                `Incorrect backup code. You have ${errorData.remaining_attempts} attempts remaining.`, 
                "error"
              );
              
              // Clear the incorrect backup code for security
              setBackupCode("");
            } 
            else {
              // Handle other errors
              setNotification({
                show: true,
                type: "error",
                message: errorData.error || "Failed to create backup file",
              });
            }
          } catch (e) {
            // If the response is not valid JSON
            setNotification({
              show: true,
              type: "error",
              message: "Failed to create backup file. Please try again later.",
            });
          }
        } else if (error.response.data && typeof error.response.data === 'object') {
          // Direct JSON response handling
          const errorData = error.response.data;
          
          // Handle rate limit error
          if (error.response.status === 429) {
            setRateLimitError({
              isLimited: true,
              message: errorData.error || "Rate limited, please try again later",
              timeRemaining: errorData.time_remaining || 60,
              formattedTime: errorData.formatted_time_remaining || formatRateLimitTime(errorData.time_remaining || 60),
              type: errorData.days_remaining ? "cooldown" : "attempts",
            });
          } 
          // Handle invalid backup code error (400)
          else if (error.response.status === 400 && errorData.remaining_attempts !== undefined) {
            // This is specifically for incorrect backup code
            setNotification({
              show: true,
              type: "error",
              message: errorData.error || "Invalid backup code",
            });
            
            // Show more visible warning with custom alert
            showCustomAlert(
              `Incorrect backup code. You have ${errorData.remaining_attempts} attempts remaining.`, 
              "error"
            );
            
            // Clear the incorrect backup code for security
            setBackupCode("");
          } 
          else {
            // Handle other errors
            setNotification({
              show: true,
              type: "error",
              message: errorData.error || "Failed to create backup file",
            });
          }
        } else {
          // Generic error handling
          setNotification({
            show: true,
            type: "error",
            message: "Failed to create backup file. Please try again later.",
          });
        }
      } else {
        // Handle non-Axios errors
        setNotification({
          show: true,
          type: "error",
          message: "Failed to create backup file. Please try again later.",
        });
      }

      // Always refresh backup status to ensure we have the latest state
      try {
        await fetchBackupStatus(true);
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

  // Add a refresh button to allow users to manually refresh status
  const handleRefreshStatus = () => {
    fetchBackupStatus(true);
  };

  return (
    <div className="min-h-screen bg-[#262626] py-4 sm:py-6 md:py-10 px-3 sm:px-4">
      <div className="container mx-auto">
        {/* Header with left alignment */}
        <div className="mb-5 sm:mb-8 text-left">
          <h1
            className={clsx(
              "text-2xl sm:text-3xl font-bold text-gray-200 mb-1 sm:mb-2",
              "transition-all duration-700",
              animateBalance
                ? "translate-y-0 opacity-100"
                : "translate-y-4 opacity-0"
            )}
          >
            Wallet Backup
          </h1>
          <p
            className={clsx(
              "text-sm sm:text-base text-gray-400 transition-all duration-700 delay-200",
              animateBalance
                ? "translate-y-0 opacity-100"
                : "translate-y-4 opacity-0"
            )}
          >
            Secure your wallet data with regular backups
          </p>
        </div>

        {/* Notification toast */}
        {notification.show && (
          <div
            className={clsx(
              "fixed top-2 sm:top-6 right-2 sm:right-6 max-w-[calc(100%-1rem)] sm:max-w-md p-3 sm:p-4 rounded-lg shadow-lg border flex items-start gap-2 sm:gap-3 z-50 animate-scaleIn",
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
              <X size={14} className="h-3 w-3 sm:h-4 sm:w-4" />
            </button>
          </div>
        )}

        {/* Main content with better layout */}
        <div className="grid grid-cols-1 gap-4 sm:gap-6">
          {/* Backup Card */}
          <div
            className={clsx(
              "bg-[#2b2b2b] rounded-lg sm:rounded-xl shadow-md border border-[#393939] overflow-hidden transition-all hover:shadow-lg mb-4 sm:mb-6",
              "transition-all duration-700",
              animateSection
                ? "translate-y-0 opacity-100"
                : "translate-y-10 opacity-0"
            )}
          >
            <div className="p-4 sm:p-6">
              <div className="flex-1">
                <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center mb-2">
                  <h2 className="text-xl sm:text-2xl font-bold text-gray-200 mb-2 sm:mb-0">
                    Wallet Backup Download
                  </h2>
                  {isPremium && (
                    <div className="px-3 py-1 bg-gradient-to-r from-amber-500 to-yellow-700 text-white text-xs font-bold rounded-full self-start sm:self-auto">
                      PREMIUM
                    </div>
                  )}
                </div>
                <p className="text-sm sm:text-base text-gray-400 mb-4">
                  {isPremium 
                    ? "Premium users can create backups anytime with enhanced formatting" 
                    : "Download your wallet data as a well-formatted text file (available every 14 days)"
                  }
                </p>

                <div className="animate-fadeIn">
                  <div className="space-y-4 sm:space-y-5">
                    {/* Wallet Information toggle */}
                    <div className="flex items-center justify-between bg-[#1a1e2e] p-2.5 sm:p-3 rounded-lg sm:rounded-xl border border-[#313b52]">
                      <div className="flex items-center gap-2 sm:gap-3">
                        <div className={`w-8 h-8 sm:w-10 sm:h-10 rounded-lg sm:rounded-xl ${isPremium ? 'bg-amber-900' : 'bg-indigo-900'} flex items-center justify-center ${isPremium ? 'text-amber-400' : 'text-indigo-400'}`}>
                          <Database size={14} className="h-4 w-4 sm:h-5 sm:w-5" />
                        </div>
                        <div>
                          <p className="font-medium text-gray-200 text-sm sm:text-base">
                            Wallet Information
                          </p>
                          <p className="text-xs text-gray-500 hidden sm:block">
                            {isPremium ? "Premium backup includes enhanced data" : "Your personal wallet details"}
                          </p>
                        </div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={includeWallet}
                          onChange={(e) =>
                            setIncludeWallet(e.target.checked)
                          }
                          className="sr-only peer"
                        />
                        <div className={`w-9 h-5 sm:w-11 sm:h-6 bg-gray-700 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-600 after:border after:rounded-full after:h-4 after:w-4 sm:after:h-5 sm:after:w-5 after:transition-all ${isPremium ? 'peer-checked:bg-amber-700' : 'peer-checked:bg-blue-700'}`}></div>
                      </label>
                    </div>

                    {/* Improved backup code input interface */}
                    <div className={`bg-[#1a1e2e] p-3 sm:p-4 rounded-lg sm:rounded-xl border ${isPremium ? 'border-amber-800' : 'border-[#313b52]'}`}>
                      <label className="block text-gray-300 text-xs sm:text-sm font-medium mb-2">
                        Backup Code
                      </label>
                      <input
                        type="text"
                        value={backupCode}
                        onChange={(e) => {
                          // Limit length to 64 characters and sanitize input
                          const sanitized = e.target.value
                            .replace(/[^\w\d-]/g, '') // Only allow alphanumeric and dash
                            .slice(0, 64); // Limit to 64 chars
                          setBackupCode(sanitized);
                        }}
                        placeholder="Enter your backup code"
                        className={`bg-[#2a2f45] w-full rounded-lg p-2.5 sm:p-3 text-sm sm:text-base text-gray-200 border ${isPremium ? 'border-amber-900 focus:ring-amber-600' : 'border-[#3d4663] focus:ring-blue-600'} focus:outline-none focus:ring-2 focus:border-transparent`}
                        disabled={isLoading}
                        maxLength={64} // Add explicit maxLength
                        autoComplete="off" // Disable autocomplete for security
                      />
                      <p className="mt-1.5 sm:mt-2 text-xs text-gray-500">
                        Enter the secure backup code to download your data
                      </p>
                    </div>

                    <div className="flex gap-3 sm:gap-4">
                      <button
                        onClick={handleDownloadBackup}
                        disabled={
                          isLoading ||
                          !backupCode.trim() ||
                          !includeWallet ||
                          rateLimitError.isLimited
                        }
                        className={clsx(
                          "flex-1 px-4 sm:px-6 py-3 sm:py-4 rounded-lg sm:rounded-xl text-sm sm:text-base text-white font-medium flex items-center justify-center gap-1.5 sm:gap-2 shadow-md transition-all",
                          rateLimitError.isLimited
                            ? "bg-red-700 cursor-not-allowed"
                            : !isPremium && !backupStatus.canCreateBackup
                            ? "bg-gray-700 cursor-not-allowed"
                            : isPremium
                            ? "bg-gradient-to-r from-amber-600 to-yellow-700 hover:shadow-lg"
                            : "bg-gradient-to-r from-blue-700 to-indigo-700 hover:shadow-lg",
                          (isLoading ||
                            !backupCode.trim() ||
                            !includeWallet ||
                            rateLimitError.isLimited) &&
                            "opacity-70"
                        )}
                      >
                        {isLoading ? (
                          <>
                            <div className="h-3 w-3 sm:h-4 sm:w-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                            <span>Downloading...</span>
                          </>
                        ) : rateLimitError.isLimited ? (
                          <>
                            <AlertCircle size={14} className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                            <span className="text-xs sm:text-sm">
                              Try again in{" "}
                              <span className="font-mono">
                                {rateLimitError.formattedTime}
                              </span>
                            </span>
                          </>
                        ) : !isPremium && !backupStatus.canCreateBackup ? (
                          <>
                            <Clock size={14} className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                            {backupStatus.daysRemaining !== undefined && backupStatus.daysRemaining > 0 ? (
                              <span className="text-xs sm:text-sm">
                                Available in {backupStatus.daysRemaining} days
                              </span>
                            ) : (
                              <span className="text-xs sm:text-sm">
                                Waiting for cooldown
                              </span>
                            )}
                          </>
                        ) : (
                          <>
                            <FileCheck size={14} className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                            <span className="text-xs sm:text-sm">{isPremium ? "Download Premium Backup" : "Download TXT Backup"}</span>
                          </>
                        )}
                      </button>
                    </div>

                    {!isPremium && (
                      <div className="mt-1 sm:mt-2 p-2.5 sm:p-3 bg-blue-900/30 border border-blue-800 rounded-lg">
                        <div className="flex items-start gap-1.5 sm:gap-2">
                          <Info className="h-4 w-4 sm:h-5 sm:w-5 text-blue-400 mt-0.5 flex-shrink-0" />
                          <p className="text-xs sm:text-sm text-blue-300">
                            Regular users can create backups every 14 days. 
                            {backupStatus.daysRemaining !== undefined && backupStatus.daysRemaining > 0 ? (
                              <span className="font-medium">
                                {" "}Next backup available in {backupStatus.daysRemaining} days
                                {backupStatus.formattedTimeRemaining && (
                                  <span className="font-mono text-xs"> ({backupStatus.formattedTimeRemaining})</span>
                                )}
                              </span>
                            ) : !backupStatus.canCreateBackup ? (
                              <span className="font-medium"> Please wait for the cooldown period.</span>
                            ) : (
                              <span className="font-medium"> You can create a backup now.</span>
                            )}
                            <span className="block mt-1 font-medium">Upgrade to premium for unlimited backups!</span>
                          </p>
                        </div>
                      </div>
                    )}
                    
                    {isPremium && (
                      <div className="mt-1 sm:mt-2 p-2.5 sm:p-3 bg-amber-900/30 border border-amber-800 rounded-lg">
                        <div className="flex items-start gap-1.5 sm:gap-2">
                          <Info className="h-4 w-4 sm:h-5 sm:w-5 text-amber-400 mt-0.5 flex-shrink-0" />
                          <p className="text-xs sm:text-sm text-amber-300">
                            As a premium user, you can create unlimited backups with enhanced formatting.
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Information Card */}
          <div
            className={clsx(
              "bg-[#2b2b2b] rounded-lg sm:rounded-xl shadow-md border border-[#393939] overflow-hidden transition-all hover:shadow-lg mb-4 sm:mb-6",
              "transition-all duration-700 delay-300",
              animateSection
                ? "translate-y-0 opacity-100"
                : "translate-y-10 opacity-0"
            )}
          >
            <div className="p-4 sm:p-6">
              <div className="flex-1">
                <h2 className="text-lg sm:text-xl font-bold text-gray-200 mb-3 sm:mb-4">
                  Backup Information
                </h2>

                <div className="space-y-3 sm:space-y-4">
                  <div className="bg-[#1a1e2e] p-3 sm:p-4 rounded-lg sm:rounded-xl border border-[#313b52]">
                    <h3 className="text-base sm:text-lg font-medium text-gray-200 mb-1 sm:mb-2">Why Regular Backups Are Important</h3>
                    <p className="text-xs sm:text-sm text-gray-400">
                      Regular backups protect your wallet from data loss due to device failure, 
                      accidental deletion, or other unexpected events. We recommend creating a 
                      backup at least once per month or after significant transactions.
                    </p>
                  </div>

                  <div className="bg-[#1a1e2e] p-3 sm:p-4 rounded-lg sm:rounded-xl border border-[#313b52]">
                    <h3 className="text-base sm:text-lg font-medium text-gray-200 mb-1 sm:mb-2">How to Store Your Backup</h3>
                    <p className="text-xs sm:text-sm text-gray-400">
                      Store your backup file in a secure location such as an encrypted drive, 
                      password manager, or offline storage device. Never share your backup code 
                      or file with anyone, as it contains sensitive wallet information.
                    </p>
                  </div>

                  <div className="bg-[#1a1e2e] p-3 sm:p-4 rounded-lg sm:rounded-xl border border-[#313b52]">
                    <h3 className="text-base sm:text-lg font-medium text-gray-200 mb-1 sm:mb-2">Premium Backup Benefits</h3>
                    <p className="text-xs sm:text-sm text-gray-400">
                      Premium users enjoy unlimited backup creation without waiting periods, 
                      enhanced data formatting, and additional wallet data protection features. 
                      Consider upgrading for maximum security and convenience.
                    </p>
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
      `}</style>
    </div>
  );
};

export default Backup; 
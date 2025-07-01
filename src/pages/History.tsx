import React, { useState, useEffect, useMemo, useCallback, useRef } from "react";
import {
  ArrowDown,
  ArrowUp,
  DollarSign,
  Search,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Info,
  ChevronDown,
  ArrowUpRight,
  ArrowDownRight,
  ArrowRightLeft,
  Calendar,
  Download,
  Check,
  Clipboard,
} from "lucide-react";
import axios from "axios";
import { format, parseISO } from "date-fns";

// Type definitions
interface Transaction {
  tx_id: string;
  type: "sent" | "received";
  amount: string;
  timestamp: { $date: string };
  counterparty_address: string;
  counterparty_public_address: string;
  counterparty_id: string;
  formatted_date: string;
  display_address: string;
  counterparty_username?: string;
  sender_username?: string;
  sender_id?: string;
  recipient_username?: string;
  recipient_id?: string;
  status: string;
  fee: string;
  reason: string;
  tax?: string;
}

interface Summary {
  total_transactions: number;
  total_sent: string;
  total_received: string;
  sent_count: number;
  received_count: number;
  largest_transaction: string;
  balance: string;
  recent_activity: {
    week: number;
    month: number;
    year: number;
  };
}

interface Pagination {
  page: number;
  per_page: number;
  total_count: number;
  total_pages: number;
}

interface ApiResponse {
  transactions: Transaction[];
  summary: Summary;
  pagination: Pagination;
}

interface DateRange {
  startDate: string;
  endDate: string;
}

// Format amount functions for display
const formatFullAmount = (amount: string) => {
  try {
    const numAmount = parseFloat(amount);
    // Always display with 8 decimal places in detailed view
    return numAmount.toFixed(8);
  } catch (e) {
    return amount;
  }
};

// Format amount for compact display
const formatCompactAmount = (amount: string) => {
  try {
    const numAmount = parseFloat(amount);
    // If it's a whole number, display without decimals
    if (Number.isInteger(numAmount)) {
      return numAmount.toString();
    }
    // For all decimals, show exactly 2 decimal places
    return numAmount.toFixed(2);
  } catch (e) {
    return amount;
  }
};

// Stat card component
const StatCard: React.FC<{
  title: string;
  value: string | number;
  icon: React.ReactNode;
  color: string;
  subtext?: string;
}> = ({ title, value, icon, color, subtext }) => {
  const valueDisplay =
    typeof value === "string" && value.includes("CRN")
      ? value.replace(" CRN", "")
      : value;

  const showCRN = typeof value === "string" && value.includes("CRN");

  return (
    <div className="bg-[#2b2b2b] rounded-2xl shadow-lg p-4 sm:p-6 transition-all duration-300 hover:shadow-2xl overflow-hidden">
      <div className="flex justify-between items-start mb-2">
        <h2 className="text-[#FFFFFF] font-semibold text-base">{title}</h2>
        <div
          className={`${color} w-10 h-10 flex items-center justify-center rounded-xl flex-shrink-0`}
        >
          {icon}
        </div>
      </div>
      <div className="flex items-baseline">
        <span className="text-3xl sm:text-4xl font-bold text-white">
          {valueDisplay}
        </span>
        {showCRN && (
          <span className="text-[#8B5CF6] font-medium ml-2">CRN</span>
        )}
      </div>
      {subtext && (
        <div className="flex mt-1 text-sm">
          {subtext.includes("sent") ? (
            <>
              <span className="text-rose-400 mr-1">
                {subtext.split(",")[0]}
              </span>
              <span className="text-emerald-400">{subtext.split(",")[1]}</span>
            </>
          ) : (
            <span className="text-[#C4C4C7]">{subtext}</span>
          )}
        </div>
      )}
    </div>
  );
};

// Copy button component with better styling
const CopyButton: React.FC<{ text: string }> = ({ text }) => {
  const [copySuccess, setCopySuccess] = useState(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const isMounted = useRef(true);

  // Add cleanup when component unmounts
  useEffect(() => {
    return () => {
      isMounted.current = false;
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, []);

  const handleCopy = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    
    navigator.clipboard.writeText(text).then(() => {
      // Only update state if component is still mounted
      if (!isMounted.current) return;
      
      setCopySuccess(true);
      
      // Clear existing timer if it exists
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
      
      // Set new timer
      timerRef.current = setTimeout(() => {
        if (!isMounted.current) return;
        setCopySuccess(false);
        timerRef.current = null;
      }, 1500);
    });
  }, [text]);

  return (
    <button
      className={`transition-all duration-200 absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-md hover:bg-[#3a3a3a] focus:outline-none focus:ring-2 focus:ring-[#8B5CF6] ${
        copySuccess ? 'bg-emerald-500/20 text-emerald-400' : 'bg-[#353535] text-[#C4C4C7]'
      }`}
      onClick={handleCopy}
      title="Copy to clipboard"
    >
      {copySuccess ? (
        <Check size={16} className="animate-pulse" />
      ) : (
        <Clipboard size={16} />
      )}
    </button>
  );
};

// Transaction row component
const TransactionRow: React.FC<{ 
  transaction: Transaction;
  activeTransactionId: string | null;
  setActiveTransactionId: (id: string | null) => void;
}> = React.memo(({
  transaction,
  activeTransactionId,
  setActiveTransactionId
}) => {
  const [isAnimating, setIsAnimating] = useState(false);
  const isMounted = useRef(true);
  
  // Add cleanup for preventing state updates after unmount
  useEffect(() => {
    return () => {
      isMounted.current = false;
    };
  }, []);

  const toggleDetails = useCallback(() => {
    setIsAnimating(true);
    if (activeTransactionId === transaction.tx_id) {
      setActiveTransactionId(null);
    } else {
      setActiveTransactionId(transaction.tx_id);
    }
    
    // Use safe timeout that checks if component is still mounted
    const timer = setTimeout(() => {
      if (isMounted.current) {
        setIsAnimating(false);
      }
    }, 300);
    
    return () => clearTimeout(timer);
  }, [activeTransactionId, transaction.tx_id, setActiveTransactionId]);

  const isActive = activeTransactionId === transaction.tx_id;

  const formattedDate = useMemo(() => {
    if (
      transaction.formatted_date &&
      transaction.formatted_date !== "Unknown date"
    ) {
      return transaction.formatted_date;
    }

    if (transaction.timestamp) {
      try {
        if (
          typeof transaction.timestamp === "object" &&
          "$date" in transaction.timestamp
        ) {
          return format(
            parseISO(transaction.timestamp.$date),
            "yyyy-MM-dd HH:mm"
          );
        }
      } catch (e) {
        console.error("Error formatting date:", e);
      }
    }

    return "Unknown date";
  }, [transaction.formatted_date, transaction.timestamp]);

  const amountValue = transaction.amount;
  const feeValue = transaction.fee || "0";

  const amountWithSign = transaction.type === "sent" 
    ? `-${formatCompactAmount(amountValue)}` 
    : `+${formatCompactAmount(amountValue)}`;

  const fullAmountWithSign = transaction.type === "sent"
    ? `-${formatFullAmount(amountValue)}`
    : `+${formatFullAmount(amountValue)}`;

  const counterpartyDisplay =
    transaction.display_address ||
    (transaction.counterparty_public_address
      ? `${transaction.counterparty_public_address.substring(
          0,
          4
        )}..${transaction.counterparty_public_address.slice(-2)}`
      : "Unknown");

  return (
    <div className="border-b border-[#2E2E3E] last:border-b-0 overflow-hidden transition-all duration-300 mb-4 rounded-xl bg-[#2b2b2b] shadow-lg hover:shadow-xl">
      <div
        className={`p-4 sm:p-5 hover:bg-[#323232] cursor-pointer transition-all duration-300 ${
          isActive ? "bg-[#323232]" : ""
        }`}
        onClick={toggleDetails}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 sm:gap-4">
            <div
              className={`p-2 sm:p-2.5 rounded-xl transition-colors duration-300 ${
                transaction.type === "sent"
                  ? "bg-rose-500/15"
                  : "bg-emerald-500/15"
              }`}
            >
              {transaction.type === "sent" ? (
                <ArrowUp className="text-rose-400" size={18} />
              ) : (
                <ArrowDown className="text-emerald-400" size={18} />
              )}
            </div>
            <div>
              <div className="text-sm sm:text-base font-medium text-white">
                {transaction.type === "sent" ? "Sent to" : "Received from"}{" "}
                {counterpartyDisplay}
              </div>
              <div className="text-xs sm:text-sm text-[#C4C4C7]">
                {formattedDate}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            <div className="flex flex-col items-end">
              <div
                className={`text-sm sm:text-base font-bold ${
                  transaction.type === "sent"
                    ? "text-rose-400"
                    : "text-emerald-400"
                }`}
              >
                {amountWithSign} CRN
              </div>
              {parseFloat(feeValue) > 0 && (
                <div className="text-xs text-[#C4C4C7]">
                  Fee: {formatCompactAmount(feeValue)} CRN
                </div>
              )}
            </div>
            <ChevronDown
              size={16}
              className={`text-[#C4C4C7] transition-transform duration-300 ${
                isActive ? "transform rotate-180" : ""
              } ${isAnimating ? "animate-pulse" : ""}`}
            />
          </div>
        </div>
      </div>

      <div
        className={`overflow-hidden transition-all duration-300 ease-in-out ${
          isActive
            ? "max-h-[800px] opacity-100 border-t border-[#2E2E3E]"
            : "max-h-0 opacity-0"
        }`}
      >
        <div className="p-6 bg-[#323232] space-y-5">
          {/* Transaction ID - enhanced design */}
          <div className="grid grid-cols-1 gap-4">
            <div className="relative">
              <div className="text-xs text-[#C4C4C7] mb-1.5">Transaction ID</div>
              <div className="relative text-sm text-white font-medium bg-[#262626] p-3.5 pr-12 rounded-lg">
                <span className="break-all">{transaction.tx_id}</span>
                <CopyButton text={transaction.tx_id} />
              </div>
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-5">
            <div>
              <div className="text-xs text-[#C4C4C7] mb-1.5">Status</div>
              <div className="text-sm text-white font-medium flex items-center p-2 bg-[#262626] rounded-lg">
                <span className={`inline-block w-2.5 h-2.5 rounded-full mr-2.5 ${
                  transaction.status === "completed" ? "bg-emerald-400" : 
                  transaction.status === "pending" ? "bg-yellow-400" : 
                  transaction.status === "failed" ? "bg-red-400" : "bg-gray-400"
                }`}></span>
                <span className="capitalize">{transaction.status}</span>
              </div>
            </div>
            
            <div>
              <div className="text-xs text-[#C4C4C7] mb-1.5">Date & Time</div>
              <div className="text-sm text-white font-medium p-2 bg-[#262626] rounded-lg">
                {formattedDate}
              </div>
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-5">
            <div>
              <div className="text-xs text-[#C4C4C7] mb-1.5">Amount</div>
              <div className={`text-sm font-medium p-2 bg-[#262626] rounded-lg ${
                transaction.type === "sent" ? "text-rose-400" : "text-emerald-400"
              }`}>
                {fullAmountWithSign} CRN
              </div>
            </div>
            <div>
              <div className="text-xs text-[#C4C4C7] mb-1.5">Fee</div>
              <div className="text-sm text-white font-medium p-2 bg-[#262626] rounded-lg">
                {parseFloat(feeValue) > 0 
                  ? `${formatFullAmount(feeValue)} CRN` 
                  : "No fee applied"}
              </div>
            </div>
          </div>
          
          {transaction.tax && (
            <div>
              <div className="text-xs text-[#C4C4C7] mb-1.5">Tax</div>
              <div className="text-sm text-white font-medium p-2 bg-[#262626] rounded-lg">
                {transaction.tax} CRN
              </div>
            </div>
          )}

          {transaction.reason && (
            <div>
              <div className="text-xs text-[#C4C4C7] mb-1.5">Reason</div>
              <div className="text-sm text-white font-medium p-2.5 bg-[#262626] rounded-lg break-words">
                {transaction.reason || "No reason specified"}
              </div>
            </div>
          )}
          
          <div>
            <div className="text-xs text-[#C4C4C7] mb-1.5">Recipient Address</div>
            <div className="text-sm text-white font-medium p-2.5 bg-[#262626] rounded-lg break-all">
              {transaction.counterparty_public_address || "Unknown address"}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}, (prevProps, nextProps) => {
  // Custom comparison to prevent unnecessary re-renders
  return (
    prevProps.transaction.tx_id === nextProps.transaction.tx_id &&
    prevProps.activeTransactionId === nextProps.activeTransactionId
  );
});

// Date Range Picker component
const DateRangePicker: React.FC<{
  dateRange: DateRange;
  setDateRange: React.Dispatch<React.SetStateAction<DateRange>>;
  onApply: () => void;
}> = ({ dateRange, setDateRange, onApply }) => {
  return (
    <div className="flex flex-col sm:flex-row gap-2 mb-2 sm:mb-0">
      <div className="flex flex-col">
        <label className="text-xs text-[#C4C4C7] mb-1">Start Date</label>
        <input
          type="date"
          value={dateRange.startDate}
          onChange={(e) =>
            setDateRange((prev) => ({ ...prev, startDate: e.target.value }))
          }
          className="bg-[#2A2A2E] border border-[#C4C4C7]/20 text-white py-1 px-2 rounded-lg focus:outline-none focus:ring-1 focus:ring-[#8B5CF6] focus:border-transparent"
        />
      </div>
      <div className="flex flex-col">
        <label className="text-xs text-[#C4C4C7] mb-1">End Date</label>
        <input
          type="date"
          value={dateRange.endDate}
          onChange={(e) =>
            setDateRange((prev) => ({ ...prev, endDate: e.target.value }))
          }
          className="bg-[#2A2A2E] border border-[#C4C4C7]/20 text-white py-1 px-2 rounded-lg focus:outline-none focus:ring-1 focus:ring-[#8B5CF6] focus:border-transparent"
        />
      </div>
      <button
        onClick={onApply}
        className="mt-auto py-1 px-4 rounded-lg bg-[#635BFF] text-white text-sm font-medium"
      >
        Apply
      </button>
    </div>
  );
};

// Export options component
const ExportButton: React.FC<{ transactions: Transaction[] }> = ({
  transactions,
}) => {
  const exportToCSV = () => {
    if (!transactions.length) return;

    // Create CSV headers
    const headers = [
      "Transaction ID",
      "Type",
      "Amount",
      "Fee",
      "Date",
      "Status",
      "Counterparty",
      "Reason",
    ].join(",");

    // Create CSV rows
    const rows = transactions.map((tx) => {
      return [
        `"${tx.tx_id}"`,
        tx.type,
        tx.amount,
        tx.fee,
        tx.formatted_date,
        tx.status,
        `"${tx.display_address}"`,
        `"${tx.reason || ""}"`,
      ].join(",");
    });

    // Combine headers and rows
    const csvContent = [headers, ...rows].join("\n");
    
    // Create download link
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `transaction_history_${new Date().toISOString().split("T")[0]}.csv`);
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <button
      onClick={exportToCSV}
      className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#2e2e2e] text-white hover:bg-[#353535] transition-colors"
    >
      <Download size={16} />
      <span>Export</span>
    </button>
  );
};

// Main History component
const History: React.FC = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [isPageLoading, setIsPageLoading] = useState(false);
  const [data, setData] = useState<ApiResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState<"all" | "sent" | "received">(
    "all"
  );
  const [showDateFilter, setShowDateFilter] = useState(false);
  const [dateRange, setDateRange] = useState<DateRange>({
    startDate: "",
    endDate: "",
  });
  const [cachedResponses, setCachedResponses] = useState<
    Record<
      string,
      {
        data: ApiResponse;
        timestamp: number;
      }
    >
  >({});
  const [filteredTransactions, setFilteredTransactions] = useState<Transaction[]>([]);
  const [activeTransactionId, setActiveTransactionId] = useState<string | null>(null);
  
  // CSRF token state
  const [csrfToken, setCsrfToken] = useState<string>('');
  
  // Prevent state updates after unmount
  const isMounted = useRef(true);
  // Add a ref to control in-flight requests
  const activeRequest = useRef<AbortController | null>(null);

  const perPage = 100;
  const CACHE_EXPIRY = 2 * 60 * 1000;

  // Function to fetch CSRF token
  const fetchCsrfToken = async () => {
    try {
      console.log('Fetching CSRF token for history...');
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
        console.log('CSRF token received successfully for history');
        setCsrfToken(data.csrf_token);
        return true;
      } else {
        console.error('CSRF token fetch failed:', data.error || 'Unknown error');
        return false;
      }
    } catch (error) {
      console.error('CSRF token fetch error:', error);
      return false;
    }
  };

  // Function to refresh CSRF token
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

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMounted.current = false;
      // Cancel any in-flight requests
      if (activeRequest.current) {
        activeRequest.current.abort();
      }
    };
  }, []);

  // Search and filter transactions locally - optimized with debounce effect
  useEffect(() => {
    if (!data || !data.transactions) return;

    const handler = setTimeout(() => {
      if (isMounted.current) {
        if (searchQuery.trim().length === 0) {
          // Don't filter when search is empty
          setFilteredTransactions(data.transactions);
          return;
        }

        const query = searchQuery.toLowerCase();

        // More efficient search - only check necessary fields
        // and break early when match is found 
        const filtered = data.transactions.filter(tx => {
          // Check tx_id first as it's the most specific
          if (tx.tx_id && tx.tx_id.toLowerCase().includes(query)) return true;
          
          // Check amount (common search)
          if (tx.amount && tx.amount.toString().includes(query)) return true;
          
          // Check display address (if available)
          if (tx.display_address && tx.display_address.toLowerCase().includes(query)) return true;
          
          // Check formatted date
          if (tx.formatted_date && tx.formatted_date.toLowerCase().includes(query)) return true;
          
          // Only check remaining fields if no matches found
          return (
            (tx.counterparty_public_address && tx.counterparty_public_address.toLowerCase().includes(query)) ||
            (tx.reason && tx.reason.toLowerCase().includes(query))
          );
        });

        setFilteredTransactions(filtered);
      }
    }, 250); // Debounce for better performance

    return () => clearTimeout(handler);
  }, [searchQuery, data]);

  const fetchTransactionHistory = useCallback(
    async (page = 1, type?: string, forceRefresh = false) => {
      try {
        // Cancel previous request if exists
        if (activeRequest.current) {
          activeRequest.current.abort();
        }
        
        // Create new abort controller
        activeRequest.current = new AbortController();
        
        // Check if CSRF token is available
        if (!csrfToken) {
          console.error('CSRF token not available for transaction history');
          setError('Security token not available. Please refresh the page and try again.');
          return;
        }
        
        // Show loading indicators based on whether this is initial load or page change
        if (!data) {
          setIsLoading(true);
        } else if (page !== currentPage) {
          setIsPageLoading(true);
        }

        // Generate cache key
        const pageKey = `transactions_page${page}_filter${type || 'all'}_startDate${dateRange.startDate}_endDate${dateRange.endDate}`;

        // Check cache first
        if (!forceRefresh && cachedResponses[pageKey] && isMounted.current) {
          const cachedData = cachedResponses[pageKey];
          const now = Date.now();

          if (now - cachedData.timestamp < CACHE_EXPIRY) {
            console.log("Using cached transaction data");
            setData(cachedData.data);
            setFilteredTransactions(cachedData.data.transactions);
            setError(null);
            setIsLoading(false);
            setIsPageLoading(false);
            return;
          }
        }

        const params: Record<string, string | number> = {
          page,
          per_page: perPage,
        };

        if (type && type !== "all") {
          params.type = type;
        }

        // Add date range filters if set
        if (dateRange.startDate) {
          params.start_date = dateRange.startDate;
        }

        if (dateRange.endDate) {
          params.end_date = dateRange.endDate;
        }

        const response = await axios.get<ApiResponse>("/api/transaction-history", {
          params,
          headers: {
            "Cache-Control": "max-age=300",
            "X-CSRF-Token": csrfToken
          },
          withCredentials: true,
          signal: activeRequest.current.signal
        });

        // Check if component is still mounted before updating state
        if (isMounted.current) {
          // Save to cache for future use
          setCachedResponses((prev) => ({
            ...prev,
            [pageKey]: {
              data: response.data,
              timestamp: Date.now(),
            },
          }));
          
          setData(response.data);
          setFilteredTransactions(response.data.transactions);
          setError(null);
        }
      } catch (err: any) {
        if (!isMounted.current) return;
        
        // Don't handle aborted requests as errors
        if (err.name === 'AbortError' || err.name === 'CanceledError') {
          console.log('Request was cancelled');
          return;
        }
        
        // Handle CSRF-related errors
        if (err.response?.status === 403 && err.response?.data?.error?.includes('CSRF')) {
          console.log('CSRF token expired, refreshing...');
          setCsrfToken('');
          
          const tokenRefreshed = await refreshCsrfToken();
          if (tokenRefreshed) {
            // Retry the request with the new token
            try {
              // Recreate params for retry
              const retryParams: Record<string, string | number> = {
                page,
                per_page: perPage,
              };

              if (type && type !== "all") {
                retryParams.type = type;
              }

              // Add date range filters if set
              if (dateRange.startDate) {
                retryParams.start_date = dateRange.startDate;
              }

              if (dateRange.endDate) {
                retryParams.end_date = dateRange.endDate;
              }

              // Recreate pageKey for retry
              const retryPageKey = `transactions_page${page}_filter${type || 'all'}_startDate${dateRange.startDate}_endDate${dateRange.endDate}`;

              const retryResponse = await axios.get<ApiResponse>("/api/transaction-history", {
                params: retryParams,
                headers: {
                  "Cache-Control": "max-age=300",
                  "X-CSRF-Token": csrfToken
                },
                withCredentials: true,
                signal: activeRequest.current?.signal
              });
              
              if (isMounted.current) {
                setCachedResponses((prev) => ({
                  ...prev,
                  [retryPageKey]: {
                    data: retryResponse.data,
                    timestamp: Date.now(),
                  },
                }));
                
                setData(retryResponse.data);
                setFilteredTransactions(retryResponse.data.transactions);
                setError(null);
                return; // Exit early on success
              }
            } catch (retryError) {
              console.error('Failed to retry transaction history fetch:', retryError);
            }
          }
        }
        
        console.error("Error fetching transaction history:", err);
        
        // More specific error message for authentication issues
        if (axios.isAxiosError(err) && err.response?.status === 401) {
          setError("Authentication error. Please log in again to view your transaction history.");
        } else if (err.message === 'Request timeout') {
          setError("The request timed out. Please try again.");
        } else {
          setError("Failed to load transaction history. Please try again later.");
        }

        // Log detailed error for debugging
        if (axios.isAxiosError(err) && err.response) {
          console.error("API error response:", err.response.data);
        }
      } finally {
        if (isMounted.current) {
          setIsLoading(false);
          setIsPageLoading(false);
          activeRequest.current = null;
        }
      }
    },
    [cachedResponses, CACHE_EXPIRY, dateRange, currentPage, data, perPage, csrfToken]
  );

  // Optimization: Add throttling to prevent excessive API calls
  useEffect(() => {
    // Do not fetch until CSRF token is available
    if (!csrfToken) {
      return;
    }

    const timer = setTimeout(() => {
      fetchTransactionHistory(
        currentPage,
        filterType === "all" ? undefined : filterType
      );
    }, 300);

    return () => clearTimeout(timer);
  }, [currentPage, filterType, fetchTransactionHistory, csrfToken]);

  // Initial data load
  useEffect(() => {
    fetchCsrfToken();
  }, []);

  const handlePageChange = (newPage: number) => {
    if (!data || newPage < 1 || newPage > data.pagination.total_pages) {
      return;
    }
    
    // Close any open transaction details when changing pages
    setActiveTransactionId(null);
    
    window.scrollTo({ top: 0, behavior: "smooth" });
    setCurrentPage(newPage);
  };

  const handleDateFilterApply = () => {
    setCurrentPage(1);
    setActiveTransactionId(null);
    fetchTransactionHistory(
      1,
      filterType === "all" ? undefined : filterType,
      true
    );
  };

  const handleFilterTypeChange = (type: "all" | "sent" | "received") => {
    setFilterType(type);
    setCurrentPage(1);
    setActiveTransactionId(null);
  };

  const renderTransactions = () => {
    // Create a new array to avoid mutating the original data
    // No need to reverse as we want newest transactions at the top
    // The API already returns them in descending order (newest first)
    const sortedTransactions = [...filteredTransactions];
    
    return sortedTransactions.map((transaction) => (
      <TransactionRow
        key={transaction.tx_id}
        transaction={transaction}
        activeTransactionId={activeTransactionId}
        setActiveTransactionId={setActiveTransactionId}
      />
    ));
  };

  if (isLoading && !data) {
    return (
      <div className="container mx-auto py-4 sm:py-8 px-3 sm:px-4">
        <div className="flex justify-center items-center h-64">
          <div className="flex flex-col items-center animate-pulse">
            <RefreshCw className="w-8 h-8 sm:w-10 sm:h-10 text-indigo-600 animate-spin" />
            <div className="mt-4 text-sm sm:text-base text-gray-600">
              Loading transaction history...
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto py-4 sm:py-8 px-3 sm:px-4">
        <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 sm:px-4 sm:py-3 rounded-lg animate-fadeIn text-sm sm:text-base">
          <div className="flex">
            <Info className="h-4 w-4 sm:h-5 sm:w-5 text-red-500 mr-2" />
            <div>{error}</div>
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const { summary, transactions, pagination } = data;

  return (
    <div className="bg-[#262626] min-h-screen py-4 px-4 sm:p-6 pb-24 md:pb-6">
      <div className="max-w-7xl mx-auto">
        {/* Header Section */}
        <div className="mb-6">
          <h1 className="text-2xl sm:text-3xl font-bold text-white mb-2">
            Transaction History
          </h1>
          <p className="text-[#C4C4C7] text-sm sm:text-base">
            View and manage your transaction history
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6">
          <div className="bg-[#2b2b2b] rounded-2xl shadow-lg p-4 sm:p-6 transition-all duration-300 hover:shadow-2xl overflow-hidden">
            <div
              className="flex justify-between items-start"
              style={{ flexWrap: "nowrap" }}
            >
              <div style={{ minWidth: 0, flex: 1, marginRight: "10px" }}>
                <h4
                  className="text-[#FFFFFF] font-semibold tracking-wide text-base"
                  style={{ maxWidth: "100%", wordWrap: "break-word" }}
                >
                  <span>Total</span> <span>Transactions</span>
                </h4>
                <div className="mt-3">
                  <div className="text-4xl font-bold text-white tracking-tight">
                    {summary.total_transactions}
                    <span className="text-sm font-medium text-[#B0B0B5] ml-2">
                      transactions
                    </span>
                  </div>
                </div>
                <div className="transaction-stats flex items-center justify-between mt-3 text-sm font-medium">
                  <div className="flex items-center gap-2 sent-stats">
                    <div className="flex items-center gap-1.5">
                      <span className="text-red-400">{summary.sent_count}</span>
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
                        {summary.received_count}
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
          </div>
          <StatCard
            title="Total Sent"
            value={`${summary.total_sent} CRN`}
            icon={<ArrowUp className="text-rose-400" size={20} />}
            color="bg-rose-500/10"
          />
          <StatCard
            title="Total Received"
            value={`${summary.total_received} CRN`}
            icon={<ArrowDown className="text-emerald-400" size={20} />}
            color="bg-emerald-500/10"
          />
          <StatCard
            title="Largest Transaction"
            value={`${summary.largest_transaction} CRN`}
            icon={<DollarSign className="text-[#8B5CF6]" size={20} />}
            color="bg-[#8B5CF6]/20"
          />
        </div>

        {/* Search and Filter Section */}
        <div className="bg-[#2b2b2b] rounded-2xl p-4 sm:p-6 mb-6 shadow-lg">
          <div className="flex flex-col gap-4">
            <div className="flex flex-col sm:flex-row gap-4 justify-between">
              <div className="flex-1">
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search by ID, address, amount..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-[#2A2A2E] border border-[#C4C4C7]/20 text-white py-2 px-4 pl-10 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#8B5CF6] focus:border-transparent"
                  />
                  <Search
                    className="absolute left-3 top-2.5 text-[#C4C4C7]"
                    size={18}
                  />
                </div>
              </div>
              
              <div className="flex gap-2 sm:gap-4">
                <button 
                  onClick={() => setShowDateFilter(!showDateFilter)}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#2e2e2e] text-white hover:bg-[#353535] transition-colors"
                >
                  <Calendar size={16} />
                  <span className="hidden sm:inline">Date Filter</span>
                </button>
                <ExportButton transactions={filteredTransactions} />
              </div>
            </div>

            {/* Date filter section */}
            {showDateFilter && (
              <div className="pt-3 border-t border-[#3a3a3a]">
                <DateRangePicker 
                  dateRange={dateRange}
                  setDateRange={setDateRange}
                  onApply={handleDateFilterApply}
                />
              </div>
            )}
            
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => handleFilterTypeChange("all")}
                className={`px-4 py-2 rounded-lg transition-all duration-300 font-medium text-white ${
                  filterType === "all" ? "bg-[#635BFF]" : "bg-[#2e2e2e]"
                }`}
              >
                All
              </button>
              <button
                onClick={() => handleFilterTypeChange("received")}
                className={`px-4 py-2 rounded-lg transition-all duration-300 font-medium text-white ${
                  filterType === "received" ? "bg-[#22c55e]" : "bg-[#2e2e2e]"
                }`}
              >
                Received
              </button>
              <button
                onClick={() => handleFilterTypeChange("sent")}
                className={`px-4 py-2 rounded-lg transition-all duration-300 font-medium text-white ${
                  filterType === "sent" ? "bg-[#e04f5f]" : "bg-[#2e2e2e]"
                }`}
              >
                Sent
              </button>
            </div>
          </div>
        </div>

        {/* Transactions List */}
        <div className="bg-[#2b2b2b] rounded-2xl overflow-hidden p-4 sm:p-6 shadow-lg">
          {isPageLoading ? (
            <div className="flex justify-center items-center p-10">
              <RefreshCw className="w-6 h-6 text-indigo-600 animate-spin" />
              <span className="ml-2 text-[#C4C4C7]">Loading transactions...</span>
            </div>
          ) : (
            <div>
              {filteredTransactions.length > 0 ? (
                <div className="space-y-0">
                  {renderTransactions()}
                </div>
              ) : (
                <div className="text-center py-10">
                  <p className="text-[#C4C4C7]">No transactions found</p>
                </div>
              )}
            </div>
          )}

          {/* Pagination */}
          {filteredTransactions.length > 0 && (
            <div className="px-4 sm:px-6 py-4 mt-4 border-t border-[#2E2E3E]">
              <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
                <div className="text-sm text-[#C4C4C7] order-2 sm:order-1">
                  {searchQuery 
                    ? `Showing ${filteredTransactions.length} matching transactions` 
                    : `Showing ${transactions.length} of ${pagination.total_count} transactions`}
                </div>
                <div className="flex items-center gap-2 order-1 sm:order-2">
                  <button
                    onClick={() => handlePageChange(pagination.page - 1)}
                    disabled={pagination.page === 1 || isPageLoading}
                    className="p-2 rounded-lg bg-[#2A2A2E] text-[#C4C4C7] disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[#2E2E3E] transition-colors"
                  >
                    <ChevronLeft size={18} />
                  </button>
                  <span className="text-sm text-white">
                    Page {pagination.page} of {pagination.total_pages}
                  </span>
                  <button
                    onClick={() => handlePageChange(pagination.page + 1)}
                    disabled={pagination.page === pagination.total_pages || isPageLoading}
                    className="p-2 rounded-lg bg-[#2A2A2E] text-[#C4C4C7] disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[#2E2E3E] transition-colors"
                  >
                    <ChevronRight size={18} />
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Add this at the top of your file, after the import statements
const style = document.createElement("style");
style.textContent = `
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fadeIn {
  animation: fadeIn 0.3s ease-out forwards;
}
`;
document.head.appendChild(style);

export default History;

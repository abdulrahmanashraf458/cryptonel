import React, {
  useState,
  useEffect,
  createContext,
  useRef,
  Suspense,
} from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
  useNavigate,
  useLocation,
} from "react-router-dom";
import PremiumProvider from "./contexts/PremiumContext";
import PremiumGuard from "./components/PremiumGuard";
import Sidebar from "./components/Sidebar";
import Navbar from "./components/Navbar";
import MobileNavbar from "./components/MobileNavbar";
import Overview from "./pages/Overview";
import Mining from "./pages/Mining";
import Transfers from "./pages/Transfers";
import DashboardSelect from "./pages/DashboardSelect";
import Login from "./pages/Login";
import SignUp from "./pages/SignUp";
import ResetPassword from "./pages/ResetPassword";
import History from "./pages/History";
import Leaderboard from "./pages/Leaderboard";
import PartnerServers from "./pages/PartnerServers";
import { Menu } from "lucide-react";

// Import landing pages
import Home from "./landing/pages/Home";
import Terms from "./landing/pages/Terms";
import LandingPrivacy from "./landing/pages/Privacy";
import Cookies from "./landing/pages/Cookies";
import WalletInfo from "./landing/pages/Wallet";
import TransfersInfo from "./landing/pages/Transfers";
import MiningInfo from "./landing/pages/Mining";
import NetworkTransactions from "./landing/pages/NetworkTransactions";
import CommunityServersLanding from "./landing/pages/PartnerServers";
import SubscriptionPage from "./landing/subscription/SubscriptionPage";

// Importar los nuevos componentes de Wallet
import Security from "./pages/wallet/Security";
import Privacy from "./pages/wallet/Privacy";
import Settings from "./pages/wallet/Settings";
import SettingsPanel from "./pages/wallet/SettingsPanel";
import QuickTransfer from "./pages/QuickTransfer";
import CustomAddress from "./pages/CustomAddress";
import PublicProfilePage from "./pages/ratings/PublicProfilePage";
import RatingContainer from "./pages/ratings/RatingContainer";

// إنشاء سياق الشريط الجانبي
interface SidebarContextType {
  isExpanded: boolean;
  setIsExpanded: React.Dispatch<React.SetStateAction<boolean>>;
  isMediumScreen: boolean;
}

export const SidebarContext = createContext<SidebarContextType>({
  isExpanded: true,
  setIsExpanded: () => {},
  isMediumScreen: false,
});

// Página principal de Wallet
const WalletPage = () => (
  <div className="py-6">
    <h1 className="text-2xl font-bold mb-6 text-[#E5E5E5]">
      Wallet Management
    </h1>
    <p className="text-[#A1A1AA]">
      Select a section from the sidebar to manage your wallet.
    </p>
  </div>
);

// Loading spinner component
const Spinner = () => (
  <div className="flex items-center justify-center h-32">
    <div className="w-8 h-8 border-4 border-[#6C5DD3] border-t-transparent rounded-full animate-spin"></div>
  </div>
);

// Page not found component
const PageNotFound = () => (
  <div className="flex flex-col items-center justify-center h-64">
    <h1 className="text-3xl font-bold text-[#E5E5E5] mb-4">404</h1>
    <p className="text-[#A1A1AA]">Page not found</p>
  </div>
);

// Cache to prevent duplicate asset requests
const assetCache = new Set<string>();

// For favicon requests - add to document head once
const addFavicon = () => {
  if (document.querySelector('link[rel="icon"]')) return;

  const link = document.createElement("link");
  link.rel = "icon";
  link.href = "/images/1.png";
  link.type = "image/png";
  document.head.appendChild(link);
  
  // Ensure the page title is set correctly
  document.title = "Clyne";
};

// Call this once when app loads
document.addEventListener("DOMContentLoaded", addFavicon);

// Import JWT decoding library to check token expiration
import { jwtDecode } from 'jwt-decode';

// Protected route component to check authentication
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [isLocked, setIsLocked] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const authCheckInProgress = useRef(false);
  const authCheckCounter = useRef(0);
  const lastAuthCheck = useRef(0);
  const tokenRefreshInProgress = useRef(false);

  // Function to refresh access token
  const refreshToken = async (refreshToken: string): Promise<boolean> => {
    if (tokenRefreshInProgress.current) return false;
    
    tokenRefreshInProgress.current = true;
    try {
      // Use the correct endpoint from the server
      const response = await fetch('/api/refresh-token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
        credentials: 'include' // Important for handling cookies
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success && data.access_token) {
          // Store new access token
          localStorage.setItem('access_token', data.access_token);
          
          // Store new access token in cookie for better persistence
          document.cookie = `access_token=${data.access_token}; path=/; max-age=${data.expires_in || 86400}; SameSite=Lax`;
          
          console.log('Token refreshed successfully');
          tokenRefreshInProgress.current = false;
          return true;
        }
      } else if (response.status === 401) {
        // Clear invalid tokens to force a new login
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        document.cookie = 'access_token=; path=/; max-age=0';
        document.cookie = 'refresh_token=; path=/; max-age=0';
        console.log('Refresh token invalid or expired, need to re-login');
      }
      
      tokenRefreshInProgress.current = false;
      return false;
    } catch (error) {
      console.error('Error refreshing token:', error);
      tokenRefreshInProgress.current = false;
      
      // On network errors, don't clear tokens - might be temporary connection issue
      return false;
    }
  };

  // Check if token is expired or about to expire
  const isTokenExpired = (token: string): boolean => {
    try {
      const decoded: any = jwtDecode(token);
      // Check if token is expired or will expire in the next 5 minutes
      const currentTime = Date.now() / 1000;
      return decoded.exp < currentTime + 300; // 5 minutes buffer
    } catch (error) {
      return true; // Assume expired if error decoding
    }
  };

  // Helper function to get a cookie value by name
  const getCookie = (name: string): string | null => {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.startsWith(name + '=')) {
        return cookie.substring(name.length + 1);
      }
    }
    return null;
  };

  // Initialize with a cached state if available
  useEffect(() => {
    // On first render, try to use cached state to avoid any API calls
    const cachedAuthState = sessionStorage.getItem("auth_state");
    if (cachedAuthState) {
      try {
        const authState = JSON.parse(cachedAuthState);
        setIsAuthenticated(authState.isAuthenticated);
        setIsLocked(authState.isLocked);
        
        // Even if we have cached auth state, always check if the access token 
        // needs refreshing when the component first mounts
        const checkTokenExpiration = async () => {
          let accessToken = localStorage.getItem("access_token");
          
          // If token exists but is expired, try to refresh it
          if (accessToken && isTokenExpired(accessToken)) {
            const refreshTokenValue = localStorage.getItem("refresh_token") || getCookie("refresh_token");
            if (refreshTokenValue && !isTokenExpired(refreshTokenValue)) {
              await refreshToken(refreshTokenValue);
            }
          }
        };
        
        checkTokenExpiration();
        setLoading(false);

        // Record the time to avoid excessive checking
        lastAuthCheck.current = Date.now();
        return;
      } catch (e) {
        console.error("Error parsing cached auth state", e);
        sessionStorage.removeItem("auth_state");
      }
    }

    // Only check auth once on component mount
    if (authCheckCounter.current === 0) {
      authCheckCounter.current++;
      checkAuth();
    } else {
      setLoading(false);
    }

    async function checkAuth() {
      // Prevent concurrent auth checks and throttle frequency
      if (authCheckInProgress.current) return;

      const now = Date.now();
      const timeSinceLastCheck = now - lastAuthCheck.current;

      // Enforce a minimum 10-second interval between checks
      if (lastAuthCheck.current > 0 && timeSinceLastCheck < 10000) {
        console.log(
          `Auth check throttled. Last check was ${timeSinceLastCheck}ms ago.`
        );
        return;
      }

      authCheckInProgress.current = true;
      lastAuthCheck.current = now;

      try {
        // Check for lockout in localStorage
        const lockoutData = localStorage.getItem("server_lockout");
        if (lockoutData) {
          try {
            const { until } = JSON.parse(lockoutData);
            const lockoutUntil = new Date(until);
            const now = new Date();

            if (now < lockoutUntil) {
              setIsLocked(true);
              setLoading(false);

              // Cache the auth state
              sessionStorage.setItem(
                "auth_state",
                JSON.stringify({
                  isAuthenticated: false,
                  isLocked: true,
                  userId: null,
                })
              );

              authCheckInProgress.current = false;
              return;
            } else {
              localStorage.removeItem("server_lockout");
            }
          } catch (err) {
            localStorage.removeItem("server_lockout");
          }
        }

        // Check for access token in multiple storage locations
        let accessToken = localStorage.getItem("access_token");
        
        // If not in localStorage, try cookies
        if (!accessToken) {
          const cookieToken = getCookie("access_token");
          if (cookieToken) {
            accessToken = cookieToken;
            // Sync to localStorage
            localStorage.setItem("access_token", cookieToken);
          }
        }
        
        if (!accessToken) {
          setIsAuthenticated(false);
          setLoading(false);

          // Cache the auth state
          sessionStorage.setItem(
            "auth_state",
            JSON.stringify({
              isAuthenticated: false,
              isLocked: false,
              userId: null,
            })
          );

          authCheckInProgress.current = false;
          return;
        }

        // Check for token expiration
        if (isTokenExpired(accessToken)) {
          // Try to refresh the token
          const refreshTokenValue = localStorage.getItem("refresh_token") || getCookie("refresh_token");
          
          if (refreshTokenValue && !isTokenExpired(refreshTokenValue)) {
            // Token is expired but we have a valid refresh token
            const refreshSuccess = await refreshToken(refreshTokenValue);
            
            if (!refreshSuccess) {
              // If refresh failed, redirect to login
              setIsAuthenticated(false);
              setLoading(false);
              
              sessionStorage.setItem(
                "auth_state",
                JSON.stringify({
                  isAuthenticated: false,
                  isLocked: false,
                  userId: null,
                })
              );
              
              authCheckInProgress.current = false;
              return;
            }
            // Continue with the fresh token
            accessToken = localStorage.getItem("access_token");
          } else if (!refreshTokenValue) {
            // No refresh token available, user needs to login
            setIsAuthenticated(false);
            setLoading(false);
            
            sessionStorage.setItem(
              "auth_state",
              JSON.stringify({
                isAuthenticated: false,
                isLocked: false,
                userId: null,
              })
            );
            
            authCheckInProgress.current = false;
            return;
          }
          // If refresh token is also expired, continue to the API call which will handle the failure
        }

        // Use a timeout to prevent hanging requests
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);

        try {
          // Make authenticated request with possible token refresh
          const response = await makeAuthenticatedRequest("/api/user", {
            method: "GET",
            signal: controller.signal,
          });

          clearTimeout(timeoutId);
          
          // Check for token refresh in response header
          const newToken = response.headers.get('X-New-Access-Token');
          if (newToken) {
            // Update token in localStorage
            localStorage.setItem('access_token', newToken);
            // Also update in cookie
            const expiresIn = response.headers.get('X-Token-Expires-In') || '86400';
            document.cookie = `access_token=${newToken}; path=/; max-age=${expiresIn}; SameSite=Lax`;
            console.log('Access token refreshed from server response');
          }

          // Only check rate limit if authenticated
          if (response.ok) {
            // Cache success immediately to avoid spinning during rate limit check
            setIsAuthenticated(true);
            setLoading(false);

            // Store user ID if available
            let userId = null;
            try {
              const userData = await response.json();
              userId = userData.user_id || null;
            } catch (e) {
              // Unable to parse user data
            }

            // Cache the positive auth state
            sessionStorage.setItem(
              "auth_state",
              JSON.stringify({
                isAuthenticated: true,
                isLocked: false,
                userId: userId,
              })
            );

            // Check rate limit in the background
            makeAuthenticatedRequest("/api/auth/check-rate-limit")
              .then(async (rlResponse) => {
                if (rlResponse.ok) {
                  const rateLimitData = await rlResponse.json();
                  if (rateLimitData && rateLimitData.is_limited) {
                    setIsLocked(true);

                    // Update cached auth state
                    sessionStorage.setItem(
                      "auth_state",
                      JSON.stringify({
                        isAuthenticated: false,
                        isLocked: true,
                        userId: userId,
                      })
                    );
                  }
                }
              })
              .catch(() => {
                // Ignore rate limit check errors
              });
          } else {
            setIsAuthenticated(false);
            setLoading(false);

            // Cache the negative auth state
            sessionStorage.setItem(
              "auth_state",
              JSON.stringify({
                isAuthenticated: false,
                isLocked: false,
                userId: null,
              })
            );
          }
        } catch (error) {
          clearTimeout(timeoutId);
          console.error("Error checking auth:", error);

          // On error, assume not authenticated
          setIsAuthenticated(false);
          setLoading(false);

          // Cache the error auth state
          sessionStorage.setItem(
            "auth_state",
            JSON.stringify({
              isAuthenticated: false,
              isLocked: false,
              userId: null,
            })
          );
        }
      } catch (error) {
        console.error("Unexpected auth error:", error);
        setIsAuthenticated(false);
        setLoading(false);
      } finally {
        authCheckInProgress.current = false;
      }
    }
  }, [navigate, location.pathname]);

  // Helper function to make authenticated requests with token refresh handling
  const makeAuthenticatedRequest = async (url: string, options: RequestInit = {}) => {
    // Get the current access token
    let accessToken = localStorage.getItem("access_token");
    
    // Set up headers
    const headers = new Headers(options.headers);
    if (accessToken) {
      headers.set('Authorization', `Bearer ${accessToken}`);
    }
    headers.set('Cache-Control', 'no-cache, no-store, must-revalidate');
    headers.set('Pragma', 'no-cache');
    headers.set('Expires', '0');
    
    // Make the request
    let response = await fetch(url, {
      ...options,
      headers,
      credentials: 'include'
    });
    
    // Check if we got a 401 and need to refresh the token
    if (response.status === 401) {
      // Try to refresh the token
      const refreshTokenValue = localStorage.getItem("refresh_token") || getCookie("refresh_token");
      if (refreshTokenValue && !isTokenExpired(refreshTokenValue)) {
        const refreshSuccess = await refreshToken(refreshTokenValue);
        
        if (refreshSuccess) {
          // Retry the request with the new token
          accessToken = localStorage.getItem("access_token");
          const newHeaders = new Headers(options.headers);
          if (accessToken) {
            newHeaders.set('Authorization', `Bearer ${accessToken}`);
          }
          newHeaders.set('Cache-Control', 'no-cache, no-store, must-revalidate');
          newHeaders.set('Pragma', 'no-cache');
          newHeaders.set('Expires', '0');
          
          // Retry the request
          response = await fetch(url, {
            ...options,
            headers: newHeaders,
            credentials: 'include'
          });
        }
      }
    }
    
    // Check for token refresh in response header
    const newToken = response.headers.get('X-New-Access-Token');
    if (newToken) {
      // Update token in localStorage
      localStorage.setItem('access_token', newToken);
      // Also update in cookie
      const expiresIn = response.headers.get('X-Token-Expires-In') || '86400';
      document.cookie = `access_token=${newToken}; path=/; max-age=${expiresIn}; SameSite=Lax`;
      console.log('Access token refreshed from server response');
    }
    
    return response;
  };

  // Show loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#18181B]">
        <div className="w-12 h-12 border-4 border-[#8875FF] border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  // Show lockout state
  if (isLocked) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[#0F172A] text-[#FFFFFF] p-4">
        <div className="bg-[#1E293B] p-6 rounded-lg max-w-md text-center shadow-xl">
          <h1 className="text-2xl font-bold mb-4 text-red-500">
            Account Locked
          </h1>
          <p className="mb-4 text-[#C4C4C7]">
            Your account has been temporarily locked due to excessive login
            attempts or suspicious activity.
          </p>
          <p className="mb-6 text-[#C4C4C7]">
            Please try again later or contact support for assistance.
          </p>
          <button
            onClick={() => {
              localStorage.removeItem("server_lockout");
              localStorage.removeItem("access_token");
              localStorage.removeItem("refresh_token"); // Also clear refresh token
              sessionStorage.removeItem("auth_state");
              window.location.href = "/login";
            }}
            className="px-4 py-2 bg-[#3B82F6] text-white rounded hover:bg-[#2563EB] transition-colors"
          >
            Return to Login
          </button>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    // Save the intended destination in localStorage so we can redirect back after login
    localStorage.setItem('intendedDestination', location.pathname);
    return <Navigate to="/login" state={{ from: location, intendedDestination: location.pathname }} replace />;
  }

  // Render children if authenticated
  return <>{children}</>;
};

function App() {
  const [isExpanded, setIsExpanded] = useState(true);
  const [screenSize, setScreenSize] = useState<"small" | "medium" | "large">(
    "large"
  );
  const isMediumScreen = screenSize === "medium";
  const [hideLayout, setHideLayout] = useState(false);

  // التحقق من حجم الشاشة عند التحميل وإعادة التحجيم
  useEffect(() => {
    const handleResize = () => {
      const windowWidth = window.innerWidth;
      if (windowWidth < 768) {
        // الشاشات الصغيرة: إخفاء الشريط الجانبي
        setIsExpanded(false);
        setScreenSize("small");
      } else if (windowWidth >= 768 && windowWidth < 1325) {
        // الشاشات المتوسطة: شريط جانبي مغلق لكن الأيقونات ظاهرة
        setIsExpanded(false);
        setScreenSize("medium");
      } else {
        // الشاشات الكبيرة: شريط جانبي مفتوح بالكامل
        setIsExpanded(true);
        setScreenSize("large");
      }
    };

    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return (
    <Router>
      <Routes>
        {/* Landing pages */}
        <Route path="/" element={<Home />} />
        <Route path="/terms" element={<Terms />} />
        <Route path="/privacy" element={<LandingPrivacy />} />
        <Route path="/cookies" element={<Cookies />} />
        <Route path="/wallet" element={<WalletInfo />} />
        <Route path="/transfers" element={<TransfersInfo />} />
        <Route path="/mining-info" element={<MiningInfo />} />
        <Route path="/network-transactions" element={<NetworkTransactions />} />
        <Route path="/community-servers" element={<CommunityServersLanding />} />
        <Route path="/subscription" element={<SubscriptionPage />} />
        
        {/* Public user profile route */}
        <Route path="/profile/:username" element={<PublicProfilePage />} />
        
        {/* Authentication pages */}
        <Route path="/dashboardselect" element={<DashboardSelect />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<SignUp />} />
        <Route path="/reset-password" element={<ResetPassword />} />

        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <PremiumProvider>
                <SidebarContext.Provider
                  value={{
                    isExpanded,
                    setIsExpanded,
                    isMediumScreen,
                  }}
                >
                  <div className="min-h-screen bg-[#262626] flex">
                    {/* إخفاء السايدبار إذا hideLayout */}
                    {!hideLayout && <Sidebar />}
                    <div
                      className={`flex-1 transition-all duration-300 text-[#FFFFFF] ${
                        !hideLayout
                          ? screenSize === "large"
                            ? isExpanded
                              ? "ml-64"
                              : "ml-20"
                            : screenSize === "medium"
                            ? "ml-20"
                            : ""
                          : ""
                      }`}
                    >
                    {/* إخفاء النافبار إذا hideLayout */}
                    {!hideLayout && (
                      <Navbar>
                        {isMediumScreen && (
                          <button
                            onClick={() => setIsExpanded(!isExpanded)}
                            className="p-2 rounded-full hover:bg-[#2A2A2D] text-[#A1A1AA] hover:text-[#E5E5E5]"
                          >
                            <Menu size={22} />
                          </button>
                        )}
                      </Navbar>
                    )}
                    <main className="p-4 md:p-6 max-w-7xl mx-auto pb-20 md:pb-6">
                      <Routes>
                        <Route path="/" element={<Overview />} />
                        <Route path="/dashboard" element={<Overview />} />
                        <Route path="/overview" element={<Overview />} />
                        <Route path="/mining" element={<Mining />} />
                        <Route path="/transfers" element={<Transfers />} />
                        <Route path="/transfer" element={<Transfers />} />
                        <Route path="/history" element={<History />} />
                        <Route path="/leaderboard" element={<Leaderboard />} />
                        <Route path="/community-servers" element={<PartnerServers />} />

                        {/* مسارات المحفظة */}
                        <Route path="/wallet" element={<WalletPage />} />

                        {/* قسم الإعدادات الموحد */}
                        <Route
                          path="/wallet/settings/*"
                          element={<SettingsPanel />}
                        />

                        {/* أقسام فردية للتوجيه المباشر - ستحول للإعدادات الموحدة */}
                        <Route
                          path="/wallet/security/*"
                          element={<Navigate to="/wallet/settings" replace />}
                        />
                        <Route
                          path="/wallet/privacy/*"
                          element={<Navigate to="/wallet/settings" replace />}
                        />
                        <Route
                          path="/wallet/backup/*"
                          element={<Navigate to="/wallet/settings" replace />}
                        />

                        {/* صفحة QuickTransfer - Premium protected */}
                        <Route path="/quick-transfer" element={<PremiumGuard><QuickTransfer /></PremiumGuard>} />
                        
                        {/* صفحة Custom Address - Premium protected */}
                        <Route path="/customaddress" element={<PremiumGuard><CustomAddress /></PremiumGuard>} />

                        {/* صفحة Ratings */}
                        <Route path="/ratings" element={<RatingContainer />} />
                        <Route path="/ratings/:userId" element={<RatingContainer />} />

                        {/* Fallback */}
                        <Route path="*" element={<PageNotFound />} />
                      </Routes>
                    </main>
                    {/* إخفاء شريط الموبايل إذا hideLayout */}
                    {!hideLayout && screenSize === "small" && <MobileNavbar />}
                  </div>
                </div>
                              </SidebarContext.Provider>
              </PremiumProvider>
              </ProtectedRoute>
            }
          />
      </Routes>
    </Router>
  );
}

export default App;

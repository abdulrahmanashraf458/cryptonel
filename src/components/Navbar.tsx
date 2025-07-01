import React, { useEffect, useState, useRef, useContext } from "react";
import { useLocation, useNavigate, Link } from "react-router-dom";
import {
  ChevronDown,
  User,
  Settings,
  LogOut,
  RefreshCw,
  HelpCircle,
  Menu,
  MessageCircle,
  ExternalLink,
  Mail,
  Star,
  Network,
  Wallet,
  Repeat,
  ListChecks,
  PickaxeIcon,
} from "lucide-react";
import { SidebarContext } from "../App";

interface NavbarProps {
  children: React.ReactNode;
}

interface UserData {
  username?: string;
  accountType?: string;
  avatar?: string;
  user_id?: string;
  verified?: boolean;
}

// قاموس لتحويل المسارات إلى أسماء أقسام مقروءة
const pathToSectionName: Record<string, string> = {
  "/overview": "Overview",
  "/dashboard": "Overview",
  "/": "Overview",
  "/transfer": "Transfer",
  "/transfers": "Transfer",
  "/mining": "Mining",
  "/wallet/settings": "Settings",
  "/history": "History",
  "/leaderboard": "Leaderboard",
  "/ratings": "Ratings",
};

const Navbar: React.FC<NavbarProps> = ({ children }) => {
  const [userData, setUserData] = useState<UserData>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false); // حالة القائمة المنسدلة
  const location = useLocation();
  const navigate = useNavigate();
  const profileMenuRef = useRef<HTMLDivElement>(null);

  // استخدام سياق السايدبار للتحكم في فتح وإغلاق السايدبار
  const { isExpanded, setIsExpanded } = useContext(SidebarContext);

  // إغلاق القائمة عند النقر خارجها
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        profileMenuRef.current &&
        !profileMenuRef.current.contains(event.target as Node)
      ) {
        setIsProfileMenuOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  // تسجيل الخروج
  const handleLogout = async () => {
    try {
      // حذف معلومات الجلسة
      localStorage.removeItem("access_token");
      sessionStorage.removeItem("auth_state");

      // استدعاء API تسجيل الخروج
      await fetch("/api/logout", {
        method: "GET",
        credentials: "include",
      });

      // إعادة التوجيه إلى صفحة تسجيل الدخول
      navigate("/login");
    } catch (error) {
      console.error("خطأ في تسجيل الخروج:", error);
    }
  };

  // دالة للتحكم بفتح/إغلاق السايدبار
  const handleToggleSidebar = () => {
    console.log("Toggle sidebar clicked, current state:", isExpanded);

    // تبسيط المنطق - دائمًا نعكس حالة السايدبار
    // هذا سيعمل بغض النظر عن الشاشة أو حالة السايدبار
    setIsExpanded(!isExpanded);
  };

  // الحصول على اسم القسم الحالي من المسار - تحسين طريقة تحديد القسم الحالي
  const getCurrentSectionName = (path: string) => {
    console.log("Current path:", path); // تسجيل المسار للتشخيص

    // تنظيف المسار (إزالة أي معلمات أو فروع)
    const cleanPath = path.split("?")[0].split("#")[0];

    // البحث عن تطابق مباشر أولاً
    if (pathToSectionName[cleanPath]) {
      return pathToSectionName[cleanPath];
    }

    // البحث عن تطابق جزئي - المسارات التي تبدأ ب
    for (const key in pathToSectionName) {
      // نتجاهل "/" لأنه سيطابق كل شيء
      if (key !== "/" && cleanPath.startsWith(key)) {
        return pathToSectionName[key];
      }
    }

    // إذا لم يتم العثور على مطابقة، نستخرج آخر جزء من المسار
    const pathSegments = cleanPath.split("/").filter(Boolean);
    if (pathSegments.length > 0) {
      const lastSegment = pathSegments[pathSegments.length - 1];
      return lastSegment.charAt(0).toUpperCase() + lastSegment.slice(1);
    }

    return "Dashboard";
  };

  // اسم القسم الحالي
  const currentSection = getCurrentSectionName(location.pathname);

  useEffect(() => {
    // Fetch authenticated user's data
    setIsLoading(true);
    console.log("Fetching user data from /api/overview");
    
    fetch("/api/overview")
      .then((response) => {
        console.log("API Response status:", response.status);
        if (!response.ok) {
          throw new Error(`API responded with status ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        console.log("User data received:", data);
        // Log specific avatar data for debugging
        console.log(`Avatar: ${data.avatar}, User ID: ${data.user_id}`);
        setUserData(data);
        setIsLoading(false);
      })
      .catch((error) => {
        console.error("Error fetching user data:", error);
        // Set default avatar on error
        setUserData({ 
          username: "Unknown User",
          avatar: "",
          user_id: ""
        });
        setIsLoading(false);
      });
  }, []);

  // Function to get Discord avatar URL
  const getDiscordAvatar = (userId: string, avatarId: string) => {
    if (!userId || !avatarId) {
      return "https://cdn.discordapp.com/embed/avatars/0.png";
    }
    const avatarUrl = `https://cdn.discordapp.com/avatars/${userId}/${avatarId}.png`;
    console.log(`Generated Discord avatar URL: ${avatarUrl}`);
    return avatarUrl;
  };

  // Get avatar URL with fallback
  const getAvatarUrl = () => {
    if (userData.avatar && userData.user_id) {
      console.log(`Getting avatar for user: ${userData.user_id}, avatar: ${userData.avatar}`);
      return getDiscordAvatar(userData.user_id, userData.avatar);
    }
    console.log("No avatar data available, using default");
    return "https://cdn.discordapp.com/embed/avatars/0.png";
  };

  // التحقق ما إذا كنا في وضع الشاشة الصغيرة
  const isSmallScreen = window.innerWidth < 768;

  // Update navigation links to include ratings
  const navLinks = [
    { name: 'Dashboard', href: '/wallet', icon: 'wallet' },
    { name: 'Transfer', href: '/transfer', icon: 'transfer' },
    { name: 'Transactions', href: '/transactions', icon: 'transactions' },
    { name: 'Mining', href: '/mining', icon: 'mining' },
    { name: 'Ratings', href: '/ratings', icon: 'star' },
    { name: 'Settings', href: '/settings', icon: 'settings' }
  ];

  // Update renderIcon function to include star icon
  const renderIcon = (iconName: string) => {
    switch (iconName) {
      case 'wallet':
        return <Wallet size={20} />;
      case 'transfer':
        return <Repeat size={20} />;
      case 'transactions':
        return <ListChecks size={20} />;
      case 'mining':
        return <PickaxeIcon size={20} />;
      case 'settings':
        return <Settings size={20} />;
      case 'star':
        return <Star size={20} />;
      default:
        return <Wallet size={20} />;
    }
  };

  return (
    <header className="bg-[#272626] backdrop-blur-md border-b border-[#2b2b2b] sticky top-0 z-30 shadow-[0_2px_8px_0_rgba(0,0,0,0.08)]">
      <div className="px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-6">
          {/* Burger button removed from mobile view since we're using MobileNavbar */}

          {children}

          {/* اسم القسم الحالي - سيكون مخفيًا في الشاشات الصغيرة */}
          <div className="hidden sm:block">
            <h1 className="font-medium text-lg text-[#FFFFFF]">
              {currentSection}
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-2 md:gap-4">
          {/* Discord Button */}
          <a 
            href="https://discord.gg/clyne" 
            target="_blank" 
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-[#FFFFFF] hover:text-[#9D8DFF] transition-colors py-2 px-3 rounded-md hover:bg-[#3A3A3E]/50"
            title="Join Support Server"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
              <path d="M20.317 4.492c-1.53-.69-3.17-1.2-4.885-1.49a.075.075 0 0 0-.079.036c-.21.39-.444.9-.608 1.297a18.25 18.25 0 0 0-5.487 0 12.78 12.78 0 0 0-.617-1.296.077.077 0 0 0-.079-.037c-1.714.29-3.354.8-4.885 1.491a.07.07 0 0 0-.032.027C.533 9.093-.32 13.555.099 17.961a.08.08 0 0 0 .031.055 20.03 20.03 0 0 0 6.031 3.056.077.077 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.995a.076.076 0 0 0-.041-.106 13.21 13.21 0 0 1-1.872-.892.077.077 0 0 1-.008-.128c.126-.094.252-.192.372-.292a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.1.246.198.373.292a.077.077 0 0 1-.006.127 12.28 12.28 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.96 19.96 0 0 0 6.032-3.055.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.06.06 0 0 0-.031-.028zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z" />
            </svg>
            <span className="hidden sm:block">Support Server</span>
          </a>

          {/* Partner Servers Button */}
          <a 
            href="/community-servers" 
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-[#FFFFFF] hover:text-[#9D8DFF] transition-colors py-2 px-3 rounded-md hover:bg-[#3A3A3E]/50 relative"
            title="Community Servers"
          >
            <Network size={18} />
            <span className="hidden md:block">Community Servers</span>
            {/* Mobile-friendly indicator */}
            <div className="md:hidden absolute -top-1 -right-1">
              <span className="flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#9D8DFF] opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-[#9D8DFF]"></span>
              </span>
            </div>
          </a>

          {/* Placeholder for removed buttons */}

          {isLoading ? (
            <div className="flex items-center gap-4 animate-pulse">
              <div className="w-10 h-10 rounded-full bg-[#3A3A3E]"></div>
              <div className="text-right sm:block">
                <div className="h-5 w-32 bg-[#3A3A3E] rounded mb-2"></div>
                <div className="h-4 w-24 bg-[#3A3A3E] rounded"></div>
              </div>
            </div>
          ) : (
            <div ref={profileMenuRef} className="relative">
              {/* معلومات المستخدم والصورة */}
              <div
                className="flex items-center gap-3 cursor-pointer group"
                onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)}
              >
                {/* صورة المستخدم مع تأثير عند التحويم */}
                <div className="relative">
                  <div className="p-0.5 rounded-full group-hover:bg-[#8875FF]/20 transition-colors">
                    <img
                      src={getAvatarUrl()}
                      alt="Profile"
                      className="w-8 h-8 sm:w-10 sm:h-10 rounded-full object-cover border-2 border-transparent group-hover:border-[#8875FF] transition-all"
                      onError={(e) => {
                        console.error("Avatar loading error, using fallback");
                        const target = e.target as HTMLImageElement;
                        target.src =
                          "https://cdn.discordapp.com/embed/avatars/0.png";
                      }}
                    />
                  </div>
                  <span className="absolute bottom-0 right-0 w-2 h-2 sm:w-3 sm:h-3 bg-green-500 rounded-full border-2 border-[#1F1F23]"></span>
                </div>

                {/* معلومات المستخدم */}
                <div className="text-right text-xs sm:text-base">
                  <p className="font-medium flex items-center text-[#FFFFFF]">
                    {userData.username || "Guest"}
                    {userData.verified && (
                      <svg
                        className="ml-1 h-4 w-4 sm:h-5 sm:w-5 text-[#9D8DFF]"
                        viewBox="0 0 22 22"
                        fill="currentColor"
                      >
                        <path d="M20.396 11c-.018-.646-.215-1.275-.57-1.816-.354-.54-.852-.972-1.438-1.246.223-.607.27-1.264.14-1.897-.131-.634-.437-1.218-.882-1.687-.47-.445-1.053-.75-1.687-.882-.633-.13-1.29-.083-1.897.14-.273-.587-.704-1.086-1.245-1.44S11.647 1.62 11 1.604c-.646.017-1.273.213-1.813.568s-.969.854-1.24 1.44c-.608-.223-1.267-.272-1.902-.14-.635.13-1.22.436-1.69.882-.445.47-.749 1.055-.878 1.688-.13.633-.08 1.29.144 1.896-.587.274-1.087.705-1.443 1.245-.356.54-.555 1.17-.574 1.817.02.647.218 1.276.574 1.817.356.54.856.972 1.443 1.245-.224.606-.274 1.263-.144 1.896.13.634.433 1.218.877 1.688.47.443 1.054.747 1.687.878.633.132 1.29.084 1.897-.136.274.586.705 1.084 1.246 1.439.54.354 1.17.551 1.816.569.647-.016 1.276-.213 1.817-.567s.972-.854 1.245-1.44c.604.239 1.266.296 1.903.164.636-.132 1.22-.447 1.68-.907.46-.46.776-1.044.908-1.681s.075-1.299-.165-1.903c.586-.274 1.084-.705 1.439-1.246.354-.54.551-1.17.569-1.816zM9.662 14.85l-3.429-3.428 1.293-1.302 2.072 2.072 4.4-4.794 1.347 1.246z" />
                      </svg>
                    )}
                  </p>
                  <p className="text-[10px] sm:text-sm text-[#C4C4C7]">
                    Cryptonel{" "}
                    {userData.accountType?.replace("Cryptonel ", "") ||
                      "Client"}
                  </p>
                </div>

                {/* أيقونة القائمة المنسدلة - only visible on sm and up */}
                <ChevronDown
                  size={18}
                  className={`hidden sm:block text-[#C4C4C7] group-hover:text-[#9D8DFF] transition-all transform ${
                    isProfileMenuOpen ? "rotate-180" : "rotate-0"
                  }`}
                />
              </div>

              {/* القائمة المنسدلة - بدون رأس المعلومات */}
              {isProfileMenuOpen && (
                <div className="absolute right-0 mt-2 w-60 bg-[#2A2A2E] rounded-lg shadow-xl py-2 z-50 border border-[#3A3A3E]">
                  {/* Placeholder for removed ratings button */}
                  <button
                    onClick={handleLogout}
                    className="flex items-center gap-3 px-4 py-2.5 hover:bg-[#3A3A3E] text-[#FFFFFF] w-full text-left"
                  >
                    <LogOut size={18} className="text-[#B0B0B5]" />
                    <span>Log Out</span>
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default Navbar;

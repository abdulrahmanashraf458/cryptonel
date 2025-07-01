import React, { useState, useEffect, useMemo } from "react";
import {
  EyeOff,
  Eye,
  Palette,
  Shield,
  Wallet,
  BadgeCheck,
  Crown as CrownIcon,
  Check,
  X,
  AlertCircle,
  Info,
  ChevronRight,
  Trophy,
  Diamond,
  Star,
} from "lucide-react";
import axios, { AxiosError } from "axios";
import { HexColorPicker } from "react-colorful";

const Privacy = () => {
  const [tempProfileHidden, setTempProfileHidden] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState("");
  const [isPremium, setIsPremium] = useState(false);
  const [premiumChecked, setPremiumChecked] = useState(false);

  // Add CSRF token state
  const [csrfToken, setCsrfToken] = useState<string>('');

  // Privacy settings
  const [hideBalance, setHideBalance] = useState(false);
  const [hideAddress, setHideAddress] = useState(false);
  const [hideVerification, setHideVerification] = useState(false);
  const [hiddenWalletMode, setHiddenWalletMode] = useState(false);

  // Premium settings (appearance only)
  const [primaryColor, setPrimaryColor] = useState("#FFD700"); // Gold
  const [secondaryColor, setSecondaryColor] = useState("#B9A64B"); // Darker gold
  const [balanceColor, setBalanceColor] = useState("#DAA520"); // Goldenrod
  
  // Color toggles
  const [enableSecondaryColor, setEnableSecondaryColor] = useState(true);
  const [enableBalanceColor, setEnableBalanceColor] = useState(true);

  // بيانات المستخدم الحقيقية
  const [userData, setUserData] = useState({
    username: "Username",
    rank: 7,
    balance: "2,500.00",
    address: "0x71C7...F8E1",
    avatar: "",
    is_premium: false,
    is_verified: false
  });

  // Expanded sections
  const [expandedSection, setExpandedSection] = useState<string | null>(null);

  // Color picker state
  const [activeColorPicker, setActiveColorPicker] = useState<string | null>(
    null
  );

  // Fetch profile visibility status when the component mounts
  useEffect(() => {
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

    // Initialize data
    const initializeData = async () => {
      await fetchCsrfToken();
      await fetchPrivacySettings();
      await fetchUserData();
    };

    initializeData();
    
    // إغلاق منتقي الألوان عند النقر خارجه
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (!target.closest('.color-picker-container') && !target.closest('.color-selector')) {
        setActiveColorPicker(null);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);
  
  // دالة لجلب بيانات المستخدم الحقيقية من الخادم
  const fetchUserData = async () => {
    try {
      setIsLoading(true);
      // استدعاء API للحصول على بيانات المستخدم
      const response = await axios.get("/api/overview", {
        headers: {
          'X-CSRF-Token': csrfToken
        },
        withCredentials: true
      });
      
      if (response.data) {
        // تحديث بيانات المستخدم من الاستجابة
        setUserData({
          username: response.data.username || "Username",
          rank: response.data.leaderboard?.rank || 7,
          balance: response.data.balance || "0.00",
          address: response.data.address?.public ? 
            `${response.data.address.public.substring(0, 6)}...${response.data.address.public.substring(response.data.address.public.length - 4)}` 
            : "0x0000...0000",
          avatar: response.data.avatar || "",
          is_premium: response.data.premium || false,
          is_verified: response.data.verified || false
        });
      }
    } catch (err) {
      console.error("خطأ في جلب بيانات المستخدم:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchPrivacySettings = async () => {
    try {
      setIsLoading(true);

      // الحصول على الإعدادات الحالية
      const response = await axios.get("/api/privacy/privacy-settings", {
        headers: {
          'X-CSRF-Token': csrfToken
        },
        withCredentials: true
      });
      const settings = response.data;

      if (settings.success) {
        setIsPremium(settings.is_premium);
        
        // تحديث الإعدادات من البيانات المسترجعة
        setTempProfileHidden(settings.profile_hidden);
        setHideBalance(settings.hide_balance);
        setHideAddress(settings.hide_address);
        
        // Use hide_badges field directly - this is the primary field now
        setHideVerification(settings.hide_badges || false);
        
        // hiddenWalletMode is deprecated, but we'll still read it for backward compatibility
        setHiddenWalletMode(false);

        // تحديث الألوان إذا كانت موجودة وكان المستخدم بريميوم
        if (settings.is_premium) {
          setPrimaryColor(settings.primary_color || "#FFD700");
          setSecondaryColor(settings.secondary_color || "#B9A64B");
          setBalanceColor(settings.highlight_color || "#DAA520");
          setEnableSecondaryColor(
            settings.enable_secondary_color !== undefined
              ? settings.enable_secondary_color
              : true
          );
          setEnableBalanceColor(
            settings.enable_highlight_color !== undefined
              ? settings.enable_highlight_color
              : true
          );
        }
      } else {
        setError("Failed to load settings");
      }
    } catch (err) {
      // Handle errors
      const axiosError = err as AxiosError;
      if (axiosError.response && axiosError.response.status === 403) {
        setIsPremium(false);
        console.log("User is not premium");
      } else {
        console.error("Error fetching privacy settings:", err);
        setError("Failed to load privacy settings"); // إضافة رسالة خطأ
      }
    } finally {
      // Mark premium check as completed whether successful or not
      setPremiumChecked(true);
      setIsLoading(false); // إنهاء التحميل
    }
  };

  const savePrivacySettings = async () => {
    try {
      setIsLoading(true);

      // أولاً، تحديث إعدادات الخصوصية العادية
      const settings: any = {
        profile_hidden: tempProfileHidden, // Only affects username and avatar
      };

      // Add premium features only if user is premium
      if (isPremium) {
        settings.hide_balance = hideBalance;
        settings.hide_address = hideAddress;
        settings.hide_badges = hideVerification; // This is the primary field now - use directly
      }

      console.log("Saving privacy settings:", settings);

      const response = await axios.post(
        "/api/privacy/privacy-settings",
        settings,
        {
          headers: {
            'X-CSRF-Token': csrfToken
          },
          withCredentials: true
        }
      );

      if (response.data.success) {
        setTempProfileHidden(tempProfileHidden); // تحديث الحالة الفعلية بعد الحفظ بنجاح
        setSaveSuccess(true);
        
        // Refresh leaderboard to see changes
        try {
          await axios.post("/api/leaderboard/refresh", {}, {
            headers: {
              'X-CSRF-Token': csrfToken
            },
            withCredentials: true
          });
        } catch (err) {
          console.warn("Failed to refresh leaderboard, but settings were saved.");
        }
        
        setTimeout(() => setSaveSuccess(false), 3000);
      }
    } catch (err) {
      console.error("Error updating privacy settings:", err);
      
      // Handle premium required error
      const axiosError = err as AxiosError;
      if (axiosError.response && axiosError.response.status === 403) {
        setError("Some settings require premium membership");
        setIsPremium(false); // Update UI to reflect correct premium status
      } else {
        setError("Failed to update privacy settings");
      }
      
      setTimeout(() => setError(""), 3000);
    } finally {
      setIsLoading(false);
    }
  };

  const saveAppearanceSettings = async () => {
    if (!isPremium) {
      setError("Premium membership required for appearance customization");
      setTimeout(() => setError(""), 3000);
      return;
    }

    try {
      setIsLoading(true);

      // تجهيز الإعدادات كاملة من أجل الحفظ
      const settings = {
        primary_color: primaryColor,
        secondary_color: secondaryColor,
        highlight_color: balanceColor,
        enable_secondary_color: enableSecondaryColor,
        enable_highlight_color: enableBalanceColor
      };

      console.log("Saving appearance settings:", settings);

      const response = await axios.post(
        "/api/privacy/appearance-settings",
        settings,
        {
          headers: {
            'X-CSRF-Token': csrfToken
          },
          withCredentials: true
        }
      );

      if (response.data.success) {
        setSaveSuccess(true);
        
        // تحديث البيانات المحلية بعد الحفظ بنجاح
        setUserData(prevData => ({
          ...prevData,
          primary_color: primaryColor,
          secondary_color: secondaryColor,
          highlight_color: balanceColor,
          enable_secondary_color: enableSecondaryColor,
          enable_highlight_color: enableBalanceColor
        }));
        
        // تحديث أيضاً لعرض التغييرات في صفحات أخرى
        await fetchUserData();
        
        // إخفاء رسالة النجاح بعد 3 ثوان
        setTimeout(() => setSaveSuccess(false), 3000);
      }
    } catch (err) {
      console.error("Error updating appearance settings:", err);
      
      // Handle premium required error
      const axiosError = err as AxiosError;
      if (axiosError.response && axiosError.response.status === 403) {
        setError("Premium membership required for appearance customization");
        setIsPremium(false); // Ensure UI updates to reflect non-premium status
      } else {
        setError("Failed to update appearance settings");
      }
      
      setTimeout(() => setError(""), 3000);
    } finally {
      setIsLoading(false);
    }
  };

  // Color picker helper functions
  const handleOpenColorPicker = (colorType: string) => {
    setActiveColorPicker(colorType);
  };

  const handleCloseColorPicker = () => {
    setActiveColorPicker(null);
  };

  const getColorDisplay = (colorType: string) => {
    switch (colorType) {
      case "primary":
        return primaryColor;
      case "secondary":
        return secondaryColor;
      case "highlight":
        return balanceColor;
      default:
        return "#FFFFFF";
    }
  };

  const handleColorChange = (color: string) => {
    if (activeColorPicker === "primary") {
      setPrimaryColor(color);
    } else if (activeColorPicker === "secondary") {
      setSecondaryColor(color);
    } else if (activeColorPicker === "highlight") {
      setBalanceColor(color);
    }
  };

  const handleColorInputChange = (
    e: React.ChangeEvent<HTMLInputElement>,
    type: string
  ) => {
    const value = e.target.value;
    const colorRegex = /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/;
    
    // التحقق من صحة قيمة اللون
    if (value.startsWith('#') && (value.length <= 7)) {
      if (type === "primary") {
        setPrimaryColor(value);
      } else if (type === "secondary") {
        setSecondaryColor(value);
      } else if (type === "highlight") {
        setBalanceColor(value);
      }
    }
  };

  // Funciones de utilidad copiadas de Leaderboard.tsx
  const formatPublicAddress = (address: string) => {
    if (!address) return "";
    if (address.length <= 10) return address;
    return `${address.substring(0, 6)}..${address.substring(address.length - 4)}`;
  };

  // Componente de insignia de verificación
  const VerificationBadge = () => (
    <svg
      className="ml-1 h-3 w-3 sm:h-4 sm:w-4 text-[#9D8DFF]"
      viewBox="0 0 22 22"
      fill="currentColor"
    >
      <path d="M20.396 11c-.018-.646-.215-1.275-.57-1.816-.354-.54-.852-.972-1.438-1.246.223-.607.27-1.264.14-1.897-.131-.634-.437-1.218-.882-1.687-.47-.445-1.053-.75-1.687-.882-.633-.13-1.29-.083-1.897.14-.273-.587-.704-1.086-1.245-1.44S11.647 1.62 11 1.604c-.646.017-1.273.213-1.813.568s-.969.854-1.24 1.44c-.608-.223-1.267-.272-1.902-.14-.635.13-1.22.436-1.69.882-.445.47-.749 1.055-.878 1.688-.13.633-.08 1.29.144 1.896-.587.274-1.087.705-1.443 1.245-.356.54-.555 1.17-.574 1.817.02.647.218 1.276.574 1.817.356.54.856.972 1.443 1.245-.224.606-.274 1.263-.144 1.896.13.634.433 1.218.877 1.688.47.443 1.054.747 1.687.878.633.132 1.29.084 1.897-.136.274.586.705 1.084 1.246 1.439.54.354 1.17.551 1.816.569.647-.016 1.276-.213 1.817-.567s.972-.854 1.245-1.44c.604.239 1.266.296 1.903.164.636-.132 1.22-.447 1.68-.907.46-.46.776-1.044.908-1.681s.075-1.299-.165-1.903c.586-.274 1.084-.705 1.439-1.246.354-.54.551-1.17.569-1.816zM9.662 14.85l-3.429-3.428 1.293-1.302 2.072 2.072 4.4-4.794 1.347 1.246z" />
    </svg>
  );

  // Componente de insignia de membresía
  const MembershipBadge = ({ type }: { type: string }) => {
    switch(type) {
      case "Premium":
        return (
          <div className="flex items-center px-2 py-0.5 text-xs font-semibold rounded-full bg-gradient-to-r from-amber-400 to-amber-600 text-black">
            <Diamond size={10} className="mr-1" />
            Premium
          </div>
        );
      case "Pro":
        return (
          <div className="flex items-center px-1.5 py-0.5 text-xs font-semibold rounded-full bg-gradient-to-r from-blue-500 to-indigo-600 text-white">
            <Star size={8} className="mr-1" />
            Pro
          </div>
        );
      case "Elite":
        return (
          <div className="flex items-center px-1.5 py-0.5 text-xs font-semibold rounded-full bg-gradient-to-r from-purple-500 to-pink-600 text-white">
            <CrownIcon size={8} className="mr-1" />
            Elite
          </div>
        );
      default:
        return (
          <div className="flex items-center px-1.5 py-0.5 text-xs font-semibold rounded-full bg-zinc-700 text-zinc-300">
            Standard
          </div>
        );
    }
  };

  // Componente de insignia compacta para usuarios premium
  const CompactPremiumBadge = () => {
    return (
      <span className="inline-flex items-center justify-center ml-1.5 w-4 h-4 bg-gradient-to-r from-yellow-400 to-amber-500 rounded-full">
        <Diamond size={8} className="text-black" />
      </span>
    );
  };

  // Componente para mostrar nombre de usuario
  const UsernameDisplay = ({ username, isVerified, isPremium }: { username: string, isVerified: boolean, isPremium: boolean }) => {
    return (
      <div className="flex items-center">
        <span className="font-medium">{username}</span>
        {isVerified && <VerificationBadge />}
        {isPremium && <CompactPremiumBadge />}
      </div>
    );
  };

  // Componente para mostrar el rango con estilo premium
  const RankBadge = ({ rank }: { rank: number }) => {
    return (
      <div className="flex items-center justify-center w-7 h-7 rounded-full bg-gradient-to-b from-yellow-300 to-amber-500 text-amber-900 font-bold text-sm shadow-md">
        {rank}
      </div>
    );
  };

  // مكون لعرض معاينة بطاقة المستخدم كما في صفحة المتصدرين
  const PreviewCard = () => {
    // Determine what to show based on privacy settings
    const showAvatar = !tempProfileHidden;
    const username = tempProfileHidden ? "Hidden Profile" : userData.username || "Username";
    const showBalance = !hideBalance;
    const showAddress = !hideAddress;
    const showVerification = !hideVerification && userData.is_verified;
    const showPremium = !hideVerification && isPremium;
    
    // تأثيرات Premium مماثلة لتلك الموجودة في Leaderboard.tsx
    const renderPremiumEffects = () => {
      if (!isPremium) return null;
      
      return (
        <div className="absolute inset-0 rounded-xl overflow-hidden pointer-events-none">
          {/* التدرج الأساسي */}
          <div 
            className="absolute inset-0 animate-pulse" 
            style={{ 
              background: `linear-gradient(to right, ${primaryColor}25, ${enableSecondaryColor ? secondaryColor + "25" : primaryColor + "25"}, ${primaryColor}25)`,
              boxShadow: enableSecondaryColor ? `inset 0 0 20px ${secondaryColor}50` : "none"
            }}
          />
          
          {/* توهج حول الحواف */}
          {enableSecondaryColor && (
            <div 
              className="absolute inset-0 opacity-20" 
              style={{ 
                boxShadow: `inset 0 0 20px 5px ${secondaryColor}70`,
              }}
            />
          )}
          
          {/* إضافة تأثيرات النجوم كما في صفحة Leaderboard */}
          <div className="absolute top-0 left-0 w-full h-full overflow-hidden opacity-30">
            <div className="absolute top-1/4 left-1/4 w-1 h-1 bg-white rounded-full opacity-70 animate-ping" style={{animationDuration: '3s'}}></div>
            <div className="absolute top-3/4 left-3/4 w-1 h-1 bg-white rounded-full opacity-70 animate-ping" style={{animationDuration: '2s'}}></div>
            <div className="absolute top-1/2 left-1/6 w-1 h-1 bg-white rounded-full opacity-70 animate-ping" style={{animationDuration: '4s'}}></div>
            <div className="absolute top-1/3 right-1/4 w-1 h-1 bg-white rounded-full opacity-70 animate-ping" style={{animationDuration: '3.5s'}}></div>
            <div className="absolute bottom-1/4 right-1/5 w-1 h-1 bg-white rounded-full opacity-70 animate-ping" style={{animationDuration: '2.7s'}}></div>
            <div className="absolute top-1/5 right-1/3 w-0.5 h-0.5 bg-white rounded-full opacity-70 animate-ping" style={{animationDuration: '5s'}}></div>
          </div>
        </div>
      );
    };
    
    return (
      <div className="bg-[#1E1E22] border border-[#3A3A3E] rounded-xl p-4 relative overflow-hidden">
        {/* تأثيرات Premium */}
        {renderPremiumEffects()}
        
        {/* محاكاة تصميم بطاقات Leaderboard */}
        <div className="mb-2 flex items-center justify-between">
          <div className="text-xs text-gray-400">Preview</div>
          <div className="text-xs text-gray-400">Rank #{userData.rank}</div>
        </div>
        
        <div className="flex items-center">
          {/* صورة المستخدم */}
          <div className="w-12 h-12 rounded-full overflow-hidden bg-[#2A2A2E] mr-3 flex items-center justify-center border border-[#3A3A3E]">
            {showAvatar ? (
              <img
                src={userData.avatar || `https://cdn.discordapp.com/embed/avatars/1.png`}
                alt="Avatar"
                className="w-full h-full object-cover"
              />
            ) : (
              <EyeOff size={20} className="text-[#C4C4C7]" />
            )}
          </div>
          
          {/* معلومات المستخدم */}
          <div className="flex-1">
            <div className="flex items-center">
              <div className="font-medium text-white">{username}</div>
              {showVerification && <VerificationBadge />}
              {showPremium && <CompactPremiumBadge />}
            </div>
            <div className="text-sm flex justify-between items-center mt-1">
              <div className="text-xs text-[#C4C4C7] font-mono">{showAddress ? userData.address : "Hidden"}</div>
              <div style={{ color: enableBalanceColor ? balanceColor : "#DAA520" }} className="font-medium">
                {showBalance ? `${userData.balance} CRN` : "Hidden"}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Toggle section expansion
  const toggleSection = (section: string) => {
    if (expandedSection === section) {
      setExpandedSection(null);
    } else {
      setExpandedSection(section);
    }
  };

  // منتقي الألوان المحسن
  const ColorPicker = () => {
    if (!activeColorPicker) return null;
    
    const activeColor = getColorDisplay(activeColorPicker);
    const colorTitle = activeColorPicker === "primary" 
      ? "Primary Color" 
      : activeColorPicker === "secondary" 
        ? "Secondary Color" 
        : "Balance Color";
    
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
        <div className="color-picker-container bg-[#1E1E22] border border-[#393939] rounded-xl shadow-xl p-4 sm:p-6 w-[90%] max-w-sm">
          <div className="flex justify-between items-center mb-4 border-b border-[#393939] pb-3">
            <h3 className="font-medium text-gray-200 flex items-center">
              <Palette className="h-5 w-5 mr-2 text-indigo-500" />
              <span>Select {colorTitle}</span>
            </h3>
            <button 
              onClick={handleCloseColorPicker}
              className="text-gray-400 hover:text-white p-1 rounded-full hover:bg-[#393939] transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
          
          <div className="mb-5 flex justify-center">
            <div 
              className="h-16 w-16 rounded-xl border-4 shadow-lg" 
              style={{ 
                backgroundColor: activeColor,
                borderColor: `${activeColor}90`,
                boxShadow: `0 0 15px ${activeColor}60`
              }}
            ></div>
          </div>
          
          <div className="mb-4 relative">
            <HexColorPicker 
              color={activeColor} 
              onChange={handleColorChange}
              className="w-full !h-48 touch-none"
            />
          </div>
          
          <div className="flex gap-3 items-center">
            <div className="bg-[#2A2A2E] rounded-lg p-2 flex-1">
              <input
                type="text"
                value={activeColor}
                onChange={(e) => handleColorInputChange(e, activeColorPicker)}
                className="w-full bg-transparent border-none text-center text-white font-mono uppercase focus:outline-none"
                maxLength={7}
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleCloseColorPicker}
                className="px-3 py-2 bg-[#393939] hover:bg-[#444] text-gray-200 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCloseColorPicker}
                className="px-3 py-2 bg-gradient-to-r from-indigo-600 to-blue-700 hover:from-indigo-700 hover:to-blue-800 text-white rounded-lg transition-colors"
              >
                Done
              </button>
            </div>
          </div>
          
          <div className="mt-4 flex flex-wrap gap-2 justify-center">
            {['#FFD700', '#9D8DFF', '#FF6B6B', '#4CAF50', '#2196F3', '#FF9800', '#E91E63', '#00BCD4'].map(color => (
              <button
                key={color}
                className="w-8 h-8 rounded-full border-2 transition-transform hover:scale-110"
                style={{ 
                  backgroundColor: color,
                  borderColor: color === activeColor ? 'white' : 'transparent'
                }}
                onClick={() => handleColorChange(color)}
              />
            ))}
          </div>
        </div>
      </div>
    );
  };

  // Show loading state while checking premium status
  if (isLoading && !premiumChecked) {
    return (
      <div className="min-h-screen bg-[#262626] flex items-center justify-center p-4">
        <div className="flex flex-col items-center">
          <div className="w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="mt-3 text-blue-400 font-medium text-sm">
            Loading privacy settings...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#262626] pb-20 pt-2">
      <div className="px-3 sm:px-6 md:px-8 max-w-lg md:max-w-4xl mx-auto">
        {/* إضافة أنماط للأنيميشن */}
        <style>{`
          @keyframes floatAnimation {
            0% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
            100% { transform: translateY(0px); }
          }
          
          .animate-float {
            animation: floatAnimation 3s ease-in-out infinite;
          }
          
          @keyframes pulse-slow {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 0.5; }
          }
          
          .animate-pulse-slow {
            animation: pulse-slow 4s ease-in-out infinite;
          }
          
          .glass-effect {
            background: rgba(42, 42, 46, 0.7);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(58, 58, 62, 0.5);
          }
        `}</style>

        <div className="mb-4 sm:mb-8">
          <h1 className="text-lg sm:text-2xl font-bold mb-1 text-gray-100">
            Privacy Settings
          </h1>
          <p className="text-xs sm:text-base text-gray-400">
            Manage your wallet privacy and visibility
          </p>
        </div>

        {error && (
          <div className="bg-red-900/30 border border-red-800 text-red-400 px-3 py-2 rounded mb-3 sm:mb-6 flex items-start">
            <AlertCircle className="h-4 w-4 text-red-500 mr-2 shrink-0 mt-0.5" />
            <span className="text-xs sm:text-sm">{error}</span>
          </div>
        )}

        {saveSuccess && (
          <div className="bg-green-900/30 border border-green-800 text-green-400 px-3 py-2 rounded mb-3 sm:mb-6 flex items-start">
            <Check className="h-4 w-4 text-green-500 mr-2 shrink-0 mt-0.5" />
            <span className="text-xs sm:text-sm">Settings saved successfully!</span>
          </div>
        )}

        <div className="grid gap-2 sm:gap-4">
          {/* Privacy Controls - Now available for all users */}
          <div className="bg-[#2b2b2b] rounded-lg sm:rounded-xl shadow-md border border-[#393939] px-3 sm:px-6 py-3 sm:py-5 transition-all duration-200">
            <div
              className="flex items-center justify-between cursor-pointer touch-manipulation"
              onClick={() => toggleSection("privacyControls")}
            >
              <div className="flex items-center gap-2 sm:gap-4">
                <div className="p-1.5 sm:p-3 bg-indigo-900/30 rounded-lg flex-shrink-0">
                  <Shield className="text-indigo-400 h-4 w-4 sm:h-6 sm:w-6" />
                </div>
                <div>
                  <div className="flex items-center flex-wrap gap-1 sm:gap-0">
                    <h3 className="font-semibold text-sm sm:text-lg text-gray-200">
                      Privacy Controls
                    </h3>
                  </div>
                  <p className="text-xs text-gray-400">
                    Advanced privacy options
                  </p>
                </div>
              </div>
              <ChevronRight
                className={`h-5 w-5 text-gray-400 transition-transform duration-200 ${
                  expandedSection === "privacyControls"
                    ? "transform rotate-90"
                    : ""
                }`}
              />
            </div>

            {expandedSection === "privacyControls" && (
              <div className="mt-3 sm:mt-5 pt-2 sm:pt-4 border-t border-[#393939]">
                <div className="space-y-2 sm:space-y-4 mb-3 sm:mb-6">
                  {/* Hide Public Profile */}
                  <div className="flex justify-between items-center bg-[#232323] p-2.5 sm:p-4 rounded-lg border border-[#393939]">
                    <div className="flex items-center">
                      <div className="p-1.5 bg-indigo-900/30 rounded-lg mr-2 sm:mr-3">
                        <EyeOff className="h-3.5 w-3.5 sm:h-5 sm:w-5 text-indigo-400" />
                      </div>
                      <div>
                        <span className="text-xs sm:text-sm font-medium text-gray-200">
                          Hide Public Profile
                        </span>
                        <p className="text-[9px] sm:text-xs text-gray-400 mt-0.5 sm:mt-1">
                          Hide your username and avatar only
                        </p>
                      </div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer touch-manipulation">
                      <input
                        type="checkbox"
                        className="sr-only peer"
                        checked={tempProfileHidden}
                        onChange={() =>
                          setTempProfileHidden(!tempProfileHidden)
                        }
                        disabled={isLoading}
                      />
                      <div
                        className={`w-9 h-5 sm:w-12 sm:h-6 rounded-[20px] peer-focus:ring-2 peer-focus:ring-indigo-500 
                        ${tempProfileHidden ? "bg-indigo-600" : "bg-gray-700"} 
                        peer-disabled:opacity-50 transition-colors duration-200
                        after:content-[''] after:absolute after:top-[2px] after:left-[2px] 
                        after:bg-gray-200 after:rounded-full after:h-4 after:w-4 sm:after:h-5 sm:after:w-5
                        after:transition-all after:duration-200
                        ${
                          tempProfileHidden
                            ? "after:translate-x-4 sm:after:translate-x-6"
                            : ""
                        }
                      `}
                      ></div>
                    </label>
                  </div>

                  {/* Hide Balance */}
                  <div className="flex justify-between items-center bg-[#232323] p-2.5 sm:p-4 rounded-lg border border-[#393939]">
                    <div className="flex items-center">
                      <div className="p-1.5 bg-indigo-900/30 rounded-lg mr-2 sm:mr-3">
                        <Wallet className="h-3.5 w-3.5 sm:h-5 sm:w-5 text-indigo-400" />
                      </div>
                      <div>
                        <div className="flex items-center gap-1">
                          <span className="text-xs sm:text-sm font-medium text-gray-200">
                            Hide Balance
                          </span>
                          <span className="ml-1 px-1.5 py-0.5 bg-gradient-to-r from-yellow-700 to-amber-600 text-yellow-300 text-[8px] sm:text-[10px] rounded-full font-semibold flex items-center">
                            <CrownIcon className="h-2 w-2 mr-0.5" />
                            Premium
                          </span>
                        </div>
                        <p className="text-[9px] sm:text-xs text-gray-400 mt-0.5 sm:mt-1">
                          Hide your balance from your public profile
                        </p>
                      </div>
                    </div>
                    <label
                      className="relative inline-flex items-center cursor-pointer touch-manipulation"
                    >
                      <input
                        type="checkbox"
                        className="sr-only peer"
                        checked={hideBalance}
                        onChange={() => {
                          if (!isPremium) {
                            setError("Premium membership required to hide balance");
                            setTimeout(() => setError(""), 3000);
                            return;
                          }
                          setHideBalance(!hideBalance);
                        }}
                        disabled={!isPremium}
                      />
                      <div
                        className={`w-9 h-5 sm:w-12 sm:h-6 rounded-[20px] peer-focus:ring-2 peer-focus:ring-yellow-500 
                        ${hideBalance && isPremium ? "bg-gradient-to-r from-yellow-600 to-amber-600 shadow-[0_0_8px_1px_rgba(255,190,0,0.5)]" : "bg-gray-700"} 
                        peer-disabled:opacity-50 transition-all duration-200
                        after:content-[''] after:absolute after:top-[2px] after:left-[2px] 
                        after:bg-gray-200 after:rounded-full after:h-4 after:w-4 sm:after:h-5 sm:after:w-5
                        after:transition-all after:duration-200
                        ${
                          hideBalance && isPremium
                            ? "after:translate-x-4 sm:after:translate-x-6"
                            : ""
                        }
                      `}
                      ></div>
                    </label>
                  </div>

                  {/* Hide Address */}
                  <div className="flex justify-between items-center bg-[#232323] p-2.5 sm:p-4 rounded-lg border border-[#393939]">
                    <div className="flex items-center">
                      <div className="p-1.5 bg-indigo-900/30 rounded-lg mr-2 sm:mr-3">
                        <Wallet className="h-3.5 w-3.5 sm:h-5 sm:w-5 text-indigo-400" />
                      </div>
                      <div>
                        <div className="flex items-center gap-1">
                          <span className="text-xs sm:text-sm font-medium text-gray-200">
                            Hide Wallet Address
                          </span>
                          <span className="ml-1 px-1.5 py-0.5 bg-gradient-to-r from-yellow-700 to-amber-600 text-yellow-300 text-[8px] sm:text-[10px] rounded-full font-semibold flex items-center">
                            <CrownIcon className="h-2 w-2 mr-0.5" />
                            Premium
                          </span>
                        </div>
                        <p className="text-[9px] sm:text-xs text-gray-400 mt-0.5 sm:mt-1">
                          Hide your wallet address from public view
                        </p>
                      </div>
                    </div>
                    <label
                      className="relative inline-flex items-center cursor-pointer touch-manipulation"
                    >
                      <input
                        type="checkbox"
                        className="sr-only peer"
                        checked={hideAddress}
                        onChange={() => {
                          if (!isPremium) {
                            setError("Premium membership required to hide wallet address");
                            setTimeout(() => setError(""), 3000);
                            return;
                          }
                          setHideAddress(!hideAddress);
                        }}
                        disabled={!isPremium}
                      />
                      <div
                        className={`w-9 h-5 sm:w-12 sm:h-6 rounded-[20px] peer-focus:ring-2 peer-focus:ring-yellow-500 
                        ${hideAddress && isPremium ? "bg-gradient-to-r from-yellow-600 to-amber-600 shadow-[0_0_8px_1px_rgba(255,190,0,0.5)]" : "bg-gray-700"} 
                        peer-disabled:opacity-50 transition-all duration-200
                        after:content-[''] after:absolute after:top-[2px] after:left-[2px] 
                        after:bg-gray-200 after:rounded-full after:h-4 after:w-4 sm:after:h-5 sm:after:w-5
                        after:transition-all after:duration-200
                        ${
                          hideAddress && isPremium
                            ? "after:translate-x-4 sm:after:translate-x-6"
                            : ""
                        }
                      `}
                      ></div>
                    </label>
                  </div>

                  {/* Hide Badges */}
                  <div className="flex justify-between items-center bg-[#232323] p-2.5 sm:p-4 rounded-lg border border-[#393939]">
                    <div className="flex items-center">
                      <div className="p-1.5 bg-indigo-900/30 rounded-lg mr-2 sm:mr-3">
                        <BadgeCheck className="h-3.5 w-3.5 sm:h-5 sm:w-5 text-indigo-400" />
                      </div>
                      <div>
                        <div className="flex items-center gap-1">
                          <span className="text-xs sm:text-sm font-medium text-gray-200">
                            Hide Badges
                          </span>
                          <span className="ml-1 px-1.5 py-0.5 bg-gradient-to-r from-yellow-700 to-amber-600 text-yellow-300 text-[8px] sm:text-[10px] rounded-full font-semibold flex items-center">
                            <CrownIcon className="h-2 w-2 mr-0.5" />
                            Premium
                          </span>
                        </div>
                        <p className="text-[9px] sm:text-xs text-gray-400 mt-0.5 sm:mt-1">
                          Hide all badges (verification, premium, etc.)
                        </p>
                      </div>
                    </div>
                    <label
                      className="relative inline-flex items-center cursor-pointer touch-manipulation"
                    >
                      <input
                        type="checkbox"
                        className="sr-only peer"
                        checked={hideVerification}
                        onChange={() => {
                          if (!isPremium) {
                            setError("Premium membership required to hide badges");
                            setTimeout(() => setError(""), 3000);
                            return;
                          }
                          setHideVerification(!hideVerification);
                        }}
                        disabled={!isPremium}
                      />
                      <div
                        className={`w-9 h-5 sm:w-12 sm:h-6 rounded-[20px] peer-focus:ring-2 peer-focus:ring-yellow-500 
                        ${hideVerification && isPremium ? "bg-gradient-to-r from-yellow-600 to-amber-600 shadow-[0_0_8px_1px_rgba(255,190,0,0.5)]" : "bg-gray-700"} 
                        peer-disabled:opacity-50 transition-all duration-200
                        after:content-[''] after:absolute after:top-[2px] after:left-[2px] 
                        after:bg-gray-200 after:rounded-full after:h-4 after:w-4 sm:after:h-5 sm:after:w-5
                        after:transition-all after:duration-200
                        ${
                          hideVerification && isPremium
                            ? "after:translate-x-4 sm:after:translate-x-6"
                            : ""
                        }
                      `}
                      ></div>
                    </label>
                  </div>

                  {/* Informational note about profile visibility */}
                  {tempProfileHidden && (
                    <div className="p-2 sm:p-4 rounded-lg bg-indigo-900/20 text-xs text-indigo-300 border border-indigo-800">
                      <div className="flex items-start gap-2">
                        <Info className="text-indigo-400 shrink-0 mt-0.5 h-3.5 w-3.5 sm:h-5 sm:w-5" />
                        <div>
                          <p className="font-medium">
                            Profile is currently hidden
                          </p>
                          <p className="mt-1 text-[9px] sm:text-xs">
                            Your profile is completely hidden from other users, but you can still customize individual privacy settings.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Replace Hidden Wallet Mode with information note */}
                  <div className="bg-blue-900/20 border border-blue-900/30 rounded-lg p-2 sm:p-3 mt-3 sm:mt-4">
                    <div className="flex">
                      <Info size={16} className="text-blue-400 shrink-0 mt-0.5 mr-2" />
                      <p className="text-[10px] sm:text-xs text-blue-300">
                        <strong>How privacy settings work:</strong>
                        <br/>
                        • "Hide Public Profile" only hides your username and avatar
                        <br/>
                        • "Hide Balance" only hides your balance 
                        <br/>
                        • "Hide Wallet Address" only hides your wallet address
                        <br/>
                        • "Hide Badges" hides verification badges and other badges
                        <br/>
                        Each setting works independently.
                      </p>
                    </div>
                  </div>

                  <button
                    onClick={savePrivacySettings}
                    disabled={isLoading}
                    className="w-full px-3 py-2 sm:py-3 bg-gradient-to-r from-indigo-600 to-blue-700 hover:from-indigo-700 hover:to-blue-800 text-white font-medium rounded-lg shadow-md disabled:opacity-50 transition-colors duration-200 flex items-center justify-center text-xs sm:text-sm"
                  >
                    {isLoading ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                        <span>Saving...</span>
                      </>
                    ) : (
                      "Save Privacy Settings"
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Card Appearance Section - Premium Only */}
          {isPremium && (
            <div className="bg-[#2b2b2b] rounded-lg sm:rounded-xl shadow-md border-2 border-yellow-800 px-3 sm:px-6 py-3 sm:py-5 transition-all duration-200">
              <div
                className="flex items-center justify-between cursor-pointer touch-manipulation"
                onClick={() => toggleSection("cardAppearance")}
              >
                <div className="flex items-center gap-2 sm:gap-4">
                  <div className="p-1.5 sm:p-3 bg-yellow-900/30 rounded-lg flex-shrink-0">
                    <Palette className="text-yellow-500 h-4 w-4 sm:h-6 sm:w-6" />
                  </div>
                  <div>
                    <div className="flex items-center flex-wrap gap-1 sm:gap-0">
                      <h3 className="font-semibold text-sm sm:text-lg text-gray-200">
                        Card Appearance
                      </h3>
                      <span className="ml-1 px-1.5 py-0.5 bg-gradient-to-r from-yellow-700 to-amber-600 text-yellow-300 text-[8px] sm:text-xs rounded-full font-semibold flex items-center">
                        <CrownIcon className="h-2 w-2 sm:h-3 sm:w-3 mr-0.5" />
                        Premium
                      </span>
                    </div>
                    <p className="text-xs text-gray-400">
                      Customize card style
                    </p>
                  </div>
                </div>
                <ChevronRight
                  className={`h-5 w-5 text-gray-400 transition-transform duration-200 ${
                    expandedSection === "cardAppearance"
                      ? "transform rotate-90"
                      : ""
                  }`}
                />
              </div>

              {expandedSection === "cardAppearance" && (
                <div className="mt-3 sm:mt-5 pt-2 sm:pt-4 border-t border-[#393939]">
                  <div className="mb-5 sm:mb-8 bg-gradient-to-br from-[#2A2A2E]/80 to-[#1E1E22]/90 rounded-xl p-3 sm:p-6 shadow-lg border border-[#3A3A3E]/50 backdrop-filter backdrop-blur-sm relative overflow-hidden">
                    {/* تأثيرات بصرية خلفية */}
                    <div className="absolute inset-0 overflow-hidden">
                      <div className="absolute -inset-1 bg-gradient-to-br from-yellow-500/5 via-amber-500/5 to-yellow-500/5 animate-pulse-slow"></div>
                      <div className="absolute top-10 left-10 w-20 h-20 rounded-full bg-indigo-600/5 blur-2xl"></div>
                      <div className="absolute bottom-5 right-5 w-16 h-16 rounded-full bg-blue-600/5 blur-xl"></div>
                    </div>
                    
                    <div className="relative z-10">
                      <h4 className="font-medium text-sm mb-3 sm:mb-5 text-yellow-300 flex items-center">
                        <Trophy className="h-4 w-4 sm:h-5 sm:w-5 mr-2 text-yellow-400" />
                        Preview Your Style
                      </h4>
                      <PreviewCard />

                      {/* أضف بعض المعلومات التوضيحية */}
                      <div className="mt-4 p-3 bg-blue-900/20 rounded-lg border border-blue-900/30">
                        <p className="text-xs text-blue-300 flex items-start">
                          <Info className="h-4 w-4 mr-2 text-blue-400 flex-shrink-0 mt-0.5" />
                          <span>
                            This is how your card will appear on the leaderboard. The effects and colors will be visible to all users.
                          </span>
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="mb-5 sm:mb-7 space-y-4 sm:space-y-6">
                    {/* Primary Color */}
                    <div className="bg-[#232323] p-3 sm:p-4 rounded-lg border border-[#393939]">
                      <label className="block text-xs font-medium text-gray-300 mb-2 sm:mb-3 flex items-center">
                        <div className="p-1 bg-yellow-900/30 rounded-md mr-2">
                          <Palette className="h-3 w-3 sm:h-4 sm:w-4 text-yellow-500" />
                        </div>
                        Primary Color (Card Effect)
                      </label>
                      <div className="flex gap-2 sm:gap-3 items-center">
                        <div
                          className="color-selector h-8 w-8 sm:h-12 sm:w-12 rounded-md cursor-pointer border border-[#393939] shadow-md touch-manipulation transition-transform hover:scale-105 active:scale-95"
                          style={{ 
                            backgroundColor: primaryColor,
                            boxShadow: `0 0 10px ${primaryColor}40`
                          }}
                          onClick={() => handleOpenColorPicker("primary")}
                        ></div>
                        <input
                          type="text"
                          value={primaryColor}
                          onChange={(e) => handleColorInputChange(e, "primary")}
                          className="flex-1 text-xs p-2 sm:p-3 border border-[#393939] rounded-md shadow-sm bg-[#1E1E22] text-gray-200 focus:ring-2 focus:ring-yellow-700 focus:border-yellow-700 uppercase font-mono"
                        />
                      </div>
                      <p className="text-[9px] sm:text-xs text-gray-400 mt-2 flex items-center">
                        <Info className="h-3 w-3 mr-1 text-gray-500" />
                        Determines the card effect color
                      </p>
                    </div>

                    {/* Secondary Color */}
                    <div className="bg-[#232323] p-3 sm:p-4 rounded-lg border border-[#393939]">
                      <div className="flex justify-between items-center mb-2 sm:mb-3">
                        <label className="text-xs font-medium text-gray-300 flex items-center">
                          <div className="p-1 bg-yellow-900/30 rounded-md mr-2">
                            <Palette className="h-3 w-3 sm:h-4 sm:w-4 text-yellow-500" />
                          </div>
                          Secondary Color (Glow Effect)
                        </label>
                        <label className="relative inline-flex items-center cursor-pointer touch-manipulation">
                          <input
                            type="checkbox"
                            className="sr-only peer"
                            checked={enableSecondaryColor}
                            onChange={() => setEnableSecondaryColor(!enableSecondaryColor)}
                          />
                          <div
                            className={`w-9 h-5 sm:w-12 sm:h-6 rounded-[20px] peer-focus:ring-2 peer-focus:ring-indigo-500 
                            ${enableSecondaryColor ? "bg-indigo-600" : "bg-gray-700"} 
                            peer-disabled:opacity-50 transition-all duration-200
                            after:content-[''] after:absolute after:top-[2px] after:left-[2px] 
                            after:bg-gray-200 after:rounded-full after:h-4 after:w-4 sm:after:h-5 sm:after:w-5
                            after:transition-all after:duration-200
                            ${enableSecondaryColor ? "after:translate-x-4 sm:after:translate-x-6" : ""}`}
                          ></div>
                        </label>
                      </div>
                      <div className="flex gap-2 sm:gap-3 items-center">
                        <div
                          className={`color-selector h-8 w-8 sm:h-12 sm:w-12 rounded-md cursor-pointer border border-[#393939] shadow-md touch-manipulation transition-transform hover:scale-105 active:scale-95 ${!enableSecondaryColor ? "opacity-50" : ""}`}
                          style={{ 
                            backgroundColor: secondaryColor,
                            boxShadow: enableSecondaryColor ? `0 0 10px ${secondaryColor}40` : "none"
                          }}
                          onClick={() => enableSecondaryColor && handleOpenColorPicker("secondary")}
                        ></div>
                        <input
                          type="text"
                          value={secondaryColor}
                          onChange={(e) => handleColorInputChange(e, "secondary")}
                          className={`flex-1 text-xs p-2 sm:p-3 border border-[#393939] rounded-md shadow-sm bg-[#1E1E22] text-gray-200 focus:ring-2 focus:ring-yellow-700 focus:border-yellow-700 uppercase font-mono ${!enableSecondaryColor ? "opacity-50" : ""}`}
                          disabled={!enableSecondaryColor}
                        />
                      </div>
                      <p className="text-[9px] sm:text-xs text-gray-400 mt-2 flex items-center">
                        <Info className="h-3 w-3 mr-1 text-gray-500" />
                        Determines the card glow effect
                      </p>
                    </div>

                    {/* Balance Color */}
                    <div className="bg-[#232323] p-3 sm:p-4 rounded-lg border border-[#393939]">
                      <div className="flex justify-between items-center mb-2 sm:mb-3">
                        <label className="text-xs font-medium text-gray-300 flex items-center">
                          <div className="p-1 bg-yellow-900/30 rounded-md mr-2">
                            <Palette className="h-3 w-3 sm:h-4 sm:w-4 text-yellow-500" />
                          </div>
                          Balance Color (Text Color)
                        </label>
                        <label className="relative inline-flex items-center cursor-pointer touch-manipulation">
                          <input
                            type="checkbox"
                            className="sr-only peer"
                            checked={enableBalanceColor}
                            onChange={() => setEnableBalanceColor(!enableBalanceColor)}
                          />
                          <div
                            className={`w-9 h-5 sm:w-12 sm:h-6 rounded-[20px] peer-focus:ring-2 peer-focus:ring-indigo-500 
                            ${enableBalanceColor ? "bg-indigo-600" : "bg-gray-700"} 
                            peer-disabled:opacity-50 transition-all duration-200
                            after:content-[''] after:absolute after:top-[2px] after:left-[2px] 
                            after:bg-gray-200 after:rounded-full after:h-4 after:w-4 sm:after:h-5 sm:after:w-5
                            after:transition-all after:duration-200
                            ${enableBalanceColor ? "after:translate-x-4 sm:after:translate-x-6" : ""}`}
                          ></div>
                        </label>
                      </div>
                      <div className="flex gap-2 sm:gap-3 items-center">
                        <div
                          className={`color-selector h-8 w-8 sm:h-12 sm:w-12 rounded-md cursor-pointer border border-[#393939] shadow-md touch-manipulation transition-transform hover:scale-105 active:scale-95 ${!enableBalanceColor ? "opacity-50" : ""}`}
                          style={{
                            backgroundColor: balanceColor,
                            boxShadow: enableBalanceColor ? `0 0 10px ${balanceColor}` : "none",
                          }}
                          onClick={() => enableBalanceColor && handleOpenColorPicker("highlight")}
                        ></div>
                        <input
                          type="text"
                          value={balanceColor}
                          onChange={(e) => handleColorInputChange(e, "highlight")}
                          className={`flex-1 text-xs p-2 sm:p-3 border border-[#393939] rounded-md shadow-sm bg-[#1E1E22] text-gray-200 focus:ring-2 focus:ring-yellow-700 focus:border-yellow-700 uppercase font-mono ${!enableBalanceColor ? "opacity-50" : ""}`}
                          disabled={!enableBalanceColor}
                        />
                      </div>
                      <p className="text-[9px] sm:text-xs text-gray-400 mt-2 flex items-center">
                        <Info className="h-3 w-3 mr-1 text-gray-500" />
                        Determines the balance text color
                      </p>
                    </div>
                  </div>

                  <button
                    onClick={saveAppearanceSettings}
                    disabled={isLoading}
                    className="w-full px-4 py-3 bg-gradient-to-r from-indigo-600 to-blue-700 hover:from-indigo-700 hover:to-blue-800 text-white font-medium rounded-lg shadow-lg disabled:opacity-50 transition-all duration-200 flex items-center justify-center text-sm sm:text-base hover:shadow-[0_0_15px_rgba(79,70,229,0.5)]"
                  >
                    {isLoading ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                        <span>Saving...</span>
                      </>
                    ) : (
                      <>
                        <Check className="w-5 h-5 mr-2" />
                        <span>Save Changes</span>
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Non-Premium Info */}
          {!isPremium && (
            <div className="bg-[#2b2b2b] rounded-lg sm:rounded-xl shadow-md border border-[#393939] px-3 sm:px-6 py-3 sm:py-5">
              <div className="flex flex-col sm:flex-row sm:items-start gap-3 sm:gap-4">
                <div className="p-2 bg-blue-900/20 rounded-lg flex-shrink-0 mx-auto sm:mx-0">
                  <CrownIcon className="text-blue-400 h-5 w-5 sm:h-6 sm:w-6" />
                </div>
                <div className="flex-1 text-center sm:text-left">
                  <h3 className="font-semibold text-sm sm:text-lg text-gray-200 mb-2">
                    Premium Appearance Features
                  </h3>
                  <p className="text-xs text-gray-400 mb-3">
                    Upgrade to Premium to access custom appearance settings.
                  </p>
                  <div className="p-2.5 sm:p-4 rounded-lg bg-blue-900/20 text-xs text-blue-300 border border-blue-800">
                    Premium members can customize their card colors with custom
                    gradients and glow effects.
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Color Picker Modal - Enhanced for mobile */}
      {activeColorPicker && (
        <ColorPicker />
      )}
    </div>
  );
};

export default Privacy;

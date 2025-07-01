import React, { useState, useEffect, useCallback, useMemo, memo, useRef } from "react";
import { motion } from "framer-motion";
import {
  Trophy,
  Medal,
  Award,
  Crown,
  Diamond,
  Star,
  TrendingUp,
  EyeOff,
  Users
} from "lucide-react";
import axios from "axios";

// Simple debounce function to prevent multiple rapid calls
const debounce = (func: Function, wait: number) => {
  let timeout: ReturnType<typeof setTimeout>;
  return function executedFunction(...args: any[]) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

// Define the leaderboard user type
interface LeaderboardUser {
  rank: number;
  user_id: string;
  username: string;
  balance: string;
  formatted_balance: string;
  membership: string;
  avatar: string | null;
  avatar_url: string;
  verified: boolean;
  profile_hidden: boolean;
  public_address: string;
  is_premium?: boolean;
  is_vip?: boolean;
  is_staff?: boolean;
  is_frozen?: boolean;  // إضافة خاصية للحسابات المجمدة
  hide_verification?: boolean;
  hide_balance?: boolean;
  hide_address?: boolean;
  hide_avatar?: boolean;
  hidden_wallet_mode?: boolean;
  primary_color?: string;
  secondary_color?: string;
  highlight_color?: string;
  background_color?: string;
  enable_secondary_color?: boolean;
  enable_highlight_color?: boolean;
  bio?: string;
  last_active?: string;
  is_current_user?: boolean;
  hide_badges?: boolean;
}

// Format balance function to handle hidden wallet mode with smaller text
const formatBalance = (balance: string, hiddenWalletMode?: boolean) => {
  // Return zero with hidden wallet mode indicator in smaller text
  if (hiddenWalletMode) {
    return "0.00 (Hidden)";
  }
  
  // Return "Hidden" if the balance is already marked as hidden
  if (balance === "Hidden") {
    return "Hidden";
  }
  
  try {
    const numericBalance = parseFloat(balance);
    
    // For large numbers, format with K, M, B suffixes
    if (numericBalance >= 1000000000) {
      // Billions (B)
      return (numericBalance / 1000000000).toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }) + "B";
    } else if (numericBalance >= 1000000) {
      // Millions (M)
      return (numericBalance / 1000000).toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }) + "M";
    } else if (numericBalance >= 1000) {
      // Thousands (K)
      return (numericBalance / 1000).toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }) + "K";
    } else {
      // Regular numbers
      return numericBalance.toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
    }
  } catch (e) {
    return balance;
  }
};

// Format public address to show partial address
const formatPublicAddress = (address: string) => {
  if (!address) return "";
  
  if (address.length <= 10) return address;
  
  // Show first 6 and last 4 characters
  return `${address.substring(0, 6)}..${address.substring(address.length - 4)}`;
};

// Get avatar display component - memoized
const AvatarDisplay = memo(({ user }: { user: LeaderboardUser }) => {
  // Check if profile is completely hidden - ONLY this affects avatar
  if (user.profile_hidden) {
    return (
      <div className="w-full h-full bg-[#3A3A3E] rounded-full flex items-center justify-center">
        <EyeOff size={user.rank <= 3 ? 24 : 16} className="text-[#C4C4C7]" />
      </div>
    );
  } 
  
  return (
    <img
      src={user.avatar_url}
      alt={user.username}
      className="w-full h-full object-cover rounded-full"
      loading="lazy"
      onError={(e) => {
        (e.target as HTMLImageElement).src = `https://cdn.discordapp.com/embed/avatars/${parseInt(user.user_id, 10) % 5}.png`;
      }}
    />
  );
});

// Verification badge component
const VerificationBadge = ({ isTop3 = false }: { isTop3?: boolean }) => (
  <svg
    className={`ml-1.5 ${isTop3 ? 'h-5 w-5' : 'h-5 w-5'} text-[#9D8DFF] cursor-help`}
    viewBox="0 0 22 22"
    fill="currentColor"
    role="img"
    aria-labelledby="verified-title"
  >
    <title id="verified-title">Verified User</title>
    <path d="M20.396 11c-.018-.646-.215-1.275-.57-1.816-.354-.54-.852-.972-1.438-1.246.223-.607.27-1.264.14-1.897-.131-.634-.437-1.218-.882-1.687-.47-.445-1.053-.75-1.687-.882-.633-.13-1.29-.083-1.897.14-.273-.587-.704-1.086-1.245-1.44S11.647 1.62 11 1.604c-.646.017-1.273.213-1.813.568s-.969.854-1.24 1.44c-.608-.223-1.267-.272-1.902-.14-.635.13-1.22.436-1.69.882-.445.47-.749 1.055-.878 1.688-.13.633-.08 1.29.144 1.896-.587.274-1.087.705-1.443 1.245-.356.54-.555 1.17-.574 1.817.02.647.218 1.276.574 1.817.356.54.856.972 1.443 1.245-.224.606-.274 1.263-.144 1.896.13.634.433 1.218.877 1.688.47.443 1.054.747 1.687.878.633.132 1.29.084 1.897-.136.274.586.705 1.084 1.246 1.439.54.354 1.17.551 1.816.569.647-.016 1.276-.213 1.817-.567s.972-.854 1.245-1.44c.604.239 1.266.296 1.903.164.636-.132 1.22-.447 1.68-.907.46-.46.776-1.044.908-1.681s.075-1.299-.165-1.903c.586-.274 1.084-.705 1.439-1.246.354-.54.551-1.17.569-1.816zM9.662 14.85l-3.429-3.428 1.293-1.302 2.072 2.072 4.4-4.794 1.347 1.246z" />
  </svg>
);

// Membership badge component - redesigned
const MembershipBadge = ({ type, isTop3 = false }: { type: string, isTop3?: boolean }) => {
  const sizeClass = isTop3 ? "text-sm py-0.5 px-2" : "text-xs py-0.5 px-1.5";
  const iconSize = isTop3 ? 10 : 10;
  
  switch(type) {
    case "Premium":
      return null; // Premium users now use CompactPremiumBadge only
    case "Pro":
      return (
        <div className={`flex items-center ${sizeClass} font-semibold rounded-full bg-gradient-to-r from-blue-500 to-indigo-600 text-white`}>
          <Star size={iconSize} className="mr-1" />
          Pro
        </div>
      );
    case "Elite":
      return (
        <div className={`flex items-center ${sizeClass} font-semibold rounded-full bg-gradient-to-r from-purple-500 to-pink-600 text-white`}>
          <Crown size={iconSize} className="mr-1" />
          Elite
        </div>
      );
    default:
      // لا نعرض أي شيء للمستخدم العادي
      return null;
  }
};

// Compact premium badge
const CompactPremiumBadge = memo(({ isTop3 = false }: { isTop3?: boolean }) => {
  const sizeClass = isTop3 ? "h-5" : "h-5";
  
  return (
    <span className="inline-flex items-center justify-center ml-1.5 cursor-help" title="Premium User">
      <img 
        src="/images/premium.png"
        alt="Premium"
        className={`${sizeClass} object-contain`}
      />
    </span>
  );
});

// VIP Badge
const VIPBadge = memo(({ isTop3 = false }: { isTop3?: boolean }) => {
  const sizeClass = isTop3 ? "text-xs px-1.5 py-0.5" : "text-xs px-1.5 py-0.5";
  
  return (
    <span 
      className={`inline-flex items-center justify-center ml-1.5 ${sizeClass} bg-gradient-to-r from-purple-600 to-indigo-600 rounded-full text-white font-bold cursor-help`}
      title="VIP User"
    >
      VIP
    </span>
  );
});

// Staff Badge
const StaffBadge = memo(({ isTop3 = false }: { isTop3?: boolean }) => {
  const sizeClass = isTop3 ? "h-5" : "h-5";
  
  return (
    <span className="inline-flex items-center justify-center ml-1.5 cursor-help" title="Staff Member">
      <img 
        src="/images/staff.png"
        alt="Staff"
        className={`${sizeClass} object-contain`}
      />
    </span>
  );
});

// Username display component - redesigned
const UsernameDisplay = ({ user, isTop3 = false }: { user: LeaderboardUser, isTop3?: boolean }) => {
  // Create two parts - username (affected by profile_hidden) and badges (affected by hide_badges only)
  
  // Username part - affected by profile_hidden only
  const usernameDisplay = user.profile_hidden ? 
    <span className="text-[#C4C4C7] italic">Hidden Profile</span> :
    <span className={`font-medium text-white ${isTop3 ? "text-lg" : ""}`}>
      {user.username}
    </span>;
    
  // For debugging
  console.log(`User ${user.user_id} badges: hide_badges=${user.hide_badges}`);
    
  // Badges part - affected by hide_badges only, NOT by profile_hidden
  // Make sure hide_badges is explicitly checked for false (not falsy)
  // Only allow hiding badges if user is actually premium
  const canHideBadges = user.is_premium === true && user.hide_badges === true;
  const showBadges = !canHideBadges;
  
  const badgesDisplay = showBadges && (
    <>
      {user.verified && <VerificationBadge isTop3={isTop3} />}
      {user.is_premium && <CompactPremiumBadge isTop3={isTop3} />}
      {user.is_vip && <VIPBadge isTop3={isTop3} />}
      {user.is_staff && <StaffBadge isTop3={isTop3} />}
    </>
  );
  
  // Return combined display
  return (
    <div className="flex items-center">
      {usernameDisplay}
      {badgesDisplay}
    </div>
  );
};

// Premium user effects - enhanced
const PremiumEffect = ({ user }: { user: LeaderboardUser }) => {
  const primaryColor = user?.primary_color || '#9D8DFF';
  const secondaryColor = user?.secondary_color || '#FFA500';
  
  return (
    <div className="absolute inset-0 overflow-hidden rounded-xl pointer-events-none">
      {/* Animated gradient border */}
      <div 
        className="absolute inset-0 opacity-50 animate-pulse" 
        style={{ 
          background: `linear-gradient(to right, ${primaryColor}50, ${secondaryColor}50, ${primaryColor}50)`,
          filter: 'blur(8px)', 
          transform: 'scale(1.02)' 
        }} 
      />
      
      {/* Subtle light effects */}
      <div className="absolute top-0 left-0 w-full h-full">
        <div className="absolute top-0 left-1/4 w-1/2 h-1/6 bg-white opacity-10 rounded-full blur-xl" />
        <div className="absolute bottom-0 right-1/4 w-1/3 h-1/6 bg-white opacity-10 rounded-full blur-xl" />
      </div>
    </div>
  );
};

// Top 3 position effects - new
const TopPositionEffect = ({ position }: { position: number }) => {
  // تأثيرات مختلفة لكل مركز من المراكز الثلاثة الأولى
  const gradients = {
    0: "bg-gradient-to-br from-yellow-500/30 via-amber-400/40 to-yellow-300/30", // المركز الأول - ذهبي
    1: "bg-gradient-to-br from-slate-400/30 via-gray-300/40 to-slate-200/30",  // المركز الثاني - فضي
    2: "bg-gradient-to-br from-amber-700/30 via-amber-600/40 to-amber-500/30"  // المركز الثالث - برونزي
  }[position];

  return (
    <div className="absolute inset-0 overflow-hidden rounded-xl pointer-events-none">
      {/* Animated gradient background */}
      <div className={`absolute inset-0 ${gradients} animate-pulse-slow`} />
      
      {/* Sparkle effects */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden">
        <div className="absolute top-1/4 left-1/4 w-1 h-1 bg-white rounded-full opacity-70 animate-ping" style={{animationDuration: '3s'}}></div>
        <div className="absolute top-3/4 left-3/4 w-1 h-1 bg-white rounded-full opacity-70 animate-ping" style={{animationDuration: '2s'}}></div>
        <div className="absolute top-1/2 left-1/6 w-1 h-1 bg-white rounded-full opacity-70 animate-ping" style={{animationDuration: '4s'}}></div>
        <div className="absolute top-1/3 right-1/4 w-1 h-1 bg-white rounded-full opacity-70 animate-ping" style={{animationDuration: '3.5s'}}></div>
      </div>
    </div>
  );
};

// Rank badge component - new
const RankBadge = ({ rank }: { rank: number }) => {
  // Special styling for top 3 ranks
  if (rank <= 3) {
    const colors = {
      1: "from-yellow-300 to-amber-500 text-amber-900",
      2: "from-slate-300 to-slate-400 text-slate-800",
      3: "from-amber-600 to-amber-700 text-amber-100",
    }[rank] || "from-gray-600 to-gray-700 text-white";

    return (
      <div className={`flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-b ${colors} font-bold text-sm shadow-md`}>
        {rank}
      </div>
    );
  }
  
  // Regular rank badge
  return (
    <div className="flex items-center justify-center w-7 h-7 rounded-full bg-[#2A2A2E] text-[#C4C4C7] font-medium text-sm">
      {rank}
    </div>
  );
};

// Balance display component - new
const BalanceDisplay = ({ user }: { user: LeaderboardUser }) => {
  // Only show premium features like hidden balance if user is actually premium
  // IMPORTANT: Only check is_premium === true, not membership
  const canUseHiddenBalance = user.is_premium === true && user.hide_balance;
  const canUseHiddenWallet = user.is_premium === true && user.hidden_wallet_mode;
  
  // ONLY hide_balance affects balance visibility - NOT profile_hidden
  if (canUseHiddenBalance) {
    return <span className="text-[#C4C4C7] italic">Hidden</span>;
  }
  
  if (canUseHiddenWallet) {
    return (
      <div className="flex items-center">
        <span className="text-[#C4C4C7]">Hidden</span>
        <EyeOff size={14} className="ml-1 text-[#C4C4C7]" />
      </div>
    );
  }
  
  // Use custom highlight_color if available for premium users
  const textColor = (user.is_premium === true && user.highlight_color) 
    ? user.highlight_color 
    : "#FFFFFF";  // Changed from #DAA520 (goldenrod) to white for non-premium users
  
  return (
    <div className="font-medium" style={{ color: textColor }}>
      {formatBalance(user.balance)} CRN
    </div>
  );
};

// Address display component - new
const AddressDisplay = ({ user }: { user: LeaderboardUser }) => {
  // Only use hide_address if user is premium
  const canHideAddress = user.is_premium === true && user.hide_address;
  
  // ONLY hide_address affects address visibility - NOT profile_hidden
  if (canHideAddress) {
    return <span className="text-[#C4C4C7] italic">Hidden</span>;
  }
  
  return (
    <div className="text-xs text-[#C4C4C7] font-mono">
      {formatPublicAddress(user.public_address)}
    </div>
  );
};

// Top user card component - redesigned
const TopUserCard = ({ user, position }: { user: LeaderboardUser, position: number }) => {
  // الألوان المخصصة من إعدادات المستخدم - فقط للمستخدمين البريميوم
  const primaryColor = user.is_premium === true ? (user.primary_color || "#FFD700") : "#FFD700";  // Default gold
  const secondaryColor = user.is_premium === true ? (user.secondary_color || "#B9A64B") : "#B9A64B";  // Default darker gold
  const balanceColor = user.is_premium === true ? (user.highlight_color || "#DAA520") : "#DAA520";  // Default goldenrod
  
  // التحقق من إعدادات التفعيل - فقط للمستخدمين البريميوم
  const enableSecondaryColor = user.is_premium === true ? (user.enable_secondary_color !== false) : false;
  const enableBalanceColor = user.is_premium === true ? (user.enable_highlight_color !== false) : false;
  
  // Determine position styling
  const getPositionStyles = () => {
    switch (position) {
      case 0: // 1st place - Gold
        return {
          containerClasses: "border-yellow-500/50 shadow-lg shadow-amber-500/10 transform scale-105 z-10",
          badgeClasses: "bg-gradient-to-r from-yellow-300 to-amber-500",
          iconColor: "text-amber-400",
          icon: <Crown size={24} className="text-amber-400" />,
          label: "1st Place"
        };
      case 1: // 2nd place - Silver
        return {
          containerClasses: "border-slate-400/50 shadow-md shadow-slate-500/10",
          badgeClasses: "bg-gradient-to-r from-slate-300 to-slate-400",
          iconColor: "text-slate-300",
          icon: <Medal size={22} className="text-slate-300" />,
          label: "2nd Place"
        };
      case 2: // 3rd place - Bronze
        return {
          containerClasses: "border-amber-700/50 shadow-md shadow-amber-700/10",
          badgeClasses: "bg-gradient-to-r from-amber-600 to-amber-700",
          iconColor: "text-amber-600",
          icon: <Award size={22} className="text-amber-600" />,
          label: "3rd Place"
        };
      default:
        return {
          containerClasses: "border-gray-700/50",
          badgeClasses: "bg-gray-700",
          iconColor: "text-gray-400",
          icon: <Trophy size={20} className="text-gray-400" />,
          label: `${position + 1}th Place`
        };
    }
  };

  const styles = getPositionStyles();
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: position * 0.1 }}
      className={`relative rounded-xl border p-5 bg-[#1E1E22] border-[#3A3A3E] ${styles.containerClasses} backdrop-blur-sm overflow-hidden`}
      style={{ 
        boxShadow: user.is_premium === true && enableSecondaryColor ? `0 0 15px ${secondaryColor}40` : "none"
      }}
    >
      {/* تأثير مميز محسن للمستخدمين المميزين - يظهر فقط للمستخدمين البريميوم */}
      {user.is_premium === true && (
        <div className="absolute inset-0 rounded-xl overflow-hidden pointer-events-none">
          <div 
            className="absolute inset-0 animate-pulse" 
            style={{ 
              background: `linear-gradient(to right, ${primaryColor}20, ${enableSecondaryColor ? secondaryColor + "20" : primaryColor + "20"}, ${primaryColor}20)`,
              boxShadow: enableSecondaryColor ? `inset 0 0 20px ${secondaryColor}50` : "none"
            }}
          />
          {/* إضافة تأثيرات النجوم كما في صفحة البرايفسي */}
          <div className="absolute top-0 left-0 w-full h-full overflow-hidden opacity-30">
            <div className="absolute top-1/4 left-1/4 w-1 h-1 bg-white rounded-full opacity-70 animate-ping" style={{animationDuration: '3s'}}></div>
            <div className="absolute top-3/4 left-3/4 w-1 h-1 bg-white rounded-full opacity-70 animate-ping" style={{animationDuration: '2s'}}></div>
            <div className="absolute top-1/2 left-1/6 w-1 h-1 bg-white rounded-full opacity-70 animate-ping" style={{animationDuration: '4s'}}></div>
            <div className="absolute top-1/3 right-1/4 w-1 h-1 bg-white rounded-full opacity-70 animate-ping" style={{animationDuration: '3.5s'}}></div>
          </div>
        </div>
      )}
      
      {/* Position badge */}
      <div className="absolute top-3 right-3 z-10">
        <div className={`flex items-center justify-center w-10 h-10 rounded-full ${styles.badgeClasses} shadow-lg`}>
          {styles.icon}
        </div>
      </div>
      
      {/* User info */}
      <div className="flex flex-col items-center text-center space-y-3 relative z-10">
        {/* Avatar */}
        <div className="w-24 h-24 rounded-full overflow-hidden border-2 border-[#3A3A3E] bg-[#1E1E22] shadow-lg">
          <AvatarDisplay user={user} />
        </div>
        
        {/* Username */}
        <div className="mt-3">
          <UsernameDisplay user={user} isTop3={true} />
        </div>
        
        {/* Membership badge */}
        {user.membership !== "Standard" && !(user.is_premium === true && user.hide_badges === true) && (
          <div className="mt-1">
            <MembershipBadge type={user.membership} isTop3={true} />
          </div>
        )}
        
        {/* Balance */}
        <div className="mt-3">
          <BalanceDisplay user={user} />
        </div>
        
        {/* Address */}
        <div className="mt-1">
          <AddressDisplay user={user} />
        </div>
      </div>
    </motion.div>
  );
};

// User rank item component - redesigned
const UserRankItem = ({ user }: { user: LeaderboardUser }) => {
  // تحديد لون الخلفية والحدود بناءً على حالة المستخدم
  const getItemStyle = () => {
    // المستخدم الحالي له الأولوية دائمًا - لون بنفسجي
    if (user.is_current_user) {
      return "bg-[#1E1E22] border border-[#3A3A3E]";
    }
    
    // مستخدم Premium - لون ذهبي
    if (user.is_premium === true) {
      return "bg-[#1E1E22] border border-[#3A3A3E]";
    }
    
    // مستخدم عادي
    return "bg-[#1E1E22] border border-[#3A3A3E]";
  };

  // تحديد ما إذا كان العنصر هو للمستخدم الحالي أو مستخدم بريميوم
  const isPremiumOrCurrentUser = user.is_premium === true || user.is_current_user;
  
  // الألوان المخصصة من إعدادات المستخدم - فقط للمستخدمين البريميوم
  const primaryColor = user.is_premium === true ? (user.primary_color || "#FFD700") : "";  // Default gold
  const secondaryColor = user.is_premium === true ? (user.secondary_color || "#B9A64B") : "";  // Default darker gold
  const balanceColor = user.is_premium === true ? (user.highlight_color || "#DAA520") : "";  // Default goldenrod
  
  // التحقق من إعدادات التفعيل - فقط للمستخدمين البريميوم
  const enableSecondaryColor = user.is_premium === true ? (user.enable_secondary_color !== false) : false;
  const enableBalanceColor = user.is_premium === true ? (user.enable_highlight_color !== false) : false;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`relative flex items-center p-3 rounded-xl ${getItemStyle()} transition-all duration-200`}
      style={{ 
        boxShadow: isPremiumOrCurrentUser && enableSecondaryColor ? 
          `0 0 15px ${secondaryColor}40` : 
          "none"
      }}
    >
      {/* تأثير مميز محسن كما في صفحة Privacy للمستخدم البريميوم - يظهر فقط إذا كان المستخدم بريميوم فعلاً */}
      {user.is_premium === true && (
        <div className="absolute inset-0 rounded-xl overflow-hidden pointer-events-none">
          <div 
            className="absolute inset-0 animate-pulse" 
            style={{ 
              background: `linear-gradient(to right, ${primaryColor}20, ${enableSecondaryColor ? secondaryColor + "20" : primaryColor + "20"}, ${primaryColor}20)`,
              boxShadow: enableSecondaryColor ? `inset 0 0 20px ${secondaryColor}50` : "none"
            }}
          />
          {/* إضافة تأثيرات النجوم كما في صفحة البرايفسي */}
          <div className="absolute top-0 left-0 w-full h-full overflow-hidden opacity-30">
            <div className="absolute top-1/4 left-1/4 w-1 h-1 bg-white rounded-full opacity-70 animate-ping" style={{animationDuration: '3s'}}></div>
            <div className="absolute top-3/4 left-3/4 w-1 h-1 bg-white rounded-full opacity-70 animate-ping" style={{animationDuration: '2s'}}></div>
            <div className="absolute top-1/2 left-1/6 w-1 h-1 bg-white rounded-full opacity-70 animate-ping" style={{animationDuration: '4s'}}></div>
          </div>
        </div>
      )}
      
      {/* Rank */}
      <div className="mr-3 z-10">
        <RankBadge rank={user.rank} />
      </div>
      
      {/* Avatar */}
      <div className="w-10 h-10 rounded-full overflow-hidden border border-[#3A3A3E] bg-[#1E1E22] z-10">
        <AvatarDisplay user={user} />
      </div>
      
      {/* User info */}
      <div className="ml-3 flex-1 min-w-0 z-10">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center">
            <UsernameDisplay user={user} />
          </div>
          
          {/* Membership badge - only show on larger screens */}
          {user.membership !== "Standard" && user.hide_badges !== true && (
            <div className="hidden sm:block ml-2">
              <MembershipBadge type={user.membership} />
            </div>
          )}
          
          {/* Balance */}
          <div className="mt-1 sm:mt-0">
            <BalanceDisplay user={user} />
          </div>
        </div>
        
        {/* Second row - address and membership badge on mobile */}
        <div className="flex items-center justify-between mt-1">
          <AddressDisplay user={user} />
          
          {/* Membership badge - only show on mobile */}
          {user.membership !== "Standard" && user.hide_badges !== true && (
            <div className="block sm:hidden">
              <MembershipBadge type={user.membership} />
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};

// StatsCard component - new
const StatsCard = ({ 
  title, 
  value, 
  icon 
}: { 
  title: string, 
  value: string | number, 
  icon: React.ReactNode 
}) => {
  return (
    <div className="bg-[#2A2A2E]/80 border border-[#3A3A3E]/50 rounded-xl p-4 flex items-center">
      <div className="mr-4 bg-[#3A3A3E]/80 p-3 rounded-lg">
        {icon}
      </div>
      <div>
        <h3 className="text-sm text-gray-400 font-medium">{title}</h3>
        <p className="text-xl font-bold text-white">{value}</p>
      </div>
    </div>
  );
};

export default function Leaderboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [leaderboardData, setLeaderboardData] = useState<LeaderboardUser[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  
  // Add state for premium status
  const [isPremium, setIsPremium] = useState<boolean>(false);
  
  // CSRF token state
  const [csrfToken, setCsrfToken] = useState<string>('');
  
  // Remove pagination - we'll load all users at once
  // const [page, setPage] = useState(1);
  // const itemsPerPage = 20;
  
  // Add refs to track API call state and prevent duplicates
  const isLoadingRef = useRef(false);
  const requestTimeRef = useRef(0);
  // Remove scroll handler ref as we don't need it anymore
  // const scrollHandlerRef = useRef<((e: Event) => void) | null>(null);

  // Function to fetch CSRF token
  const fetchCsrfToken = async () => {
    try {
      console.log('Fetching CSRF token for leaderboard...');
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
        console.log('CSRF token received successfully for leaderboard');
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

  // No filtering needed anymore
  const filteredUsers = useMemo(() => {
    return leaderboardData;
  }, [leaderboardData]);

  // Function to check premium status
  const checkPremiumStatus = useCallback(async () => {
    try {
      // Check if CSRF token is available
      if (!csrfToken) {
        console.error('CSRF token not available for premium check');
        return;
      }

      const response = await axios.get('/api/premium/check', {
        headers: {
          'X-CSRF-Token': csrfToken
        },
        withCredentials: true
      });
      
      if (response.data.success) {
        setIsPremium(response.data.premium);
        
        // If settings were just reset, update the UI
        if (response.data.settings_reset) {
          console.log("Premium settings were reset. Refreshing leaderboard data...");
          fetchLeaderboardData(true);
        }
      } else {
        console.error("Failed to check premium status:", response.data.message);
        setIsPremium(false);
      }
    } catch (error: any) {
      console.error("Error checking premium status:", error);
      
      // Handle CSRF-related errors
      if (error.response?.status === 403 && error.response?.data?.error?.includes('CSRF')) {
        console.log('CSRF token expired, refreshing...');
        setCsrfToken('');
        
        const tokenRefreshed = await refreshCsrfToken();
        if (tokenRefreshed) {
          // Retry the request with the new token
          try {
            const retryResponse = await axios.get('/api/premium/check', {
              headers: {
                'X-CSRF-Token': csrfToken
              },
              withCredentials: true
            });
            
            if (retryResponse.data.success) {
              setIsPremium(retryResponse.data.premium);
            }
          } catch (retryError) {
            console.error('Failed to retry premium check:', retryError);
            setIsPremium(false);
          }
        } else {
          setIsPremium(false);
        }
      } else {
        setIsPremium(false);
      }
    }
  }, [csrfToken]);

  // Fetch leaderboard data with caching
  const fetchLeaderboardData = useCallback(async (forceRefresh = false) => {
    // Prevent concurrent requests
    if (isLoadingRef.current) return;
    
    // Prevent too frequent requests (at least 1 second between calls)
    const now = Date.now();
    if (!forceRefresh && now - requestTimeRef.current < 1000) return;
    
    // Check if CSRF token is available
    if (!csrfToken) {
      console.error('CSRF token not available for leaderboard data');
      setError('Security token not available. Please refresh the page and try again.');
      return;
    }
    
    try {
      isLoadingRef.current = true;
      setRefreshing(true);
      requestTimeRef.current = now;
      
      // Always add cache-busting parameter to ensure fresh data
      const url = `/api/leaderboard?_t=${now}`;
      
      const response = await axios.get(url, {
        headers: {
          'X-CSRF-Token': csrfToken
        },
        withCredentials: true
      });
      
      if (response.data.success) {
        // Add performance timing info
        console.log(`Leaderboard data fetched: ${response.data?.meta?.execution_time_ms || 'unknown'} ms`);
        
        // Process users to ensure premium-only features are disabled for non-premium users
        const processedUsers = response.data.data.map((user: LeaderboardUser) => {
          // If user is not premium, reset all premium features
          if (user.is_premium !== true) {
            return {
              ...user,
              hide_balance: false,
              hide_address: false,
              hide_badges: false,
              hide_verification: false,
              hidden_wallet_mode: false,
              primary_color: null,
              secondary_color: null,
              highlight_color: null,
              background_color: null
            };
          }
          return user;
        });
        
        setLeaderboardData(processedUsers);
        setError("");
      } else {
        setError("Failed to load leaderboard data");
      }
    } catch (err: any) {
      // Handle CSRF-related errors
      if (err.response?.status === 403 && err.response?.data?.error?.includes('CSRF')) {
        console.log('CSRF token expired, refreshing...');
        setCsrfToken('');
        
        const tokenRefreshed = await refreshCsrfToken();
        if (tokenRefreshed) {
          // Retry the request with the new token
          try {
            const retryUrl = `/api/leaderboard?_t=${now}`;
            const retryResponse = await axios.get(retryUrl, {
              headers: {
                'X-CSRF-Token': csrfToken
              },
              withCredentials: true
            });
            
            if (retryResponse.data.success) {
              const processedUsers = retryResponse.data.data.map((user: LeaderboardUser) => {
                if (user.is_premium !== true) {
                  return {
                    ...user,
                    hide_balance: false,
                    hide_address: false,
                    hide_badges: false,
                    hide_verification: false,
                    hidden_wallet_mode: false,
                    primary_color: null,
                    secondary_color: null,
                    highlight_color: null,
                    background_color: null
                  };
                }
                return user;
              });
              
              setLeaderboardData(processedUsers);
              setError("");
              return; // Exit early on success
            }
          } catch (retryError) {
            console.error('Failed to retry leaderboard fetch:', retryError);
          }
        }
      }
      
      setError("Error connecting to server");
      console.error("Leaderboard fetch error:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
      isLoadingRef.current = false;
    }
  }, [csrfToken]);

  // Initial data load and refresh on visibility change
  useEffect(() => {
    // First fetch CSRF token, then check premium status and fetch data
    const initializeData = async () => {
      await fetchCsrfToken();
      await checkPremiumStatus();
      await fetchLeaderboardData(true);
    };
    
    initializeData();
    
    // Remove scroll event listener as we don't need pagination anymore
    /*
    if (scrollHandlerRef.current) {
      window.removeEventListener('scroll', scrollHandlerRef.current);
    }
    
    scrollHandlerRef.current = debouncedHandleScroll;
    window.addEventListener('scroll', scrollHandlerRef.current);
    */
    
    // Add visibility change listener to refresh when tab becomes active
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        // Check premium status on visibility change
        checkPremiumStatus();
        fetchLeaderboardData(true);
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    // Cleanup
    return () => {
      /*
      if (scrollHandlerRef.current) {
        window.removeEventListener('scroll', scrollHandlerRef.current);
        scrollHandlerRef.current = null;
      }
      */
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  // Remove debouncedHandleScroll from dependencies as we don't use it anymore
  }, [fetchLeaderboardData, checkPremiumStatus]);
  
  // Memoized top 3 users
  const topThree = useMemo(() => filteredUsers.slice(0, 3), [filteredUsers]);
  
  // ترتيب المراكز الثلاثة الأولى - استخدام ترتيب مختلف للموبايل والديسكتوب
  const [isMobile, setIsMobile] = useState(window.innerWidth < 640);

  // إضافة event listener لتتبع تغير حجم الشاشة
  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 640);
    };
    
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  
  const orderedTopThree = useMemo(() => {
    if (topThree.length < 3) return topThree;
    
    // استخدام ترتيب طبيعي للموبايل (الأول، الثاني، الثالث)
    if (isMobile) {
      return [...topThree]; // ترتيب عادي للموبايل
    }
    
    // ترتيب خاص للشاشات الكبيرة: الأول في المنتصف، الثاني على اليمين، الثالث على اليسار
    return [
      topThree[2], // الثالث على اليسار
      topThree[0], // الأول في المنتصف
      topThree[1], // الثاني على اليمين
    ];
  }, [topThree, isMobile]);
  
  // Memoized remaining users - show all at once instead of paginating
  const restOfUsers = useMemo(() => {
    return filteredUsers.slice(3);
  }, [filteredUsers]);
  
  return (
    <div className="min-h-screen bg-[#262626] text-white py-8 px-4 sm:px-6 pb-24 md:pb-16">
      {/* Global styles */}
      <style>{`
        :root {
          --color-primary: #9D8DFF;
          --color-primary-light: #B3A6FF;
          --color-primary-dark: #8875FF;
        }
        
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
      
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div>
            <h1 className="text-3xl sm:text-4xl font-bold flex items-center">
              <Trophy className="text-[#9D8DFF] mr-3" size={32} />
              Leaderboard
            </h1>
            <p className="text-gray-400 mt-2">
              Top CRN holders ranked by balance
            </p>
          </div>
          
          <div className="flex items-center gap-3">
            {/* Refresh button removed */}
            
            {/* Search bar removed */}
          </div>
        </div>
      </div>

      {/* Loading state */}
      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="flex flex-col items-center">
            <div className="w-16 h-16 border-4 border-[#9D8DFF] border-t-transparent rounded-full animate-spin"></div>
            <p className="mt-6 text-[#9D8DFF] font-medium">Loading leaderboard...</p>
          </div>
        </div>
      ) : error ? (
        <div className="max-w-7xl mx-auto bg-[#3A3A3E]/30 border-l-4 border-red-500 p-4 rounded-lg mb-8">
          <p className="text-[#F4F4F7]">{error}</p>
          <button 
            onClick={() => fetchLeaderboardData(true)}
            className="mt-2 text-[#9D8DFF] hover:underline"
          >
            Try again
          </button>
        </div>
      ) : filteredUsers.length === 0 ? (
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
            <div className="bg-[#2A2A2E]/80 p-4 rounded-full mb-4">
              <Users size={32} className="text-gray-400" />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">No users found</h3>
            <p className="text-gray-400 mb-6 max-w-md">
              There are currently no users in the leaderboard.
            </p>
          </div>
        </div>
      ) : (
        <div className="max-w-7xl mx-auto">
          {/* Top 3 Podium */}
          {topThree.length > 0 && (
            <div className="mb-12">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 w-full">
                {orderedTopThree.map((user, index) => {
                  // تحديد الموضع الحقيقي بناءً على نوع الجهاز
                  let actualPosition;
                  
                  if (isMobile) {
                    // للموبايل: استخدام الترتيب العادي
                    actualPosition = user.rank - 1; // الترتيب الأصلي (صفر للأول، 1 للثاني، 2 للثالث)
                  } else {
                    // للديسكتوب: استخدام الترتيب الخاص (الأول في المنتصف، الثاني على اليمين، الثالث على اليسار)
                    if (index === 0) actualPosition = 2; // الثالث على اليسار
                    else if (index === 1) actualPosition = 0; // الأول في المنتصف
                    else actualPosition = 1; // الثاني على اليمين
                  }
                  
                  return (
                    <TopUserCard 
                      key={user.user_id} 
                      user={user} 
                      position={actualPosition} 
                    />
                  );
                })}
              </div>
            </div>
          )}
          
          {/* Rest of the Leaderboard */}
          {restOfUsers.length > 0 && (
            <div>
              <h3 className="text-lg font-bold mb-4 flex items-center text-[#F4F4F7]">
                <TrendingUp className="text-[#9D8DFF] mr-2" size={18} />
                Leaderboard Rankings
              </h3>
              
              <div className="space-y-3 w-full">
                {restOfUsers.map((user) => (
                  <UserRankItem key={user.user_id} user={user} />
                ))}
              </div>
              
              {/* End of list indicator - always show since we have all users */}
              {filteredUsers.length > 3 && (
                <div className="text-center mt-8 pb-8">
                  <p className="text-sm text-gray-400">End of leaderboard • {filteredUsers.length} users total</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
} 

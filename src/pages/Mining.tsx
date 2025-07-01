import React, { useState, useEffect, useRef, useCallback, lazy, Suspense, useMemo } from 'react';
import { 
  Cpu, 
  Coins,
  Activity,
  Play,
  ChevronUp,
  Award,
  BarChart3,
  TrendingUp,
  Sparkles,
  Zap,
  AlertCircle,
  Clock,
  Users,
  Timer,
  Check,
  RefreshCw,
  Star,
  Flame,
  Rocket,
  AlertTriangle,
  LightbulbIcon,
  Cog,
  Hammer,
  ShieldAlert,
  Globe,
  Smartphone, // Add this for device management UI
  Trash, // Add this for device management UI
  Shield, // Add this for device management UI
  Lock // Add this for lock icon
} from 'lucide-react';
import axios from 'axios';
// @ts-ignore - Import JavaScript module without type declarations
import { getAllFingerprints, addFingerprintHeaders } from '../lib/advanced-fingerprinting.js';

// Lazy load SlotCounter to improve initial load time
const SlotCounter = lazy(() => import('react-slot-counter'));

// Simple fallback for SlotCounter during loading
const NumberDisplay = ({ value }: { value: string | number }) => (
  <span>{value}</span>
);

// Create a debounce utility function
const debounce = <T extends (...args: any[]) => any>(fn: T, ms = 300) => {
  let timeoutId: ReturnType<typeof setTimeout>;
  return function(this: any, ...args: Parameters<T>) {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn.apply(this, args), ms);
  };
};

interface MiningStatus {
  total_mined: string;
  last_mined: string;
  today_mined: number;
  daily_mining_rate: number;
  hourly_mining_rate: number;
  can_mine: boolean;
  hours_remaining: number;
  wallet_balance: string;
  mining_session_hours: number;
  boosted_mining: boolean;
  maintenance_mode?: boolean;
  mining_conditions: string;
  security_violation?: boolean;
  mining_block?: boolean;
  ban?: boolean;
  security_details?: {
    penalty_type: string;
    risk_score?: number;
    is_vpn_detected?: boolean;
    violations?: string[];
    raw_violations?: any[];
    severity?: string;
    message?: string;
    user_id?: string;
  };
}

interface HoursRemaining {
  hours: number;
  minutes: number;
}

interface MiningRewardInfo {
  actual: number;
  base: number;
  conditions: string;
}

interface TwoFAStatus {
  is2FAEnabled: boolean;
  require2FASetup: boolean;
  isVerifying: boolean;
  code: string;
  error: string | null;
  showModal: boolean;
  isRateLimited?: boolean;
  remainingAttempts?: number;
  blockedUntil?: number;
  remainingTime?: number;
}

const MaintenanceScreen = () => {
  return (
    <div className="max-w-3xl mx-auto bg-gray-900 p-4 sm:p-10 rounded-3xl shadow-lg border border-gray-700 transition-all duration-500 animate-fadeIn">
      <div className="flex flex-col items-center text-center">
        <div className="relative w-28 h-28 sm:w-40 sm:h-40 mb-4 sm:mb-6">
          <Cog 
            size={70} 
            className="absolute text-blue-500 opacity-80 animate-spin-slow left-3 sm:left-4 top-4 sm:top-6" 
          />
          
          <Cog 
            size={40} 
            className="absolute text-indigo-500 opacity-90 animate-spin-reverse left-11 sm:left-16 top-1 sm:top-2" 
          />
          
          <Hammer 
            size={36} 
            className="absolute text-gray-500 right-0 bottom-0 animate-hammer" 
          />
        </div>
        
        <h2 className="text-xl sm:text-3xl font-bold text-gray-100 mb-2 sm:mb-3">Mining Maintenance</h2>
        
        <p className="text-sm sm:text-lg text-gray-300 mb-3 sm:mb-4">
          We're currently performing maintenance on our mining system.
        </p>
        
        <p className="text-xs sm:text-sm text-gray-400">
          Please check back shortly. We apologize for the inconvenience.
        </p>
      </div>
    </div>
  );
};

const MiningConditionsCard = ({ conditions }: { conditions: string }) => {
  const getConditionData = (condition: string) => {
    switch (condition) {
      case 'optimal':
        return {
          icon: <Zap size={20} className="text-yellow-300" />,
          color: 'bg-gradient-to-br from-[#23272A] to-[#1E2124] border-yellow-700',
          titleColor: 'text-yellow-300',
          textColor: 'text-gray-300',
          badge: {
            text: 'MINING',
            bg: 'bg-gradient-to-r from-yellow-600 to-yellow-400',
            ring: 'ring-1 ring-yellow-500/30'
          },
          title: 'Excellent Mining Conditions',
          description: 'Peak network performance detected. Mining yield potential is exceptionally high right now.',
          indicatorCount: 5,
          role: {
            text: '👑',
            color: 'text-yellow-300'
          }
        };
      case 'favorable':
        return {
          icon: <Sparkles size={20} className="text-blue-300" />,
          color: 'bg-gradient-to-br from-[#23272A] to-[#1E2124] border-blue-700',
          titleColor: 'text-blue-300',
          textColor: 'text-gray-300',
          badge: {
            text: 'MINING',
            bg: 'bg-gradient-to-r from-blue-600 to-blue-400',
            ring: 'ring-1 ring-blue-500/30'
          },
          title: 'Good Mining Conditions',
          description: 'Strong network performance detected. Mining yield potential is above average.',
          indicatorCount: 4,
          role: {
            text: '✨',
            color: 'text-blue-300'
          }
        };
      case 'normal':
        return {
          icon: <Activity size={20} className="text-purple-300" />,
          color: 'bg-gradient-to-br from-[#23272A] to-[#1E2124] border-purple-700',
          titleColor: 'text-purple-300',
          textColor: 'text-gray-300',
          badge: {
            text: 'MINING',
            bg: 'bg-gradient-to-r from-purple-600 to-purple-400',
            ring: 'ring-1 ring-purple-500/30'
          },
          title: 'Average Mining Conditions',
          description: 'Steady network performance detected. Mining yield potential is standard.',
          indicatorCount: 3,
          role: {
            text: '💎',
            color: 'text-purple-300'
          }
        };
      case 'challenging':
        return {
          icon: <AlertCircle size={20} className="text-amber-300" />,
          color: 'bg-gradient-to-br from-[#23272A] to-[#1E2124] border-amber-700',
          titleColor: 'text-amber-300',
          textColor: 'text-gray-300',
          badge: {
            text: 'MINING',
            bg: 'bg-gradient-to-r from-amber-600 to-amber-400',
            ring: 'ring-1 ring-amber-500/30'
          },
          title: 'Variable Mining Conditions',
          description: 'Unstable network performance detected. Mining yield potential may be reduced.',
          indicatorCount: 2,
          role: {
            text: '🔸',
            color: 'text-amber-300'
          }
        };
      case 'difficult':
        return {
          icon: <AlertTriangle size={20} className="text-red-300" />,
          color: 'bg-gradient-to-br from-[#23272A] to-[#1E2124] border-red-700',
          titleColor: 'text-red-300',
          textColor: 'text-gray-300',
          badge: {
            text: 'MINING',
            bg: 'bg-gradient-to-r from-red-600 to-red-400',
            ring: 'ring-1 ring-red-500/30'
          },
          title: 'Challenging Mining Conditions',
          description: 'Network congestion detected. Mining yield potential is currently limited.',
          indicatorCount: 1,
          role: {
            text: '⚠️',
            color: 'text-red-300'
          }
        };
      default:
        return {
          icon: <Activity size={20} className="text-gray-400" />,
          color: 'bg-gradient-to-br from-[#23272A] to-[#1E2124] border-gray-700',
          titleColor: 'text-gray-300',
          textColor: 'text-gray-400',
          badge: {
            text: 'MINING',
            bg: 'bg-gradient-to-r from-gray-600 to-gray-500',
            ring: 'ring-1 ring-gray-500/30'
          },
          title: 'Unknown Mining Conditions',
          description: 'Unable to determine current network conditions.',
          indicatorCount: 3,
          role: {
            text: '🔄',
            color: 'text-gray-400'
          }
        };
    }
  };

  const conditionData = getConditionData(conditions);

  return (
    <div className={`p-4 sm:p-6 rounded-2xl border shadow-lg hover:shadow-xl transition-all ${conditionData.color}`}>
      <div className="flex items-center justify-between mb-3 sm:mb-4">
        <div className="flex items-center gap-2 sm:gap-3">
          <div className="p-2 sm:p-3 rounded-xl bg-[#36393F] shadow-md border border-[#202225] relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-black/5 to-white/5 pointer-events-none"></div>
            {conditionData.icon}
          </div>
          <div>
            <h3 className={`font-bold text-sm sm:text-base ${conditionData.titleColor} flex items-center gap-2`}>
              Mining Conditions 
              <span className={`text-xs px-1.5 py-0.5 rounded ${conditionData.badge.bg} ${conditionData.badge.ring} text-white font-medium`}>
                MINING
              </span>
              <span className="ml-1">{conditionData.role.text}</span>
            </h3>
          </div>
        </div>
      </div>
      
      <div className="mb-2 sm:mb-3 bg-[#2F3136] p-3 rounded-lg border border-[#202225]">
        <h2 className={`text-base sm:text-xl font-bold ${conditionData.titleColor} flex items-center gap-2`}>
          {conditionData.title}
          <span className={`inline-flex ${conditionData.role.color} text-xs`}>
            {new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
          </span>
        </h2>
        <p className={`text-xs sm:text-sm ${conditionData.textColor} mt-1`}>{conditionData.description}</p>
      </div>
      
      <div className="flex items-center justify-between py-1 sm:py-2 bg-[#2F3136] rounded-lg p-2 border border-[#202225]">
        <div className="flex space-x-1">
          {[1, 2, 3, 4, 5].map((i) => (
            <div 
              key={`indicator-${i}`}
              className={`w-1.5 sm:w-2 h-4 sm:h-6 rounded-full 
                ${i <= conditionData.indicatorCount 
                ? i === 5 ? 'bg-gradient-to-r from-green-400 to-green-500 shadow-[0_0_5px_rgba(74,222,128,0.5)]' 
                : i === 4 ? 'bg-gradient-to-r from-blue-400 to-blue-500 shadow-[0_0_5px_rgba(59,130,246,0.5)]' 
                : i === 3 ? 'bg-gradient-to-r from-purple-400 to-purple-500 shadow-[0_0_5px_rgba(168,85,247,0.5)]' 
                : i === 2 ? 'bg-gradient-to-r from-amber-400 to-amber-500 shadow-[0_0_5px_rgba(251,191,36,0.5)]' 
                : 'bg-gradient-to-r from-red-400 to-red-500 shadow-[0_0_5px_rgba(239,68,68,0.5)]' 
                : 'bg-[#40444B]'}`}
            />
          ))}
        </div>
        <div className="text-xs sm:text-sm font-medium text-gray-400 flex items-center gap-1">
                        <span className="bg-black/20 px-1.5 py-0.5 rounded text-[10px]">
                Network Status
              </span>
        </div>
      </div>
    </div>
  );
};

const MiningBlockScreen = ({ message }: { message: string }) => {
  return (
    <div className="max-w-3xl mx-auto bg-gray-900 p-4 sm:p-10 rounded-3xl shadow-lg border border-orange-700 transition-all duration-500 animate-fadeIn">
      <div className="flex flex-col items-center text-center">
        <div className="relative w-28 h-28 sm:w-40 sm:h-40 mb-4 sm:mb-6">
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="bg-orange-900/40 rounded-full p-3 sm:p-5 animate-pulse">
              <AlertCircle size={60} className="text-orange-500" />
            </div>
          </div>
        </div>
        
        <h2 className="text-xl sm:text-3xl font-bold text-gray-100 mb-2 sm:mb-3">Mining Access Blocked</h2>
        
        <p className="text-sm sm:text-lg text-gray-300 mb-4 sm:mb-6">
          {message || "Your account has been temporarily blocked from mining due to security violations."}
        </p>
        
        <div className="bg-orange-950/50 border border-orange-800 rounded-xl p-3 sm:p-4 mb-3 sm:mb-4 max-w-xl">
          <h3 className="font-bold text-orange-200 mb-1 sm:mb-2 text-sm sm:text-base">Why am I seeing this?</h3>
          <p className="text-orange-200 text-xs sm:text-sm">
            Our system has detected a violation of our mining policy. Your mining privileges have been
            suspended, but you can still access other features of your account. This is not a permanent ban.
          </p>
        </div>
        
        <div className="bg-green-950/50 border border-green-800 rounded-xl p-3 sm:p-4 mb-3 sm:mb-4 max-w-xl">
          <h3 className="font-bold text-green-200 mb-1 sm:mb-2 text-sm sm:text-base">What can I still do?</h3>
          <p className="text-green-200 text-xs sm:text-sm">
            You can still use all other features of your wallet, including transfers, marketplace, and more. 
            Only your mining capability has been temporarily suspended.
          </p>
        </div>
        
        <p className="text-gray-400 text-xs sm:text-sm mt-3 sm:mt-4">
          If you believe this is an error, please contact support.
        </p>
      </div>
    </div>
  );
};

const PermanentBanScreen = ({ message }: { message: string }) => {
  return (
    <div className="max-w-3xl mx-auto bg-gray-900 p-4 sm:p-10 rounded-3xl shadow-lg border border-red-700 transition-all duration-500 animate-fadeIn">
      <div className="flex flex-col items-center text-center">
        <div className="relative w-28 h-28 sm:w-40 sm:h-40 mb-4 sm:mb-6">
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="bg-red-900/40 rounded-full p-3 sm:p-5 animate-pulse">
              <AlertTriangle size={60} className="text-red-500" />
            </div>
          </div>
        </div>
        
        <h2 className="text-xl sm:text-3xl font-bold text-gray-100 mb-2 sm:mb-3">Account Banned</h2>
        
        <p className="text-sm sm:text-lg text-gray-300 mb-4 sm:mb-6">
          {message || "Your account has been permanently banned due to security violations."}
        </p>
        
        <div className="bg-red-950/50 border border-red-800 rounded-xl p-3 sm:p-4 mb-3 sm:mb-4 max-w-xl">
          <h3 className="font-bold text-red-200 mb-1 sm:mb-2 text-sm sm:text-base">Why was my account banned?</h3>
          <p className="text-red-200 text-xs sm:text-sm">
            Our system has detected serious violations of our platform's terms of service.
            All account functionality has been restricted.
          </p>
        </div>
        
        <p className="text-gray-400 text-xs sm:text-sm mt-3 sm:mt-4">
          If you believe this is an error, please contact support for assistance.
        </p>
      </div>
    </div>
  );
};

const WarningScreen = ({ message }: { message: string }) => {
  return (
    <div className="max-w-3xl mx-auto bg-gray-900 p-4 sm:p-10 rounded-3xl shadow-lg border border-yellow-700 transition-all duration-500 animate-fadeIn">
      <div className="flex flex-col items-center text-center">
        <div className="relative w-28 h-28 sm:w-40 sm:h-40 mb-4 sm:mb-6">
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="bg-yellow-900/40 rounded-full p-3 sm:p-5 animate-pulse">
              <AlertTriangle size={60} className="text-yellow-500" />
            </div>
          </div>
        </div>
        
        <h2 className="text-xl sm:text-3xl font-bold text-gray-100 mb-2 sm:mb-3">⚠️ Warning: First Violation</h2>
        
        <p className="text-sm sm:text-lg text-gray-300 mb-4 sm:mb-6">
          {message || "We've detected a policy violation associated with your account."}
        </p>
        
        <div className="bg-yellow-950/50 border border-yellow-800 rounded-xl p-3 sm:p-4 mb-3 sm:mb-4 max-w-xl">
          <h3 className="font-bold text-yellow-200 mb-1 sm:mb-2 text-sm sm:text-base">Important Notice</h3>
          <p className="text-yellow-200 text-xs sm:text-sm">
            This is your first warning. Multiple accounts mining from the same device or IP address
            is not allowed. Further violations will result in a permanent ban from the platform.
          </p>
        </div>
        
        <p className="text-gray-300 text-xs sm:text-sm mt-3 sm:mt-4">
          Please ensure you're following our terms of service to avoid further action on your account.
        </p>
      </div>
    </div>
  );
};

const SecurityViolationScreen = ({ 
  message, 
  penaltyType,
  securityDetails 
}: { 
  message: string; 
  penaltyType?: string;
  securityDetails?: MiningStatus['security_details']
}) => {
  if (penaltyType === 'mining_block') {
    return <MiningBlockScreen message={message} />;
  } else if (penaltyType === 'permanent_ban' || penaltyType === 'permanent_ban_after_warning') {
    return <PermanentBanScreen message={message} />;
  } else if (penaltyType === 'warning') {
    return <WarningScreen message={message} />;
  }
  
  const getRiskColor = (score?: number) => {
    if (!score) return 'yellow';
    if (score >= 90) return 'red';
    if (score >= 70) return 'orange';
    if (score >= 50) return 'yellow';
    return 'green';
  };

  const getViolationDescription = (violation: string) => {
    switch (violation) {
      case 'device_violation':
        return 'Multiple accounts using the same device and IP';
      case 'browser_violation':
        return 'Multiple accounts using the same browser and IP';
      case 'ip_violation':
        return 'Too many accounts using the same IP address';
      case 'same_ip_browser_violation':
        return 'Multiple accounts using the same IP address and browser';
      case 'same_ip_device_violation':
        return 'Multiple accounts using the same IP address and device';
      case 'suspicious_device':
        return 'Suspicious device detected (emulator or VM)';
      case 'repeat_violation':
        return 'Repeat mining attempt after previous violations';
      case 'shared_resources':
        return 'Shared computing resources detected';
      case 'vpn_violation':
        return 'VPN/proxy usage with multiple accounts';
      case 'vpn_usage':
        return 'Mining through VPN/proxy detected';
      case 'persistent_vpn_evasion':
        return 'Persistent VPN usage after warnings';
      case 'too_many_devices':
        return 'Too many devices registered for this account';
      case 'too_many_networks':
        return 'Too many networks used with this account';
      default:
        return 'Security policy violation';
    }
  };

  const getViolationExplanation = (violation: string) => {
    switch (violation) {
      case 'device_violation':
        return 'Our system detected you are using a device that has been previously used by another account. Each account must use a unique device.';
      case 'ip_violation':
        return 'Our system detected too many accounts mining from the same network. We limit accounts per network to prevent mining farms.';
      case 'browser_violation':
        return 'Our system detected you are using a browser that has been previously used by another account on the same network. Each account must use a different browser when sharing a network.';
      case 'same_ip_browser_violation':
        return 'Our system detected multiple accounts using the same browser fingerprint from your IP address.';
      case 'same_ip_device_violation':
        return 'Our system detected another account previously mining from both this IP address and device fingerprint. Each account needs a unique device when mining from the same network.';
      case 'suspicious_device':
        return 'Our system detected you may be using an emulator, virtual machine, or sandbox environment, which is not allowed for mining.';
      case 'repeat_violation':
        return 'Our system detected previous security violations from your account in the past 48 hours.';
      case 'shared_resources':
        return 'Our system detected that you may be sharing computing resources with another user. Each user must mine from a unique device on the same IP.';
      case 'vpn_violation':
        return 'Our system detected you are using a VPN or proxy service while mining with multiple accounts. This is strictly prohibited.';
      case 'vpn_usage':
        return 'Our system detected you are mining through a VPN or proxy service. Mining through VPN is not allowed by our security policy.';
      case 'persistent_vpn_evasion':
        return 'Our system detected you have continued to attempt mining with VPN despite previous warnings. This indicates intentional evasion of our security measures.';
      case 'too_many_devices':
        return 'You\'ve reached the maximum number of allowed devices (3) for your account. Please remove an old device before adding a new one.';
      case 'too_many_networks':
        return 'You\'ve connected from too many different networks with this account. This may indicate account sharing or unusual activity.';
      case 'time_violation':
        return 'You\'ve attempted to mine again too soon after changing your network. Please wait at least 24 hours before mining from a completely different network.';
      case 'network_change_frequency':
        return 'Our system detected unusually frequent network changes. This pattern resembles VPN usage or account sharing.';
      case 'temporary_ip_change':
        return 'You\'ve recently changed networks. This is fine, but please note we track your regular networks to ensure fair mining practices.';
      default:
        return 'Our system detected unusual activity that violates our security policy.';
    }
  };
  
  const getPenaltyExplanation = (penaltyType?: string) => {
    switch (penaltyType) {
      case 'permanent_ban':
        return 'Your account has been permanently banned from using our platform due to severe security violations.';
      case 'mining_block':
        return 'Your account has been temporarily blocked from mining, but you can still use other platform features. This is not a permanent ban.';
      case 'warning':
        return 'This is a warning. Further violations may result in mining restrictions or account suspension.';
      default:
        return 'Your account has been restricted due to security violations.';
    }
  };

  const getViolationSolution = (violation: string) => {
    switch (violation) {
      case 'device_violation':
        return 'You cannot use multiple accounts on the same device, even with different IP addresses. Each account must use a unique physical device.';
      case 'vpn_usage':
        return 'If you are not the original owner of this device, you must disconnect from VPN/proxy before mining. Only the first account that registered this device can use VPN.';
      case 'browser_violation':
        return 'If you\'re sharing a network with family or friends, make sure each person uses a different browser on their own device. You cannot use multiple accounts on the same browser with the same IP.';
      case 'ip_violation':
        return 'If you\'re on a shared network (like a family home), make sure no more than 10 accounts are mining from this network, and each account uses a different device.';
      case 'same_ip_device_violation':
        return 'Each account needs to use a unique device when mining from the same network. You cannot use multiple accounts on the same device from the same IP.';
      case 'too_many_devices':
        return 'Remove an old device from your account to add this new one. You can use a maximum of 5 devices per account.';
      case 'too_many_networks':
        return 'Try to use consistent networks with your account. You can use up to 20 different networks with your account.';
      case 'vpn_solution':
        return 'Disconnect from VPN before mining. Mining through VPN or proxy is not permitted.';
      case 'time_violation':
        return 'Continue using your account normally. You\'ll be able to mine after the waiting period or if you connect from one of your previously used networks.';
      case 'network_change_frequency':
        return 'Try to mine from consistent networks rather than frequently changing your connection. Our system recognizes and trusts networks you regularly use.';
      case 'browser_solution':
        return 'Use a different browser or clear your browser fingerprint data if you believe this is an error.';
      case 'suspicious_device':
        return 'Use a physical device rather than virtual machines or emulators for mining.';
      case 'temporary_ip_change':
        return 'No action needed. You can continue mining normally. Our system now recognizes all of your regular networks.';
      case 'same_ip_browser_violation':
        return 'Make sure only one account mines from each unique device/browser combination. If sharing a network, each person should use their own device and browser.';
      default:
        return 'Please contact support if you believe this is an error.';
    }
  };
  
  const getViolationDetail = (violation: any) => {
    if (!violation) return null;
    
    let detail = '';
    
    if (violation.existing_users && violation.existing_users.length > 0) {
      detail += `Conflicting user ID: ${violation.existing_users[0]}`;
    }
    
    if (violation.first_user && !detail.includes(violation.first_user)) {
      detail += detail ? `, ` : '';
      detail += `First registered user: ${violation.first_user}`;
    }
    
    if (violation.vpn_confidence) {
      detail += detail ? `, ` : '';
      detail += `VPN detection confidence: ${violation.vpn_confidence}%`;
    }
    
    if (violation.ip_type) {
      detail += detail ? `, ` : '';
      detail += `IP type: ${violation.ip_type}`;
    }
    
    return detail;
  };
  
  const isLocalhost = securityDetails?.violations?.some(v => 
    (v === 'ip_violation' || v === 'same_ip_browser_violation') && 
    securityDetails?.message?.includes('localhost')
  );

  const getContextMessage = () => {
    if (isLocalhost) {
      return "You're connecting from localhost (127.0.0.1), which is typically used in development environments. Our system detected that another account has used this same connection. If you're a developer, this may be a false positive.";
    }
    
    if (securityDetails?.violations?.includes('vpn_violation') || securityDetails?.violations?.includes('vpn_usage')) {
      return "Our system has detected that you're attempting to mine while using a VPN or proxy service. Mining through VPN is prohibited by our security policy as it can be used to circumvent our security rules.";
    }
    
    if (securityDetails?.violations?.includes('persistent_vpn_evasion')) {
      return "Our system has detected that you're repeatedly attempting to mine using different VPN connections. This pattern of behavior strongly indicates intentional evasion of our security measures and is a severe violation of our terms of service.";
    }
    
    if (securityDetails?.is_vpn_detected) {
      return "Our system has detected that you're using a VPN or proxy service while attempting to mine. Mining through VPN is not allowed per our security policy.";
    }
    
    if (securityDetails?.violations?.includes('too_many_devices')) {
      return "Our system allows a maximum of 3 devices per account. You've reached this limit. To use this new device, please remove an old device from your account first.";
    }
    
    if (securityDetails?.violations?.includes('too_many_networks')) {
      return "You've connected from too many different networks with this account. We limit the number of networks to prevent account sharing.";
    }
    
    if (securityDetails?.violations?.includes('network_change_frequency')) {
      return "Our system has detected unusually frequent changes in your connection networks. Changing networks too often may trigger our security system as it resembles VPN usage patterns.";
    }
    
    if (securityDetails?.violations?.includes('time_violation')) {
      return "You've recently changed to a completely different network. Our system requires a waiting period between using drastically different networks to prevent fraud and account sharing. You can mine immediately from known networks associated with your device.";
    }
    
    if (securityDetails?.violations?.includes('same_ip_device_violation')) {
      return "Our system has detected that you're attempting to mine from multiple accounts using the same device and IP address. On a shared network, each account must use a unique device for mining.";
    }
    
    if (securityDetails?.violations?.includes('same_ip_browser_violation')) {
      return "Our system has detected that you're attempting to mine from multiple accounts using the same browser and IP address. On a shared network, each account must use a unique browser and device for mining.";
    }
    
    if (securityDetails?.violations?.includes('device_violation')) {
      return "We've improved our security system to only block accounts that use the same device AND same IP address. If you're receiving this message incorrectly, please contact support with your device details.";
    }
    
    if (securityDetails?.violations?.includes('browser_violation')) {
      return "Our system has detected that you're attempting to mine from multiple accounts using the same browser with the same IP. When sharing a network, each account must use a different browser on a unique device.";
    }
    
    if (securityDetails?.violations?.includes('ip_violation')) {
      return "Our system has detected that you're attempting to mine from a network with too many accounts. We allow a maximum of 10 accounts per network to prevent mining farms, but each account must use a unique device.";
    }
    
    if (securityDetails?.violations?.includes('suspicious_device')) {
      return "Our system has detected that you're attempting to mine using a virtual machine, emulator, or other suspicious device configuration. This violates our mining policy.";
    }
    
    if (securityDetails?.violations?.includes('repeat_violation')) {
      return "Our system has detected repeated mining attempts after previous security violations. This pattern of behavior violates our mining policy.";
    }
    
    if (securityDetails?.violations?.includes('temporary_ip_change')) {
      return "We've detected you're mining from a different network than usual. This is completely fine - our system now automatically recognizes your trusted networks and allows mining from them.";
    }
    
    return "Our system has detected that you're attempting to mine in a way that violates our security policy. You can share a network with others, but each account must use a unique device for mining on that network.";
  };
  
  return (
    <div className="max-w-3xl mx-auto bg-gray-900 p-4 sm:p-10 rounded-3xl shadow-lg border border-red-700 transition-all duration-500 animate-fadeIn">
      <div className="flex flex-col items-center text-center">
        <div className="relative w-28 h-28 sm:w-40 sm:h-40 mb-4 sm:mb-6">
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="bg-red-900/40 rounded-full p-3 sm:p-5 animate-pulse">
              <ShieldAlert size={60} className="text-red-500" />
            </div>
          </div>
        </div>
        
        <h2 className="text-xl sm:text-3xl font-bold text-gray-100 mb-2 sm:mb-3">Security Violation Detected</h2>
        
        <p className="text-sm sm:text-lg text-gray-300 mb-4 sm:mb-6">
          {message || "Multiple accounts detected from the same device AND IP address."}
        </p>
        
        {securityDetails && (
          <div className="bg-red-950/50 border border-red-800 rounded-xl p-3 sm:p-4 mb-3 sm:mb-4 max-w-xl w-full">
            <h3 className="font-bold text-red-200 mb-2 sm:mb-3 text-sm sm:text-base">Security Details</h3>
            
            {securityDetails.risk_score && (
              <div className="mb-2 flex justify-between">
                <span className="text-xs sm:text-sm text-gray-200">Risk Score:</span>
                <span className={`font-bold text-xs sm:text-sm text-${getRiskColor(securityDetails.risk_score)}-400`}>
                  {securityDetails.risk_score.toFixed(0)}/100
                </span>
              </div>
            )}
            
            {securityDetails.violations && securityDetails.violations.length > 0 && (
              <div className="mb-3">
                <p className="text-left text-gray-200 mb-1">Detected Violations:</p>
                <ul className="list-disc list-inside text-left text-gray-200">
                  {securityDetails.violations.map((violation, index) => (
                                          <li key={index} className="mb-2">
                        <span className="font-medium">{getViolationDescription(violation)}</span>
                        <p className="text-sm ml-5 mt-1 text-gray-300">{getViolationExplanation(violation)}</p>
                        
                        {securityDetails.raw_violations && securityDetails.raw_violations[index] && (
                          <div className="text-xs ml-5 mt-1 text-gray-300 bg-gray-800 p-2 rounded">
                            {getViolationDetail(securityDetails.raw_violations[index])}
                          </div>
                        )}
                        
                        <p className="text-sm ml-5 mt-1 text-green-300 bg-green-950/30 p-2 rounded border border-green-900/50">
                          <span className="font-medium">Solution: </span>
                          {getViolationSolution(violation)}
                        </p>
                      </li>
                  ))}
                </ul>
              </div>
            )}
            
            {securityDetails.is_vpn_detected && (
              <div className="mb-4 bg-red-950/40 p-4 rounded-xl text-left border border-red-800">
                <div className="flex items-center gap-2 mb-2">
                  <Globe size={20} className="text-red-400" />
                  <p className="text-red-300 font-bold">VPN or Proxy Detected</p>
                </div>
                <p className="text-red-200 text-sm mb-2">
                  {isLocalhost ? 
                    "Note: You're connecting from localhost (127.0.0.1). This is typically used in development environments and shouldn't trigger VPN detection." :
                    "Our system has detected that you're using a VPN or proxy service. Mining through VPN is strictly prohibited by our security policy."}
                </p>
              </div>
            )}
            
            {securityDetails.penalty_type && (
              <div className="mb-3">
                <p className="text-left text-gray-200 mb-1">Penalty Type: {penaltyType === 'mining_block' ? 'Mining Block' : penaltyType}</p>
                <p className="text-gray-300 text-sm text-left">
                  Your account has been temporarily blocked from mining, but you can still use other platform features. This is not a permanent ban.
                </p>
              </div>
            )}
          </div>
        )}
        
                            <div className="bg-gray-800/50 p-4 rounded-xl max-w-xl w-full mb-4">
                      <h3 className="text-gray-100 font-medium mb-2 text-center">Why am I seeing this?</h3>
                      <p className="text-gray-300 text-sm text-center">
                        {getContextMessage()}
                      </p>
                    </div>

                    <div className="bg-blue-900/40 border border-blue-800 rounded-xl p-4 max-w-xl w-full mb-4">
                      <h3 className="text-blue-200 font-medium mb-2 flex items-center">
                        <LightbulbIcon size={16} className="mr-2 text-blue-400" /> 
                        Updated Security Policy
                      </h3>
                      <p className="text-blue-200 text-sm">
                        Our mining security now focuses on IP address + device combinations. Multiple accounts can mine from the same network (like a family home) as long as each account uses a unique device. Maximum 10 accounts per network are allowed.
                      </p>
                    </div>

                    <div className="bg-amber-900/40 border border-amber-800 rounded-xl p-4 max-w-xl w-full mb-4">
                      <h3 className="text-amber-200 font-medium mb-2 flex items-center">
                        <AlertCircle size={16} className="mr-2 text-amber-400" /> 
                        Important Fix (June 9, 2025)
                      </h3>
                      <p className="text-amber-200 text-sm">
                        We've fixed an issue where users with different IP addresses were incorrectly blocked due to similar device fingerprints. If you've been affected, please contact support to have your account reviewed.
                      </p>
                    </div>
        
        <p className="text-gray-400 text-sm mt-4">
          If you believe this is an error, please contact support with your user ID: {securityDetails?.user_id || "Unknown"}
        </p>
      </div>
    </div>
  );
};

// Add DeviceManagement component with the necessary imports and fixes
const DeviceManagement = () => {
  const [devices, setDevices] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [limitReached, setLimitReached] = useState(false);
  const [deviceCount, setDeviceCount] = useState(0);
  const [maxDevices, setMaxDevices] = useState(3);
  const [networks, setNetworks] = useState<string[]>([]);
  const [showNetworksInfo, setShowNetworksInfo] = useState(false);

  const fetchDevices = async () => {
    setLoading(true);
    try {
      // Use advanced fingerprinting
      const options = await addFingerprintHeaders({
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      });
      
      // Convert options to axios format
      const response = await axios.get('/api/mining/fingerprint/devices', {
        headers: options.headers
      });
      
      if (response.status === 200) {
        setDevices(response.data.devices || []);
        setDeviceCount(response.data.device_count || 0);
        setLimitReached(response.data.device_limit_reached || false);
        setMaxDevices(response.data.max_devices || 3);
        
        // Set networks if available
        if (response.data.user_networks && Array.isArray(response.data.user_networks)) {
          setNetworks(response.data.user_networks);
        }
      } else {
        setError(response.data.message || 'Failed to fetch devices');
      }
    } catch (err: any) {
      setError('Error connecting to server');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const removeDevice = async (fingerprint: string) => {
    if (!confirm('Are you sure you want to remove this device?')) return;
    
    try {
      // Use advanced fingerprinting
      const options = await addFingerprintHeaders({
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' }
      });
      
      // Convert options to axios format
      const response = await axios.delete(`/api/mining/fingerprint/devices/${fingerprint}`, {
        headers: options.headers
      });
      
      if (response.status === 200) {
        // Refresh device list
        fetchDevices();
      } else {
        setError(response.data.message || 'Failed to remove device');
      }
    } catch (err: any) {
      setError('Error connecting to server');
      console.error(err);
    }
  };

  // Toggle networks info section
  const toggleNetworksInfo = () => {
    setShowNetworksInfo(!showNetworksInfo);
  };

  // Fetch devices on component mount
  useEffect(() => {
    fetchDevices();
  }, []);

  return (
    <div className="mt-8 rounded-2xl bg-gray-900 bg-opacity-50 border border-gray-800 p-5 backdrop-blur-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center">
          <Shield className="text-purple-400 mr-2" size={20} />
          <h2 className="text-lg font-semibold text-white">Device Management</h2>
        </div>
        <button 
          onClick={fetchDevices}
          className="text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 px-2 py-1 rounded flex items-center"
        >
          <RefreshCw size={12} className="mr-1" /> Refresh
        </button>
      </div>
      
      {loading ? (
        <div className="py-8 flex justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-purple-500"></div>
        </div>
      ) : error ? (
        <div className="bg-red-900 bg-opacity-20 border border-red-700 text-red-300 p-3 rounded-lg">
          {error}
        </div>
      ) : (
        <>
          <div className="mb-4">
            <div className="flex justify-between items-center mb-2">
              <span className="text-gray-400 text-sm">
                Registered Devices: <span className="text-white">{deviceCount} / {maxDevices}</span>
              </span>
            </div>
            
            <div className="w-full bg-gray-800 rounded-full h-2.5">
              <div 
                className={`h-2.5 rounded-full ${limitReached ? 'bg-red-500' : 'bg-purple-500'}`} 
                style={{ width: `${(deviceCount / maxDevices) * 100}%` }}
              ></div>
            </div>
          </div>
          
          {devices.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <Smartphone className="mx-auto mb-3 text-gray-600" size={40} />
              <p>No devices registered yet.</p>
              <p className="text-sm mt-1">Start mining to register this device.</p>
            </div>
          ) : (
            <div className="overflow-hidden rounded-lg border border-gray-800">
              {devices.map((device, index) => (
                <div 
                  key={device.fingerprint_hash} 
                  className={`flex items-center justify-between p-3 ${
                    index < devices.length - 1 ? 'border-b border-gray-800' : ''
                  } ${device.is_current_device ? 'bg-purple-900 bg-opacity-20' : 'hover:bg-gray-800'}`}
                >
                  <div className="flex items-center">
                    <Smartphone className="text-gray-400 mr-3" size={16} />
                    <div>
                      <div className="flex items-center">
                        <span className="text-white text-sm font-medium">
                          {device.display_id}
                        </span>
                        {device.is_current_device && (
                          <span className="ml-2 px-1.5 py-0.5 text-xs rounded bg-purple-900 text-purple-300">
                            Current
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-gray-500 mt-0.5">
                        {device.device_type} • Last used: {new Date(device.last_seen).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => removeDevice(device.fingerprint_hash)}
                    disabled={device.is_current_device}
                    className={`text-xs px-2 py-1 rounded flex items-center ${
                      device.is_current_device
                        ? 'bg-gray-800 text-gray-600 cursor-not-allowed'
                        : 'bg-red-900 bg-opacity-30 text-red-400 hover:bg-red-800'
                    }`}
                  >
                    <Trash size={12} className="mr-1" /> Remove
                  </button>
                </div>
              ))}
            </div>
          )}
          
          {/* Networks Information Section */}
          <div className="mt-6 border-t border-gray-800 pt-4">
            <button
              onClick={toggleNetworksInfo}
              className="w-full flex justify-between items-center text-sm text-gray-300 hover:text-white transition-colors duration-200"
            >
              <div className="flex items-center">
                <Globe size={16} className="mr-2 text-indigo-400" />
                <span className="font-medium">Trusted Networks</span> 
                <span className="ml-2 px-1.5 py-0.5 text-xs bg-indigo-900 text-indigo-300 rounded-full">
                  NEW
                </span>
              </div>
              <ChevronUp size={16} className={`transition-transform duration-200 ${showNetworksInfo ? '' : 'transform rotate-180'}`} />
            </button>
            
            {showNetworksInfo && (
              <div className="mt-3 bg-gray-800 rounded-lg p-4 text-sm">
                <p className="text-gray-300 mb-3">
                  Our improved security system now automatically recognizes and tracks your trusted networks.
                  You can safely mine from any of your regular networks without triggering security alerts.
                </p>
                
                {networks.length > 0 ? (
                  <>
                    <h4 className="text-white font-medium mb-2">Your Trusted Networks:</h4>
                    <div className="grid grid-cols-1 gap-2">
                      {networks.map((network, index) => (
                        <div key={index} className="bg-gray-700 rounded p-2 flex items-center">
                          <div className="w-2 h-2 rounded-full bg-green-500 mr-2"></div>
                          <span className="text-gray-300">{network.substring(0, 3)}***{network.substring(network.length-3)}</span>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <p className="text-gray-400 italic">
                    No trusted networks found yet. Networks will be added automatically as you mine.
                  </p>
                )}
                
                <div className="mt-4 bg-indigo-900 bg-opacity-30 border border-indigo-800 p-3 rounded-lg">
                  <h4 className="text-indigo-300 font-medium flex items-center mb-1">
                    <LightbulbIcon size={14} className="mr-1" />
                    About Network Security
                  </h4>
                  <p className="text-gray-300 text-xs">
                    Our updated mining security system now allows you to mine from different locations with the same account safely. 
                    The system learns your trusted networks and allows easy network switching while still preventing multiple accounts from using the same device.
                  </p>
                </div>
              </div>
            )}
          </div>
          
          <div className="mt-3 text-xs text-gray-500">
            <p>Each account can have up to {maxDevices} registered devices for mining.</p>
          </div>
        </>
      )}
    </div>
  );
};

  // Add a banner component to explain the new security policy
const SecurityPolicyBanner = () => {
  // Always return null to hide the banner
  return null;
};

  // Add TwoFAVerificationModal component
const TwoFAVerificationModal = ({ 
  isOpen, 
  onClose, 
  onVerify, 
  error, 
  isVerifying,
  require2FASetup
}: { 
  isOpen: boolean; 
  onClose: () => void; 
  onVerify: (code: string) => void; 
  error: string | null;
  isVerifying: boolean;
  require2FASetup: boolean;
}) => {
  const [code, setCode] = useState('');
  const [timeRemaining, setTimeRemaining] = useState<number | null>(null);
  
  // Extract rate limit info from error message if it exists
  const rateLimitInfo = useMemo(() => {
    if (!error) return null;
    
    // Check if error contains rate limit information
    const remainingAttemptsMatch = error.match(/(\d+) attempts remaining/);
    const timeRemainingMatch = error.match(/try again in (\d+) seconds/);
    
    return {
      hasRemainingAttempts: !!remainingAttemptsMatch,
      remainingAttempts: remainingAttemptsMatch ? Number(remainingAttemptsMatch[1]) : null,
      isRateLimited: !!timeRemainingMatch,
      timeRemaining: timeRemainingMatch ? Number(timeRemainingMatch[1]) : null
    };
  }, [error]);
  
  // Countdown timer for rate-limited users
  useEffect(() => {
    if (!rateLimitInfo?.isRateLimited || !rateLimitInfo.timeRemaining) return;
    
    setTimeRemaining(rateLimitInfo.timeRemaining);
    
    const interval = setInterval(() => {
      setTimeRemaining(prev => {
        if (!prev || prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    
    return () => clearInterval(interval);
  }, [rateLimitInfo?.isRateLimited, rateLimitInfo?.timeRemaining]);
  
  // Function to handle input change
  const handleCodeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    // Only allow digits
    const value = e.target.value.replace(/[^0-9]/g, '');
    // Limit to 6 characters
    setCode(value.substring(0, 6));
  };
  
  // Function to handle form submission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (code.length === 6) {
      onVerify(code);
    }
  };
  
  // Redirect to security page
  const redirectToSecurity = () => {
    window.location.href = '/wallet/security';
  };
  
  // Format time remaining for display
  const formatTimeRemaining = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };
  
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-60 z-50 flex items-center justify-center p-4">
      <div className="bg-[#262626] rounded-2xl shadow-2xl border border-[#3A3A3E] p-6 max-w-md w-full animate-fadeIn">
        <div className="text-center mb-6">
          {require2FASetup ? (
            <>
              <div className="w-16 h-16 bg-[#8875FF] rounded-full flex items-center justify-center mx-auto mb-4">
                <Shield className="text-white" size={24} />
              </div>
              <h2 className="text-xl font-bold text-white mb-2">Two-Factor Authentication Required</h2>
              <p className="text-gray-300 text-sm">
                To enhance your account security, you must enable two-factor authentication before mining.
              </p>
            </>
          ) : (
            <>
              <div className="w-16 h-16 bg-[#8875FF] rounded-full flex items-center justify-center mx-auto mb-4">
                <Lock className="text-white" size={24} />
              </div>
              <h2 className="text-xl font-bold text-white mb-2">Two-Factor Authentication</h2>
              <p className="text-gray-300 text-sm">
                Please enter the 6-digit code from your authenticator app to verify your identity.
              </p>
            </>
          )}
        </div>
        
        {require2FASetup ? (
          // Show setup button
          <div className="mt-6">
            <button
              onClick={redirectToSecurity}
              className="w-full bg-[#8875FF] hover:bg-[#7865FF] text-white py-3 rounded-xl font-medium transition-colors duration-200 flex items-center justify-center gap-2"
            >
              <Shield size={18} />
              <span>Set Up Two-Factor Authentication</span>
            </button>
            
            <button
              onClick={onClose}
              className="w-full mt-3 bg-[#333333] hover:bg-[#404040] text-gray-200 py-3 rounded-xl font-medium transition-colors duration-200"
            >
              Cancel
            </button>
          </div>
        ) : (
          // Show code input form
          <form onSubmit={handleSubmit}>
            {error && (
              <div className="mb-4 p-3 bg-red-900/20 border border-red-800/50 rounded-xl text-red-300 text-sm">
                {error}
                {rateLimitInfo?.isRateLimited && timeRemaining && timeRemaining > 0 && (
                  <div className="mt-2 text-amber-300 font-medium">
                    Try again in: {formatTimeRemaining(timeRemaining)}
                  </div>
                )}
              </div>
            )}
            
            <div className="mb-4">
              <label htmlFor="code" className="block text-gray-300 text-sm font-medium mb-2">
                Authentication Code
              </label>
              <input
                type="text"
                id="code"
                value={code}
                onChange={handleCodeChange}
                placeholder="123456"
                className="w-full bg-[#333333] border border-[#4A4A4E] rounded-xl py-3 px-4 text-white text-center text-xl tracking-widest focus:outline-none focus:ring-2 focus:ring-[#8875FF] focus:border-transparent"
                autoComplete="one-time-code"
                inputMode="numeric"
                disabled={!!rateLimitInfo?.isRateLimited && !!timeRemaining && timeRemaining > 0}
              />
            </div>
            
            {rateLimitInfo?.hasRemainingAttempts && rateLimitInfo.remainingAttempts !== null && (
              <div className="text-center mb-4">
                <span className="text-amber-400 text-sm">
                  {rateLimitInfo.remainingAttempts} attempts remaining
                </span>
              </div>
            )}
            
            <div className="mt-6 flex flex-col gap-3">
              <button
                type="submit"
                disabled={(code.length !== 6 || isVerifying) || (!!rateLimitInfo?.isRateLimited && !!timeRemaining && timeRemaining > 0)}
                className={`w-full py-3 rounded-xl font-medium transition-colors duration-200 flex items-center justify-center gap-2 
                  ${code.length === 6 && !isVerifying && !(!!rateLimitInfo?.isRateLimited && !!timeRemaining && timeRemaining > 0)
                    ? 'bg-[#8875FF] hover:bg-[#7865FF] text-white' 
                    : 'bg-[#3A3A3E] text-gray-500 cursor-not-allowed'}`}
              >
                {isVerifying ? (
                  <>
                    <RefreshCw size={18} className="animate-spin" />
                    <span>Verifying...</span>
                  </>
                ) : (!!rateLimitInfo?.isRateLimited && !!timeRemaining && timeRemaining > 0) ? (
                  <>
                    <Timer size={18} />
                    <span>Locked</span>
                  </>
                ) : (
                  <>
                    <Check size={18} />
                    <span>Verify</span>
                  </>
                )}
              </button>
              
              <button
                type="button"
                onClick={onClose}
                className="w-full bg-[#333333] hover:bg-[#404040] text-gray-200 py-3 rounded-xl font-medium transition-colors duration-200"
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

const Mining = () => {
  // CSRF protection warning
  React.useEffect(() => {
    console.warn("⚠️ WARNING: CSRF protection is temporarily disabled for debugging purposes. Re-enable it after fixing the issues!");
  }, []);

  const [isMining, setIsMining] = useState(false);
  const [miningTime, setMiningTime] = useState(0);
  const [miningAnimation, setMiningAnimation] = useState(false);
  const [statAnimations, setStatAnimations] = useState(false);
  const [particles, setParticles] = useState<Array<{ id: number; x: number; y: number; size: number; speed: number }>>([]);
  const [startTime, setStartTime] = useState<Date | null>(null);
  const [miningStatus, setMiningStatus] = useState<MiningStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [miningComplete, setMiningComplete] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSecurityChecking, setIsSecurityChecking] = useState(false);
  const [progressPercent, setProgressPercent] = useState<number>(0);
  const [hoursRemaining, setHoursRemaining] = useState<HoursRemaining>({ hours: 0, minutes: 0 });
  const [showCooldownAnimation, setShowCooldownAnimation] = useState(false);
  const [miningCompleted, setMiningCompleted] = useState(false);
  const [showSuccessScreen, setShowSuccessScreen] = useState(false);
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const [securityViolation, setSecurityViolation] = useState<string | null>(null);
  const [penaltyType, setPenaltyType] = useState<string | null>(null);
  const [miningRewardInfo, setMiningRewardInfo] = useState<MiningRewardInfo>({
    actual: 0,
    base: 0,
    conditions: 'normal'
  });
  // Add securityDetails state variable
  const [securityDetails, setSecurityDetails] = useState<MiningStatus['security_details']>(undefined);
  // Add mining_block state
  const [miningBlock, setMiningBlock] = useState<boolean>(false);
  // Add new state variable to store mining response
  const [pendingMiningResponse, setPendingMiningResponse] = useState<any>(null);
  // Add CSRF token state
  const [csrfToken, setCsrfToken] = useState<string>('');
  
  // Add 2FA verification state
  const [twoFA, setTwoFA] = useState<TwoFAStatus>({
    is2FAEnabled: false,
    require2FASetup: false,
    isVerifying: false,
    code: '',
    error: null,
    showModal: false
  });
  
  // Add a state to store security check response while waiting for 2FA
  const [pendingSecurityCheck, setPendingSecurityCheck] = useState<any>(null);

  // Function to fetch CSRF token
  const fetchCsrfToken = useCallback(async () => {
    try {
      const response = await fetch("/api/csrf-token", {
        method: "GET",
        credentials: "include",
        headers: {
          "Accept": "application/json",
        }
      });

      if (response.ok) {
        const data = await response.json();
        console.log("CSRF token fetched successfully");
        setCsrfToken(data.csrf_token);
        return data.csrf_token;
      } else {
        console.error("Failed to fetch CSRF token:", response.status);
        setError("Failed to establish a secure connection. Please refresh the page.");
        return null;
      }
    } catch (error) {
      console.error("Error fetching CSRF token:", error);
      setError("Failed to establish a secure connection. Please refresh the page.");
      return null;
    }
  }, []);

  // Fetch CSRF token on component mount
  useEffect(() => {
    fetchCsrfToken();
  }, [fetchCsrfToken]);

  // Create optimized fetch function that's memoized
  const fetchMiningData = useCallback(async () => {
    try {
      if (isInitialLoad) {
        setIsLoading(true);
      }
      setError(null);
      
      // Get CSRF token if not available
      let token = csrfToken;
      if (!token) {
        token = await fetchCsrfToken();
      }
      
      // Fetch only status data
      const statusResponse = await axios.get('/api/mining/status', {
        headers: {
          "X-CSRF-Token": token || ''
        }
      });
      
      // Debug logging for mining data
      console.log("Mining data received:", {
        total_mined: statusResponse.data.total_mined,
        formatted: typeof statusResponse.data.total_mined,
      });
      
      // IMPORTANTE: No formatear ni modificar el valor total_mined
      // ya que debe usarse exactamente como viene de la API
      // Esta es la corrección principal para el bug
      
      // Asignar los datos directamente al estado
      setMiningStatus(statusResponse.data);
      
      // Check for mining_block flag
      if (statusResponse.data.mining_block) {
        setMiningBlock(true);
        // Reset any cooldown timer for blocked users
        setHoursRemaining({ hours: 0, minutes: 0 });
      } else {
        setMiningBlock(false);
        // Only set hours remaining if the user is not blocked
        if (statusResponse.data.hours_remaining) {
          setHoursRemaining({
            hours: statusResponse.data.hours_remaining,
            minutes: 0
          });
        }
      }
      
      // Check for security violations from the status response
      if (statusResponse.data.security_violation && !statusResponse.data.mining_block) {
        // Only set security violation if it's not just a mining block
        // This allows mining_block users to see the stats with the locked start button
        // instead of a full security violation screen
        let violationMessage = "Your account has security restrictions.";
        let penaltyTypeValue = null;
        
        // Set appropriate message and penalty type based on flags
        if (statusResponse.data.ban) {
          violationMessage = "Your account has been banned due to security violations.";
          penaltyTypeValue = "permanent_ban";
          setSecurityViolation(violationMessage);
          setPenaltyType(penaltyTypeValue || null);
        }
        
        // Set security details if available
        if (statusResponse.data.security_details) {
          setSecurityDetails(statusResponse.data.security_details);
        }
      } else if (!statusResponse.data.mining_block) {
        // Clear security violation if mining is not blocked
        setSecurityViolation(null);
        setPenaltyType(null);
        setSecurityDetails(undefined);
      }
    } catch (err) {
      console.error('Error fetching mining data:', err);
      setError('Failed to load mining data. Please try again later.');
    } finally {
      setIsLoading(false);
      setIsInitialLoad(false);
    }
  }, [isInitialLoad, csrfToken, fetchCsrfToken]);

  // Create a debounced refresh function
  const debouncedRefresh = useCallback(
    debounce(() => {
      fetchMiningData();
    }, 500),
    [fetchMiningData]
  );

  // Initial data fetch
  useEffect(() => {
    fetchMiningData();
    
    // Check rate limit status when page loads
    const checkRateLimit = async () => {
      try {
        // Get CSRF token if not available
        let token = csrfToken;
        if (!token) {
          token = await fetchCsrfToken();
        }
        
        const response = await axios.post('/api/mining/verify-2fa', 
          { 
            code: '000000', // Intentionally invalid code to check rate limit status
            auto_check: true  // Tell backend this is just an automatic check on page load
          }, 
          {
            headers: {
              "X-CSRF-Token": token || '',
              "Content-Type": "application/json"
            }
          }
        );
      } catch (err: any) {
        // If we get a 429 response, user is rate limited
        if (err.response?.status === 429) {
          const data = err.response.data;
          
          // Update the rate limit status without showing error messages
          setTwoFA(prev => ({
            ...prev,
            isRateLimited: true,
            blockedUntil: data.blocked_until,
            remainingTime: data.remaining_time
          }));
        }
      }
    };
    
    // Only check rate limit if we have a CSRF token
    if (csrfToken) {
      checkRateLimit();
    }
  }, [fetchMiningData, csrfToken, fetchCsrfToken]);
  
  // Add countdown timer for rate-limited users
  useEffect(() => {
    if (!twoFA.isRateLimited || !twoFA.remainingTime) return;
    
    // Update the timer every second
    const interval = setInterval(() => {
      setTwoFA((prev) => {
        const newRemainingTime = prev.remainingTime ? prev.remainingTime - 1 : 0;
        
        // If countdown reaches zero, reset rate limit
        if (newRemainingTime <= 0) {
          return {
            ...prev,
            isRateLimited: false,
            remainingTime: undefined
          };
        }
        
        return {
          ...prev,
          remainingTime: newRemainingTime
        };
      });
    }, 1000);
    
    return () => clearInterval(interval);
  }, [twoFA.isRateLimited, twoFA.remainingTime]);

  // Effect to update security details when miningStatus changes
  useEffect(() => {
    if (miningStatus?.security_violation) {
      if (miningStatus.security_details) {
        setSecurityDetails(miningStatus.security_details);
      }
    }
  }, [miningStatus]);
  
  // Simplified entrance animations - only on initial render
  useEffect(() => {
    if (isInitialLoad) {
      const timer = setTimeout(() => setStatAnimations(true), 300);
      return () => clearTimeout(timer);
    }
  }, [isInitialLoad]);

  // Memoized formatting functions
  const formatTime = useCallback((seconds: number) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }, []);

  const formatCRN = useCallback((value: number | string) => {
    if (value === undefined || value === null) return "0.00000000";
    const numValue = typeof value === 'string' ? parseFloat(value) : value;
    return isNaN(numValue) ? "0.00000000" : numValue.toFixed(8);
  }, []);
  
  const formatCRNInteger = useCallback((value: number | string) => {
    if (value === undefined || value === null) return "0";
    const numValue = typeof value === 'string' ? parseFloat(value) : value;
    if (isNaN(numValue)) return "0";
    return Number.isInteger(numValue) ? numValue.toString() : numValue.toFixed(2);
  }, []);
  
  const formatHoursRemaining = useCallback((hours: number) => {
    if (hours <= 0) return "Available now";
    
    const hoursInt = Math.floor(hours);
    const minutesInt = Math.floor((hours - hoursInt) * 60);
    const secondsInt = Math.floor(((hours - hoursInt) * 60 - minutesInt) * 60);
    
    return `${hoursInt}h ${minutesInt}m ${secondsInt}s`;
  }, []);

  const formatTimeLeft = useCallback((time: HoursRemaining) => {
    if (time.hours === 0 && time.minutes === 0) return "0:00:00";
    
    // Convert decimal hours to proper hours, minutes and seconds
    const totalSeconds = Math.floor(time.hours * 3600);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    
    return `${hours}:${minutes < 10 ? '0' : ''}${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
  }, []);

  // Optimize particle generation - reduce quantity and frequency
  useEffect(() => {
    if (isMining) {
      const generateParticles = () => {
        // Use fewer particles (6 instead of 15)
        const newParticles = Array.from({ length: 6 }, () => ({
          id: Math.random(),
          x: Math.random() * 100,
          y: Math.random() * 100,
          size: Math.random() * 3 + 1,
          speed: Math.random() * 3 + 1
        }));
        
        setParticles(newParticles);
      };

      // Generate initially and then less frequently
      generateParticles();
      const particleInterval = setInterval(generateParticles, 3500);

      return () => clearInterval(particleInterval);
    } else {
      // Clear particles when not mining
      setParticles([]);
    }
  }, [isMining]);

  // Optimize countdown timer to reduce re-renders
  useEffect(() => {
    let timer: NodeJS.Timeout;
    
    if (hoursRemaining.hours > 0) {
      timer = setInterval(() => {
        setHoursRemaining(prev => {
          const newHours = Math.max(0, prev.hours - (1/3600)); // Subtract 1 second
          // Only update if there's a meaningful change to reduce renders
          if (Math.abs(newHours - prev.hours) < 0.0001) return prev;
          return { hours: newHours, minutes: prev.minutes };
        });
      }, 1000);
    }
    
    return () => clearInterval(timer);
  }, [hoursRemaining.hours]);

  // Add device security check function
  const checkDeviceSecurity = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Get CSRF token if not available
      let token = csrfToken;
      if (!token) {
        token = await fetchCsrfToken();
      }
      
      // Use advanced fingerprinting to get all browser fingerprints
      const fingerprintData = await getAllFingerprints();
      
      // احصل على عنوان IP الحالي وأضفه إلى البيانات
      const currentIp = await axios.get('/api/user/ip').then(res => res.data.ip).catch(() => null);
      
      // Call the security check API endpoint with enhanced fingerprint data
      const response = await axios.post('/api/mining/check', {
        fingerprint_data: {
          ...fingerprintData,
          ip_address: currentIp
        }
      }, {
        headers: {
          "X-CSRF-Token": token || ''
        }
      });
      
      // Handle the security check response
      if (response.data.status === 'security_violation') {
        setSecurityViolation(response.data.message || 'Security violation detected');
        setPenaltyType(response.data.penalty_type || null);
        
        // Set security details if available
        if (response.data.details) {
          setSecurityDetails(response.data.details);
        }
      } else {
        // Security check passed
        setSecurityViolation(null);
        setPenaltyType(null);
        setSecurityDetails(undefined);
      }
    } catch (error: any) {
      console.error('Error checking device security:', error);
      
      // Handle security violation response
      if (error.response && error.response.status === 403) {
        // Check if this is a CSRF token error
        if (error.response.data && error.response.data.error && error.response.data.error.includes("CSRF token")) {
          console.log("CSRF token error, refreshing token...");
          await fetchCsrfToken();
          setError('Session expired. Please try again.');
          return;
        }
        
        setSecurityViolation('Security violation detected');
        
        if (error.response.data && error.response.data.penalty_type) {
          setPenaltyType(error.response.data.penalty_type);
        }
        
        if (error.response.data && error.response.data.details) {
          setSecurityDetails(error.response.data.details);
        }
      } else {
        setError('Failed to check device security. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Optimized complete mining with reward function
  const completeMiningWithReward = useCallback(async () => {
    try {
      // If we have a pending mining response, apply the rewards now
      if (pendingMiningResponse) {
        // Get the verification token from session storage (set by verify2FACode)
        const verificationToken = sessionStorage.getItem('2fa_verification_token');
        const verificationSignature = sessionStorage.getItem('2fa_verification_signature');
        const verificationTimestamp = sessionStorage.getItem('2fa_verification_timestamp');
        
        // Ensure verification data exists and is recent (within last 5 minutes)
        const now = Date.now();
        const tokenTimestamp = verificationTimestamp ? parseInt(verificationTimestamp) : 0;
        const isValidToken = verificationToken && 
                            verificationSignature && 
                            (now - tokenTimestamp < 300000); // 5 minutes
        
        if (!isValidToken) {
          setError('Your verification has expired. Please try again.');
          setPendingMiningResponse(null);
          return;
        }
        
        // Call the API to apply the pending mining reward with verification
        await axios.post('/api/mining/apply-reward', { 
          mining_data: pendingMiningResponse,
          verification: {
            token: verificationToken,
            signature: verificationSignature,
            timestamp: tokenTimestamp
          }
        }, {
          headers: {
            "X-CSRF-Token": csrfToken || ''
          }
        });
        
        // Clear the verification data
        sessionStorage.removeItem('2fa_verification_token');
        sessionStorage.removeItem('2fa_verification_signature');
        sessionStorage.removeItem('2fa_verification_timestamp');
        
        // Clear the pending response
        setPendingMiningResponse(null);
        
        // Refresh mining data to update the UI with new balances
        await fetchMiningData();
      }
      
      // If mining session hours is set, update cooldown
      if (miningStatus?.mining_session_hours) {
        setHoursRemaining({ hours: miningStatus.mining_session_hours, minutes: 0 });
      }
    } catch (err: any) {
      console.error('Error completing mining:', err);
      
      // Check if this is a CSRF token error
      if (err.response && err.response.status === 403 && 
          err.response.data && err.response.data.error && 
          err.response.data.error.includes("CSRF token")) {
        console.log("CSRF token error, refreshing token...");
        await fetchCsrfToken();
        setError('Session expired. Please try again.');
        return;
      }
      
      // Check if this is an authentication error
      if (err.response && (err.response.status === 401 || err.response.status === 403)) {
        setError('Authentication error. Please try again.');
        // Clear any mining in progress
        setIsMining(false);
        setMiningCompleted(false);
        setMiningComplete(false);
        setPendingMiningResponse(null);
        // Clear verification data
        sessionStorage.removeItem('2fa_verification_token');
        sessionStorage.removeItem('2fa_verification_signature');
        sessionStorage.removeItem('2fa_verification_timestamp');
        return;
      }
      
      setError('Error completing mining process.');
    }
  }, [miningStatus?.mining_session_hours, pendingMiningResponse, fetchMiningData, csrfToken, fetchCsrfToken]);
  
  // Optimized mining timer
  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (isMining) {
      // Set initial progress to 0
      setProgressPercent(0);
      
      interval = setInterval(() => {
        setMiningTime(prev => {
          // Increase the timer
          const newTime = prev + 1;
          
          // Update progress percentage for animation
          const totalTime = 10; // Animation lasts 10 seconds
          const newPercent = Math.min(100, (newTime / totalTime) * 100);
          setProgressPercent(newPercent);
          
          // Auto-complete mining after animation time
          if (newTime >= totalTime) {
            completeMiningWithReward();
            
            setIsMining(false);
            setMiningCompleted(true);
            setMiningComplete(true);
            
            return newTime;
          }
          
          return newTime;
        });
      }, 1000);
    }
    
    return () => clearInterval(interval);
  }, [isMining, completeMiningWithReward]);

  // Check if 2FA is required and update state
  const check2FARequired = useCallback(async () => {
    try {
      const response = await axios.get('/api/mining/check-2fa-required', {
        headers: {
          "X-CSRF-Token": csrfToken
        }
      });
      
      if (response.status === 200) {
        // Update 2FA status based on response
        setTwoFA(prev => ({
          ...prev,
          is2FAEnabled: response.data.is_2fa_enabled,
          require2FASetup: response.data.require_2fa_setup,
          error: null
        }));
        
        return {
          is2FAEnabled: response.data.is_2fa_enabled,
          require2FASetup: response.data.require_2fa_setup
        };
      }
      
      return { is2FAEnabled: false, require2FASetup: true };
    } catch (err) {
      console.error('Error checking 2FA status:', err);
      setTwoFA(prev => ({
        ...prev,
        error: 'Failed to check 2FA status'
      }));
      return { is2FAEnabled: false, require2FASetup: true };
    }
  }, [csrfToken]);
  
  // Verify 2FA code
  const verify2FACode = async (code: string) => {
    try {
      setTwoFA(prev => ({
        ...prev,
        isVerifying: true,
        error: null
      }));
      
      // Get CSRF token if not available
      let token = csrfToken;
      if (!token) {
        token = await fetchCsrfToken();
      }
      
      // Create a cryptographic hash of the code + timestamp for additional verification
      const timestamp = Date.now();
      const codeHash = await crypto.subtle.digest(
        'SHA-256',
        new TextEncoder().encode(`${code}-${timestamp}`)
      ).then(hashBuffer => {
        // Convert the hash to a hex string
        return Array.from(new Uint8Array(hashBuffer))
          .map(b => b.toString(16).padStart(2, '0'))
          .join('');
      }).catch(() => '');
      
      const response = await axios.post('/api/mining/verify-2fa', 
        { 
          code,
          timestamp,
          codeHash,
          challenge: window.btoa(code.split('').reverse().join('')) // Additional verification
        },
        {
          headers: {
            "X-CSRF-Token": token || '',
            "Content-Type": "application/json"
          }
        }
      );
      
      // Enhanced security: Check BOTH status code AND response content
      if (response.status === 200 && 
          response.data && 
          response.data.message && 
          response.data.message.includes('verified successfully') &&
          response.data.is_valid === true &&
          response.data.verification_token && 
          response.data.signature) {
        
        // Store verification info in sessionStorage with expiration
        sessionStorage.setItem('2fa_verification_token', response.data.verification_token);
        sessionStorage.setItem('2fa_verification_signature', response.data.signature);
        sessionStorage.setItem('2fa_verification_timestamp', Date.now().toString());
        
        // 2FA verification successful, continue with mining
        setTwoFA(prev => ({
          ...prev,
          isVerifying: false,
          showModal: false,
          error: null,
          isRateLimited: false,
          remainingAttempts: undefined,
          blockedUntil: undefined,
          remainingTime: undefined
        }));
        
        // If we have a pending security check, continue with mining
        if (pendingSecurityCheck) {
          // Store the mining response for later use when animation completes
          setPendingMiningResponse(pendingSecurityCheck);
          setPendingSecurityCheck(null);
          
          // Start mining animation
          setMiningAnimation(true);
          setMiningComplete(false);
          setMiningCompleted(false);
          setProgressPercent(0);
          setMiningTime(0);
          setShowCooldownAnimation(false);
          
          // Capture mining reward data
          const actualReward = pendingSecurityCheck.potential_reward || pendingSecurityCheck.daily_mining_rate;
          const baseReward = pendingSecurityCheck.daily_mining_rate;
          
          // Store values to display in the success screen
          setMiningRewardInfo({
            actual: actualReward,
            base: baseReward,
            conditions: pendingSecurityCheck.mining_conditions || 'normal'
          });
          
          // Start animation
          setTimeout(() => {
            setIsMining(true);
            setMiningAnimation(false);
          }, 500);
        }
      } else {
        // If response is 200 but doesn't contain the expected success message,
        // it might be a tampered response
        console.error('Unexpected response format or tampered response');
        setTwoFA(prev => ({
          ...prev,
          isVerifying: false,
          error: 'Security verification failed. Please try again.'
        }));
      }
    } catch (err: any) {
      console.error('Error verifying 2FA code:', err);
      
      if (err.response) {
        // Handle different error status codes
        if (err.response.status === 429) {
          // Rate limiting error
          const data = err.response.data;
          
          setTwoFA(prev => ({
            ...prev,
            isVerifying: false,
            error: data.message || 'Too many attempts. Please try again later.',
            isRateLimited: true,
            blockedUntil: data.blocked_until,
            remainingTime: data.remaining_time
          }));
        } else if (err.response.status === 401) {
          // Invalid 2FA code
          const errorMessage = err.response.data.message || 'Invalid authentication code';
          const remainingAttempts = err.response.data.remaining_attempts;
          
          setTwoFA(prev => ({
            ...prev,
            isVerifying: false,
            error: errorMessage,
            remainingAttempts: remainingAttempts
          }));
        } else if (err.response.status === 403) {
          // 2FA not set up
          setTwoFA(prev => ({
            ...prev,
            isVerifying: false,
            error: err.response.data.message || '2FA needs to be set up first',
            require2FASetup: true
          }));
        } else {
          // General error
          setTwoFA(prev => ({
            ...prev,
            isVerifying: false,
            error: err.response.data?.message || 'Failed to verify authentication code'
          }));
        }
      } else {
        setTwoFA(prev => ({
          ...prev,
          isVerifying: false,
          error: 'Network error. Please try again.'
        }));
      }
    }
  };
  
  // Handle 2FA modal close
  const handleTwoFAModalClose = () => {
    setTwoFA(prev => ({
      ...prev,
      showModal: false,
      error: null
    }));
    
    // Clear pending security check
    setPendingSecurityCheck(null);
  };

  // Optimized start mining function
  const startMining = useCallback(async () => {
    try {
      // Set loading state without animation yet
      setError(null);
      setSecurityViolation(null);
      setIsSecurityChecking(true); // Show security checking indicator
      
      // Check if 2FA is required first
      const twoFAStatus = await check2FARequired();
      
      // If 2FA is not enabled, show setup required modal
      if (!twoFAStatus.is2FAEnabled) {
        setIsSecurityChecking(false);
        setTwoFA(prev => ({
          ...prev,
          showModal: true,
          require2FASetup: true
        }));
        return;
      }
      
      // First check security with backend before any animations
      try {
        // Get CSRF token if not available
        let token = csrfToken;
        if (!token) {
          token = await fetchCsrfToken();
        }
        
        // Use advanced fingerprinting to collect device fingerprints
        const fingerprintData = await getAllFingerprints();
        
        // احصل على عنوان IP الحالي وأضفه إلى البيانات
        const currentIp = await axios.get('/api/user/ip').then(res => res.data.ip).catch(() => null);
        
        // Call the API to check if mining is allowed, including fingerprint data
        const response = await axios.post('/api/mining/check', {
          fingerprint_data: {
            ...fingerprintData,
            ip_address: currentIp
          }
        }, {
          headers: {
            "X-CSRF-Token": token || '',
            "Content-Type": "application/json"
          }
        });
        
        // Security check completed
        setIsSecurityChecking(false);
        
        if (response.data.status === 'mining_cooldown') {
          setError('You need to wait before mining again.');
          setHoursRemaining({ 
            hours: response.data.hours_remaining,
            minutes: 0 
          });
          return;
        }
        
        // Check for security violations
        if (response.data.status === 'security_violation') {
          // Check if it's a mining_block and update state accordingly
          if (response.data.penalty_type === 'mining_block' && response.data.risk_score > 80) {  // Add risk score check
              setMiningBlock(true);
              // Don't set securityViolation to allow mining stats to show
          } else {
              // For other security violations, show the full screen
              setSecurityViolation(response.data.message || 'Multiple accounts detected');
              setPenaltyType(response.data.penalty_type || null);
          }
          
          // Set security details if available
          if (response.data.details) {
              setSecurityDetails(response.data.details);
          }
          
          return;
        }
        
        // Security check passed, now prompt for 2FA verification
        // Store the security check response while waiting for 2FA
        setPendingSecurityCheck(response.data);
        
        // Show 2FA modal
        setTwoFA(prev => ({
          ...prev,
          showModal: true,
          require2FASetup: false
        }));
        
      } catch (err: any) {
        console.error('Error starting mining:', err);
        setIsSecurityChecking(false);
        
        // Check if this is a CSRF token error
        if (err.response && err.response.status === 403 && 
            err.response.data && err.response.data.error && 
            err.response.data.error.includes("CSRF token")) {
          console.log("CSRF token error, refreshing token...");
          await fetchCsrfToken();
          setError('Session expired. Please try again.');
          return;
        }
        
        if (err.response && err.response.status === 403) {
          // Handle other security violations
          setSecurityViolation('Security violation detected');
          
          if (err.response.data && err.response.data.penalty_type) {
            setPenaltyType(err.response.data.penalty_type);
          }
          
          if (err.response.data && err.response.data.details) {
            setSecurityDetails(err.response.data.details);
          }
        } else {
          setError('Failed to start mining. Please try again.');
        }
      }
    } catch (err) {
      console.error('Error in mining process:', err);
      setIsSecurityChecking(false);
      setError('An unexpected error occurred. Please try again.');
    }
  }, [csrfToken, fetchCsrfToken, check2FARequired]);

  // Optimized complete mining function
  const completeMining = useCallback(async () => {
    try {
      // Get CSRF token if not available
      let token = csrfToken;
      if (!token) {
        token = await fetchCsrfToken();
      }
      
      // Just notify the backend that mining is complete
      await axios.post('/api/mining/stop', {}, {
        headers: {
          "X-CSRF-Token": token || ''
        }
      });
      
      // Use our optimized fetch function
      debouncedRefresh();
    } catch (err: any) {
      console.error('Error completing mining:', err);
      
      // Check if this is a CSRF token error
      if (err.response && err.response.status === 403 && 
          err.response.data && err.response.data.error && 
          err.response.data.error.includes("CSRF token")) {
        console.log("CSRF token error, refreshing token...");
        await fetchCsrfToken();
      }
    }
  }, [debouncedRefresh, csrfToken, fetchCsrfToken]);

  // Optimized hourly rate formatter
  const formatHourlyRate = useCallback((rate: number | undefined): string => {
    if (rate === undefined || rate === null || isNaN(rate)) {
      return "0.00000000";
    }
    return rate.toFixed(8);
  }, []);

  // Optimized mining rate percentage calculation
  const getMiningRatePercentage = useCallback(() => {
    if (!miningStatus || !miningStatus.hourly_mining_rate || isNaN(miningStatus.hourly_mining_rate)) {
      return 10; // Default to 10% so it's visible
    }
    
    // Calculate percentage based on max rate of 1 CRN/hour
    const percentage = (miningStatus.hourly_mining_rate / 1) * 100;
    
    // Ensure it's at least 10% so it's visible
    return Math.max(10, Math.min(100, percentage));
  }, [miningStatus]);

  // Optimized success to cooldown transition
  useEffect(() => {
    let timer: NodeJS.Timeout;
    
    // When mining is completed, show success screen for 3 seconds, then switch to cooldown
    if (miningComplete && !isMining) {
      setShowSuccessScreen(true);
      
      // After 3 seconds, transition to the cooldown screen
      timer = setTimeout(() => {
        setShowSuccessScreen(false);
      }, 3000);
    }
    
    return () => clearTimeout(timer);
  }, [miningComplete, isMining]);

  // Optimized data refresh function
  const refreshData = useCallback(async () => {
    debouncedRefresh();
  }, [debouncedRefresh]);

  // Calculate hours remaining for cooldown more efficiently
  useEffect(() => {
    if (!miningStatus || miningStatus.can_mine || !miningStatus.last_mined) return;
    
    const calculateRemainingTime = () => {
      const lastMined = new Date(miningStatus.last_mined);
      const now = new Date();
      const miningSessionHours = miningStatus.mining_session_hours || 1;
      
      // Calculate when mining will be available again
      const nextMiningTime = new Date(lastMined);
      nextMiningTime.setHours(nextMiningTime.getHours() + miningSessionHours);
      
      // Calculate time difference
      const diff = Math.max(0, nextMiningTime.getTime() - now.getTime());
      const hours = diff / (1000 * 60 * 60);
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      
      // Set hours remaining state
      setHoursRemaining({ hours, minutes });
    };
    
    calculateRemainingTime();
    
    // Update the cooldown time every 5 seconds instead of on each render
    const interval = setInterval(calculateRemainingTime, 5000);
    return () => clearInterval(interval);
  }, [miningStatus]);

  // If security violation is detected, show violation screen
  if (securityViolation) {
    return (
      <div className="bg-[#262626] min-h-screen p-4 sm:p-6 pb-24 md:pb-6">
        <SecurityViolationScreen 
          message={securityViolation} 
          penaltyType={penaltyType || undefined} 
          securityDetails={securityDetails}
        />
      </div>
    );
  }

  // If in maintenance mode, show maintenance screen first (early return)
  if (miningStatus?.maintenance_mode) {
    return (
      <div className="bg-[#262626] min-h-screen p-4 sm:p-6 pb-24 md:pb-6">
        <MaintenanceScreen />
        
        {/* Global styles for animations */}
        <style>{`
          @keyframes pulse {
            0%, 100% { opacity: 0.6; transform: scale(1); }
            50% { opacity: 1; transform: scale(1.05); }
          }
          
          @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
          }
          
          @keyframes spin-slow {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
          
          @keyframes spin-reverse {
            from { transform: rotate(0deg); }
            to { transform: rotate(-360deg); }
          }
          
          @keyframes glow {
            0%, 100% { box-shadow: 0 0 5px rgba(59, 130, 246, 0.5); }
            50% { box-shadow: 0 0 20px rgba(59, 130, 246, 0.8); }
          }
          
          @keyframes shake {
            0%, 100% { transform: translateX(0); }
            10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
            20%, 40%, 60%, 80% { transform: translateX(5px); }
          }
          
          @keyframes hammer {
            0%, 100% { transform: rotate(0deg); }
            50% { transform: rotate(-30deg); }
          }
          
          .animate-spin-slow {
            animation: spin-slow 6s linear infinite;
          }
          
          .animate-spin-reverse {
            animation: spin-reverse 8s linear infinite;
          }
          
          .animate-hammer {
            animation: hammer 2s ease-in-out infinite;
            transform-origin: bottom right;
          }
          
          .shadow-amber-glow {
            box-shadow: 0 0 15px rgba(251, 191, 36, 0.6);
          }
        `}</style>
      </div>
    );
  }

  // If loading, show loading screen with dark theme
  if (isLoading) {
    return (
      <div className="bg-[#262626] min-h-screen flex items-center justify-center p-4 sm:p-6 pb-24 md:pb-6">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-10 w-10 sm:h-12 sm:w-12 border-b-2 border-gray-300 mb-4"></div>
          <p className="text-gray-300 text-sm sm:text-base">Loading mining data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#262626] text-gray-200 py-4 px-3 sm:py-6 sm:px-6 pb-24 md:pb-6">
      {isLoading && (
        <div className="bg-[#262626] min-h-screen flex items-center justify-center p-4 sm:p-6 pb-24 md:pb-6">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-10 w-10 sm:h-12 sm:w-12 border-b-2 border-gray-300 mb-4"></div>
            <p className="text-gray-300 text-sm sm:text-base">Loading mining data...</p>
          </div>
        </div>
      )}
      <div className="max-w-7xl mx-auto">
        {/* Show the security policy banner if not in a security violation or maintenance state */}
        {!securityViolation && !miningStatus?.maintenance_mode && !isLoading && <SecurityPolicyBanner />}
        {/* Regular mining UI without maintenance mode check */}
        {/* BOOSTED MINING EVENT BANNER - ظاهر فقط عندما boosted_mining نشط */}
        {miningStatus?.boosted_mining && (
          <div className="relative overflow-hidden rounded-2xl mb-6 sm:mb-8">
            {/* خلفية متحركة مع تأثير التوهج */}
            <div className="absolute inset-0 bg-gradient-to-r from-yellow-500 via-amber-500 to-orange-500 animate-gradient-x"></div>
            
            {/* طبقة التأثير المتوهج */}
                <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjxkZWZzPjxwYXR0ZXJuIGlkPSJwYXR0ZXJuIiB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHBhdHRlcm5Vbml0cz0idXNlclNwYWNlT25Vc2UiIHBhdHRlcm5UcmFuc2Zvcm09InJvdGF0ZSg0NSkiPjxyZWN0IHg9IjAiIHk9IjAiIHdpZHRoPSIyMCIgaGVpZ2h0PSIyMCIgZmlsbD0icmdiYSgyNTUsMjU1LDI1NSwwLjA1KSIvPjwvcGF0dGVybj48L2RlZnM+PHJlY3QgeD0iMCIgeT0iMCIgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0idXJsKCNwYXR0ZXJuKSIvPjwvc3ZnPg==')]"></div>
                
            {/* الجسيمات المتطايرة - reduce for mobile */}
                <div className="absolute inset-0 overflow-hidden">
              {Array.from({ length: 8 }).map((_, i) => (
                    <div
                      key={`particle-${i}`}
                      className="absolute rounded-full animate-float-particle"
                      style={{
                        width: `${Math.random() * 6 + 3}px`,
                        height: `${Math.random() * 6 + 3}px`,
                        backgroundColor: i % 3 === 0 ? 'rgba(255,255,255,0.8)' : i % 3 === 1 ? 'rgba(255,235,151,0.7)' : 'rgba(255,203,97,0.6)',
                        left: `${Math.random() * 100}%`,
                        top: `${Math.random() * 100}%`,
                        animationDuration: `${Math.random() * 5 + 5}s`,
                        animationDelay: `${Math.random() * 2}s`
                      }}
                    />
                  ))}
                </div>
                
            {/* محتوى البانر */}
            <div className="relative z-10 p-4 sm:p-8 flex flex-col md:flex-row items-center justify-between">
              <div className="flex flex-col sm:flex-row items-center text-center sm:text-left mb-4 md:mb-0">
                <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-gradient-to-br from-yellow-300 to-amber-500 flex items-center justify-center mb-3 sm:mb-0 sm:mr-6 shadow-xl animate-pulse-glow">
                  <Rocket className="text-white" size={28} />
                    </div>
                    <div>
                  <h2 className="text-xl sm:text-3xl font-extrabold text-white mb-1 sm:mb-2 flex flex-wrap items-center justify-center sm:justify-start gap-1 sm:gap-2">
                    <Star className="text-yellow-200 animate-spin-slow" size={18} />
                    <span className="animate-text-glow">BOOSTED MINING!</span>
                    <Star className="text-yellow-200 animate-spin-slow-reverse" size={18} />
                      </h2>
                  <p className="text-sm sm:text-xl text-yellow-100 font-medium">All miners now receive <span className="font-bold text-white">DOUBLE REWARDS</span>!</p>
                    </div>
                  </div>
                  
              <div className="bg-white/20 backdrop-blur-sm text-white rounded-full px-4 py-2 sm:px-6 sm:py-3 font-bold text-sm sm:text-xl border-2 border-white/30 animate-pulse shadow-glow">
                <Flame className="inline mr-1 sm:mr-2 text-yellow-200 animate-flicker" size={18} />
                <span className="animate-text-glow">2X REWARDS</span>
                  </div>
                </div>
                
            {/* زخارف مضيئة */}
                <div className="absolute top-0 left-0 w-16 h-16 sm:w-24 sm:h-24 rounded-full bg-yellow-300/30 blur-xl"></div>
                <div className="absolute bottom-0 right-0 w-20 h-20 sm:w-32 sm:h-32 rounded-full bg-orange-400/30 blur-xl"></div>
              </div>
            )}

        {/* Error message with dark theme */}
        {error && (
          <div className="bg-red-900 border border-red-700 rounded-xl p-3 sm:p-4 mb-4 sm:mb-6 flex items-center gap-2 sm:gap-3">
            <AlertCircle className="text-red-300 flex-shrink-0" size={18} />
            <p className="text-red-200 text-sm">{error}</p>
              </div>
            )}
            
            {miningStatus && (
              <>
            {/* Mining Stats Cards with dark theme */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6 sm:mb-10">
                  {/* Total Mining with dark theme */}
              <div className={`bg-[#2b2b2b] p-4 sm:p-6 rounded-2xl border border-[#3A3A3E] shadow-lg hover:shadow-xl ${miningStatus?.boosted_mining ? 'border-amber-700' : ''}`}>
                <div className="flex items-center justify-between mb-3 sm:mb-4">
                  <div className="flex items-center gap-2 sm:gap-3">
                    <div className={`p-2 sm:p-3 rounded-xl shadow-lg ${miningStatus?.boosted_mining ? 'bg-gradient-to-br from-amber-400 to-yellow-600 animate-pulse-subtle' : 'bg-gradient-to-br from-yellow-400 to-yellow-600'}`}>
                      <Coins className="text-white" size={20} />
                        </div>
                    <h3 className="font-medium text-sm sm:text-base text-[#FFFFFF]">Total Mining</h3>
                      </div>
                      <div className="p-1 sm:p-1.5 rounded-lg bg-green-100">
                        <TrendingUp size={12} className="text-green-600" />
                      </div>
                    </div>
                    <div className="mt-1 sm:mt-2">
                      <div className="flex items-baseline gap-1 sm:gap-2">
                        <h2 className="text-xl sm:text-3xl font-bold text-gray-300">
                          <Suspense fallback={<NumberDisplay value={miningStatus?.total_mined || "0.00000000"} />}>
                            <SlotCounter
                              value={miningStatus?.total_mined || "0.00000000"}
                              duration={0.5}
                              startValue="0"
                              containerClassName={miningStatus?.boosted_mining ? "text-amber-600" : ""}
                            />
                          </Suspense>
                        </h2>
                        <span className="text-gray-500 text-sm sm:text-xl">CRN</span>
                        {miningStatus?.boosted_mining && (
                          <div className="flex items-center text-amber-600 font-bold animate-pulse mt-0.5 sm:mt-1">
                            <Flame size={14} className="mr-0.5 animate-flicker" />
                            <span className="text-xs sm:text-lg">+100%</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

              {/* Mining Rate with dark theme */}
              <div className={`bg-[#2b2b2b] p-4 sm:p-6 rounded-2xl border border-[#3A3A3E] shadow-lg hover:shadow-xl ${miningStatus?.boosted_mining ? 'border-amber-700' : ''}`}>
                <div className="flex items-center justify-between mb-3 sm:mb-4">
                  <div className="flex items-center gap-2 sm:gap-3">
                    <div className={`p-2 sm:p-3 rounded-xl shadow-lg ${miningStatus?.boosted_mining ? 'bg-gradient-to-br from-amber-400 to-yellow-600 animate-pulse-subtle' : 'bg-gradient-to-br from-amber-400 to-amber-600'}`}>
                      <BarChart3 className="text-white" size={20} />
                        </div>
                    <h3 className="font-medium text-sm sm:text-base text-[#FFFFFF]">Mining Rate</h3>
                      </div>
                      <div className="p-1 sm:p-1.5 rounded-lg bg-green-100">
                        <TrendingUp size={12} className="text-green-600" />
                      </div>
                    </div>
                    <div className="mt-1 sm:mt-2">
                  <div className="flex items-baseline gap-1 sm:gap-2 flex-wrap">
                    <h2 className="text-xl sm:text-3xl font-bold text-gray-300">
                          <Suspense fallback={<NumberDisplay value={formatCRNInteger(miningStatus?.daily_mining_rate)} />}>
                            <SlotCounter
                              value={formatCRNInteger(miningStatus?.daily_mining_rate)}
                              duration={0.5}
                              startValue={formatCRNInteger(miningStatus?.daily_mining_rate)}
                              containerClassName={miningStatus?.boosted_mining ? "text-amber-600" : ""}
                            />
                          </Suspense>
                        </h2>
                    <span className="text-gray-500 text-sm sm:text-xl">CRN/day</span>
                        
                    {/* Boost Indicator */}
                        {miningStatus?.boosted_mining && (
                      <div className="flex items-center ml-1 sm:ml-2 text-amber-600 font-bold animate-pulse">
                        <Flame size={14} className="mr-1 animate-flicker" />
                        <span className="text-xs sm:text-lg">+100%</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

              {/* Mining Speed with Boost Badge with dark theme */}
              <div className={`bg-[#2b2b2b] p-4 sm:p-6 rounded-2xl border border-[#3A3A3E] shadow-lg hover:shadow-xl ${miningStatus?.boosted_mining ? 'border-amber-700' : ''}`}>
                <div className="flex items-center justify-between mb-3 sm:mb-4">
                  <div className="flex items-center gap-2 sm:gap-3">
                    <div className={`p-2 sm:p-3 rounded-xl shadow-lg ${miningStatus?.boosted_mining ? 'bg-gradient-to-br from-amber-400 to-orange-500 animate-pulse-subtle' : 'bg-gradient-to-br from-blue-400 to-blue-600'}`}>
                      <Activity className="text-white" size={20} />
                    </div>
                    <h3 className="font-medium text-sm sm:text-base text-[#FFFFFF]">Mining Speed</h3>
                  </div>
                  
                  {/* Boost Badge */}
                  {miningStatus?.boosted_mining && (
                    <div className="bg-gradient-to-r from-amber-100 to-amber-200 text-amber-800 text-xs font-bold px-2 py-0.5 sm:px-3 sm:py-1 rounded-full flex items-center shadow-sm animate-pulse-slow">
                      <Flame size={12} className="mr-0.5 text-orange-500 animate-flicker" />
                      2X
                    </div>
                  )}
                </div>
                
                <div className="mt-1 sm:mt-2">
                  <div className="flex flex-wrap items-baseline gap-1 sm:gap-2">
                    <h2 className={`text-xl sm:text-2xl font-bold ${miningStatus?.boosted_mining ? 'text-amber-600' : 'text-gray-300'}`}>
                      <Suspense fallback={<NumberDisplay value={formatHourlyRate(miningStatus?.hourly_mining_rate)} />}>
                        <SlotCounter
                          value={formatHourlyRate(miningStatus?.hourly_mining_rate)}
                          duration={0.5}
                          startValue={formatHourlyRate(miningStatus?.hourly_mining_rate)}
                          containerClassName="max-w-full inline-block"
                        />
                      </Suspense>
                    </h2>
                    <span className="text-gray-500 text-sm sm:text-xl whitespace-nowrap">CRN/h</span>
                    
                    {/* Boost Indicator */}
                    {miningStatus?.boosted_mining && (
                      <div className="flex items-center text-amber-600 font-bold animate-pulse mt-0.5 sm:mt-1">
                        <Flame size={14} className="mr-0.5 animate-flicker" />
                        <span className="text-xs sm:text-lg">+100%</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Mining Conditions Card */}
              <MiningConditionsCard conditions={miningStatus.mining_conditions || 'normal'} />
            </div>

            {/* Mining Status: READY state with dark theme */}
            {!isMining && miningStatus?.can_mine && !miningComplete && !miningBlock && (
              <div className={`bg-[#2b2b2b] rounded-3xl border-2 ${miningStatus?.boosted_mining ? 'border-amber-700 shadow-amber-glow' : 'border-[#8875FF] shadow-xl shadow-[#8875FF]/20'} p-4 sm:p-8 mb-6 sm:mb-10 relative overflow-hidden`}>
                {/* Subtle background waves */}
                <div className="absolute inset-0 overflow-hidden pointer-events-none">
                  <svg className="absolute inset-0 w-full h-full opacity-5" viewBox="0 0 100 100" preserveAspectRatio="none">
                    <path 
                      d="M0,50 Q20,45 40,50 T80,55 T120,50" 
                      fill="none" 
                      stroke={miningStatus?.boosted_mining ? "#f59e0b" : "#3b82f6"} 
                      strokeWidth="1"
                    />
                    <path 
                      d="M0,60 Q25,55 50,60 T100,55" 
                      fill="none" 
                      stroke={miningStatus?.boosted_mining ? "#f97316" : "#8b5cf6"}
                      strokeWidth="1"
                    />
                  </svg>
                </div>
                
                <div className="flex flex-col space-y-4 sm:space-y-6">
                  <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
                    <div>
                      <h2 className="text-xl sm:text-3xl font-bold mb-1 sm:mb-2">
                        Mining Status: <span className={miningStatus?.boosted_mining ? "text-amber-500" : "text-white font-bold"}>READY</span> <span className="text-[#8875FF] font-bold">✓</span>
                      </h2>
                      <p className="text-sm sm:text-lg text-gray-300">
                        Ready to mine! Press the Start Mining button to earn CRN.
                      </p>
                    </div>
                    
                    {/* Boosted Mining Badge */}
                    {miningStatus?.boosted_mining && (
                      <div className="px-3 py-1 sm:px-4 sm:py-2 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-full shadow-lg flex items-center gap-1 sm:gap-2 animate-pulse self-start sm:self-auto">
                        <Zap size={16} />
                        <span className="text-sm font-bold">BOOSTED EVENT</span>
                      </div>
                    )}
                  </div>

                  <div className="flex flex-col sm:flex-row">
                    {/* Left side - Mining icon */}
                    <div className="w-full sm:w-1/3 flex justify-center items-center mb-4 sm:mb-0">
                      <div className="relative w-28 h-28 sm:w-40 sm:h-40">
                        {/* Background ring */}
                        <div className={`absolute inset-0 rounded-full ${miningStatus?.boosted_mining ? 'bg-amber-100' : 'bg-[#8875FF]/30'} opacity-80 shadow-[0_0_25px_8px_rgba(136,117,255,0.4)] animate-pulse`}></div>
                        
                        {/* CPU icon in center with animation */}
                        <div className="absolute inset-0 flex items-center justify-center">
                          <div className={`relative z-10 w-20 h-20 sm:w-32 sm:h-32 rounded-full ${miningStatus?.boosted_mining ? 'bg-amber-200' : 'bg-[#8875FF]/50'} flex items-center justify-center border-4 ${miningStatus?.boosted_mining ? 'border-amber-300' : 'border-[#8875FF]'} animate-pulse`}>
                            <Cpu size={36} className={`${miningStatus?.boosted_mining ? "text-amber-600" : "text-white"} animate-spin-slow`} />
                          </div>
                          
                          {/* Accent rings with animation */}
                          <div className={`absolute inset-0 rounded-full border-4 ${miningStatus?.boosted_mining ? 'border-amber-200' : 'border-[#8875FF]/70'} opacity-70 animate-pulse`}></div>
                          <div className={`absolute inset-2 rounded-full border-2 ${miningStatus?.boosted_mining ? 'border-amber-300' : 'border-[#8875FF]'} opacity-50`}></div>
                        </div>
                      </div>
                    </div>
                    
                    {/* Right side - Mining Info */}
                    <div className="w-full sm:w-2/3 sm:ml-8">
                      <div className="bg-gray-700 backdrop-blur-sm rounded-xl p-4 sm:p-6 shadow-md border border-gray-600">
                        {/* Mining Rate and Info */}
                        <div className="flex justify-between mb-4 sm:mb-6">
                          <div>
                            <p className="text-gray-300 text-xs sm:text-sm font-medium">Mining Rate</p>
                            <p className={`text-xl sm:text-2xl font-bold ${miningStatus?.boosted_mining ? 'text-amber-600' : 'text-[#8875FF]'}`}>
                              {miningStatus && miningStatus.daily_mining_rate ? formatCRNInteger(miningStatus.daily_mining_rate) : "0.00"} CRN
                              {miningStatus?.boosted_mining && (
                                <span className="text-xs sm:text-sm ml-2 bg-amber-100 text-amber-800 px-2 py-0.5 rounded">2x</span>
                              )}
                            </p>
                            <p className="text-xs sm:text-sm text-gray-300 mt-1">
                              Full value: {miningStatus ? formatCRN(miningStatus.daily_mining_rate) : "0.00000000"} CRN
                            </p>
                          </div>
                        </div>
                        
                        {/* Tip */}
                        <div className={`flex items-center gap-2 sm:gap-3 p-3 sm:p-4 rounded-lg ${miningStatus?.boosted_mining ? 'bg-amber-900 text-amber-300' : 'bg-[#8875FF]/30 text-[#D4CCFF]'}`}>
                          <LightbulbIcon size={18} className={miningStatus?.boosted_mining ? 'text-amber-500' : 'text-[#8875FF]'} />
                          <p className="text-xs sm:text-sm">
                            <span className="font-medium">TIP:</span> Your mining rewards are deposited directly into your wallet after completion.
                          </p>
                        </div>
                      </div>

                      {/* Start Mining Button */}
                      <div className="mt-4 sm:mt-6 flex justify-center">
                        <button
                          onClick={startMining}
                          disabled={!miningStatus?.can_mine || isMining || isSecurityChecking || twoFA.isRateLimited}
                          className={`px-4 sm:px-8 py-3 sm:py-4 rounded-xl w-full flex items-center justify-center gap-2 sm:gap-3 text-base sm:text-lg font-medium transition-all duration-300 shadow-lg ${
                            isSecurityChecking 
                              ? "bg-gray-400 text-white cursor-wait" 
                              : twoFA.isRateLimited
                              ? "bg-gray-700 text-gray-400 cursor-not-allowed"
                              : miningStatus?.boosted_mining 
                              ? "bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white relative overflow-hidden" 
                              : "bg-gradient-to-r from-[#7865FF] to-[#8875FF] hover:from-[#6855FF] hover:to-[#7865FF] text-white"
                          }`}
                        >
                          {/* Button effects */}
                          {miningStatus?.boosted_mining && !isSecurityChecking && !twoFA.isRateLimited && (
                            <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" style={{ backgroundSize: '200% 100%' }}></span>
                          )}
                          
                          {/* Button content */}
                          <span className="relative z-10 flex items-center gap-2">
                            {isSecurityChecking ? (
                              <>
                                <RefreshCw size={18} className="animate-spin" />
                                <span className="text-sm sm:text-base">Checking Security...</span>
                              </>
                            ) : twoFA.isRateLimited ? (
                              <>
                                <Lock size={18} />
                                <span className="text-sm sm:text-base">
                                  Locked for {twoFA.remainingTime && twoFA.remainingTime > 60 
                                    ? Math.ceil(twoFA.remainingTime / 60) + " min" 
                                    : (twoFA.remainingTime || 0) + " sec"}
                                </span>
                              </>
                            ) : (
                              <>
                                <Play size={18} />
                                <span>{miningStatus?.boosted_mining ? "Start Boosted Mining" : "Start Mining"}</span>
                              </>
                            )}
                          </span>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Mining IN PROGRESS state with dark theme */}
            {isMining && (
              <div className={`bg-gray-800 rounded-3xl border-2 ${miningStatus?.boosted_mining ? 'border-amber-700 shadow-amber-glow' : 'border-[#8875FF] shadow-xl shadow-[#8875FF]/20'} p-4 sm:p-8 mb-6 sm:mb-10 relative overflow-hidden`}>
                {/* Subtle background waves */}
                <div className="absolute inset-0 overflow-hidden pointer-events-none">
                  <svg className="absolute inset-0 w-full h-full opacity-5" viewBox="0 0 100 100" preserveAspectRatio="none">
                    <path 
                      d="M0,50 Q20,45 40,50 T80,55 T120,50" 
                      fill="none" 
                      stroke={miningStatus?.boosted_mining ? "#f59e0b" : "#3b82f6"} 
                      strokeWidth="1"
                    />
                    <path 
                      d="M0,60 Q25,55 50,60 T100,55" 
                      fill="none" 
                      stroke={miningStatus?.boosted_mining ? "#f97316" : "#8b5cf6"}
                      strokeWidth="1"
                    />
                  </svg>
                </div>
                
                <div className="flex flex-col space-y-4 sm:space-y-6">
                  <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
                    <div>
                      <h2 className="text-xl sm:text-3xl font-bold mb-1 sm:mb-2">
                        Mining Status: <span className={miningStatus?.boosted_mining ? "text-amber-500" : "text-[#8875FF]"}>IN PROGRESS</span>
                      </h2>
                      <p className="text-sm sm:text-lg text-gray-300">
                        Mining in progress. Please wait while we process your mining session.
                      </p>
                    </div>
                    
                    {/* Boosted Mining Badge */}
                    {miningStatus?.boosted_mining && (
                      <div className="px-3 py-1 sm:px-4 sm:py-2 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-full shadow-lg flex items-center gap-1 sm:gap-2 animate-pulse self-start sm:self-auto">
                        <Zap size={16} />
                        <span className="text-sm font-bold">BOOSTED EVENT</span>
                      </div>
                    )}
                  </div>

                  <div className="flex flex-col sm:flex-row">
                    {/* Left side - Mining animation */}
                    <div className="w-full sm:w-1/3 flex justify-center items-center mb-4 sm:mb-0">
                      <div className="relative w-28 h-28 sm:w-40 sm:h-40">
                        {/* Background ring */}
                        <div className={`absolute inset-0 rounded-full ${miningStatus?.boosted_mining ? 'bg-amber-100' : 'bg-[#8875FF]/30'} opacity-80 shadow-[0_0_25px_8px_rgba(136,117,255,0.4)] animate-pulse`}></div>
                        
                        {/* CPU icon in center with animation */}
                        <div className="absolute inset-0 flex items-center justify-center">
                          <div className={`relative z-10 w-20 h-20 sm:w-32 sm:h-32 rounded-full ${miningStatus?.boosted_mining ? 'bg-amber-200' : 'bg-[#8875FF]/50'} flex items-center justify-center border-4 ${miningStatus?.boosted_mining ? 'border-amber-300' : 'border-[#8875FF]'} animate-pulse`}>
                            <Cpu size={36} className={`${miningStatus?.boosted_mining ? "text-amber-600" : "text-white"} animate-spin-slow`} />
                          </div>
                          
                          {/* Accent rings with animation */}
                          <div className={`absolute inset-0 rounded-full border-4 ${miningStatus?.boosted_mining ? 'border-amber-200' : 'border-[#8875FF]/70'} opacity-70 animate-pulse`}></div>
                          <div className={`absolute inset-2 rounded-full border-2 ${miningStatus?.boosted_mining ? 'border-amber-300' : 'border-[#8875FF]'} opacity-50`}></div>
                          
                          {/* Particle effects - reduced for mobile */}
                          {particles.slice(0, 3).map(particle => (
                            <div
                              key={particle.id}
                              className="absolute w-2 h-2 rounded-full bg-white animate-float-particle"
                              style={{
                                left: `${particle.x}%`,
                                top: `${particle.y}%`,
                                width: `${particle.size}px`,
                                height: `${particle.size}px`,
                                animationDuration: `${particle.speed}s`,
                                backgroundColor: miningStatus?.boosted_mining 
                                  ? `rgba(${217 + Math.random() * 38}, ${119 + Math.random() * 30}, ${6 + Math.random() * 10}, ${0.6 + Math.random() * 0.4})` 
                                  : `rgba(${59 + Math.random() * 40}, ${130 + Math.random() * 40}, ${246 + Math.random() * 10}, ${0.6 + Math.random() * 0.4})`
                              }}
                            />
                          ))}
                        </div>
                      </div>
                    </div>
                    
                    {/* Right side - Mining Progress Info */}
                    <div className="w-full sm:w-2/3 sm:ml-8">
                      <div className="bg-gray-700/80 backdrop-blur-sm rounded-xl p-4 sm:p-6 shadow-md border border-gray-600">
                        {/* Progress bar */}
                        <div className="mb-3 sm:mb-4">
                          <div className="flex justify-between items-center mb-1 sm:mb-2">
                            <p className="text-gray-300 text-xs sm:text-sm font-medium">Mining Progress</p>
                            <p className="text-gray-300 text-xs sm:text-sm font-medium">{progressPercent.toFixed(0)}%</p>
                          </div>
                          
                          <div className="w-full bg-gray-600 rounded-full h-2 sm:h-3">
                            <div 
                              className={`${miningStatus?.boosted_mining ? 'bg-gradient-to-r from-amber-500 to-orange-500' : 'bg-gradient-to-r from-[#7865FF] to-[#9D8DFF]'} h-2 sm:h-3 rounded-full transition-all duration-300 ease-out`}
                              style={{ width: `${progressPercent}%` }}
                            ></div>
                          </div>
                        </div>
                        
                        {/* Timer */}
                        <div className="flex flex-col sm:flex-row sm:justify-between mb-4 sm:mb-6 gap-2">
                          <div>
                            <p className="text-gray-300 text-xs sm:text-sm font-medium">Elapsed Time</p>
                            <p className={`text-lg sm:text-2xl font-bold font-mono ${miningStatus?.boosted_mining ? 'text-amber-600' : 'text-[#8875FF]'}`}>
                              {formatTime(miningTime)}
                            </p>
                          </div>
                          <div className="sm:text-right">
                            <p className="text-gray-300 text-xs sm:text-sm font-medium">Expected Reward</p>
                            <p className="text-lg sm:text-2xl font-bold text-gray-300">
                              {miningStatus && miningStatus.daily_mining_rate ? formatCRNInteger(miningStatus.daily_mining_rate) : "0"} CRN
                              {miningStatus?.boosted_mining && (
                                <span className="text-xs sm:text-sm ml-2 bg-amber-100 text-amber-800 px-2 py-0.5 rounded">2x</span>
                              )}
                            </p>
                          </div>
                        </div>
                        
                        {/* Mining message */}
                        <div className={`flex items-center gap-2 sm:gap-3 p-3 sm:p-4 rounded-lg ${miningStatus?.boosted_mining ? 'bg-amber-900 text-amber-300' : 'bg-[#8875FF]/40 text-white'}`}>
                          <Activity size={18} className={`${miningStatus?.boosted_mining ? 'text-amber-500' : 'text-white'} animate-pulse`} />
                          <p className="text-xs sm:text-sm">
                            <span className="font-medium">MINING:</span> Your device is currently mining CRN. Please don't close this page.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Mining Status: COOLDOWN state with dark theme */}
            {!isMining && (!miningStatus?.can_mine || (miningComplete && !showSuccessScreen)) && !miningBlock && (
              <div className="bg-gray-800 rounded-3xl border border-orange-700 shadow-xl p-4 sm:p-8 mb-6 sm:mb-10 relative overflow-hidden">
                {/* Subtle background waves */}
                <div className="absolute inset-0 overflow-hidden pointer-events-none">
                  <svg className="absolute inset-0 w-full h-full opacity-5" viewBox="0 0 100 100" preserveAspectRatio="none">
                    <path 
                      d="M0,50 Q20,45 40,50 T80,55 T120,50" 
                      fill="none" 
                      stroke="#f97316" 
                      strokeWidth="1"
                    />
                    <path 
                      d="M0,60 Q25,55 50,60 T100,55" 
                      fill="none" 
                      stroke="#fb923c"
                      strokeWidth="1"
                    />
                  </svg>
                </div>
                
                <div className="flex flex-col space-y-4 sm:space-y-6">
                  <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
                    <div>
                      <h2 className="text-xl sm:text-3xl font-bold mb-1 sm:mb-2">
                        Mining Status: <span className="text-orange-600">COOLDOWN</span>
                      </h2>
                      <p className="text-sm sm:text-lg text-gray-300">
                        Mining cooldown active. Please wait before mining again.
                      </p>
                      
                      {/* Add last mining reward info */}
                      {miningRewardInfo.actual > 0 && (
                        <div className="mt-1 sm:mt-2 text-indigo-600 text-sm sm:text-base font-medium">
                          Last mining session: <span className="text-indigo-700 font-bold">{formatCRN(miningRewardInfo.actual)}</span> CRN mined
                          <span className="ml-1 sm:ml-2 text-xs sm:text-sm text-gray-500">({miningRewardInfo.conditions} conditions)</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex flex-col sm:flex-row">
                    {/* Left side - Clock icon */}
                    <div className="w-full sm:w-1/3 flex justify-center items-center mb-4 sm:mb-0">
                      <div className="relative w-28 h-28 sm:w-40 sm:h-40">
                        {/* Background ring */}
                        <div className="absolute inset-0 rounded-full bg-orange-100 opacity-60"></div>
                        
                        {/* Clock icon in center */}
                        <div className="absolute inset-0 flex items-center justify-center">
                          <div className="relative z-10 w-20 h-20 sm:w-32 sm:h-32 rounded-full bg-orange-200 flex items-center justify-center border-4 border-orange-300">
                            <Clock size={36} className="text-orange-600" />
                          </div>
                          
                          {/* Accent rings */}
                          <div className="absolute inset-0 rounded-full border-4 border-orange-200 opacity-50"></div>
                          <div className="absolute inset-2 rounded-full border-2 border-orange-300 opacity-30"></div>
                        </div>
                      </div>
                    </div>

                    {/* Right side - Cooldown Info */}
                    <div className="w-full sm:w-2/3 sm:ml-8">
                      <div className="bg-gray-700/80 backdrop-blur-sm rounded-xl p-4 sm:p-6 shadow-md border border-gray-600">
                        {/* Cooldown details */}
                        <div className="mb-4 sm:mb-6">
                          <p className="text-gray-300 text-xs sm:text-sm font-medium mb-1">Next Available Mining</p>
                          <p className="text-orange-700 mb-3 sm:mb-4">
                            <span className="text-lg sm:text-xl font-mono font-bold">
                              {formatTimeLeft(hoursRemaining)}
                            </span>
                          </p>
                          
                          <div className="w-full bg-gray-600 rounded-full h-2 sm:h-2.5">
                            <div 
                              className="bg-orange-500 h-2 sm:h-2.5 rounded-full"
                              style={{ 
                                width: `${100 - Math.min(100, (hoursRemaining.hours * 60 + hoursRemaining.minutes) / (miningStatus?.mining_session_hours * 60) * 100)}%` 
                              }}
                            ></div>
                          </div>
                        </div>
                        
                        <div className="flex justify-between text-xs sm:text-sm text-gray-300 mb-3 sm:mb-6">
                          <span>Cooldown Period: {miningStatus?.mining_session_hours || 1} hour{miningStatus?.mining_session_hours !== 1 ? 's' : ''}</span>
                        </div>
                        
                        {/* Notification */}
                        <div className="flex items-center gap-2 sm:gap-3 p-3 sm:p-4 rounded-lg bg-orange-900 text-orange-300 mb-2">
                          <AlertTriangle size={16} className="text-orange-500" />
                          <p className="text-xs sm:text-sm">
                            <span className="font-medium">NOTE:</span> Mining is limited to once every {miningStatus?.mining_session_hours || 1} hour{miningStatus?.mining_session_hours !== 1 ? 's' : ''}.
                          </p>
                        </div>
                      </div>

                      {/* Cooldown Button */}
                      <div className="mt-4 sm:mt-6 flex justify-center">
                        <button
                          disabled
                          className="px-4 sm:px-8 py-3 sm:py-4 rounded-xl w-full bg-gray-400 text-white text-sm sm:text-base font-medium flex items-center justify-center gap-2 sm:gap-3 opacity-90 cursor-not-allowed shadow-md"
                        >
                          <Clock size={18} />
                          <span>Mining Cooldown</span>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Mining Success State with dark theme */}
            {miningComplete && !isMining && showSuccessScreen && (
              <div className="bg-gray-800 rounded-3xl border border-green-700 shadow-xl p-4 sm:p-8 mb-6 sm:mb-10 relative overflow-hidden">
                {/* Subtle background waves */}
                <div className="absolute inset-0 overflow-hidden pointer-events-none">
                  <svg className="absolute inset-0 w-full h-full opacity-5" viewBox="0 0 100 100" preserveAspectRatio="none">
                    <path 
                      d="M0,50 Q20,45 40,50 T80,55 T120,50" 
                      fill="none" 
                      stroke="#10b981" 
                      strokeWidth="1"
                    />
                    <path 
                      d="M0,60 Q25,55 50,60 T100,55" 
                      fill="none" 
                      stroke="#059669"
                      strokeWidth="1"
                    />
                  </svg>
                </div>
                
                <div className="flex flex-col space-y-4 sm:space-y-6">
                  <div>
                    <h2 className="text-xl sm:text-3xl font-bold mb-1 sm:mb-2">
                      Mining Status: <span className="text-green-600">COMPLETED</span>
                    </h2>
                    <p className="text-sm sm:text-lg text-gray-300">
                      Mining complete! You've successfully mined CRN.
                    </p>
                  </div>

                  <div className="flex flex-col sm:flex-row">
                    {/* Left side - Success icon */}
                    <div className="w-full sm:w-1/3 flex justify-center items-center mb-4 sm:mb-0">
                      <div className="relative w-28 h-28 sm:w-40 sm:h-40">
                        {/* Success icon in center with green circle */}
                        <div className="w-full h-full rounded-full bg-green-100/40 flex items-center justify-center">
                          <div className="w-3/4 h-3/4 rounded-full bg-green-500 flex items-center justify-center">
                            <Check size={36} className="text-white" />
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    {/* Right side - Success Info */}
                    <div className="w-full sm:w-2/3 sm:ml-8">
                      <div className="bg-green-900/80 rounded-xl p-4 sm:p-6 shadow-md border border-green-800">
                        {/* Mining Reward Earned */}
                        <div className="flex flex-col mb-3 sm:mb-4">
                          <p className="text-green-300 font-medium text-base sm:text-lg mb-1">
                            Mining Reward Earned
                          </p>
                          <div className="flex flex-wrap items-baseline gap-1">
                            <h2 className="text-xl sm:text-3xl font-bold text-green-400">
                              {formatCRNInteger(miningRewardInfo.actual)}
                            </h2>
                            <span className="text-gray-300 text-sm sm:text-xl">CRN</span>
                          </div>
                          <p className="text-xs sm:text-sm text-gray-300 mt-1">
                            Full value: {formatCRN(miningRewardInfo.actual)} CRN
                          </p>
                        </div>
                        
                        {/* Mining conditions indicator */}
                        <div className="flex items-center mb-3 sm:mb-4">
                          <p className="text-red-400 text-xs sm:text-sm font-medium mr-3">
                            Mining conditions were {miningRewardInfo.conditions}
                          </p>
                          <div className="text-xs bg-gray-700 px-2 py-1 rounded text-gray-300">
                            Network difficulty reduced yield
                          </div>
                        </div>
                        
                        
                        {/* Success message */}
                        <div className="flex items-center gap-2 sm:gap-3 p-3 sm:p-4 rounded-lg bg-green-800 text-green-300">
                          <Check size={18} className="text-green-500 flex-shrink-0" />
                          <p className="text-xs sm:text-sm">
                            <span className="font-medium">SUCCESS:</span> Your mining rewards have been deposited into your wallet.
                          </p>
                        </div>
                      </div>

                      {/* Success Button */}
                      <div className="mt-4 sm:mt-6 flex justify-center">
                        <button
                          disabled
                          className="px-4 sm:px-8 py-3 sm:py-4 rounded-xl w-full bg-gradient-to-r from-green-500 to-emerald-600 cursor-not-allowed opacity-80 text-white text-base sm:text-lg font-medium flex items-center justify-center gap-2 sm:gap-3 shadow-lg"
                        >
                          <Check size={18} />
                          <span>Awesome!</span>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Mining Block state with dark theme */}
            {miningBlock && (
              <div className="bg-gray-800 rounded-3xl border border-orange-700 shadow-xl p-4 sm:p-8 mb-6 sm:mb-10 relative overflow-hidden">
                <div className="flex flex-col space-y-4 sm:space-y-6">
                  <div className="flex flex-col">
                    <h2 className="text-xl sm:text-3xl font-bold mb-1 sm:mb-2">
                      Mining Status: <span className="text-orange-600">BLOCKED</span>
                    </h2>
                    <p className="text-sm sm:text-lg text-gray-300">
                      Your mining access has been limited due to policy violations.
                    </p>
                  </div>

                  <div className="flex flex-col md:flex-row">
                    {/* Left side - Warning icon */}
                    <div className="w-full md:w-1/3 flex justify-center items-center mb-4 md:mb-0">
                      <div className="relative w-28 h-28 sm:w-40 sm:h-40">
                        {/* Background ring */}
                        <div className="absolute inset-0 rounded-full bg-orange-950/40 opacity-60"></div>
                        
                        {/* Warning icon in center */}
                        <div className="absolute inset-0 flex items-center justify-center">
                          <div className="relative z-10 w-24 h-24 sm:w-32 sm:h-32 rounded-full bg-orange-950/70 flex items-center justify-center border-4 border-orange-800/70">
                            <AlertTriangle size={40} className="text-orange-400" />
                          </div>
                          
                          {/* Accent rings */}
                          <div className="absolute inset-0 rounded-full border-4 border-orange-800/50 opacity-50"></div>
                          <div className="absolute inset-2 rounded-full border-2 border-orange-700/50 opacity-30"></div>
                        </div>
                      </div>
                    </div>
                    
                    {/* Right side - Block Info */}
                    <div className="w-full md:w-2/3 md:ml-6">
                      <div className="bg-gray-800/80 backdrop-blur-sm rounded-xl p-4 sm:p-6 shadow-md border border-gray-700">
                        {/* Block message */}
                        <div className="flex items-center gap-2 sm:gap-3 p-3 sm:p-4 rounded-lg bg-orange-950/70 text-orange-200 mb-4 sm:mb-6 border border-orange-800/50">
                          <AlertCircle size={18} className="text-orange-400 flex-shrink-0" />
                          <p className="text-xs sm:text-sm">
                            <span className="font-medium">NOTICE:</span> Your mining privileges have been limited due to violations of wallet policy.
                          </p>
                        </div>
                        
                        {/* Additional info */}
                        <div className="bg-gray-800/80 p-3 sm:p-4 rounded-lg border border-gray-700">
                          <h3 className="font-medium text-gray-200 mb-2">What does this mean?</h3>
                          <p className="text-xs sm:text-sm text-gray-300 mb-2">
                            You can still view mining statistics, but the mining function is temporarily unavailable to your account.
                          </p>
                          <p className="text-xs sm:text-sm text-gray-300">
                            If you believe this is an error, please contact support for assistance.
                          </p>
                        </div>
                      </div>

                      {/* Locked Button - IMPROVED STYLING */}
                      <div className="mt-4 sm:mt-6 flex justify-center">
                        <button
                          disabled
                          className="px-4 sm:px-8 py-3 sm:py-4 rounded-xl w-full bg-gray-800 text-gray-400 font-medium flex items-center justify-center gap-2 sm:gap-3 shadow-md relative border border-gray-700"
                        >
                          {/* Lock icon container with better positioning */}
                          <div className="bg-orange-950/70 h-6 w-6 sm:h-8 sm:w-8 rounded-full flex items-center justify-center mr-2 border border-orange-800/50">
                            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-orange-300">
                              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                              <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                            </svg>
                          </div>
                          <span className="text-sm sm:text-base">Mining Access Blocked</span>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
      
      {/* Global styles for animations */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.6; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.05); }
        }
        
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-10px); }
        }
        
        @keyframes float-particle {
          0% { transform: translate(0, 0); opacity: 1; }
          100% { transform: translate(-40px, 0); opacity: 0; }
        }
        
        @keyframes pulse-glow {
          0%, 100% { box-shadow: 0 0 15px rgba(251, 191, 36, 0.6); }
          50% { box-shadow: 0 0 30px rgba(251, 191, 36, 0.9); }
        }
        
        @keyframes pulse-subtle {
          0%, 100% { opacity: 0.9; }
          50% { opacity: 1; }
        }
        
        @keyframes pulse-slow {
          0%, 100% { opacity: 0.8; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.03); }
        }
        
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        
        @keyframes spin-slow-reverse {
          from { transform: rotate(360deg); }
          to { transform: rotate(0deg); }
        }
        
        @keyframes text-glow {
          0%, 100% { text-shadow: 0 0 8px rgba(255, 255, 255, 0.6); }
          50% { text-shadow: 0 0 16px rgba(255, 255, 255, 0.9), 0 0 30px rgba(251, 191, 36, 0.4); }
        }
        
        @keyframes flicker {
          0%, 100% { opacity: 1; }
          25% { opacity: 0.8; }
          50% { opacity: 0.6; }
          75% { opacity: 0.9; }
        }
        
        @keyframes gradient-x {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
        
        @keyframes hammer {
          0%, 100% { transform: rotate(0deg); }
          50% { transform: rotate(-30deg); }
        }
        
        @keyframes spin-reverse {
          from { transform: rotate(360deg); }
          to { transform: rotate(0deg); }
        }
        
        .animate-hammer {
          animation: hammer 2s ease-in-out infinite;
          transform-origin: bottom right;
        }
        
        .animate-spin-reverse {
          animation: spin-reverse 8s linear infinite;
        }
        
        .animate-fadeIn {
          animation: fadeInUp 0.5s ease-out forwards;
        }
        
        .animate-pulse-glow {
          animation: pulse-glow 2s ease-in-out infinite;
        }
        
        .animate-pulse-subtle {
          animation: pulse-subtle 2s ease-in-out infinite;
        }
        
        .animate-pulse-slow {
          animation: pulse-slow 3s ease-in-out infinite;
        }
        
        .animate-spin-slow {
          animation: spin-slow 6s linear infinite;
        }
        
        .animate-spin-slow-reverse {
          animation: spin-slow-reverse 6s linear infinite;
        }
        
        .animate-text-glow {
          animation: text-glow 2s ease-in-out infinite;
        }
        
        .animate-flicker {
          animation: flicker 2s ease-in-out infinite;
        }
        
        .animate-float-particle {
          animation: float-particle 6s ease-out infinite;
        }
        
        .animate-gradient-x {
          background-size: 200% 200%;
          animation: gradient-x 6s ease infinite;
        }
        
        .shadow-glow {
          box-shadow: 0 0 20px rgba(251, 191, 36, 0.7);
        }
        
        .shadow-amber-glow {
          box-shadow: 0 0 15px rgba(251, 191, 36, 0.6);
        }
        
        /* Additional animations */
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes shimmer {
          0% { background-position: -1000px 0; }
          100% { background-position: 1000px 0; }
        }
      `}</style>
      
      {/* 2FA Verification Modal */}
      <TwoFAVerificationModal
        isOpen={twoFA.showModal}
        onClose={handleTwoFAModalClose}
        onVerify={verify2FACode}
        error={twoFA.error}
        isVerifying={twoFA.isVerifying}
        require2FASetup={twoFA.require2FASetup}
      />
    </div>
  );
};

export default Mining;


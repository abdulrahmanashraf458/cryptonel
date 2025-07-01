import React, { useState, useEffect } from 'react';
import LandingLayout from '../components/LandingLayout';
import { Check, X, Zap, Shield, Repeat, Trophy, User, Clock, LifeBuoy, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';

const SubscriptionPage: React.FC = () => {
  const [isYearly, setIsYearly] = useState(false);
  
  useEffect(() => {
    return () => {
      const elements = document.querySelectorAll('.pricing-toggle, .pricing-card');
      elements.forEach(el => {
        const parent = el.parentNode;
        if (parent && parent.contains(el)) {
          parent.removeChild(el);
        }
      });
    };
  }, []);
  
  return (
    <LandingLayout>
      <div className="min-h-screen bg-gradient-to-b from-[#18181B] to-[#1F1F23] py-16 px-4 sm:px-6 lg:px-8">
        {/* Header Section */}
        <motion.div 
          className="text-center max-w-5xl mx-auto"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7 }}
        >
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold bg-gradient-to-r from-[#6C5DD3] to-[#8875FF] bg-clip-text text-transparent mb-6">
            Choose Your Plan
          </h1>
          <p className="text-lg text-gray-300 max-w-3xl mx-auto mb-12">
            Unlock premium features and elevate your experience with Clyne Premium. 
            Compare our plans and choose what works best for you.
          </p>
          
          {/* Pricing Toggle - Fixed Design */}
          <div className="flex justify-center items-center space-x-4 mb-16">
            <span className={`text-sm md:text-base ${!isYearly ? 'text-white font-medium' : 'text-gray-400'}`}>Monthly</span>
            <div 
              onClick={() => setIsYearly(!isYearly)}
              className="relative w-[70px] h-[36px] rounded-full cursor-pointer bg-[#6C5DD3] shadow-lg"
            >
              <div className="absolute inset-0 flex items-center justify-end pr-3 text-xs text-white font-medium pointer-events-none">
                <span></span>
              </div>
              <motion.div 
                className="absolute left-1 top-1 w-[28px] h-[28px] bg-white rounded-full shadow-md"
                animate={{ x: isYearly ? 34 : 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
              />
            </div>
            <span className={`text-sm md:text-base flex items-center ${isYearly ? 'text-white font-medium' : 'text-gray-400'}`}>
              Yearly <span className="ml-2 text-xs py-1 px-2 bg-[#6C5DD3]/30 text-[#8875FF] rounded-full font-medium">Save 20%</span>
            </span>
          </div>
        </motion.div>
        
        {/* Pricing Cards */}
        <div className="max-w-7xl mx-auto grid md:grid-cols-2 gap-8 lg:gap-12">
          {/* Standard Plan */}
          <motion.div 
            className="bg-[#1A1A1D] rounded-3xl overflow-hidden shadow-lg border border-gray-800"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1 }}
          >
            <div className="p-8">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-3xl font-bold text-white">Standard</h2>
                <span className="px-4 py-1 bg-gray-800 text-gray-300 text-sm rounded-full">Free</span>
              </div>
              <p className="text-gray-400 mb-6">Basic features for all users</p>
              
              <div className="mb-6 h-20">
                <motion.div
                  key="standard-price"
                  initial={false}
                  animate={{ scale: [0.9, 1], opacity: [0.8, 1] }}
                  transition={{ duration: 0.3 }}
                >
                  <div className="text-5xl font-bold text-white mb-2">$0</div>
                  <div className="text-gray-400">Forever free</div>
                </motion.div>
              </div>
              
              <button className="w-full py-4 px-6 bg-gray-700 text-white rounded-xl font-medium transition-transform hover:bg-gray-600 mb-8">
                Current Plan
              </button>
              
              <div className="space-y-4">
                <div className="flex items-start">
                  <Check className="h-5 w-5 text-green-500 mt-0.5 mr-3" />
                  <span className="text-white">Standard Transfers</span>
                </div>
                <div className="flex items-start">
                  <Check className="h-5 w-5 text-green-500 mt-0.5 mr-3" />
                  <span className="text-white">Basic Security Features</span>
                </div>
                <div className="flex items-start">
                  <Check className="h-5 w-5 text-green-500 mt-0.5 mr-3" />
                  <span className="text-white">Standard Leaderboard Access</span>
                </div>
                <div className="flex items-start">
                  <Check className="h-5 w-5 text-green-500 mt-0.5 mr-3" />
                  <span className="text-white">Community Support</span>
                </div>
              </div>
            </div>
          </motion.div>
          
          {/* Premium Plan */}
          <motion.div 
            className="bg-[#2D2A64] rounded-3xl overflow-hidden shadow-xl border border-[#6C5DD3]/30 relative"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.3 }}
          >
            {/* Popular badge */}
            <div className="absolute top-0 right-0">
              <div className="bg-[#8875FF] text-white text-xs font-bold px-4 py-1 rounded-bl-lg shadow-lg">
                POPULAR
              </div>
            </div>
            
            <div className="p-8">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center">
                  <h2 className="text-3xl font-bold text-white mr-2">Premium</h2>
                  <span className="text-sm text-[#8875FF] flex items-center">
                    <Sparkles className="h-4 w-4 mr-1" />
                    Premium
                  </span>
                </div>
                <Zap className="h-6 w-6 text-[#8875FF]" />
              </div>
              <p className="text-gray-300 mb-6">All features for crypto enthusiasts</p>
              
              <div className="mb-6 h-20">
                <motion.div
                  key={isYearly ? "yearly-price" : "monthly-price"}
                  initial={{ y: -20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.3 }}
                >
                  <div className="text-5xl font-bold text-white mb-2">
                    ${isYearly ? '40' : '5'}
                    <span className="text-lg font-normal text-gray-300">/{isYearly ? 'year' : 'month'}</span>
                  </div>
                  {isYearly && <div className="text-[#8875FF] text-sm">$3.33/month, billed annually</div>}
                </motion.div>
              </div>
              
              <button className="w-full py-4 px-6 bg-[#6C5DD3] text-white rounded-xl font-medium transition-transform hover:bg-[#5C4DC3] mb-8">
                Subscribe Now
              </button>
              
              <div className="grid grid-cols-1 gap-4">
                <h3 className="font-medium text-[#8875FF] flex items-center">
                  <Shield className="h-4 w-4 mr-2" />
                  Security Features
                </h3>
                <div className="flex items-start">
                  <Check className="h-5 w-5 text-green-500 mt-0.5 mr-3" />
                  <span className="text-white">Geo Lock</span>
                </div>
                <div className="flex items-start">
                  <Check className="h-5 w-5 text-green-500 mt-0.5 mr-3" />
                  <span className="text-white">IP Whitelist</span>
                </div>
                <div className="flex items-start">
                  <Check className="h-5 w-5 text-green-500 mt-0.5 mr-3" />
                  <span className="text-white">Time-Based Access</span>
                </div>
                
                <h3 className="font-medium text-[#8875FF] flex items-center mt-2">
                  <Repeat className="h-4 w-4 mr-2" />
                  Transfer & Backup Features
                </h3>
                <div className="flex items-start">
                  <Check className="h-5 w-5 text-green-500 mt-0.5 mr-3" />
                  <span className="text-white">0% Taxes</span>
                </div>
                <div className="flex items-start">
                  <Check className="h-5 w-5 text-green-500 mt-0.5 mr-3" />
                  <span className="text-white">No Cooldown on Transfers</span>
                </div>
                <div className="flex items-start">
                  <Check className="h-5 w-5 text-green-500 mt-0.5 mr-3" />
                  <span className="text-white">No Cooldown on Backups</span>
                </div>
                <div className="flex items-start">
                  <Check className="h-5 w-5 text-green-500 mt-0.5 mr-3" />
                  <span className="text-white">No Per-Transaction Limit</span>
                </div>
                <div className="flex items-start">
                  <Check className="h-5 w-5 text-green-500 mt-0.5 mr-3" />
                  <span className="text-white">Quick Transfers</span>
                </div>
                
                <h3 className="font-medium text-[#8875FF] flex items-center mt-2">
                  <Trophy className="h-4 w-4 mr-2" />
                  Leaderboard Features
                </h3>
                <div className="flex items-start">
                  <Check className="h-5 w-5 text-green-500 mt-0.5 mr-3" />
                  <span className="text-white">Special Frame on Leaderboard</span>
                </div>
                <div className="flex items-start">
                  <Check className="h-5 w-5 text-green-500 mt-0.5 mr-3" />
                  <span className="text-white">Full Control over Leaderboard Privacy & Colors</span>
                </div>
                
                <h3 className="font-medium text-[#8875FF] flex items-center mt-2">
                  <User className="h-4 w-4 mr-2" />
                  Customization
                </h3>
                <div className="flex items-start">
                  <Check className="h-5 w-5 text-green-500 mt-0.5 mr-3" />
                  <span className="text-white">Custom Private Address</span>
                </div>
                <div className="flex items-start">
                  <Check className="h-5 w-5 text-green-500 mt-0.5 mr-3" />
                  <span className="text-white">Premium Badge</span>
                </div>
                <div className="flex items-start">
                  <Check className="h-5 w-5 text-green-500 mt-0.5 mr-3" />
                  <span className="text-white">Premium Discord Role</span>
                </div>
                <div className="flex items-start">
                  <Check className="h-5 w-5 text-green-500 mt-0.5 mr-3" />
                  <span className="text-white">Early Access to New Features</span>
                </div>
                
                <h3 className="font-medium text-[#8875FF] flex items-center mt-2">
                  <LifeBuoy className="h-4 w-4 mr-2" />
                  Support
                </h3>
                <div className="flex items-start">
                  <Check className="h-5 w-5 text-green-500 mt-0.5 mr-3" />
                  <span className="text-white">24/7 Technical Support</span>
                </div>
                <div className="flex items-start">
                  <Check className="h-5 w-5 text-green-500 mt-0.5 mr-3" />
                  <span className="text-white">Private Premium Discord Channel</span>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
        
        {/* Features Comparison Table */}
        <motion.div 
          className="max-w-5xl mx-auto mt-24 overflow-hidden rounded-2xl shadow-lg bg-[#1A1A1D]/80 backdrop-blur-sm border border-gray-800"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.5 }}
        >
          <div className="text-center p-8 border-b border-gray-800">
            <h2 className="text-2xl md:text-3xl font-bold text-white mb-2">Detailed Features Comparison</h2>
            <p className="text-gray-400">See exactly what you get with each plan</p>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-[#2A2A2D]">
                  <th className="p-4 text-left text-gray-300 font-medium">Feature</th>
                  <th className="p-4 text-center text-gray-300 font-medium">Standard</th>
                  <th className="p-4 text-center text-gray-300 font-medium">Premium</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {/* Security Features */}
                <tr>
                  <td colSpan={3} className="p-4 font-semibold text-[#8875FF] bg-[#2D2A64]/20">Security Features</td>
                </tr>
                <tr className="hover:bg-[#2A2A2D]/30">
                  <td className="p-4 text-gray-300">Geo Lock</td>
                  <td className="p-4 text-center">
                    <X className="h-5 w-5 text-red-500 mx-auto" />
                  </td>
                  <td className="p-4 text-center">
                    <Check className="h-5 w-5 text-green-500 mx-auto" />
                  </td>
                </tr>
                <tr className="hover:bg-[#2A2A2D]/30">
                  <td className="p-4 text-gray-300">IP Whitelist</td>
                  <td className="p-4 text-center">
                    <X className="h-5 w-5 text-red-500 mx-auto" />
                  </td>
                  <td className="p-4 text-center">
                    <Check className="h-5 w-5 text-green-500 mx-auto" />
                  </td>
                </tr>
                <tr className="hover:bg-[#2A2A2D]/30">
                  <td className="p-4 text-gray-300">Time-Based Access</td>
                  <td className="p-4 text-center">
                    <X className="h-5 w-5 text-red-500 mx-auto" />
                  </td>
                  <td className="p-4 text-center">
                    <Check className="h-5 w-5 text-green-500 mx-auto" />
                  </td>
                </tr>
                
                {/* Transfer & Backup Features */}
                <tr>
                  <td colSpan={3} className="p-4 font-semibold text-[#8875FF] bg-[#2D2A64]/20">Transfer & Backup Features</td>
                </tr>
                <tr className="hover:bg-[#2A2A2D]/30">
                  <td className="p-4 text-gray-300">Transaction Taxes</td>
                  <td className="p-4 text-center text-gray-300">1%</td>
                  <td className="p-4 text-center text-green-500 font-medium">0%</td>
                </tr>
                <tr className="hover:bg-[#2A2A2D]/30">
                  <td className="p-4 text-gray-300">Cooldown on Transfers</td>
                  <td className="p-4 text-center text-gray-300">Yes (1 min)</td>
                  <td className="p-4 text-center text-green-500 font-medium">Unlimited</td>
                </tr>
                <tr className="hover:bg-[#2A2A2D]/30">
                  <td className="p-4 text-gray-300">Cooldown on Backups</td>
                  <td className="p-4 text-center text-gray-300">Yes (14 days)</td>
                  <td className="p-4 text-center text-green-500 font-medium">Unlimited</td>
                </tr>
                <tr className="hover:bg-[#2A2A2D]/30">
                  <td className="p-4 text-gray-300">Per-Transaction Limit</td>
                  <td className="p-4 text-center text-gray-300">Yes</td>
                  <td className="p-4 text-center text-green-500 font-medium">Unlimited</td>
                </tr>
                <tr className="hover:bg-[#2A2A2D]/30">
                  <td className="p-4 text-gray-300">Quick Transfers</td>
                  <td className="p-4 text-center">
                    <X className="h-5 w-5 text-red-500 mx-auto" />
                  </td>
                  <td className="p-4 text-center">
                    <Check className="h-5 w-5 text-green-500 mx-auto" />
                  </td>
                </tr>
                
                {/* Leaderboard Features */}
                <tr>
                  <td colSpan={3} className="p-4 font-semibold text-[#8875FF] bg-[#2D2A64]/20">Leaderboard Features</td>
                </tr>
                <tr className="hover:bg-[#2A2A2D]/30">
                  <td className="p-4 text-gray-300">Special Frame on Leaderboard</td>
                  <td className="p-4 text-center">
                    <X className="h-5 w-5 text-red-500 mx-auto" />
                  </td>
                  <td className="p-4 text-center">
                    <Check className="h-5 w-5 text-green-500 mx-auto" />
                  </td>
                </tr>
                <tr className="hover:bg-[#2A2A2D]/30">
                  <td className="p-4 text-gray-300">Leaderboard Privacy Controls</td>
                  <td className="p-4 text-center text-gray-300">Basic</td>
                  <td className="p-4 text-center text-green-500 font-medium">Full</td>
                </tr>
                <tr className="hover:bg-[#2A2A2D]/30">
                  <td className="p-4 text-gray-300">Custom Card Colors</td>
                  <td className="p-4 text-center">
                    <X className="h-5 w-5 text-red-500 mx-auto" />
                  </td>
                  <td className="p-4 text-center">
                    <Check className="h-5 w-5 text-green-500 mx-auto" />
                  </td>
                </tr>
                
                {/* Customization */}
                <tr>
                  <td colSpan={3} className="p-4 font-semibold text-[#8875FF] bg-[#2D2A64]/20">Customization</td>
                </tr>
                <tr className="hover:bg-[#2A2A2D]/30">
                  <td className="p-4 text-gray-300">Custom Private Address</td>
                  <td className="p-4 text-center">
                    <X className="h-5 w-5 text-red-500 mx-auto" />
                  </td>
                  <td className="p-4 text-center">
                    <Check className="h-5 w-5 text-green-500 mx-auto" />
                  </td>
                </tr>
                <tr className="hover:bg-[#2A2A2D]/30">
                  <td className="p-4 text-gray-300">Premium Badge</td>
                  <td className="p-4 text-center">
                    <X className="h-5 w-5 text-red-500 mx-auto" />
                  </td>
                  <td className="p-4 text-center">
                    <Check className="h-5 w-5 text-green-500 mx-auto" />
                  </td>
                </tr>
                <tr className="hover:bg-[#2A2A2D]/30">
                  <td className="p-4 text-gray-300">Premium Discord Role</td>
                  <td className="p-4 text-center">
                    <X className="h-5 w-5 text-red-500 mx-auto" />
                  </td>
                  <td className="p-4 text-center">
                    <Check className="h-5 w-5 text-green-500 mx-auto" />
                  </td>
                </tr>
                <tr className="hover:bg-[#2A2A2D]/30">
                  <td className="p-4 text-gray-300">Early Access to New Features</td>
                  <td className="p-4 text-center">
                    <X className="h-5 w-5 text-red-500 mx-auto" />
                  </td>
                  <td className="p-4 text-center">
                    <Check className="h-5 w-5 text-green-500 mx-auto" />
                  </td>
                </tr>
                
                {/* Support */}
                <tr>
                  <td colSpan={3} className="p-4 font-semibold text-[#8875FF] bg-[#2D2A64]/20">Support</td>
                </tr>
                <tr className="hover:bg-[#2A2A2D]/30">
                  <td className="p-4 text-gray-300">Technical Support</td>
                  <td className="p-4 text-center text-gray-300">Community</td>
                  <td className="p-4 text-center text-green-500 font-medium">24/7 Dedicated</td>
                </tr>
                <tr className="hover:bg-[#2A2A2D]/30">
                  <td className="p-4 text-gray-300">Private Premium Discord Channel</td>
                  <td className="p-4 text-center">
                    <X className="h-5 w-5 text-red-500 mx-auto" />
                  </td>
                  <td className="p-4 text-center">
                    <Check className="h-5 w-5 text-green-500 mx-auto" />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </motion.div>
      </div>
    </LandingLayout>
  );
};

export default SubscriptionPage; 
import React, { useState, useEffect } from "react";
import { Activity, Zap } from "lucide-react";

interface TransactionStatsProps {
  totalTransactions: number;
}

const TransactionStats: React.FC<TransactionStatsProps> = ({ 
  totalTransactions 
}) => {
  const [animatedTotal, setAnimatedTotal] = useState(0);

  // Animate transaction count on change
  useEffect(() => {
    // Don't animate on first render (0 -> value)
    if (animatedTotal === 0 && totalTransactions > 0) {
      setAnimatedTotal(totalTransactions);
      return;
    }

    // Calculate step size based on difference magnitude
    const diff = totalTransactions - animatedTotal;
    if (diff <= 0) {
      setAnimatedTotal(totalTransactions);
      return;
    }

    // Animate counting upward
    const animationDuration = 1500; // ms
    const frameDuration = 16; // ms per frame (approx 60fps)
    const totalFrames = Math.round(animationDuration / frameDuration);
    const step = Math.ceil(diff / totalFrames);

    let currentFrame = 0;
    const counter = setInterval(() => {
      currentFrame++;
      setAnimatedTotal(prev => {
        const next = prev + step;
        if (next >= totalTransactions || currentFrame >= totalFrames) {
          clearInterval(counter);
          return totalTransactions;
        }
        return next;
      });

      if (currentFrame >= totalFrames) {
        clearInterval(counter);
      }
    }, frameDuration);

    return () => clearInterval(counter);
  }, [totalTransactions]);

  // Format large numbers with commas
  const formatNumber = (num: number): string => {
    return num.toLocaleString();
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-10">
      {/* Total Transactions Stat */}
      <div className="bg-gradient-to-br from-[#2A2A2D] to-[#262626] rounded-xl p-6 shadow-lg border border-[#3A3A3D]/30 hover:border-[#6C5DD3]/50 transition-all duration-300">
        <div className="flex items-center gap-4">
          <div className="bg-[#6C5DD3]/20 p-3 rounded-lg">
            <Activity className="h-6 w-6 text-[#6C5DD3]" />
          </div>
          <div>
            <p className="text-sm text-[#A1A1AA] font-medium">Total Transactions</p>
            <h3 className="text-2xl font-bold text-white tracking-tight">
              {formatNumber(animatedTotal)}
            </h3>
          </div>
        </div>
      </div>

      {/* Network Status */}
      <div className="bg-gradient-to-br from-[#2A2A2D] to-[#262626] rounded-xl p-6 shadow-lg border border-[#3A3A3D]/30 hover:border-[#22C55E]/50 transition-all duration-300">
        <div className="flex items-center gap-4">
          <div className="bg-[#22C55E]/20 p-3 rounded-lg">
            <Zap className="h-6 w-6 text-[#22C55E]" />
          </div>
          <div>
            <p className="text-sm text-[#A1A1AA] font-medium">Network Status</p>
            <h3 className="text-2xl font-bold text-white tracking-tight flex items-center">
              <span className="inline-block w-2 h-2 rounded-full bg-[#22C55E] mr-2 animate-pulse"></span>
              Active
            </h3>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TransactionStats; 
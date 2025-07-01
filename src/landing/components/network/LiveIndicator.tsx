import React, { useState, useEffect } from "react";
import { Radio, AlertCircle } from "lucide-react";

interface LiveIndicatorProps {
  active: boolean;
}

const LiveIndicator: React.FC<LiveIndicatorProps> = ({ active }) => {
  const [isVisible, setIsVisible] = useState(true);
  const [animationClass, setAnimationClass] = useState("");
  
  // Effect to handle entrance animation when active state changes
  useEffect(() => {
    if (active) {
      setAnimationClass("animate-bounce");
      // Remove animation after 1 second
      const timeout = setTimeout(() => {
        setAnimationClass("");
      }, 1000);
      return () => clearTimeout(timeout);
    }
  }, [active]);
  
  // Effect to make the indicator pulse every few seconds when idle
  useEffect(() => {
    if (!active) {
      const interval = setInterval(() => {
        setIsVisible(false);
        setTimeout(() => setIsVisible(true), 200);
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [active]);
  
  return (
    <div 
      className={`inline-flex items-center gap-2 px-4 py-2 rounded-full 
      ${active 
        ? 'bg-[#22C55E]/20 text-[#22C55E] shadow-lg shadow-[#22C55E]/20' 
        : 'bg-[#6C5DD3]/20 text-[#6C5DD3]'}
      transition-all duration-500 ${animationClass}`}
    >
      {active ? (
        <AlertCircle className="h-4 w-4 animate-pulse" />
      ) : (
        <Radio className={`h-4 w-4 ${isVisible ? 'opacity-100' : 'opacity-30'} transition-opacity`} />
      )}
      <span className="text-xs font-semibold tracking-wide uppercase">
        {active ? 'New Transaction' : 'Live Updates'}
      </span>
    </div>
  );
};

export default LiveIndicator; 
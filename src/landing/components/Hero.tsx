import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";

const Hero = () => {
  useEffect(() => {
    // Animation for floating devices
    const animateDevices = () => {
      const devices = document.querySelectorAll('.floating-device');
      devices.forEach((device, index) => {
        const element = device as HTMLElement;
        const randomDelay = 2 + Math.random() * 3;
        const randomDuration = 15 + Math.random() * 10;
        
        element.style.animationDelay = `${randomDelay}s`;
        element.style.animationDuration = `${randomDuration}s`;
      });
    };
    
    animateDevices();
    
    // Text reveal animation
    const revealText = () => {
      const elements = document.querySelectorAll('.reveal-text');
      elements.forEach((element, index) => {
        setTimeout(() => {
          (element as HTMLElement).style.opacity = '1';
          (element as HTMLElement).style.transform = 'translateY(0)';
        }, 300 + (index * 200));
      });
    };
    
    revealText();
  }, []);

  // Function to handle Discord Add Bot click
  const handleAddBot = () => {
    window.open('https://discord.com/oauth2/authorize?client_id=1339264170226356286&permissions=8&integration_type=0&scope=bot', '_blank');
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-black">
      {/* Grid pattern background */}
      <div className="absolute inset-0 z-0">
        <div 
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: `
              linear-gradient(to right, rgba(108, 93, 211, 0.2) 1px, transparent 1px),
              linear-gradient(to bottom, rgba(108, 93, 211, 0.2) 1px, transparent 1px)
            `,
            backgroundSize: '80px 80px',
          }}
        ></div>
        
        {/* Subtle gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-tr from-black via-[#161616] to-black opacity-80"></div>
      </div>
      
      {/* Floating devices */}
      <div className="absolute inset-0 z-0 overflow-hidden">
        <div className="floating-device absolute w-[280px] h-[560px] rounded-[40px] bg-[#1A1A1A] right-[15%] top-[15%] shadow-xl transform rotate-12 animate-float-slow"></div>
        <div className="floating-device absolute w-[240px] h-[480px] rounded-[36px] bg-[#222222] right-[30%] bottom-[15%] shadow-xl transform rotate-6 animate-float-slow"></div>
        <div className="floating-device absolute w-[200px] h-[400px] rounded-[32px] bg-[#262626] right-[5%] bottom-[25%] shadow-xl transform rotate-[20deg] animate-float-slow"></div>
        <div className="floating-device absolute w-[180px] h-[360px] rounded-[28px] bg-[#1A1A1A] right-[40%] top-[20%] shadow-xl transform rotate-[15deg] animate-float-slow"></div>
      </div>
      
      {/* Content */}
      <div className="relative z-10 container mx-auto px-6 py-32 md:py-40 lg:py-48 max-w-7xl">
        <div className="max-w-3xl">
          <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold text-white mb-6 leading-tight reveal-text opacity-0 transform translate-y-6 transition-all duration-700">
            We leverage a <span className="bg-gradient-to-r from-[#6C5DD3] to-[#8875FF] bg-clip-text text-transparent">CRN based</span> system to solve major challenges users face
          </h1>
          
          <p className="text-lg md:text-xl text-[#A1A1AA] mb-12 max-w-2xl leading-relaxed reveal-text opacity-0 transform translate-y-6 transition-all duration-700 delay-200">
            We're developing innovative solutions that redefine the way people interact
          </p>
          
          <div className="flex space-x-6 reveal-text opacity-0 transform translate-y-6 transition-all duration-700 delay-400">
            <Link
              to="/dashboard"
              className="bg-white/10 backdrop-blur-lg text-white border border-white/20 py-4 px-8 rounded-full transition-all duration-300 flex items-center justify-center font-medium text-lg shadow-lg hover:bg-white/20 hover:border-white/30 hover:translate-y-[-2px] group"
            >
              Dashboard 
              <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
            
            <button
              onClick={handleAddBot}
              className="bg-[#6C5DD3]/30 backdrop-blur-lg text-white border border-[#6C5DD3]/40 py-4 px-8 rounded-full transition-all duration-300 flex items-center justify-center font-medium text-lg shadow-lg hover:bg-[#6C5DD3]/40 hover:border-[#6C5DD3]/60 hover:translate-y-[-2px] group"
            >
              Add Bot
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Hero; 
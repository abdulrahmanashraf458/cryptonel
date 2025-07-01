import React, { useEffect, useState, useRef } from "react";
import { Shield, RefreshCw, Zap, Layout, Globe, Lock } from "lucide-react";

const Features = () => {
  const [activeFeature, setActiveFeature] = useState(0);
  const [autoRotate, setAutoRotate] = useState(true);
  const autoRotateTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Parallax effect for background elements
    const handleMouseMove = (e: MouseEvent) => {
      const parallaxElements = document.querySelectorAll('.parallax-element');
      const x = (e.clientX / window.innerWidth) - 0.5;
      const y = (e.clientY / window.innerHeight) - 0.5;
      
      parallaxElements.forEach(el => {
        const element = el as HTMLElement;
        const speed = element.getAttribute('data-speed') || '20';
        const moveX = parseFloat(speed) * x;
        const moveY = parseFloat(speed) * y;
        element.style.transform = `translate(${moveX}px, ${moveY}px)`;
      });
    };
    
    // Animated line drawing effect
    const animateLineDrawing = () => {
      const paths = document.querySelectorAll('.path-animate');
      paths.forEach((path) => {
        const pathElement = path as SVGPathElement;
        const length = pathElement.getTotalLength();
        
        pathElement.style.strokeDasharray = length.toString();
        pathElement.style.strokeDashoffset = length.toString();
        
        setTimeout(() => {
          pathElement.style.transition = 'stroke-dashoffset 1.5s ease-in-out';
          pathElement.style.strokeDashoffset = '0';
        }, 300);
      });
    };

    // Animation for feature cards
    const animateFeatures = () => {
      const features = document.querySelectorAll('.feature-item');
      features.forEach((feature, index) => {
        const element = feature as HTMLElement;
        setTimeout(() => {
          element.style.opacity = '1';
          element.style.transform = 'translateY(0)';
        }, 200 + (index * 150));
      });
    };

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
    
    // Initialize animations
    setTimeout(() => {
      animateFeatures();
      animateLineDrawing();
      revealText();
    }, 100);
    
    window.addEventListener('mousemove', handleMouseMove);
    
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      if (autoRotateTimeoutRef.current) {
        clearTimeout(autoRotateTimeoutRef.current);
      }
    };
  }, []);

  // Effect for feature rotation that respects the autoRotate state
  useEffect(() => {
    if (!autoRotate) return;
    
    const rotateFeature = () => {
      setActiveFeature((prev) => (prev + 1) % 6);
    };
    
    autoRotateTimeoutRef.current = setTimeout(rotateFeature, 5000);
    
    return () => {
      if (autoRotateTimeoutRef.current) {
        clearTimeout(autoRotateTimeoutRef.current);
      }
    };
  }, [activeFeature, autoRotate]);

  // Reset auto-rotation after user inactivity
  useEffect(() => {
    const resetAutoRotate = () => {
      setAutoRotate(true);
    };
    
    // Reset auto-rotation after 15 seconds of inactivity
    const inactivityTimeout = setTimeout(resetAutoRotate, 15000);
    
    return () => {
      clearTimeout(inactivityTimeout);
    };
  }, [activeFeature]);

  const features = [
    {
      icon: Shield,
      title: "Multi-layer Security",
      description: "Advanced encryption and two-factor authentication ensure your assets are always protected",
      benefits: ["Two-factor authentication", "Anti-hack protection", "Instant security alerts"],
      color: "#6C5DD3"
    },
    {
      icon: RefreshCw,
      title: "Real-time Transactions",
      description: "Send and receive CRN instantly with live status updates and smart notifications",
      benefits: ["Instant transfers", "Live transaction tracking", "Transaction history"],
      color: "#5B8BF9"
    },
    {
      icon: Zap,
      title: "Optimized Performance",
      description: "Enjoy fast, reliable performance even during peak times",
      benefits: ["Quick execution", "Stable infrastructure", "Ongoing maintenance and upgrades"],
      color: "#8A77FF"
    },
    {
      icon: Layout,
      title: "User-Friendly Design",
      description: "Simple and intuitive interface that makes everything easy to use",
      benefits: ["Clean UI", "Streamlined process", "Built-in support features"],
      color: "#7A4BFF"
    },
    {
      icon: Globe,
      title: "Global Accessibility",
      description: "Access your wallet anytime, anywhere, on any device",
      benefits: ["Works on all platforms", "24/7 access", "Seamless device sync"],
      color: "#6C5DD3"
    },
    {
      icon: Lock,
      title: "Privacy Protection",
      description: "We keep your data safe and your activity private with strong encryption and smart privacy features",
      benefits: ["End-to-end encryption", "Secure transactions", "Minimal data collection"],
      color: "#4F46E5"
    }
  ];

  // Helper function for feature selection
  const handleFeatureClick = (index: number) => {
    // Pause auto-rotation when user clicks
    setAutoRotate(false);
    setActiveFeature(index);
  };

  return (
    <div className="relative py-28 overflow-hidden bg-black">
      {/* Background elements */}
      <div className="absolute inset-0 z-0 overflow-hidden">
        {/* Grid pattern */}
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
        
        {/* Decorative circles */}
        <div className="parallax-element absolute top-[10%] right-[15%] w-[400px] h-[400px] rounded-full bg-[#6C5DD3]/5 blur-[100px]" data-speed="15"></div>
        <div className="parallax-element absolute top-[60%] left-[5%] w-[300px] h-[300px] rounded-full bg-[#8A77FF]/5 blur-[80px]" data-speed="25"></div>
        <div className="parallax-element absolute bottom-[15%] right-[25%] w-[250px] h-[250px] rounded-full bg-[#4F46E5]/5 blur-[70px]" data-speed="10"></div>
        
        {/* Diagonal line */}
        <div className="absolute inset-0 overflow-hidden">
          <svg className="absolute h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none">
            <path 
              d="M-10,110 L110,-10" 
              stroke="rgba(108, 93, 211, 0.1)" 
              strokeWidth="0.5" 
              fill="none"
              className="path-animate"
            />
            <path 
              d="M-10,90 L90,-10" 
              stroke="rgba(108, 93, 211, 0.07)" 
              strokeWidth="0.5" 
              fill="none" 
              className="path-animate"
            />
            <path 
              d="M-10,70 L70,-10" 
              stroke="rgba(108, 93, 211, 0.05)" 
              strokeWidth="0.5" 
              fill="none"
              className="path-animate"
            />
          </svg>
        </div>
        
        {/* Subtle gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-tr from-black via-[#161616] to-black opacity-80"></div>
      </div>

      {/* Main content */}
      <div className="relative z-10 container mx-auto px-6 max-w-7xl">
        {/* Header section with creative layout */}
        <div className="flex flex-col lg:flex-row items-center justify-between mb-20">
          <div className="lg:max-w-lg mb-10 lg:mb-0">
            <div className="inline-flex items-center mb-3 px-3 py-1 rounded-full bg-white/5 border border-[#6C5DD3]/20 backdrop-blur-sm">
              <span className="bg-gradient-to-r from-[#6C5DD3] to-[#8875FF] bg-clip-text text-transparent text-sm font-medium">Next Generation Features</span>
            </div>
            <h2 className="text-4xl md:text-5xl font-bold mb-6 reveal-text opacity-0 transform translate-y-6 transition-all duration-700">
              Designed For <span className="bg-gradient-to-r from-[#6C5DD3] to-[#8875FF] bg-clip-text text-transparent">Professional</span> Crypto Users
            </h2>
            
            <p className="text-lg text-[#A1A1AA] reveal-text opacity-0 transform translate-y-6 transition-all duration-700 delay-200">
              Our platform combines advanced technology with elegant design for an unrivaled crypto experience.
            </p>
          </div>
          
          <div className="lg:w-1/2 relative">
            <svg className="w-full max-w-sm mx-auto" viewBox="0 0 300 200">
              <defs>
                <linearGradient id="purpleGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#6C5DD3" stopOpacity="0.3" />
                  <stop offset="100%" stopColor="#8875FF" stopOpacity="0.1" />
                </linearGradient>
              </defs>
              
              {/* Animated network graph */}
              <g>
                {[...Array(5)].map((_, i) => (
                  <circle 
                    key={`node-${i}`} 
                    cx={80 + i * 40} 
                    cy={100 + (i % 2 === 0 ? -30 : 30)} 
                    r="8" 
                    fill="url(#purpleGradient)" 
                    stroke="#6C5DD3" 
                    strokeWidth="1" 
                    className="animate-pulse"
                    style={{ animationDelay: `${i * 0.2}s` }}
                  />
                ))}
                
                {[...Array(4)].map((_, i) => (
                  <line 
                    key={`edge-${i}`} 
                    x1={88 + i * 40} 
                    y1={100 + (i % 2 === 0 ? -30 : 30)} 
                    x2={120 + i * 40} 
                    y2={100 + (i % 2 === 0 ? 30 : -30)} 
                    stroke="#6C5DD3" 
                    strokeWidth="1" 
                    strokeDasharray="1,3"
                    className="path-animate"
                  />
                ))}
              </g>
            </svg>
          </div>
        </div>

        {/* Interactive feature selection */}
        <div className="flex flex-wrap gap-4 justify-center mb-20">
          {features.map((feature, index) => (
            <button
              key={index}
              onClick={() => handleFeatureClick(index)}
              className={`px-5 py-3 rounded-full text-sm font-medium transition-all duration-300 ${
                activeFeature === index
                  ? 'bg-white/10 border border-[#6C5DD3]/30 text-white shadow-lg shadow-[#6C5DD3]/20'
                  : 'bg-white/5 border border-white/5 text-[#A1A1AA] hover:bg-white/10'
              }`}
              aria-pressed={activeFeature === index}
              aria-label={`Select ${feature.title} feature`}
            >
              {feature.title}
            </button>
          ))}
        </div>
        
        {/* Featured highlight section with improved transitions */}
        <div className="mb-24 relative h-[500px]">
          {features.map((feature, index) => {
            const isActive = activeFeature === index;
            const direction = index > activeFeature ? 1 : -1;
            
            return (
              <div
                key={index}
                className={`absolute top-0 left-0 w-full transition-all duration-700 ${
                  isActive 
                    ? 'opacity-100 translate-x-0' 
                    : `opacity-0 pointer-events-none ${
                        direction > 0 ? 'translate-x-10' : 'translate-x-[-10px]'
                      }`
                }`}
                aria-hidden={!isActive}
              >
                <div className="relative">
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div 
                      className="w-[300px] h-[300px] rounded-full blur-[100px] transition-all duration-700" 
                      style={{ backgroundColor: `${feature.color}10` }}
                    ></div>
                  </div>
                  
                  <div className="flex flex-col md:flex-row items-center gap-10 p-10 rounded-2xl bg-white/5 backdrop-blur-sm border border-white/10 relative overflow-hidden">
                    {/* Feature icon */}
                    <div 
                      className="w-24 h-24 rounded-xl flex items-center justify-center relative"
                      style={{ background: `linear-gradient(135deg, ${feature.color}20, ${feature.color}05)` }}
                    >
                      <feature.icon size={40} className="text-white" />
                      <div className="absolute inset-0 border border-white/10 rounded-xl"></div>
                    </div>
                    
                    {/* Feature details */}
                    <div className="flex-1 text-center md:text-left">
                      <h3 className="text-2xl font-bold text-white mb-3">{feature.title}</h3>
                      <p className="text-[#A1A1AA] mb-6 text-lg">{feature.description}</p>
                      
                      <div className="flex flex-col gap-3">
                        {feature.benefits.map((benefit, i) => (
                          <div key={i} className="flex items-center">
                            <div className="w-1.5 h-1.5 rounded-full mr-3" style={{ backgroundColor: feature.color }}></div>
                            <span className="text-white text-lg">{benefit}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
      
      {/* Add CSS for animations */}
      <style>{`
        @keyframes pulse {
          0% { transform: scale(1); opacity: 0.8; }
          50% { transform: scale(1.05); opacity: 1; }
          100% { transform: scale(1); opacity: 0.8; }
        }
        .animate-pulse {
          animation: pulse 3s infinite ease-in-out;
        }
        
        @keyframes float {
          0% { transform: translateY(0px); }
          50% { transform: translateY(-10px); }
          100% { transform: translateY(0px); }
        }
        .animate-float {
          animation: float 5s infinite ease-in-out;
        }
      `}</style>
    </div>
  );
};

export default Features; 
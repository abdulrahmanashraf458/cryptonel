import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUp, Mail, Send } from "lucide-react";

const DiscordIcon = () => (
  <svg 
    xmlns="http://www.w3.org/2000/svg" 
    width="24" 
    height="24" 
    viewBox="0 0 127.14 96.36" 
    fill="currentColor"
    className="w-7 h-7"
  >
    <path d="M107.7,8.07A105.15,105.15,0,0,0,81.47,0a72.06,72.06,0,0,0-3.36,6.83A97.68,97.68,0,0,0,49,6.83,72.37,72.37,0,0,0,45.64,0,105.89,105.89,0,0,0,19.39,8.09C2.79,32.65-1.71,56.6.54,80.21h0A105.73,105.73,0,0,0,32.71,96.36,77.7,77.7,0,0,0,39.6,85.25a68.42,68.42,0,0,1-10.85-5.18c.91-.66,1.8-1.34,2.66-2a75.57,75.57,0,0,0,64.32,0c.87.71,1.76,1.39,2.66,2a68.68,68.68,0,0,1-10.87,5.19,77,77,0,0,0,6.89,11.1A105.25,105.25,0,0,0,126.6,80.22h0C129.24,52.84,122.09,29.11,107.7,8.07ZM42.45,65.69C36.18,65.69,31,60,31,53s5-12.74,11.43-12.74S54,46,53.89,53,48.84,65.69,42.45,65.69Zm42.24,0C78.41,65.69,73.25,60,73.25,53s5-12.74,11.44-12.74S96.23,46,96.12,53,91.08,65.69,84.69,65.69Z" />
  </svg>
);

const Footer = () => {
  const [email, setEmail] = useState("");
  
  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleSubscribe = (e: React.FormEvent) => {
    e.preventDefault();
    // Handle subscription logic
    alert(`Thank you for subscribing with: ${email}`);
    setEmail("");
  };

  return (
    <footer className="bg-gradient-to-b from-[#1A1A1A] to-[#262626] border-t border-[#2A2A2D]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Newsletter */}
        <div className="mb-16 pb-12 border-b border-[#2A2A2D]">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-2xl font-bold text-white mb-3">Stay Updated</h2>
            <p className="text-[#A1A1AA] mb-6">
              Subscribe to our newsletter for the latest updates, crypto news, and exclusive offers
            </p>
            <form onSubmit={handleSubscribe} className="flex flex-col sm:flex-row gap-3 w-full max-w-lg mx-auto">
              <div className="relative flex-grow">
                <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <input
                  type="email"
                  placeholder="Your email address"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full pl-10 pr-3 py-3 bg-[#1A1A1A] border border-[#3A3A3D] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#6C5DD3] text-white placeholder-gray-400"
                />
              </div>
              <button
                type="submit"
                className="bg-gradient-to-r from-[#6C5DD3] to-[#8875FF] hover:opacity-90 transition-all duration-300 text-white font-medium py-3 px-6 rounded-lg flex items-center justify-center"
              >
                Subscribe
                <Send className="w-4 h-4 ml-2" />
              </button>
            </form>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-10">
          {/* Logo and description */}
          <div className="md:col-span-5">
            <Link 
              to="/" 
              className="inline-flex items-center mb-6 group"
            >
              <span className="text-3xl font-bold bg-gradient-to-r from-[#6C5DD3] to-[#8875FF] bg-clip-text text-transparent group-hover:from-[#8875FF] group-hover:to-[#6C5DD3] transition-all duration-300">
                Clyne
              </span>
            </Link>
            <p className="text-[#A1A1AA] mb-8 text-lg leading-relaxed max-w-lg">
              The next generation cryptocurrency wallet with advanced security features
              and user-friendly interface for managing your digital assets.
            </p>
            <div className="flex flex-wrap gap-5">
              <a 
                href="https://discord.gg/clyne" 
                target="_blank" 
                rel="noopener noreferrer"
                aria-label="Discord"
                className="text-[#A1A1AA] hover:text-[#6C5DD3] transition-all duration-300 transform hover:scale-110"
              >
                <DiscordIcon />
              </a>
            </div>
          </div>

          {/* Quick links */}
          <div className="md:col-span-2">
            <h3 className="text-white font-bold text-lg mb-6">Quick Links</h3>
            <ul className="space-y-3">
              {[
                { name: "Home", path: "/" }
              ].map((link, index) => (
                <li key={index}>
                  <Link 
                    to={link.path} 
                    className="text-[#A1A1AA] hover:text-[#6C5DD3] transition-colors flex items-center group"
                  >
                    <span className="inline-block w-0 group-hover:w-2 transition-all duration-300 h-0.5 bg-[#6C5DD3] mr-0 group-hover:mr-2"></span>
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Products renamed to Information */}
          <div className="md:col-span-2">
            <h3 className="text-white font-bold text-lg mb-6">Information</h3>
            <ul className="space-y-3">
              {[
                { name: "Wallet", path: "/wallet" },
                { name: "Mining", path: "/mining-info" },
                { name: "Transfers", path: "/transfers" },
                { name: "Network Transactions", path: "/network-transactions" }
              ].map((link, index) => (
                <li key={index}>
                  <Link 
                    to={link.path} 
                    className="text-[#A1A1AA] hover:text-[#6C5DD3] transition-colors flex items-center group"
                  >
                    <span className="inline-block w-0 group-hover:w-2 transition-all duration-300 h-0.5 bg-[#6C5DD3] mr-0 group-hover:mr-2"></span>
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal */}
          <div className="md:col-span-3">
            <h3 className="text-white font-bold text-lg mb-6">Legal</h3>
            <ul className="space-y-3">
              {[
                { name: "Privacy Policy", path: "/privacy" },
                { name: "Terms of Service", path: "/terms" },
                { name: "Cookie Policy", path: "/cookies" }
              ].map((link, index) => (
                <li key={index}>
                  <Link 
                    to={link.path} 
                    className="text-[#A1A1AA] hover:text-[#6C5DD3] transition-colors flex items-center group"
                  >
                    <span className="inline-block w-0 group-hover:w-2 transition-all duration-300 h-0.5 bg-[#6C5DD3] mr-0 group-hover:mr-2"></span>
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom section with copyright and scroll to top */}
        <div className="border-t border-[#2A2A2D] mt-16 pt-8 flex flex-col md:flex-row justify-between items-center">
          <p className="text-[#A1A1AA] text-center md:text-left mb-4 md:mb-0">
            &copy; {new Date().getFullYear()} Clyne. All rights reserved
          </p>
          
          <button
            onClick={scrollToTop}
            className="flex items-center justify-center p-3 bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 hover:from-[#6C5DD3]/30 hover:to-[#8875FF]/30 rounded-full transition-all duration-300 transform hover:scale-110"
            aria-label="Scroll to top"
          >
            <ArrowUp className="w-5 h-5 text-[#6C5DD3]" />
          </button>
        </div>
      </div>
    </footer>
  );
};

export default Footer; 
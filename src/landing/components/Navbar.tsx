import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Menu, X, Zap } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const Navbar = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 20) {
        setIsScrolled(true);
      } else {
        setIsScrolled(false);
      }
    };

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (isMenuOpen && !target.closest('.mobile-menu-container') && !target.closest('.menu-button')) {
        setIsMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isMenuOpen]);

  // Prevent body scroll when menu is open
  useEffect(() => {
    if (isMenuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'auto';
    }
    return () => {
      document.body.style.overflow = 'auto';
    };
  }, [isMenuOpen]);

  return (
    <nav
      className={`fixed w-full z-50 transition-all duration-300 ${
        isScrolled || isMenuOpen
          ? "bg-[#262626]/90 backdrop-blur-md py-2 shadow-lg"
          : "bg-transparent py-4"
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center">
          {/* Logo */}
          <div className="flex items-center">
            <Link
              to="/"
              className="flex items-center space-x-2"
            >
              <img src="/images/1.png" alt="Clyne Logo" className="h-12 w-auto" />
              <span className="text-2xl font-bold bg-gradient-to-r from-[#6C5DD3] to-[#8875FF] bg-clip-text text-transparent">Clyne</span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-6">
            <Link to="/" className="text-white hover:text-[#6C5DD3] transition-colors">Home</Link>
            <Link to="/community-servers" className="text-white hover:text-[#6C5DD3] transition-colors">Community Servers</Link>
            <Link to="/network-transactions" className="text-white hover:text-[#6C5DD3] transition-colors">Network Transactions</Link>
            <div className="flex items-center text-gray-400 cursor-not-allowed">
              <Zap className="w-4 h-4 mr-1" />
              <span className="flex items-center">
                Subscription
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="ml-1">
                  <rect width="18" height="11" x="3" y="11" rx="2" ry="2"></rect>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                </svg>
              </span>
            </div>
          </div>

          {/* Dashboard button */}
          <div className="hidden md:flex items-center">
            <Link
              to="/dashboard"
              className="bg-[#6C5DD3] hover:bg-[#5849B1] text-white py-2 px-6 rounded-lg transition-colors shadow-md"
            >
              Dashboard
            </Link>
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden flex items-center menu-button">
            <button
              className="text-white hover:text-[#6C5DD3] focus:outline-none p-2"
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              aria-label="Toggle menu"
            >
              <motion.div
                initial={false}
                animate={isMenuOpen ? "open" : "closed"}
              >
                {isMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
              </motion.div>
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu with animation and glass effect */}
      <AnimatePresence>
        {isMenuOpen && (
          <motion.div 
            className="fixed inset-0 top-[60px] z-40 mobile-menu-container"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {/* Backdrop overlay */}
            <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setIsMenuOpen(false)} />
            
            {/* Menu content */}
            <motion.div 
              className="absolute top-0 left-0 right-0 bg-[#262626]/95 backdrop-blur-md border-t border-[#3A3A3D]/40 shadow-lg max-h-[calc(100vh-60px)] overflow-auto"
              initial={{ y: -50, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: -50, opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              <div className="px-4 py-5 space-y-3">
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                  className="overflow-hidden"
                >
                  <Link
                    to="/"
                    className="block px-4 py-3 text-white hover:bg-[#6C5DD3]/20 rounded-lg transition-colors"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    Home
                  </Link>
                </motion.div>
                
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                  className="overflow-hidden"
                >
                  <Link
                    to="/community-servers"
                    className="block px-4 py-3 text-white hover:bg-[#6C5DD3]/20 rounded-lg transition-colors"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    Community Servers
                  </Link>
                </motion.div>
                
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="overflow-hidden"
                >
                  <Link
                    to="/network-transactions"
                    className="block px-4 py-3 text-white hover:bg-[#6C5DD3]/20 rounded-lg transition-colors"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    Network Transactions
                  </Link>
                </motion.div>
                
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                  className="overflow-hidden"
                >
                  <div
                    className="flex items-center px-4 py-3 text-gray-400 rounded-lg cursor-not-allowed"
                  >
                    <Zap className="w-5 h-5 mr-3" />
                    <span className="flex items-center">
                      Subscription
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="ml-1">
                        <rect width="18" height="11" x="3" y="11" rx="2" ry="2"></rect>
                        <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                      </svg>
                    </span>
                  </div>
                </motion.div>

                <motion.div 
                  className="pt-4 flex flex-col space-y-2"
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 }}
                >
                  <Link
                    to="/dashboard"
                    className="block px-4 py-3 text-center bg-gradient-to-r from-[#6C5DD3] to-[#8875FF] hover:from-[#5849B1] hover:to-[#7665ED] text-white rounded-lg shadow-md transition-colors"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    Dashboard
                  </Link>
                </motion.div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
};

export default Navbar; 
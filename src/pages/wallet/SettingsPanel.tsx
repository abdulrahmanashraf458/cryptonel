import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useLocation } from "react-router-dom";

// Import original pages
import Security from "./Security";
import Privacy from "./Privacy";
import Settings from "./Settings";
import Backup from "./Backup";

// Icons
import { Shield, Eye, Settings as SettingsIcon, Database } from "lucide-react";

const SettingsPanel: React.FC = () => {
  // Active tab state
  const [activeTab, setActiveTab] = useState<
    "security" | "privacy" | "settings" | "backup"
  >("settings");

  // Use location to get information about current path
  const location = useLocation();

  // Set active tab based on clicked link in sidebar
  useEffect(() => {
    // Extract tab info from state if available
    const tabInfo = location.state as { tabName?: string } | null;

    if (tabInfo?.tabName) {
      // If there's specific tab info from the link
      setActiveTab(tabInfo.tabName as "security" | "privacy" | "settings" | "backup");
    } else {
      // Check based on original path that was redirected
      const pathname = location.pathname;

      if (pathname.includes("/security")) {
        setActiveTab("security");
      } else if (pathname.includes("/privacy")) {
        setActiveTab("privacy");
      } else if (pathname.includes("/backup")) {
        setActiveTab("backup");
      } else {
        setActiveTab("settings");
      }
    }
  }, [location]);

  return (
    <div className="min-h-screen bg-[#262626]">
      <div className="container mx-auto px-4 py-6">
        {/* Tab Navigation */}
        <div className="mb-6">
          <div className="border-b border-[#393939]">
            {/* On larger screens, all tabs in one row */}
            <div className="hidden min-[551px]:flex">
              {/* Security Tab */}
              <button
                onClick={() => setActiveTab("security")}
                className={`flex items-center justify-center gap-2 py-4 px-5 text-base font-medium relative ${
                  activeTab === "security"
                    ? "text-blue-500"
                    : "text-gray-400 hover:text-blue-400"
                }`}
              >
                <Shield
                  size={20}
                  className={
                    activeTab === "security" ? "text-blue-500" : "text-gray-400"
                  }
                />
                <span>Security</span>
                {activeTab === "security" && (
                  <div className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-500"></div>
                )}
              </button>

              {/* Privacy Tab */}
              <button
                onClick={() => setActiveTab("privacy")}
                className={`flex items-center justify-center gap-2 py-4 px-5 text-base font-medium relative ${
                  activeTab === "privacy"
                    ? "text-blue-500"
                    : "text-gray-400 hover:text-blue-400"
                }`}
              >
                <Eye
                  size={20}
                  className={
                    activeTab === "privacy" ? "text-blue-500" : "text-gray-400"
                  }
                />
                <span>Privacy</span>
                {activeTab === "privacy" && (
                  <div className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-500"></div>
                )}
              </button>

              {/* Backup Tab */}
              <button
                onClick={() => setActiveTab("backup")}
                className={`flex items-center justify-center gap-2 py-4 px-5 text-base font-medium relative ${
                  activeTab === "backup"
                    ? "text-blue-500"
                    : "text-gray-400 hover:text-blue-400"
                }`}
              >
                <Database
                  size={20}
                  className={
                    activeTab === "backup" ? "text-blue-500" : "text-gray-400"
                  }
                />
                <span>Backup</span>
                {activeTab === "backup" && (
                  <div className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-500"></div>
                )}
              </button>

              {/* Settings Tab */}
              <button
                onClick={() => setActiveTab("settings")}
                className={`flex items-center justify-center gap-2 py-4 px-5 text-base font-medium relative ${
                  activeTab === "settings"
                    ? "text-blue-500"
                    : "text-gray-400 hover:text-blue-400"
                }`}
              >
                <SettingsIcon
                  size={20}
                  className={
                    activeTab === "settings" ? "text-blue-500" : "text-gray-400"
                  }
                />
                <span>Settings</span>
                {activeTab === "settings" && (
                  <div className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-500"></div>
                )}
              </button>
            </div>

            {/* On smaller screens (< 550px), two rows */}
            <div className="flex flex-col max-[550px]:flex min-[551px]:hidden">
              {/* First row: Security and Privacy */}
              <div className="flex">
                {/* Security Tab */}
                <button
                  onClick={() => setActiveTab("security")}
                  className={`flex items-center justify-center gap-2 py-4 px-5 text-base font-medium relative flex-1 ${
                    activeTab === "security"
                      ? "text-blue-500"
                      : "text-gray-400 hover:text-blue-400"
                  }`}
                >
                  <Shield
                    size={20}
                    className={
                      activeTab === "security" ? "text-blue-500" : "text-gray-400"
                    }
                  />
                  <span>Security</span>
                  {activeTab === "security" && (
                    <div className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-500"></div>
                  )}
                </button>

                {/* Privacy Tab */}
                <button
                  onClick={() => setActiveTab("privacy")}
                  className={`flex items-center justify-center gap-2 py-4 px-5 text-base font-medium relative flex-1 ${
                    activeTab === "privacy"
                      ? "text-blue-500"
                      : "text-gray-400 hover:text-blue-400"
                  }`}
                >
                  <Eye
                    size={20}
                    className={
                      activeTab === "privacy" ? "text-blue-500" : "text-gray-400"
                    }
                  />
                  <span>Privacy</span>
                  {activeTab === "privacy" && (
                    <div className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-500"></div>
                  )}
                </button>
              </div>

              {/* Second row: Backup and Settings */}
              <div className="flex">
                {/* Backup Tab */}
                <button
                  onClick={() => setActiveTab("backup")}
                  className={`flex items-center justify-center gap-2 py-4 px-5 text-base font-medium relative flex-1 ${
                    activeTab === "backup"
                      ? "text-blue-500"
                      : "text-gray-400 hover:text-blue-400"
                  }`}
                >
                  <Database
                    size={20}
                    className={
                      activeTab === "backup" ? "text-blue-500" : "text-gray-400"
                    }
                  />
                  <span>Backup</span>
                  {activeTab === "backup" && (
                    <div className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-500"></div>
                  )}
                </button>

                {/* Settings Tab */}
                <button
                  onClick={() => setActiveTab("settings")}
                  className={`flex items-center justify-center gap-2 py-4 px-5 text-base font-medium relative flex-1 ${
                    activeTab === "settings"
                      ? "text-blue-500"
                      : "text-gray-400 hover:text-blue-400"
                  }`}
                >
                  <SettingsIcon
                    size={20}
                    className={
                      activeTab === "settings" ? "text-blue-500" : "text-gray-400"
                    }
                  />
                  <span>Settings</span>
                  {activeTab === "settings" && (
                    <div className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-500"></div>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Tab Content */}
        <div>
          <motion.div
            key={activeTab}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.2 }}
          >
            {activeTab === "security" && <Security />}
            {activeTab === "privacy" && <Privacy />}
            {activeTab === "backup" && <Backup />}
            {activeTab === "settings" && <Settings />}
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel;

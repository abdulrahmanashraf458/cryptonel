import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import axios from 'axios';
import { Shield, EyeOff, MessageCircle, Users, Check } from 'lucide-react';

interface AdvancedSettings {
  showRatingCount: boolean;
  showComments: boolean;
  sortByNewest: boolean;
  showUsernameOnly: boolean;
  allowAnonymousRatings: boolean;
}

export default function AdvancedSettingsManager() {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [settings, setSettings] = useState<AdvancedSettings>({
    showRatingCount: false,
    showComments: false,
    sortByNewest: false,
    showUsernameOnly: false,
    allowAnonymousRatings: false
  });

  // Load settings on component mount
  useEffect(() => {
    fetchSettings();
  }, []);

  // Fetch settings from API
  const fetchSettings = async () => {
    try {
      setIsLoading(true);
      const response = await axios.get('/api/ratings/settings');
      if (response.data && response.data.settings) {
        setSettings(response.data.settings);
      }
    } catch (error) {
      console.error('Error fetching settings:', error);
      toast.error('Failed to load settings');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle toggle setting
  const handleToggle = async (setting: keyof AdvancedSettings, settingName: string) => {
    try {
      setIsLoading(true);
      
      // Update optimistically
      const newValue = !settings[setting];
      setSettings(prev => ({
        ...prev,
        [setting]: newValue
      }));
      
      // Save to server
      await axios.post('/api/ratings/settings/update', {
        setting,
        value: newValue
      });
      
      toast.success(`${settingName} ${newValue ? 'enabled' : 'disabled'}`);
    } catch (error) {
      // Revert on error
      setSettings(prev => ({
        ...prev,
        [setting]: !prev[setting]
      }));
      console.error(`Error updating ${setting}:`, error);
      toast.error(`Failed to update ${settingName}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle save all settings
  const handleSaveAll = async () => {
    try {
      setIsSaving(true);
      
      // Save all settings to server
      const response = await axios.post('/api/ratings/settings/update-all', {
        settings
      });
      
      if (response.data && response.data.success) {
        // Show success toast with better styling
        toast.success(
          <div className="flex items-center gap-2">
            <Check className="text-white" size={18} />
            <span>All settings have been saved successfully!</span>
          </div>,
          {
            duration: 4000,
            position: 'top-center',
            style: {
              background: '#10B981',
              color: '#fff',
              fontWeight: 'bold',
              padding: '12px 16px',
              borderRadius: '8px',
            }
          }
        );
      } else {
        throw new Error('Failed to save settings');
      }
    } catch (error) {
      console.error('Error saving all settings:', error);
      toast.error('Failed to save settings. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">Advanced Settings</h2>
        <div className="flex items-center gap-2 text-xs bg-gradient-to-r from-amber-500 to-yellow-700 text-white px-3 py-1 rounded-full">
          <Shield size={14} />
          <span className="font-bold">Premium Features</span>
        </div>
      </div>
      
      {/* Privacy Settings */}
      <div className="bg-gradient-to-br from-[#2A2A2E] to-[#252530] p-5 rounded-2xl shadow-lg border border-gray-700/30 mb-6">
        <div className="flex items-center mb-5">
          <EyeOff size={18} className="text-purple-400 mr-2" />
          <h3 className="text-xl font-medium text-gray-200">Privacy Settings</h3>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Show Ratings Count Toggle */}
          <div className="bg-[#1E1E20] p-4 rounded-xl border border-gray-700/50 hover:border-purple-500/30 hover:bg-[#1E1E20]/80 transition-all">
            <div className="flex items-start mb-3">
              <div className="flex-1">
                <h4 className="text-sm font-medium text-gray-200">Show Rating Count</h4>
                <p className="text-xs text-gray-400 mt-1">Display total number of ratings on your profile</p>
              </div>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-400">
                {settings.showRatingCount ? 'Visible' : 'Hidden'}
              </span>
              <button
                onClick={() => handleToggle('showRatingCount', 'Rating Count Display')}
                className="relative inline-flex items-center cursor-pointer"
                disabled={isLoading}
              >
                <div className={`w-12 h-6 rounded-full transition-colors duration-300 ${settings.showRatingCount ? 'bg-purple-600' : 'bg-gray-700'}`}>
                  <div className={`absolute w-5 h-5 rounded-full bg-white shadow-md transition-transform duration-300 transform ${settings.showRatingCount ? 'translate-x-6' : 'translate-x-1'}`}></div>
                </div>
              </button>
            </div>
          </div>
          
          {/* Display Comments Toggle */}
          <div className="bg-[#1E1E20] p-4 rounded-xl border border-gray-700/50 hover:border-purple-500/30 hover:bg-[#1E1E20]/80 transition-all">
            <div className="flex items-start mb-3">
              <div className="flex-1">
                <h4 className="text-sm font-medium text-gray-200">Show Comments</h4>
                <p className="text-xs text-gray-400 mt-1">Display comments along with ratings</p>
              </div>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-400">
                {settings.showComments ? 'Visible' : 'Hidden'}
              </span>
              <button
                onClick={() => handleToggle('showComments', 'Comments Display')}
                className="relative inline-flex items-center cursor-pointer"
                disabled={isLoading}
              >
                <div className={`w-12 h-6 rounded-full transition-colors duration-300 ${settings.showComments ? 'bg-purple-600' : 'bg-gray-700'}`}>
                  <div className={`absolute w-5 h-5 rounded-full bg-white shadow-md transition-transform duration-300 transform ${settings.showComments ? 'translate-x-6' : 'translate-x-1'}`}></div>
                </div>
              </button>
            </div>
          </div>
          
          {/* Show Username Only */}
          <div className="bg-[#1E1E20] p-4 rounded-xl border border-gray-700/50 hover:border-purple-500/30 hover:bg-[#1E1E20]/80 transition-all">
            <div className="flex items-start mb-3">
              <div className="flex-1">
                <h4 className="text-sm font-medium text-gray-200">Show Username Only</h4>
                <p className="text-xs text-gray-400 mt-1">Hide avatar and other user details in ratings</p>
              </div>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-400">
                {settings.showUsernameOnly ? 'Enabled' : 'Disabled'}
              </span>
              <button
                onClick={() => handleToggle('showUsernameOnly', 'Username Only Display')}
                className="relative inline-flex items-center cursor-pointer"
                disabled={isLoading}
              >
                <div className={`w-12 h-6 rounded-full transition-colors duration-300 ${settings.showUsernameOnly ? 'bg-purple-600' : 'bg-gray-700'}`}>
                  <div className={`absolute w-5 h-5 rounded-full bg-white shadow-md transition-transform duration-300 transform ${settings.showUsernameOnly ? 'translate-x-6' : 'translate-x-1'}`}></div>
                </div>
              </button>
            </div>
          </div>
          
          {/* Allow Anonymous Ratings */}
          <div className="bg-[#1E1E20] p-4 rounded-xl border border-gray-700/50 hover:border-blue-500/30 hover:bg-[#1E1E20]/80 transition-all">
            <div className="flex items-start mb-3">
              <div className="flex-1">
                <h4 className="text-sm font-medium text-gray-200">Allow Anonymous Ratings</h4>
                <p className="text-xs text-gray-400 mt-1">Let users rate without showing their identity</p>
              </div>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-400">
                {settings.allowAnonymousRatings ? 'Enabled' : 'Disabled'}
              </span>
              <button
                onClick={() => handleToggle('allowAnonymousRatings', 'Anonymous Ratings')}
                className="relative inline-flex items-center cursor-pointer"
                disabled={isLoading}
              >
                <div className={`w-12 h-6 rounded-full transition-colors duration-300 ${settings.allowAnonymousRatings ? 'bg-blue-600' : 'bg-gray-700'}`}>
                  <div className={`absolute w-5 h-5 rounded-full bg-white shadow-md transition-transform duration-300 transform ${settings.allowAnonymousRatings ? 'translate-x-6' : 'translate-x-1'}`}></div>
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>
      
      {/* Display Settings */}
      <div className="bg-gradient-to-br from-[#2A2A2E] to-[#252530] p-5 rounded-2xl shadow-lg border border-gray-700/30 mb-6">
        <div className="flex items-center mb-5">
          <MessageCircle size={18} className="text-amber-400 mr-2" />
          <h3 className="text-xl font-medium text-gray-200">Display Settings</h3>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Sort by Date Toggle */}
          <div className="bg-[#1E1E20] p-4 rounded-xl border border-gray-700/50 hover:border-amber-500/30 hover:bg-[#1E1E20]/80 transition-all">
            <div className="flex items-start mb-3">
              <div className="flex-1">
                <h4 className="text-sm font-medium text-gray-200">Sort Order</h4>
                <p className="text-xs text-gray-400 mt-1">Choose how ratings are sorted</p>
              </div>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-400">
                {settings.sortByNewest ? 'Newest First' : 'Oldest First'}
              </span>
              <button
                onClick={() => handleToggle('sortByNewest', 'Sort Order')}
                className="relative inline-flex items-center cursor-pointer"
                disabled={isLoading}
              >
                <div className={`w-12 h-6 rounded-full transition-colors duration-300 ${settings.sortByNewest ? 'bg-amber-600' : 'bg-gray-700'}`}>
                  <div className={`absolute w-5 h-5 rounded-full bg-white shadow-md transition-transform duration-300 transform ${settings.sortByNewest ? 'translate-x-6' : 'translate-x-1'}`}></div>
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>
      
      {/* Save Button */}
      <div className="flex justify-end mt-8">
        <button 
          className={`px-6 py-2.5 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-medium rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all shadow-md hover:shadow-lg transform ${isSaving ? 'opacity-80' : 'hover:-translate-y-0.5 active:scale-95'} flex items-center gap-2`}
          onClick={handleSaveAll}
          disabled={isLoading || isSaving}
        >
          {isSaving ? (
            <>
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Saving...
            </>
          ) : (
            'Save All Settings'
          )}
        </button>
      </div>
    </div>
  );
} 
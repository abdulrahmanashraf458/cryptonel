import React, { useState } from 'react';
import { toast } from 'react-hot-toast';
import { Shield, EyeOff, Bell, Mail, Award, BadgeCheck, Clock, Filter, Lock, Star, MessageCircle, Users } from 'lucide-react';

export default function AdvancedSettingsRating() {
  // Toggle settings state
  const [showRatingCount, setShowRatingCount] = useState<boolean>(true);
  const [showComments, setShowComments] = useState<boolean>(true);
  const [sortByNewest, setSortByNewest] = useState<boolean>(true);
  const [emailNotifications, setEmailNotifications] = useState<boolean>(true);
  const [showUsernameOnly, setShowUsernameOnly] = useState<boolean>(false);
  const [allowAnonymousRatings, setAllowAnonymousRatings] = useState<boolean>(false);
  
  // Handle toggle setting
  const handleToggle = (
    setter: React.Dispatch<React.SetStateAction<boolean>>,
    settingId: string
  ) => {
    setter(prev => {
      const newValue = !prev;
      // In a real implementation, you would update the setting in the backend
      // This simulates the API call
      setTimeout(() => {
        toast.success(`${settingId} ${newValue ? 'enabled' : 'disabled'}`);
      }, 300);
      return newValue;
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">Advanced Settings</h2>
        <div className="flex items-center gap-2 text-xs text-blue-400 px-3 py-1 bg-blue-500/10 rounded-full">
          <Shield size={14} />
          <span>Premium Features</span>
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
                {showRatingCount ? 'Visible' : 'Hidden'}
              </span>
              <button
                onClick={() => handleToggle(setShowRatingCount, 'Rating Count Display')}
                className="relative inline-flex items-center cursor-pointer"
              >
                <div className={`w-12 h-6 rounded-full transition-colors duration-300 ${showRatingCount ? 'bg-purple-600' : 'bg-gray-700'}`}>
                  <div className={`absolute w-5 h-5 rounded-full bg-white shadow-md transition-transform duration-300 transform ${showRatingCount ? 'translate-x-6' : 'translate-x-1'}`}></div>
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
                {showComments ? 'Visible' : 'Hidden'}
              </span>
              <button
                onClick={() => handleToggle(setShowComments, 'Comments Display')}
                className="relative inline-flex items-center cursor-pointer"
              >
                <div className={`w-12 h-6 rounded-full transition-colors duration-300 ${showComments ? 'bg-purple-600' : 'bg-gray-700'}`}>
                  <div className={`absolute w-5 h-5 rounded-full bg-white shadow-md transition-transform duration-300 transform ${showComments ? 'translate-x-6' : 'translate-x-1'}`}></div>
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
                {showUsernameOnly ? 'Enabled' : 'Disabled'}
              </span>
              <button
                onClick={() => handleToggle(setShowUsernameOnly, 'Username Only Display')}
                className="relative inline-flex items-center cursor-pointer"
              >
                <div className={`w-12 h-6 rounded-full transition-colors duration-300 ${showUsernameOnly ? 'bg-purple-600' : 'bg-gray-700'}`}>
                  <div className={`absolute w-5 h-5 rounded-full bg-white shadow-md transition-transform duration-300 transform ${showUsernameOnly ? 'translate-x-6' : 'translate-x-1'}`}></div>
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
                {allowAnonymousRatings ? 'Enabled' : 'Disabled'}
              </span>
              <button
                onClick={() => handleToggle(setAllowAnonymousRatings, 'Anonymous Ratings')}
                className="relative inline-flex items-center cursor-pointer"
              >
                <div className={`w-12 h-6 rounded-full transition-colors duration-300 ${allowAnonymousRatings ? 'bg-blue-600' : 'bg-gray-700'}`}>
                  <div className={`absolute w-5 h-5 rounded-full bg-white shadow-md transition-transform duration-300 transform ${allowAnonymousRatings ? 'translate-x-6' : 'translate-x-1'}`}></div>
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>
      
      {/* Display Settings */}
      <div className="bg-gradient-to-br from-[#2A2A2E] to-[#252530] p-5 rounded-2xl shadow-lg border border-gray-700/30 mb-6">
        <div className="flex items-center mb-5">
          <Star size={18} className="text-amber-400 mr-2" />
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
                {sortByNewest ? 'Newest First' : 'Oldest First'}
              </span>
              <button
                onClick={() => handleToggle(setSortByNewest, 'Sort Order')}
                className="relative inline-flex items-center cursor-pointer"
              >
                <div className={`w-12 h-6 rounded-full transition-colors duration-300 ${sortByNewest ? 'bg-amber-600' : 'bg-gray-700'}`}>
                  <div className={`absolute w-5 h-5 rounded-full bg-white shadow-md transition-transform duration-300 transform ${sortByNewest ? 'translate-x-6' : 'translate-x-1'}`}></div>
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>
      
      {/* Notification Settings */}
      <div className="bg-gradient-to-br from-[#2A2A2E] to-[#252530] p-5 rounded-2xl shadow-lg border border-gray-700/30">
        <div className="flex items-center mb-5">
          <Bell size={18} className="text-green-400 mr-2" />
          <h3 className="text-xl font-medium text-gray-200">Notification Settings</h3>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Email Notifications */}
          <div className="bg-[#1E1E20] p-4 rounded-xl border border-gray-700/50 hover:border-green-500/30 hover:bg-[#1E1E20]/80 transition-all">
            <div className="flex items-start mb-3">
              <div className="flex-1">
                <h4 className="text-sm font-medium text-gray-200">Email Notifications</h4>
                <p className="text-xs text-gray-400 mt-1">Receive email notifications for new ratings</p>
              </div>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-400">
                {emailNotifications ? 'Enabled' : 'Disabled'}
              </span>
              <button
                onClick={() => handleToggle(setEmailNotifications, 'Email Notifications')}
                className="relative inline-flex items-center cursor-pointer"
              >
                <div className={`w-12 h-6 rounded-full transition-colors duration-300 ${emailNotifications ? 'bg-green-600' : 'bg-gray-700'}`}>
                  <div className={`absolute w-5 h-5 rounded-full bg-white shadow-md transition-transform duration-300 transform ${emailNotifications ? 'translate-x-6' : 'translate-x-1'}`}></div>
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>
      
      {/* Save Button */}
      <div className="flex justify-end mt-8">
        <button 
          className="px-6 py-2.5 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-medium rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all shadow-md hover:shadow-lg transform hover:-translate-y-0.5"
          onClick={() => toast.success('All settings saved successfully')}
        >
          Save All Settings
        </button>
      </div>
    </div>
  );
}


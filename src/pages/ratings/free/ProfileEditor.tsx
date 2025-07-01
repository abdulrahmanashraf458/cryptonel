import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import axios from 'axios';
import { ProfileData } from '../types';

export default function ProfileEditor() {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [profileData, setProfileData] = useState<ProfileData>({
    title: '',
    bio: ''
  });
  const [editingField, setEditingField] = useState<string | null>(null);
  const [tempValue, setTempValue] = useState<string>('');

  // Load profile data on component mount
  useEffect(() => {
    fetchProfileData();
  }, []);

  // Fetch profile data from API
  const fetchProfileData = async () => {
    try {
      setIsLoading(true);
      const response = await axios.get('/api/ratings/profile');
      if (response.data && response.data.profile) {
        setProfileData(response.data.profile);
      }
    } catch (error) {
      console.error('Error fetching profile data:', error);
      toast.error('Failed to load profile data');
    } finally {
      setIsLoading(false);
    }
  };

  // Start editing a field
  const startEditing = (field: string, currentValue: string = '') => {
    setEditingField(field);
    setTempValue(currentValue);
  };

  // Cancel editing
  const cancelEditing = () => {
    setEditingField(null);
    setTempValue('');
  };

  // Save the edited field
  const saveField = async (field: string) => {
    try {
      // Validate title (max 5 words)
      if (field === 'title') {
        const wordCount = tempValue.trim().split(/\s+/).filter(word => word.length > 0).length;
        if (wordCount > 5) {
          toast.error('Title cannot exceed 5 words');
          return;
        }
      }

      setIsLoading(true);
      
      // Save to API
      await axios.post('/api/ratings/profile/update', {
        field,
        value: tempValue
      });

      // Update local state
      setProfileData(prev => ({
        ...prev,
        [field]: tempValue
      }));
      
      setEditingField(null);
      toast.success(`${field.charAt(0).toUpperCase() + field.slice(1)} updated successfully`);
    } catch (error) {
      console.error(`Error updating ${field}:`, error);
      toast.error(`Failed to update ${field}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold text-white mb-6">Profile Information</h2>
      
      {/* Title Field */}
      <div className="bg-[#1E1E20] p-5 rounded-xl border border-gray-700/50">
        <div className="flex flex-col">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-lg font-medium text-gray-200">Title</h3>
            {editingField !== 'title' && (
              <button 
                onClick={() => startEditing('title', profileData.title || '')}
                className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
                disabled={isLoading}
              >
                Edit
              </button>
            )}
          </div>
          
          {editingField === 'title' ? (
            <div className="space-y-3">
              <input 
                type="text"
                value={tempValue}
                onChange={(e) => setTempValue(e.target.value)}
                placeholder="Add your professional title"
                className="w-full bg-[#2A2A2E] text-white border border-gray-700 rounded-lg p-3 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all"
                maxLength={50}
              />
              <p className="text-xs text-gray-400">Limited to 5 words maximum</p>
              <div className="flex gap-2">
                <button
                  onClick={() => saveField('title')}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  disabled={isLoading}
                >
                  Save
                </button>
                <button
                  onClick={cancelEditing}
                  className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
                  disabled={isLoading}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <p className="text-gray-400">
              {profileData.title || 'Add your professional title'}
            </p>
          )}
        </div>
      </div>
      
      {/* Bio Field */}
      <div className="bg-[#1E1E20] p-5 rounded-xl border border-gray-700/50">
        <div className="flex flex-col">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-lg font-medium text-gray-200">Bio</h3>
            {editingField !== 'bio' && (
              <button 
                onClick={() => startEditing('bio', profileData.bio || '')}
                className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
                disabled={isLoading}
              >
                Edit
              </button>
            )}
          </div>
          
          {editingField === 'bio' ? (
            <div className="space-y-3">
              <textarea 
                value={tempValue}
                onChange={(e) => setTempValue(e.target.value)}
                placeholder="Add a short bio about yourself"
                className="w-full bg-[#2A2A2E] text-white border border-gray-700 rounded-lg p-3 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all min-h-[120px]"
                maxLength={300}
              />
              <p className="text-xs text-gray-400">{tempValue.length}/300 characters</p>
              <div className="flex gap-2">
                <button
                  onClick={() => saveField('bio')}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  disabled={isLoading}
                >
                  Save
                </button>
                <button
                  onClick={cancelEditing}
                  className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
                  disabled={isLoading}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <p className="text-gray-400 whitespace-pre-wrap">
              {profileData.bio || 'Add a short bio about yourself'}
            </p>
          )}
        </div>
      </div>
    </div>
  );
} 
import React, { useState, useEffect } from "react";
import { toast } from "react-hot-toast";
import axios from "axios";
import { Star, Award, MessageSquare, Users, Eye, ExternalLink } from 'lucide-react';
import { RatingStats } from '../types';
import { Link } from "react-router-dom";

export default function OverviewRating() {
  const [bio, setBio] = useState<string>("");
  const [title, setTitle] = useState<string>("");
  const [isEditingBio, setIsEditingBio] = useState<boolean>(false);
  const [isEditingTitle, setIsEditingTitle] = useState<boolean>(false);
  const [tempBio, setTempBio] = useState<string>(bio);
  const [tempTitle, setTempTitle] = useState<string>(title);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [stats, setStats] = useState<RatingStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savingProfile, setSavingProfile] = useState<boolean>(false);
  const [username, setUsername] = useState<string>("");

  // Fetch ratings data
  useEffect(() => {
    const fetchRatings = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        // Use current user endpoint
        const endpoint = '/api/ratings/user/current';
        
        const response = await axios.get(endpoint);
        console.log("Ratings data:", response.data); // Debug log
        setStats(response.data);
        
        // Get username for public profile link
        if (response.data && response.data.username) {
          setUsername(response.data.username);
        }
        
        // Get profile data from somewhere if available
        // For now, we'll use placeholder or empty values
        setBio("");
        setTitle("");
        setTempBio("");
        setTempTitle("");
      } catch (err) {
        console.error('Error fetching ratings:', err);
        setError('Failed to load ratings. Please try again later.');
        toast.error('Failed to load ratings');
      } finally {
        setIsLoading(false);
      }
    };

    fetchRatings();
  }, []);

  // Handle bio save
  const handleBioSave = async () => {
    if (tempBio.trim() === "") {
      toast.error("Bio cannot be empty");
      return;
    }
    
    try {
      setSavingProfile(true);
      
      // Here you would typically send this to your API
      // await axios.post('/api/profile/update', { bio: tempBio });
      
      setBio(tempBio);
      setIsEditingBio(false);
      toast.success("Bio saved successfully");
    } catch (err) {
      toast.error("Failed to save bio");
    } finally {
      setSavingProfile(false);
    }
  };

  // Handle title save
  const handleTitleSave = async () => {
    if (tempTitle.trim() === "") {
      toast.error("Title cannot be empty");
      return;
    }
    
    // Check if title is more than 5 words
    const wordCount = tempTitle.trim().split(/\s+/).length;
    if (wordCount > 5) {
      toast.error("Title should not exceed 5 words");
      return;
    }
    
    try {
      setSavingProfile(true);
      
      // Here you would typically send this to your API
      // await axios.post('/api/profile/update', { title: tempTitle });
      
      setTitle(tempTitle);
      setIsEditingTitle(false);
      toast.success("Title saved successfully");
    } catch (err) {
      toast.error("Failed to save title");
    } finally {
      setSavingProfile(false);
    }
  };

  // Cancel editing
  const handleCancel = (type: 'bio' | 'title') => {
    if (type === 'bio') {
      setTempBio(bio);
      setIsEditingBio(false);
    } else {
      setTempTitle(title);
      setIsEditingTitle(false);
    }
  };

  // Format date string - improved with better TypeScript support
  function formatDate(dateString: string | null | undefined): string {
    if (!dateString) return 'Unknown date';
    
    try {
      const date = new Date(dateString);
      // Check if date is valid before using it
      if (isNaN(date.getTime())) {
        return 'Invalid date';
      }
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch (e) {
      return 'Invalid date';
    }
  }

  // Get latest rating
  const getLatestRating = () => {
    if (!stats?.ratings || stats.ratings.length === 0) {
      return null;
    }
    
    // Sort by timestamp and get the most recent
    return stats.ratings.sort((a, b) => {
      // Handle potentially undefined timestamps safely
      const timestampA = a.timestamp || '';
      const timestampB = b.timestamp || '';
      
      // Create dates safely
      const dateA = timestampA ? new Date(timestampA) : new Date(0);
      const dateB = timestampB ? new Date(timestampB) : new Date(0);
      
      // Check if dates are valid before comparing
      const timeA = !isNaN(dateA.getTime()) ? dateA.getTime() : 0;
      const timeB = !isNaN(dateB.getTime()) ? dateB.getTime() : 0;
      
      return timeB - timeA;
    })[0];
  };

  if (isLoading) {
    return <LoadingState />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => {}} />;
  }

  if (!stats) {
    return <EmptyState />;
  }

  const latestRating = getLatestRating();

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-white">Rating Overview</h2>
        {username && (
          <Link 
            to={`/profile/${username}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600/30 to-purple-600/30 hover:from-blue-500/40 hover:to-purple-500/40 text-white rounded-lg transition-all duration-300 border border-blue-500/30"
          >
            <Eye size={16} />
            <span>Public Profile</span>
            <ExternalLink size={14} />
          </Link>
        )}
      </div>
      
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Average Rating */}
        <div className="bg-gradient-to-br from-[#2A2A2E] to-[#252530] p-5 rounded-2xl shadow-lg border border-gray-700/30">
          <div className="flex items-center gap-3 mb-3">
            <div className="bg-yellow-500/20 p-2 rounded-lg">
              <Star className="text-yellow-500" size={20} />
            </div>
            <h3 className="text-gray-300 font-medium">Average Rating</h3>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold text-white">{stats.average_rating.toFixed(1)}</span>
            <div className="flex">
              {[1, 2, 3, 4, 5].map((star) => (
                <Star 
                  key={star}
                  size={16} 
                  className={`${star <= Math.round(stats.average_rating) ? 'text-yellow-400' : 'text-gray-600'}`}
                  fill={star <= Math.round(stats.average_rating) ? 'currentColor' : 'none'}
                />
              ))}
            </div>
          </div>
        </div>
        
        {/* Total Ratings */}
        <div className="bg-gradient-to-br from-[#2A2A2E] to-[#252530] p-5 rounded-2xl shadow-lg border border-gray-700/30">
          <div className="flex items-center gap-3 mb-3">
            <div className="bg-blue-500/20 p-2 rounded-lg">
              <Users className="text-blue-500" size={20} />
            </div>
            <h3 className="text-gray-300 font-medium">Total Ratings</h3>
          </div>
          <div>
            <span className="text-2xl font-bold text-white">{stats.total_ratings}</span>
            <span className="text-gray-400 text-sm ml-2">reviews</span>
          </div>
        </div>
        
        {/* Featured Quote */}
        <div className="bg-gradient-to-br from-[#2A2A2E] to-[#252530] p-5 rounded-2xl shadow-lg border border-gray-700/30">
          <div className="flex items-center gap-3 mb-3">
            <div className="bg-purple-500/20 p-2 rounded-lg">
              <MessageSquare className="text-purple-500" size={20} />
            </div>
            <h3 className="text-gray-300 font-medium">Featured Quote</h3>
          </div>
          {stats.featured_quote && stats.featured_quote.text && stats.featured_quote.text !== "No ratings yet" ? (
            <div>
              <p className="text-gray-300 text-sm italic">"{stats.featured_quote.text}"</p>
              <div className="flex items-center mt-2">
                <span className="text-gray-400 text-xs">- {stats.featured_quote.author || 'Anonymous'}</span>
                <div className="flex ml-2">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <Star 
                      key={star}
                      size={12} 
                      className={`${star <= (stats.featured_quote.stars || 0) ? 'text-yellow-400' : 'text-gray-600'}`}
                      fill={star <= (stats.featured_quote.stars || 0) ? 'currentColor' : 'none'}
                    />
                  ))}
                </div>
              </div>
            </div>
          ) : latestRating && latestRating.comment ? (
            <div>
              <p className="text-gray-300 text-sm italic">"{latestRating.comment}"</p>
              <div className="flex items-center mt-2">
                <span className="text-gray-400 text-xs">- {latestRating.rater_username || 'Anonymous'}</span>
                <div className="flex ml-2">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <Star 
                      key={star}
                      size={12} 
                      className={`${star <= (latestRating.stars || 0) ? 'text-yellow-400' : 'text-gray-600'}`}
                      fill={star <= (latestRating.stars || 0) ? 'currentColor' : 'none'}
                    />
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No featured quotes yet</p>
          )}
        </div>
      </div>
      
      {/* Rating Distribution */}
      <div className="bg-gradient-to-br from-[#2A2A2E] to-[#252530] p-5 rounded-2xl shadow-lg border border-gray-700/30 mt-6">
        <h3 className="text-xl font-medium text-gray-200 mb-4">Rating Distribution</h3>
        <div className="space-y-3">
          {stats.distribution && stats.distribution.map((item) => (
            <div key={`star-${item.stars}`} className="flex items-center">
              <div className="w-10 flex justify-end mr-3">
                <span className="text-gray-400">{item.stars} ★</span>
              </div>
              <div className="flex-1 bg-gray-700 rounded-full h-3 overflow-hidden">
                <div 
                  className="h-full bg-yellow-500 rounded-full"
                  style={{ width: `${item.percentage || 0}%` }}
                ></div>
              </div>
              <span className="text-gray-400 ml-3 w-10">{item.percentage || 0}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-white mb-6">Rating Overview</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-gradient-to-br from-[#2A2A2E] to-[#252530] p-5 rounded-2xl shadow-lg border border-gray-700/30">
            <div className="animate-pulse flex items-center gap-3 mb-3">
              <div className="bg-gray-700 p-2 rounded-lg h-8 w-8"></div>
              <div className="h-4 bg-gray-700 rounded w-24"></div>
            </div>
            <div className="h-6 bg-gray-700 rounded w-16"></div>
          </div>
        ))}
      </div>
      <div className="bg-gradient-to-br from-[#2A2A2E] to-[#252530] p-5 rounded-2xl shadow-lg border border-gray-700/30">
        <div className="h-6 bg-gray-700 rounded w-40 mb-4"></div>
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex items-center">
              <div className="h-4 bg-gray-700 rounded w-8 mr-3"></div>
              <div className="flex-1 bg-gray-700 rounded-full h-3"></div>
              <div className="h-4 bg-gray-700 rounded w-8 ml-3"></div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string, onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="bg-red-500/20 p-3 rounded-full mb-4">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#EF4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
      </div>
      <h3 className="text-xl font-bold text-white mb-2">Failed to Load</h3>
      <p className="text-gray-400 text-center max-w-md mb-6">{message}</p>
      <button 
        onClick={onRetry}
        className="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-6 rounded-lg transition-colors"
      >
        Try Again
      </button>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="bg-blue-500/20 p-3 rounded-full mb-4">
        <Star className="text-blue-500" size={24} />
      </div>
      <h3 className="text-xl font-bold text-white mb-2">No Ratings Yet</h3>
      <p className="text-gray-400 text-center max-w-md mb-6">
        You haven't received any ratings yet. Ratings will appear here once users rate your profile.
      </p>
    </div>
  );
}

import React, { useState, useEffect, useCallback, memo } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { Star, Check, MessageCircle, BarChart2, User, Calendar, CheckCircle2, Loader2, Send, Crown, Medal, Award, EyeOff } from 'lucide-react';

// --- Badge Components (copied from Leaderboard.tsx for consistency) ---

const VerificationBadge = memo(({ isTop3 = false }: { isTop3?: boolean }) => (
  <svg
    className={`ml-1.5 ${isTop3 ? 'h-5 w-5' : 'h-5 w-5'} text-[#9D8DFF] cursor-help`}
    viewBox="0 0 22 22"
    fill="currentColor"
    role="img"
    aria-labelledby="verified-title"
  >
    <title id="verified-title">Verified User</title>
    <path d="M20.396 11c-.018-.646-.215-1.275-.57-1.816-.354-.54-.852-.972-1.438-1.246.223-.607.27-1.264.14-1.897-.131-.634-.437-1.218-.882-1.687-.47-.445-1.053-.75-1.687-.882-.633-.13-1.29-.083-1.897.14-.273-.587-.704-1.086-1.245-1.44S11.647 1.62 11 1.604c-.646.017-1.273.213-1.813.568s-.969.854-1.24 1.44c-.608-.223-1.267-.272-1.902-.14-.635.13-1.22.436-1.69.882-.445.47-.749 1.055-.878 1.688-.13.633-.08 1.29.144 1.896-.587.274-1.087.705-1.443 1.245-.356.54-.555 1.17-.574 1.817.02.647.218 1.276.574 1.817.356.54.856.972 1.443 1.245-.224.606-.274 1.263-.144 1.896.13.634.433 1.218.877 1.688.47.443 1.054.747 1.687.878.633.132 1.29.084 1.897-.136.274.586.705 1.084 1.246 1.439.54.354 1.17.551 1.816.569.647-.016 1.276-.213 1.817-.567s.972-.854 1.245-1.44c.604.239 1.266.296 1.903.164.636-.132 1.22-.447 1.68-.907.46-.46.776-1.044.908-1.681s.075-1.299-.165-1.903c.586-.274 1.084-.705 1.439-1.246.354-.54.551-1.17.569-1.816zM9.662 14.85l-3.429-3.428 1.293-1.302 2.072 2.072 4.4-4.794 1.347 1.246z" />
  </svg>
));

const CompactPremiumBadge = memo(() => (
    <span className="inline-flex items-center justify-center ml-1.5 cursor-help" title="Premium User">
      <img src="/images/premium.png" alt="Premium" className="h-5 object-contain" />
    </span>
));

const VIPBadge = memo(() => (
    <span className="inline-flex items-center justify-center ml-1.5 text-xs px-1.5 py-0.5 bg-gradient-to-r from-purple-600 to-indigo-600 rounded-full text-white font-bold cursor-help" title="VIP User">
      VIP
    </span>
));

const StaffBadge = memo(() => (
    <span className="inline-flex items-center justify-center ml-1.5 cursor-help" title="Staff Member">
      <img src="/images/staff.png" alt="Staff" className="h-5 object-contain" />
    </span>
));

// A new component to display username with badges
const UsernameDisplay = memo(({ user, isProfileOwner = false }: { user: Partial<UserData> & Partial<RatingEntry> & { rater_username?: string }, isProfileOwner?: boolean }) => {
    const name = user.rater_username || user.username;
    
    return (
        <div className="flex items-center">
            <span className={`font-medium ${isProfileOwner ? "text-3xl" : ""}`}>{name}</span>
            {user.verified && <VerificationBadge />}
            {user.premium && <CompactPremiumBadge />}
            {user.vip && <VIPBadge />}
            {user.staff && <StaffBadge />}
        </div>
    );
});

// --- Interfaces to define data structures ---
interface UserData {
  username: string;
  user_id: string;
  avatar?: string;
  premium?: boolean;
  vip?: boolean;
  verified?: boolean;
  staff?: boolean;
  account_type?: string;
  bio?: string;
  title?: string;
  appearance: AppearanceSettings;
  settings: AdvancedSettings;
}

interface RatingEntry {
  rater_id: string;
  rater_username: string;
  stars: number;
  comment?: string | null;
  timestamp?: string;
  // Badges for raters
  premium?: boolean;
  vip?: boolean;
  verified?: boolean;
  staff?: boolean;
}

interface RatingsData {
  total_ratings: number;
  average_rating: number;
  ratings: RatingEntry[];
  distribution?: { stars: number; percentage: number }[];
  featured_quote?: { text: string; author: string; stars: number };
  // Pagination
  total_pages: number;
  current_page: number;
}

interface AppearanceSettings {
  theme: 'default' | 'dark' | 'gradient' | 'luxury' | 'elegant' | 'neon' | 'forest' | 'cosmic' | 'minimalist' | 'tech' | 'pastel' | 'monochrome' | 'custom';
  customThemeColors: {
    primary: string;
    secondary: string;
    text: string;
    background: string;
  };
  ratingStyle: 'stars' | 'numbers' | 'bars' | 'emoji' | 'percent';
  cardStyle: 'modern' | 'compact' | 'detailed';
  fontStyle: 'default' | 'modern' | 'classic';
  showAnimation: boolean;
  highlightTopRatings: boolean;
}

interface AdvancedSettings {
  allowAnonymousRatings: boolean;
  showComments: boolean;
  showRatingCount: boolean;
  showUsernameOnly: boolean;
  sortByNewest: boolean;
}

interface RaterInfo {
  [key: string]: {
    avatar?: string;
    premium?: boolean;
    vip?: boolean;
    verified?: boolean;
    staff?: boolean;
  };
}

// --- Helper Functions ---
const getDiscordAvatar = (userId: string, avatarId?: string) => {
  if (!userId || !avatarId) {
    return "https://cdn.discordapp.com/embed/avatars/0.png";
  }
  const extension = avatarId.startsWith("a_") ? "gif" : "png";
  return `https://cdn.discordapp.com/avatars/${userId}/${avatarId}.${extension}?size=512`;
};

// The main Public Profile Page Component
export default function PublicProfilePage() {
  const { username } = useParams<{ username: string }>();
  const [userData, setUserData] = useState<UserData | null>(null);
  const [ratingsData, setRatingsData] = useState<RatingsData | null>(null);
  const [raterAvatarsAndBadges, setRaterAvatarsAndBadges] = useState<RaterInfo>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'reviews' | 'statistics'>('reviews');
  
  // State for pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [isFetchingPage, setIsFetchingPage] = useState(false);

  // State for the new rating form
  const [newRating, setNewRating] = useState(0);
  const [newComment, setNewComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitMessage, setSubmitMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);

  const fetchData = useCallback(async (page = 1) => {
    if (!username) return;
    
    if(page === 1) setLoading(true);
    else setIsFetchingPage(true);

    setError(null);
    try {
      const profileRes = await axios.get(`/api/public-profile/${username}?page=${page}`);
      if (!profileRes.data.success) {
        throw new Error(profileRes.data.error || 'User not found');
      }
      
      setUserData(profileRes.data.user);
      setRatingsData(profileRes.data.ratings);
      setCurrentPage(profileRes.data.ratings.current_page);

      // Fetch avatars and badges for the user and the raters
      const userIds = new Set<string>([profileRes.data.user.user_id]);
      profileRes.data.ratings.ratings.forEach((r: RatingEntry) => userIds.add(r.rater_id));
      
      const ids = Array.from(userIds);
      if (ids.length > 0) {
          const res = await axios.get(`/api/discord-users?ids=${ids.join(',')}`);
          if (res.data.success) {
              const newInfo: RaterInfo = {};
              res.data.users.forEach((u: any) => {
                  newInfo[u.user_id] = { 
                      avatar: u.avatar,
                      verified: u.verified,
                      premium: u.premium,
                      vip: u.vip,
                      staff: u.staff
                  };
              });
              setRaterAvatarsAndBadges(prev => ({...prev, ...newInfo}));
          }
      }

    } catch (err: any) {
      setError(err.message || 'Failed to load profile.');
      console.error("Error fetching profile:", err);
    } finally {
      setLoading(false);
      setIsFetchingPage(false);
    }
  }, [username]);

  useEffect(() => {
    fetchData(1);
  }, [fetchData]);

  const handlePageChange = (newPage: number) => {
    if (newPage > 0 && newPage <= (ratingsData?.total_pages || 1) && !isFetchingPage) {
      fetchData(newPage);
    }
  };

  const handleRatingSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newRating === 0) {
      setSubmitMessage({ type: 'error', text: 'Please select a star rating.' });
      return;
    }

    setIsSubmitting(true);
    setSubmitMessage(null);

    try {
      const response = await axios.post(`/api/public-profile/${username}/rate`, {
        stars: newRating,
        comment: newComment,
      });
      
      if (response.data.success) {
        setSubmitMessage({ type: 'success', text: 'Thank you! Your rating has been submitted.' });
        setNewRating(0);
        setNewComment("");
        fetchData(1);
      } else {
        throw new Error(response.data.error || 'Failed to submit rating.');
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || err.message || 'An error occurred.';
      setSubmitMessage({ type: 'error', text: errorMessage });
    } finally {
      setIsSubmitting(false);
    }
  };

  // --- Render logic ---
  if (loading) {
    return (
      <div className="min-h-screen bg-black flex flex-col items-center justify-center text-white">
        <Loader2 className="animate-spin h-10 w-10 text-white mb-4" />
        <span>Loading profile...</span>
      </div>
    );
  }

  if (error) {
    return <div className="min-h-screen bg-gray-900 flex items-center justify-center text-red-500">{error}</div>;
  }

  if (!userData || !ratingsData) {
    return <div className="min-h-screen bg-gray-900 flex items-center justify-center text-white">Profile not available.</div>;
  }
  
  const { appearance } = userData;
  const theme = appearance?.theme || 'default';
  const customThemeColors = appearance?.customThemeColors || { primary: '#4338ca', secondary: '#6366f1', text: '#ffffff', background: '#111827' };
  const cardStyle = appearance?.cardStyle || 'modern';
  const fontStyle = appearance?.fontStyle || 'default';
  const ratingStyle = appearance?.ratingStyle || 'stars';

  // Theme-specific classes
  const themeClasses = {
    dark: 'bg-[#1A1A1E] text-white',
    gradient: 'bg-gradient-to-br from-gray-900 to-gray-800 text-white',
    luxury: 'bg-gradient-to-br from-gray-900 to-stone-900 text-yellow-50',
    elegant: 'bg-gradient-to-r from-[#232526] to-[#414345] text-gray-200',
    neon: 'bg-[#0d0d0f] text-purple-100',
    forest: 'bg-gradient-to-br from-green-900 to-emerald-800 text-green-50',
    cosmic: 'bg-gradient-to-br from-indigo-900 to-purple-900 text-indigo-50',
    minimalist: 'bg-white text-gray-800',
    tech: 'bg-gradient-to-br from-sky-900 to-cyan-800 text-cyan-50',
    pastel: 'bg-gradient-to-br from-pink-200 to-sky-200 text-gray-700',
    monochrome: 'bg-gradient-to-br from-zinc-700 to-zinc-900 text-zinc-100',
    default: 'bg-[#1E1E20] text-white',
    custom: ''
  };
  
  const fontClasses = {
    default: 'font-sans',
    modern: 'font-sans font-medium',
    classic: 'font-serif'
  };

  // Rating color based on theme
  const ratingColor = {
    luxury: 'text-yellow-500',
    elegant: 'text-amber-400',
    neon: 'text-purple-400',
    forest: 'text-emerald-400',
    cosmic: 'text-indigo-400',
    minimalist: 'text-gray-600',
    tech: 'text-cyan-400',
    pastel: 'text-pink-400',
    monochrome: 'text-zinc-400',
    default: 'text-yellow-400',
    dark: 'text-yellow-400',
    gradient: 'text-blue-400',
    custom: 'text-blue-400'
  };

  // Rating bar color based on theme
  const barColor = {
    luxury: 'bg-yellow-500',
    elegant: 'bg-amber-500',
    neon: 'bg-purple-500',
    forest: 'bg-emerald-500',
    cosmic: 'bg-indigo-500',
    minimalist: 'bg-gray-500',
    tech: 'bg-cyan-500',
    pastel: 'bg-pink-500',
    monochrome: 'bg-zinc-500',
    default: 'bg-blue-500',
    dark: 'bg-blue-500',
    gradient: 'bg-blue-500',
    custom: 'bg-blue-500'
  };

  // Border color based on theme
  const borderColor = {
    luxury: 'border-yellow-500/20',
    elegant: 'border-amber-500/30',
    neon: 'border-purple-500/30',
    forest: 'border-emerald-500/30',
    cosmic: 'border-indigo-500/30',
    minimalist: 'border-gray-200',
    tech: 'border-cyan-500/30',
    pastel: 'border-pink-200',
    monochrome: 'border-zinc-700',
    default: 'border-gray-700/50',
    dark: 'border-gray-800',
    gradient: 'border-blue-500/50',
    custom: 'border-gray-700/50'
  };

  // Card background based on theme
  const cardBg = {
    minimalist: 'bg-gray-100',
    pastel: 'bg-pink-100/30',
    luxury: 'bg-[#1A1A1A]/70',
    neon: 'bg-[#0d0d0f]/80 shadow-[0_0_10px_1px_rgba(168,85,247,0.15)]',
    default: 'bg-[#1E1E20]/70',
    dark: 'bg-[#1E1E20]/70',
    gradient: 'bg-[#1E1E20]/70',
    forest: 'bg-[#1E1E20]/70',
    cosmic: 'bg-[#1E1E20]/70',
    tech: 'bg-[#1E1E20]/70',
    monochrome: 'bg-[#1E1E20]/70',
    elegant: 'bg-[#1E1E20]/70',
    custom: 'bg-[#1E1E20]/70'
  };

  // Render stars based on rating
  const renderStars = (rating: number) => {
    const stars = [];
    for (let i = 0; i < 5; i++) {
      stars.push(
        <Star
          key={i}
          size={16}
          className={i < Math.round(rating) ? ratingColor[theme] : 'text-gray-600'}
          fill={i < Math.round(rating) ? 'currentColor' : 'none'}
        />
      );
    }
    return <div className="flex">{stars}</div>;
  };

  // Render rating based on style
  const renderRating = (rating: number) => {
    switch (ratingStyle) {
      case 'stars':
        return (
          <span className={ratingColor[theme]}>
            {'★'.repeat(Math.round(rating)) + '☆'.repeat(5 - Math.round(rating))}
          </span>
        );
      case 'numbers':
        return (
          <span className={`${ratingColor[theme]} font-bold`}>
            {rating.toFixed(1)}<span className="text-gray-400 font-normal text-sm">/5</span>
          </span>
        );
      case 'bars':
        return (
          <div className="w-24 bg-gray-700 h-2 rounded-full overflow-hidden">
            <div className={`${barColor[theme]} h-full rounded-full`} style={{ width: `${(rating / 5) * 100}%` }}></div>
          </div>
        );
      case 'emoji':
        const emojis = ['😞', '😕', '😐', '🙂', '😊'];
        return <div className="text-xl">{emojis[Math.round(rating) - 1] || emojis[4]}</div>;
      case 'percent':
        return (
          <div className="flex items-center">
            <span className={`${ratingColor[theme]} font-bold`}>{Math.round((rating / 5) * 100)}%</span>
          </div>
        );
      default:
        return renderStars(rating);
    }
  };

  return (
    <div 
      style={theme === 'custom' ? { 
        backgroundColor: customThemeColors.background,
        color: customThemeColors.text
      } : {}}
      className={`min-h-screen w-full ${fontClasses[fontStyle]} ${themeClasses[theme]}`}
    >
      {/* Main content - full width */}
      <div className="w-full">
        {/* Header Image */}
        <div 
          style={theme === 'custom' ? {
            background: `linear-gradient(135deg, ${customThemeColors.primary}, ${customThemeColors.secondary})`
          } : {}}
          className="h-64 relative overflow-hidden"
        >
          <div className={`absolute inset-0 ${theme === 'minimalist' || theme === 'pastel' ? 'bg-black/10' : 'bg-black/30'}`}></div>
          {theme === 'neon' && (
            <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-purple-500/50 to-transparent"></div>
          )}
          {theme === 'elegant' && (
            <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-amber-500/30 to-transparent"></div>
          )}
        </div>
        
        {/* Profile Content */}
        <div className="relative px-6 py-6 max-w-6xl mx-auto">
          {/* Profile Image */}
          <div className="absolute -top-20 left-1/2 transform -translate-x-1/2">
            <div className="w-40 h-40 rounded-full flex items-center justify-center overflow-hidden shadow-lg">
              <img 
                src={getDiscordAvatar(userData.user_id, raterAvatarsAndBadges[userData.user_id]?.avatar || userData.avatar)}
                alt={`${userData.username}'s profile`}
                className="w-full h-full object-cover"
              />
            </div>
          </div>
          
          {/* Content with spacing for image */}
          <div className="mt-24 text-center">
            {/* Name and Verification */}
            <div className="flex items-center justify-center gap-2 mb-1">
              <UsernameDisplay user={userData} isProfileOwner={true} />
            </div>
            
            {/* Title */}
            {userData.title && (
              <p className={`-mt-1 text-base font-medium mb-3 opacity-80`} style={{ color: ratingColor[theme] ? ratingColor[theme] : customThemeColors.primary }}>
                {userData.title}
              </p>
            )}
            
            {/* Rating Display */}
            <div className="flex items-center justify-center gap-2 mb-2">
              <div className="flex">
                {renderRating(ratingsData.average_rating)}
              </div>
              <span className="text-gray-400">
                {ratingsData.average_rating.toFixed(1)} stars
              </span>
            </div>
            
            {/* Bio */}
            <p className="text-gray-400 mb-6 max-w-2xl mx-auto">
              {userData.bio || 'No bio provided.'}
            </p>
            
            {/* Tabs */}
            <div className="border-b border-gray-700 flex justify-center">
              <button 
                onClick={() => setActiveTab('reviews')}
                className={`px-6 py-3 font-medium ${
                  activeTab === 'reviews' ? `text-white border-b-2 ${borderColor[theme]}` : 'text-gray-400'
                }`}
              >
                Reviews
              </button>
              <button 
                onClick={() => setActiveTab('statistics')}
                className={`px-6 py-3 font-medium ${
                  activeTab === 'statistics' ? `text-white border-b-2 ${borderColor[theme]}` : 'text-gray-400'
                }`}
              >
                Statistics
              </button>
            </div>
            
            {/* Tab Content */}
            <div className="mt-8 max-w-4xl mx-auto">
              {activeTab === 'reviews' && (
                <div>
                  <h3 className="text-xl font-medium mb-6 text-center">
                    Customer Reviews
                  </h3>
                  
                  <div className="space-y-6">
                    {ratingsData.ratings.map((rating, index) => {
                      const raterInfo = raterAvatarsAndBadges[rating.rater_id] || {};
                      const combinedRaterInfo = { ...rating, ...raterInfo };

                      return (
                        <div key={index} className={`${cardBg[theme]} p-5 rounded-xl border ${borderColor[theme]}`}>
                          <div className="flex items-start gap-4">
                            <div className="w-12 h-12 rounded-full overflow-hidden flex-shrink-0">
                              <img 
                                src={getDiscordAvatar(rating.rater_id, raterInfo.avatar)} 
                                alt={rating.rater_username} 
                                className="w-full h-full object-cover" 
                              />
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center justify-between">
                                <UsernameDisplay user={combinedRaterInfo} />
                                <span className="text-xs text-gray-500">
                                  {rating.timestamp ? new Date(rating.timestamp).toLocaleDateString() : ''}
                                </span>
                              </div>
                              <div className="flex mt-1 mb-2">
                                {renderRating(rating.stars)}
                              </div>
                              {rating.comment && (
                                <p className="text-sm text-gray-400">
                                  {rating.comment}
                                </p>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                    
                    {ratingsData.ratings.length === 0 && (
                      <p className="text-center opacity-70">No reviews yet.</p>
                    )}
                  </div>
                  
                  {/* Pagination Controls */}
                  {ratingsData.total_pages > 1 && (
                    <div className="flex justify-center items-center gap-4 mt-8">
                      <button
                        onClick={() => handlePageChange(currentPage - 1)}
                        disabled={currentPage === 1 || isFetchingPage}
                        className="px-4 py-2 bg-gray-700/50 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Previous
                      </button>
                      <span className="text-gray-400">
                        Page {currentPage} of {ratingsData.total_pages}
                      </span>
                      <button
                        onClick={() => handlePageChange(currentPage + 1)}
                        disabled={currentPage === ratingsData.total_pages || isFetchingPage}
                        className="px-4 py-2 bg-gray-700/50 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Next
                      </button>
                    </div>
                  )}
                  
                  {/* Anonymous Rating Form */}
                  {userData.settings?.allowAnonymousRatings && (
                    <div className={`mt-10 pt-8 border-t ${borderColor[theme]}`}>
                      <h3 className="text-xl font-medium mb-6 text-center">Leave a Review</h3>
                      <form onSubmit={handleRatingSubmit} className="max-w-lg mx-auto">
                        <div className="mb-4">
                          <label className="block text-gray-400 mb-2">Your Rating</label>
                          <div className="flex justify-center items-center gap-2 text-3xl">
                            {[1, 2, 3, 4, 5].map((star) => (
                              <Star
                                key={star}
                                className={`cursor-pointer transition-colors ${
                                  star <= newRating ? ratingColor[theme] : 'text-gray-600 hover:text-gray-400'
                                }`}
                                fill={star <= newRating ? 'currentColor' : 'none'}
                                onClick={() => setNewRating(star)}
                              />
                            ))}
                          </div>
                        </div>
                        <div className="mb-6">
                          <label htmlFor="comment" className="block text-gray-400 mb-2">Your Comment (Optional)</label>
                          <textarea
                            id="comment"
                            value={newComment}
                            onChange={(e) => setNewComment(e.target.value)}
                            placeholder="Tell us about your experience..."
                            rows={4}
                            className={`w-full p-3 rounded-lg bg-transparent border ${borderColor[theme]} focus:ring-2 focus:ring-opacity-50 transition-all`}
                            style={{
                              borderColor: theme === 'custom' ? customThemeColors.primary : undefined,
                              '--tw-ring-color': theme === 'custom' ? customThemeColors.primary : undefined,
                            } as React.CSSProperties}
                          />
                        </div>
                        {submitMessage && (
                          <div className={`text-center p-3 rounded-lg mb-4 ${submitMessage.type === 'success' ? 'bg-green-500/20 text-green-300' : 'bg-red-500/20 text-red-300'}`}>
                            {submitMessage.text}
                          </div>
                        )}
                        <button 
                          type="submit"
                          disabled={isSubmitting}
                          className={`w-full py-3 px-4 rounded-lg font-semibold flex items-center justify-center gap-2 transition-all disabled:opacity-50`}
                          style={{
                            backgroundColor: theme === 'custom' ? customThemeColors.primary : undefined
                          }}
                        >
                          {isSubmitting ? (
                            <Loader2 className="animate-spin" />
                          ) : (
                            <Send size={18} />
                          )}
                          <span>{isSubmitting ? 'Submitting...' : 'Submit Review'}</span>
                        </button>
                      </form>
                    </div>
                  )}
                </div>
              )}
              
              {/* Statistics Tab Content */}
              {activeTab === 'statistics' && ratingsData.distribution && (
                <div>
                  <h3 className="text-xl font-medium mb-6 text-center">
                    Rating Distribution
                  </h3>
                  
                  {/* Rating Distribution */}
                  <div className={`p-6 rounded-xl ${cardBg[theme]} border ${borderColor[theme]} mb-8`}>
                    {[5, 4, 3, 2, 1].map(stars => {
                      const dist = ratingsData.distribution?.find(d => d.stars === stars) || { stars, percentage: 0 };
                      return (
                        <div key={stars} className="flex items-center mb-3 last:mb-0">
                          <div className="flex items-center w-12">
                            <span className={`text-sm ${ratingColor[theme]}`}>{stars} Star</span>
                          </div>
                          <div className="flex-1 mx-4">
                            <div className="w-full bg-gray-700 rounded-full h-2.5">
                              <div 
                                className={`h-2.5 rounded-full ${barColor[theme]}`} 
                                style={{ width: `${dist.percentage}%` }}
                              ></div>
                            </div>
                          </div>
                          <div className="w-12 text-right">
                            <span className="text-gray-400 text-sm">{dist.percentage}%</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  
                  {/* Statistics Cards */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {/* Total Reviews */}
                    <div className={`p-4 rounded-xl ${cardBg[theme]} border ${borderColor[theme]} text-center`}>
                      <div className={`text-2xl font-bold ${ratingColor[theme]}`}>
                        {ratingsData.total_ratings}
                      </div>
                      <div className="text-gray-400 text-xs mt-1">Total Reviews</div>
                    </div>
                    
                    {/* Average Rating */}
                    <div className={`p-4 rounded-xl ${cardBg[theme]} border ${borderColor[theme]} text-center`}>
                      <div className={`text-2xl font-bold ${ratingColor[theme]}`}>
                        {ratingsData.average_rating.toFixed(1)}
                      </div>
                      <div className="text-gray-400 text-xs mt-1">Average Rating</div>
                    </div>
                    
                    {/* Most Common */}
                    <div className={`p-4 rounded-xl ${cardBg[theme]} border ${borderColor[theme]} text-center`}>
                      <div className={`text-2xl font-bold ${ratingColor[theme]}`}>
                        {Math.max(...(ratingsData.distribution?.map(d => d.percentage) || [0]))}%
                      </div>
                      <div className="text-gray-400 text-xs mt-1">Most Common</div>
                    </div>
                    
                    {/* 5-Star Reviews */}
                    <div className={`p-4 rounded-xl ${cardBg[theme]} border ${borderColor[theme]} text-center`}>
                      <div className={`text-2xl font-bold ${ratingColor[theme]}`}>
                        {ratingsData.ratings.filter(r => Math.round(r.stars) === 5).length}
                      </div>
                      <div className="text-gray-400 text-xs mt-1">5-Star Reviews</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 
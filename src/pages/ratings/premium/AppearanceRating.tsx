import React, { useState, useEffect, useRef } from 'react';
import { toast } from 'react-hot-toast';
import { Palette, Star, LayoutTemplate, Check, Sliders, Shield, MessageCircle, Brush, Palette as PaletteIcon, Share2, Copy, CheckCircle2, Download, Upload, Eye, Smartphone, Monitor, X, ArrowLeft } from 'lucide-react';
import { useNavigate, Routes, Route } from 'react-router-dom';
import axios from 'axios';

// أنماط CSS للصفحة عندما يكون السايدبار مخفياً
const fullScreenStyles = {
  marginLeft: 0,
  width: '100%',
  maxWidth: '100%',
  padding: '0 2rem',
};

// أنماط CSS لإخفاء شريط التمرير
const scrollbarHideStyles = `
  /* إخفاء شريط التمرير للكروم وسفاري والإيدج */
  .scrollbar-hide::-webkit-scrollbar {
    display: none;
  }
  
  /* إخفاء شريط التمرير للفايرفوكس */
  .scrollbar-hide {
    -ms-overflow-style: none;  /* لمتصفح إنترنت إكسبلورر والإيدج */
    scrollbar-width: none;  /* للفايرفوكس */
  }
`;

// مكون معاينة الملف الشخصي الكامل
interface ProfilePreviewProps {
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
  isMobile: boolean;
  setFullPreviewMode: React.Dispatch<React.SetStateAction<boolean>>;
}

const ProfilePreview: React.FC<ProfilePreviewProps> = ({
  theme,
  customThemeColors,
  ratingStyle,
  cardStyle,
  fontStyle,
  showAnimation,
  highlightTopRatings,
  isMobile,
  setFullPreviewMode
}) => {
  const [activeTab, setActiveTab] = useState<'reviews' | 'statistics'>('reviews');
  
  return (
    <div className={`${isMobile ? 'w-full' : 'max-w-6xl mx-auto'}`}>
      {/* رأس الصفحة */}
      <div className="flex items-center justify-between p-4 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center">
            <span className="text-white font-bold">C</span>
          </div>
          <h2 className="text-xl font-bold text-white">كلاين</h2>
        </div>
        
        <div className="flex items-center gap-3">
          <button className="p-2 rounded-full hover:bg-gray-800">
            <MessageCircle size={20} className="text-gray-400" />
          </button>
          <div className="w-8 h-8 rounded-full bg-white overflow-hidden">
            <img 
              src="https://randomuser.me/api/portraits/men/32.jpg" 
              alt="User" 
              className="w-full h-full object-cover" 
            />
          </div>
        </div>
      </div>
      
      {/* محتوى الصفحة */}
      <div className={`${isMobile ? 'p-2' : 'p-6'}`}>
        <div 
          style={theme === 'custom' ? {background: `linear-gradient(135deg, ${customThemeColors.primary}, ${customThemeColors.secondary})`} : {}}
          className={`${
          theme === 'dark' ? 'bg-[#1A1A1E]' : 
          theme === 'gradient' ? 'bg-gradient-to-br from-gray-900 to-gray-800' : 
          theme === 'luxury' ? 'bg-gradient-to-br from-gray-900 to-stone-900' :
          theme === 'elegant' ? 'bg-gradient-to-r from-[#232526] to-[#414345]' :
          theme === 'neon' ? 'bg-[#0d0d0f]' :
          theme === 'forest' ? 'bg-gradient-to-br from-green-900 to-emerald-800' :
          theme === 'cosmic' ? 'bg-gradient-to-br from-indigo-900 to-purple-900' :
          theme === 'minimalist' ? 'bg-white' :
          theme === 'tech' ? 'bg-gradient-to-br from-sky-900 to-cyan-800' :
          theme === 'pastel' ? 'bg-gradient-to-br from-pink-200 to-sky-200' :
          theme === 'monochrome' ? 'bg-gradient-to-br from-zinc-700 to-zinc-900' :
          'bg-[#1E1E20]'
        } rounded-2xl shadow-lg ${
          theme === 'gradient' ? 'border border-blue-500/50' : 
          theme === 'dark' ? 'border border-gray-800' : 
          theme === 'luxury' ? 'border-2 border-yellow-500/20' :
          theme === 'elegant' ? 'border border-amber-500/30' : 
          theme === 'neon' ? 'shadow-[0_0_20px_2px_rgba(168,85,247,0.15)] border border-purple-500/30' : 
          theme === 'forest' ? 'border border-emerald-500/30' :
          theme === 'cosmic' ? 'border border-indigo-500/30' :
          theme === 'minimalist' ? 'border border-gray-200' :
          theme === 'tech' ? 'border border-cyan-500/30' :
          theme === 'pastel' ? 'border border-pink-200' :
          theme === 'monochrome' ? 'border border-zinc-700' :
          theme === 'custom' ? 'border border-gray-700/50' :
          'border border-gray-700/50'
        } overflow-hidden`}>
          {/* Header Image */}
          <div 
            style={theme === 'custom' ? {background: `linear-gradient(135deg, ${customThemeColors.primary}, ${customThemeColors.secondary})`} : {}}
            className={`${isMobile ? 'h-48' : 'h-64'} ${
            theme === 'gradient' ? 'bg-gradient-to-br from-gray-900 to-gray-800' : 
            theme === 'dark' ? 'bg-[#1A1A1E]' : 
            theme === 'luxury' ? 'bg-gradient-to-br from-gray-900 to-stone-900' :
            theme === 'elegant' ? 'bg-gradient-to-r from-[#232526] to-[#414345]' :
            theme === 'neon' ? 'bg-[#0d0d0f]' :
            theme === 'forest' ? 'bg-gradient-to-br from-green-900 to-emerald-800' :
            theme === 'cosmic' ? 'bg-gradient-to-br from-indigo-900 to-purple-900' :
            theme === 'minimalist' ? 'bg-[#f5f5f5]' :
            theme === 'tech' ? 'bg-gradient-to-br from-sky-900 to-cyan-800' :
            theme === 'pastel' ? 'bg-gradient-to-br from-pink-200 to-sky-200' :
            theme === 'monochrome' ? 'bg-gradient-to-br from-zinc-700 to-zinc-900' :
            'bg-[#2A2A2E]'
          } rounded-t-2xl relative overflow-hidden`}>
            <div className={`absolute inset-0 ${theme === 'minimalist' || theme === 'pastel' ? 'bg-black/10' : 'bg-black/30'}`}></div>
            {theme === 'neon' && (
              <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-purple-500/50 to-transparent"></div>
            )}
            {theme === 'elegant' && (
              <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-amber-500/30 to-transparent"></div>
            )}
          </div>
          
          {/* Profile Content */}
          <div 
            style={theme === 'custom' ? {background: `linear-gradient(135deg, ${customThemeColors.primary}, ${customThemeColors.secondary})`} : {}}
            className={`px-6 pb-6 pt-6 relative ${
            theme === 'dark' ? 'bg-[#1A1A1E]' : 
            theme === 'gradient' ? 'bg-gradient-to-br from-gray-900 to-gray-800' : 
            theme === 'luxury' ? 'bg-gradient-to-br from-gray-900 to-stone-900' :
            theme === 'elegant' ? 'bg-gradient-to-r from-[#232526] to-[#414345]' :
            theme === 'neon' ? 'bg-[#0d0d0f]' :
            theme === 'forest' ? 'bg-gradient-to-br from-green-900 to-emerald-800' :
            theme === 'cosmic' ? 'bg-gradient-to-br from-indigo-900 to-purple-900' :
            theme === 'minimalist' ? 'bg-white' :
            theme === 'tech' ? 'bg-gradient-to-br from-sky-900 to-cyan-800' :
            theme === 'pastel' ? 'bg-gradient-to-br from-pink-200 to-sky-200' :
            theme === 'monochrome' ? 'bg-gradient-to-br from-zinc-700 to-zinc-900' :
            'bg-[#2A2A2E]'
          }`}>
            {/* Profile Image */}
            <div className={`absolute -top-20 flex ${
              cardStyle === 'modern' ? 'left-1/2 transform -translate-x-1/2 justify-center' : 
              cardStyle === 'compact' ? 'left-6 justify-start' : 
              cardStyle === 'detailed' ? 'right-6 justify-end' : 'left-6 justify-start'
            }`}>
              <div className={`w-32 h-32 rounded-full bg-white p-1 shadow-lg hover:shadow-xl transition-shadow ${
                theme === 'gradient' ? 'border border-blue-500/50' : ''
              }`}>
                <div className="w-full h-full rounded-full flex items-center justify-center overflow-hidden">
                  <img 
                    src="https://cdn.discordapp.com/avatars/1137470473819656293/5fdb66437c22488495ff102924ba0b80.webp?size=4096" 
                    alt="zkr profile" 
                    className="w-full h-full object-cover"
                  />
                </div>
              </div>
            </div>
            
            {/* Content with spacing for image */}
            <div className="mt-20">
              {/* Name and Verification */}
              <div className="flex items-center justify-between mb-1">
                <div className={`flex items-center ${
                  cardStyle === 'modern' ? 'mx-auto' : 
                  cardStyle === 'compact' ? 'mr-auto' : 
                  cardStyle === 'detailed' ? 'ml-auto' : ''
                }`}>
                  <h3 
                    style={theme === 'custom' ? {color: customThemeColors.text} : {}}
                    className={`text-xl font-bold ${
                    theme === 'dark' ? 'text-gray-200' : 
                    theme === 'minimalist' ? 'text-gray-800' :
                    theme === 'pastel' ? 'text-gray-800' :
                    'text-white'
                  } mr-2 font-${fontStyle === 'modern' ? 'medium' : fontStyle === 'classic' ? 'serif' : 'normal'}`}>zkr</h3>
                  <div className={`w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center shadow-md`}>
                    <Check size={12} className="text-white" />
                  </div>
                </div>
                
                {/* Three dots menu - vertical */}
                <div className="relative group">
                  <button className="p-1.5 rounded-full hover:bg-gray-700/50 transition-colors">
                    <div className="flex flex-col space-y-0.5">
                      <div className="w-1.5 h-1.5 rounded-full bg-gray-400"></div>
                      <div className="w-1.5 h-1.5 rounded-full bg-gray-400"></div>
                      <div className="w-1.5 h-1.5 rounded-full bg-gray-400"></div>
                    </div>
                  </button>
                </div>
              </div>
              
              {/* Rating Stars */}
              <div className="mb-1">
                <div className={`flex items-center ${
                  cardStyle === 'modern' ? 'justify-center' : 
                  cardStyle === 'compact' ? 'justify-start' : 
                  cardStyle === 'detailed' ? 'justify-end' : ''
                }`}>
                  <div className="flex">
                    {ratingStyle === 'stars' && (
                      <span 
                        style={theme === 'custom' ? {color: customThemeColors.text} : {}}
                        className={`${
                        theme === 'luxury' ? 'text-yellow-500' :
                        theme === 'elegant' ? 'text-amber-400' :
                        theme === 'neon' ? 'text-purple-400' :
                        theme === 'forest' ? 'text-emerald-400' :
                        theme === 'cosmic' ? 'text-indigo-400' :
                        theme === 'minimalist' ? 'text-gray-600' :
                        theme === 'tech' ? 'text-cyan-400' :
                        theme === 'pastel' ? 'text-pink-400' :
                        theme === 'monochrome' ? 'text-zinc-400' :
                        `text-blue-400`
                      }`}>★★★★★</span>
                    )}
                    {ratingStyle === 'numbers' && (
                      <span 
                        style={theme === 'custom' ? {color: customThemeColors.text} : {}}
                        className={`${
                        theme === 'luxury' ? 'text-yellow-500' :
                        theme === 'elegant' ? 'text-amber-400' :
                        theme === 'neon' ? 'text-purple-400' :
                        theme === 'forest' ? 'text-emerald-400' :
                        theme === 'cosmic' ? 'text-indigo-400' :
                        theme === 'minimalist' ? 'text-gray-600' :
                        theme === 'tech' ? 'text-cyan-400' :
                        theme === 'pastel' ? 'text-pink-400' :
                        theme === 'monochrome' ? 'text-zinc-400' :
                        `text-blue-400`
                      } font-bold`}>4.7<span className="text-gray-400 font-normal text-sm">/5</span></span>
                    )}
                    {ratingStyle === 'bars' && (
                      <div className="w-24 bg-gray-700 h-2 rounded-full overflow-hidden">
                        <div className={`${
                          theme === 'luxury' ? 'bg-yellow-500' :
                          theme === 'elegant' ? 'bg-amber-500' :
                          theme === 'neon' ? 'bg-purple-500' :
                          theme === 'forest' ? 'bg-emerald-500' :
                          theme === 'cosmic' ? 'bg-indigo-500' :
                          theme === 'minimalist' ? 'bg-gray-500' :
                          theme === 'tech' ? 'bg-cyan-500' :
                          theme === 'pastel' ? 'bg-pink-500' :
                          theme === 'monochrome' ? 'bg-zinc-500' :
                          `bg-blue-500`
                        } h-full rounded-full`} style={{ width: '94%' }}></div>
                      </div>
                    )}
                    {ratingStyle === 'emoji' && (
                      <div className="text-xl">😊</div>
                    )}
                    {ratingStyle === 'percent' && (
                      <div className="flex items-center">
                        <span className="text-cyan-500 font-bold">94%</span>
                      </div>
                    )}
                  </div>
                  <span className={`text-gray-400 text-sm ml-2 font-${fontStyle === 'modern' ? 'medium' : fontStyle === 'classic' ? 'serif' : 'normal'}`}>
                    {ratingStyle === 'percent' ? 'تقييم إيجابي' : 
                     ratingStyle === 'numbers' ? 'نجوم' : '4.7 نجوم'}
                  </span>
                </div>
              </div>
              
              {/* Bio */}
              <p className={`text-gray-400 text-sm mb-4 font-${fontStyle === 'modern' ? 'medium' : fontStyle === 'classic' ? 'serif' : 'normal'} ${
                cardStyle === 'modern' ? 'text-center' : 
                cardStyle === 'compact' ? 'text-left' : 
                cardStyle === 'detailed' ? 'text-right' : ''
              }`}>
                مرحباً بكم في صفحتي الشخصية. أنا مطور برمجيات متخصص في تطوير تطبيقات الويب والجوال باستخدام أحدث التقنيات.
              </p>
              
              {/* Tabs */}
              <div className={`flex border-b ${theme === 'dark' ? 'border-gray-800' : 'border-gray-700'}`}>
                <div 
                  onClick={() => setActiveTab('reviews')}
                  style={theme === 'custom' ? {borderColor: activeTab === 'reviews' ? customThemeColors.primary : 'transparent', color: customThemeColors.text} : {}}
                  className={`px-6 py-3 font-medium cursor-pointer hover:text-gray-300 transition-colors ${
                  activeTab === 'reviews' ? `text-gray-300 border-b-2 ${
                    theme === 'elegant' ? 'border-amber-500' :
                    theme === 'neon' ? 'border-purple-500' :
                    theme === 'forest' ? 'border-emerald-500' :
                    theme === 'cosmic' ? 'border-indigo-500' :
                    theme === 'minimalist' ? 'border-gray-500' :
                    theme === 'tech' ? 'border-cyan-500' :
                    theme === 'luxury' ? 'border-yellow-500' :
                    theme === 'pastel' ? 'border-pink-500' :
                    theme === 'monochrome' ? 'border-zinc-500' :
                    theme === 'custom' ? '' :
                    `border-blue-500`
                  }` : 'text-gray-500 border-b-2 border-transparent'
                }`}>
                  Reviews
                </div>
                <div 
                  onClick={() => setActiveTab('statistics')}
                  style={theme === 'custom' ? {borderColor: activeTab === 'statistics' ? customThemeColors.primary : 'transparent', color: customThemeColors.text} : {}}
                  className={`px-6 py-3 font-medium cursor-pointer hover:text-gray-300 transition-colors ${
                  activeTab === 'statistics' ? `text-gray-300 border-b-2 ${
                    theme === 'elegant' ? 'border-amber-500' :
                    theme === 'neon' ? 'border-purple-500' :
                    theme === 'forest' ? 'border-emerald-500' :
                    theme === 'cosmic' ? 'border-indigo-500' :
                    theme === 'minimalist' ? 'border-gray-500' :
                    theme === 'tech' ? 'border-cyan-500' :
                    theme === 'luxury' ? 'border-yellow-500' :
                    theme === 'pastel' ? 'border-pink-500' :
                    theme === 'monochrome' ? 'border-zinc-500' :
                    theme === 'custom' ? '' :
                    `border-blue-500`
                  }` : 'text-gray-500 border-b-2 border-transparent'
                }`}>
                  Statistics
                </div>
              </div>
              
              {/* Tab Content */}
              {activeTab === 'reviews' && (
                <div className="mt-6 space-y-4 max-h-[400px] overflow-y-auto pr-2">
                  <h3 className={`text-lg font-medium ${
                    theme === 'custom' ? 'text-white' : 
                    theme === 'minimalist' ? 'text-gray-800' :
                    theme === 'pastel' ? 'text-gray-800' :
                    'text-gray-200'
                  } mb-3 ${
                    cardStyle === 'modern' ? 'text-center' : 
                    cardStyle === 'compact' ? 'text-left' : 
                    cardStyle === 'detailed' ? 'text-right' : ''
                  }`}>Customer Reviews</h3>
                  
                  {/* Review 1 */}
                  <div className={`${
                    theme === 'minimalist' ? 'bg-gray-100' :
                    theme === 'pastel' ? 'bg-pink-100/30' :
                    theme === 'luxury' ? 'bg-[#1A1A1A]/70' :
                    theme === 'neon' ? 'bg-[#0d0d0f]/80 shadow-[0_0_10px_1px_rgba(168,85,247,0.15)]' :
                    theme === 'custom' ? 'bg-[#1E1E20]/70' :
                    'bg-[#1E1E20]/70'
                  } p-4 rounded-xl border ${
                    theme === 'luxury' ? 'border-yellow-500/20' :
                    theme === 'elegant' ? 'border-amber-500/20' :
                    theme === 'neon' ? 'border-purple-500/20' :
                    theme === 'forest' ? 'border-emerald-500/20' :
                    theme === 'cosmic' ? 'border-indigo-500/20' :
                    theme === 'minimalist' ? 'border-gray-200' :
                    theme === 'tech' ? 'border-cyan-500/20' :
                    theme === 'pastel' ? 'border-pink-200/50' :
                    theme === 'monochrome' ? 'border-zinc-700/50' :
                    'border-gray-700/50'
                  }`}>
                    <div className={`flex items-start ${
                      cardStyle === 'detailed' ? 'flex-row-reverse text-right' : 'text-left'
                    }`}>
                      <div className={`w-10 h-10 rounded-full overflow-hidden flex-shrink-0 ${
                        cardStyle === 'detailed' ? 'mr-0 ml-3' : 'mr-3'
                      }`}>
                        <img src="https://randomuser.me/api/portraits/men/32.jpg" alt="User" className="w-full h-full object-cover" />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <h4 className={`font-medium ${
                            theme === 'custom' ? 'text-white' : 
                            theme === 'minimalist' ? 'text-gray-800' :
                            theme === 'pastel' ? 'text-gray-800' :
                            'text-gray-200'
                          }`}>أحمد محمد</h4>
                          <span className="text-xs text-gray-500">12 مايو 2025</span>
                        </div>
                        <div className={`flex mt-1 mb-2 ${
                          cardStyle === 'modern' ? 'justify-center' : 
                          cardStyle === 'detailed' ? 'justify-end' : ''
                        }`}>
                          <span className={`${
                            theme === 'luxury' ? 'text-yellow-500' : 
                            theme === 'elegant' ? 'text-amber-400' :
                            theme === 'neon' ? 'text-purple-400' :
                            theme === 'forest' ? 'text-emerald-400' :
                            theme === 'cosmic' ? 'text-indigo-400' :
                            theme === 'minimalist' ? 'text-gray-600' :
                            theme === 'tech' ? 'text-cyan-400' :
                            theme === 'pastel' ? 'text-pink-400' :
                            theme === 'monochrome' ? 'text-zinc-400' :
                            theme === 'custom' ? 'text-blue-400' :
                            'text-blue-400'
                          } text-sm`}>★★★★★</span>
                        </div>
                        <p className={`text-sm text-gray-400 ${
                          cardStyle === 'modern' ? 'text-center' : 
                          cardStyle === 'detailed' ? 'text-right' : ''
                        }`}>خدمة ممتازة وسريعة جداً، أنصح بالتعامل معهم. التطبيق سهل الاستخدام والدعم الفني متعاون.</p>
                      </div>
                    </div>
                  </div>
                  
                  {/* Review 2 */}
                  <div className={`${
                    theme === 'minimalist' ? 'bg-gray-100' :
                    theme === 'pastel' ? 'bg-pink-100/30' :
                    theme === 'luxury' ? 'bg-[#1A1A1A]/70' :
                    theme === 'neon' ? 'bg-[#0d0d0f]/80 shadow-[0_0_10px_1px_rgba(168,85,247,0.15)]' :
                    theme === 'custom' ? 'bg-[#1E1E20]/70' :
                    'bg-[#1E1E20]/70'
                  } p-4 rounded-xl border ${
                    theme === 'luxury' ? 'border-yellow-500/20' :
                    theme === 'elegant' ? 'border-amber-500/20' :
                    theme === 'neon' ? 'border-purple-500/20' :
                    theme === 'forest' ? 'border-emerald-500/20' :
                    theme === 'cosmic' ? 'border-indigo-500/20' :
                    theme === 'minimalist' ? 'border-gray-200' :
                    theme === 'tech' ? 'border-cyan-500/20' :
                    theme === 'pastel' ? 'border-pink-200/50' :
                    theme === 'monochrome' ? 'border-zinc-700/50' :
                    'border-gray-700/50'
                  }`}>
                    <div className={`flex items-start ${
                      cardStyle === 'detailed' ? 'flex-row-reverse text-right' : 'text-left'
                    }`}>
                      <div className={`w-10 h-10 rounded-full overflow-hidden flex-shrink-0 ${
                        cardStyle === 'detailed' ? 'mr-0 ml-3' : 'mr-3'
                      }`}>
                        <img src="https://randomuser.me/api/portraits/women/44.jpg" alt="User" className="w-full h-full object-cover" />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <h4 className={`font-medium ${
                            theme === 'custom' ? 'text-white' : 
                            theme === 'minimalist' ? 'text-gray-800' :
                            theme === 'pastel' ? 'text-gray-800' :
                            'text-gray-200'
                          }`}>سارة خالد</h4>
                          <span className="text-xs text-gray-500">5 مايو 2025</span>
                        </div>
                        <div className={`flex mt-1 mb-2 ${
                          cardStyle === 'modern' ? 'justify-center' : 
                          cardStyle === 'detailed' ? 'justify-end' : ''
                        }`}>
                          <span className={`${
                            theme === 'luxury' ? 'text-yellow-500' : 
                            theme === 'elegant' ? 'text-amber-400' :
                            theme === 'neon' ? 'text-purple-400' :
                            theme === 'forest' ? 'text-emerald-400' :
                            theme === 'cosmic' ? 'text-indigo-400' :
                            theme === 'minimalist' ? 'text-gray-600' :
                            theme === 'tech' ? 'text-cyan-400' :
                            theme === 'pastel' ? 'text-pink-400' :
                            theme === 'monochrome' ? 'text-zinc-400' :
                            theme === 'custom' ? 'text-blue-400' :
                            'text-blue-400'
                          } text-sm`}>★★★★<span className="text-gray-600">★</span></span>
                        </div>
                        <p className={`text-sm text-gray-400 ${
                          cardStyle === 'modern' ? 'text-center' : 
                          cardStyle === 'detailed' ? 'text-right' : ''
                        }`}>تجربة رائعة، المنتج وصل بسرعة وبحالة ممتازة. سأتعامل معهم مرة أخرى بالتأكيد.</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Statistics Tab Content */}
              {activeTab === 'statistics' && (
                <div className="mt-6 space-y-6 max-h-[400px] overflow-y-auto pr-2">
                  <h3 className={`text-lg font-medium ${
                    theme === 'custom' ? 'text-white' : 
                    theme === 'minimalist' ? 'text-gray-800' :
                    theme === 'pastel' ? 'text-gray-800' :
                    'text-gray-200'
                  } mb-4 ${
                    cardStyle === 'modern' ? 'text-center' : 
                    cardStyle === 'compact' ? 'text-left' : 
                    cardStyle === 'detailed' ? 'text-right' : ''
                  }`}>Rating Distribution</h3>
                  
                  {/* Rating Distribution */}
                  <div className={`p-4 rounded-xl ${
                    theme === 'minimalist' ? 'bg-gray-100' :
                    theme === 'pastel' ? 'bg-pink-100/30' :
                    theme === 'luxury' ? 'bg-[#1A1A1A]/70' :
                    theme === 'neon' ? 'bg-[#0d0d0f]/80 shadow-[0_0_10px_1px_rgba(168,85,247,0.15)]' :
                    theme === 'custom' ? 'bg-[#1E1E20]/70' :
                    'bg-[#1E1E20]/70'
                  } border ${
                    theme === 'luxury' ? 'border-yellow-500/20' :
                    theme === 'elegant' ? 'border-amber-500/20' :
                    theme === 'neon' ? 'border-purple-500/20' :
                    theme === 'forest' ? 'border-emerald-500/20' :
                    theme === 'cosmic' ? 'border-indigo-500/20' :
                    theme === 'minimalist' ? 'border-gray-200' :
                    theme === 'tech' ? 'border-cyan-500/20' :
                    theme === 'pastel' ? 'border-pink-200/50' :
                    theme === 'monochrome' ? 'border-zinc-700/50' :
                    'border-gray-700/50'
                  }`}>
                    {/* 5 Stars */}
                    <div className="flex items-center mb-2">
                      <div className="flex items-center w-8">
                        <span className={`text-sm ${
                          theme === 'luxury' ? 'text-yellow-500' : 
                          theme === 'elegant' ? 'text-amber-400' :
                          theme === 'neon' ? 'text-purple-400' :
                          theme === 'forest' ? 'text-emerald-400' :
                          theme === 'cosmic' ? 'text-indigo-400' :
                          theme === 'minimalist' ? 'text-gray-600' :
                          theme === 'tech' ? 'text-cyan-400' :
                          theme === 'pastel' ? 'text-pink-400' :
                          theme === 'monochrome' ? 'text-zinc-400' :
                          'text-yellow-400'
                        }`}>5 ★</span>
                      </div>
                      <div className="flex-1 mx-3">
                        <div className="w-full bg-gray-700 rounded-full h-2.5">
                          <div className={`h-2.5 rounded-full ${
                            theme === 'luxury' ? 'bg-yellow-500' :
                            theme === 'elegant' ? 'bg-amber-500' :
                            theme === 'neon' ? 'bg-purple-500' :
                            theme === 'forest' ? 'bg-emerald-500' :
                            theme === 'cosmic' ? 'bg-indigo-500' :
                            theme === 'minimalist' ? 'bg-gray-500' :
                            theme === 'tech' ? 'bg-cyan-500' :
                            theme === 'pastel' ? 'bg-pink-500' :
                            theme === 'monochrome' ? 'bg-zinc-500' :
                            'bg-yellow-500'
                          }`} style={{ width: '67%' }}></div>
                        </div>
                      </div>
                      <div className="w-10 text-right">
                        <span className="text-gray-400 text-sm">67%</span>
                      </div>
                    </div>
                    
                    {/* 4 Stars */}
                    <div className="flex items-center mb-2">
                      <div className="flex items-center w-8">
                        <span className={`text-sm ${
                          theme === 'luxury' ? 'text-yellow-500' : 
                          theme === 'elegant' ? 'text-amber-400' :
                          theme === 'neon' ? 'text-purple-400' :
                          theme === 'forest' ? 'text-emerald-400' :
                          theme === 'cosmic' ? 'text-indigo-400' :
                          theme === 'minimalist' ? 'text-gray-600' :
                          theme === 'tech' ? 'text-cyan-400' :
                          theme === 'pastel' ? 'text-pink-400' :
                          theme === 'monochrome' ? 'text-zinc-400' :
                          'text-yellow-400'
                        }`}>4 ★</span>
                      </div>
                      <div className="flex-1 mx-3">
                        <div className="w-full bg-gray-700 rounded-full h-2.5">
                          <div className={`h-2.5 rounded-full ${
                            theme === 'luxury' ? 'bg-yellow-500' :
                            theme === 'elegant' ? 'bg-amber-500' :
                            theme === 'neon' ? 'bg-purple-500' :
                            theme === 'forest' ? 'bg-emerald-500' :
                            theme === 'cosmic' ? 'bg-indigo-500' :
                            theme === 'minimalist' ? 'bg-gray-500' :
                            theme === 'tech' ? 'bg-cyan-500' :
                            theme === 'pastel' ? 'bg-pink-500' :
                            theme === 'monochrome' ? 'bg-zinc-500' :
                            'bg-yellow-500'
                          }`} style={{ width: '0%' }}></div>
                        </div>
                      </div>
                      <div className="w-10 text-right">
                        <span className="text-gray-400 text-sm">0%</span>
                      </div>
                    </div>
                    
                    {/* 3 Stars */}
                    <div className="flex items-center mb-2">
                      <div className="flex items-center w-8">
                        <span className={`text-sm ${
                          theme === 'luxury' ? 'text-yellow-500' : 
                          theme === 'elegant' ? 'text-amber-400' :
                          theme === 'neon' ? 'text-purple-400' :
                          theme === 'forest' ? 'text-emerald-400' :
                          theme === 'cosmic' ? 'text-indigo-400' :
                          theme === 'minimalist' ? 'text-gray-600' :
                          theme === 'tech' ? 'text-cyan-400' :
                          theme === 'pastel' ? 'text-pink-400' :
                          theme === 'monochrome' ? 'text-zinc-400' :
                          'text-yellow-400'
                        }`}>3 ★</span>
                      </div>
                      <div className="flex-1 mx-3">
                        <div className="w-full bg-gray-700 rounded-full h-2.5">
                          <div className={`h-2.5 rounded-full ${
                            theme === 'luxury' ? 'bg-yellow-500' :
                            theme === 'elegant' ? 'bg-amber-500' :
                            theme === 'neon' ? 'bg-purple-500' :
                            theme === 'forest' ? 'bg-emerald-500' :
                            theme === 'cosmic' ? 'bg-indigo-500' :
                            theme === 'minimalist' ? 'bg-gray-500' :
                            theme === 'tech' ? 'bg-cyan-500' :
                            theme === 'pastel' ? 'bg-pink-500' :
                            theme === 'monochrome' ? 'bg-zinc-500' :
                            'bg-yellow-500'
                          }`} style={{ width: '33%' }}></div>
                        </div>
                      </div>
                      <div className="w-10 text-right">
                        <span className="text-gray-400 text-sm">33%</span>
                      </div>
                    </div>
                    
                    {/* 2 Stars */}
                    <div className="flex items-center mb-2">
                      <div className="flex items-center w-8">
                        <span className={`text-sm ${
                          theme === 'luxury' ? 'text-yellow-500' : 
                          theme === 'elegant' ? 'text-amber-400' :
                          theme === 'neon' ? 'text-purple-400' :
                          theme === 'forest' ? 'text-emerald-400' :
                          theme === 'cosmic' ? 'text-indigo-400' :
                          theme === 'minimalist' ? 'text-gray-600' :
                          theme === 'tech' ? 'text-cyan-400' :
                          theme === 'pastel' ? 'text-pink-400' :
                          theme === 'monochrome' ? 'text-zinc-400' :
                          'text-yellow-400'
                        }`}>2 ★</span>
                      </div>
                      <div className="flex-1 mx-3">
                        <div className="w-full bg-gray-700 rounded-full h-2.5">
                          <div className={`h-2.5 rounded-full ${
                            theme === 'luxury' ? 'bg-yellow-500' :
                            theme === 'elegant' ? 'bg-amber-500' :
                            theme === 'neon' ? 'bg-purple-500' :
                            theme === 'forest' ? 'bg-emerald-500' :
                            theme === 'cosmic' ? 'bg-indigo-500' :
                            theme === 'minimalist' ? 'bg-gray-500' :
                            theme === 'tech' ? 'bg-cyan-500' :
                            theme === 'pastel' ? 'bg-pink-500' :
                            theme === 'monochrome' ? 'bg-zinc-500' :
                            'bg-yellow-500'
                          }`} style={{ width: '0%' }}></div>
                        </div>
                      </div>
                      <div className="w-10 text-right">
                        <span className="text-gray-400 text-sm">0%</span>
                      </div>
                    </div>
                    
                    {/* 1 Star */}
                    <div className="flex items-center">
                      <div className="flex items-center w-8">
                        <span className={`text-sm ${
                          theme === 'luxury' ? 'text-yellow-500' : 
                          theme === 'elegant' ? 'text-amber-400' :
                          theme === 'neon' ? 'text-purple-400' :
                          theme === 'forest' ? 'text-emerald-400' :
                          theme === 'cosmic' ? 'text-indigo-400' :
                          theme === 'minimalist' ? 'text-gray-600' :
                          theme === 'tech' ? 'text-cyan-400' :
                          theme === 'pastel' ? 'text-pink-400' :
                          theme === 'monochrome' ? 'text-zinc-400' :
                          'text-yellow-400'
                        }`}>1 ★</span>
                      </div>
                      <div className="flex-1 mx-3">
                        <div className="w-full bg-gray-700 rounded-full h-2.5">
                          <div className={`h-2.5 rounded-full ${
                            theme === 'luxury' ? 'bg-yellow-500' :
                            theme === 'elegant' ? 'bg-amber-500' :
                            theme === 'neon' ? 'bg-purple-500' :
                            theme === 'forest' ? 'bg-emerald-500' :
                            theme === 'cosmic' ? 'bg-indigo-500' :
                            theme === 'minimalist' ? 'bg-gray-500' :
                            theme === 'tech' ? 'bg-cyan-500' :
                            theme === 'pastel' ? 'bg-pink-500' :
                            theme === 'monochrome' ? 'bg-zinc-500' :
                            'bg-yellow-500'
                          }`} style={{ width: '0%' }}></div>
                        </div>
                      </div>
                      <div className="w-10 text-right">
                        <span className="text-gray-400 text-sm">0%</span>
                      </div>
                    </div>
                  </div>
                  
                  {/* Statistics Cards */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
                    {/* Total Reviews */}
                    <div className={`p-4 rounded-xl ${
                      theme === 'minimalist' ? 'bg-gray-100' :
                      theme === 'pastel' ? 'bg-pink-100/30' :
                      theme === 'luxury' ? 'bg-[#1A1A1A]/70' :
                      theme === 'neon' ? 'bg-[#0d0d0f]/80 shadow-[0_0_10px_1px_rgba(168,85,247,0.15)]' :
                      theme === 'custom' ? 'bg-[#1E1E20]/70' :
                      'bg-[#1E1E20]/70'
                    } border ${
                      theme === 'luxury' ? 'border-yellow-500/20' :
                      theme === 'elegant' ? 'border-amber-500/20' :
                      theme === 'neon' ? 'border-purple-500/20' :
                      theme === 'forest' ? 'border-emerald-500/20' :
                      theme === 'cosmic' ? 'border-indigo-500/20' :
                      theme === 'minimalist' ? 'border-gray-200' :
                      theme === 'tech' ? 'border-cyan-500/20' :
                      theme === 'pastel' ? 'border-pink-200/50' :
                      theme === 'monochrome' ? 'border-zinc-700/50' :
                      'border-gray-700/50'
                    } text-center`}>
                      <div className={`text-2xl font-bold ${
                        theme === 'luxury' ? 'text-yellow-500' : 
                        theme === 'elegant' ? 'text-amber-400' :
                        theme === 'neon' ? 'text-purple-400' :
                        theme === 'forest' ? 'text-emerald-400' :
                        theme === 'cosmic' ? 'text-indigo-400' :
                        theme === 'minimalist' ? 'text-gray-800' :
                        theme === 'tech' ? 'text-cyan-400' :
                        theme === 'pastel' ? 'text-pink-500' :
                        theme === 'monochrome' ? 'text-zinc-300' :
                        'text-yellow-400'
                      }`}>3</div>
                      <div className="text-gray-400 text-xs mt-1">Total Reviews</div>
                    </div>
                    
                    {/* Average Rating */}
                    <div className={`p-4 rounded-xl ${
                      theme === 'minimalist' ? 'bg-gray-100' :
                      theme === 'pastel' ? 'bg-pink-100/30' :
                      theme === 'luxury' ? 'bg-[#1A1A1A]/70' :
                      theme === 'neon' ? 'bg-[#0d0d0f]/80 shadow-[0_0_10px_1px_rgba(168,85,247,0.15)]' :
                      theme === 'custom' ? 'bg-[#1E1E20]/70' :
                      'bg-[#1E1E20]/70'
                    } border ${
                      theme === 'luxury' ? 'border-yellow-500/20' :
                      theme === 'elegant' ? 'border-amber-500/20' :
                      theme === 'neon' ? 'border-purple-500/20' :
                      theme === 'forest' ? 'border-emerald-500/20' :
                      theme === 'cosmic' ? 'border-indigo-500/20' :
                      theme === 'minimalist' ? 'border-gray-200' :
                      theme === 'tech' ? 'border-cyan-500/20' :
                      theme === 'pastel' ? 'border-pink-200/50' :
                      theme === 'monochrome' ? 'border-zinc-700/50' :
                      'border-gray-700/50'
                    } text-center`}>
                      <div className={`text-2xl font-bold ${
                        theme === 'luxury' ? 'text-yellow-500' : 
                        theme === 'elegant' ? 'text-amber-400' :
                        theme === 'neon' ? 'text-purple-400' :
                        theme === 'forest' ? 'text-emerald-400' :
                        theme === 'cosmic' ? 'text-indigo-400' :
                        theme === 'minimalist' ? 'text-gray-800' :
                        theme === 'tech' ? 'text-cyan-400' :
                        theme === 'pastel' ? 'text-pink-500' :
                        theme === 'monochrome' ? 'text-zinc-300' :
                        'text-yellow-400'
                      }`}>4.3</div>
                      <div className="text-gray-400 text-xs mt-1">Average Rating</div>
                    </div>
                    
                    {/* Most Common */}
                    <div className={`p-4 rounded-xl ${
                      theme === 'minimalist' ? 'bg-gray-100' :
                      theme === 'pastel' ? 'bg-pink-100/30' :
                      theme === 'luxury' ? 'bg-[#1A1A1A]/70' :
                      theme === 'neon' ? 'bg-[#0d0d0f]/80 shadow-[0_0_10px_1px_rgba(168,85,247,0.15)]' :
                      theme === 'custom' ? 'bg-[#1E1E20]/70' :
                      'bg-[#1E1E20]/70'
                    } border ${
                      theme === 'luxury' ? 'border-yellow-500/20' :
                      theme === 'elegant' ? 'border-amber-500/20' :
                      theme === 'neon' ? 'border-purple-500/20' :
                      theme === 'forest' ? 'border-emerald-500/20' :
                      theme === 'cosmic' ? 'border-indigo-500/20' :
                      theme === 'minimalist' ? 'border-gray-200' :
                      theme === 'tech' ? 'border-cyan-500/20' :
                      theme === 'pastel' ? 'border-pink-200/50' :
                      theme === 'monochrome' ? 'border-zinc-700/50' :
                      'border-gray-700/50'
                    } text-center`}>
                      <div className={`text-2xl font-bold ${
                        theme === 'luxury' ? 'text-yellow-500' : 
                        theme === 'elegant' ? 'text-amber-400' :
                        theme === 'neon' ? 'text-purple-400' :
                        theme === 'forest' ? 'text-emerald-400' :
                        theme === 'cosmic' ? 'text-indigo-400' :
                        theme === 'minimalist' ? 'text-gray-800' :
                        theme === 'tech' ? 'text-cyan-400' :
                        theme === 'pastel' ? 'text-pink-500' :
                        theme === 'monochrome' ? 'text-zinc-300' :
                        'text-yellow-400'
                      }`}>67%</div>
                      <div className="text-gray-400 text-xs mt-1">Most Common</div>
                    </div>
                    
                    {/* 5-Star Reviews */}
                    <div className={`p-4 rounded-xl ${
                      theme === 'minimalist' ? 'bg-gray-100' :
                      theme === 'pastel' ? 'bg-pink-100/30' :
                      theme === 'luxury' ? 'bg-[#1A1A1A]/70' :
                      theme === 'neon' ? 'bg-[#0d0d0f]/80 shadow-[0_0_10px_1px_rgba(168,85,247,0.15)]' :
                      theme === 'custom' ? 'bg-[#1E1E20]/70' :
                      'bg-[#1E1E20]/70'
                    } border ${
                      theme === 'luxury' ? 'border-yellow-500/20' :
                      theme === 'elegant' ? 'border-amber-500/20' :
                      theme === 'neon' ? 'border-purple-500/20' :
                      theme === 'forest' ? 'border-emerald-500/20' :
                      theme === 'cosmic' ? 'border-indigo-500/20' :
                      theme === 'minimalist' ? 'border-gray-200' :
                      theme === 'tech' ? 'border-cyan-500/20' :
                      theme === 'pastel' ? 'border-pink-200/50' :
                      theme === 'monochrome' ? 'border-zinc-700/50' :
                      'border-gray-700/50'
                    } text-center`}>
                      <div className={`text-2xl font-bold ${
                        theme === 'luxury' ? 'text-yellow-500' : 
                        theme === 'elegant' ? 'text-amber-400' :
                        theme === 'neon' ? 'text-purple-400' :
                        theme === 'forest' ? 'text-emerald-400' :
                        theme === 'cosmic' ? 'text-indigo-400' :
                        theme === 'minimalist' ? 'text-gray-800' :
                        theme === 'tech' ? 'text-cyan-400' :
                        theme === 'pastel' ? 'text-pink-500' :
                        theme === 'monochrome' ? 'text-zinc-300' :
                        'text-yellow-400'
                      }`}>2</div>
                      <div className="text-gray-400 text-xs mt-1">5-Star Reviews</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      
      {/* أزرار التحكم السفلية */}
      <div className="mt-8 flex justify-center">
        <button 
          onClick={() => setFullPreviewMode(false)}
          className="px-6 py-2.5 bg-gray-700 text-white font-medium rounded-lg hover:bg-gray-600 transition-all shadow-md hover:shadow-lg transform hover:-translate-y-0.5 flex items-center gap-2"
        >
          <X size={18} />
          إغلاق المعاينة
        </button>
      </div>
    </div>
  );
};

// مكون صفحة المعاينة الكاملة
const FullPreviewPage: React.FC<{
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
  goBack: () => void;
}> = ({
  theme,
  customThemeColors,
  ratingStyle,
  cardStyle,
  fontStyle,
  showAnimation,
  highlightTopRatings,
  goBack
}) => {
  const [previewDevice, setPreviewDevice] = useState<'desktop' | 'mobile'>('desktop');
  const [activeTab, setActiveTab] = useState<'reviews' | 'statistics'>('reviews');
  
  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      {/* Top Control Bar */}
      <div className="bg-[#1A1A1E] p-4 flex items-center justify-between border-b border-gray-800 sticky top-0 z-50">
        <div className="flex items-center gap-4">
          <button 
            onClick={goBack}
            className="p-2 rounded-full hover:bg-gray-800 transition-colors flex items-center gap-2"
            title="Go back to settings"
          >
            <ArrowLeft size={20} className="text-white" />
            <span className="text-white font-medium">Back to Settings</span>
          </button>
          <h3 className="text-lg font-bold text-white">Full Page Preview</h3>
        </div>
        
        {/* Device Size Toggle */}
        <div className="flex items-center gap-2 bg-[#252530] p-1 rounded-lg">
          <button 
            onClick={() => setPreviewDevice('desktop')}
            className={`p-2 rounded-lg flex items-center gap-1 ${previewDevice === 'desktop' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`}
            title="Desktop view"
          >
            <Monitor size={18} />
            <span className="text-sm">Desktop</span>
          </button>
          <button 
            onClick={() => setPreviewDevice('mobile')}
            className={`p-2 rounded-lg flex items-center gap-1 ${previewDevice === 'mobile' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`}
            title="Mobile view"
          >
            <Smartphone size={18} />
            <span className="text-sm">Mobile</span>
          </button>
        </div>
      </div>
      
      {/* Preview Content */}
      <div className="w-full flex-1 flex items-center justify-center">
        <div className={`transition-all duration-300 ${
          previewDevice === 'mobile' ? 'max-w-[390px] p-4' : 'w-full h-full'
        }`}>
          {/* Profile Preview */}
          <div 
            style={theme === 'custom' ? {background: `linear-gradient(135deg, ${customThemeColors.primary}, ${customThemeColors.secondary})`} : {}}
            className={`${
            theme === 'dark' ? 'bg-[#1A1A1E]' : 
            theme === 'gradient' ? 'bg-gradient-to-br from-gray-900 to-gray-800' : 
            theme === 'luxury' ? 'bg-gradient-to-br from-gray-900 to-stone-900' :
            theme === 'elegant' ? 'bg-gradient-to-r from-[#232526] to-[#414345]' :
            theme === 'neon' ? 'bg-[#0d0d0f]' :
            theme === 'forest' ? 'bg-gradient-to-br from-green-900 to-emerald-800' :
            theme === 'cosmic' ? 'bg-gradient-to-br from-indigo-900 to-purple-900' :
            theme === 'minimalist' ? 'bg-white' :
            theme === 'tech' ? 'bg-gradient-to-br from-sky-900 to-cyan-800' :
            theme === 'pastel' ? 'bg-gradient-to-br from-pink-200 to-sky-200' :
            theme === 'monochrome' ? 'bg-gradient-to-br from-zinc-700 to-zinc-900' :
            'bg-[#1E1E20]'
          } ${previewDevice === 'mobile' ? 'rounded-2xl' : ''} shadow-lg ${
            theme === 'gradient' ? 'border border-blue-500/50' : 
            theme === 'dark' ? 'border border-gray-800' : 
            theme === 'luxury' ? 'border-2 border-yellow-500/20' :
            theme === 'elegant' ? 'border border-amber-500/30' : 
            theme === 'neon' ? 'shadow-[0_0_20px_2px_rgba(168,85,247,0.15)] border border-purple-500/30' : 
            theme === 'forest' ? 'border border-emerald-500/30' :
            theme === 'cosmic' ? 'border border-indigo-500/30' :
            theme === 'minimalist' ? 'border border-gray-200' :
            theme === 'tech' ? 'border border-cyan-500/30' :
            theme === 'pastel' ? 'border border-pink-200' :
            theme === 'monochrome' ? 'border border-zinc-700' :
            theme === 'custom' ? 'border border-gray-700/50' :
            'border border-gray-700/50'
          } overflow-hidden`}>
            {/* Header Image */}
            <div 
              style={theme === 'custom' ? {background: `linear-gradient(135deg, ${customThemeColors.primary}, ${customThemeColors.secondary})`} : {}}
              className={`h-48 ${
              theme === 'gradient' ? 'bg-gradient-to-br from-gray-900 to-gray-800' : 
              theme === 'dark' ? 'bg-[#1A1A1E]' : 
              theme === 'luxury' ? 'bg-gradient-to-br from-gray-900 to-stone-900' :
              theme === 'elegant' ? 'bg-gradient-to-r from-[#232526] to-[#414345]' :
              theme === 'neon' ? 'bg-[#0d0d0f]' :
              theme === 'forest' ? 'bg-gradient-to-br from-green-900 to-emerald-800' :
              theme === 'cosmic' ? 'bg-gradient-to-br from-indigo-900 to-purple-900' :
              theme === 'minimalist' ? 'bg-[#f5f5f5]' :
              theme === 'tech' ? 'bg-gradient-to-br from-sky-900 to-cyan-800' :
              theme === 'pastel' ? 'bg-gradient-to-br from-pink-200 to-sky-200' :
              theme === 'monochrome' ? 'bg-gradient-to-br from-zinc-700 to-zinc-900' :
              'bg-[#2A2A2E]'
            } rounded-t-2xl relative overflow-hidden`}>
              <div className={`absolute inset-0 ${theme === 'minimalist' || theme === 'pastel' ? 'bg-black/10' : 'bg-black/30'}`}></div>
              {theme === 'neon' && (
                <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-purple-500/50 to-transparent"></div>
              )}
              {theme === 'elegant' && (
                <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-amber-500/30 to-transparent"></div>
              )}
            </div>
            
            {/* Profile Content */}
            <div 
              style={theme === 'custom' ? {background: `linear-gradient(135deg, ${customThemeColors.primary}, ${customThemeColors.secondary})`} : {}}
              className={`px-6 pb-6 pt-6 relative ${
              theme === 'dark' ? 'bg-[#1A1A1E]' : 
              theme === 'gradient' ? 'bg-gradient-to-br from-gray-900 to-gray-800' : 
              theme === 'luxury' ? 'bg-gradient-to-br from-gray-900 to-stone-900' :
              theme === 'elegant' ? 'bg-gradient-to-r from-[#232526] to-[#414345]' :
              theme === 'neon' ? 'bg-[#0d0d0f]' :
              theme === 'forest' ? 'bg-gradient-to-br from-green-900 to-emerald-800' :
              theme === 'cosmic' ? 'bg-gradient-to-br from-indigo-900 to-purple-900' :
              theme === 'minimalist' ? 'bg-white' :
              theme === 'tech' ? 'bg-gradient-to-br from-sky-900 to-cyan-800' :
              theme === 'pastel' ? 'bg-gradient-to-br from-pink-200 to-sky-200' :
              theme === 'monochrome' ? 'bg-gradient-to-br from-zinc-700 to-zinc-900' :
              'bg-[#2A2A2E]'
            }`}>
              {/* Profile Image */}
              <div className={`absolute -top-20 flex ${
                cardStyle === 'modern' ? 'left-1/2 transform -translate-x-1/2 justify-center' : 
                cardStyle === 'compact' ? 'left-6 justify-start' : 
                cardStyle === 'detailed' ? 'right-6 justify-end' : 'left-6 justify-start'
              }`}>
                <div className={`w-32 h-32 rounded-full bg-white p-1 shadow-lg hover:shadow-xl transition-shadow ${
                  theme === 'gradient' ? 'border border-blue-500/50' : ''
                }`}>
                  <div className="w-full h-full rounded-full flex items-center justify-center overflow-hidden">
                    <img 
                      src="https://cdn.discordapp.com/avatars/1137470473819656293/5fdb66437c22488495ff102924ba0b80.webp?size=4096" 
                      alt="zkr profile" 
                      className="w-full h-full object-cover"
                    />
                  </div>
                </div>
              </div>
              
              {/* Content with spacing for image */}
              <div className="mt-20">
                {/* Name and Verification */}
                <div className="flex items-center justify-between mb-1">
                  <div className={`flex items-center ${
                    cardStyle === 'modern' ? 'mx-auto' : 
                    cardStyle === 'compact' ? 'mr-auto' : 
                    cardStyle === 'detailed' ? 'ml-auto' : ''
                  }`}>
                    <h3 
                      style={theme === 'custom' ? {color: customThemeColors.text} : {}}
                      className={`text-xl font-bold ${
                      theme === 'dark' ? 'text-gray-200' : 
                      theme === 'minimalist' ? 'text-gray-800' :
                      theme === 'pastel' ? 'text-gray-800' :
                      'text-white'
                    } mr-2 font-${fontStyle === 'modern' ? 'medium' : fontStyle === 'classic' ? 'serif' : 'normal'}`}>zkr</h3>
                    <div className={`w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center shadow-md`}>
                      <Check size={12} className="text-white" />
                    </div>
                  </div>
                  
                  {/* Three dots menu - vertical */}
                  <div className="relative group">
                    <button className="p-1.5 rounded-full hover:bg-gray-700/50 transition-colors">
                      <div className="flex flex-col space-y-0.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-gray-400"></div>
                        <div className="w-1.5 h-1.5 rounded-full bg-gray-400"></div>
                        <div className="w-1.5 h-1.5 rounded-full bg-gray-400"></div>
                      </div>
                    </button>
                  </div>
                </div>
                
                {/* Rating Stars */}
                <div className="mb-1">
                  <div className={`flex items-center ${
                    cardStyle === 'modern' ? 'justify-center' : 
                    cardStyle === 'compact' ? 'justify-start' : 
                    cardStyle === 'detailed' ? 'justify-end' : ''
                  }`}>
                    <div className="flex">
                      {ratingStyle === 'stars' && (
                        <span 
                          style={theme === 'custom' ? {color: customThemeColors.text} : {}}
                          className={`${
                          theme === 'luxury' ? 'text-yellow-500' :
                          theme === 'elegant' ? 'text-amber-400' :
                          theme === 'neon' ? 'text-purple-400' :
                          theme === 'forest' ? 'text-emerald-400' :
                          theme === 'cosmic' ? 'text-indigo-400' :
                          theme === 'minimalist' ? 'text-gray-600' :
                          theme === 'tech' ? 'text-cyan-400' :
                          theme === 'pastel' ? 'text-pink-400' :
                          theme === 'monochrome' ? 'text-zinc-400' :
                          `text-blue-400`
                        }`}>★★★★★</span>
                      )}
                      {ratingStyle === 'numbers' && (
                        <span 
                          style={theme === 'custom' ? {color: customThemeColors.text} : {}}
                          className={`${
                          theme === 'luxury' ? 'text-yellow-500' :
                          theme === 'elegant' ? 'text-amber-400' :
                          theme === 'neon' ? 'text-purple-400' :
                          theme === 'forest' ? 'text-emerald-400' :
                          theme === 'cosmic' ? 'text-indigo-400' :
                          theme === 'minimalist' ? 'text-gray-600' :
                          theme === 'tech' ? 'text-cyan-400' :
                          theme === 'pastel' ? 'text-pink-400' :
                          theme === 'monochrome' ? 'text-zinc-400' :
                          `text-blue-400`
                        } font-bold`}>4.7<span className="text-gray-400 font-normal text-sm">/5</span></span>
                      )}
                      {ratingStyle === 'bars' && (
                        <div className="w-24 bg-gray-700 h-2 rounded-full overflow-hidden">
                          <div className={`${
                            theme === 'luxury' ? 'bg-yellow-500' :
                            theme === 'elegant' ? 'bg-amber-500' :
                            theme === 'neon' ? 'bg-purple-500' :
                            theme === 'forest' ? 'bg-emerald-500' :
                            theme === 'cosmic' ? 'bg-indigo-500' :
                            theme === 'minimalist' ? 'bg-gray-500' :
                            theme === 'tech' ? 'bg-cyan-500' :
                            theme === 'pastel' ? 'bg-pink-500' :
                            theme === 'monochrome' ? 'bg-zinc-500' :
                            `bg-blue-500`
                          } h-full rounded-full`} style={{ width: '94%' }}></div>
                        </div>
                      )}
                      {ratingStyle === 'emoji' && (
                        <div className="text-xl">😊</div>
                      )}
                      {ratingStyle === 'percent' && (
                        <div className="flex items-center">
                          <span className="text-cyan-500 font-bold">94%</span>
                        </div>
                      )}
                    </div>
                    <span className={`text-gray-400 text-sm ml-2 font-${fontStyle === 'modern' ? 'medium' : fontStyle === 'classic' ? 'serif' : 'normal'}`}>
                      {ratingStyle === 'percent' ? 'Positive Rating' : 
                       ratingStyle === 'numbers' ? 'stars' : '4.7 stars'}
                    </span>
                  </div>
                </div>
                
                {/* Bio */}
                <p className={`text-gray-400 text-sm mb-4 font-${fontStyle === 'modern' ? 'medium' : fontStyle === 'classic' ? 'serif' : 'normal'} ${
                  cardStyle === 'modern' ? 'text-center' : 
                  cardStyle === 'compact' ? 'text-left' : 
                  cardStyle === 'detailed' ? 'text-right' : ''
                }`}>
                  Hello and welcome to my profile. I'm a software developer specializing in web and mobile app development using the latest technologies.
                </p>
                
                {/* Tabs */}
                <div className={`flex border-b ${theme === 'dark' ? 'border-gray-800' : 'border-gray-700'}`}>
                  <div 
                    style={theme === 'custom' ? {borderColor: activeTab === 'reviews' ? customThemeColors.primary : 'transparent', color: customThemeColors.text} : {}}
                    className={`px-6 py-3 font-medium cursor-pointer hover:text-gray-300 transition-colors ${
                    activeTab === 'reviews' ? `text-gray-300 border-b-2 ${
                      theme === 'elegant' ? 'border-amber-500' :
                      theme === 'neon' ? 'border-purple-500' :
                      theme === 'forest' ? 'border-emerald-500' :
                      theme === 'cosmic' ? 'border-indigo-500' :
                      theme === 'minimalist' ? 'border-gray-500' :
                      theme === 'tech' ? 'border-cyan-500' :
                      theme === 'luxury' ? 'border-yellow-500' :
                      theme === 'pastel' ? 'border-pink-500' :
                      theme === 'monochrome' ? 'border-zinc-500' :
                      theme === 'custom' ? '' :
                      `border-blue-500`
                    }` : 'text-gray-500 border-b-2 border-transparent'
                  }`}>
                    Reviews
                  </div>
                  <div 
                    style={theme === 'custom' ? {borderColor: activeTab === 'statistics' ? customThemeColors.primary : 'transparent', color: customThemeColors.text} : {}}
                    className={`px-6 py-3 font-medium cursor-pointer hover:text-gray-300 transition-colors ${
                    activeTab === 'statistics' ? `text-gray-300 border-b-2 ${
                      theme === 'elegant' ? 'border-amber-500' :
                      theme === 'neon' ? 'border-purple-500' :
                      theme === 'forest' ? 'border-emerald-500' :
                      theme === 'cosmic' ? 'border-indigo-500' :
                      theme === 'minimalist' ? 'border-gray-500' :
                      theme === 'tech' ? 'border-cyan-500' :
                      theme === 'luxury' ? 'border-yellow-500' :
                      theme === 'pastel' ? 'border-pink-500' :
                      theme === 'monochrome' ? 'border-zinc-500' :
                      theme === 'custom' ? '' :
                      `border-blue-500`
                    }` : 'text-gray-500 border-b-2 border-transparent'
                  }`}>
                    Statistics
                  </div>
                </div>
                
                {/* Tab Content */}
                {activeTab === 'reviews' && (
                  <div className="mt-6 space-y-4 max-h-[400px] overflow-y-auto pr-2">
                    <h3 className={`text-lg font-medium ${
                      theme === 'custom' ? 'text-white' : 
                      theme === 'minimalist' ? 'text-gray-800' :
                      theme === 'pastel' ? 'text-gray-800' :
                      'text-gray-200'
                    } mb-3 ${
                      cardStyle === 'modern' ? 'text-center' : 
                      cardStyle === 'compact' ? 'text-left' : 
                      cardStyle === 'detailed' ? 'text-right' : ''
                    }`}>Customer Reviews</h3>
                    
                    {/* Review 1 */}
                    <div className={`${
                      theme === 'minimalist' ? 'bg-gray-100' :
                      theme === 'pastel' ? 'bg-pink-100/30' :
                      theme === 'luxury' ? 'bg-[#1A1A1A]/70' :
                      theme === 'neon' ? 'bg-[#0d0d0f]/80 shadow-[0_0_10px_1px_rgba(168,85,247,0.15)]' :
                      theme === 'custom' ? 'bg-[#1E1E20]/70' :
                      'bg-[#1E1E20]/70'
                    } p-4 rounded-xl border ${
                      theme === 'luxury' ? 'border-yellow-500/20' :
                      theme === 'elegant' ? 'border-amber-500/20' :
                      theme === 'neon' ? 'border-purple-500/20' :
                      theme === 'forest' ? 'border-emerald-500/20' :
                      theme === 'cosmic' ? 'border-indigo-500/20' :
                      theme === 'minimalist' ? 'border-gray-200' :
                      theme === 'tech' ? 'border-cyan-500/20' :
                      theme === 'pastel' ? 'border-pink-200/50' :
                      theme === 'monochrome' ? 'border-zinc-700/50' :
                      'border-gray-700/50'
                    }`}>
                      <div className={`flex items-start ${
                        cardStyle === 'detailed' ? 'flex-row-reverse text-right' : 'text-left'
                      }`}>
                        <div className={`w-10 h-10 rounded-full overflow-hidden flex-shrink-0 ${
                          cardStyle === 'detailed' ? 'mr-0 ml-3' : 'mr-3'
                        }`}>
                          <img src="https://randomuser.me/api/portraits/men/32.jpg" alt="User" className="w-full h-full object-cover" />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <h4 className={`font-medium ${
                              theme === 'custom' ? 'text-white' : 
                              theme === 'minimalist' ? 'text-gray-800' :
                              theme === 'pastel' ? 'text-gray-800' :
                              'text-gray-200'
                            }`}>Ahmed Mohammed</h4>
                            <span className="text-xs text-gray-500">May 12, 2025</span>
                          </div>
                          <div className={`flex mt-1 mb-2 ${
                            cardStyle === 'modern' ? 'justify-center' : 
                            cardStyle === 'detailed' ? 'justify-end' : ''
                          }`}>
                            <span className={`${
                              theme === 'luxury' ? 'text-yellow-500' : 
                              theme === 'elegant' ? 'text-amber-400' :
                              theme === 'neon' ? 'text-purple-400' :
                              theme === 'forest' ? 'text-emerald-400' :
                              theme === 'cosmic' ? 'text-indigo-400' :
                              theme === 'minimalist' ? 'text-gray-600' :
                              theme === 'tech' ? 'text-cyan-400' :
                              theme === 'pastel' ? 'text-pink-400' :
                              theme === 'monochrome' ? 'text-zinc-400' :
                              theme === 'custom' ? 'text-blue-400' :
                              'text-blue-400'
                            } text-sm`}>★★★★★</span>
                          </div>
                          <p className={`text-sm text-gray-400 ${
                            cardStyle === 'modern' ? 'text-center' : 
                            cardStyle === 'detailed' ? 'text-right' : ''
                          }`}>Excellent service and very fast, I recommend dealing with them. The application is easy to use and the technical support is cooperative.</p>
                        </div>
                      </div>
                    </div>
                    
                    {/* Review 2 */}
                    <div className={`${
                      theme === 'minimalist' ? 'bg-gray-100' :
                      theme === 'pastel' ? 'bg-pink-100/30' :
                      theme === 'luxury' ? 'bg-[#1A1A1A]/70' :
                      theme === 'neon' ? 'bg-[#0d0d0f]/80 shadow-[0_0_10px_1px_rgba(168,85,247,0.15)]' :
                      theme === 'custom' ? 'bg-[#1E1E20]/70' :
                      'bg-[#1E1E20]/70'
                    } p-4 rounded-xl border ${
                      theme === 'luxury' ? 'border-yellow-500/20' :
                      theme === 'elegant' ? 'border-amber-500/20' :
                      theme === 'neon' ? 'border-purple-500/20' :
                      theme === 'forest' ? 'border-emerald-500/20' :
                      theme === 'cosmic' ? 'border-indigo-500/20' :
                      theme === 'minimalist' ? 'border-gray-200' :
                      theme === 'tech' ? 'border-cyan-500/20' :
                      theme === 'pastel' ? 'border-pink-200/50' :
                      theme === 'monochrome' ? 'border-zinc-700/50' :
                      'border-gray-700/50'
                    }`}>
                      <div className={`flex items-start ${
                        cardStyle === 'detailed' ? 'flex-row-reverse text-right' : 'text-left'
                      }`}>
                        <div className={`w-10 h-10 rounded-full overflow-hidden flex-shrink-0 ${
                          cardStyle === 'detailed' ? 'mr-0 ml-3' : 'mr-3'
                        }`}>
                          <img src="https://randomuser.me/api/portraits/women/44.jpg" alt="User" className="w-full h-full object-cover" />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <h4 className={`font-medium ${
                              theme === 'custom' ? 'text-white' : 
                              theme === 'minimalist' ? 'text-gray-800' :
                              theme === 'pastel' ? 'text-gray-800' :
                              'text-gray-200'
                            }`}>Sarah Khalid</h4>
                            <span className="text-xs text-gray-500">May 5, 2025</span>
                          </div>
                          <div className={`flex mt-1 mb-2 ${
                            cardStyle === 'modern' ? 'justify-center' : 
                            cardStyle === 'detailed' ? 'justify-end' : ''
                          }`}>
                            <span className={`${
                              theme === 'luxury' ? 'text-yellow-500' : 
                              theme === 'elegant' ? 'text-amber-400' :
                              theme === 'neon' ? 'text-purple-400' :
                              theme === 'forest' ? 'text-emerald-400' :
                              theme === 'cosmic' ? 'text-indigo-400' :
                              theme === 'minimalist' ? 'text-gray-600' :
                              theme === 'tech' ? 'text-cyan-400' :
                              theme === 'pastel' ? 'text-pink-400' :
                              theme === 'monochrome' ? 'text-zinc-400' :
                              theme === 'custom' ? 'text-blue-400' :
                              'text-blue-400'
                            } text-sm`}>★★★★<span className="text-gray-600">★</span></span>
                          </div>
                          <p className={`text-sm text-gray-400 ${
                            cardStyle === 'modern' ? 'text-center' : 
                            cardStyle === 'detailed' ? 'text-right' : ''
                          }`}>Great experience, the product arrived quickly and in excellent condition. I will definitely deal with them again.</p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Statistics Tab Content */}
                {activeTab === 'statistics' && (
                  <div className="mt-6 space-y-6 max-h-[400px] overflow-y-auto pr-2">
                    <h3 className={`text-lg font-medium ${
                      theme === 'custom' ? 'text-white' : 
                      theme === 'minimalist' ? 'text-gray-800' :
                      theme === 'pastel' ? 'text-gray-800' :
                      'text-gray-200'
                    } mb-4 ${
                      cardStyle === 'modern' ? 'text-center' : 
                      cardStyle === 'compact' ? 'text-left' : 
                      cardStyle === 'detailed' ? 'text-right' : ''
                    }`}>Rating Distribution</h3>
                    
                    {/* Rating Distribution */}
                    <div className={`p-4 rounded-xl ${
                      theme === 'minimalist' ? 'bg-gray-100' :
                      theme === 'pastel' ? 'bg-pink-100/30' :
                      theme === 'luxury' ? 'bg-[#1A1A1A]/70' :
                      theme === 'neon' ? 'bg-[#0d0d0f]/80 shadow-[0_0_10px_1px_rgba(168,85,247,0.15)]' :
                      theme === 'custom' ? 'bg-[#1E1E20]/70' :
                      'bg-[#1E1E20]/70'
                    } border ${
                      theme === 'luxury' ? 'border-yellow-500/20' :
                      theme === 'elegant' ? 'border-amber-500/20' :
                      theme === 'neon' ? 'border-purple-500/20' :
                      theme === 'forest' ? 'border-emerald-500/20' :
                      theme === 'cosmic' ? 'border-indigo-500/20' :
                      theme === 'minimalist' ? 'border-gray-200' :
                      theme === 'tech' ? 'border-cyan-500/20' :
                      theme === 'pastel' ? 'border-pink-200/50' :
                      theme === 'monochrome' ? 'border-zinc-700/50' :
                      'border-gray-700/50'
                    }`}>
                      {/* 5 Stars */}
                      <div className="flex items-center mb-2">
                        <div className="flex items-center w-8">
                          <span className={`text-sm ${
                            theme === 'luxury' ? 'text-yellow-500' : 
                            theme === 'elegant' ? 'text-amber-400' :
                            theme === 'neon' ? 'text-purple-400' :
                            theme === 'forest' ? 'text-emerald-400' :
                            theme === 'cosmic' ? 'text-indigo-400' :
                            theme === 'minimalist' ? 'text-gray-600' :
                            theme === 'tech' ? 'text-cyan-400' :
                            theme === 'pastel' ? 'text-pink-400' :
                            theme === 'monochrome' ? 'text-zinc-400' :
                            'text-yellow-400'
                          }`}>5 ★</span>
                        </div>
                        <div className="flex-1 mx-3">
                          <div className="w-full bg-gray-700 rounded-full h-2.5">
                            <div className={`h-2.5 rounded-full ${
                              theme === 'luxury' ? 'bg-yellow-500' :
                              theme === 'elegant' ? 'bg-amber-500' :
                              theme === 'neon' ? 'bg-purple-500' :
                              theme === 'forest' ? 'bg-emerald-500' :
                              theme === 'cosmic' ? 'bg-indigo-500' :
                              theme === 'minimalist' ? 'bg-gray-500' :
                              theme === 'tech' ? 'bg-cyan-500' :
                              theme === 'pastel' ? 'bg-pink-500' :
                              theme === 'monochrome' ? 'bg-zinc-500' :
                              'bg-yellow-500'
                            }`} style={{ width: '67%' }}></div>
                          </div>
                        </div>
                        <div className="w-10 text-right">
                          <span className="text-gray-400 text-sm">67%</span>
                        </div>
                      </div>
                      
                      {/* 4 Stars */}
                      <div className="flex items-center mb-2">
                        <div className="flex items-center w-8">
                          <span className={`text-sm ${
                            theme === 'luxury' ? 'text-yellow-500' : 
                            theme === 'elegant' ? 'text-amber-400' :
                            theme === 'neon' ? 'text-purple-400' :
                            theme === 'forest' ? 'text-emerald-400' :
                            theme === 'cosmic' ? 'text-indigo-400' :
                            theme === 'minimalist' ? 'text-gray-600' :
                            theme === 'tech' ? 'text-cyan-400' :
                            theme === 'pastel' ? 'text-pink-400' :
                            theme === 'monochrome' ? 'text-zinc-400' :
                            'text-yellow-400'
                          }`}>4 ★</span>
                        </div>
                        <div className="flex-1 mx-3">
                          <div className="w-full bg-gray-700 rounded-full h-2.5">
                            <div className={`h-2.5 rounded-full ${
                              theme === 'luxury' ? 'bg-yellow-500' :
                              theme === 'elegant' ? 'bg-amber-500' :
                              theme === 'neon' ? 'bg-purple-500' :
                              theme === 'forest' ? 'bg-emerald-500' :
                              theme === 'cosmic' ? 'bg-indigo-500' :
                              theme === 'minimalist' ? 'bg-gray-500' :
                              theme === 'tech' ? 'bg-cyan-500' :
                              theme === 'pastel' ? 'bg-pink-500' :
                              theme === 'monochrome' ? 'bg-zinc-500' :
                              'bg-yellow-500'
                            }`} style={{ width: '0%' }}></div>
                          </div>
                        </div>
                        <div className="w-10 text-right">
                          <span className="text-gray-400 text-sm">0%</span>
                        </div>
                      </div>
                      
                      {/* 3 Stars */}
                      <div className="flex items-center mb-2">
                        <div className="flex items-center w-8">
                          <span className={`text-sm ${
                            theme === 'luxury' ? 'text-yellow-500' : 
                            theme === 'elegant' ? 'text-amber-400' :
                            theme === 'neon' ? 'text-purple-400' :
                            theme === 'forest' ? 'text-emerald-400' :
                            theme === 'cosmic' ? 'text-indigo-400' :
                            theme === 'minimalist' ? 'text-gray-600' :
                            theme === 'tech' ? 'text-cyan-400' :
                            theme === 'pastel' ? 'text-pink-400' :
                            theme === 'monochrome' ? 'text-zinc-400' :
                            'text-yellow-400'
                          }`}>3 ★</span>
                        </div>
                        <div className="flex-1 mx-3">
                          <div className="w-full bg-gray-700 rounded-full h-2.5">
                            <div className={`h-2.5 rounded-full ${
                              theme === 'luxury' ? 'bg-yellow-500' :
                              theme === 'elegant' ? 'bg-amber-500' :
                              theme === 'neon' ? 'bg-purple-500' :
                              theme === 'forest' ? 'bg-emerald-500' :
                              theme === 'cosmic' ? 'bg-indigo-500' :
                              theme === 'minimalist' ? 'bg-gray-500' :
                              theme === 'tech' ? 'bg-cyan-500' :
                              theme === 'pastel' ? 'bg-pink-500' :
                              theme === 'monochrome' ? 'bg-zinc-500' :
                              'bg-yellow-500'
                            }`} style={{ width: '33%' }}></div>
                          </div>
                        </div>
                        <div className="w-10 text-right">
                          <span className="text-gray-400 text-sm">33%</span>
                        </div>
                      </div>
                      
                      {/* 2 Stars */}
                      <div className="flex items-center mb-2">
                        <div className="flex items-center w-8">
                          <span className={`text-sm ${
                            theme === 'luxury' ? 'text-yellow-500' : 
                            theme === 'elegant' ? 'text-amber-400' :
                            theme === 'neon' ? 'text-purple-400' :
                            theme === 'forest' ? 'text-emerald-400' :
                            theme === 'cosmic' ? 'text-indigo-400' :
                            theme === 'minimalist' ? 'text-gray-600' :
                            theme === 'tech' ? 'text-cyan-400' :
                            theme === 'pastel' ? 'text-pink-400' :
                            theme === 'monochrome' ? 'text-zinc-400' :
                            'text-yellow-400'
                          }`}>2 ★</span>
                        </div>
                        <div className="flex-1 mx-3">
                          <div className="w-full bg-gray-700 rounded-full h-2.5">
                            <div className={`h-2.5 rounded-full ${
                              theme === 'luxury' ? 'bg-yellow-500' :
                              theme === 'elegant' ? 'bg-amber-500' :
                              theme === 'neon' ? 'bg-purple-500' :
                              theme === 'forest' ? 'bg-emerald-500' :
                              theme === 'cosmic' ? 'bg-indigo-500' :
                              theme === 'minimalist' ? 'bg-gray-500' :
                              theme === 'tech' ? 'bg-cyan-500' :
                              theme === 'pastel' ? 'bg-pink-500' :
                              theme === 'monochrome' ? 'bg-zinc-500' :
                              'bg-yellow-500'
                            }`} style={{ width: '0%' }}></div>
                          </div>
                        </div>
                        <div className="w-10 text-right">
                          <span className="text-gray-400 text-sm">0%</span>
                        </div>
                      </div>
                      
                      {/* 1 Star */}
                      <div className="flex items-center">
                        <div className="flex items-center w-8">
                          <span className={`text-sm ${
                            theme === 'luxury' ? 'text-yellow-500' : 
                            theme === 'elegant' ? 'text-amber-400' :
                            theme === 'neon' ? 'text-purple-400' :
                            theme === 'forest' ? 'text-emerald-400' :
                            theme === 'cosmic' ? 'text-indigo-400' :
                            theme === 'minimalist' ? 'text-gray-600' :
                            theme === 'tech' ? 'text-cyan-400' :
                            theme === 'pastel' ? 'text-pink-400' :
                            theme === 'monochrome' ? 'text-zinc-400' :
                            'text-yellow-400'
                          }`}>1 ★</span>
                        </div>
                        <div className="flex-1 mx-3">
                          <div className="w-full bg-gray-700 rounded-full h-2.5">
                            <div className={`h-2.5 rounded-full ${
                              theme === 'luxury' ? 'bg-yellow-500' :
                              theme === 'elegant' ? 'bg-amber-500' :
                              theme === 'neon' ? 'bg-purple-500' :
                              theme === 'forest' ? 'bg-emerald-500' :
                              theme === 'cosmic' ? 'bg-indigo-500' :
                              theme === 'minimalist' ? 'bg-gray-500' :
                              theme === 'tech' ? 'bg-cyan-500' :
                              theme === 'pastel' ? 'bg-pink-500' :
                              theme === 'monochrome' ? 'bg-zinc-500' :
                              'bg-yellow-500'
                            }`} style={{ width: '0%' }}></div>
                          </div>
                        </div>
                        <div className="w-10 text-right">
                          <span className="text-gray-400 text-sm">0%</span>
                        </div>
                      </div>
                    </div>
                    
                    {/* Statistics Cards */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
                      {/* Total Reviews */}
                      <div className={`p-4 rounded-xl ${
                        theme === 'minimalist' ? 'bg-gray-100' :
                        theme === 'pastel' ? 'bg-pink-100/30' :
                        theme === 'luxury' ? 'bg-[#1A1A1A]/70' :
                        theme === 'neon' ? 'bg-[#0d0d0f]/80 shadow-[0_0_10px_1px_rgba(168,85,247,0.15)]' :
                        theme === 'custom' ? 'bg-[#1E1E20]/70' :
                        'bg-[#1E1E20]/70'
                      } border ${
                        theme === 'luxury' ? 'border-yellow-500/20' :
                        theme === 'elegant' ? 'border-amber-500/20' :
                        theme === 'neon' ? 'border-purple-500/20' :
                        theme === 'forest' ? 'border-emerald-500/20' :
                        theme === 'cosmic' ? 'border-indigo-500/20' :
                        theme === 'minimalist' ? 'border-gray-200' :
                        theme === 'tech' ? 'border-cyan-500/20' :
                        theme === 'pastel' ? 'border-pink-200/50' :
                        theme === 'monochrome' ? 'border-zinc-700/50' :
                        'border-gray-700/50'
                      } text-center`}>
                        <div className={`text-2xl font-bold ${
                          theme === 'luxury' ? 'text-yellow-500' : 
                          theme === 'elegant' ? 'text-amber-400' :
                          theme === 'neon' ? 'text-purple-400' :
                          theme === 'forest' ? 'text-emerald-400' :
                          theme === 'cosmic' ? 'text-indigo-400' :
                          theme === 'minimalist' ? 'text-gray-800' :
                          theme === 'tech' ? 'text-cyan-400' :
                          theme === 'pastel' ? 'text-pink-500' :
                          theme === 'monochrome' ? 'text-zinc-300' :
                          'text-yellow-400'
                        }`}>3</div>
                        <div className="text-gray-400 text-xs mt-1">Total Reviews</div>
                      </div>
                      
                      {/* Average Rating */}
                      <div className={`p-4 rounded-xl ${
                        theme === 'minimalist' ? 'bg-gray-100' :
                        theme === 'pastel' ? 'bg-pink-100/30' :
                        theme === 'luxury' ? 'bg-[#1A1A1A]/70' :
                        theme === 'neon' ? 'bg-[#0d0d0f]/80 shadow-[0_0_10px_1px_rgba(168,85,247,0.15)]' :
                        theme === 'custom' ? 'bg-[#1E1E20]/70' :
                        'bg-[#1E1E20]/70'
                      } border ${
                        theme === 'luxury' ? 'border-yellow-500/20' :
                        theme === 'elegant' ? 'border-amber-500/20' :
                        theme === 'neon' ? 'border-purple-500/20' :
                        theme === 'forest' ? 'border-emerald-500/20' :
                        theme === 'cosmic' ? 'border-indigo-500/20' :
                        theme === 'minimalist' ? 'border-gray-200' :
                        theme === 'tech' ? 'border-cyan-500/20' :
                        theme === 'pastel' ? 'border-pink-200/50' :
                        theme === 'monochrome' ? 'border-zinc-700/50' :
                        'border-gray-700/50'
                      } text-center`}>
                        <div className={`text-2xl font-bold ${
                          theme === 'luxury' ? 'text-yellow-500' : 
                          theme === 'elegant' ? 'text-amber-400' :
                          theme === 'neon' ? 'text-purple-400' :
                          theme === 'forest' ? 'text-emerald-400' :
                          theme === 'cosmic' ? 'text-indigo-400' :
                          theme === 'minimalist' ? 'text-gray-800' :
                          theme === 'tech' ? 'text-cyan-400' :
                          theme === 'pastel' ? 'text-pink-500' :
                          theme === 'monochrome' ? 'text-zinc-300' :
                          'text-yellow-400'
                        }`}>4.3</div>
                        <div className="text-gray-400 text-xs mt-1">Average Rating</div>
                      </div>
                      
                      {/* Most Common */}
                      <div className={`p-4 rounded-xl ${
                        theme === 'minimalist' ? 'bg-gray-100' :
                        theme === 'pastel' ? 'bg-pink-100/30' :
                        theme === 'luxury' ? 'bg-[#1A1A1A]/70' :
                        theme === 'neon' ? 'bg-[#0d0d0f]/80 shadow-[0_0_10px_1px_rgba(168,85,247,0.15)]' :
                        theme === 'custom' ? 'bg-[#1E1E20]/70' :
                        'bg-[#1E1E20]/70'
                      } border ${
                        theme === 'luxury' ? 'border-yellow-500/20' :
                        theme === 'elegant' ? 'border-amber-500/20' :
                        theme === 'neon' ? 'border-purple-500/20' :
                        theme === 'forest' ? 'border-emerald-500/20' :
                        theme === 'cosmic' ? 'border-indigo-500/20' :
                        theme === 'minimalist' ? 'border-gray-200' :
                        theme === 'tech' ? 'border-cyan-500/20' :
                        theme === 'pastel' ? 'border-pink-200/50' :
                        theme === 'monochrome' ? 'border-zinc-700/50' :
                        'border-gray-700/50'
                      } text-center`}>
                        <div className={`text-2xl font-bold ${
                          theme === 'luxury' ? 'text-yellow-500' : 
                          theme === 'elegant' ? 'text-amber-400' :
                          theme === 'neon' ? 'text-purple-400' :
                          theme === 'forest' ? 'text-emerald-400' :
                          theme === 'cosmic' ? 'text-indigo-400' :
                          theme === 'minimalist' ? 'text-gray-800' :
                          theme === 'tech' ? 'text-cyan-400' :
                          theme === 'pastel' ? 'text-pink-500' :
                          theme === 'monochrome' ? 'text-zinc-300' :
                          'text-yellow-400'
                        }`}>67%</div>
                        <div className="text-gray-400 text-xs mt-1">Most Common</div>
                      </div>
                      
                      {/* 5-Star Reviews */}
                      <div className={`p-4 rounded-xl ${
                        theme === 'minimalist' ? 'bg-gray-100' :
                        theme === 'pastel' ? 'bg-pink-100/30' :
                        theme === 'luxury' ? 'bg-[#1A1A1A]/70' :
                        theme === 'neon' ? 'bg-[#0d0d0f]/80 shadow-[0_0_10px_1px_rgba(168,85,247,0.15)]' :
                        theme === 'custom' ? 'bg-[#1E1E20]/70' :
                        'bg-[#1E1E20]/70'
                      } border ${
                        theme === 'luxury' ? 'border-yellow-500/20' :
                        theme === 'elegant' ? 'border-amber-500/20' :
                        theme === 'neon' ? 'border-purple-500/20' :
                        theme === 'forest' ? 'border-emerald-500/20' :
                        theme === 'cosmic' ? 'border-indigo-500/20' :
                        theme === 'minimalist' ? 'border-gray-200' :
                        theme === 'tech' ? 'border-cyan-500/20' :
                        theme === 'pastel' ? 'border-pink-200/50' :
                        theme === 'monochrome' ? 'border-zinc-700/50' :
                        'border-gray-700/50'
                      } text-center`}>
                        <div className={`text-2xl font-bold ${
                          theme === 'luxury' ? 'text-yellow-500' : 
                          theme === 'elegant' ? 'text-amber-400' :
                          theme === 'neon' ? 'text-purple-400' :
                          theme === 'forest' ? 'text-emerald-400' :
                          theme === 'cosmic' ? 'text-indigo-400' :
                          theme === 'minimalist' ? 'text-gray-800' :
                          theme === 'tech' ? 'text-cyan-400' :
                          theme === 'pastel' ? 'text-pink-500' :
                          theme === 'monochrome' ? 'text-zinc-300' :
                          'text-yellow-400'
                        }`}>2</div>
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
    </div>
  );
};

function AppearanceRating() {
  const navigate = useNavigate();
  
  // State for appearance settings
  const [theme, setTheme] = useState<'default' | 'dark' | 'gradient' | 'luxury' | 'elegant' | 'neon' | 'forest' | 'cosmic' | 'minimalist' | 'tech' | 'pastel' | 'monochrome' | 'custom'>('default');
  const [ratingStyle, setRatingStyle] = useState<'stars' | 'numbers' | 'bars' | 'emoji' | 'percent'>('stars');
  const [cardStyle, setCardStyle] = useState<'modern' | 'compact' | 'detailed'>('modern');
  const [fontStyle, setFontStyle] = useState<'default' | 'modern' | 'classic'>('default');
  const [customThemeColors, setCustomThemeColors] = useState({
    primary: '#4338ca',
    secondary: '#6366f1',
    text: '#ffffff',
    background: '#111827'
  });
  const [copied, setCopied] = useState<boolean>(false);
  const [importCode, setImportCode] = useState<string>('');
  const [shareCode, setShareCode] = useState<string>('');
  const [showFullPreview, setShowFullPreview] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'reviews' | 'statistics'>('reviews');
  const [showAnimation, setShowAnimation] = useState<boolean>(true);
  const [highlightTopRatings, setHighlightTopRatings] = useState<boolean>(true);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  
  const themeRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});
  const styleRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});
  const shareCodeRef = useRef<HTMLInputElement>(null);
  
  // Fetch appearance settings on component mount
  useEffect(() => {
    fetchAppearanceSettings();
    
    // Generate a share code on component mount
    generateShareCode().catch((error) => {
      console.error('Error generating initial share code:', error);
    });
  }, []);
  
  // Fetch appearance settings from API
  const fetchAppearanceSettings = async () => {
    try {
      setIsLoading(true);
      const response = await axios.get('/api/ratings/appearance');
      
      if (response.data && response.data.appearance) {
        const settings = response.data.appearance;
        
        // Update state with fetched settings
        setTheme(settings.theme || 'default');
        setRatingStyle(settings.ratingStyle || 'stars');
        setCardStyle(settings.cardStyle || 'modern');
        setFontStyle(settings.fontStyle || 'default');
        
        if (settings.customThemeColors) {
          setCustomThemeColors(settings.customThemeColors);
        }
        
        setShowAnimation(settings.showAnimation ?? true);
        setHighlightTopRatings(settings.highlightTopRatings ?? true);
        
        toast.success('Appearance settings loaded');
      }
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.data?.code === 'PREMIUM_REQUIRED') {
        toast.error('Premium subscription required');
        navigate('/upgrade');
      } else if (axios.isAxiosError(error) && error.response?.data?.code === 'WALLET_LOCKED') {
        toast.error('Your wallet is locked. Please unlock it to modify appearance settings.');
      } else {
        console.error('Error fetching appearance settings:', error);
        toast.error('Failed to load appearance settings');
      }
    } finally {
      setIsLoading(false);
    }
  };
  
  // Save individual appearance setting
  const saveAppearanceSetting = async (setting: string, value: any) => {
    try {
      setIsSaving(true);
      
      await axios.post('/api/ratings/appearance/update', {
        setting,
        value
      });
      
      // No need for toast here as the update functions already show toasts
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.data?.code === 'PREMIUM_REQUIRED') {
        toast.error('Premium subscription required');
        navigate('/upgrade');
      } else if (axios.isAxiosError(error) && error.response?.data?.code === 'WALLET_LOCKED') {
        toast.error('Your wallet is locked. Please unlock it to modify appearance settings.');
      } else {
        console.error(`Error updating ${setting}:`, error);
        toast.error(`Failed to save ${setting}`);
      }
    } finally {
      setIsSaving(false);
    }
  };
  
  // Save all appearance settings at once
  const saveAllAppearanceSettings = async () => {
    try {
      setIsSaving(true);
      
      const allSettings = {
        theme,
        customThemeColors,
        ratingStyle,
        cardStyle,
        fontStyle,
        showAnimation,
        highlightTopRatings
      };
      
      await axios.post('/api/ratings/appearance/update-all', {
        appearance: allSettings
      });
      
      toast.success('All appearance settings saved');
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.data?.code === 'PREMIUM_REQUIRED') {
        toast.error('Premium subscription required');
        navigate('/upgrade');
      } else if (axios.isAxiosError(error) && error.response?.data?.code === 'WALLET_LOCKED') {
        toast.error('Your wallet is locked. Please unlock it to modify appearance settings.');
      } else {
        console.error('Error saving all appearance settings:', error);
        toast.error('Failed to save settings');
      }
    } finally {
      setIsSaving(false);
    }
  };
  
  // Reset to default appearance settings
  const resetAppearanceSettings = async () => {
    try {
      setIsSaving(true);
      
      const response = await axios.post('/api/ratings/appearance/reset');
      
      if (response.data && response.data.appearance) {
        const defaultSettings = response.data.appearance;
        
        // Update state with default settings
        setTheme(defaultSettings.theme || 'default');
        setRatingStyle(defaultSettings.ratingStyle || 'stars');
        setCardStyle(defaultSettings.cardStyle || 'modern');
        setFontStyle(defaultSettings.fontStyle || 'default');
        
        if (defaultSettings.customThemeColors) {
          setCustomThemeColors(defaultSettings.customThemeColors);
        }
        
        setShowAnimation(defaultSettings.showAnimation ?? true);
        setHighlightTopRatings(defaultSettings.highlightTopRatings ?? true);
        
        toast.success('Settings reset to defaults');
      }
    } catch (error) {
      console.error('Error resetting appearance settings:', error);
      toast.error('Failed to reset settings');
    } finally {
      setIsSaving(false);
    }
  };

  // Handle navigation to full preview page
  const goToFullPreview = () => {
    setShowFullPreview(true);
  };
  
  // Handle going back from full preview
  const goBackFromPreview = () => {
    setShowFullPreview(false);
  };

  const scrollToTheme = (themeKey: string) => {
    if (themeRefs.current[themeKey]) {
      themeRefs.current[themeKey]?.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
        inline: 'center'
      });
    }
  };
  
  const scrollToStyle = (styleKey: string) => {
    if (styleRefs.current[styleKey]) {
      styleRefs.current[styleKey]?.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
        inline: 'center'
      });
    }
  };
  
  // إعلام الأب بأننا في صفحة Appearance
  useEffect(() => {
    // تأكد من أن عنصر الجذر يحتوي على الفئة hide-layout
    document.body.classList.add('hide-sidebar');
    const appElement = document.getElementById('root');
    if (appElement) {
      appElement.classList.add('hide-layout');
    }
    
    // إضافة أنماط إخفاء شريط التمرير
    const styleElement = document.createElement('style');
    styleElement.innerHTML = scrollbarHideStyles;
    document.head.appendChild(styleElement);
    
    // تنظيف عند إزالة المكون
    return () => {
      document.body.classList.remove('hide-sidebar');
      const appElement = document.getElementById('root');
      if (appElement) {
        appElement.classList.remove('hide-layout');
      }
      
      // إزالة أنماط إخفاء شريط التمرير
      document.head.removeChild(styleElement);
    };
  }, []);
  
  // Update functions
  const updateTheme = (newTheme: 'default' | 'dark' | 'gradient' | 'luxury' | 'elegant' | 'neon' | 'forest' | 'cosmic' | 'minimalist' | 'tech' | 'pastel' | 'monochrome' | 'custom') => {
    setTheme(newTheme);
    scrollToTheme(newTheme);
    toast.success(`Theme updated to ${newTheme}`);
    saveAppearanceSetting('theme', newTheme);
  };
  
  const updateCustomThemeColor = (colorKey: 'primary' | 'secondary' | 'text' | 'background', value: string) => {
    const newCustomThemeColors = {
      ...customThemeColors,
      [colorKey]: value
    };
    setCustomThemeColors(newCustomThemeColors);
    saveAppearanceSetting('customThemeColors', newCustomThemeColors);
  };
  
  const updateRatingStyle = (style: 'stars' | 'numbers' | 'bars' | 'emoji' | 'percent') => {
    setRatingStyle(style);
    scrollToStyle(style);
    toast.success(`Rating style updated to ${style}`);
    saveAppearanceSetting('ratingStyle', style);
  };
  
  const updateCardStyle = (style: 'modern' | 'compact' | 'detailed') => {
    setCardStyle(style);
    toast.success(`Card style updated to ${style}`);
    saveAppearanceSetting('cardStyle', style);
  };
  
  const updateFontStyle = (style: 'default' | 'modern' | 'classic') => {
    setFontStyle(style);
    toast.success(`Font style updated to ${style}`);
    saveAppearanceSetting('fontStyle', style);
  };
  
  // Toggle animation and top ratings highlighting functions
  const toggleShowAnimation = () => {
    setShowAnimation(prev => {
      const newValue = !prev;
      saveAppearanceSetting('showAnimation', newValue);
      return newValue;
    });
  };
  
  const toggleHighlightTopRatings = () => {
    setHighlightTopRatings(prev => {
      const newValue = !prev;
      saveAppearanceSetting('highlightTopRatings', newValue);
      return newValue;
    });
  };

  // Generate share code based on current settings
  const generateShareCode = async () => {
    try {
      setIsSaving(true);
      
      const response = await axios.post('/api/ratings/appearance/share-code');
      
      if (response.data && response.data.share_code) {
        setShareCode(response.data.share_code);
        setImportCode(response.data.share_code);
        if (shareCodeRef.current) {
          shareCodeRef.current.value = response.data.share_code;
        }
        toast.success('Share code generated successfully');
      }
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.data?.code === 'PREMIUM_REQUIRED') {
        toast.error('Premium subscription required');
        navigate('/upgrade');
      } else if (axios.isAxiosError(error) && error.response?.data?.code === 'WALLET_LOCKED') {
        toast.error('Your wallet is locked. Please unlock it to generate a share code.');
      } else {
        console.error('Error generating share code:', error);
        toast.error('Failed to generate share code');
      }
    } finally {
      setIsSaving(false);
    }
  };
  
  // Copy share code to clipboard
  const copyShareCode = () => {
    if (shareCodeRef.current) {
      shareCodeRef.current.select();
      document.execCommand('copy');
      setCopied(true);
      toast.success('Design code copied to clipboard!');
      
      // Reset copied state after 2 seconds
      setTimeout(() => {
        setCopied(false);
      }, 2000);
    }
  };

  // Apply imported design code
  const applyImportedDesign = async () => {
    if (!importCode.trim()) {
      toast.error('Please enter a design code');
      return;
    }
    
    try {
      setIsSaving(true);
      
      const response = await axios.post('/api/ratings/appearance/import', {
        share_code: importCode
      });
      
      if (response.data && response.data.appearance) {
        const importedSettings = response.data.appearance;
        
        // Update state with imported settings
        setTheme(importedSettings.theme || 'default');
        setRatingStyle(importedSettings.ratingStyle || 'stars');
        setCardStyle(importedSettings.cardStyle || 'modern');
        setFontStyle(importedSettings.fontStyle || 'default');
        
        if (importedSettings.customThemeColors) {
          setCustomThemeColors(importedSettings.customThemeColors);
        }
        
        setShowAnimation(importedSettings.showAnimation ?? true);
        setHighlightTopRatings(importedSettings.highlightTopRatings ?? true);
        
        toast.success('Imported design applied successfully');
      }
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.data?.code === 'PREMIUM_REQUIRED') {
        toast.error('Premium subscription required');
        navigate('/upgrade');
      } else if (axios.isAxiosError(error) && error.response?.data?.code === 'WALLET_LOCKED') {
        toast.error('Your wallet is locked. Please unlock it to import appearance settings.');
      } else {
        console.error('Error importing design:', error);
        toast.error('Failed to import design. Invalid share code.');
      }
    } finally {
      setIsSaving(false);
    }
  };

  // Show full preview page when requested
  if (showFullPreview) {
    return (
      <FullPreviewPage 
        theme={theme}
        customThemeColors={customThemeColors}
        ratingStyle={ratingStyle}
        cardStyle={cardStyle}
        fontStyle={fontStyle}
        showAnimation={showAnimation}
        highlightTopRatings={highlightTopRatings}
        goBack={goBackFromPreview}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">Appearance Settings</h2>
        <div className="flex items-center gap-2 text-xs bg-gradient-to-r from-amber-500 to-yellow-700 text-white px-3 py-1 rounded-full">
          <Shield size={14} />
          <span className="font-bold">Premium Features</span>
        </div>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column - All Controls and Settings (takes 1/2 of the width) */}
        <div className="space-y-6">
          {/* Theme Selection */}
          <div className="bg-gradient-to-br from-[#2A2A2E] to-[#252530] p-5 rounded-2xl shadow-lg border border-gray-700/30">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center">
                <Palette size={18} className="text-purple-400 mr-2" />
                <h3 className="text-xl font-medium text-gray-200">Rating Display Theme</h3>
              </div>
            </div>
            
            <div className="overflow-x-auto pb-2 scrollbar-hide">
              <div className="flex space-x-4 min-w-max">
                {/* Theme Options */}
                <div 
                  ref={el => themeRefs.current['default'] = el}
                  className={`bg-[#1E1E20] p-3 rounded-xl border ${theme === 'default' ? 'border-blue-500 ring-2 ring-blue-500/30' : 'border-gray-700/50'} cursor-pointer hover:bg-[#1E1E20]/80 transition-all min-w-[130px]`}
                  onClick={() => updateTheme('default')}
                >
                  <div className="h-20 bg-[#2A2A2E] rounded-lg mb-3 flex items-center justify-center">
                    <div className="w-12 h-3 bg-blue-500 rounded-full"></div>
                  </div>
                  <h4 className="text-sm font-medium text-gray-200 text-center">Default</h4>
                </div>
                
                <div 
                  ref={el => themeRefs.current['dark'] = el}
                  className={`bg-[#1E1E20] p-3 rounded-xl border ${theme === 'dark' ? 'border-blue-500 ring-2 ring-blue-500/30' : 'border-gray-700/50'} cursor-pointer hover:bg-[#1E1E20]/80 transition-all min-w-[130px]`}
                  onClick={() => updateTheme('dark')}
                >
                  <div className="h-20 bg-[#1A1A1E] rounded-lg mb-3 flex items-center justify-center">
                    <div className="w-12 h-3 bg-blue-500 rounded-full"></div>
                  </div>
                  <h4 className="text-sm font-medium text-gray-200 text-center">Dark</h4>
                </div>
                
                <div 
                  ref={el => themeRefs.current['gradient'] = el}
                  className={`bg-[#1E1E20] p-3 rounded-xl border ${theme === 'gradient' ? 'border-blue-500 ring-2 ring-blue-500/30' : 'border-gray-700/50'} cursor-pointer hover:bg-[#1E1E20]/80 transition-all min-w-[130px]`}
                  onClick={() => updateTheme('gradient')}
                >
                  <div className="h-20 bg-gradient-to-br from-gray-900 to-gray-800 rounded-lg mb-3 flex items-center justify-center">
                    <div className="w-12 h-3 bg-blue-500 rounded-full"></div>
                  </div>
                  <h4 className="text-sm font-medium text-gray-200 text-center">Gradient</h4>
                </div>

                <div 
                  ref={el => themeRefs.current['luxury'] = el}
                  className={`bg-[#1E1E20] p-3 rounded-xl border ${theme === 'luxury' ? 'border-blue-500 ring-2 ring-blue-500/30' : 'border-gray-700/50'} cursor-pointer hover:bg-[#1E1E20]/80 transition-all min-w-[130px]`}
                  onClick={() => updateTheme('luxury')}
                >
                  <div className="h-20 bg-gradient-to-br from-gray-900 to-stone-900 rounded-lg mb-3 flex items-center justify-center">
                    <div className="w-12 h-3 bg-yellow-500 rounded-full"></div>
                  </div>
                  <h4 className="text-sm font-medium text-gray-200 text-center">Luxury</h4>
                </div>

                <div 
                  ref={el => themeRefs.current['elegant'] = el}
                  className={`bg-[#1E1E20] p-3 rounded-xl border ${theme === 'elegant' ? 'border-blue-500 ring-2 ring-blue-500/30' : 'border-gray-700/50'} cursor-pointer hover:bg-[#1E1E20]/80 transition-all min-w-[130px]`}
                  onClick={() => updateTheme('elegant')}
                >
                  <div className="h-20 bg-gradient-to-r from-[#232526] to-[#414345] rounded-lg mb-3 flex items-center justify-center">
                    <div className="w-12 h-3 bg-amber-500 rounded-full"></div>
                  </div>
                  <h4 className="text-sm font-medium text-gray-200 text-center">Elegant</h4>
                </div>

                <div 
                  ref={el => themeRefs.current['neon'] = el}
                  className={`bg-[#1E1E20] p-3 rounded-xl border ${theme === 'neon' ? 'border-blue-500 ring-2 ring-blue-500/30' : 'border-gray-700/50'} cursor-pointer hover:bg-[#1E1E20]/80 transition-all min-w-[130px]`}
                  onClick={() => updateTheme('neon')}
                >
                  <div className="h-20 bg-[#0d0d0f] rounded-lg mb-3 flex items-center justify-center relative overflow-hidden">
                    <div className="absolute inset-0 bg-[#0d0d0f]"></div>
                    <div className="relative z-10 w-12 h-3 bg-purple-500 rounded-full shadow-[0_0_10px_3px_rgba(168,85,247,0.5)]"></div>
                  </div>
                  <h4 className="text-sm font-medium text-gray-200 text-center">Neon</h4>
                </div>

                <div 
                  ref={el => themeRefs.current['forest'] = el}
                  className={`bg-[#1E1E20] p-3 rounded-xl border ${theme === 'forest' ? 'border-blue-500 ring-2 ring-blue-500/30' : 'border-gray-700/50'} cursor-pointer hover:bg-[#1E1E20]/80 transition-all min-w-[130px]`}
                  onClick={() => updateTheme('forest')}
                >
                  <div className="h-20 bg-gradient-to-br from-green-900 to-emerald-800 rounded-lg mb-3 flex items-center justify-center">
                    <div className="w-12 h-3 bg-emerald-400 rounded-full"></div>
                  </div>
                  <h4 className="text-sm font-medium text-gray-200 text-center">Forest</h4>
                </div>

                <div 
                  ref={el => themeRefs.current['cosmic'] = el}
                  className={`bg-[#1E1E20] p-3 rounded-xl border ${theme === 'cosmic' ? 'border-blue-500 ring-2 ring-blue-500/30' : 'border-gray-700/50'} cursor-pointer hover:bg-[#1E1E20]/80 transition-all min-w-[130px]`}
                  onClick={() => updateTheme('cosmic')}
                >
                  <div className="h-20 bg-gradient-to-br from-indigo-900 to-purple-900 rounded-lg mb-3 flex items-center justify-center">
                    <div className="w-12 h-3 bg-indigo-400 rounded-full"></div>
                  </div>
                  <h4 className="text-sm font-medium text-gray-200 text-center">Cosmic</h4>
                </div>

                <div 
                  ref={el => themeRefs.current['minimalist'] = el}
                  className={`bg-[#1E1E20] p-3 rounded-xl border ${theme === 'minimalist' ? 'border-blue-500 ring-2 ring-blue-500/30' : 'border-gray-700/50'} cursor-pointer hover:bg-[#1E1E20]/80 transition-all min-w-[130px]`}
                  onClick={() => updateTheme('minimalist')}
                >
                  <div className="h-20 bg-[#f5f5f5] rounded-lg mb-3 flex items-center justify-center">
                    <div className="w-12 h-3 bg-gray-500 rounded-full"></div>
                  </div>
                  <h4 className="text-sm font-medium text-gray-200 text-center">Minimalist</h4>
                </div>

                <div 
                  ref={el => themeRefs.current['tech'] = el}
                  className={`bg-[#1E1E20] p-3 rounded-xl border ${theme === 'tech' ? 'border-blue-500 ring-2 ring-blue-500/30' : 'border-gray-700/50'} cursor-pointer hover:bg-[#1E1E20]/80 transition-all min-w-[130px]`}
                  onClick={() => updateTheme('tech')}
                >
                  <div className="h-20 bg-gradient-to-br from-sky-900 to-cyan-800 rounded-lg mb-3 flex items-center justify-center">
                    <div className="w-12 h-3 bg-cyan-400 rounded-full"></div>
                  </div>
                  <h4 className="text-sm font-medium text-gray-200 text-center">Tech</h4>
                </div>

                <div 
                  ref={el => themeRefs.current['pastel'] = el}
                  className={`bg-[#1E1E20] p-3 rounded-xl border ${theme === 'pastel' ? 'border-blue-500 ring-2 ring-blue-500/30' : 'border-gray-700/50'} cursor-pointer hover:bg-[#1E1E20]/80 transition-all min-w-[130px]`}
                  onClick={() => updateTheme('pastel')}
                >
                  <div className="h-20 bg-gradient-to-br from-pink-200 to-sky-200 rounded-lg mb-3 flex items-center justify-center">
                    <div className="w-12 h-3 bg-pink-400 rounded-full"></div>
                  </div>
                  <h4 className="text-sm font-medium text-gray-200 text-center">Pastel</h4>
                </div>

                <div 
                  ref={el => themeRefs.current['monochrome'] = el}
                  className={`bg-[#1E1E20] p-3 rounded-xl border ${theme === 'monochrome' ? 'border-blue-500 ring-2 ring-blue-500/30' : 'border-gray-700/50'} cursor-pointer hover:bg-[#1E1E20]/80 transition-all min-w-[130px]`}
                  onClick={() => updateTheme('monochrome')}
                >
                  <div className="h-20 bg-gradient-to-br from-zinc-700 to-zinc-900 rounded-lg mb-3 flex items-center justify-center">
                    <div className="w-12 h-3 bg-zinc-400 rounded-full"></div>
                  </div>
                  <h4 className="text-sm font-medium text-gray-200 text-center">Monochrome</h4>
                </div>

                <div 
                  ref={el => themeRefs.current['custom'] = el}
                  className={`bg-[#1E1E20] p-3 rounded-xl border ${theme === 'custom' ? 'border-blue-500 ring-2 ring-blue-500/30' : 'border-gray-700/50'} cursor-pointer hover:bg-[#1E1E20]/80 transition-all min-w-[130px]`}
                  onClick={() => updateTheme('custom')}
                >
                  <div 
                    style={{background: `linear-gradient(135deg, ${customThemeColors.primary}, ${customThemeColors.secondary})`}}
                    className="h-20 rounded-lg mb-3 flex items-center justify-center">
                    <Brush size={20} className="text-white" />
                  </div>
                  <h4 className="text-sm font-medium text-gray-200 text-center">Custom</h4>
                </div>
              </div>
            </div>
          </div>

          {/* Custom Theme Editor - Only visible when custom theme is selected */}
          {theme === 'custom' && (
            <div className="bg-gradient-to-br from-[#2A2A2E] to-[#252530] p-6 rounded-2xl shadow-xl border border-gray-700/30 mt-4 overflow-hidden relative">
              <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-bl from-purple-500/10 to-transparent rounded-full -mr-32 -mt-32 blur-xl"></div>
              <div className="absolute bottom-0 left-0 w-64 h-64 bg-gradient-to-tr from-blue-500/10 to-transparent rounded-full -ml-32 -mb-32 blur-xl"></div>
              
              <div className="flex items-center mb-6 relative">
                <div className="p-2 bg-gradient-to-br from-purple-500 to-blue-600 rounded-lg mr-3 shadow-lg">
                  <PaletteIcon size={18} className="text-white" />
                </div>
                <h3 className="text-xl font-bold text-gray-200">Custom Theme Editor</h3>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative">
                <div className="bg-[#1E1E20]/70 p-4 rounded-xl border border-gray-700/50 backdrop-blur-sm shadow-md">
                  <label className="block text-sm font-medium text-gray-300 mb-2 flex items-center">
                    <div className="w-3 h-3 rounded-full mr-2" style={{backgroundColor: customThemeColors.primary}}></div>
                    Primary Color
                  </label>
                  <div className="flex items-center space-x-3">
                    <div className="relative">
                      <input 
                        type="color" 
                        value={customThemeColors.primary} 
                        onChange={(e) => updateCustomThemeColor('primary', e.target.value)} 
                        className="w-12 h-12 cursor-pointer rounded-lg overflow-hidden opacity-0 absolute inset-0 z-10"
                      />
                      <div className="w-12 h-12 rounded-lg border-2 border-white/20 shadow-lg" style={{backgroundColor: customThemeColors.primary}}></div>
                    </div>
                    <input 
                      type="text" 
                      value={customThemeColors.primary} 
                      onChange={(e) => updateCustomThemeColor('primary', e.target.value)}
                      className="bg-[#1E1E20] border border-gray-700 text-white rounded-lg px-3 py-2 text-sm flex-1 font-mono shadow-inner focus:ring-2 focus:ring-purple-500/30 focus:outline-none transition-all"
                    />
                  </div>
                </div>
                
                <div className="bg-[#1E1E20]/70 p-4 rounded-xl border border-gray-700/50 backdrop-blur-sm shadow-md">
                  <label className="block text-sm font-medium text-gray-300 mb-2 flex items-center">
                    <div className="w-3 h-3 rounded-full mr-2" style={{backgroundColor: customThemeColors.secondary}}></div>
                    Secondary Color
                  </label>
                  <div className="flex items-center space-x-3">
                    <div className="relative">
                      <input 
                        type="color" 
                        value={customThemeColors.secondary} 
                        onChange={(e) => updateCustomThemeColor('secondary', e.target.value)} 
                        className="w-12 h-12 cursor-pointer rounded-lg overflow-hidden opacity-0 absolute inset-0 z-10"
                      />
                      <div className="w-12 h-12 rounded-lg border-2 border-white/20 shadow-lg" style={{backgroundColor: customThemeColors.secondary}}></div>
                    </div>
                    <input 
                      type="text" 
                      value={customThemeColors.secondary} 
                      onChange={(e) => updateCustomThemeColor('secondary', e.target.value)}
                      className="bg-[#1E1E20] border border-gray-700 text-white rounded-lg px-3 py-2 text-sm flex-1 font-mono shadow-inner focus:ring-2 focus:ring-purple-500/30 focus:outline-none transition-all"
                    />
                  </div>
                </div>
                
                <div className="bg-[#1E1E20]/70 p-4 rounded-xl border border-gray-700/50 backdrop-blur-sm shadow-md">
                  <label className="block text-sm font-medium text-gray-300 mb-2 flex items-center">
                    <div className="w-3 h-3 rounded-full mr-2" style={{backgroundColor: customThemeColors.text}}></div>
                    Text Color
                  </label>
                  <div className="flex items-center space-x-3">
                    <div className="relative">
                      <input 
                        type="color" 
                        value={customThemeColors.text} 
                        onChange={(e) => updateCustomThemeColor('text', e.target.value)} 
                        className="w-12 h-12 cursor-pointer rounded-lg overflow-hidden opacity-0 absolute inset-0 z-10"
                      />
                      <div className="w-12 h-12 rounded-lg border-2 border-white/20 shadow-lg" style={{backgroundColor: customThemeColors.text}}></div>
                    </div>
                    <input 
                      type="text" 
                      value={customThemeColors.text} 
                      onChange={(e) => updateCustomThemeColor('text', e.target.value)}
                      className="bg-[#1E1E20] border border-gray-700 text-white rounded-lg px-3 py-2 text-sm flex-1 font-mono shadow-inner focus:ring-2 focus:ring-purple-500/30 focus:outline-none transition-all"
                    />
                  </div>
                </div>
                
                <div className="bg-[#1E1E20]/70 p-4 rounded-xl border border-gray-700/50 backdrop-blur-sm shadow-md">
                  <label className="block text-sm font-medium text-gray-300 mb-2 flex items-center">
                    <div className="w-3 h-3 rounded-full mr-2" style={{backgroundColor: customThemeColors.background}}></div>
                    Background Color
                  </label>
                  <div className="flex items-center space-x-3">
                    <div className="relative">
                      <input 
                        type="color" 
                        value={customThemeColors.background} 
                        onChange={(e) => updateCustomThemeColor('background', e.target.value)} 
                        className="w-12 h-12 cursor-pointer rounded-lg overflow-hidden opacity-0 absolute inset-0 z-10"
                      />
                      <div className="w-12 h-12 rounded-lg border-2 border-white/20 shadow-lg" style={{backgroundColor: customThemeColors.background}}></div>
                    </div>
                    <input 
                      type="text" 
                      value={customThemeColors.background} 
                      onChange={(e) => updateCustomThemeColor('background', e.target.value)}
                      className="bg-[#1E1E20] border border-gray-700 text-white rounded-lg px-3 py-2 text-sm flex-1 font-mono shadow-inner focus:ring-2 focus:ring-purple-500/30 focus:outline-none transition-all"
                    />
                  </div>
                </div>
              </div>

              <div className="mt-6 relative">
                <label className="block text-sm font-medium text-gray-300 mb-3 flex items-center">
                  <div className="p-1 bg-gradient-to-r from-purple-500 to-blue-500 rounded-md mr-2">
                    <Brush size={12} className="text-white" />
                  </div>
                  Live Preview
                </label>
                <div className="h-28 rounded-xl mb-3 flex items-center justify-center overflow-hidden shadow-xl relative backdrop-blur-sm" 
                  style={{
                    background: `linear-gradient(135deg, ${customThemeColors.primary}, ${customThemeColors.secondary})`
                  }}>
                  <div className="absolute inset-0 opacity-30 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiMyMjIiIGZpbGwtb3BhY2l0eT0iLjA1Ij48cGF0aCBkPSJNMzYgMzRoLTZsLTQtNGgtNnY2aDZsNCA0aDZ6TTMwIDMwaDZsNCA0aDZ2LTZoLTZsLTQtNGgtNnoiLz48L2c+PC9nPjwvc3ZnPg==')]"></div>
                  <div className="flex flex-col items-center relative z-10">
                    <div className="flex gap-1 mb-2">
                      {[1,2,3,4,5].map((_, idx) => (
                        <div key={idx} className="w-4 h-4 rounded-full flex items-center justify-center" 
                          style={{backgroundColor: customThemeColors.text, opacity: idx < 4 ? 1 : 0.3}}>
                          <Star size={10} style={{color: customThemeColors.secondary}} />
                        </div>
                      ))}
                    </div>
                    <span className="text-sm font-medium" style={{color: customThemeColors.text}}>Custom Theme Preview</span>
                    <div className="mt-2 px-3 py-1 rounded-full text-xs" 
                      style={{backgroundColor: customThemeColors.text, color: customThemeColors.secondary}}>
                      Premium Theme
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {/* Rating Style Selection */}
          <div className="bg-gradient-to-br from-[#2A2A2E] to-[#252530] p-5 rounded-2xl shadow-lg border border-gray-700/30">
            <div className="flex items-center mb-5">
              <Star size={18} className="text-amber-400 mr-2" />
                              <h3 className="text-xl font-medium text-gray-200">Rating Style</h3>
            </div>
            
            <div className="overflow-x-auto pb-2 scrollbar-hide">
              <div className="flex space-x-4 min-w-max">
                {/* Rating Style Options */}
                <div 
                  ref={el => styleRefs.current['stars'] = el}
                  className={`bg-[#1E1E20] p-3 rounded-xl border ${ratingStyle === 'stars' ? 'border-blue-500 ring-2 ring-blue-500/30' : 'border-gray-700/50'} cursor-pointer hover:bg-[#1E1E20]/80 transition-all min-w-[130px]`}
                  onClick={() => updateRatingStyle('stars')}
                >
                  <div className="h-20 bg-[#2A2A2E] rounded-lg mb-3 flex items-center justify-center">
                    <div className="flex space-x-1">
                      <span className="text-yellow-400 text-lg">★★★★</span><span className="text-gray-500 text-lg">★</span>
                    </div>
                  </div>
                  <h4 className="text-sm font-medium text-gray-200 text-center">Stars</h4>
                </div>
                
                <div 
                  ref={el => styleRefs.current['numbers'] = el}
                  className={`bg-[#1E1E20] p-3 rounded-xl border ${ratingStyle === 'numbers' ? 'border-blue-500 ring-2 ring-blue-500/30' : 'border-gray-700/50'} cursor-pointer hover:bg-[#1E1E20]/80 transition-all min-w-[130px]`}
                  onClick={() => updateRatingStyle('numbers')}
                >
                  <div className="h-20 bg-[#2A2A2E] rounded-lg mb-3 flex items-center justify-center">
                    <span className="text-white font-bold text-lg">4.5</span><span className="text-gray-500 text-sm">/5</span>
                  </div>
                  <h4 className="text-sm font-medium text-gray-200 text-center">Numbers</h4>
                </div>
                
                <div 
                  ref={el => styleRefs.current['bars'] = el}
                  className={`bg-[#1E1E20] p-3 rounded-xl border ${ratingStyle === 'bars' ? 'border-blue-500 ring-2 ring-blue-500/30' : 'border-gray-700/50'} cursor-pointer hover:bg-[#1E1E20]/80 transition-all min-w-[130px]`}
                  onClick={() => updateRatingStyle('bars')}
                >
                  <div className="h-20 bg-[#2A2A2E] rounded-lg mb-3 flex items-center justify-center">
                    <div className="w-2/3">
                      <div className="w-full bg-gray-700 h-2 rounded-full overflow-hidden">
                        <div className="bg-blue-500 h-full rounded-full" style={{ width: '80%' }}></div>
                      </div>
                    </div>
                  </div>
                  <h4 className="text-sm font-medium text-gray-200 text-center">Progress Bars</h4>
                </div>
                
                <div 
                  ref={el => styleRefs.current['emoji'] = el}
                  className={`bg-[#1E1E20] p-3 rounded-xl border ${ratingStyle === 'emoji' ? 'border-blue-500 ring-2 ring-blue-500/30' : 'border-gray-700/50'} cursor-pointer hover:bg-[#1E1E20]/80 transition-all min-w-[130px]`}
                  onClick={() => updateRatingStyle('emoji')}
                >
                  <div className="h-20 bg-[#2A2A2E] rounded-lg mb-3 flex items-center justify-center">
                    <div className="text-xl">😊</div>
                  </div>
                  <h4 className="text-sm font-medium text-gray-200 text-center">Emoji</h4>
                </div>
                
                <div 
                  ref={el => styleRefs.current['percent'] = el}
                  className={`bg-[#1E1E20] p-3 rounded-xl border ${ratingStyle === 'percent' ? 'border-blue-500 ring-2 ring-blue-500/30' : 'border-gray-700/50'} cursor-pointer hover:bg-[#1E1E20]/80 transition-all min-w-[130px]`}
                  onClick={() => updateRatingStyle('percent')}
                >
                  <div className="h-20 bg-[#2A2A2E] rounded-lg mb-3 flex items-center justify-center">
                    <div className="flex items-center">
                      <span className="text-cyan-500 font-bold text-xl">94%</span>
                    </div>
                  </div>
                  <h4 className="text-sm font-medium text-gray-200 text-center">Percent</h4>
                </div>
              </div>
            </div>
          </div>
          
          {/* Card Style */}
          <div className="bg-gradient-to-br from-[#2A2A2E] to-[#252530] p-5 rounded-2xl shadow-lg border border-gray-700/30">
            <div className="flex items-center mb-5">
              <LayoutTemplate size={18} className="text-blue-400 mr-2" />
                              <h3 className="text-xl font-medium text-gray-200">Card Layout</h3>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Card Style Options */}
              <div 
                className={`bg-[#1E1E20] p-4 rounded-xl border ${cardStyle === 'modern' ? 'border-blue-500 ring-2 ring-blue-500/30' : 'border-gray-700/50'} cursor-pointer hover:bg-[#1E1E20]/80 transition-all`}
                onClick={() => updateCardStyle('modern')}
              >
                <div className="h-16 bg-[#2A2A2E] rounded-lg mb-3 flex items-center justify-center p-3">
                  <div className="flex flex-col w-full items-center">
                    <div className="h-2 w-1/3 bg-gray-600 rounded-full mb-2"></div>
                    <div className="flex space-x-1">
                      <div className="h-3 w-3 bg-blue-500 rounded-full"></div>
                      <div className="h-3 w-3 bg-blue-500 rounded-full"></div>
                      <div className="h-3 w-3 bg-blue-500 rounded-full"></div>
                      <div className="h-3 w-3 bg-blue-500 rounded-full"></div>
                      <div className="h-3 w-3 bg-gray-600 rounded-full"></div>
                    </div>
                  </div>
                </div>
                <h4 className="text-sm font-medium text-gray-200 text-center">Center</h4>
                <p className="text-xs text-gray-500 text-center mt-1">Elements centered in the middle</p>
              </div>
              
              <div 
                className={`bg-[#1E1E20] p-4 rounded-xl border ${cardStyle === 'compact' ? 'border-blue-500 ring-2 ring-blue-500/30' : 'border-gray-700/50'} cursor-pointer hover:bg-[#1E1E20]/80 transition-all`}
                onClick={() => updateCardStyle('compact')}
              >
                <div className="h-16 bg-[#2A2A2E] rounded-lg mb-3 flex items-center justify-start p-3">
                  <div className="flex flex-col items-start w-full">
                    <div className="h-2 w-1/3 bg-gray-600 rounded-full mb-2"></div>
                    <div className="flex space-x-1">
                      <div className="h-3 w-3 bg-blue-500 rounded-full"></div>
                      <div className="h-3 w-3 bg-blue-500 rounded-full"></div>
                      <div className="h-3 w-3 bg-blue-500 rounded-full"></div>
                      <div className="h-3 w-3 bg-blue-500 rounded-full"></div>
                      <div className="h-3 w-3 bg-gray-600 rounded-full"></div>
                    </div>
                  </div>
                </div>
                <h4 className="text-sm font-medium text-gray-200 text-center">Left</h4>
                <p className="text-xs text-gray-500 text-center mt-1">Elements aligned to the left</p>
              </div>
              
              <div 
                className={`bg-[#1E1E20] p-4 rounded-xl border ${cardStyle === 'detailed' ? 'border-blue-500 ring-2 ring-blue-500/30' : 'border-gray-700/50'} cursor-pointer hover:bg-[#1E1E20]/80 transition-all`}
                onClick={() => updateCardStyle('detailed')}
              >
                <div className="h-16 bg-[#2A2A2E] rounded-lg mb-3 flex items-center justify-end p-3">
                  <div className="flex flex-col items-end w-full">
                    <div className="h-2 w-1/3 bg-gray-600 rounded-full mb-2"></div>
                    <div className="flex space-x-1">
                      <div className="h-3 w-3 bg-blue-500 rounded-full"></div>
                      <div className="h-3 w-3 bg-blue-500 rounded-full"></div>
                      <div className="h-3 w-3 bg-blue-500 rounded-full"></div>
                      <div className="h-3 w-3 bg-blue-500 rounded-full"></div>
                      <div className="h-3 w-3 bg-gray-600 rounded-full"></div>
                    </div>
                    <div className="h-1 w-16 bg-gray-600 rounded-full mt-2"></div>
                  </div>
                </div>
                <h4 className="text-sm font-medium text-gray-200 text-center">Right</h4>
                <p className="text-xs text-gray-500 text-center mt-1">Elements aligned to the right</p>
              </div>
            </div>
          </div>
          
          {/* Additional Settings */}
          <div className="bg-gradient-to-br from-[#2A2A2E] to-[#252530] p-5 rounded-2xl shadow-lg border border-gray-700/30">
            <div className="flex items-center mb-5">
              <Sliders size={18} className="text-green-400 mr-2" />
              <h3 className="text-xl font-medium text-gray-200">Additional Options</h3>
            </div>
            
            <div className="space-y-5">
              {/* Font Style */}
              <div>
                <label className="text-sm font-medium text-gray-300 mb-3 block">Font Style</label>
                <div className="grid grid-cols-3 gap-3">
                  <button
                    onClick={() => updateFontStyle('default')}
                    className={`py-2 rounded-lg text-sm ${
                      fontStyle === 'default' 
                        ? 'bg-blue-600 text-white' 
                        : 'bg-[#1E1E20] text-gray-300 hover:bg-[#2A2A2E]'
                    }`}
                  >
                    Default
                  </button>
                  <button
                    onClick={() => updateFontStyle('modern')}
                    className={`py-2 rounded-lg text-sm ${
                      fontStyle === 'modern' 
                        ? 'bg-blue-600 text-white' 
                        : 'bg-[#1E1E20] text-gray-300 hover:bg-[#2A2A2E]'
                    }`}
                  >
                    Modern
                  </button>

                </div>
              </div>
            </div>
          </div>
          
          {/* Share Your Design Section */}
          <div className="mt-6 pt-6 border-t border-gray-700/30">
            <div className="bg-gradient-to-br from-[#2A2A2E] to-[#252530] p-5 rounded-2xl shadow-lg border border-gray-700/30">
              <div className="flex items-center mb-5">
                <Share2 size={18} className="text-blue-400 mr-2" />
                <h3 className="text-lg font-medium text-gray-200">Share Your Design</h3>
              </div>
              
              <div className="space-y-5">
                {/* Export Design Code */}
                <div className="bg-[#1E1E20] p-4 rounded-xl border border-gray-700/50">
                  <label className="text-sm font-medium text-gray-300 mb-3 block flex items-center">
                    <Download size={14} className="mr-1 text-blue-400" />
                    <span>Export Design Code</span>
                  </label>
                  <div className="flex items-center space-x-2">
                    <input
                      ref={shareCodeRef}
                      type="text"
                      readOnly
                      value={shareCode}
                      className="flex-1 bg-[#1E1E20] border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/50 font-mono"
                    />
                    <button 
                      onClick={() => void generateShareCode()}
                      className="p-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                      title="Generate code"
                      disabled={isSaving}
                    >
                      <Share2 size={18} />
                    </button>
                    <button 
                      onClick={copyShareCode}
                      className="p-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                      title="Copy to clipboard"
                    >
                      {copied ? <CheckCircle2 size={18} /> : <Copy size={18} />}
                    </button>
                  </div>
                  <p className="text-xs text-gray-400 mt-2">Share this code with others to let them use your design.</p>
                </div>
                
                {/* Import Design Code */}
                <div className="bg-[#1E1E20] p-4 rounded-xl border border-gray-700/50">
                  <label className="text-sm font-medium text-gray-300 mb-3 block flex items-center">
                    <Upload size={14} className="mr-1 text-purple-400" />
                    <span>Import Design Code</span>
                  </label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="text"
                      value={importCode}
                      onChange={(e) => setImportCode(e.target.value)}
                      placeholder="Paste design code here"
                      className="flex-1 bg-[#1E1E20] border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/50 font-mono"
                    />
                    <button 
                      onClick={applyImportedDesign}
                      className="px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors text-sm font-medium"
                    >
                      Apply
                    </button>
                  </div>
                  <p className="text-xs text-gray-400 mt-2">Enter a design code from someone else to apply their settings.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        {/* Right Column - Profile Preview */}
        <div className="flex flex-col">
          {/* Profile Preview Card - Similar to the image */}
          <div 
            style={theme === 'custom' ? {background: `linear-gradient(135deg, ${customThemeColors.primary}, ${customThemeColors.secondary})`} : {}}
            className={`${
            theme === 'dark' ? 'bg-[#1A1A1E]' : 
            theme === 'gradient' ? 'bg-gradient-to-br from-gray-900 to-gray-800' : 
            theme === 'luxury' ? 'bg-gradient-to-br from-gray-900 to-stone-900' :
            theme === 'elegant' ? 'bg-gradient-to-r from-[#232526] to-[#414345]' :
            theme === 'neon' ? 'bg-[#0d0d0f]' :
            theme === 'forest' ? 'bg-gradient-to-br from-green-900 to-emerald-800' :
            theme === 'cosmic' ? 'bg-gradient-to-br from-indigo-900 to-purple-900' :
            theme === 'minimalist' ? 'bg-white' :
            theme === 'tech' ? 'bg-gradient-to-br from-sky-900 to-cyan-800' :
            theme === 'pastel' ? 'bg-gradient-to-br from-pink-200 to-sky-200' :
            theme === 'monochrome' ? 'bg-gradient-to-br from-zinc-700 to-zinc-900' :
            'bg-[#1E1E20]'
                      } rounded-2xl shadow-lg ${
            theme === 'gradient' ? 'border border-blue-500/50' : 
            theme === 'dark' ? 'border border-gray-800' : 
            theme === 'luxury' ? 'border-2 border-yellow-500/20' :
            theme === 'elegant' ? 'border border-amber-500/30' : 
            theme === 'neon' ? 'shadow-[0_0_20px_2px_rgba(168,85,247,0.15)] border border-purple-500/30' : 
            theme === 'forest' ? 'border border-emerald-500/30' :
            theme === 'cosmic' ? 'border border-indigo-500/30' :
            theme === 'minimalist' ? 'border border-gray-200' :
            theme === 'tech' ? 'border border-cyan-500/30' :
            theme === 'pastel' ? 'border border-pink-200' :
            theme === 'monochrome' ? 'border border-zinc-700' :
            theme === 'custom' ? 'border border-gray-700/50' :
            'border border-gray-700/50'
          } sticky top-4 h-full overflow-hidden`}>
            {/* Header Image */}
            <div 
              style={theme === 'custom' ? {background: `linear-gradient(135deg, ${customThemeColors.primary}, ${customThemeColors.secondary})`} : {}}
              className={`h-48 ${
              theme === 'gradient' ? 'bg-gradient-to-br from-gray-900 to-gray-800' : 
              theme === 'dark' ? 'bg-[#1A1A1E]' : 
              theme === 'luxury' ? 'bg-gradient-to-br from-gray-900 to-stone-900' :
              theme === 'elegant' ? 'bg-gradient-to-r from-[#232526] to-[#414345]' :
              theme === 'neon' ? 'bg-[#0d0d0f]' :
              theme === 'forest' ? 'bg-gradient-to-br from-green-900 to-emerald-800' :
              theme === 'cosmic' ? 'bg-gradient-to-br from-indigo-900 to-purple-900' :
              theme === 'minimalist' ? 'bg-[#f5f5f5]' :
              theme === 'tech' ? 'bg-gradient-to-br from-sky-900 to-cyan-800' :
              theme === 'pastel' ? 'bg-gradient-to-br from-pink-200 to-sky-200' :
              theme === 'monochrome' ? 'bg-gradient-to-br from-zinc-700 to-zinc-900' :
              'bg-[#2A2A2E]'
            } rounded-t-2xl relative overflow-hidden`}>
              <div className={`absolute inset-0 ${theme === 'minimalist' || theme === 'pastel' ? 'bg-black/10' : 'bg-black/30'}`}></div>
              {theme === 'neon' && (
                <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-purple-500/50 to-transparent"></div>
              )}
              {theme === 'elegant' && (
                <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-amber-500/30 to-transparent"></div>
              )}
            </div>
            
            {/* Profile Content */}
            <div 
              style={theme === 'custom' ? {background: `linear-gradient(135deg, ${customThemeColors.primary}, ${customThemeColors.secondary})`} : {}}
              className={`px-6 pb-6 pt-6 relative ${
              theme === 'dark' ? 'bg-[#1A1A1E]' : 
              theme === 'gradient' ? 'bg-gradient-to-br from-gray-900 to-gray-800' : 
              theme === 'luxury' ? 'bg-gradient-to-br from-gray-900 to-stone-900' :
              theme === 'elegant' ? 'bg-gradient-to-r from-[#232526] to-[#414345]' :
              theme === 'neon' ? 'bg-[#0d0d0f]' :
              theme === 'forest' ? 'bg-gradient-to-br from-green-900 to-emerald-800' :
              theme === 'cosmic' ? 'bg-gradient-to-br from-indigo-900 to-purple-900' :
              theme === 'minimalist' ? 'bg-white' :
              theme === 'tech' ? 'bg-gradient-to-br from-sky-900 to-cyan-800' :
              theme === 'pastel' ? 'bg-gradient-to-br from-pink-200 to-sky-200' :
              theme === 'monochrome' ? 'bg-gradient-to-br from-zinc-700 to-zinc-900' :
              'bg-[#2A2A2E]'
            }`}>
              {/* Profile Image - تعديل الموضع ليتغير حسب نمط البطاقة */}
              <div className={`absolute -top-20 flex ${
                cardStyle === 'modern' ? 'left-1/2 transform -translate-x-1/2 justify-center' : 
                cardStyle === 'compact' ? 'left-6 justify-start' : 
                cardStyle === 'detailed' ? 'right-6 justify-end' : 'left-6 justify-start'
              }`}>
                <div className={`w-32 h-32 rounded-full bg-white p-1 shadow-lg hover:shadow-xl transition-shadow ${
                  theme === 'gradient' ? 'border border-blue-500/50' : ''
                }`}>
                  <div className="w-full h-full rounded-full flex items-center justify-center overflow-hidden">
                    <img 
                      src="https://cdn.discordapp.com/avatars/1137470473819656293/5fdb66437c22488495ff102924ba0b80.webp?size=4096" 
                      alt="zkr profile" 
                      className="w-full h-full object-cover"
                    />
                  </div>
                </div>
              </div>
              
              {/* Content with spacing for image */}
              <div className="mt-20">
                {/* Name and Verification */}
                <div className="flex items-center justify-between mb-1">
                  <div className={`flex items-center ${
                    cardStyle === 'modern' ? 'mx-auto' : 
                    cardStyle === 'compact' ? 'mr-auto' : 
                    cardStyle === 'detailed' ? 'ml-auto' : ''
                  }`}>
                    <h3 
                      style={theme === 'custom' ? {color: customThemeColors.text} : {}}
                      className={`text-xl font-bold ${
                      theme === 'dark' ? 'text-gray-200' : 
                      theme === 'minimalist' ? 'text-gray-800' :
                      theme === 'pastel' ? 'text-gray-800' :
                      'text-white'
                    } mr-2 font-${fontStyle === 'modern' ? 'medium' : fontStyle === 'classic' ? 'serif' : 'normal'}`}>zkr</h3>
                    <div className={`w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center shadow-md`}>
                      <Check size={12} className="text-white" />
                    </div>
                  </div>
                  
                  {/* Three dots menu - vertical */}
                  <div className="relative group">
                    <button className="p-1.5 rounded-full hover:bg-gray-700/50 transition-colors">
                      <div className="flex flex-col space-y-0.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-gray-400"></div>
                        <div className="w-1.5 h-1.5 rounded-full bg-gray-400"></div>
                        <div className="w-1.5 h-1.5 rounded-full bg-gray-400"></div>
                      </div>
                    </button>
                    
                    {/* Dropdown menu */}
                    <div className="absolute right-0 mt-1 w-48 bg-[#1A1A1E] border border-gray-700 rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10 transform origin-top-right scale-95 group-hover:scale-100">
                      <div className="py-1">
                        <a href="https://discord.gg/clyne" target="_blank" rel="noopener noreferrer" className="flex w-full items-center px-4 py-2 text-sm text-gray-300 hover:bg-gray-700/50 transition-colors">
                          <Shield size={14} className="mr-2 text-red-400" />
                          <span>Report User</span>
                        </a>
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Rating Stars */}
                <div className="mb-1">
                  <div className={`flex items-center ${
                    cardStyle === 'modern' ? 'justify-center' : 
                    cardStyle === 'compact' ? 'justify-start' : 
                    cardStyle === 'detailed' ? 'justify-end' : ''
                  }`}>
                    <div className="flex">
                      {ratingStyle === 'stars' && (
                        <span 
                          style={theme === 'custom' ? {color: customThemeColors.text} : {}}
                          className={`${
                          theme === 'luxury' ? 'text-yellow-500' :
                          theme === 'elegant' ? 'text-amber-400' :
                          theme === 'neon' ? 'text-purple-400' :
                          theme === 'forest' ? 'text-emerald-400' :
                          theme === 'cosmic' ? 'text-indigo-400' :
                          theme === 'minimalist' ? 'text-gray-600' :
                          theme === 'tech' ? 'text-cyan-400' :
                          theme === 'pastel' ? 'text-pink-400' :
                          theme === 'monochrome' ? 'text-zinc-400' :
                          `text-blue-400`
                        }`}>★★★★★</span>
                      )}
                      {ratingStyle === 'numbers' && (
                        <span 
                          style={theme === 'custom' ? {color: customThemeColors.text} : {}}
                          className={`${
                          theme === 'luxury' ? 'text-yellow-500' :
                          theme === 'elegant' ? 'text-amber-400' :
                          theme === 'neon' ? 'text-purple-400' :
                          theme === 'forest' ? 'text-emerald-400' :
                          theme === 'cosmic' ? 'text-indigo-400' :
                          theme === 'minimalist' ? 'text-gray-600' :
                          theme === 'tech' ? 'text-cyan-400' :
                          theme === 'pastel' ? 'text-pink-400' :
                          theme === 'monochrome' ? 'text-zinc-400' :
                          `text-blue-400`
                        } font-bold`}>4.7<span className="text-gray-400 font-normal text-sm">/5</span></span>
                      )}
                      {ratingStyle === 'bars' && (
                        <div className="w-24 bg-gray-700 h-2 rounded-full overflow-hidden">
                          <div className={`${
                            theme === 'luxury' ? 'bg-yellow-500' :
                            theme === 'elegant' ? 'bg-amber-500' :
                            theme === 'neon' ? 'bg-purple-500' :
                            theme === 'forest' ? 'bg-emerald-500' :
                            theme === 'cosmic' ? 'bg-indigo-500' :
                            theme === 'minimalist' ? 'bg-gray-500' :
                            theme === 'tech' ? 'bg-cyan-500' :
                            theme === 'pastel' ? 'bg-pink-500' :
                            theme === 'monochrome' ? 'bg-zinc-500' :
                            `bg-blue-500`
                          } h-full rounded-full`} style={{ width: '94%' }}></div>
                        </div>
                      )}
                      {ratingStyle === 'emoji' && (
                        <div className="text-xl">😊</div>
                      )}
                      {ratingStyle === 'percent' && (
                        <div className="flex items-center">
                          <span className="text-cyan-500 font-bold">94%</span>
                        </div>
                      )}
                    </div>
                    <span className={`text-gray-400 text-sm ml-2 font-${fontStyle === 'modern' ? 'medium' : fontStyle === 'classic' ? 'serif' : 'normal'}`}>
                      {ratingStyle === 'percent' ? 'Positive Rating' : 
                       ratingStyle === 'numbers' ? 'stars' : '4.7 stars'}
                    </span>
                  </div>
                </div>
                
                {/* Bio */}
                <p className={`text-gray-400 text-sm mb-4 font-${fontStyle === 'modern' ? 'medium' : fontStyle === 'classic' ? 'serif' : 'normal'} ${
                  cardStyle === 'modern' ? 'text-center' : 
                  cardStyle === 'compact' ? 'text-left' : 
                  cardStyle === 'detailed' ? 'text-right' : ''
                }`}>
                  Lorem ipsum dolor sit amet, Eam stabilem appell consectetur adipiscing elit. Duo Reges constructio interrete itaque
                </p>
                
                {/* Tabs */}
                <div className={`flex border-b ${theme === 'dark' ? 'border-gray-800' : 'border-gray-700'}`}>
                  <div 
                    onClick={() => setActiveTab('reviews')}
                    style={theme === 'custom' ? {borderColor: activeTab === 'reviews' ? customThemeColors.primary : 'transparent', color: customThemeColors.text} : {}}
                    className={`px-6 py-3 font-medium cursor-pointer hover:text-gray-300 transition-colors ${
                    activeTab === 'reviews' ? `text-gray-300 border-b-2 ${
                      theme === 'elegant' ? 'border-amber-500' :
                      theme === 'neon' ? 'border-purple-500' :
                      theme === 'forest' ? 'border-emerald-500' :
                      theme === 'cosmic' ? 'border-indigo-500' :
                      theme === 'minimalist' ? 'border-gray-500' :
                      theme === 'tech' ? 'border-cyan-500' :
                      theme === 'luxury' ? 'border-yellow-500' :
                      theme === 'pastel' ? 'border-pink-500' :
                      theme === 'monochrome' ? 'border-zinc-500' :
                      theme === 'custom' ? '' :
                      `border-blue-500`
                    }` : 'text-gray-500 border-b-2 border-transparent'
                  }`}>
                    Reviews
                  </div>
                  <div 
                    onClick={() => setActiveTab('statistics')}
                    style={theme === 'custom' ? {borderColor: activeTab === 'statistics' ? customThemeColors.primary : 'transparent', color: customThemeColors.text} : {}}
                    className={`px-6 py-3 font-medium cursor-pointer hover:text-gray-300 transition-colors ${
                    activeTab === 'statistics' ? `text-gray-300 border-b-2 ${
                      theme === 'elegant' ? 'border-amber-500' :
                      theme === 'neon' ? 'border-purple-500' :
                      theme === 'forest' ? 'border-emerald-500' :
                      theme === 'cosmic' ? 'border-indigo-500' :
                      theme === 'minimalist' ? 'border-gray-500' :
                      theme === 'tech' ? 'border-cyan-500' :
                      theme === 'luxury' ? 'border-yellow-500' :
                      theme === 'pastel' ? 'border-pink-500' :
                      theme === 'monochrome' ? 'border-zinc-500' :
                      theme === 'custom' ? '' :
                      `border-blue-500`
                    }` : 'text-gray-500 border-b-2 border-transparent'
                  }`}>
                    Statistics
                  </div>
                </div>
                
                {/* Tab Content */}
                {activeTab === 'reviews' && (
                  <div className="mt-6 space-y-4 max-h-[400px] overflow-y-auto pr-2">
                    <h3 className={`text-lg font-medium ${
                      theme === 'custom' ? 'text-white' : 
                      theme === 'minimalist' ? 'text-gray-800' :
                      theme === 'pastel' ? 'text-gray-800' :
                      'text-gray-200'
                    } mb-3 ${
                      cardStyle === 'modern' ? 'text-center' : 
                      cardStyle === 'compact' ? 'text-left' : 
                      cardStyle === 'detailed' ? 'text-right' : ''
                    }`}>Customer Reviews</h3>
                    
                    {/* Review 1 */}
                    <div className={`${
                      theme === 'minimalist' ? 'bg-gray-100' :
                      theme === 'pastel' ? 'bg-pink-100/30' :
                      theme === 'luxury' ? 'bg-[#1A1A1A]/70' :
                      theme === 'neon' ? 'bg-[#0d0d0f]/80 shadow-[0_0_10px_1px_rgba(168,85,247,0.15)]' :
                      theme === 'custom' ? 'bg-[#1E1E20]/70' :
                      'bg-[#1E1E20]/70'
                    } p-4 rounded-xl border ${
                      theme === 'luxury' ? 'border-yellow-500/20' :
                      theme === 'elegant' ? 'border-amber-500/20' :
                      theme === 'neon' ? 'border-purple-500/20' :
                      theme === 'forest' ? 'border-emerald-500/20' :
                      theme === 'cosmic' ? 'border-indigo-500/20' :
                      theme === 'minimalist' ? 'border-gray-200' :
                      theme === 'tech' ? 'border-cyan-500/20' :
                      theme === 'pastel' ? 'border-pink-200/50' :
                      theme === 'monochrome' ? 'border-zinc-700/50' :
                      'border-gray-700/50'
                    }`}>
                      <div className={`flex items-start ${
                        cardStyle === 'detailed' ? 'flex-row-reverse text-right' : 'text-left'
                      }`}>
                        <div className={`w-10 h-10 rounded-full overflow-hidden flex-shrink-0 ${
                          cardStyle === 'detailed' ? 'mr-0 ml-3' : 'mr-3'
                        }`}>
                          <img src="https://randomuser.me/api/portraits/men/32.jpg" alt="User" className="w-full h-full object-cover" />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <h4 className={`font-medium ${
                              theme === 'custom' ? 'text-white' : 
                              theme === 'minimalist' ? 'text-gray-800' :
                              theme === 'pastel' ? 'text-gray-800' :
                              'text-gray-200'
                            }`}>أحمد محمد</h4>
                            <span className="text-xs text-gray-500">12 مايو 2025</span>
                          </div>
                          <div className={`flex mt-1 mb-2 ${
                            cardStyle === 'modern' ? 'justify-center' : 
                            cardStyle === 'detailed' ? 'justify-end' : ''
                          }`}>
                            <span className={`${
                              theme === 'luxury' ? 'text-yellow-500' : 
                              theme === 'elegant' ? 'text-amber-400' :
                              theme === 'neon' ? 'text-purple-400' :
                              theme === 'forest' ? 'text-emerald-400' :
                              theme === 'cosmic' ? 'text-indigo-400' :
                              theme === 'minimalist' ? 'text-gray-600' :
                              theme === 'tech' ? 'text-cyan-400' :
                              theme === 'pastel' ? 'text-pink-400' :
                              theme === 'monochrome' ? 'text-zinc-400' :
                              theme === 'custom' ? 'text-blue-400' :
                              'text-blue-400'
                            } text-sm`}>★★★★★</span>
                          </div>
                          <p className={`text-sm text-gray-400 ${
                            cardStyle === 'modern' ? 'text-center' : 
                            cardStyle === 'detailed' ? 'text-right' : ''
                          }`}>خدمة ممتازة وسريعة جداً، أنصح بالتعامل معهم. التطبيق سهل الاستخدام والدعم الفني متعاون.</p>
                        </div>
                      </div>
                    </div>
                    
                    {/* Review 2 */}
                    <div className={`${
                      theme === 'minimalist' ? 'bg-gray-100' :
                      theme === 'pastel' ? 'bg-pink-100/30' :
                      theme === 'luxury' ? 'bg-[#1A1A1A]/70' :
                      theme === 'neon' ? 'bg-[#0d0d0f]/80 shadow-[0_0_10px_1px_rgba(168,85,247,0.15)]' :
                      theme === 'custom' ? 'bg-[#1E1E20]/70' :
                      'bg-[#1E1E20]/70'
                    } p-4 rounded-xl border ${
                      theme === 'luxury' ? 'border-yellow-500/20' :
                      theme === 'elegant' ? 'border-amber-500/20' :
                      theme === 'neon' ? 'border-purple-500/20' :
                      theme === 'forest' ? 'border-emerald-500/20' :
                      theme === 'cosmic' ? 'border-indigo-500/20' :
                      theme === 'minimalist' ? 'border-gray-200' :
                      theme === 'tech' ? 'border-cyan-500/20' :
                      theme === 'pastel' ? 'border-pink-200/50' :
                      theme === 'monochrome' ? 'border-zinc-700/50' :
                      'border-gray-700/50'
                    }`}>
                      <div className={`flex items-start ${
                        cardStyle === 'detailed' ? 'flex-row-reverse text-right' : 'text-left'
                      }`}>
                        <div className={`w-10 h-10 rounded-full overflow-hidden flex-shrink-0 ${
                          cardStyle === 'detailed' ? 'mr-0 ml-3' : 'mr-3'
                        }`}>
                          <img src="https://randomuser.me/api/portraits/women/44.jpg" alt="User" className="w-full h-full object-cover" />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <h4 className={`font-medium ${
                              theme === 'custom' ? 'text-white' : 
                              theme === 'minimalist' ? 'text-gray-800' :
                              theme === 'pastel' ? 'text-gray-800' :
                              'text-gray-200'
                            }`}>سارة خالد</h4>
                            <span className="text-xs text-gray-500">5 مايو 2025</span>
                          </div>
                          <div className={`flex mt-1 mb-2 ${
                            cardStyle === 'modern' ? 'justify-center' : 
                            cardStyle === 'detailed' ? 'justify-end' : ''
                          }`}>
                            <span className={`${
                              theme === 'luxury' ? 'text-yellow-500' : 
                              theme === 'elegant' ? 'text-amber-400' :
                              theme === 'neon' ? 'text-purple-400' :
                              theme === 'forest' ? 'text-emerald-400' :
                              theme === 'cosmic' ? 'text-indigo-400' :
                              theme === 'minimalist' ? 'text-gray-600' :
                              theme === 'tech' ? 'text-cyan-400' :
                              theme === 'pastel' ? 'text-pink-400' :
                              theme === 'monochrome' ? 'text-zinc-400' :
                              theme === 'custom' ? 'text-blue-400' :
                              'text-blue-400'
                            } text-sm`}>★★★★<span className="text-gray-600">★</span></span>
                          </div>
                          <p className={`text-sm text-gray-400 ${
                            cardStyle === 'modern' ? 'text-center' : 
                            cardStyle === 'detailed' ? 'text-right' : ''
                          }`}>تجربة رائعة، المنتج وصل بسرعة وبحالة ممتازة. سأتعامل معهم مرة أخرى بالتأكيد.</p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Statistics Tab Content */}
                {activeTab === 'statistics' && (
                  <div className="mt-6 space-y-6 max-h-[400px] overflow-y-auto pr-2">
                    <h3 className={`text-lg font-medium ${
                      theme === 'custom' ? 'text-white' : 
                      theme === 'minimalist' ? 'text-gray-800' :
                      theme === 'pastel' ? 'text-gray-800' :
                      'text-gray-200'
                    } mb-4 ${
                      cardStyle === 'modern' ? 'text-center' : 
                      cardStyle === 'compact' ? 'text-left' : 
                      cardStyle === 'detailed' ? 'text-right' : ''
                    }`}>Rating Distribution</h3>
                    
                    {/* Rating Distribution */}
                    <div className={`p-4 rounded-xl ${
                      theme === 'minimalist' ? 'bg-gray-100' :
                      theme === 'pastel' ? 'bg-pink-100/30' :
                      theme === 'luxury' ? 'bg-[#1A1A1A]/70' :
                      theme === 'neon' ? 'bg-[#0d0d0f]/80 shadow-[0_0_10px_1px_rgba(168,85,247,0.15)]' :
                      theme === 'custom' ? 'bg-[#1E1E20]/70' :
                      'bg-[#1E1E20]/70'
                    } border ${
                      theme === 'luxury' ? 'border-yellow-500/20' :
                      theme === 'elegant' ? 'border-amber-500/20' :
                      theme === 'neon' ? 'border-purple-500/20' :
                      theme === 'forest' ? 'border-emerald-500/20' :
                      theme === 'cosmic' ? 'border-indigo-500/20' :
                      theme === 'minimalist' ? 'border-gray-200' :
                      theme === 'tech' ? 'border-cyan-500/20' :
                      theme === 'pastel' ? 'border-pink-200/50' :
                      theme === 'monochrome' ? 'border-zinc-700/50' :
                      'border-gray-700/50'
                    }`}>
                      {/* 5 Stars */}
                      <div className="flex items-center mb-2">
                        <div className="flex items-center w-8">
                          <span className={`text-sm ${
                            theme === 'luxury' ? 'text-yellow-500' : 
                            theme === 'elegant' ? 'text-amber-400' :
                            theme === 'neon' ? 'text-purple-400' :
                            theme === 'forest' ? 'text-emerald-400' :
                            theme === 'cosmic' ? 'text-indigo-400' :
                            theme === 'minimalist' ? 'text-gray-600' :
                            theme === 'tech' ? 'text-cyan-400' :
                            theme === 'pastel' ? 'text-pink-400' :
                            theme === 'monochrome' ? 'text-zinc-400' :
                            'text-yellow-400'
                          }`}>5 ★</span>
                        </div>
                        <div className="flex-1 mx-3">
                          <div className="w-full bg-gray-700 rounded-full h-2.5">
                            <div className={`h-2.5 rounded-full ${
                              theme === 'luxury' ? 'bg-yellow-500' :
                              theme === 'elegant' ? 'bg-amber-500' :
                              theme === 'neon' ? 'bg-purple-500' :
                              theme === 'forest' ? 'bg-emerald-500' :
                              theme === 'cosmic' ? 'bg-indigo-500' :
                              theme === 'minimalist' ? 'bg-gray-500' :
                              theme === 'tech' ? 'bg-cyan-500' :
                              theme === 'pastel' ? 'bg-pink-500' :
                              theme === 'monochrome' ? 'bg-zinc-500' :
                              'bg-yellow-500'
                            }`} style={{ width: '67%' }}></div>
                          </div>
                        </div>
                        <div className="w-10 text-right">
                          <span className="text-gray-400 text-sm">67%</span>
                        </div>
                      </div>
                      
                      {/* 4 Stars */}
                      <div className="flex items-center mb-2">
                        <div className="flex items-center w-8">
                          <span className={`text-sm ${
                            theme === 'luxury' ? 'text-yellow-500' : 
                            theme === 'elegant' ? 'text-amber-400' :
                            theme === 'neon' ? 'text-purple-400' :
                            theme === 'forest' ? 'text-emerald-400' :
                            theme === 'cosmic' ? 'text-indigo-400' :
                            theme === 'minimalist' ? 'text-gray-600' :
                            theme === 'tech' ? 'text-cyan-400' :
                            theme === 'pastel' ? 'text-pink-400' :
                            theme === 'monochrome' ? 'text-zinc-400' :
                            'text-yellow-400'
                          }`}>4 ★</span>
                        </div>
                        <div className="flex-1 mx-3">
                          <div className="w-full bg-gray-700 rounded-full h-2.5">
                            <div className={`h-2.5 rounded-full ${
                              theme === 'luxury' ? 'bg-yellow-500' :
                              theme === 'elegant' ? 'bg-amber-500' :
                              theme === 'neon' ? 'bg-purple-500' :
                              theme === 'forest' ? 'bg-emerald-500' :
                              theme === 'cosmic' ? 'bg-indigo-500' :
                              theme === 'minimalist' ? 'bg-gray-500' :
                              theme === 'tech' ? 'bg-cyan-500' :
                              theme === 'pastel' ? 'bg-pink-500' :
                              theme === 'monochrome' ? 'bg-zinc-500' :
                              'bg-yellow-500'
                            }`} style={{ width: '0%' }}></div>
                          </div>
                        </div>
                        <div className="w-10 text-right">
                          <span className="text-gray-400 text-sm">0%</span>
                        </div>
                      </div>
                      
                      {/* 3 Stars */}
                      <div className="flex items-center mb-2">
                        <div className="flex items-center w-8">
                          <span className={`text-sm ${
                            theme === 'luxury' ? 'text-yellow-500' : 
                            theme === 'elegant' ? 'text-amber-400' :
                            theme === 'neon' ? 'text-purple-400' :
                            theme === 'forest' ? 'text-emerald-400' :
                            theme === 'cosmic' ? 'text-indigo-400' :
                            theme === 'minimalist' ? 'text-gray-600' :
                            theme === 'tech' ? 'text-cyan-400' :
                            theme === 'pastel' ? 'text-pink-400' :
                            theme === 'monochrome' ? 'text-zinc-400' :
                            'text-yellow-400'
                          }`}>3 ★</span>
                        </div>
                        <div className="flex-1 mx-3">
                          <div className="w-full bg-gray-700 rounded-full h-2.5">
                            <div className={`h-2.5 rounded-full ${
                              theme === 'luxury' ? 'bg-yellow-500' :
                              theme === 'elegant' ? 'bg-amber-500' :
                              theme === 'neon' ? 'bg-purple-500' :
                              theme === 'forest' ? 'bg-emerald-500' :
                              theme === 'cosmic' ? 'bg-indigo-500' :
                              theme === 'minimalist' ? 'bg-gray-500' :
                              theme === 'tech' ? 'bg-cyan-500' :
                              theme === 'pastel' ? 'bg-pink-500' :
                              theme === 'monochrome' ? 'bg-zinc-500' :
                              'bg-yellow-500'
                            }`} style={{ width: '33%' }}></div>
                          </div>
                        </div>
                        <div className="w-10 text-right">
                          <span className="text-gray-400 text-sm">33%</span>
                        </div>
                      </div>
                      
                      {/* 2 Stars */}
                      <div className="flex items-center mb-2">
                        <div className="flex items-center w-8">
                          <span className={`text-sm ${
                            theme === 'luxury' ? 'text-yellow-500' : 
                            theme === 'elegant' ? 'text-amber-400' :
                            theme === 'neon' ? 'text-purple-400' :
                            theme === 'forest' ? 'text-emerald-400' :
                            theme === 'cosmic' ? 'text-indigo-400' :
                            theme === 'minimalist' ? 'text-gray-600' :
                            theme === 'tech' ? 'text-cyan-400' :
                            theme === 'pastel' ? 'text-pink-400' :
                            theme === 'monochrome' ? 'text-zinc-400' :
                            'text-yellow-400'
                          }`}>2 ★</span>
                        </div>
                        <div className="flex-1 mx-3">
                          <div className="w-full bg-gray-700 rounded-full h-2.5">
                            <div className={`h-2.5 rounded-full ${
                              theme === 'luxury' ? 'bg-yellow-500' :
                              theme === 'elegant' ? 'bg-amber-500' :
                              theme === 'neon' ? 'bg-purple-500' :
                              theme === 'forest' ? 'bg-emerald-500' :
                              theme === 'cosmic' ? 'bg-indigo-500' :
                              theme === 'minimalist' ? 'bg-gray-500' :
                              theme === 'tech' ? 'bg-cyan-500' :
                              theme === 'pastel' ? 'bg-pink-500' :
                              theme === 'monochrome' ? 'bg-zinc-500' :
                              'bg-yellow-500'
                            }`} style={{ width: '0%' }}></div>
                          </div>
                        </div>
                        <div className="w-10 text-right">
                          <span className="text-gray-400 text-sm">0%</span>
                        </div>
                      </div>
                      
                      {/* 1 Star */}
                      <div className="flex items-center">
                        <div className="flex items-center w-8">
                          <span className={`text-sm ${
                            theme === 'luxury' ? 'text-yellow-500' : 
                            theme === 'elegant' ? 'text-amber-400' :
                            theme === 'neon' ? 'text-purple-400' :
                            theme === 'forest' ? 'text-emerald-400' :
                            theme === 'cosmic' ? 'text-indigo-400' :
                            theme === 'minimalist' ? 'text-gray-600' :
                            theme === 'tech' ? 'text-cyan-400' :
                            theme === 'pastel' ? 'text-pink-400' :
                            theme === 'monochrome' ? 'text-zinc-400' :
                            'text-yellow-400'
                          }`}>1 ★</span>
                        </div>
                        <div className="flex-1 mx-3">
                          <div className="w-full bg-gray-700 rounded-full h-2.5">
                            <div className={`h-2.5 rounded-full ${
                              theme === 'luxury' ? 'bg-yellow-500' :
                              theme === 'elegant' ? 'bg-amber-500' :
                              theme === 'neon' ? 'bg-purple-500' :
                              theme === 'forest' ? 'bg-emerald-500' :
                              theme === 'cosmic' ? 'bg-indigo-500' :
                              theme === 'minimalist' ? 'bg-gray-500' :
                              theme === 'tech' ? 'bg-cyan-500' :
                              theme === 'pastel' ? 'bg-pink-500' :
                              theme === 'monochrome' ? 'bg-zinc-500' :
                              'bg-yellow-500'
                            }`} style={{ width: '0%' }}></div>
                          </div>
                        </div>
                        <div className="w-10 text-right">
                          <span className="text-gray-400 text-sm">0%</span>
                        </div>
                      </div>
                    </div>
                    
                    {/* Statistics Cards */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
                      {/* Total Reviews */}
                      <div className={`p-4 rounded-xl ${
                        theme === 'minimalist' ? 'bg-gray-100' :
                        theme === 'pastel' ? 'bg-pink-100/30' :
                        theme === 'luxury' ? 'bg-[#1A1A1A]/70' :
                        theme === 'neon' ? 'bg-[#0d0d0f]/80 shadow-[0_0_10px_1px_rgba(168,85,247,0.15)]' :
                        theme === 'custom' ? 'bg-[#1E1E20]/70' :
                        'bg-[#1E1E20]/70'
                      } border ${
                        theme === 'luxury' ? 'border-yellow-500/20' :
                        theme === 'elegant' ? 'border-amber-500/20' :
                        theme === 'neon' ? 'border-purple-500/20' :
                        theme === 'forest' ? 'border-emerald-500/20' :
                        theme === 'cosmic' ? 'border-indigo-500/20' :
                        theme === 'minimalist' ? 'border-gray-200' :
                        theme === 'tech' ? 'border-cyan-500/20' :
                        theme === 'pastel' ? 'border-pink-200/50' :
                        theme === 'monochrome' ? 'border-zinc-700/50' :
                        'border-gray-700/50'
                      } text-center`}>
                        <div className={`text-2xl font-bold ${
                          theme === 'luxury' ? 'text-yellow-500' : 
                          theme === 'elegant' ? 'text-amber-400' :
                          theme === 'neon' ? 'text-purple-400' :
                          theme === 'forest' ? 'text-emerald-400' :
                          theme === 'cosmic' ? 'text-indigo-400' :
                          theme === 'minimalist' ? 'text-gray-800' :
                          theme === 'tech' ? 'text-cyan-400' :
                          theme === 'pastel' ? 'text-pink-500' :
                          theme === 'monochrome' ? 'text-zinc-300' :
                          'text-yellow-400'
                        }`}>3</div>
                        <div className="text-gray-400 text-xs mt-1">Total Reviews</div>
                      </div>
                      
                      {/* Average Rating */}
                      <div className={`p-4 rounded-xl ${
                        theme === 'minimalist' ? 'bg-gray-100' :
                        theme === 'pastel' ? 'bg-pink-100/30' :
                        theme === 'luxury' ? 'bg-[#1A1A1A]/70' :
                        theme === 'neon' ? 'bg-[#0d0d0f]/80 shadow-[0_0_10px_1px_rgba(168,85,247,0.15)]' :
                        theme === 'custom' ? 'bg-[#1E1E20]/70' :
                        'bg-[#1E1E20]/70'
                      } border ${
                        theme === 'luxury' ? 'border-yellow-500/20' :
                        theme === 'elegant' ? 'border-amber-500/20' :
                        theme === 'neon' ? 'border-purple-500/20' :
                        theme === 'forest' ? 'border-emerald-500/20' :
                        theme === 'cosmic' ? 'border-indigo-500/20' :
                        theme === 'minimalist' ? 'border-gray-200' :
                        theme === 'tech' ? 'border-cyan-500/20' :
                        theme === 'pastel' ? 'border-pink-200/50' :
                        theme === 'monochrome' ? 'border-zinc-700/50' :
                        'border-gray-700/50'
                      } text-center`}>
                        <div className={`text-2xl font-bold ${
                          theme === 'luxury' ? 'text-yellow-500' : 
                          theme === 'elegant' ? 'text-amber-400' :
                          theme === 'neon' ? 'text-purple-400' :
                          theme === 'forest' ? 'text-emerald-400' :
                          theme === 'cosmic' ? 'text-indigo-400' :
                          theme === 'minimalist' ? 'text-gray-800' :
                          theme === 'tech' ? 'text-cyan-400' :
                          theme === 'pastel' ? 'text-pink-500' :
                          theme === 'monochrome' ? 'text-zinc-300' :
                          'text-yellow-400'
                        }`}>4.3</div>
                        <div className="text-gray-400 text-xs mt-1">Average Rating</div>
                      </div>
                      
                      {/* Most Common */}
                      <div className={`p-4 rounded-xl ${
                        theme === 'minimalist' ? 'bg-gray-100' :
                        theme === 'pastel' ? 'bg-pink-100/30' :
                        theme === 'luxury' ? 'bg-[#1A1A1A]/70' :
                        theme === 'neon' ? 'bg-[#0d0d0f]/80 shadow-[0_0_10px_1px_rgba(168,85,247,0.15)]' :
                        theme === 'custom' ? 'bg-[#1E1E20]/70' :
                        'bg-[#1E1E20]/70'
                      } border ${
                        theme === 'luxury' ? 'border-yellow-500/20' :
                        theme === 'elegant' ? 'border-amber-500/20' :
                        theme === 'neon' ? 'border-purple-500/20' :
                        theme === 'forest' ? 'border-emerald-500/20' :
                        theme === 'cosmic' ? 'border-indigo-500/20' :
                        theme === 'minimalist' ? 'border-gray-200' :
                        theme === 'tech' ? 'border-cyan-500/20' :
                        theme === 'pastel' ? 'border-pink-200/50' :
                        theme === 'monochrome' ? 'border-zinc-700/50' :
                        'border-gray-700/50'
                      } text-center`}>
                        <div className={`text-2xl font-bold ${
                          theme === 'luxury' ? 'text-yellow-500' : 
                          theme === 'elegant' ? 'text-amber-400' :
                          theme === 'neon' ? 'text-purple-400' :
                          theme === 'forest' ? 'text-emerald-400' :
                          theme === 'cosmic' ? 'text-indigo-400' :
                          theme === 'minimalist' ? 'text-gray-800' :
                          theme === 'tech' ? 'text-cyan-400' :
                          theme === 'pastel' ? 'text-pink-500' :
                          theme === 'monochrome' ? 'text-zinc-300' :
                          'text-yellow-400'
                        }`}>67%</div>
                        <div className="text-gray-400 text-xs mt-1">Most Common</div>
                      </div>
                      
                      {/* 5-Star Reviews */}
                      <div className={`p-4 rounded-xl ${
                        theme === 'minimalist' ? 'bg-gray-100' :
                        theme === 'pastel' ? 'bg-pink-100/30' :
                        theme === 'luxury' ? 'bg-[#1A1A1A]/70' :
                        theme === 'neon' ? 'bg-[#0d0d0f]/80 shadow-[0_0_10px_1px_rgba(168,85,247,0.15)]' :
                        theme === 'custom' ? 'bg-[#1E1E20]/70' :
                        'bg-[#1E1E20]/70'
                      } border ${
                        theme === 'luxury' ? 'border-yellow-500/20' :
                        theme === 'elegant' ? 'border-amber-500/20' :
                        theme === 'neon' ? 'border-purple-500/20' :
                        theme === 'forest' ? 'border-emerald-500/20' :
                        theme === 'cosmic' ? 'border-indigo-500/20' :
                        theme === 'minimalist' ? 'border-gray-200' :
                        theme === 'tech' ? 'border-cyan-500/20' :
                        theme === 'pastel' ? 'border-pink-200/50' :
                        theme === 'monochrome' ? 'border-zinc-700/50' :
                        'border-gray-700/50'
                      } text-center`}>
                        <div className={`text-2xl font-bold ${
                          theme === 'luxury' ? 'text-yellow-500' : 
                          theme === 'elegant' ? 'text-amber-400' :
                          theme === 'neon' ? 'text-purple-400' :
                          theme === 'forest' ? 'text-emerald-400' :
                          theme === 'cosmic' ? 'text-indigo-400' :
                          theme === 'minimalist' ? 'text-gray-800' :
                          theme === 'tech' ? 'text-cyan-400' :
                          theme === 'pastel' ? 'text-pink-500' :
                          theme === 'monochrome' ? 'text-zinc-300' :
                          'text-yellow-400'
                        }`}>2</div>
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
      
      {/* Preview & Save Buttons */}
      <div className="flex justify-between mt-8">
        <button 
          className={`px-6 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 text-white font-medium rounded-lg hover:from-emerald-700 hover:to-teal-700 transition-all shadow-md hover:shadow-lg transform hover:-translate-y-0.5 flex items-center gap-2`}
          onClick={goToFullPreview}
        >
          <Eye size={18} />
          Full Page Preview
        </button>
        <button 
          className={`px-6 py-2.5 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-medium rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all shadow-md hover:shadow-lg transform hover:-translate-y-0.5`}
          onClick={saveAllAppearanceSettings}
        >
          Save Settings
        </button>
      </div>
    </div>
  );
}

export default AppearanceRating;
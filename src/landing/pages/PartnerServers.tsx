import React, { useState, useEffect, useCallback } from 'react';
import { ExternalLink, Users, Search, Star, AlertTriangle, ChevronLeft, ChevronRight, Settings, ShoppingBag } from 'lucide-react';
import LandingLayout from '../../landing/components/LandingLayout';
import LoadingSpinner from '../../landing/components/LoadingSpinner';
import debounce from 'lodash/debounce';

// Types for server data
interface ServerData {
  _id: string;
  server_id: number;
  server_name: string;
  member_count: number;
  invite_link: string;
  icon_url?: string;
  banner_url?: string;
  server_type?: string;
  partner?: boolean;
  server_shop?: boolean;
  service?: boolean;
}

// Stats interface
interface NetworkStats {
  totalServers: number;
  totalMembers: number;
  partners: {
    count: number;
    members: number;
  };
  services: {
    count: number;
    members: number;
  };
  shops: {
    count: number;
    members: number;
  };
}

// Clean hero section with enhanced gradient and larger text
const HeroSection = () => (
  <div className="relative overflow-hidden mb-6 rounded-2xl">
    <div className="absolute inset-0 bg-gradient-to-r from-purple-900/90 via-indigo-900/90 to-blue-900/90 z-10"></div>
    <div className="absolute inset-0 bg-[url('/assets/hero-pattern.svg')] opacity-15 z-0"></div>
    
    <div className="relative z-20 py-12 px-4 text-center">
      <h1 className="text-3xl md:text-5xl font-bold mb-4 text-white">
        <span className="inline-block bg-clip-text text-transparent bg-gradient-to-r from-white via-blue-200 to-purple-200 drop-shadow-[0_2px_2px_rgba(0,0,0,0.5)]">
          CRN Community Servers
        </span>
      </h1>
      
      <p className="text-base md:text-lg text-white max-w-2xl mx-auto drop-shadow-[0_1px_1px_rgba(0,0,0,0.8)]">
        Explore trusted Discord servers, connect with trading communities, and trade with CRN confidence.
      </p>
    </div>
  </div>
);

// Simple server type badge component with more rounded corners
const ServerBadge: React.FC<{ type: string }> = ({ type }) => {
  if (type === 'partner') {
    return (
      <div className="flex items-center px-2 py-0.5 rounded-full bg-amber-950 border border-amber-800/50 text-amber-200 text-xs font-medium">
        <Star size={10} className="mr-1" />
        <span>Partner</span>
      </div>
    );
  } else if (type === 'service') {
    return (
      <div className="flex items-center px-2 py-0.5 rounded-full bg-blue-950 border border-blue-800/50 text-blue-200 text-xs font-medium">
        <Settings size={10} className="mr-1" />
        <span>Service</span>
      </div>
    );
  } else {
    return (
      <div className="flex items-center px-2 py-0.5 rounded-full bg-emerald-950 border border-emerald-800/50 text-emerald-200 text-xs font-medium">
        <ShoppingBag size={10} className="mr-1" />
        <span>Shop</span>
      </div>
    );
  }
};

// High-performance server card component with more rounded corners and animation
const ServerCard: React.FC<{ server: ServerData }> = ({ server }) => {
  // Determine server badge type
  const getBadgeType = () => {
    if (server.partner) return 'partner';
    if (server.service) return 'service';
    return 'shop';
  };

  return (
    <div className="bg-[#1E1E30] rounded-2xl overflow-hidden shadow-lg border border-[#2A2A40] hover:shadow-xl hover:border-purple-500/40 hover:-translate-y-1 transition-all duration-300">
      {/* Banner with static gradient overlay */}
      <div className="h-24 w-full relative overflow-hidden">
        {server.banner_url ? (
          <>
            <img 
              src={server.banner_url} 
              alt={`${server.server_name} banner`} 
              className="w-full h-full object-cover"
              loading="lazy"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
            <div className="absolute inset-0 bg-gradient-to-t from-[#1E1E30] to-transparent opacity-70"></div>
          </>
        ) : (
          <div className="w-full h-full bg-gradient-to-r from-purple-900/20 to-indigo-900/20 flex items-center justify-center">
            <div className="text-2xl font-bold text-white/10">{server.server_name.charAt(0)}</div>
          </div>
        )}
        
        {/* Server status badge */}
        <div className="absolute top-2 right-2">
          <div className="flex items-center px-1.5 py-0.5 rounded-full bg-green-900/60 backdrop-blur-sm border border-green-800/30">
            <div className="w-1.5 h-1.5 rounded-full bg-green-400 mr-1"></div>
            <span className="text-xs font-medium text-green-300">Online</span>
          </div>
        </div>

        {/* Server type badge in top left */}
        <div className="absolute top-2 left-2">
          <ServerBadge type={getBadgeType()} />
        </div>
      </div>
      
      {/* Content with server icon and info */}
      <div className="p-4 relative">
        {/* Server Icon */}
        <div className="absolute -top-6 left-4 w-12 h-12 rounded-full border-2 border-[#1E1E30] overflow-hidden bg-[#2A2A40] flex items-center justify-center shadow-md">
          {server.icon_url ? (
            <img 
              src={server.icon_url} 
              alt={`${server.server_name} icon`}
              className="w-full h-full object-cover"
              loading="lazy"
              onError={(e) => {
                (e.target as HTMLImageElement).src = '/assets/default-server-icon.png';
              }}
            />
          ) : (
            <div className="text-lg font-bold text-purple-400">
              {server.server_name.charAt(0)}
            </div>
          )}
        </div>
        
        <div className="pt-6 pl-2">
          {/* Server name */}
          <div className="mb-1">
            <h3 className="text-base font-semibold text-white leading-tight line-clamp-1">{server.server_name}</h3>
          </div>
          
          {/* Member count */}
          <div className="flex items-center text-[#A1A1AA] mb-3">
            <Users size={12} className="mr-1" />
            <span className="text-xs font-medium">{server.member_count.toLocaleString()} members</span>
          </div>
          
          {/* Join Button with static gradient and hover effect */}
          <a 
            href={server.invite_link} 
            target="_blank" 
            rel="noopener noreferrer"
            className="flex items-center justify-center w-full py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-full transition-all duration-300 font-medium text-sm transform hover:scale-105 mb-2"
          >
            <span>Join Server</span>
            <div className="ml-2">
              <ExternalLink size={14} />
            </div>
          </a>
          
          {/* Report Server Button */}
          <a 
            href="https://discord.com/invite/clyne" 
            target="_blank" 
            rel="noopener noreferrer"
            className="flex items-center justify-center w-full py-1.5 bg-transparent border border-red-500/30 hover:bg-red-500/10 text-red-400 rounded-full transition-all duration-300 text-xs font-medium"
            title="Report this server to our support team"
          >
            <AlertTriangle size={10} className="mr-1" />
            <span>Report Server</span>
          </a>
        </div>
      </div>
    </div>
  );
};

// Clean pagination component with more rounded buttons
const Pagination: React.FC<{ 
  currentPage: number; 
  totalPages: number; 
  onPageChange: (page: number) => void 
}> = ({ currentPage, totalPages, onPageChange }) => {
  // Generate page numbers
  const getPageNumbers = () => {
    const pages = [];
    const maxPagesToShow = window.innerWidth < 640 ? 3 : 5;
    
    if (totalPages <= maxPagesToShow) {
      // Show all pages if total pages is less than max pages to show
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      // Always include first page
      pages.push(1);
      
      // Calculate start and end of visible pages
      let start = Math.max(2, currentPage - 1);
      let end = Math.min(totalPages - 1, currentPage + 1);
      
      // Adjust start and end to always show 3 pages
      if (currentPage <= 2) {
        end = 3;
      } else if (currentPage >= totalPages - 1) {
        start = totalPages - 2;
      }
      
      // Add ellipsis after first page if needed
      if (start > 2) {
        pages.push('ellipsis-start');
      }
      
      // Add visible pages
      for (let i = start; i <= end; i++) {
        pages.push(i);
      }
      
      // Add ellipsis before last page if needed
      if (end < totalPages - 1) {
        pages.push('ellipsis-end');
      }
      
      // Always include last page
      if (totalPages > 1) {
        pages.push(totalPages);
      }
    }
    
    return pages;
  };

  return (
    <div className="flex items-center justify-center mt-8 space-x-1.5">
      {/* Previous Page Button */}
      <button 
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        className={`w-9 h-9 rounded-full flex items-center justify-center ${
          currentPage === 1 
            ? 'bg-[#1E1E30] text-gray-500 cursor-not-allowed' 
            : 'bg-[#1E1E30] text-white hover:bg-purple-600 hover:text-white transition-colors'
        }`}
        aria-label="Previous page"
      >
        <ChevronLeft size={16} />
      </button>
      
      {/* Page Numbers */}
      {getPageNumbers().map((page, index) => (
        page === 'ellipsis-start' || page === 'ellipsis-end' ? (
          <span 
            key={`ellipsis-${index}`}
            className="w-9 h-9 flex items-center justify-center text-gray-400"
          >
            ...
          </span>
        ) : (
          <button
            key={`page-${page}`}
            onClick={() => onPageChange(page as number)}
            className={`w-9 h-9 rounded-full flex items-center justify-center transition-colors ${
              currentPage === page
                ? 'bg-purple-600 text-white' 
                : 'bg-[#1E1E30] text-white hover:bg-[#2A2A40]'
            }`}
            aria-label={`Page ${page}`}
            aria-current={currentPage === page ? 'page' : undefined}
          >
            <span className="text-sm">{page}</span>
          </button>
        )
      ))}
      
      {/* Next Page Button */}
      <button 
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        className={`w-9 h-9 rounded-full flex items-center justify-center ${
          currentPage === totalPages 
            ? 'bg-[#1E1E30] text-gray-500 cursor-not-allowed' 
            : 'bg-[#1E1E30] text-white hover:bg-purple-600 hover:text-white transition-colors'
        }`}
        aria-label="Next page"
      >
        <ChevronRight size={16} />
      </button>
    </div>
  );
};

// Clean category filter button with more rounded design and enhanced animations
const FilterButton: React.FC<{
  filter: string;
  activeFilter: string;
  onClick: () => void;
}> = ({ filter, activeFilter, onClick }) => {
  // Get styles based on filter and active state
  const getFilterStyles = () => {
    const isActive = activeFilter === filter;
    
    if (filter === 'partner') {
      return isActive 
        ? "bg-amber-900/40 border-amber-700/50 text-amber-100 shadow-lg shadow-amber-900/20" 
        : "bg-[#1E1E30] border-[#2A2A40]/50 text-gray-300 hover:border-amber-700/30 hover:bg-amber-900/10";
    } else if (filter === 'service') {
      return isActive 
        ? "bg-blue-900/40 border-blue-700/50 text-blue-100 shadow-lg shadow-blue-900/20" 
        : "bg-[#1E1E30] border-[#2A2A40]/50 text-gray-300 hover:border-blue-700/30 hover:bg-blue-900/10";
    } else if (filter === 'shop') {
      return isActive 
        ? "bg-emerald-900/40 border-emerald-700/50 text-emerald-100 shadow-lg shadow-emerald-900/20" 
        : "bg-[#1E1E30] border-[#2A2A40]/50 text-gray-300 hover:border-emerald-700/30 hover:bg-emerald-900/10";
    }
    
    return "";
  };

  // Get icon based on filter type
  const getIcon = () => {
    if (filter === 'partner') return <Star size={16} />;
    if (filter === 'service') return <Settings size={16} />;
    return <ShoppingBag size={16} />;
  };
  
  return (
    <button
      onClick={onClick}
      className={`rounded-2xl p-3 text-center transition-all duration-300 border transform ${activeFilter === filter ? 'scale-[1.02]' : ''} ${getFilterStyles()}`}
    >
      <div className="flex flex-col items-center space-y-2">
        {getIcon()}
        <span className="font-medium text-sm">
          {filter === 'partner' ? 'Partners' : 
           filter === 'service' ? 'Services' : 'Shops'}
        </span>
        {activeFilter === filter && (
          <div className="h-1 w-8 bg-white rounded-full animate-pulse"></div>
        )}
      </div>
    </button>
  );
};

// Category header with more curved design
const CategoryHeader: React.FC<{
  type: string;
  count: number;
}> = ({ type, count }) => {
  let icon = <Star className="mr-2" size={18} />;
  let title = "Partner Servers";
  let bgColor = "bg-amber-900/20";
  let borderColor = "border-amber-800/30";
  
  if (type === 'service') {
    icon = <Settings className="mr-2" size={18} />;
    title = "Service Servers";
    bgColor = "bg-blue-900/20";
    borderColor = "border-blue-800/30";
  } else if (type === 'shop') {
    icon = <ShoppingBag className="mr-2" size={18} />;
    title = "Shop Servers";
    bgColor = "bg-emerald-900/20";
    borderColor = "border-emerald-800/30";
  }

  return (
    <div className={`mb-4 p-3 rounded-xl ${bgColor} border ${borderColor} flex items-center`}>
      <div className="text-white">
        {icon}
      </div>
      <h2 className="font-bold text-white">{title}</h2>
      <div className="ml-2 px-2 py-0.5 bg-[#2A2A40] rounded-full text-xs text-gray-300">
        {count}
      </div>
    </div>
  );
};

// Network Statistics component with more rounded design and animated transitions
const NetworkStatsDisplay: React.FC<{
  stats: NetworkStats;
  activeFilter: string;
}> = ({ stats, activeFilter }) => {
  return (
    <div className="bg-[#1A1A2E]/80 rounded-2xl border border-[#2A2A40]/70 p-4 shadow-lg">
      <h3 className="text-center text-lg font-bold text-white mb-3">CRN Community Statistics</h3>
      
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
        {/* Partners Stats */}
        <div className={`bg-amber-900/20 border ${activeFilter === 'partner' ? 'border-amber-600 ring-2 ring-amber-600/30' : 'border-amber-800/30'} rounded-xl p-3 transition-all duration-300 transform ${activeFilter === 'partner' ? 'scale-[1.02]' : ''}`}>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center">
              <Star className={`mr-2 ${activeFilter === 'partner' ? 'text-amber-400' : 'text-amber-300'}`} size={16} />
              <h4 className="font-semibold text-amber-200">Partner Servers</h4>
            </div>
            <div className="text-amber-200 font-bold">{stats.partners.count}</div>
          </div>
          <div className="flex items-center text-sm text-amber-100/80">
            <Users size={14} className="mr-1" />
            <span>{stats.partners.members.toLocaleString()} members</span>
          </div>
        </div>
        
        {/* Services Stats */}
        <div className={`bg-blue-900/20 border ${activeFilter === 'service' ? 'border-blue-600 ring-2 ring-blue-600/30' : 'border-blue-800/30'} rounded-xl p-3 transition-all duration-300 transform ${activeFilter === 'service' ? 'scale-[1.02]' : ''}`}>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center">
              <Settings className={`mr-2 ${activeFilter === 'service' ? 'text-blue-400' : 'text-blue-300'}`} size={16} />
              <h4 className="font-semibold text-blue-200">Service Servers</h4>
            </div>
            <div className="text-blue-200 font-bold">{stats.services.count}</div>
          </div>
          <div className="flex items-center text-sm text-blue-100/80">
            <Users size={14} className="mr-1" />
            <span>{stats.services.members.toLocaleString()} members</span>
          </div>
        </div>
        
        {/* Shops Stats */}
        <div className={`bg-emerald-900/20 border ${activeFilter === 'shop' ? 'border-emerald-600 ring-2 ring-emerald-600/30' : 'border-emerald-800/30'} rounded-xl p-3 transition-all duration-300 transform ${activeFilter === 'shop' ? 'scale-[1.02]' : ''}`}>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center">
              <ShoppingBag className={`mr-2 ${activeFilter === 'shop' ? 'text-emerald-400' : 'text-emerald-300'}`} size={16} />
              <h4 className="font-semibold text-emerald-200">Shop Servers</h4>
            </div>
            <div className="text-emerald-200 font-bold">{stats.shops.count}</div>
          </div>
          <div className="flex items-center text-sm text-emerald-100/80">
            <Users size={14} className="mr-1" />
            <span>{stats.shops.members.toLocaleString()} members</span>
          </div>
        </div>
      </div>
      
      {/* Network Totals */}
      <div className="bg-purple-900/20 border border-purple-800/30 rounded-xl p-3">
        <div className="flex items-center justify-between mb-1">
          <h4 className="font-semibold text-purple-200">Total CRN Servers</h4>
          <div className="text-purple-200 font-bold">{stats.totalServers}</div>
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center text-sm text-purple-100/80">
            <Users size={14} className="mr-1" />
            <span>Total Community Members</span>
          </div>
          <div className="font-bold text-lg text-purple-100">{stats.totalMembers.toLocaleString()}</div>
        </div>
      </div>
    </div>
  );
};

// Main component
const PartnerServers: React.FC = () => {
  const [allServers, setAllServers] = useState<ServerData[]>([]);
  const [displayedServers, setDisplayedServers] = useState<ServerData[]>([]);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [searchError, setSearchError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState('partner');
  const [transitionKey, setTransitionKey] = useState(0);
  
  // Network stats
  const [networkStats, setNetworkStats] = useState<NetworkStats>({
    totalServers: 0,
    totalMembers: 0,
    partners: { count: 0, members: 0 },
    services: { count: 0, members: 0 },
    shops: { count: 0, members: 0 }
  });
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalServers, setTotalServers] = useState(0);
  const serversPerPage = 50;
  
  // Get current page of servers
  const getCurrentPageServers = (servers: ServerData[], page: number) => {
    const startIndex = (page - 1) * serversPerPage;
    return servers.slice(startIndex, startIndex + serversPerPage);
  };
  
  // Apply filters to servers
  const applyFilters = useCallback((servers: ServerData[], filter: string, term: string) => {
    let filtered = [...servers];
    
    // Apply category filter
    if (filter === 'partner') {
      filtered = filtered.filter(server => server.partner);
    } else if (filter === 'service') {
      filtered = filtered.filter(server => server.service);
    } else if (filter === 'shop') {
      filtered = filtered.filter(server => server.server_shop);
    }
    
    // Apply search filter if there's a search term
    if (term.trim()) {
      const searchLower = term.toLowerCase();
      filtered = filtered.filter(server => 
        server.server_name.toLowerCase().includes(searchLower)
      );
    }
    
    return filtered;
  }, []);

  // Calculate network stats
  const calculateNetworkStats = useCallback((servers: ServerData[]) => {
    const stats: NetworkStats = {
      totalServers: servers.length,
      totalMembers: 0,
      partners: { count: 0, members: 0 },
      services: { count: 0, members: 0 },
      shops: { count: 0, members: 0 }
    };
    
    servers.forEach(server => {
      // Add to total members
      stats.totalMembers += server.member_count;
      
      // Add to category counts
      if (server.partner) {
        stats.partners.count++;
        stats.partners.members += server.member_count;
      } else if (server.service) {
        stats.services.count++;
        stats.services.members += server.member_count;
      } else if (server.server_shop) {
        stats.shops.count++;
        stats.shops.members += server.member_count;
      }
    });
    
    return stats;
  }, []);

  // Debounced search function
  const debouncedSearch = useCallback(
    debounce(async (term: string) => {
      if (!term.trim()) {
        const filteredServers = applyFilters(allServers, activeFilter, '');
        setTotalServers(filteredServers.length);
        setTotalPages(Math.ceil(filteredServers.length / serversPerPage));
        setDisplayedServers(getCurrentPageServers(filteredServers, currentPage));
        setSearching(false);
        return;
      }

      try {
        // Only update the searching state, don't reload statistics
        setSearching(true);
        setSearchError(null);
        
        // Validate search term
        if (/[<>{}[\]\\\/]/.test(term)) {
          setSearchError("Special characters are not allowed");
          setSearching(false);
          return;
        }
        
        // Filter locally without fetching data again
        let localFiltered = [...allServers];
        
        if (activeFilter === 'partner') {
          localFiltered = localFiltered.filter(server => server.partner);
        } else if (activeFilter === 'service') {
          localFiltered = localFiltered.filter(server => server.service);
        } else if (activeFilter === 'shop') {
          localFiltered = localFiltered.filter(server => server.server_shop);
        }
        
        const searchLower = term.toLowerCase();
        localFiltered = localFiltered.filter(server => 
          server.server_name.toLowerCase().includes(searchLower)
        );
        
        // Update only what needs to be updated
        setDisplayedServers(getCurrentPageServers(localFiltered, 1));
        setTotalServers(localFiltered.length);
        setTotalPages(Math.ceil(localFiltered.length / serversPerPage));
      } catch (error) {
        console.error('Search error:', error);
        setSearchError('An error occurred during search');
      } finally {
        setSearching(false);
      }
    }, 300),
    [allServers, activeFilter, applyFilters, currentPage, serversPerPage]
  );

  // Handle search
  useEffect(() => {
    debouncedSearch(searchTerm);
    return () => debouncedSearch.cancel();
  }, [searchTerm, debouncedSearch]);

  // Enhance handleFilterChange to update transition key
  const handleFilterChange = (filter: string) => {
    if (activeFilter !== filter) {
      // Don't set searching state to avoid full component reload
      setTransitionKey(prevKey => prevKey + 1);
      
      // Just update the filter directly without timeout or search state change
      setActiveFilter(filter);
      setCurrentPage(1);
      
      // Apply the filter immediately without full reload
      const filteredServers = applyFilters(allServers, filter, searchTerm);
      setTotalServers(filteredServers.length);
      setTotalPages(Math.ceil(filteredServers.length / serversPerPage));
      setDisplayedServers(getCurrentPageServers(filteredServers, 1));
    }
  };

  // Handle filter change effect
  useEffect(() => {
    if (searchTerm.trim()) {
      debouncedSearch(searchTerm);
    } else {
      const filteredServers = applyFilters(allServers, activeFilter, '');
      setTotalServers(filteredServers.length);
      setTotalPages(Math.ceil(filteredServers.length / serversPerPage));
      setDisplayedServers(getCurrentPageServers(filteredServers, 1));
    }
  }, [activeFilter, allServers, applyFilters, debouncedSearch, searchTerm, serversPerPage]);

  // Handle page change with animation but without full reloading
  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages && page !== currentPage) {
      // Only animate the server content, not the statistics
      setCurrentPage(page);
      
      // Update displayed servers based on new page without full reload
      const filteredServers = applyFilters(allServers, activeFilter, searchTerm);
      setDisplayedServers(getCurrentPageServers(filteredServers, page));
      
      // Smooth scroll to top
      scrollToTop();
    }
  };

  // Simple scroll to top without animation
  const scrollToTop = () => {
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  };

  // Initial data fetch
  useEffect(() => {
    const fetchServers = async () => {
      // Only set loading on initial fetch, not when navigating between pages/filters
      if (allServers.length === 0) {
        setLoading(true);
      }
      
      try {
        const response = await fetch(`/api/partner-servers/?page=${currentPage}&limit=${serversPerPage}`);
        if (!response.ok) throw new Error('Failed to fetch servers');
        
        const data = await response.json();
        if (data.success) {
          const servers = data.servers || [];
          setAllServers(servers);
          
          // Calculate network stats only when servers change
          if (servers.length > 0) {
            setNetworkStats(calculateNetworkStats(servers));
          }
          
          // Filter servers based on activeFilter
          const filteredServers = applyFilters(servers, activeFilter, searchTerm);
          setTotalServers(filteredServers.length);
          setTotalPages(Math.ceil(filteredServers.length / serversPerPage));
          setDisplayedServers(getCurrentPageServers(filteredServers, currentPage));
        } else {
          console.error('Error fetching servers:', data.error);
          setError(data.error || 'Failed to fetch servers');
        }
      } catch (error) {
        console.error('Error:', error);
        setError('Failed to load servers. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    // Only fetch servers on initial load or if allServers is empty
    if (allServers.length === 0) {
      fetchServers();
    } else {
      // If we already have servers, just filter and display them
      const filteredServers = applyFilters(allServers, activeFilter, searchTerm);
      setTotalServers(filteredServers.length);
      setTotalPages(Math.ceil(filteredServers.length / serversPerPage));
      setDisplayedServers(getCurrentPageServers(filteredServers, currentPage));
    }
  }, [currentPage, serversPerPage, activeFilter, searchTerm, applyFilters, calculateNetworkStats, allServers.length]);

  return (
    <LandingLayout>
      <div className="max-w-6xl mx-auto px-3 sm:px-4 py-6">
        {/* Hero section */}
        <HeroSection />
        
        {/* Network Stats - moved outside the conditional to prevent reloading */}
        <div className="mb-6 transform hover:scale-[1.01] transition-transform duration-300">
          <NetworkStatsDisplay stats={networkStats} activeFilter={activeFilter} />
        </div>
        
        {/* Filter and Search */}
        <div className="bg-[#151525] rounded-2xl border border-[#2A2A40]/70 p-4 mb-6 shadow-lg">
          <div className="flex flex-col space-y-4">
            {/* Category Title */}
            <div>
              <h2 className="text-xl font-bold text-white mb-1">Server Categories</h2>
              <p className="text-sm text-gray-300">Find trading servers based on their type and functionality</p>
            </div>
            
            {/* Filter Tabs */}
            <div className="grid grid-cols-3 gap-3">
              {['partner', 'service', 'shop'].map((filter) => (
                <FilterButton
                  key={filter}
                  filter={filter}
                  activeFilter={activeFilter}
                  onClick={() => handleFilterChange(filter)}
                />
              ))}
            </div>
            
            {/* Search Box */}
            <div className="relative w-full mt-2">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search size={16} className={searching ? 'text-purple-400' : 'text-gray-400'} />
              </div>
              <input
                type="text"
                placeholder={`Search ${activeFilter} servers by name...`}
                value={searchTerm}
                onChange={(e) => {
                  const value = e.target.value;
                  if (value.length <= 50) {
                    setSearchTerm(value);
                    setSearchError(null);
                    setCurrentPage(1);
                    setTransitionKey(prevKey => prevKey + 1);
                  }
                }}
                className={`w-full pl-10 pr-4 py-3 bg-[#1A1A2E] border ${
                  searchError ? 'border-red-500' : 'border-[#2A2A40]/50'
                } text-white rounded-xl focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all text-sm`}
                maxLength={50}
                aria-label={`Search for ${activeFilter} servers`}
              />
              {searchError && (
                <div className="mt-1 flex items-center text-red-400 text-xs">
                  <AlertTriangle size={12} className="mr-1" />
                  {searchError}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Content Transition Container */}
        <div key={transitionKey} className="transition-all duration-300 transform ease-out">
          {/* Category Header */}
          {!loading && !searching && displayedServers.length > 0 && (
            <CategoryHeader type={activeFilter} count={totalServers} />
          )}

          {/* Results info */}
          <div className="mb-4 flex items-center justify-between bg-[#1A1A2E] rounded-xl py-2.5 px-4 border border-[#2A2A40]/70">
            <p className="text-[#A1A1AA] text-xs sm:text-sm truncate flex-1">
              {loading ? 'Loading servers...' : 
               searching ? 'Searching...' :
               displayedServers.length === 0 ? 'No servers found' : 
               `Showing ${displayedServers.length} of ${totalServers} ${activeFilter} servers • Page ${currentPage} of ${totalPages}`}
            </p>
            
            {/* Stats */}
            {!loading && !searching && displayedServers.length > 0 && (
              <div className="text-[#A1A1AA] text-xs flex items-center ml-2">
                <div className="w-1.5 h-1.5 rounded-full bg-green-500 mr-1"></div>
                <span>{totalServers} online</span>
              </div>
            )}
          </div>
          
          {/* Error display with more curved design */}
          {error && (
            <div className="bg-red-900/20 border border-red-700 rounded-xl p-4 mb-6">
              <p className="text-red-400 flex items-center text-sm">
                <AlertTriangle size={16} className="mr-2 flex-shrink-0" />
                {error}
              </p>
            </div>
          )}

          {/* Loading state with more elegant styling */}
          {loading ? (
            <div className="flex flex-col items-center justify-center py-16">
              <LoadingSpinner size="large" />
              <p className="mt-4 text-purple-300 text-sm">Loading servers...</p>
            </div>
          ) : searching ? (
            <div className="flex flex-col items-center justify-center py-16">
              <LoadingSpinner size="medium" />
              <p className="mt-4 text-purple-300 text-sm">Searching for "{searchTerm}"...</p>
            </div>
          ) : displayedServers.length === 0 ? (
            <div className="bg-[#1A1A2E] text-center py-12 px-4 rounded-xl border border-[#2A2A40]/60">
              <div>
                <h3 className="text-lg sm:text-xl text-white font-medium mb-2">No servers found</h3>
                <p className="text-sm text-[#A1A1AA]">
                  {searchTerm ? 'Try a different search term' : `No ${activeFilter} servers are available at the moment`}
                </p>
                {searchTerm && (
                  <button
                    onClick={() => setSearchTerm('')}
                    className="mt-4 bg-purple-600 hover:bg-purple-500 text-white py-2 px-5 rounded-full transition-colors"
                  >
                    Clear Search
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="min-h-[300px]">
              {/* Server grid - optimized for performance with smooth transitions */}
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 transition-all duration-500 transform">
                {displayedServers.map((server) => (
                  <div 
                    key={server._id} 
                    className="transition-all duration-500"
                  >
                    <ServerCard server={server} />
                  </div>
                ))}
              </div>
              
              {/* Pagination */}
              {totalPages > 1 && (
                <Pagination 
                  currentPage={currentPage} 
                  totalPages={totalPages} 
                  onPageChange={handlePageChange}
                />
              )}
            </div>
          )}
        </div>
      </div>
    </LandingLayout>
  );
};

export default PartnerServers;
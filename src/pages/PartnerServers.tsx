import React, { useState, useEffect, useRef } from 'react';
import { Users, ExternalLink, Search, Star, Award, LayoutGrid, List } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

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
}

// View modes
type ViewMode = 'grid' | 'list';

// Server card component with hover animations
const ServerCard: React.FC<{ 
  server: ServerData; 
  index: number; 
  viewMode: ViewMode; 
}> = ({ server, index, viewMode }) => {

  // Grid view card
  if (viewMode === 'grid') {
    return (
      <motion.div 
        className="bg-gradient-to-br from-[#1E1E30] to-[#25253A] rounded-xl overflow-hidden shadow-lg border border-[#2A2A40] group hover:shadow-xl hover:border-purple-500/50 transition-all duration-300"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: index * 0.05 }}
        layout
      >
        {/* Banner with gradient overlay */}
        <div className="h-32 w-full relative overflow-hidden">
          {server.banner_url ? (
            <>
              <img 
                src={server.banner_url} 
                alt={`${server.server_name} banner`} 
                className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none';
                }}
              />
              <div className="absolute inset-0 bg-gradient-to-t from-[#1E1E30] to-transparent opacity-70"></div>
            </>
          ) : (
            <div className="w-full h-full bg-gradient-to-r from-purple-900/20 to-indigo-900/20 flex items-center justify-center">
              <div className="text-3xl font-bold text-white/10">{server.server_name.charAt(0)}</div>
            </div>
          )}
          
          {/* Server status badge */}
          <div className="absolute top-3 right-3">
            <div className="flex items-center px-2 py-1 rounded-full bg-green-500/20 backdrop-blur-sm border border-green-500/30">
              <div className="w-2 h-2 rounded-full bg-green-400 mr-1.5"></div>
              <span className="text-xs font-medium text-green-300">Online</span>
            </div>
          </div>
        </div>
        
        {/* Content with server icon and info */}
        <div className="p-5 relative">
          {/* Server Icon - positioned over banner */}
          <div className="absolute -top-8 left-5 w-16 h-16 rounded-full border-4 border-[#1E1E30] overflow-hidden bg-[#2A2A40] flex items-center justify-center shadow-lg">
            {server.icon_url ? (
              <img 
                src={server.icon_url} 
                alt={`${server.server_name} icon`}
                className="w-full h-full object-cover"
                onError={(e) => {
                  (e.target as HTMLImageElement).src = '/assets/default-server-icon.png';
                }}
              />
            ) : (
              <div className="text-xl font-bold text-purple-400">
                {server.server_name.charAt(0)}
              </div>
            )}
          </div>
          
          <div className="pt-8">
            {/* Server name with animated sparkle */}
            <div className="flex items-start justify-between mb-1">
              <h3 className="text-xl font-semibold text-white leading-tight">{server.server_name}</h3>
              {server.member_count > 1000 && (
                <div className="text-yellow-400">
                  <Star size={16} className="fill-yellow-400" />
                </div>
              )}
            </div>
            
            {/* Member count */}
            <div className="flex items-center text-[#A1A1AA] mb-5">
              <Users size={14} className="mr-1.5" />
              <span className="text-sm font-medium">{server.member_count.toLocaleString()} members</span>
            </div>
            
            {/* Join Button with hover effect */}
            <a 
              href={server.invite_link} 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center justify-center w-full py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-lg transition duration-300 font-medium shadow-lg shadow-purple-900/20 group-hover:shadow-purple-900/40"
            >
              <span>Join Server</span>
              <div className="ml-2">
                <ExternalLink size={16} />
              </div>
            </a>
          </div>
        </div>
      </motion.div>
    );
  }
  
  // List view card
  return (
    <motion.div 
      className="bg-gradient-to-r from-[#1E1E30] to-[#25253A] rounded-xl overflow-hidden shadow-lg border border-[#2A2A40] hover:shadow-xl hover:border-purple-500/50 transition-all duration-300"
      initial={{ opacity: 0, x: -30 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: index * 0.05 }}
      layout
    >
      <div className="p-4 flex items-center">
        {/* Server Icon */}
        <div className="w-16 h-16 rounded-full overflow-hidden bg-[#2A2A40] flex items-center justify-center mr-4 border-2 border-[#2A2A40] flex-shrink-0">
          {server.icon_url ? (
            <img 
              src={server.icon_url} 
              alt={`${server.server_name} icon`}
              className="w-full h-full object-cover"
              onError={(e) => {
                (e.target as HTMLImageElement).src = '/assets/default-server-icon.png';
              }}
            />
          ) : (
            <div className="text-2xl font-bold text-purple-400">
              {server.server_name.charAt(0)}
            </div>
          )}
        </div>
        
        {/* Server details */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center mb-1">
            <h3 className="text-lg font-semibold text-white truncate mr-2">{server.server_name}</h3>
            {server.member_count > 1000 && <Star size={14} className="text-yellow-400 fill-yellow-400" />}
          </div>
          <div className="flex items-center text-[#A1A1AA]">
            <Users size={14} className="mr-1.5" />
            <span className="text-sm">{server.member_count.toLocaleString()} members</span>
            <div className="mx-2 w-1 h-1 rounded-full bg-[#4A4A60]"></div>
            <div className="flex items-center">
              <div className="w-2 h-2 rounded-full bg-green-400 mr-1.5"></div>
              <span className="text-sm">Online</span>
            </div>
          </div>
        </div>
        
        {/* Join button */}
        <a 
          href={server.invite_link} 
          target="_blank" 
          rel="noopener noreferrer"
          className="px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-lg transition duration-300 font-medium shadow-lg shadow-purple-900/20 flex items-center flex-shrink-0"
        >
          <span>Join</span>
          <ExternalLink size={14} className="ml-1.5" />
        </a>
      </div>
    </motion.div>
  );
};

// Loading skeleton component for server cards
const ServerCardSkeleton: React.FC<{ viewMode: ViewMode }> = ({ viewMode }) => {
  if (viewMode === 'grid') {
    return (
      <div className="bg-[#1E1E30] rounded-xl overflow-hidden shadow-lg animate-pulse border border-[#2A2A40]">
        {/* Banner skeleton */}
        <div className="h-32 w-full bg-[#2A2A40]"></div>
        
        {/* Content skeleton */}
        <div className="p-5 relative">
          {/* Icon skeleton */}
          <div className="absolute -top-8 left-5 w-16 h-16 rounded-full border-4 border-[#1E1E30] bg-[#2A2A40]"></div>
          
          <div className="pt-8">
            <div className="h-5 bg-[#2A2A40] rounded w-3/4 mb-2"></div>
            <div className="h-4 bg-[#2A2A40] rounded w-1/3 mb-5"></div>
            <div className="h-10 bg-[#2A2A40] rounded w-full"></div>
          </div>
        </div>
      </div>
    );
  }
  
  return (
    <div className="bg-[#1E1E30] rounded-xl overflow-hidden shadow-lg animate-pulse border border-[#2A2A40] p-4 flex items-center">
      {/* Icon skeleton */}
      <div className="w-16 h-16 rounded-full bg-[#2A2A40] mr-4 flex-shrink-0"></div>
      
      {/* Content skeleton */}
      <div className="flex-1">
        <div className="h-5 bg-[#2A2A40] rounded w-3/4 mb-2"></div>
        <div className="h-4 bg-[#2A2A40] rounded w-1/2"></div>
      </div>
      
      {/* Button skeleton */}
      <div className="w-20 h-10 bg-[#2A2A40] rounded-lg flex-shrink-0"></div>
    </div>
  );
};

// Main component
const PartnerServers: React.FC = () => {
  const [servers, setServers] = useState<ServerData[]>([]);
  const [displayedServers, setDisplayedServers] = useState<ServerData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  
  // Handle search
  useEffect(() => {
    if (!servers || servers.length === 0) return;
    
    let filtered = [...servers];
    
    // Filter by search term
    if (searchTerm) {
      filtered = filtered.filter(server => 
        server.server_name.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }
    
    // Sort by popularity by default
    filtered = [...filtered].sort((a, b) => b.member_count - a.member_count);
    
    setDisplayedServers(filtered);
  }, [servers, searchTerm]);

  // Fetch servers
  useEffect(() => {
    const fetchServers = async () => {
      setLoading(true);
      try {
        const response = await fetch('/api/partner-servers/');
        if (!response.ok) throw new Error('Failed to fetch servers');
        
        const data = await response.json();
        if (data.success) {
          setServers(data.servers || []);
          setDisplayedServers(data.servers || []);
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

    fetchServers();
  }, []);

  // Generate skeleton loaders
  const generateSkeletons = (count: number) => {
    return Array(count).fill(0).map((_, index) => (
      <ServerCardSkeleton key={index} viewMode={viewMode} />
    ));
  };

  return (
    <div className="space-y-6">
      {/* Header with stats */}
      <motion.div 
        className="bg-gradient-to-r from-[#1E1E30] to-[#25253A] rounded-xl p-6 border border-[#2A2A40] shadow-lg"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="mb-4 flex flex-col md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white mb-2 flex items-center">
              <Award size={22} className="text-purple-400 mr-2" />
              Servers Using CRN
            </h1>
            <p className="text-[#A1A1AA]">
              Step into the world of trading with top Discord servers
            </p>
          </div>
          
          {!loading && displayedServers.length > 0 && (
            <div className="mt-4 md:mt-0 bg-[#2A2A40]/50 px-4 py-2 rounded-lg">
              <div className="flex items-center text-white">
                <div className="text-2xl font-bold">{displayedServers.length}</div>
                <div className="text-sm text-[#A1A1AA] ml-2">Servers<br/>Online</div>
              </div>
            </div>
          )}
        </div>
      </motion.div>
      
      {/* Search and controls */}
      <div className="flex flex-col md:flex-row md:items-center gap-4">
        {/* Search box */}
        <div className="relative flex-1">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search size={18} className="text-gray-400" />
          </div>
          <input
            type="text"
            placeholder="Search servers..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-[#1E1E30] border border-[#2A2A40] text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
          />
        </div>
        
        {/* View toggle */}
        <div className="flex items-center bg-[#1E1E30] border border-[#2A2A40] rounded-lg overflow-hidden">
          <button
            onClick={() => setViewMode('grid')}
            className={`p-2.5 flex items-center justify-center ${
              viewMode === 'grid' ? 'bg-purple-900/30 text-purple-400' : 'text-white hover:bg-[#2A2A40]/30'
            }`}
          >
            <LayoutGrid size={18} />
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`p-2.5 flex items-center justify-center ${
              viewMode === 'list' ? 'bg-purple-900/30 text-purple-400' : 'text-white hover:bg-[#2A2A40]/30'
            }`}
          >
            <List size={18} />
          </button>
        </div>
      </div>
      
      {/* Results count */}
      {!loading && !error && (
        <div className="flex justify-between items-center">
          <p className="text-[#A1A1AA]">
            {displayedServers.length === 0
              ? 'No servers found'
              : `Showing ${displayedServers.length} ${displayedServers.length === 1 ? 'server' : 'servers'}`}
          </p>
          
          {searchTerm && (
            <button
              onClick={() => setSearchTerm('')}
              className="text-purple-400 text-sm hover:text-purple-300 transition-colors"
            >
              Clear filters
            </button>
          )}
        </div>
      )}

      {error && (
        <motion.div 
          className="bg-red-900/20 border border-red-700 rounded-lg p-4"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <p className="text-red-400">{error}</p>
        </motion.div>
      )}

      {/* Server grid/list with animated transitions */}
      <AnimatePresence mode="wait">
        <motion.div
          key={viewMode}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
        >
          {loading ? (
            <div className={viewMode === 'grid' 
              ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" 
              : "space-y-4"
            }>
              {generateSkeletons(6)}
            </div>
          ) : displayedServers.length === 0 ? (
            <motion.div 
              className="bg-[#1E1E30] text-center py-16 px-4 rounded-xl border border-[#2A2A40]"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5 }}
            >
              <h3 className="text-xl text-white font-medium mb-2">No servers found</h3>
              <p className="text-[#A1A1AA]">
                {searchTerm ? 'Try a different search term or clear filters' : 'No partner servers are available at the moment'}
              </p>
            </motion.div>
          ) : (
            <motion.div 
              className={viewMode === 'grid' 
                ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" 
                : "space-y-4"
              }
              layout
            >
              {displayedServers.map((server, index) => (
                <ServerCard 
                  key={server._id} 
                  server={server} 
                  index={index} 
                  viewMode={viewMode}
                />
              ))}
            </motion.div>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
};

export default PartnerServers; 
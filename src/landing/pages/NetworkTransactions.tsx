import React, { useState, useEffect, useRef, useMemo } from "react";
import { ArrowUpRight, ArrowDownRight, Search, Filter, RefreshCw } from "lucide-react";
import TransactionsList from "../components/network/TransactionsList";
// @ts-ignore
import TransactionStats from "../components/network/TransactionStats";
// @ts-ignore
import LiveIndicator from "../components/network/LiveIndicator";
import { io, Socket } from "socket.io-client";
import LandingLayout from "../components/LandingLayout";

export interface Transaction {
  tx_id: string;
  amount: number;
  timestamp: string;
  sender: {
    public_address: string;
    username: string;
  };
  receiver: {
    public_address: string;
    username: string;
  };
  status: string;
}

const NetworkTransactions: React.FC = () => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [filteredTransactions, setFilteredTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalTransactions, setTotalTransactions] = useState(0);
  const [newTransactionReceived, setNewTransactionReceived] = useState(false);
  const socketRef = useRef<Socket | null>(null);
  const isInitialLoadRef = useRef<boolean>(true);

  // Fetch initial transactions
  useEffect(() => {
    fetchTransactions();
  }, [page]);

  // Setup socket connection for real-time updates
  useEffect(() => {
    // Create socket connection with reconnection options for better reliability
    socketRef.current = io('/network-transactions', {
      transports: ['websocket'],
      upgrade: false,
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000
    });

    // Listen for new transactions
    socketRef.current.on('new_transactions', (data: { transactions: any[] }) => {
      setTransactions(prevTx => {
        // Transform the new transactions to ensure consistency
        const newFormattedTransactions = data.transactions.map((tx: any) => ({
          tx_id: tx.tx_id || 'Unknown',
          amount: typeof tx.amount === 'number' ? tx.amount : parseFloat(tx.amount) || 0,
          timestamp: tx.timestamp || new Date().toISOString(),
          sender: {
            public_address: tx.sender?.public_address || 'Unknown',
            username: tx.sender?.username || 'Unknown'
          },
          receiver: {
            public_address: tx.receiver?.public_address || 'Unknown',
            username: tx.receiver?.username || 'Unknown'
          },
          status: tx.status || 'completed'
        }));
        
        // Add new transactions at the top and filter out duplicates
        const newTx = [...newFormattedTransactions, ...prevTx];
        const uniqueTx = newTx.filter((tx, index, self) => 
          index === self.findIndex(t => t.tx_id === tx.tx_id)
        );
        
        // Count how many actually new transactions were added (weren't duplicates)
        const uniqueNewCount = newFormattedTransactions.filter(
          newTx => !prevTx.some(existingTx => existingTx.tx_id === newTx.tx_id)
        ).length;
        
        // Update total count with only the unique new transactions
        setTotalTransactions(prev => prev + uniqueNewCount);
        
        return uniqueTx.slice(0, 100); // Keep only the 100 latest
      });
      
      // Also update filtered transactions to match
      setFilteredTransactions(prevFiltered => {
        const newFormattedTransactions = data.transactions.map((tx: any) => ({
          tx_id: tx.tx_id || 'Unknown',
          amount: typeof tx.amount === 'number' ? tx.amount : parseFloat(tx.amount) || 0,
          timestamp: tx.timestamp || new Date().toISOString(),
          sender: {
            public_address: tx.sender?.public_address || 'Unknown',
            username: tx.sender?.username || 'Unknown'
          },
          receiver: {
            public_address: tx.receiver?.public_address || 'Unknown',
            username: tx.receiver?.username || 'Unknown'
          },
          status: tx.status || 'completed'
        }));
        
        // Add to filtered transactions and remove duplicates
        const newFiltered = [...newFormattedTransactions, ...prevFiltered];
        const uniqueFiltered = newFiltered.filter((tx, index, self) => 
          index === self.findIndex(t => t.tx_id === tx.tx_id)
        );
        
        return uniqueFiltered.slice(0, 100);
      });
      
      setNewTransactionReceived(true);
      
      // Reset the visual indicator after 2 seconds
      setTimeout(() => {
        setNewTransactionReceived(false);
      }, 2000);
    });

    // Handle reconnection events
    socketRef.current.on('reconnect', () => {
      console.log('Reconnected to transaction socket');
      // Refetch transactions to ensure no missed transactions during disconnection
      if (!isInitialLoadRef.current) {
        fetchTransactions();
      }
    });

    // Cleanup on unmount
    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, []);

  const fetchTransactions = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/network-transactions?page=${page}&limit=100`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch transactions');
      }
      
      const data = await response.json();
      
      // Transform the transactions if needed
      const formattedTransactions: Transaction[] = data.transactions.map((tx: any) => ({
        tx_id: tx.tx_id || 'Unknown',
        amount: typeof tx.amount === 'number' ? tx.amount : parseFloat(tx.amount) || 0,
        timestamp: tx.timestamp || new Date().toISOString(),
        sender: {
          public_address: tx.sender?.public_address || 'Unknown',
          username: tx.sender?.username || 'Unknown'
        },
        receiver: {
          public_address: tx.receiver?.public_address || 'Unknown',
          username: tx.receiver?.username || 'Unknown'
        },
        status: tx.status || 'completed'
      }));
      
      setTransactions(formattedTransactions);
      setFilteredTransactions(formattedTransactions);
      setTotalPages(data.meta.pages || 1);
      setTotalTransactions(data.meta.total || 0);
      setError(null);
      isInitialLoadRef.current = false;
    } catch (err) {
      setError('Error loading transactions. Please try again later.');
      console.error('Error fetching transactions:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleNextPage = () => {
    if (page < totalPages) {
      setPage(page + 1);
      window.scrollTo({ top: 0, behavior: 'smooth' }); // Smooth scroll to top
    }
  };

  const handlePrevPage = () => {
    if (page > 1) {
      setPage(page - 1);
      window.scrollTo({ top: 0, behavior: 'smooth' }); // Smooth scroll to top
    }
  };

  // Generate page numbers for pagination
  const getPageNumbers = () => {
    const pageNumbers = [];
    const maxVisiblePages = 5;
    
    if (totalPages <= maxVisiblePages) {
      // Show all pages if total is less than max visible
      for (let i = 1; i <= totalPages; i++) {
        pageNumbers.push(i);
      }
    } else {
      // Always show first page
      pageNumbers.push(1);
      
      // Calculate start and end of middle pages
      let startPage = Math.max(2, page - 1);
      let endPage = Math.min(totalPages - 1, page + 1);
      
      // If we're at the start, show more pages after
      if (page <= 2) {
        endPage = Math.min(totalPages - 1, 4);
      }
      
      // If we're at the end, show more pages before
      if (page >= totalPages - 1) {
        startPage = Math.max(2, totalPages - 3);
      }
      
      // Add ellipsis if needed before middle pages
      if (startPage > 2) {
        pageNumbers.push('...');
      }
      
      // Add middle pages
      for (let i = startPage; i <= endPage; i++) {
        pageNumbers.push(i);
      }
      
      // Add ellipsis if needed after middle pages
      if (endPage < totalPages - 1) {
        pageNumbers.push('...');
      }
      
      // Always show last page
      pageNumbers.push(totalPages);
    }
    
    return pageNumbers;
  };

  // Create loading skeletons for transactions
  const renderSkeletons = () => {
    return Array(5).fill(0).map((_, index) => (
      <div key={`skeleton-${index}`} className="grid grid-cols-12 px-4 py-4 animate-pulse">
        <div className="col-span-3 lg:col-span-2 h-6 bg-gray-700 rounded"></div>
        <div className="col-span-5 lg:col-span-5 h-6 bg-gray-700 rounded ml-2"></div>
        <div className="col-span-4 lg:col-span-5 h-6 bg-gray-700 rounded ml-2"></div>
      </div>
    ));
  };

  return (
    <LandingLayout>
      <div className="min-h-screen bg-[#1A1A1A] text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="text-center mb-12">
            <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-[#6C5DD3] to-[#8875FF] bg-clip-text text-transparent mb-4">
              Cryptonel Network Transactions
            </h1>
            <p className="text-xl text-[#A1A1AA] max-w-3xl mx-auto">
              Real-time view of all transactions happening on the Cryptonel network
            </p>
            
            <div className="mt-6 flex items-center justify-center">
              <LiveIndicator active={newTransactionReceived} />
            </div>
          </div>
          
          {/* Stats Section */}
          <TransactionStats totalTransactions={totalTransactions} />
          
          {/* Transactions Table */}
          {loading && transactions.length === 0 ? (
            <div className="bg-[#262626] rounded-xl overflow-hidden shadow-lg">
              <div className="grid grid-cols-12 bg-[#2A2A2D] px-4 py-3 text-sm text-[#A1A1AA] font-medium">
                <div className="col-span-3 lg:col-span-2">Amount</div>
                <div className="col-span-5 lg:col-span-5">Transaction ID</div>
                <div className="col-span-4 lg:col-span-5 text-right">Time</div>
              </div>
              <div className="divide-y divide-[#3A3A3D]">
                {renderSkeletons()}
              </div>
            </div>
          ) : error ? (
            <div className="text-center py-10 bg-[#262626] rounded-lg">
              <p className="text-red-400">{error}</p>
              <button 
                onClick={() => fetchTransactions()} 
                className="mt-4 px-4 py-2 bg-[#6C5DD3] rounded-lg hover:bg-[#5B4DC3] transition-colors"
              >
                Try Again
              </button>
            </div>
          ) : (
            <>
              <TransactionsList 
                transactions={filteredTransactions} 
                newTransaction={newTransactionReceived} 
              />
              
              {/* Enhanced Pagination */}
              {filteredTransactions.length > 0 && (
                <div className="mt-8 flex flex-wrap justify-center items-center gap-2">
                  <button
                    onClick={handlePrevPage}
                    disabled={page === 1}
                    className={`px-3 py-1.5 rounded-md text-sm ${
                      page === 1
                        ? 'bg-[#3A3A3D]/50 text-[#717179] cursor-not-allowed'
                        : 'bg-[#3A3A3D] hover:bg-[#4A4A50] text-white'
                    }`}
                  >
                    Previous
                  </button>
                  
                  {getPageNumbers().map((pageNum, idx) => (
                    <button
                      key={`page-${idx}`}
                      onClick={() => typeof pageNum === 'number' ? setPage(pageNum) : null}
                      className={`px-3 py-1.5 rounded-md text-sm ${
                        pageNum === page
                          ? 'bg-[#6C5DD3] text-white'
                          : pageNum === '...'
                          ? 'bg-transparent text-[#A1A1AA] cursor-default'
                          : 'bg-[#3A3A3D] hover:bg-[#4A4A50] text-white'
                      }`}
                      disabled={pageNum === '...'}
                    >
                      {pageNum}
                    </button>
                  ))}
                  
                  <button
                    onClick={handleNextPage}
                    disabled={page === totalPages}
                    className={`px-3 py-1.5 rounded-md text-sm ${
                      page === totalPages
                        ? 'bg-[#3A3A3D]/50 text-[#717179] cursor-not-allowed'
                        : 'bg-[#3A3A3D] hover:bg-[#4A4A50] text-white'
                    }`}
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </LandingLayout>
  );
};

export default NetworkTransactions; 
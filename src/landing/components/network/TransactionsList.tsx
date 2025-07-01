import React, { useRef, useEffect, useState } from "react";
import { Transaction } from "../../pages/NetworkTransactions";
import { Copy, Check, ExternalLink } from "lucide-react";

interface TransactionsListProps {
  transactions: Transaction[];
  newTransaction: boolean;
  searchQuery?: string;
}

const TransactionsList: React.FC<TransactionsListProps> = ({ 
  transactions,
  newTransaction,
  searchQuery = ""
}) => {
  const tableRef = useRef<HTMLDivElement>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Add animation effect when new transactions arrive
  useEffect(() => {
    if (newTransaction && tableRef.current) {
      tableRef.current.classList.add('animate-pulse');
      
      setTimeout(() => {
        if (tableRef.current) {
          tableRef.current.classList.remove('animate-pulse');
        }
      }, 1000);
    }
  }, [newTransaction]);

  // Format amount to ensure it shows with proper decimal places
  const formatAmount = (amount: number): string => {
    // Ensure at least 2 decimal places but show up to 6 if needed
    const formattedAmount = amount.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 6,
    });
    return `${formattedAmount} CRN`;
  };

  // Copy transaction ID to clipboard
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(text);
    
    // Reset the copied state after 2 seconds
    setTimeout(() => {
      setCopiedId(null);
    }, 2000);
  };

  // Highlight text matching search query
  const highlightText = (text: string, highlight: string) => {
    if (!highlight.trim()) return text;
    
    const regex = new RegExp(`(${highlight.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    const parts = text.split(regex);
    
    return (
      <>
        {parts.map((part, i) => 
          regex.test(part) ? 
            <span key={i} className="bg-[#6C5DD3]/40">{part}</span> : 
            <span key={i}>{part}</span>
        )}
      </>
    );
  };

  // Format transaction ID for display
  const formatTransactionId = (txId: string) => {
    if (!txId || txId === 'Unknown') {
      return 'Unknown';
    }
    
    if (window.innerWidth < 768) {
      // On mobile, truncate to first 8 and last 8 chars
      return `${txId.slice(0, 8)}...${txId.slice(-8)}`;
    }
    return txId;
  };

  // Get status indicator color based on transaction status
  const getStatusIndicator = (status: string) => {
    if (!status) return 'bg-blue-500';
    
    switch(status.toLowerCase()) {
      case 'completed':
        return 'bg-green-500';
      case 'pending':
        return 'bg-yellow-500';
      case 'failed':
        return 'bg-red-500';
      default:
        return 'bg-blue-500';
    }
  };

  // Format the status text for display
  const formatStatus = (status: string): string => {
    if (!status) return 'Completed';
    
    // Convert to lowercase and capitalize first letter
    return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
  };

  return (
    <div 
      ref={tableRef}
      className="bg-[#262626] rounded-xl overflow-hidden shadow-lg transition-colors"
    >
      {/* Table Header */}
      <div className="grid grid-cols-12 bg-[#2A2A2D] px-4 py-3 text-sm text-[#A1A1AA] font-medium">
        <div className="col-span-3 lg:col-span-2">Amount</div>
        <div className="col-span-6 lg:col-span-4">Transaction ID</div>
        <div className="hidden lg:block lg:col-span-3">Status</div>
        <div className="col-span-3 lg:col-span-3 text-right">Time</div>
      </div>

      {/* Transaction Items */}
      <div className="divide-y divide-[#3A3A3D]">
        {transactions.length === 0 ? (
          <div className="text-center py-12 text-[#A1A1AA]">
            No transactions found
          </div>
        ) : (
          transactions.map((tx, index) => (
            <div 
              key={tx.tx_id}
              className={`grid grid-cols-12 px-4 py-4 text-sm hover:bg-[#2A2A2D] transition-colors
                ${index === 0 && newTransaction ? 'bg-[#6C5DD3]/10' : ''}`}
            >              
              {/* Amount */}
              <div className="col-span-3 lg:col-span-2 font-mono font-semibold text-white">
                {formatAmount(tx.amount)}
              </div>
              
              {/* Transaction ID */}
              <div className="col-span-6 lg:col-span-4 flex items-center">
                <div className="overflow-hidden text-ellipsis">
                  <span className="hidden md:inline text-[#A1A1AA]" title={tx.tx_id}>
                    {searchQuery ? highlightText(tx.tx_id, searchQuery) : tx.tx_id}
                  </span>
                  <span className="md:hidden text-[#A1A1AA]" title={tx.tx_id}>
                    {formatTransactionId(tx.tx_id)}
                  </span>
                </div>
                <button
                  onClick={() => copyToClipboard(tx.tx_id)}
                  className="ml-2 text-[#A1A1AA] hover:text-white p-1 rounded-md hover:bg-[#3A3A3D] transition-colors"
                  title="Copy to clipboard"
                >
                  {copiedId === tx.tx_id ? (
                    <Check className="h-4 w-4 text-green-400" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </button>
              </div>
              
              {/* Status */}
              <div className="hidden lg:flex lg:col-span-3 items-center">
                <span className={`inline-block w-2 h-2 rounded-full mr-2 ${getStatusIndicator(tx.status)}`}></span>
                <span className="text-[#A1A1AA] capitalize">
                  {formatStatus(tx.status)}
                </span>
              </div>
              
              {/* Date & Time */}
              <div className="col-span-3 lg:col-span-3 text-right text-[#A1A1AA]">
                {new Date(tx.timestamp).toLocaleString([], {
                  year: '2-digit',
                  month: '2-digit',
                  day: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default TransactionsList; 
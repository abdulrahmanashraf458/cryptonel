import React from 'react';
import { AlertTriangle } from 'lucide-react';

const GenericErrorPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-900 flex flex-col items-center justify-center p-4">
      <div className="bg-gray-800 rounded-lg shadow-xl p-6 max-w-lg w-full border border-gray-700">
        <div className="flex items-center justify-center mb-6">
          <div className="bg-red-900/30 p-4 rounded-full">
            <AlertTriangle size={48} className="text-red-500" />
          </div>
        </div>
        
        <h1 className="text-2xl font-bold text-white text-center mb-4">
          Something went wrong
        </h1>
        
        <p className="text-gray-300 text-center">
          We're sorry, but there was a problem loading the application. Our team has been notified and is working to fix the issue.
        </p>
      </div>
    </div>
  );
};

export default GenericErrorPage; 
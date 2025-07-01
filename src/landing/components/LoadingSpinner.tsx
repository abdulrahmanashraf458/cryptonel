import React from 'react';

const LoadingSpinner: React.FC<{ size?: 'small' | 'medium' | 'large' }> = ({ size = 'medium' }) => {
  const sizeClasses = {
    small: 'w-4 h-4 border-2',
    medium: 'w-8 h-8 border-3',
    large: 'w-12 h-12 border-4'
  };
  
  return (
    <div className={`${sizeClasses[size]} border-[#8875FF] border-t-transparent rounded-full animate-spin`}></div>
  );
};

export default LoadingSpinner; 
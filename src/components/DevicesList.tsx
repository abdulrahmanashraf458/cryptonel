import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  Shield,
  Smartphone,
  Laptop,
  Monitor,
  Tablet,
  X,
  ChevronRight,
  Clock,
  MapPin,
  Check,
  Trash2,
  AlertCircle
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

type Device = {
  device_id: string;
  device_type: string;
  os: string;
  browser: string;
  ip_address: string;
  country: string;
  city: string;
  location: string;
  last_active: string;
  is_current: boolean;
  session_id: string;
};

type RateLimitStatus = {
  is_limited: boolean;
  retry_after: number;
  retry_after_minutes: number;
  deletions_remaining: number;
};

type DevicesListProps = {
  isOpen: boolean;
  onClose: () => void;
};

const DevicesList: React.FC<DevicesListProps> = ({ isOpen, onClose }) => {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [removingDevice, setRemovingDevice] = useState<string | null>(null);
  
  // Rate limit related states
  const [rateLimitStatus, setRateLimitStatus] = useState<RateLimitStatus>({
    is_limited: false,
    retry_after: 0,
    retry_after_minutes: 0,
    deletions_remaining: 5
  });
  const [remainingTime, setRemainingTime] = useState<number>(0);

  useEffect(() => {
    if (isOpen) {
      fetchDevices();
      fetchRateLimitStatus();
    }
  }, [isOpen]);

  // Rate limit countdown timer
  useEffect(() => {
    let timer: NodeJS.Timeout | null = null;
    
    if (rateLimitStatus.is_limited && remainingTime > 0) {
      timer = setInterval(() => {
        setRemainingTime(prev => {
          const newTime = prev - 1;
          if (newTime <= 0) {
            // When countdown reaches zero, refresh rate limit status
            fetchRateLimitStatus();
            return 0;
          }
          return newTime;
        });
      }, 1000);
    }
    
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [rateLimitStatus.is_limited, remainingTime]);

  const fetchRateLimitStatus = async () => {
    try {
      const response = await fetch('/api/devices/rate-limit-status');
      
      if (!response.ok) {
        throw new Error('Failed to fetch rate limit status');
      }
      
      const data = await response.json();
      setRateLimitStatus(data);
      
      // Set countdown timer if limited
      if (data.is_limited) {
        setRemainingTime(data.retry_after);
      } else {
        setRemainingTime(0);
      }
    } catch (err) {
      console.error('Error fetching rate limit status:', err);
      // Don't set error state to avoid confusing the user with multiple errors
    }
  };

  const fetchDevices = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/devices');
      
      if (!response.ok) {
        throw new Error('Failed to fetch devices');
      }
      
      const data = await response.json();
      setDevices(data.devices || []);
      setError(null);
    } catch (err) {
      setError('Failed to load active devices');
      console.error('Error fetching devices:', err);
    } finally {
      setLoading(false);
    }
  };

  const removeDevice = async (deviceId: string) => {
    // Check rate limits first
    if (rateLimitStatus.is_limited) {
      setError(`Rate limit reached. Please try again in ${formatTimeRemaining(remainingTime)}`);
      return;
    }

    if (deviceId) {
      try {
        setRemovingDevice(deviceId);
        const response = await fetch(`/api/devices/${deviceId}`, {
          method: 'DELETE',
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          
          // Handle rate limit error
          if (response.status === 429) {
            await fetchRateLimitStatus(); // Refresh rate limit status
            throw new Error(errorData.error || 'Rate limit reached. Please try again later.');
          } else {
            throw new Error(errorData.error || 'Failed to remove device');
          }
        }
        
        // Update the devices list after successful removal
        setDevices(devices.filter(device => device.device_id !== deviceId));
        
        // Update rate limit status after successful removal
        await fetchRateLimitStatus();
      } catch (err: any) {
        setError(err.message || 'Failed to remove device');
      } finally {
        setRemovingDevice(null);
      }
    }
  };

  const formatTimeRemaining = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    
    if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`;
    }
    return `${remainingSeconds}s`;
  };

  const getDeviceIcon = (device: Device) => {
    const iconProps = { className: "w-6 h-6 text-indigo-400" };
    
    if (device.device_type.includes('iPhone')) {
      return <Smartphone {...iconProps} />;
    } else if (device.device_type.includes('iPad') || device.device_type.includes('Tablet')) {
      return <Tablet {...iconProps} />;
    } else if (device.device_type.includes('Android') && device.device_type.includes('Phone')) {
      return <Smartphone {...iconProps} />;
    } else if (device.device_type.includes('Windows') || device.device_type.includes('PC')) {
      return <Monitor {...iconProps} />;
    } else if (device.device_type.includes('Mac')) {
      return <Laptop {...iconProps} />;
    } else {
      return <Monitor {...iconProps} />;
    }
  };

  const formatLastActive = (lastActive: string) => {
    try {
      const date = new Date(lastActive);
      return formatDistanceToNow(date, { addSuffix: true });
    } catch (e) {
      return 'Unknown';
    }
  };

  // If the modal is not open, don't render anything
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-[#1e1e1e] rounded-xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[#333333]">
          <div className="flex items-center">
            <Smartphone className="w-6 h-6 text-indigo-500 mr-2" />
            <h2 className="text-lg font-medium text-white">Active Devices</h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {/* Rate limit warning */}
          {rateLimitStatus.is_limited && (
            <div className="bg-yellow-900/30 border border-yellow-600/30 text-yellow-300 p-4 rounded-lg mb-4">
              <div className="flex items-start">
                <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium">Device removal limit reached</p>
                  <p className="text-sm mt-1">
                    For security reasons, you can only remove up to 5 devices per minute. 
                    Please wait {formatTimeRemaining(remainingTime)} before removing more devices.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Rate limit counter when not limited but approaching limit */}
          {!rateLimitStatus.is_limited && rateLimitStatus.deletions_remaining < 5 && (
            <div className="bg-indigo-900/20 border border-indigo-500/30 text-indigo-300 p-3 rounded-lg mb-4">
              <div className="flex items-center">
                <AlertTriangle className="w-4 h-4 mr-2" />
                <p className="text-sm">
                  {rateLimitStatus.deletions_remaining} device {rateLimitStatus.deletions_remaining === 1 ? 'removal' : 'removals'} remaining before rate limit.
                </p>
              </div>
            </div>
          )}

          {error && (
            <div className="bg-red-900/30 text-red-300 p-4 rounded-lg mb-4">
              <div className="flex items-center">
                <AlertTriangle className="w-5 h-5 mr-2" />
                <p>{error}</p>
              </div>
            </div>
          )}
          
          {loading ? (
            <div className="flex justify-center items-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
            </div>
          ) : devices.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <p>No active devices found</p>
            </div>
          ) : (
            <div className="space-y-4">
              {devices.map((device) => (
                <div
                  key={device.device_id}
                  className={`${
                    device.is_current
                      ? 'bg-indigo-900/20 border border-indigo-500/30'
                      : 'bg-[#2b2b2b] border border-[#333333]'
                  } rounded-xl p-4 transition-all hover:border-indigo-500/50`}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex items-start">
                      {getDeviceIcon(device)}
                      <div className="ml-3">
                        <div className="flex items-center">
                          <h3 className="text-white font-medium">
                            {device.device_type} 
                          </h3>
                          {device.is_current && (
                            <span className="ml-2 px-2 py-0.5 bg-indigo-900/50 text-indigo-200 text-xs font-semibold rounded">
                              Current Device
                            </span>
                          )}
                        </div>
                        <p className="text-gray-400 text-sm">
                          {device.os} - {device.browser}
                        </p>
                      </div>
                    </div>
                    
                    {!device.is_current && (
                      <button
                        onClick={() => removeDevice(device.device_id)}
                        disabled={removingDevice === device.device_id || rateLimitStatus.is_limited}
                        className={`group p-2 rounded-full hover:bg-red-900/20 transition-colors ${
                          removingDevice === device.device_id || rateLimitStatus.is_limited
                            ? 'opacity-50 cursor-not-allowed'
                            : ''
                        }`}
                        title={rateLimitStatus.is_limited 
                          ? `Rate limit reached. Try again in ${formatTimeRemaining(remainingTime)}`
                          : "Remove this device"}
                      >
                        {removingDevice === device.device_id ? (
                          <div className="animate-spin h-5 w-5 border-2 border-red-500 rounded-full border-t-transparent"></div>
                        ) : (
                          <Trash2 className={`h-5 w-5 ${
                            rateLimitStatus.is_limited 
                              ? 'text-gray-600' 
                              : 'text-gray-400 group-hover:text-red-400'
                          } transition-colors`} />
                        )}
                      </button>
                    )}
                  </div>
                  
                  <div className="mt-4 grid grid-cols-2 gap-3">
                    <div className="flex items-center">
                      <MapPin className="w-4 h-4 text-gray-400 mr-2" />
                      <span className="text-sm text-gray-300">
                        {device.location || `${device.city || 'Unknown'}, ${device.country || 'Unknown'}`}
                      </span>
                    </div>
                    
                    <div className="flex items-center">
                      <Clock className="w-4 h-4 text-gray-400 mr-2" />
                      <span className="text-sm text-gray-300">
                        Last active: {formatLastActive(device.last_active)}
                      </span>
                    </div>
                    
                    <div className="flex items-center">
                      <Shield className="w-4 h-4 text-gray-400 mr-2" />
                      <span className="text-sm text-gray-300">
                        IP Address: {device.ip_address}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-[#333333] flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default DevicesList;
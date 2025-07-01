import React, { useState, useEffect, useRef } from 'react';
import {
  Plus,
  X,
  RefreshCw,
  Search,
  AlertCircle,
  CheckCircle,
  User,
  Send,
  Loader2
} from 'lucide-react';
import axios from 'axios';
import { toast } from 'react-hot-toast';
import { motion, AnimatePresence } from 'framer-motion';

// تعريف نوع للتاريخ من MongoDB
interface MongoDBDate {
  $date: string;
}

// تعديل واجهة TrustedContact لإضافة حقول can_delete و days_remaining
interface TrustedContact {
  id: string;
  user_id: string;
  username: string;
  public_address: string;
  private_address: string;
  avatar?: string;
  discord_id?: string;
  avatar_hash?: string;
  added_at?: string | MongoDBDate | Date;
  can_delete?: boolean;
  days_remaining?: number;
  added_at_formatted?: string;
}

interface UserBalanceInfo {
  balance: number;
  formattedBalance: string;
}

const QuickTransfer: React.FC = () => {
  const [trustedContacts, setTrustedContacts] = useState<TrustedContact[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showTransferModal, setShowTransferModal] = useState(false);
  const [privateAddress, setPrivateAddress] = useState('');
  const [userId, setUserId] = useState('');
  const [password, setPassword] = useState('');
  const [addressValidation, setAddressValidation] = useState<{
    isValid: boolean;
    message: string;
    username?: string;
    user_id?: string;
    loading: boolean;
  }>({ isValid: false, message: '', loading: false });
  const [selectedContact, setSelectedContact] = useState<TrustedContact | null>(null);
  const [transferAmount, setTransferAmount] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [balance, setBalance] = useState<UserBalanceInfo>({ 
    balance: 0, 
    formattedBalance: '0.00000000' 
  });
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [isSuccess, setIsSuccess] = useState(false);
  const [animate, setAnimate] = useState(false);
  const [validationAttempts, setValidationAttempts] = useState<number>(0);
  const [isRateLimited, setIsRateLimited] = useState<boolean>(false);
  const [rateLimitRemaining, setRateLimitRemaining] = useState<number>(5);
  const [rateLimitResetTime, setRateLimitResetTime] = useState<number>(0);
  const [showDeleteConfirmModal, setShowDeleteConfirmModal] = useState<boolean>(false);
  const [contactToDelete, setContactToDelete] = useState<TrustedContact | null>(null);
  const [userPrivateAddress, setUserPrivateAddress] = useState<string>('');
  const [currentUserId, setCurrentUserId] = useState<string>('');
  const [csrfToken, setCsrfToken] = useState<string>('');
  
  // ثابت للحد الأقصى لمحاولات التحقق
  const RATE_LIMIT_MAX_ATTEMPTS = 5;
  
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Add shimmer animation class
  const shimmer = "relative overflow-hidden before:absolute before:inset-0 before:-translate-x-full before:animate-shimmer before:bg-gradient-to-r before:from-transparent before:via-white/10 before:to-transparent";

  // Fetch CSRF token
  const fetchCsrfToken = async () => {
    try {
      console.log('Fetching CSRF token for QuickTransfer...');
      const response = await fetch('/api/csrf-token', {
        credentials: 'include'
      });
      
      console.log('CSRF token response status:', response.status);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('CSRF token response data:', data);
      
      if (data.success && data.csrf_token) {
        console.log('CSRF token received successfully for QuickTransfer');
        setCsrfToken(data.csrf_token);
      } else {
        console.error('CSRF token fetch failed:', data.error || 'Unknown error');
        toast.error('Security token initialization failed. Please refresh.');
      }
    } catch (error) {
      console.error('CSRF token fetch error:', error);
      toast.error('Security token initialization failed. Please refresh.');
    }
  };

  // Refresh CSRF token
  const refreshCsrfToken = async () => {
    try {
      console.log('Refreshing CSRF token for QuickTransfer...');
      const response = await fetch('/api/csrf-token', {
        credentials: 'include'
      });
      
      console.log('Refresh token response status:', response.status);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('Refresh token response data:', data);
      
      if (data.success && data.csrf_token) {
        console.log('CSRF token refreshed successfully for QuickTransfer');
        setCsrfToken(data.csrf_token);
        return true;
      } else {
        console.error('Failed to refresh CSRF token:', data.error || 'Unknown error');
        return false;
      }
    } catch (error) {
      console.error('Error refreshing CSRF token:', error);
      return false;
    }
  };

  // تكوين axios لإرسال رمز المصادقة مع كل طلب
  useEffect(() => {
    // إعداد اعتراض الطلبات لإضافة رمز المصادقة
    const requestInterceptor = axios.interceptors.request.use(config => {
      // الحصول على رمز المصادقة من localStorage
      const token = localStorage.getItem('access_token');
      console.log("Access token found:", token ? "YES" : "NO");
      
      if (token && config.headers) {
        // إضافة رمز المصادقة إلى رأس الطلب
        config.headers.Authorization = `Bearer ${token}`;
        console.log("Added Authorization header:", `Bearer ${token.substring(0, 15)}...`);
        
        // إضافة خيارات إضافية للتأكد من إرسال الكوكيز والجلسة
        config.withCredentials = true;
      }

      // Add CSRF token to POST, PUT, DELETE requests
      if (csrfToken && config.method && ['post', 'put', 'delete'].includes(config.method.toLowerCase())) {
        config.headers['X-CSRF-Token'] = csrfToken;
        console.log("Added CSRF token to request:", csrfToken.substring(0, 20) + '...');
      }
      
      return config;
    });
    
    // تنظيف عند إلغاء تحميل المكون
    return () => {
      axios.interceptors.request.eject(requestInterceptor);
    };
  }, [csrfToken]);

  // Fetch user's trusted contacts and balance on component mount
  useEffect(() => {
    const initializeData = async () => {
      setIsLoading(true);
      try {
        // Fetch CSRF token first
        await fetchCsrfToken();
        
        // Then fetch other data
        await Promise.all([
          fetchTrustedContacts(),
          fetchUserBalance(),
          fetchCurrentUserId()
        ]);
      } catch (error) {
        console.error('Error during initial data fetch:', error);
        toast.error('Failed to load data. Please try again.');
      } finally {
        setIsLoading(false);
        // Add animation after loading
        setTimeout(() => {
          setAnimate(true);
        }, 100);
      }
    };

    initializeData();
    
    // Cleanup any timers
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, []);

  // تحميل عنوان المستخدم الخاص عند تحميل المكون
  useEffect(() => {
    // محاكاة الحصول على عنوان المستخدم الخاص من الخادم
    const fetchUserPrivateAddress = async () => {
      try {
        // في الحالة الحقيقية، هذا سيكون طلب API
        // هنا نستخدم localStorage كبديل مؤقت
        const storedAddress = localStorage.getItem('user_private_address');
        if (storedAddress) {
          setUserPrivateAddress(storedAddress);
        } else {
          // إذا لم يكن موجودًا، يمكننا محاولة الحصول عليه من الخادم
          const response = await axios.get('/api/user/private-address');
          if (response.data && response.data.private_address) {
            setUserPrivateAddress(response.data.private_address);
            localStorage.setItem('user_private_address', response.data.private_address);
          }
        }
      } catch (error) {
        console.error('Error fetching user private address:', error);
      }
    };

    fetchUserPrivateAddress();
  }, []);

  // دالة لجلب معرف المستخدم الحالي
  const fetchCurrentUserId = async () => {
    try {
      const response = await axios.get('/api/user/current');
      if (response.data && response.data.user_id) {
        setCurrentUserId(response.data.user_id);
      }
    } catch (error) {
      console.error('Error fetching current user ID:', error);
    }
  };

  const fetchTrustedContacts = async () => {
    try {
      console.log("Fetching trusted contacts...");
      const response = await axios.get('/api/quicktransfer/contacts');
      console.log("Trusted contacts response:", response.data);
      
      if (response.data && response.data.contacts) {
        setTrustedContacts(response.data.contacts);
        console.log(`Found ${response.data.contacts.length} trusted contacts`);
        return response.data;
      } else {
        console.warn("No contacts found in response", response.data);
        setTrustedContacts([]);
        return response.data;
      }
    } catch (error: any) {
      console.error('Error fetching trusted contacts:', error);
      // Try to extract error message
      const errorMessage = error.response?.data?.error || 'Unknown error occurred';
      console.error('Error details:', errorMessage);
      // Check authentication status
      console.log('Token status:', localStorage.getItem('access_token') ? 'Token exists' : 'No token found');
      
      toast.error(`Failed to load contacts: ${errorMessage}`);
      throw error;
    }
  };

  const fetchUserBalance = async () => {
    try {
      // استخدام طريقة بديلة لجلب الرصيد
      const response = await axios.get('/api/overview');
      
      // تأكد من وجود البيانات
      if (response.data && response.data.balance) {
        setBalance({
          balance: parseFloat(response.data.balance),
          formattedBalance: response.data.balance
        });
        console.log("Balance loaded successfully:", response.data.balance);
      } else {
        console.error('Invalid balance data received:', response.data);
        toast.error('Could not load balance data. Please refresh.');
      }
      return response.data;
    } catch (error) {
      console.error('Error fetching balance:', error);
      toast.error('Failed to load balance. Please refresh.');
      throw error;
    }
  };

  const validateAddress = async (userId: string) => {
    if (!userId.trim()) {
      setAddressValidation({
        isValid: false,
        message: 'Please enter a Discord user ID',
        loading: false
      });
      return;
    }

    // التحقق مما إذا كان المستخدم يحاول إضافة معرفه الخاص
    if (userId.trim() === currentUserId) {
      setAddressValidation({
        isValid: false,
        message: 'You cannot add your own ID as a trusted contact',
        loading: false
      });
      return;
    }

    // التحقق من معدل الحد
    if (isRateLimited) {
      const timeRemaining = Math.ceil((rateLimitResetTime - Date.now()) / 1000);
      setAddressValidation({
        isValid: false,
        message: `Rate limit exceeded. Please try again in ${timeRemaining} seconds.`,
        loading: false
      });
      return;
    }

    setAddressValidation({
      isValid: false,
      message: '',
      loading: true
    });

    try {
      // تغيير الـ API لاستخدام معرف المستخدم بدلاً من العنوان الخاص
      const response = await axios.post('/api/quicktransfer/validate-id', {
        user_id: userId.trim()
      });

      if (response.data.valid) {
        setAddressValidation({
          isValid: true,
          message: `Found user: ${response.data.username}`,
          username: response.data.username,
          user_id: response.data.user_id,
          loading: false
        });
      } else {
        setAddressValidation({
          isValid: false,
          message: response.data.message || 'Invalid user ID',
          loading: false
        });

        // تحديث عدد المحاولات المتبقية
        if (response.data.rate_limit) {
          setRateLimitRemaining(response.data.rate_limit.remaining);
          setValidationAttempts(RATE_LIMIT_MAX_ATTEMPTS - response.data.rate_limit.remaining);
        }
      }
    } catch (error: any) {
      console.error('Error validating user ID:', error);
      
      // Handle CSRF-related errors
      if (error.response && error.response.status === 403) {
        if (error.response.data.error && error.response.data.error.includes('CSRF')) {
          console.log('CSRF token error detected, attempting to refresh...');
          
          // Clear the invalid token
          setCsrfToken('');
          
          // Try to refresh the token automatically
          const tokenRefreshed = await refreshCsrfToken();
          if (tokenRefreshed) {
            // Retry the request with the new token
            try {
              const retryResponse = await axios.post('/api/quicktransfer/validate-id', {
                user_id: userId.trim()
              });

              if (retryResponse.data.valid) {
                setAddressValidation({
                  isValid: true,
                  message: `Found user: ${retryResponse.data.username}`,
                  username: retryResponse.data.username,
                  user_id: retryResponse.data.user_id,
                  loading: false
                });
                return; // Exit early on success
              } else {
                setAddressValidation({
                  isValid: false,
                  message: retryResponse.data.message || 'Invalid user ID',
                  loading: false
                });
                return; // Exit early on validation failure
              }
            } catch (retryError: any) {
              console.error('Error on retry after CSRF refresh:', retryError);
              setAddressValidation({
                isValid: false,
                message: 'Security validation failed. Please refresh the page and try again.',
                loading: false
              });
              return;
            }
          } else {
            setAddressValidation({
              isValid: false,
              message: 'Security validation failed. Please refresh the page and try again.',
              loading: false
            });
            return;
          }
        }
      }
      
      // التعامل مع أخطاء معدل الحد
      if (error.response && error.response.status === 429) {
        const resetTime = error.response.data.reset_time || (Date.now() + 60000);
        setIsRateLimited(true);
        setRateLimitResetTime(resetTime);
        setRateLimitRemaining(0);
        
        const timeRemaining = Math.ceil((resetTime - Date.now()) / 1000);
        setAddressValidation({
          isValid: false,
          message: `Rate limit exceeded. Please try again in ${timeRemaining} seconds.`,
          loading: false
        });
        
        // إعادة تعيين معدل الحد بعد انتهاء الوقت
        if (timerRef.current) {
          clearTimeout(timerRef.current);
        }
        timerRef.current = setTimeout(() => {
          setIsRateLimited(false);
          setRateLimitRemaining(RATE_LIMIT_MAX_ATTEMPTS);
        }, timeRemaining * 1000);
      } else {
        setAddressValidation({
          isValid: false,
          message: error.response?.data?.message || 'Error validating user ID',
          loading: false
        });
      }
    }
  };

  const addTrustedContact = async () => {
    if (!addressValidation.isValid || !addressValidation.username || !addressValidation.user_id) {
      return;
    }

    if (!password.trim()) {
      toast.error('Password is required to add a trusted contact');
      return;
    }

    setIsLoading(true);
    
    try {
      // Check if we already have 5 contacts
      if (trustedContacts.length >= 5) {
        toast.error('Maximum of 5 trusted contacts allowed. Remove one to add another.');
        setIsLoading(false);
        return;
      }

      const response = await axios.post('/api/quicktransfer/contacts', {
        contact_user_id: addressValidation.user_id,
        password: password
      });

      if (response.data.success) {
        toast.success('Contact added successfully!');
        // Refresh contacts
        await fetchTrustedContacts();
        // Close modal and reset state
        setShowAddModal(false);
        setUserId('');
        setPassword('');
        setAddressValidation({ isValid: false, message: '', loading: false });
      } else {
        toast.error(response.data.message || 'Failed to add contact');
      }
    } catch (error: any) {
      console.error('Error adding trusted contact:', error);
      
      // Handle CSRF-related errors
      if (error.response && error.response.status === 403) {
        if (error.response.data.error && error.response.data.error.includes('CSRF')) {
          console.log('CSRF token error detected in addTrustedContact, attempting to refresh...');
          
          // Clear the invalid token
          setCsrfToken('');
          
          // Try to refresh the token automatically
          const tokenRefreshed = await refreshCsrfToken();
          if (tokenRefreshed) {
            // Retry the request with the new token
            try {
              const retryResponse = await axios.post('/api/quicktransfer/contacts', {
                contact_user_id: addressValidation.user_id,
                password: password
              });

              if (retryResponse.data.success) {
                toast.success('Contact added successfully!');
                // Refresh contacts
                await fetchTrustedContacts();
                // Close modal and reset state
                setShowAddModal(false);
                setUserId('');
                setPassword('');
                setAddressValidation({ isValid: false, message: '', loading: false });
                return; // Exit early on success
              } else {
                toast.error(retryResponse.data.message || 'Failed to add contact');
                return; // Exit early on failure
              }
            } catch (retryError: any) {
              console.error('Error on retry after CSRF refresh:', retryError);
              toast.error('Security validation failed. Please refresh the page and try again.');
              return;
            }
          } else {
            toast.error('Security validation failed. Please refresh the page and try again.');
            return;
          }
        }
      }
      
      const errorMessage = error.response?.data?.error || 'Failed to add contact. Please try again.';
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const removeTrustedContact = async (contactId: string) => {
    if (!password.trim()) {
      toast.error('Password is required to remove a trusted contact');
      return;
    }

    setIsLoading(true);
    
    try {
      const response = await axios.delete(`/api/quicktransfer/contacts/${contactId}`, {
        params: { password: password }
      });

      if (response.data.success) {
        toast.success('Contact removed successfully!');
        // Update the contacts list by removing the deleted contact
        setTrustedContacts(prev => prev.filter(contact => contact.id !== contactId));
        // إغلاق نافذة التأكيد إذا كانت مفتوحة
        setShowDeleteConfirmModal(false);
        setContactToDelete(null);
        setPassword('');
      } else {
        toast.error(response.data.message || 'Failed to remove contact');
      }
    } catch (error: any) {
      console.error('Error removing trusted contact:', error);
      
      // Handle CSRF-related errors
      if (error.response && error.response.status === 403) {
        if (error.response.data.error && error.response.data.error.includes('CSRF')) {
          console.log('CSRF token error detected in removeTrustedContact, attempting to refresh...');
          
          // Clear the invalid token
          setCsrfToken('');
          
          // Try to refresh the token automatically
          const tokenRefreshed = await refreshCsrfToken();
          if (tokenRefreshed) {
            // Retry the request with the new token
            try {
              const retryResponse = await axios.delete(`/api/quicktransfer/contacts/${contactId}`, {
                params: { password: password }
              });

              if (retryResponse.data.success) {
                toast.success('Contact removed successfully!');
                // Update the contacts list by removing the deleted contact
                setTrustedContacts(prev => prev.filter(contact => contact.id !== contactId));
                // إغلاق نافذة التأكيد إذا كانت مفتوحة
                setShowDeleteConfirmModal(false);
                setContactToDelete(null);
                setPassword('');
                return; // Exit early on success
              } else {
                toast.error(retryResponse.data.message || 'Failed to remove contact');
                return; // Exit early on failure
              }
            } catch (retryError: any) {
              console.error('Error on retry after CSRF refresh:', retryError);
              toast.error('Security validation failed. Please refresh the page and try again.');
              return;
            }
          } else {
            toast.error('Security validation failed. Please refresh the page and try again.');
            return;
          }
        }
      }
      
      // عرض رسالة الخطأ من الخادم إذا كانت متوفرة
      const errorMessage = error.response?.data?.error || 'Failed to remove contact. Please try again.';
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteRequest = (contact: TrustedContact) => {
    // التحقق من إمكانية حذف جهة الاتصال
    if (contact.can_delete === false) {
      // حساب الأيام المتبقية
      const daysRemaining = contact.days_remaining || 14;
      toast.error(`You cannot remove this contact yet. Contacts can only be removed after 14 days (${daysRemaining} days remaining).`);
      return;
    }
    
    setContactToDelete(contact);
    setShowDeleteConfirmModal(true);
  };

  const handleContactClick = (contact: TrustedContact) => {
    setSelectedContact(contact);
    setTransferAmount('');
    setErrorMessage('');
    setShowTransferModal(true);
  };

  const getAvatarDisplay = (contact: TrustedContact) => {
    // إذا كان لدينا رابط الصورة المباشر من Discord
    if (contact.avatar) {
      return (
        <img
          src={contact.avatar}
          alt={contact.username}
          className="w-full h-full object-cover rounded-full"
          onError={(e) => {
            // Fallback to Discord default avatar if custom avatar fails to load
            const userId = parseInt(contact.user_id, 10);
            (e.target as HTMLImageElement).src = `https://cdn.discordapp.com/embed/avatars/${userId % 5}.png`;
          }}
        />
      );
    } else {
      // Default avatar with user initial
      const initial = contact.username ? contact.username.charAt(0).toUpperCase() : '?';
      return (
        <div className="w-full h-full bg-gradient-to-br from-blue-600 to-purple-700 flex items-center justify-center text-white text-lg font-bold rounded-full">
          {initial}
        </div>
      );
    }
  };

  const validateTransferAmount = (amount: string): { valid: boolean; message: string } => {
    if (!amount.trim()) {
      return { valid: false, message: 'Please enter an amount' };
    }

    const numericAmount = parseFloat(amount);
    
    if (isNaN(numericAmount)) {
      return { valid: false, message: 'Please enter a valid number' };
    }

    if (numericAmount <= 0) {
      return { valid: false, message: 'Amount must be greater than zero' };
    }

    if (numericAmount > balance.balance) {
      return { valid: false, message: 'Insufficient balance' };
    }

    // Check if it has more than 8 decimal places
    const decimalPlaces = amount.includes('.')
      ? amount.split('.')[1].length
      : 0;
      
    if (decimalPlaces > 8) {
      return { valid: false, message: 'Maximum of 8 decimal places allowed' };
    }

    return { valid: true, message: '' };
  };

  const handleTransferAmountChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    
    // منع كتابة 0 فقط أو 0 متبوعة برقم آخر
    if (value === '0') {
      return;
    }
    
    // منع كتابة 0 في البداية متبوعًا برقم آخر
    if (value.length > 1 && value.startsWith('0') && value[1] !== '.') {
      return;
    }
    
    // Allow only numbers and a single decimal point
    if (!/^[0-9]*\.?[0-9]*$/.test(value) && value !== '') {
      return;
    }
    
    // Limit to 8 decimal places
    if (value.includes('.')) {
      const parts = value.split('.');
      if (parts[1] && parts[1].length > 8) {
        return;
      }
    }
    
    // Check if the entered amount exceeds balance
    if (value !== '' && parseFloat(value) > balance.balance) {
      setErrorMessage('Amount exceeds available balance');
    } else {
      setErrorMessage('');
    }
    
    setTransferAmount(value);
  };

  const calculateExpectedBalance = () => {
    if (!transferAmount || transferAmount === '') {
      return balance.formattedBalance;
    }
    
    try {
      const amountValue = parseFloat(transferAmount);
      if (isNaN(amountValue) || amountValue <= 0) {
        return balance.formattedBalance;
      }
      
      const newBalance = Math.max(0, balance.balance - amountValue);
      return newBalance.toFixed(8);
    } catch (e) {
      return balance.formattedBalance;
    }
  };

  const executeTransfer = async () => {
    if (!selectedContact) return;

    const validation = validateTransferAmount(transferAmount);
    if (!validation.valid) {
      setErrorMessage(validation.message);
      return;
    }

    setIsProcessing(true);
    
    try {
      const response = await axios.post('/api/quicktransfer/transfer', {
        contact_id: selectedContact.id,
        amount: transferAmount
      });

      if (response.data.success) {
        // Update local balance with the new balance from the response
        if (response.data.new_balance) {
          setBalance({
            balance: parseFloat(response.data.new_balance),
            formattedBalance: response.data.new_balance
          });
        } else {
          // Fallback to fetching balance if not provided in response
          await fetchUserBalance();
        }
        
        // Set success state but don't auto-close with timer
        setIsSuccess(true);
      } else {
        setErrorMessage(response.data.error || 'Transfer failed');
      }
    } catch (error: any) {
      console.error('Error executing transfer:', error);
      
      // Handle CSRF-related errors
      if (error.response && error.response.status === 403) {
        if (error.response.data.error && error.response.data.error.includes('CSRF')) {
          console.log('CSRF token error detected in executeTransfer, attempting to refresh...');
          
          // Clear the invalid token
          setCsrfToken('');
          
          // Try to refresh the token automatically
          const tokenRefreshed = await refreshCsrfToken();
          if (tokenRefreshed) {
            // Retry the request with the new token
            try {
              const retryResponse = await axios.post('/api/quicktransfer/transfer', {
                contact_id: selectedContact.id,
                amount: transferAmount
              });

              if (retryResponse.data.success) {
                // Update local balance with the new balance from the response
                if (retryResponse.data.new_balance) {
                  setBalance({
                    balance: parseFloat(retryResponse.data.new_balance),
                    formattedBalance: retryResponse.data.new_balance
                  });
                } else {
                  // Fallback to fetching balance if not provided in response
                  await fetchUserBalance();
                }
                
                // Set success state but don't auto-close with timer
                setIsSuccess(true);
                return; // Exit early on success
              } else {
                setErrorMessage(retryResponse.data.error || 'Transfer failed');
                return; // Exit early on failure
              }
            } catch (retryError: any) {
              console.error('Error on retry after CSRF refresh:', retryError);
              setErrorMessage('Security validation failed. Please refresh the page and try again.');
              return;
            }
          } else {
            setErrorMessage('Security validation failed. Please refresh the page and try again.');
            return;
          }
        }
      }
      
      setErrorMessage(error.response?.data?.error || 'Transfer failed. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#262626] py-4 sm:py-6 px-3 sm:px-4 md:px-6">
      <div className="max-w-4xl mx-auto">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className={`transition-all duration-700 ${animate ? 'translate-y-0 opacity-100' : 'translate-y-10 opacity-0'}`}
        >
          {/* Header */}
          <div className="mb-5 sm:mb-8">
            <div className="flex items-center justify-between">
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-200 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">Quick Transfer</h1>
              <div className="px-2 sm:px-3 py-1 sm:py-1.5 bg-gradient-to-r from-amber-500 to-yellow-700 text-white text-xs font-bold rounded-full shadow-lg">
                PREMIUM
              </div>
            </div>
            <p className="text-sm sm:text-base text-gray-400 mt-2">Transfer funds instantly to your trusted contacts - no password required</p>
          </div>

          {isLoading ? (
            <div className="space-y-6">
              {/* Balance Card Skeleton */}
              <div className={`bg-[#2b2b2b] rounded-xl p-5 border border-[#3A3A3E] shadow-lg`}>
                <div className={`h-4 w-28 bg-[#323234] rounded-md ${shimmer}`}></div>
                <div className={`h-6 w-40 bg-[#323234] rounded-md ${shimmer} mt-1`}></div>
              </div>
              
              {/* Contacts Skeleton */}
              <div className={`bg-[#2b2b2b] rounded-xl p-6 border border-[#3A3A3E] shadow-lg`}>
                <div className={`h-5 w-40 bg-[#323234] rounded-md ${shimmer} mb-6`}></div>
                
                <div className="flex justify-center space-x-6 py-6">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div key={i} className="flex flex-col items-center">
                      <div className={`w-14 h-14 sm:w-16 sm:h-16 rounded-full bg-[#323234] ${shimmer}`}></div>
                      <div className={`h-2 w-10 bg-[#323234] rounded mt-2 ${shimmer}`}></div>
                    </div>
                  ))}
                </div>
                
                <div className={`h-20 bg-[#323234] rounded-lg ${shimmer} mt-6`}></div>
              </div>
              
              {/* How It Works Skeleton */}
              <div className={`bg-[#2b2b2b] rounded-xl p-6 border border-[#3A3A3E] shadow-lg`}>
                <div className={`h-5 w-32 bg-[#323234] rounded-md ${shimmer} mb-6`}></div>
                
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="flex items-start space-x-3">
                      <div className={`w-7 h-7 rounded-full bg-[#323234] ${shimmer} flex-shrink-0`}></div>
                      <div className={`h-4 bg-[#323234] rounded ${shimmer} w-full`}></div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <>
              {/* Balance Card - تحسين التصميم */}
              <div className="bg-gradient-to-r from-[#2b2b2b] to-[#323232] rounded-xl shadow-lg border border-[#393939] p-4 sm:p-6 mb-4 sm:mb-6 hover:shadow-xl transition-all duration-300">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-400">Available Balance</p>
                    <h2 className="text-xl sm:text-2xl font-bold text-white mt-1">{balance.formattedBalance} CRN</h2>
                  </div>
                </div>
              </div>

              {/* Trusted Contacts Circle - تحسين التصميم وجعله أكثر استجابة للموبايل */}
              <div className="bg-gradient-to-r from-[#2b2b2b] to-[#323232] rounded-xl shadow-lg border border-[#393939] p-4 sm:p-6 mb-4 sm:mb-6">
                <h3 className="text-lg sm:text-xl font-semibold text-gray-200 mb-4 sm:mb-6">Trusted Contacts</h3>
                
                <div className="flex justify-center flex-wrap gap-3 sm:gap-6 py-3 sm:py-4">
                  {trustedContacts.map((contact) => (
                    <div 
                      key={contact.id} 
                      className="relative"
                    >
                      <button
                        onClick={() => handleContactClick(contact)}
                        className="w-14 h-14 sm:w-16 sm:h-16 md:w-20 md:h-20 rounded-full overflow-hidden hover:shadow-lg flex items-center justify-center transition-all transform hover:scale-110 shadow-lg group"
                      >
                        <div className="w-14 h-14 sm:w-16 sm:h-16 md:w-20 md:h-20 rounded-full overflow-hidden">
                          {getAvatarDisplay(contact)}
                        </div>
                      </button>
                      <p className="text-center text-xs text-gray-300 mt-1 truncate w-14 sm:w-16 md:w-20">{contact.username}</p>
                      
                      {/* Add button to remove contact for better mobile UX */}
                      {contact.can_delete !== false && (
                        <button 
                          onClick={() => handleDeleteRequest(contact)} 
                          className="absolute -top-1 -right-1 bg-red-600 rounded-full w-5 h-5 flex items-center justify-center shadow-md"
                          aria-label="Delete contact"
                        >
                          <X size={12} className="text-white" />
                        </button>
                      )}
                    </div>
                  ))}
                  
                  {/* Add Contact Button */}
                  {trustedContacts.length < 5 && (
                    <div>
                      <button 
                        onClick={() => setShowAddModal(true)}
                        className="w-14 h-14 sm:w-16 sm:h-16 md:w-20 md:h-20 rounded-full bg-[#383838] flex items-center justify-center hover:bg-[#444444] transition-all transform hover:scale-110"
                      >
                        <Plus size={24} className="text-gray-300" />
                      </button>
                      <p className="text-center text-xs text-gray-400 mt-1">Add New</p>
                    </div>
                  )}

                  {/* Placeholder circles if less than 5 contacts */}
                  {Array.from({ length: Math.max(0, 5 - trustedContacts.length - 1) }).map((_, index) => (
                    <div key={`placeholder-${index}`}>
                      <div className="w-14 h-14 sm:w-16 sm:h-16 md:w-20 md:h-20 rounded-full bg-[#333333] opacity-30 border border-[#444444] border-dashed"></div>
                      <p className="text-center text-xs text-gray-500 mt-1">Empty</p>
                    </div>
                  ))}
                </div>

                {trustedContacts.length >= 5 && (
                  <p className="text-sm text-amber-400 text-center mt-4">
                    Maximum number of trusted contacts (5) reached
                  </p>
                )}
                
                {/* تحذير محسن مع إضافة النص الجديد */}
                <div className="bg-blue-900/30 mt-4 sm:mt-6 p-3 sm:p-4 rounded-lg border border-blue-800">
                  <div className="flex items-start gap-2 sm:gap-3">
                    <AlertCircle className="text-blue-400 h-5 w-5 flex-shrink-0 mt-0.5" />
                    <div className="space-y-2">
                      <p className="text-xs sm:text-sm text-blue-300">
                        Quick transfers are instant and don't require additional authentication. Add only contacts you fully trust. Once added, contacts cannot be removed for 14 days to prevent abuse.
                      </p>
                      <p className="text-xs sm:text-sm text-yellow-300 font-medium">
                        WARNING: Using this service is entirely at your own risk. You are solely responsible for selecting your trusted contacts.
                      </p>
                    </div>
                  </div>
                </div>

                {/* عرض معدل الحد المتبقي */}
                {validationAttempts > 0 && (
                  <div className="mt-2 text-xs text-gray-400">
                    Validation attempts remaining: {rateLimitRemaining}/5
                    {isRateLimited && (
                      <div className="mt-1 text-amber-400">
                        Rate limited. Reset in {Math.ceil((rateLimitResetTime - Date.now()) / 1000)}s
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Information and Help - تحسين التصميم */}
              <div className="bg-gradient-to-r from-[#2b2b2b] to-[#323232] rounded-xl shadow-lg border border-[#393939] p-4 sm:p-6">
                <h3 className="text-lg sm:text-xl font-semibold text-gray-200 mb-4">How It Works</h3>
                <div className="space-y-3 sm:space-y-4">
                  <div className="flex items-start gap-2 sm:gap-3">
                    <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-gradient-to-br from-blue-600 to-blue-900 flex items-center justify-center text-blue-400 shadow-md flex-shrink-0">
                      1
                    </div>
                    <p className="text-sm sm:text-base text-gray-300">Add up to 5 trusted contacts using their private address</p>
                  </div>
                  <div className="flex items-start gap-2 sm:gap-3">
                    <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-gradient-to-br from-blue-600 to-blue-900 flex items-center justify-center text-blue-400 shadow-md flex-shrink-0">
                      2
                    </div>
                    <p className="text-sm sm:text-base text-gray-300">Click on a contact's avatar to initiate a quick transfer</p>
                  </div>
                  <div className="flex items-start gap-2 sm:gap-3">
                    <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-gradient-to-br from-blue-600 to-blue-900 flex items-center justify-center text-blue-400 shadow-md flex-shrink-0">
                      3
                    </div>
                    <p className="text-sm sm:text-base text-gray-300">Enter the amount and send instantly - no additional verification required</p>
                  </div>
                </div>
              </div>
            </>
          )}
        </motion.div>
      </div>

      {/* Add Contact Modal - تحسين التصميم ليكون أكثر استجابة للموبايل */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:p-0">
            <div className="fixed inset-0 transition-opacity" aria-hidden="true">
              <div className="absolute inset-0 bg-black bg-opacity-75 backdrop-blur-sm"></div>
            </div>

            <div className="inline-block w-full align-bottom bg-gradient-to-b from-[#2b2b2b] to-[#323232] rounded-xl text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:max-w-lg max-w-[95%] border border-[#393939]">
              <div className="flex justify-between items-center p-4 sm:p-6 border-b border-[#393939]">
                <h3 className="text-lg sm:text-xl font-semibold text-gray-200">
                  Add Trusted Contact
                </h3>
                <button
                  onClick={() => setShowAddModal(false)}
                  className="text-gray-400 hover:text-white p-2"
                >
                  <X size={20} />
                </button>
              </div>

              <div className="p-4 sm:p-6">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Enter Discord User ID
                </label>
                <div className="relative mb-4">
                  <input
                    type="text"
                    value={userId}
                    onChange={(e) => setUserId(e.target.value)}
                    className="w-full h-12 px-4 py-3 bg-[#232323] border border-[#393939] rounded-lg text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter contact's Discord user ID"
                  />
                  <button
                    onClick={() => validateAddress(userId)}
                    disabled={addressValidation.loading || isRateLimited}
                    className="absolute right-2 top-1/2 transform -translate-y-1/2 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors flex items-center justify-center"
                  >
                    {addressValidation.loading ? (
                      <RefreshCw size={16} className="animate-spin" />
                    ) : (
                      <>
                        <Search size={14} className="mr-1" />
                        Verify
                      </>
                    )}
                  </button>
                </div>

                {/* شرح كيفية العثور على معرف المستخدم */}
                <div className="mb-4 p-3 bg-[#1c1c1c] rounded-lg border border-[#393939]">
                  <p className="text-sm text-gray-300">
                    <strong>How to find a Discord User ID:</strong>
                  </p>
                  <ol className="text-xs text-gray-400 mt-1 list-decimal pl-4 space-y-1">
                    <li>Enable Developer Mode in Discord (User Settings → Advanced → Developer Mode)</li>
                    <li>Right-click on the user's name and select "Copy ID"</li>
                    <li>Paste the ID here (it should be a long number like 964005304943661106)</li>
                  </ol>
                </div>

                {/* Validation message */}
                {addressValidation.message && (
                  <div className={`flex items-start gap-2 mt-2 ${addressValidation.isValid ? 'text-green-400' : 'text-red-400'}`}>
                    {addressValidation.isValid ? (
                      <CheckCircle size={16} className="flex-shrink-0 mt-0.5" />
                    ) : (
                      <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />
                    )}
                    <p className="text-sm">{addressValidation.message}</p>
                  </div>
                )}

                {/* حقل كلمة المرور - أضفنا هذا الحقل */}
                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Password
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full h-12 px-4 py-3 bg-[#232323] border border-[#393939] rounded-lg text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter your password for verification"
                  />
                  <p className="text-xs text-gray-400 mt-1">Your password is required for security purposes.</p>
                </div>

                {/* User info if address is valid */}
                {addressValidation.isValid && addressValidation.username && (
                  <div className="mt-4 p-3 bg-[#1c1c1c] rounded-lg border border-[#393939]">
                    <p className="text-gray-300 text-sm">Verified User:</p>
                    <div className="flex items-center gap-3 mt-2">
                      <div className="w-10 h-10 rounded-full bg-blue-900/50 flex items-center justify-center">
                        <User size={20} className="text-blue-400" />
                      </div>
                      <div>
                        <p className="font-medium text-white">{addressValidation.username}</p>
                        <p className="text-xs text-gray-400 truncate max-w-[250px]">{userId}</p>
                      </div>
                    </div>
                    <div className="mt-3 p-2 bg-green-900/20 rounded border border-green-900/30">
                      <p className="text-xs text-green-400">
                        User successfully verified. Click "Enable" to add this user to your trusted contacts list.
                      </p>
                    </div>
                  </div>
                )}

                <div className="mt-6 flex justify-end gap-3">
                  <button
                    onClick={() => setShowAddModal(false)}
                    className="px-4 py-2.5 bg-[#393939] text-gray-200 rounded-lg hover:bg-[#444444] transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={addTrustedContact}
                    disabled={!addressValidation.isValid || isLoading}
                    className={`px-4 py-2.5 rounded-lg transition-colors flex items-center gap-2 ${
                      addressValidation.isValid
                        ? 'bg-blue-600 hover:bg-blue-700 text-white'
                        : 'bg-gray-700 text-gray-500 cursor-not-allowed'
                    }`}
                  >
                    {isLoading ? (
                      <RefreshCw size={16} className="animate-spin" />
                    ) : (
                      <Plus size={16} />
                    )}
                    {addressValidation.isValid ? 'Enable' : 'Add Contact'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Transfer Modal - تحسين التصميم ليكون أكثر استجابة للموبايل */}
      {showTransferModal && selectedContact && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:p-0">
            <div className="fixed inset-0 transition-opacity" aria-hidden="true">
              <div className="absolute inset-0 bg-black bg-opacity-75 backdrop-blur-sm"></div>
            </div>

            <div className="inline-block w-full align-bottom bg-gradient-to-b from-[#2b2b2b] to-[#323232] rounded-xl text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:max-w-md max-w-[95%] border border-[#393939]">
              {!isSuccess ? (
                <>
                  <div className="flex justify-between items-center p-4 sm:p-6 border-b border-[#393939]">
                    <h3 className="text-lg sm:text-xl font-semibold text-gray-200">
                      Quick Transfer
                    </h3>
                    <button
                      onClick={() => setShowTransferModal(false)}
                      className="text-gray-400 hover:text-white p-2"
                    >
                      <X size={20} />
                    </button>
                  </div>

                  <div className="p-4 sm:p-6">
                    {/* Recipient Info */}
                    <div className="flex flex-col items-center mb-6">
                      <div className="w-16 h-16 rounded-full overflow-hidden mb-3">
                        {getAvatarDisplay(selectedContact)}
                      </div>
                      <p className="text-gray-200 font-medium">{selectedContact.username}</p>
                      <p className="text-gray-400 text-xs mt-1">
                        {selectedContact.private_address.slice(0, 8)}...{selectedContact.private_address.slice(-8)}
                      </p>
                    </div>

                    {/* Amount Input */}
                    <div className="mb-6">
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Amount to Transfer
                      </label>
                      <div className="relative">
                        <input
                          type="text"
                          value={transferAmount}
                          onChange={handleTransferAmountChange}
                          className={`w-full h-12 px-4 py-3 bg-[#232323] border ${
                            errorMessage ? 'border-red-500' : 'border-[#393939]'
                          } rounded-lg text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500 text-lg`}
                          placeholder="0.00000000"
                          inputMode="decimal"
                          pattern="[0-9]*\.?[0-9]*"
                          max={balance.balance.toString()}
                          onKeyPress={(e) => {
                            // Allow only numbers and decimal point
                            const isValidKey = /[0-9.]/.test(e.key);
                            // Prevent multiple decimal points
                            if (e.key === '.' && transferAmount.includes('.')) {
                              e.preventDefault();
                              return;
                            }
                            // Prevent non-numeric and non-decimal input
                            if (!isValidKey) {
                              e.preventDefault();
                            }
                          }}
                        />
                        <div className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 font-medium">
                          CRN
                        </div>
                      </div>

                      {errorMessage && (
                        <div className="flex items-center gap-1.5 mt-2 text-red-400">
                          <AlertCircle size={14} />
                          <p className="text-sm">{errorMessage}</p>
                        </div>
                      )}

                      <div className="flex justify-between mt-2 text-sm">
                        <div className="flex flex-col">
                          <p className="text-gray-400">Available: {balance.formattedBalance} CRN</p>
                          {transferAmount && !errorMessage && (
                            <p className="text-green-400 text-xs mt-1">Balance after transfer: {calculateExpectedBalance()} CRN</p>
                          )}
                        </div>
                        <button 
                          className="text-blue-500 hover:text-blue-400 transition-colors ml-2 px-2"
                          onClick={() => setTransferAmount(balance.formattedBalance)}
                        >
                          Max
                        </button>
                      </div>
                    </div>

                    <div className="mt-6 flex flex-wrap justify-end gap-3">
                      <button
                        onClick={() => setShowTransferModal(false)}
                        className="px-4 py-2.5 bg-[#393939] text-gray-200 rounded-lg hover:bg-[#444444] transition-colors"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => {
                          setShowTransferModal(false);
                          handleDeleteRequest(selectedContact);
                        }}
                        className={`px-4 py-2.5 rounded-lg transition-colors flex items-center gap-2 ${
                          selectedContact.can_delete !== false
                            ? 'bg-red-600 hover:bg-red-700 text-white'
                            : 'bg-gray-700 text-gray-500 cursor-not-allowed'
                        }`}
                        title={selectedContact.can_delete !== false 
                          ? 'Delete contact' 
                          : `Contacts can only be removed after 14 days (${selectedContact.days_remaining || 14} days remaining)`}
                      >
                        <X size={16} />
                        {selectedContact.can_delete !== false ? 'Delete' : `${selectedContact.days_remaining || 14} days left`}
                      </button>
                      <button
                        onClick={executeTransfer}
                        disabled={!transferAmount || isProcessing || !!errorMessage}
                        className={`px-4 py-2.5 rounded-lg transition-colors flex items-center gap-2 ${
                          transferAmount && !isProcessing && !errorMessage
                            ? 'bg-blue-600 hover:bg-blue-700 text-white'
                            : 'bg-gray-700 text-gray-500 cursor-not-allowed'
                        }`}
                      >
                        {isProcessing ? (
                          <RefreshCw size={16} className="animate-spin" />
                        ) : (
                          <Send size={16} />
                        )}
                        Send Now
                      </button>
                    </div>
                  </div>
                </>
              ) : (
                <div className="p-4 sm:p-6 py-6 flex flex-col items-center">
                  <div className="w-16 h-16 rounded-full bg-green-900/30 flex items-center justify-center mb-4">
                    <CheckCircle size={32} className="text-green-500" />
                  </div>
                  <h3 className="text-xl font-semibold text-green-400 mb-2">Transfer Successful!</h3>
                  <p className="text-gray-300 text-center mb-3">
                    Successfully sent {transferAmount} CRN to {selectedContact.username}
                  </p>
                  <div className="bg-[#1c1c1c] rounded-lg p-4 mb-4 w-full">
                    <div className="flex justify-between text-sm mb-2">
                      <span className="text-gray-400">Amount Sent:</span>
                      <span className="text-white font-medium">{transferAmount} CRN</span>
                    </div>
                    <div className="flex justify-between text-sm mb-2">
                      <span className="text-gray-400">Recipient:</span>
                      <span className="text-white font-medium">{selectedContact.username}</span>
                    </div>
                    <div className="flex justify-between text-sm mb-2">
                      <span className="text-gray-400">Previous Balance:</span>
                      <span className="text-gray-300">{(parseFloat(transferAmount) + balance.balance).toFixed(8)} CRN</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">New Balance:</span>
                      <span className="text-green-400 font-medium">{balance.formattedBalance} CRN</span>
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      setShowTransferModal(false);
                      setSelectedContact(null);
                      setTransferAmount('');
                      setIsSuccess(false);
                    }}
                    className="px-6 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                  >
                    Done
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* نافذة تأكيد الحذف */}
      {showDeleteConfirmModal && contactToDelete && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:p-0">
            <div className="fixed inset-0 transition-opacity" aria-hidden="true">
              <div className="absolute inset-0 bg-black bg-opacity-75 backdrop-blur-sm"></div>
            </div>

            <div className="inline-block w-full align-bottom bg-gradient-to-b from-[#2b2b2b] to-[#323232] rounded-xl text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:max-w-md max-w-[95%] border border-[#393939]">
              <div className="flex justify-between items-center p-4 sm:p-6 border-b border-[#393939]">
                <h3 className="text-lg sm:text-xl font-semibold text-red-400">
                  Confirm Deletion
                </h3>
                <button
                  onClick={() => setShowDeleteConfirmModal(false)}
                  className="text-gray-400 hover:text-white p-2"
                >
                  <X size={20} />
                </button>
              </div>

              <div className="p-4 sm:p-6">
                <div className="flex flex-col items-center mb-6">
                  <div className="w-16 h-16 rounded-full overflow-hidden mb-3">
                    {getAvatarDisplay(contactToDelete)}
                  </div>
                  <p className="text-gray-200 font-medium">{contactToDelete.username}</p>
                  <p className="text-gray-400 text-xs mt-1">
                    {contactToDelete.private_address.slice(0, 8)}...{contactToDelete.private_address.slice(-8)}
                  </p>
                  {contactToDelete.added_at_formatted && (
                    <p className="text-gray-400 text-xs mt-1">
                      Added on: {contactToDelete.added_at_formatted}
                    </p>
                  )}
                </div>

                <div className="bg-red-900/20 p-4 rounded-lg border border-red-900/30 mb-6">
                  <p className="text-sm text-red-300 text-center">
                    Are you sure you want to remove this contact from your trusted list? This action cannot be undone.
                  </p>
                </div>

                {/* حقل كلمة المرور - أضفنا هذا الحقل */}
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Password
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full h-12 px-4 py-3 bg-[#232323] border border-[#393939] rounded-lg text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter your password for verification"
                  />
                  <p className="text-xs text-gray-400 mt-1">Your password is required for security purposes.</p>
                </div>

                <div className="flex flex-wrap justify-end gap-3">
                  <button
                    onClick={() => setShowDeleteConfirmModal(false)}
                    className="px-4 py-2.5 bg-[#393939] text-gray-200 rounded-lg hover:bg-[#444444] transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => removeTrustedContact(contactToDelete.id)}
                    disabled={isLoading}
                    className="px-4 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2"
                  >
                    {isLoading ? (
                      <RefreshCw size={16} className="animate-spin" />
                    ) : (
                      <X size={16} />
                    )}
                    Delete
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default QuickTransfer; 
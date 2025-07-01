import React, { createContext, useState, useContext, useEffect, ReactNode } from 'react';

// Define languages available in the app
export const languages = {
  en: 'English',
  ar: 'العربية'
};

export type LanguageKey = keyof typeof languages;

// Cache for loaded translation files
const translationCache: Record<string, Record<string, any>> = {
  en: {},
  ar: {}
};

// Interface for language context
interface LanguageContextType {
  language: LanguageKey;
  setLanguage: (language: LanguageKey) => void;
  t: (key: string, file?: string) => string;
  isRTL: boolean;
}

// Create context with default values
const LanguageContext = createContext<LanguageContextType>({
  language: 'en',
  setLanguage: () => {},
  t: () => '',
  isRTL: false,
});

// Props for provider component
interface LanguageProviderProps {
  children: ReactNode;
}

// Function to load a translation file dynamically
const loadTranslation = async (
  language: LanguageKey, 
  file: string
): Promise<Record<string, any>> => {
  // Check if already cached
  if (translationCache[language][file]) {
    return translationCache[language][file];
  }
  
  try {
    // Dynamic import based on language and file
    const module = await import(`./${language}/${file}.json`);
    translationCache[language][file] = module.default || module;
    return translationCache[language][file];
  } catch (error) {
    console.error(`Failed to load ${file} translations for ${language}:`, error);
    return {};
  }
};

// Provider component
export const LanguageProvider = ({ children }: LanguageProviderProps): JSX.Element => {
  // Try to get language from localStorage, default to 'en'
  const [language, setLanguage] = useState<LanguageKey>(() => {
    const savedLanguage = localStorage.getItem('language');
    return (savedLanguage === 'ar' || savedLanguage === 'en') ? savedLanguage : 'en';
  });
  
  // Check if current language is RTL
  const isRTL = language === 'ar';

  // Update document direction and localStorage when language changes
  useEffect(() => {
    document.documentElement.dir = isRTL ? 'rtl' : 'ltr';
    document.documentElement.lang = language;
    localStorage.setItem('language', language);
    
    // Add or remove RTL class to body
    if (isRTL) {
      document.body.classList.add('rtl');
    } else {
      document.body.classList.remove('rtl');
    }
  }, [language, isRTL]);

  // Translation function that loads the required file
  const t = (key: string, file: string = 'common'): string => {
    const [fileName, entryKey] = key.includes('.') ? 
      key.split('.', 2) : 
      [file, key];
    
    // Try to get from cache first
    const cachedTranslations = translationCache[language][fileName];
    
    if (cachedTranslations && cachedTranslations[entryKey]) {
      return cachedTranslations[entryKey];
    }
    
    // Load file if not in cache
    if (!translationCache[language][fileName]) {
      loadTranslation(language, fileName).then(() => {
        // Force re-render after loading
        const forceUpdate = {};
        setLanguage(lang => {
          // This trick forces a re-render without changing the value
          Object.assign(forceUpdate, { temp: lang });
          return lang;
        });
      });
    }
    
    // Fallback to key
    return entryKey;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t, isRTL }}>
      {children}
    </LanguageContext.Provider>
  );
};

// Custom hook to use the language context
export const useLanguage = (): LanguageContextType => useContext(LanguageContext); 
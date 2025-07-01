import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import { Shield, LineChart, Clock, Key, Users, BarChart3, Wallet as WalletIcon, RefreshCw, Layers, Database, Lock, Shuffle } from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";

const Wallet = () => {
  // التمرير إلى الأعلى عند تحميل المكون
  useEffect(() => {
    window.scrollTo(0, 0);
    
    // إضافة اتجاه RTL للعناصر العربية
    document.documentElement.dir = 'rtl';
    
    return () => {
      document.documentElement.dir = 'ltr';
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#262626]">
      <Navbar />
      
      {/* قسم العنوان الرئيسي */}
      <div className="bg-gradient-to-b from-[#1A1A1A] to-[#262626] pt-24 pb-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h1 
              className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-[#6C5DD3] to-[#8875FF] bg-clip-text text-transparent mb-6"
              style={{ direction: 'rtl', textAlign: 'center', fontFamily: 'Arial, sans-serif' }}
            >
              محفظة كلاين
            </h1>
            <p 
              className="text-xl text-[#A1A1AA] max-w-3xl mx-auto leading-relaxed"
              style={{ direction: 'rtl', textAlign: 'center' }}
            >
              محفظة آمنة لتخزين وإدارة عملات CRN الخاصة بك مع واجهة سهلة الاستخدام
            </p>
          </div>
        </div>
      </div>
      
      {/* قسم نظرة عامة على الميزات */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">ميزات محفظة متطورة</h2>
            <p className="text-[#A1A1AA] max-w-2xl mx-auto">
              تم تصميم محفظة كلاين لتوفير أعلى مستويات الأمان والراحة لمستخدمي العملات المشفرة
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {/* ميزة الأمان */}
            <div className="bg-[#1A1A1A] rounded-xl p-8 border border-[#2A2A2D] hover:border-[#6C5DD3] transition-all duration-300 hover:shadow-lg hover:shadow-[#6C5DD3]/10">
              <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-14 h-14 rounded-lg flex items-center justify-center mb-6">
                <Shield className="w-7 h-7 text-[#6C5DD3]" />
              </div>
              <h3 className="text-xl font-bold text-white mb-3">أمان متقدم</h3>
              <p className="text-[#A1A1AA]">
                استمتع بميزات أمان متعددة الطبقات بما في ذلك المصادقة الثنائية، قفل المحفظة، وتقييد العناوين IP، وتأمين المحفظة بكلمة سر، والمزيد.
              </p>
            </div>
            
            {/* ميزة تتبع النمو */}
            <div className="bg-[#1A1A1A] rounded-xl p-8 border border-[#2A2A2D] hover:border-[#6C5DD3] transition-all duration-300 hover:shadow-lg hover:shadow-[#6C5DD3]/10">
              <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-14 h-14 rounded-lg flex items-center justify-center mb-6">
                <LineChart className="w-7 h-7 text-[#6C5DD3]" />
              </div>
              <h3 className="text-xl font-bold text-white mb-3">تتبع النمو</h3>
              <p className="text-[#A1A1AA]">
                راقب نمو رصيدك ومعدلات النمو على مدار اليوم والأسبوع والشهر مع مخططات تفاعلية وتحليلات متقدمة.
              </p>
            </div>
            
            {/* ميزة النسخ الاحتياطي */}
            <div className="bg-[#1A1A1A] rounded-xl p-8 border border-[#2A2A2D] hover:border-[#6C5DD3] transition-all duration-300 hover:shadow-lg hover:shadow-[#6C5DD3]/10">
              <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-14 h-14 rounded-lg flex items-center justify-center mb-6">
                <Database className="w-7 h-7 text-[#6C5DD3]" />
              </div>
              <h3 className="text-xl font-bold text-white mb-3">نسخ احتياطي آمن</h3>
              <p className="text-[#A1A1AA]">
                قم بإنشاء نسخ احتياطية مشفرة لمحفظتك وبياناتك، واسترجعها بسهولة باستخدام رموز استرداد آمنة.
              </p>
            </div>
            
            {/* ميزة سجل المعاملات */}
            <div className="bg-[#1A1A1A] rounded-xl p-8 border border-[#2A2A2D] hover:border-[#6C5DD3] transition-all duration-300 hover:shadow-lg hover:shadow-[#6C5DD3]/10">
              <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-14 h-14 rounded-lg flex items-center justify-center mb-6">
                <Clock className="w-7 h-7 text-[#6C5DD3]" />
              </div>
              <h3 className="text-xl font-bold text-white mb-3">سجل المعاملات</h3>
              <p className="text-[#A1A1AA]">
                تتبع جميع معاملاتك المرسلة والمستلمة مع تفاصيل كاملة وإحصائيات شاملة عن نشاط محفظتك.
              </p>
            </div>
            
            {/* ميزة العنوان المخصص */}
            <div className="bg-[#1A1A1A] rounded-xl p-8 border border-[#2A2A2D] hover:border-[#6C5DD3] transition-all duration-300 hover:shadow-lg hover:shadow-[#6C5DD3]/10">
              <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-14 h-14 rounded-lg flex items-center justify-center mb-6">
                <Key className="w-7 h-7 text-[#6C5DD3]" />
              </div>
              <h3 className="text-xl font-bold text-white mb-3">عنوان مخصص</h3>
              <p className="text-[#A1A1AA]">
                قم بإنشاء وتخصيص عنوان محفظتك الخاص لتسهيل استلام المدفوعات والتحويلات.
              </p>
            </div>
            
            {/* ميزة تصنيف المستخدم */}
            <div className="bg-[#1A1A1A] rounded-xl p-8 border border-[#2A2A2D] hover:border-[#6C5DD3] transition-all duration-300 hover:shadow-lg hover:shadow-[#6C5DD3]/10">
              <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-14 h-14 rounded-lg flex items-center justify-center mb-6">
                <Users className="w-7 h-7 text-[#6C5DD3]" />
              </div>
              <h3 className="text-xl font-bold text-white mb-3">تصنيف المستخدم</h3>
              <p className="text-[#A1A1AA]">
                اكتسب تقييمات إيجابية وتابع سمعتك في النظام مع نظام تقييم متكامل.
              </p>
            </div>
          </div>
        </div>
      </section>
      
      {/* قسم ميزات الأمان المتقدمة */}
      <section className="py-16 bg-[#1A1A1A]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">ميزات أمان متقدمة</h2>
            <p className="text-[#A1A1AA] max-w-2xl mx-auto">
              حماية مشددة لأصولك الرقمية مع مجموعة شاملة من ميزات الأمان
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
            <div className="space-y-6">
              <div className="flex gap-4">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-12 h-12 rounded-lg flex items-center justify-center shrink-0">
                  <Lock className="w-6 h-6 text-[#6C5DD3]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">المصادقة الثنائية (2FA)</h3>
                  <p className="text-[#A1A1AA]">
                    طبقة أمان إضافية لحساب محفظتك باستخدام رموز أمان متغيرة. تتوفر أيضًا رموز استرداد احتياطية.
                  </p>
                </div>
              </div>
              
              <div className="flex gap-4">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-12 h-12 rounded-lg flex items-center justify-center shrink-0">
                  <Shield className="w-6 h-6 text-[#6C5DD3]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">تجميد المحفظة</h3>
                  <p className="text-[#A1A1AA]">
                    قم بتجميد محفظتك فوراً في حالة الاشتباه بنشاط غير مصرح به، مما يمنع أي عمليات سحب أو تحويل.
                  </p>
                </div>
              </div>
              
              <div className="flex gap-4">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-12 h-12 rounded-lg flex items-center justify-center shrink-0">
                  <WalletIcon className="w-6 h-6 text-[#6C5DD3]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">حدود التحويل اليومية</h3>
                  <p className="text-[#A1A1AA]">
                    تعيين حدود قصوى للتحويلات اليومية لحماية أموالك حتى في حالة الوصول غير المصرح به.
                  </p>
                </div>
              </div>
            </div>
            
            <div className="space-y-6">
              <div className="flex gap-4">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-12 h-12 rounded-lg flex items-center justify-center shrink-0">
                  <Shuffle className="w-6 h-6 text-[#6C5DD3]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">طرق مصادقة التحويل</h3>
                  <p className="text-[#A1A1AA]">
                    خيارات متعددة للمصادقة عند إجراء التحويلات، بما في ذلك كلمة المرور، 2FA، أو كلمة سرية.
                  </p>
                </div>
              </div>
              
              <div className="flex gap-4">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-12 h-12 rounded-lg flex items-center justify-center shrink-0">
                  <BarChart3 className="w-6 h-6 text-[#6C5DD3]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">مراقبة النشاط المشبوه</h3>
                  <p className="text-[#A1A1AA]">
                    تحليل مستمر لأنماط المعاملات للكشف عن النشاط غير العادي وإرسال تنبيهات في حالة الاشتباه.
                  </p>
                </div>
              </div>
              
              <div className="flex gap-4">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-12 h-12 rounded-lg flex items-center justify-center shrink-0">
                  <Layers className="w-6 h-6 text-[#6C5DD3]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">قائمة IP المسموح بها</h3>
                  <p className="text-[#A1A1AA]">
                    قيود الوصول الجغرافي وإدارة قائمة عناوين IP المسموح بها للوصول إلى حسابك.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
      
      {/* قسم ميزات النسخ الاحتياطي */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">النسخ الاحتياطي والاسترداد</h2>
            <p className="text-[#A1A1AA] max-w-2xl mx-auto">
              تأمين بياناتك وأصولك الرقمية مع خيارات نسخ احتياطي متعددة
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
            <div className="space-y-6">
              <div className="flex gap-4">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-12 h-12 rounded-lg flex items-center justify-center shrink-0">
                  <Database className="w-6 h-6 text-[#6C5DD3]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">نسخ احتياطي مشفر</h3>
                  <p className="text-[#A1A1AA]">
                    إنشاء نسخ احتياطية مشفرة كاملة لمحفظتك وبياناتك، محمية بكلمة مرور قوية.
                  </p>
                </div>
              </div>
              
              <div className="flex gap-4">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-12 h-12 rounded-lg flex items-center justify-center shrink-0">
                  <RefreshCw className="w-6 h-6 text-[#6C5DD3]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">تنبيهات النسخ الاحتياطي</h3>
                  <p className="text-[#A1A1AA]">
                    تذكيرات دورية لإنشاء نسخ احتياطية جديدة، مع تصنيف مستوى الأمان بناءً على حداثة النسخة الاحتياطية.
                  </p>
                </div>
              </div>
            </div>
            
            <div className="space-y-6">
              <div className="flex gap-4">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-12 h-12 rounded-lg flex items-center justify-center shrink-0">
                  <Key className="w-6 h-6 text-[#6C5DD3]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">رموز الاسترداد</h3>
                  <p className="text-[#A1A1AA]">
                    مجموعة من رموز الاسترداد لمرة واحدة يمكن استخدامها لاستعادة الوصول إلى حسابك في حالة فقدان بيانات المصادقة.
                  </p>
                </div>
              </div>
              
              <div className="flex gap-4">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-12 h-12 rounded-lg flex items-center justify-center shrink-0">
                  <WalletIcon className="w-6 h-6 text-[#6C5DD3]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">تصدير البيانات</h3>
                  <p className="text-[#A1A1AA]">
                    تصدير بيانات المعاملات وتاريخ النشاط بتنسيقات متعددة للاحتفاظ بسجلات خارجية.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
      
      {/* قسم العضويات المميزة */}
      <section className="py-16 bg-[#1A1A1A]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">مزايا العضوية المميزة</h2>
            <p className="text-[#A1A1AA] max-w-2xl mx-auto">
              ميزات إضافية حصرية لأعضاء العضوية المميزة
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-[#262626] rounded-xl p-8 border border-[#2A2A2D] hover:border-[#6C5DD3] transition-all duration-300">
              <h3 className="text-xl font-bold text-white mb-3">حدود تحويل أعلى</h3>
              <p className="text-[#A1A1AA] mb-6">
                استمتع بحدود تحويل يومية أعلى للمعاملات أكثر مرونة.
              </p>
              <div className="h-1 w-full bg-[#2A2A2D]">
                <div className="h-1 bg-gradient-to-r from-[#6C5DD3] to-[#8875FF] w-3/4"></div>
              </div>
            </div>
            
            <div className="bg-[#262626] rounded-xl p-8 border border-[#2A2A2D] hover:border-[#6C5DD3] transition-all duration-300">
              <h3 className="text-xl font-bold text-white mb-3">رسوم تحويل مخفضة</h3>
              <p className="text-[#A1A1AA] mb-6">
                استفد من رسوم تحويل مخفضة على جميع المعاملات.
              </p>
              <div className="h-1 w-full bg-[#2A2A2D]">
                <div className="h-1 bg-gradient-to-r from-[#6C5DD3] to-[#8875FF] w-2/3"></div>
              </div>
            </div>
            
            <div className="bg-[#262626] rounded-xl p-8 border border-[#2A2A2D] hover:border-[#6C5DD3] transition-all duration-300">
              <h3 className="text-xl font-bold text-white mb-3">تحليلات متقدمة</h3>
              <p className="text-[#A1A1AA] mb-6">
                رؤى وتحليلات متقدمة لتتبع أداء محفظتك بشكل أفضل.
              </p>
              <div className="h-1 w-full bg-[#2A2A2D]">
                <div className="h-1 bg-gradient-to-r from-[#6C5DD3] to-[#8875FF] w-5/6"></div>
              </div>
            </div>
          </div>
        </div>
      </section>
      
      {/* قسم الدعوة للعمل */}
      <section className="py-20">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 rounded-2xl p-10 border border-[#6C5DD3]/30 text-center">
            <h2 className="text-3xl font-bold text-white mb-6">ابدأ استخدام محفظة كلاين اليوم</h2>
            <p className="text-[#A1A1AA] text-lg mb-8 max-w-2xl mx-auto">
              إنشاء حساب مجاني وابدأ في إدارة أصولك الرقمية بأمان وسهولة. استمتع بجميع الميزات المتقدمة التي توفرها محفظة كلاين.
            </p>
            <div className="flex flex-col sm:flex-row justify-center gap-4">
              <Link
                to="/signup"
                className="bg-gradient-to-r from-[#6C5DD3] to-[#8875FF] hover:opacity-90 transition-all duration-300 text-white font-medium py-3 px-8 rounded-lg"
              >
                إنشاء محفظة جديدة
              </Link>
              <Link
                to="/login"
                className="bg-[#1A1A1A] border border-[#2A2A2D] hover:border-[#6C5DD3] transition-all duration-300 text-white font-medium py-3 px-8 rounded-lg"
              >
                تسجيل الدخول
              </Link>
            </div>
          </div>
        </div>
      </section>
      
      <Footer />
    </div>
  );
};

export default Wallet; 
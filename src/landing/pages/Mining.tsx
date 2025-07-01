import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import { Cpu, Clock, Shield, AlertTriangle, CheckCircle, Zap, Monitor, Lock, Users, Smartphone, TrendingUp, Server, Globe, Ban, AlertCircle } from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";

const Mining = () => {
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
              نظام التعدين في كلاين
            </h1>
            <p 
              className="text-xl text-[#A1A1AA] max-w-3xl mx-auto leading-relaxed"
              style={{ direction: 'rtl', textAlign: 'center' }}
            >
              قم بتعدين عملات CRN بسهولة وأمان من خلال نظام التعدين المباشر في كلاين
            </p>
          </div>
        </div>
      </div>
      
      {/* قسم كيفية عمل التعدين */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">كيفية عمل نظام التعدين</h2>
            <p className="text-[#A1A1AA] max-w-2xl mx-auto">
              عملية بسيطة ومباشرة للحصول على عملة CRN من خلال تشغيل التعدين في حسابك
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* الخطوة الأولى */}
            <div className="bg-[#1A1A1A] rounded-xl p-8 border border-[#2A2A2D] hover:border-[#6C5DD3] transition-all duration-300 hover:shadow-lg hover:shadow-[#6C5DD3]/10">
              <div className="relative mb-8">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-14 h-14 rounded-lg flex items-center justify-center">
                  <Cpu className="w-7 h-7 text-[#6C5DD3]" />
                </div>
                <div className="absolute top-0 left-0 w-8 h-8 bg-[#6C5DD3] rounded-full flex items-center justify-center -translate-x-2 -translate-y-2">
                  <span className="text-white font-bold">1</span>
                </div>
              </div>
              <h3 className="text-xl font-bold text-white mb-3">تشغيل التعدين</h3>
              <p className="text-[#A1A1AA]">
                انقر على زر "ابدأ التعدين" في صفحة التعدين لبدء عملية التعدين. سيقوم النظام بإجراء فحص أمني قبل بدء التعدين.
              </p>
            </div>
            
            {/* الخطوة الثانية */}
            <div className="bg-[#1A1A1A] rounded-xl p-8 border border-[#2A2A2D] hover:border-[#6C5DD3] transition-all duration-300 hover:shadow-lg hover:shadow-[#6C5DD3]/10">
              <div className="relative mb-8">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-14 h-14 rounded-lg flex items-center justify-center">
                  <Zap className="w-7 h-7 text-[#6C5DD3]" />
                </div>
                <div className="absolute top-0 left-0 w-8 h-8 bg-[#6C5DD3] rounded-full flex items-center justify-center -translate-x-2 -translate-y-2">
                  <span className="text-white font-bold">2</span>
                </div>
              </div>
              <h3 className="text-xl font-bold text-white mb-3">انتظر عملية التعدين</h3>
              <p className="text-[#A1A1AA]">
                ستعمل عملية التعدين لمدة تصل إلى 10 ثوانٍ. خلال هذا الوقت، ستكسب عملة CRN بناءً على معدل التعدين الخاص بك وظروف الشبكة.
              </p>
            </div>
            
            {/* الخطوة الثالثة */}
            <div className="bg-[#1A1A1A] rounded-xl p-8 border border-[#2A2A2D] hover:border-[#6C5DD3] transition-all duration-300 hover:shadow-lg hover:shadow-[#6C5DD3]/10">
              <div className="relative mb-8">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-14 h-14 rounded-lg flex items-center justify-center">
                  <Clock className="w-7 h-7 text-[#6C5DD3]" />
                </div>
                <div className="absolute top-0 left-0 w-8 h-8 bg-[#6C5DD3] rounded-full flex items-center justify-center -translate-x-2 -translate-y-2">
                  <span className="text-white font-bold">3</span>
                </div>
              </div>
              <h3 className="text-xl font-bold text-white mb-3">فترة الانتظار</h3>
              <p className="text-[#A1A1AA]">
                بعد اكتمال التعدين، ستكون هناك فترة انتظار مدتها 24 ساعة قبل أن تتمكن من التعدين مرة أخرى.
              </p>
            </div>
          </div>
        </div>
      </section>
      
      {/* قسم معدلات التعدين */}
      <section className="py-16 bg-[#1A1A1A]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">معدلات التعدين والمكافآت</h2>
            <p className="text-[#A1A1AA] max-w-2xl mx-auto">
              معدلات التعدين ديناميكية وتعتمد على عدة عوامل بما في ذلك ظروف الشبكة والعضوية
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
            <div className="space-y-6">
              <div className="flex gap-4">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-12 h-12 rounded-lg flex items-center justify-center shrink-0">
                  <TrendingUp className="w-6 h-6 text-[#6C5DD3]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">معدل التعدين الأساسي</h3>
                  <p className="text-[#A1A1AA]">
                    معدل التعدين يتغير باستمرار ويعتمد على العديد من العوامل مثل نشاط الشبكة وعدد المستخدمين. يتناقص المعدل تدريجياً مع مرور الوقت وزيادة عدد المستخدمين.
                  </p>
                </div>
              </div>
              
              <div className="flex gap-4">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-12 h-12 rounded-lg flex items-center justify-center shrink-0">
                  <Server className="w-6 h-6 text-[#6C5DD3]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">ظروف الشبكة</h3>
                  <p className="text-[#A1A1AA]">
                    تؤثر ظروف الشبكة على معدل التعدين الخاص بك. يمكن أن تكون الظروف: ممتازة، جيدة، عادية، متغيرة، أو صعبة، وتؤثر على كمية العملات المعدنة.
                  </p>
                </div>
              </div>
              
              <div className="flex gap-4">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-12 h-12 rounded-lg flex items-center justify-center shrink-0">
                  <Zap className="w-6 h-6 text-[#6C5DD3]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">التعدين المعزز</h3>
                  <p className="text-[#A1A1AA]">
                    خلال فترات التعدين المعزز، يتضاعف معدل التعدين لجميع المستخدمين (100% زيادة). يتم الإعلان عن هذه الفترات من خلال شعار "التعدين المعزز" في واجهة التعدين.
                  </p>
                </div>
              </div>
            </div>
            
            <div className="space-y-6">
              <div className="flex gap-4">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-12 h-12 rounded-lg flex items-center justify-center shrink-0">
                  <Clock className="w-6 h-6 text-[#6C5DD3]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">فترة الانتظار</h3>
                  <p className="text-[#A1A1AA]">
                    بعد كل عملية تعدين، هناك فترة انتظار مدتها 24 ساعة قبل أن تتمكن من التعدين مرة أخرى.
                  </p>
                </div>
              </div>
              
              <div className="flex gap-4">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-12 h-12 rounded-lg flex items-center justify-center shrink-0">
                  <Users className="w-6 h-6 text-[#6C5DD3]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">التعدين من أجهزة متعددة</h3>
                  <p className="text-[#A1A1AA]">
                    يمكن لكل مستخدم التعدين من حتى 3 أجهزة مختلفة. يتم تسجيل الأجهزة تلقائيًا عند التعدين.
                  </p>
                </div>
              </div>
              
              <div className="flex gap-4">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-12 h-12 rounded-lg flex items-center justify-center shrink-0">
                  <Smartphone className="w-6 h-6 text-[#6C5DD3]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">التعدين من أجهزة متعددة</h3>
                  <p className="text-[#A1A1AA]">
                    يمكن لكل مستخدم التعدين من حتى 3 أجهزة مختلفة. يتم تسجيل الأجهزة تلقائيًا عند التعدين.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
      
      {/* قسم سياسة التعدين والأمان */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">سياسة التعدين والأمان</h2>
            <p className="text-[#A1A1AA] max-w-2xl mx-auto">
              نظام التعدين لدينا مصمم ليكون آمنًا وعادلًا للجميع مع تطبيق قواعد صارمة لضمان نزاهة النظام
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
            <div>
              <h3 className="text-xl font-bold text-white mb-6 flex items-center">
                <Shield className="w-6 h-6 text-[#6C5DD3] mr-3" />
                ما هو مسموح به
              </h3>
              <ul className="space-y-3 text-[#A1A1AA]">
                <li className="flex items-start">
                  <CheckCircle className="w-5 h-5 text-green-500 mr-2 shrink-0 mt-0.5" />
                  <span>استخدام ما يصل إلى 3 أجهزة مختلفة للتعدين لكل حساب</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle className="w-5 h-5 text-green-500 mr-2 shrink-0 mt-0.5" />
                  <span>استخدام ما يصل إلى 5 حسابات مختلفة على نفس الشبكة (نفس عنوان IP)</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle className="w-5 h-5 text-green-500 mr-2 shrink-0 mt-0.5" />
                  <span>التعدين من شبكات مختلفة (المنزل، العمل، إلخ) باستخدام نفس الحساب</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle className="w-5 h-5 text-green-500 mr-2 shrink-0 mt-0.5" />
                  <span>استخدام متصفحات مختلفة على نفس الجهاز (يتم احتسابها كجهاز واحد)</span>
                </li>
              </ul>
            </div>
            
            <div>
              <h3 className="text-xl font-bold text-white mb-6 flex items-center">
                <Ban className="w-6 h-6 text-red-500 mr-3" />
                ما هو غير مسموح به
              </h3>
              <ul className="space-y-3 text-[#A1A1AA]">
                <li className="flex items-start">
                  <AlertTriangle className="w-5 h-5 text-red-500 mr-2 shrink-0 mt-0.5" />
                  <span>استخدام أكثر من حساب واحد على نفس الجهاز</span>
                </li>
                <li className="flex items-start">
                  <AlertTriangle className="w-5 h-5 text-red-500 mr-2 shrink-0 mt-0.5" />
                  <span>استخدام VPN أو بروكسي للتعدين (سيؤدي ذلك إلى حظر التعدين)</span>
                </li>
                <li className="flex items-start">
                  <AlertTriangle className="w-5 h-5 text-red-500 mr-2 shrink-0 mt-0.5" />
                  <span>استخدام الأجهزة الافتراضية أو المحاكيات للتعدين</span>
                </li>
                <li className="flex items-start">
                  <AlertTriangle className="w-5 h-5 text-red-500 mr-2 shrink-0 mt-0.5" />
                  <span>محاولة التحايل على نظام فترة الانتظار أو نظام تتبع الأجهزة</span>
                </li>
                <li className="flex items-start">
                  <AlertTriangle className="w-5 h-5 text-red-500 mr-2 shrink-0 mt-0.5" />
                  <span>إنشاء حسابات متعددة للتعدين من نفس الجهاز (مزارع التعدين)</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>
      
      {/* قسم أنظمة الأمان */}
      <section className="py-16 bg-[#1A1A1A]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">أنظمة الحماية</h2>
            <p className="text-[#A1A1AA] max-w-2xl mx-auto">
              تم تصميم نظام التعدين لتوفير تجربة آمنة وعادلة لجميع المستخدمين
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-[#262626] rounded-xl p-6 border border-[#2A2A2D] transition-all duration-300">
              <div className="flex items-center mb-4">
                <div className="bg-[#6C5DD3]/20 w-10 h-10 rounded-lg flex items-center justify-center mr-3">
                  <Shield className="w-5 h-5 text-[#6C5DD3]" />
                </div>
                <h3 className="text-lg font-bold text-white">حماية الحساب</h3>
              </div>
              <p className="text-[#A1A1AA] text-sm">
                نظام متكامل يعمل على حماية حسابك والعملات التي قمت بتعدينها من أي محاولات وصول غير مصرح بها.
              </p>
            </div>
            
            <div className="bg-[#262626] rounded-xl p-6 border border-[#2A2A2D] transition-all duration-300">
              <div className="flex items-center mb-4">
                <div className="bg-[#6C5DD3]/20 w-10 h-10 rounded-lg flex items-center justify-center mr-3">
                  <Cpu className="w-5 h-5 text-[#6C5DD3]" />
                </div>
                <h3 className="text-lg font-bold text-white">تكنولوجيا متقدمة</h3>
              </div>
              <p className="text-[#A1A1AA] text-sm">
                نستخدم تقنيات متقدمة لضمان عمليات تعدين سلسة وآمنة مع منع أي محاولات للتلاعب بالنظام.
              </p>
            </div>
            
            <div className="bg-[#262626] rounded-xl p-6 border border-[#2A2A2D] transition-all duration-300">
              <div className="flex items-center mb-4">
                <div className="bg-[#6C5DD3]/20 w-10 h-10 rounded-lg flex items-center justify-center mr-3">
                  <Users className="w-5 h-5 text-[#6C5DD3]" />
                </div>
                <h3 className="text-lg font-bold text-white">نظام عادل</h3>
              </div>
              <p className="text-[#A1A1AA] text-sm">
                تم تصميم النظام ليوفر فرصاً متساوية لجميع المستخدمين للتعدين والحصول على عملات CRN.
              </p>
            </div>
          </div>
        </div>
      </section>
      
      {/* قسم الأسئلة الشائعة */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">الأسئلة الشائعة</h2>
            <p className="text-[#A1A1AA] max-w-2xl mx-auto">
              إجابات على الأسئلة الأكثر شيوعًا حول نظام التعدين
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-[#1A1A1A] rounded-xl p-6 border border-[#2A2A2D]">
              <h3 className="text-lg font-bold text-white mb-3">كيف يتم حساب معدل التعدين؟</h3>
              <p className="text-[#A1A1AA]">
                يتم حساب معدل التعدين بناءً على نشاطك في المنصة، تاريخ تعدينك، ووقت تسجيلك. تؤثر ظروف الشبكة أيضًا على المعدل النهائي، وقد يتم تعزيزه خلال فترات التعدين المعزز.
              </p>
            </div>
            
            <div className="bg-[#1A1A1A] rounded-xl p-6 border border-[#2A2A2D]">
              <h3 className="text-lg font-bold text-white mb-3">لماذا تم حظر تعديني؟</h3>
              <p className="text-[#A1A1AA]">
                قد يتم حظر التعدين بسبب انتهاك سياسة التعدين، مثل استخدام VPN، أو تعدين حسابات متعددة من نفس الجهاز، أو استخدام محاكيات. تظهر رسالة توضح سبب الحظر عند محاولة التعدين.
              </p>
            </div>
            
            <div className="bg-[#1A1A1A] rounded-xl p-6 border border-[#2A2A2D]">
              <h3 className="text-lg font-bold text-white mb-3">ما هي فترة الانتظار؟</h3>
              <p className="text-[#A1A1AA]">
                فترة الانتظار هي 24 ساعة بين عمليات التعدين. هذه الفترة مطبقة على جميع المستخدمين بدون استثناءات.
              </p>
            </div>
            
            <div className="bg-[#1A1A1A] rounded-xl p-6 border border-[#2A2A2D]">
              <h3 className="text-lg font-bold text-white mb-3">هل يمكنني التعدين من أجهزة متعددة؟</h3>
              <p className="text-[#A1A1AA]">
                نعم، يمكنك التعدين من حتى 3 أجهزة مختلفة باستخدام نفس الحساب. يتم تسجيل الأجهزة تلقائيًا عند التعدين.
              </p>
            </div>
            
            <div className="bg-[#1A1A1A] rounded-xl p-6 border border-[#2A2A2D]">
              <h3 className="text-lg font-bold text-white mb-3">ما معنى "ظروف التعدين"؟</h3>
              <p className="text-[#A1A1AA]">
                ظروف التعدين تشير إلى حالة شبكة التعدين وتأثيرها على العائد. تتراوح من "ممتازة" (عائد أعلى) إلى "صعبة" (عائد أقل) وتتغير ديناميكيًا بناءً على نشاط الشبكة.
              </p>
            </div>
            
            <div className="bg-[#1A1A1A] rounded-xl p-6 border border-[#2A2A2D]">
              <h3 className="text-lg font-bold text-white mb-3">لماذا يتطلب التعدين التحقق بخطوتين؟</h3>
              <p className="text-[#A1A1AA]">
                يتطلب التعدين التحقق بخطوتين (2FA) لزيادة أمان حسابك ومنع الاستخدام غير المصرح به. هذا إجراء أمان إلزامي لجميع عمليات التعدين.
              </p>
            </div>
          </div>
        </div>
      </section>
      
      {/* قسم الدعوة للعمل */}
      <section className="py-20">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 rounded-2xl p-10 border border-[#6C5DD3]/30 text-center">
            <h2 className="text-3xl font-bold text-white mb-6">ابدأ التعدين اليوم</h2>
            <p className="text-[#A1A1AA] text-lg mb-8 max-w-2xl mx-auto">
              سجل دخولك وابدأ في استخدام نظام التعدين للحصول على عملة CRN بسهولة وأمان.
            </p>
            <div className="flex flex-col sm:flex-row justify-center gap-4">
              <Link
                to="/signup"
                className="bg-gradient-to-r from-[#6C5DD3] to-[#8875FF] hover:opacity-90 transition-all duration-300 text-white font-medium py-3 px-8 rounded-lg"
              >
                إنشاء حساب جديد
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

export default Mining; 
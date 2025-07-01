import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import { Shield, Clock, Send, ArrowRight, AlertCircle, CheckCircle, ArrowRightCircle, TrendingUp, User, Users, Wallet, Ban, Info } from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";

const Transfers = () => {
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
              نظام التحويلات في كلاين
            </h1>
            <p 
              className="text-xl text-[#A1A1AA] max-w-3xl mx-auto leading-relaxed"
              style={{ direction: 'rtl', textAlign: 'center' }}
            >
              أرسل واستقبل عملات CRN بسرعة وأمان بين مستخدمي منصة كلاين
            </p>
          </div>
        </div>
      </div>
      
      {/* قسم كيفية عمل التحويلات */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">كيفية إجراء التحويلات</h2>
            <p className="text-[#A1A1AA] max-w-2xl mx-auto">
              عملية بسيطة ومباشرة لإرسال الأموال إلى مستخدمين آخرين بأمان وسرعة
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* الخطوة الأولى */}
            <div className="bg-[#1A1A1A] rounded-xl p-8 border border-[#2A2A2D] hover:border-[#6C5DD3] transition-all duration-300 hover:shadow-lg hover:shadow-[#6C5DD3]/10">
              <div className="relative mb-8">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-14 h-14 rounded-lg flex items-center justify-center">
                  <User className="w-7 h-7 text-[#6C5DD3]" />
                </div>
                <div className="absolute top-0 left-0 w-8 h-8 bg-[#6C5DD3] rounded-full flex items-center justify-center -translate-x-2 -translate-y-2">
                  <span className="text-white font-bold">1</span>
                </div>
              </div>
              <h3 className="text-xl font-bold text-white mb-3">إدخال عنوان المستلم</h3>
              <p className="text-[#A1A1AA]">
                أدخل العنوان الخاص بالمستلم. يمكنك استخدام نظام العناوين المخصصة أو نظام جهات الاتصال الموثوقة للتحويل السريع.
              </p>
            </div>
            
            {/* الخطوة الثانية */}
            <div className="bg-[#1A1A1A] rounded-xl p-8 border border-[#2A2A2D] hover:border-[#6C5DD3] transition-all duration-300 hover:shadow-lg hover:shadow-[#6C5DD3]/10">
              <div className="relative mb-8">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-14 h-14 rounded-lg flex items-center justify-center">
                  <Wallet className="w-7 h-7 text-[#6C5DD3]" />
                </div>
                <div className="absolute top-0 left-0 w-8 h-8 bg-[#6C5DD3] rounded-full flex items-center justify-center -translate-x-2 -translate-y-2">
                  <span className="text-white font-bold">2</span>
                </div>
              </div>
              <h3 className="text-xl font-bold text-white mb-3">تحديد المبلغ</h3>
              <p className="text-[#A1A1AA]">
                حدد المبلغ الذي تريد تحويله، مع مراعاة الرسوم ونسبة الخصم التي تعتمد على نوع عضويتك. سترى ملخصًا للمبلغ النهائي قبل التأكيد.
              </p>
            </div>
            
            {/* الخطوة الثالثة */}
            <div className="bg-[#1A1A1A] rounded-xl p-8 border border-[#2A2A2D] hover:border-[#6C5DD3] transition-all duration-300 hover:shadow-lg hover:shadow-[#6C5DD3]/10">
              <div className="relative mb-8">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-14 h-14 rounded-lg flex items-center justify-center">
                  <Shield className="w-7 h-7 text-[#6C5DD3]" />
                </div>
                <div className="absolute top-0 left-0 w-8 h-8 bg-[#6C5DD3] rounded-full flex items-center justify-center -translate-x-2 -translate-y-2">
                  <span className="text-white font-bold">3</span>
                </div>
              </div>
              <h3 className="text-xl font-bold text-white mb-3">التحقق والتأكيد</h3>
              <p className="text-[#A1A1AA]">
                أدخل سبب التحويل وطريقة المصادقة المطلوبة (الكلمة السرية أو 2FA أو كلمة مرور التحويل) ثم أكد العملية لإتمام التحويل.
              </p>
            </div>
          </div>
        </div>
      </section>
      
      {/* قسم القوانين والحدود */}
      <section className="py-16 bg-[#1A1A1A]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">قوانين وحدود التحويلات</h2>
            <p className="text-[#A1A1AA] max-w-2xl mx-auto">
              الضوابط والإجراءات المتبعة لضمان أمان وسلامة عمليات التحويل
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
            <div className="space-y-6">
              <div className="flex gap-4">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-12 h-12 rounded-lg flex items-center justify-center shrink-0">
                  <Clock className="w-6 h-6 text-[#6C5DD3]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">فترة الانتظار بين التحويلات</h3>
                  <p className="text-[#A1A1AA]">
                    تطبق فترة انتظار قدرها دقيقة واحدة بين كل عملية تحويل وأخرى للمستخدمين العاديين. أما أعضاء العضوية المميزة فيستمتعون بميزة عدم الانتظار بين التحويلات.
                  </p>
                </div>
              </div>
              
              <div className="flex gap-4">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-12 h-12 rounded-lg flex items-center justify-center shrink-0">
                  <Ban className="w-6 h-6 text-[#6C5DD3]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">القيود على الحسابات المحظورة</h3>
                  <p className="text-[#A1A1AA]">
                    لا يمكن إجراء تحويلات إلى الحسابات المحظورة أو المجمدة. ستظهر رسالة خطأ توضح سبب رفض التحويل عند محاولة التحويل لهذه الحسابات.
                  </p>
                </div>
              </div>
              
              <div className="flex gap-4">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-12 h-12 rounded-lg flex items-center justify-center shrink-0">
                  <Wallet className="w-6 h-6 text-[#6C5DD3]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">الحد اليومي للتحويل</h3>
                  <p className="text-[#A1A1AA]">
                    يمكنك تعيين حد يومي للتحويلات من إعدادات المحفظة لزيادة مستوى الأمان. يتم تحديث هذا الحد يوميًا ويمكن تعديله حسب احتياجاتك.
                  </p>
                </div>
              </div>
            </div>
            
            <div className="space-y-6">
              <div className="flex gap-4">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-12 h-12 rounded-lg flex items-center justify-center shrink-0">
                  <Send className="w-6 h-6 text-[#6C5DD3]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">رسوم التحويل</h3>
                  <p className="text-[#A1A1AA]">
                    تطبق رسوم بنسبة 1% على جميع التحويلات للمستخدمين العاديين. أعضاء العضوية المميزة يستفيدون من الإعفاء التام من الرسوم.
                  </p>
                </div>
              </div>
              
              <div className="flex gap-4">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-12 h-12 rounded-lg flex items-center justify-center shrink-0">
                  <Info className="w-6 h-6 text-[#6C5DD3]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">سبب التحويل</h3>
                  <p className="text-[#A1A1AA]">
                    يجب تحديد سبب واضح لكل عملية تحويل. هذا يساعد في توثيق المعاملات وتسهيل تتبعها في سجل المعاملات الخاص بك.
                  </p>
                </div>
              </div>
              
              <div className="flex gap-4">
                <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 w-12 h-12 rounded-lg flex items-center justify-center shrink-0">
                  <Users className="w-6 h-6 text-[#6C5DD3]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">نظام التقييم</h3>
                  <p className="text-[#A1A1AA]">
                    بعد إتمام التحويل، يمكنك تقييم تجربة التحويل مع المستلم. يساعد نظام التقييم في بناء سمعة المستخدمين وزيادة الثقة في المنصة.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
      
      {/* قسم ميزات التحويل السريع */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">التحويل السريع والجهات الموثوقة</h2>
            <p className="text-[#A1A1AA] max-w-2xl mx-auto">
              ميزات متقدمة لتسهيل وتسريع عمليات التحويل المتكررة
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
            <div className="bg-[#1A1A1A] rounded-xl p-8 border border-[#2A2A2D] hover:border-[#6C5DD3] transition-all duration-300">
              <h3 className="text-xl font-bold text-white mb-6 flex items-center">
                <Send className="w-6 h-6 text-[#6C5DD3] mr-3" />
                التحويل السريع (للعضوية المميزة فقط)
              </h3>
              <p className="text-[#A1A1AA] mb-6">
                ميزة حصرية تتيح للمستخدمين المميزين إجراء تحويلات سريعة إلى جهات الاتصال الموثوقة المحفوظة لديهم، دون الحاجة لإدخال العنوان الخاص في كل مرة.
              </p>
              <ul className="space-y-3 text-[#A1A1AA]">
                <li className="flex items-start">
                  <CheckCircle className="w-5 h-5 text-green-500 mr-2 shrink-0 mt-0.5" />
                  <span>إضافة ما يصل إلى 5 جهات اتصال موثوقة</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle className="w-5 h-5 text-green-500 mr-2 shrink-0 mt-0.5" />
                  <span>تحويل سريع بضغطة واحدة</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle className="w-5 h-5 text-green-500 mr-2 shrink-0 mt-0.5" />
                  <span>تتبع تاريخ التحويلات لكل جهة اتصال</span>
                </li>
              </ul>
            </div>
            
            <div className="bg-[#1A1A1A] rounded-xl p-8 border border-[#2A2A2D] hover:border-[#6C5DD3] transition-all duration-300">
              <h3 className="text-xl font-bold text-white mb-6 flex items-center">
                <Users className="w-6 h-6 text-[#6C5DD3] mr-3" />
                جهات الاتصال الموثوقة
              </h3>
              <p className="text-[#A1A1AA] mb-6">
                أضف مستخدمين تتعامل معهم بشكل متكرر إلى قائمة جهات الاتصال الموثوقة لتسهيل وتسريع عمليات التحويل المستقبلية.
              </p>
              <ul className="space-y-3 text-[#A1A1AA]">
                <li className="flex items-start">
                  <CheckCircle className="w-5 h-5 text-green-500 mr-2 shrink-0 mt-0.5" />
                  <span>إضافة جهات الاتصال باستخدام العنوان الخاص</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle className="w-5 h-5 text-green-500 mr-2 shrink-0 mt-0.5" />
                  <span>إدارة قائمة جهات الاتصال الموثوقة بسهولة</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle className="w-5 h-5 text-green-500 mr-2 shrink-0 mt-0.5" />
                  <span>خاصية مسح العناوين للتحقق من صحتها</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>
      
      {/* قسم حالات الخطأ الشائعة */}
      <section className="py-16 bg-[#1A1A1A]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">حالات الخطأ الشائعة</h2>
            <p className="text-[#A1A1AA] max-w-2xl mx-auto">
              فهم أسباب رفض التحويلات وكيفية التعامل معها
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* خطأ 1 */}
            <div className="bg-[#262626] rounded-xl p-6 border border-red-900/30">
              <div className="flex items-start gap-3">
                <div className="bg-red-900/30 p-2 rounded-lg">
                  <AlertCircle className="w-6 h-6 text-red-500" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">محفظة مجمدة</h3>
                  <p className="text-[#A1A1AA]">
                    تظهر هذه الرسالة عندما تكون محفظة المستلم مجمدة. لا يمكن إرسال الأموال إلى محفظة مجمدة حتى يقوم المستلم بإلغاء تجميدها.
                  </p>
                </div>
              </div>
            </div>
            
            {/* خطأ 2 */}
            <div className="bg-[#262626] rounded-xl p-6 border border-red-900/30">
              <div className="flex items-start gap-3">
                <div className="bg-red-900/30 p-2 rounded-lg">
                  <AlertCircle className="w-6 h-6 text-red-500" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">رصيد غير كافٍ</h3>
                  <p className="text-[#A1A1AA]">
                    تظهر هذه الرسالة عندما لا يكون لديك رصيد كافٍ لإتمام التحويل، مع الأخذ في الاعتبار المبلغ ورسوم التحويل.
                  </p>
                </div>
              </div>
            </div>
            
            {/* خطأ 3 */}
            <div className="bg-[#262626] rounded-xl p-6 border border-red-900/30">
              <div className="flex items-start gap-3">
                <div className="bg-red-900/30 p-2 rounded-lg">
                  <AlertCircle className="w-6 h-6 text-red-500" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">فترة الانتظار نشطة</h3>
                  <p className="text-[#A1A1AA]">
                    تظهر هذه الرسالة عندما تحاول إجراء تحويل قبل انتهاء فترة الانتظار المطلوبة بين التحويلات. انتظر حتى انتهاء الوقت المحدد.
                  </p>
                </div>
              </div>
            </div>
            
            {/* خطأ 4 */}
            <div className="bg-[#262626] rounded-xl p-6 border border-red-900/30">
              <div className="flex items-start gap-3">
                <div className="bg-red-900/30 p-2 rounded-lg">
                  <AlertCircle className="w-6 h-6 text-red-500" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">خطأ في المصادقة</h3>
                  <p className="text-[#A1A1AA]">
                    تظهر هذه الرسالة عند إدخال رمز 2FA أو كلمة المرور أو الكلمة السرية بشكل غير صحيح. تحقق من المعلومات وحاول مرة أخرى.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
      
      {/* قسم مزايا العضوية المميزة */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">مزايا العضوية المميزة للتحويلات</h2>
            <p className="text-[#A1A1AA] max-w-2xl mx-auto">
              استمتع بمزايا حصرية عند الترقية إلى العضوية المميزة
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-gradient-to-r from-[#1A1A1A] to-[#262626] rounded-xl p-8 border border-[#2A2A2D] hover:border-[#6C5DD3] transition-all duration-300">
              <TrendingUp className="w-10 h-10 text-[#6C5DD3] mb-6" />
              <h3 className="text-xl font-bold text-white mb-3">إعفاء من الرسوم</h3>
              <p className="text-[#A1A1AA] mb-4">
                استمتع بإعفاء كامل من رسوم التحويل البالغة 1% على جميع عمليات التحويل التي تقوم بها.
              </p>
              <div className="h-1 w-full bg-[#2A2A2D]">
                <div className="h-1 bg-gradient-to-r from-[#6C5DD3] to-[#8875FF] w-full"></div>
              </div>
            </div>
            
            <div className="bg-gradient-to-r from-[#1A1A1A] to-[#262626] rounded-xl p-8 border border-[#2A2A2D] hover:border-[#6C5DD3] transition-all duration-300">
              <Clock className="w-10 h-10 text-[#6C5DD3] mb-6" />
              <h3 className="text-xl font-bold text-white mb-3">إلغاء فترة الانتظار</h3>
              <p className="text-[#A1A1AA] mb-4">
                استمتع بميزة إجراء التحويلات المتتالية دون أي فترة انتظار، بدلاً من الانتظار لمدة دقيقة واحدة بين كل تحويل وآخر.
              </p>
              <div className="h-1 w-full bg-[#2A2A2D]">
                <div className="h-1 bg-gradient-to-r from-[#6C5DD3] to-[#8875FF] w-4/5"></div>
              </div>
            </div>
            
            <div className="bg-gradient-to-r from-[#1A1A1A] to-[#262626] rounded-xl p-8 border border-[#2A2A2D] hover:border-[#6C5DD3] transition-all duration-300">
              <Users className="w-10 h-10 text-[#6C5DD3] mb-6" />
              <h3 className="text-xl font-bold text-white mb-3">التحويل السريع (للعضوية المميزة فقط)</h3>
              <p className="text-[#A1A1AA] mb-4">
                ميزة حصرية للأعضاء المميزين تتيح إضافة 5 جهات اتصال موثوقة وإجراء تحويلات سريعة إليهم بضغطة واحدة.
              </p>
              <div className="h-1 w-full bg-[#2A2A2D]">
                <div className="h-1 bg-gradient-to-r from-[#6C5DD3] to-[#8875FF] w-2/3"></div>
              </div>
            </div>
          </div>
        </div>
      </section>
      
      {/* قسم الدعوة للعمل */}
      <section className="py-20">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-gradient-to-r from-[#6C5DD3]/20 to-[#8875FF]/20 rounded-2xl p-10 border border-[#6C5DD3]/30 text-center">
            <h2 className="text-3xl font-bold text-white mb-6">ابدأ استخدام نظام التحويلات اليوم</h2>
            <p className="text-[#A1A1AA] text-lg mb-8 max-w-2xl mx-auto">
              سجل دخولك وابدأ في استخدام نظام التحويلات الآمن والسريع، وأرسل الأموال إلى أصدقائك وعائلتك بكل سهولة.
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

export default Transfers; 
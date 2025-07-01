import React, { useEffect } from "react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";

const Terms = () => {
  // Scroll to top when the component mounts
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="min-h-screen bg-[#262626]">
      <Navbar />
      
      <main className="max-w-4xl mx-auto px-4 py-16 sm:px-6 lg:px-8 text-gray-300">
        <h1 className="text-3xl font-bold text-white mb-8 text-center">Terms of Service</h1>
        
        <div className="space-y-8">
          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Introduction</h2>
            <p className="mb-4">
              Welcome to Clyne. These Terms of Service ("Terms") govern your use of our website, services, and any related applications (collectively, the "Service").
            </p>
            <p className="mb-4">
              By accessing or using our Service, you agree to be bound by these Terms. If you disagree with any part of the terms, you may not access the Service.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Accounts</h2>
            <p className="mb-4">
              When you create an account with us, you must provide information that is accurate, complete, and current at all times. Failure to do so constitutes a breach of the Terms, which may result in immediate termination of your account on our Service.
            </p>
            <p className="mb-4">
              You are responsible for safeguarding the password and credentials used to access the Service and for any activities or actions under your account. You agree not to disclose your password to any third party.
            </p>
            <p>
              You must notify us immediately upon becoming aware of any breach of security or unauthorized use of your account.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Services and Fees</h2>
            <p className="mb-4">
              Clyne provides digital wallet services, cryptocurrency management tools, and related functionalities. Some of our services may be subject to fees, which will be clearly disclosed before any transaction.
            </p>
            <p className="mb-4">
              We reserve the right to modify or discontinue, temporarily or permanently, the Service (or any part thereof) with or without notice. We shall not be liable to you or to any third party for any modification, price change, suspension, or discontinuance of the Service.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Intellectual Property</h2>
            <p className="mb-4">
              The Service and its original content, features, and functionality are and will remain the exclusive property of Clyne and its licensors. The Service is protected by copyright, trademark, and other laws of both the United States and foreign countries.
            </p>
            <p>
              Our trademarks and trade dress may not be used in connection with any product or service without the prior written consent of Clyne.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">User Conduct</h2>
            <p className="mb-4">You agree not to use the Service:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li>In any way that violates any applicable national or international law or regulation</li>
              <li>For the purpose of exploiting, harming, or attempting to exploit or harm minors in any way</li>
              <li>To transmit, or procure the sending of, any advertising or promotional material, including any "junk mail", "chain letter," "spam," or any other similar solicitation</li>
              <li>To impersonate or attempt to impersonate Clyne, a Clyne employee, another user, or any other person or entity</li>
              <li>For fraud, scams, or any form of deceptive activities</li>
              <li>For gambling or any other illegal betting activities</li>
              <li>To engage in any other conduct that restricts or inhibits anyone's use or enjoyment of the Service, or which, as determined by us, may harm Clyne or users of the Service or expose them to liability</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Disclaimer</h2>
            <p className="mb-4">
              Your use of the Service is at your sole risk. The Service is provided on an "AS IS" and "AS AVAILABLE" basis. The Service is provided without warranties of any kind, whether express or implied, including, but not limited to, implied warranties of merchantability, fitness for a particular purpose, non-infringement, or course of performance.
            </p>
            <p>
              Clyne does not warrant that: (a) the Service will function uninterrupted, secure, or available at any particular time or location; (b) any errors or defects will be corrected; (c) the Service is free of viruses or other harmful components; or (d) the results of using the Service will meet your requirements.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Limitation of Liability</h2>
            <p className="mb-4">
              In no event shall Clyne, nor its directors, employees, partners, agents, suppliers, or affiliates, be liable for any indirect, incidental, special, consequential, or punitive damages, including without limitation, loss of profits, data, use, goodwill, or other intangible losses, resulting from: (i) your access to or use of or inability to access or use the Service; (ii) any conduct or content of any third party on the Service; (iii) any content obtained from the Service; and (iv) unauthorized access, use, or alteration of your transmissions or content, whether based on warranty, contract, tort (including negligence), or any other legal theory, whether or not we have been informed of the possibility of such damage.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Governing Law</h2>
            <p>
              These Terms shall be governed and construed in accordance with the laws of [Your Country/State], without regard to its conflict of law provisions. Our failure to enforce any right or provision of these Terms will not be considered a waiver of those rights.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Changes to These Terms</h2>
            <p className="mb-4">
              We reserve the right, at our sole discretion, to modify or replace these Terms at any time. If a revision is material, we will try to provide at least 30 days' notice prior to any new terms taking effect.
            </p>
            <p>
              By continuing to access or use our Service after those revisions become effective, you agree to be bound by the revised terms. If you do not agree to the new terms, please stop using the Service.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Contact Us</h2>
            <p>
              If you have any questions about these Terms, please contact us 
            </p>
          </section>
        </div>
      </main>
      
      <Footer />
    </div>
  );
};

export default Terms; 
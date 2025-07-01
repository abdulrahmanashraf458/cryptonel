import React, { useEffect } from "react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";

const Privacy = () => {
  // Scroll to top when the component mounts
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="min-h-screen bg-[#262626]">
      <Navbar />
      
      <main className="max-w-4xl mx-auto px-4 py-16 sm:px-6 lg:px-8 text-gray-300">
        <h1 className="text-3xl font-bold text-white mb-8 text-center">Privacy Policy</h1>
        
        <div className="space-y-8">
          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Introduction</h2>
            <p className="mb-4">
              At Clyne, we respect your privacy and are committed to protecting your personal data. This Privacy Policy explains how we collect, use, process, and store your information when you use our services.
            </p>
            <p>
              By using Clyne's services, you consent to the collection and use of information in accordance with this policy.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Information We Collect</h2>
            <p className="mb-4">We collect several types of information for various purposes to provide and improve our service to you:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li><strong>Personal Data:</strong> Email address, first name, last name, username</li>
              <li><strong>Usage Data:</strong> Information on how you use our service</li>
              <li><strong>Transaction Data:</strong> Details of transactions you carry out through our service</li>
              <li><strong>Device Information:</strong> IP address, browser type, operating system</li>
              <li><strong>Cookies and Tracking Data:</strong> We use cookies and similar tracking technologies to track activity on our service</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Use of Your Information</h2>
            <p className="mb-4">We may use the information we collect for the following purposes:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li>To provide and maintain our service</li>
              <li>To notify you about changes to our service</li>
              <li>To allow you to participate in interactive features of our service</li>
              <li>To provide customer support</li>
              <li>To gather analysis or valuable information to improve our service</li>
              <li>To monitor the usage of our service</li>
              <li>To detect, prevent, and address technical issues</li>
              <li>To fulfill any other purpose for which you provide it</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Security of Data</h2>
            <p className="mb-4">
              The security of your data is important to us. We strive to use commercially acceptable means to protect your personal information, 
              including implementing advanced encryption, secure network architecture, and access controls.
            </p>
            <p>
              However, please be aware that no method of transmission over the Internet or method of electronic storage is 100% secure. 
              While we strive to use commercially acceptable means to protect your personal data, we cannot guarantee its absolute security.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Your Data Protection Rights</h2>
            <p className="mb-4">
              Depending on your location, you may have certain rights regarding your personal data:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>The right to access, update or delete the information we have about you</li>
              <li>The right of rectification - the right to have your information corrected if it is inaccurate or incomplete</li>
              <li>The right to object - the right to object to our processing of your personal data</li>
              <li>The right of restriction - the right to request that we restrict the processing of your personal information</li>
              <li>The right to data portability - the right to receive a copy of your personal data in a structured, machine-readable format</li>
              <li>The right to withdraw consent - the right to withdraw your consent at any time</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Changes to This Privacy Policy</h2>
            <p className="mb-4">
              We may update our Privacy Policy from time to time. We will notify you of any changes by posting the new Privacy Policy on this page.
            </p>
            <p>
              You are advised to review this Privacy Policy periodically for any changes. Changes to this Privacy Policy are effective when they are posted on this page.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Contact Us</h2>
            <p>
              If you have any questions about this Privacy Policy, please contact us
            </p>
          </section>
        </div>
      </main>
      
      <Footer />
    </div>
  );
};

export default Privacy; 
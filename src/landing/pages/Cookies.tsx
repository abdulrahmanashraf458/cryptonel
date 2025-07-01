import React, { useEffect } from "react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";

const Cookies = () => {
  // Scroll to top when the component mounts
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="min-h-screen bg-[#262626]">
      <Navbar />
      
      <main className="max-w-4xl mx-auto px-4 py-16 sm:px-6 lg:px-8 text-gray-300">
        <h1 className="text-3xl font-bold text-white mb-8 text-center">Cookie Policy</h1>
        
        <div className="space-y-8">
          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">What Are Cookies</h2>
            <p className="mb-4">
              Cookies are small pieces of text sent to your web browser by a website you visit. A cookie file is stored in your web browser and allows the Service or a third-party to recognize you and make your next visit easier and the Service more useful to you.
            </p>
            <p>
              Cookies can be "persistent" or "session" cookies. Persistent cookies remain on your personal computer or mobile device when you go offline, while session cookies are deleted as soon as you close your web browser.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">How Clyne Uses Cookies</h2>
            <p className="mb-4">
              When you use and access the Service, we may place a number of cookie files in your web browser. We use cookies for the following purposes:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>
                <strong>Essential cookies:</strong> These are cookies that are required for the operation of our website. They include, for example, cookies that enable you to log into secure areas of our website or make use of e-billing services.
              </li>
              <li>
                <strong>Functionality cookies:</strong> These are used to recognize you when you return to our website. This enables us to personalize our content for you, greet you by name, and remember your preferences (for example, your choice of language or region).
              </li>
              <li>
                <strong>Analytical/performance cookies:</strong> They allow us to recognize and count the number of visitors and to see how visitors move around our website when they are using it. This helps us to improve the way our website works, for example, by ensuring that users are finding what they are looking for easily.
              </li>
              <li>
                <strong>Targeting cookies:</strong> These cookies record your visit to our website, the pages you have visited, and the links you have followed. We will use this information to make our website and the advertising displayed on it more relevant to your interests.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Third-Party Cookies</h2>
            <p className="mb-4">
              In addition to our own cookies, we may also use various third-party cookies to report usage statistics of the Service, deliver advertisements on and through the Service, and so on.
            </p>
            <p>
              These third-party services may use cookies, pixel tags, and other technologies to collect information about your use of our website and other websites, including your IP address, web browser, pages viewed, time spent on pages, links clicked, and conversion information. This information may be used by these third-party services to provide analytics services and deliver targeted content and advertising to you.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">What Are Your Choices Regarding Cookies</h2>
            <p className="mb-4">
              If you'd like to delete cookies or instruct your web browser to delete or refuse cookies, please visit the help pages of your web browser.
            </p>
            <p className="mb-4">
              Please note, however, that if you delete cookies or refuse to accept them, you might not be able to use all of the features we offer, you may not be able to store your preferences, and some of our pages might not display properly.
            </p>
            <p>
              Most web browsers allow you to manage your cookie preferences. You can set your browser to refuse cookies or delete certain cookies. Generally, you can also manage similar technologies in the same way that you manage cookies using your browser's preferences.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Browser Specific Instructions</h2>
            <div className="space-y-4">
              <div>
                <h3 className="text-xl font-semibold text-white mb-2">Google Chrome</h3>
                <p>
                  You can manage cookies in Chrome by clicking on Settings {'->'} Privacy and Security {'->'} Cookies and other site data. From here, you can choose to block third-party cookies, clear cookies when you close your browser, or block all cookies (not recommended).
                </p>
              </div>
              
              <div>
                <h3 className="text-xl font-semibold text-white mb-2">Mozilla Firefox</h3>
                <p>
                  You can manage cookies in Firefox by clicking on Options {'->'} Privacy & Security. Under the Cookies and Site Data section, you can choose to delete cookies when Firefox closes or block cookies altogether.
                </p>
              </div>
              
              <div>
                <h3 className="text-xl font-semibold text-white mb-2">Safari</h3>
                <p>
                  You can manage cookies in Safari by clicking on Preferences {'->'} Privacy. You can choose to block all cookies, only allow cookies from websites you visit, or other customized settings.
                </p>
              </div>
              
              <div>
                <h3 className="text-xl font-semibold text-white mb-2">Microsoft Edge</h3>
                <p>
                  You can manage cookies in Edge by clicking on Settings {'->'} Cookies and site permissions {'->'} Cookies and site data. You can choose to block third-party cookies or clear cookies when you close the browser.
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Changes to This Cookie Policy</h2>
            <p className="mb-4">
              We may update our Cookie Policy from time to time. We will notify you of any changes by posting the new Cookie Policy on this page.
            </p>
            <p>
              You are advised to review this Cookie Policy periodically for any changes. Changes to this Cookie Policy are effective when they are posted on this page.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-white mb-4">Contact Us</h2>
            <p>
              If you have any questions about our Cookie Policy, please contact us at
            </p>
          </section>
        </div>
      </main>
      
      <Footer />
    </div>
  );
};

export default Cookies; 
// app/privacy/page.tsx
"use client";

import React from "react";
import Link from "next/link";

const InteliaLogo = ({ className = "w-8 h-8" }: { className?: string }) => (
  <img src="/images/favicon.png" alt="Intelia Logo" className={className} />
);

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <Link
              href="/"
              className="flex items-center space-x-3 hover:opacity-80 transition-opacity"
            >
              <InteliaLogo className="w-8 h-8" />
              <span className="text-xl font-bold text-gray-900">
                Intelia Cognito
              </span>
            </Link>
            <Link
              href="/chat"
              className="text-blue-600 hover:text-blue-700 font-medium transition-colors"
            >
              Back to Chat
            </Link>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow-sm border p-4 sm:p-6 lg:p-8">
          <div className="prose prose-gray max-w-none">
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-8">
              PRIVACY POLICY - INTELIA TECHNOLOGIES
            </h1>

            <p className="text-sm text-gray-500 mb-8">
              <strong>Last Updated:</strong> August 14, 2025
            </p>

            <div className="space-y-8">
              <section>
                <p className="text-gray-700 leading-relaxed">
                  Intelia Technologies Inc. ("Intelia," "we," "us," or "our") is
                  committed to protecting your privacy and handling your
                  personal information responsibly. This Privacy Policy explains
                  how we collect, use, disclose, and protect your personal
                  information when you use our artificial intelligence services,
                  website, and related applications (collectively, the
                  "Services").
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  SCOPE AND APPLICATION
                </h2>
                <p className="text-gray-700 leading-relaxed mb-4">
                  This Privacy Policy applies to the personal information we
                  collect when you use our Services as an individual user, visit
                  our website, or interact with us in any other way.
                </p>

                <div className="bg-blue-50 border-l-4 border-blue-400 p-4 my-6">
                  <p className="text-blue-800 font-semibold mb-2">
                    Important Note for Business Users:
                  </p>
                  <p className="text-blue-700 text-sm">
                    This Privacy Policy does not apply to personal information
                    that we process on behalf of business customers who use our
                    enterprise services, API services, or other business
                    offerings. In those cases, we act as a data processor, and
                    the business customer acts as the data controller. Our use
                    of such data is governed by our customer agreements,
                    including our Data Processing Addendum (DPA), which covers
                    access to and use of those business offerings.
                  </p>
                </div>

                <p className="text-gray-700 leading-relaxed mb-4">
                  If you use our Services through your employer or organization
                  (such as via a business account), your use may be subject to
                  different data handling terms established by your
                  organization. Please refer to your organization's privacy
                  policies and our business customer agreements for additional
                  information.
                </p>

                <p className="text-gray-700 leading-relaxed">
                  By using our Services as an individual user, you agree to the
                  collection, use, and disclosure of your personal information
                  as described in this Privacy Policy.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  1. INFORMATION WE COLLECT
                </h2>

                <p className="text-gray-700 mb-4">
                  We collect personal information in the following ways:
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">
                  1.1 Information You Provide to Us
                </h3>

                <div className="space-y-4">
                  <div>
                    <h4 className="text-lg font-medium text-gray-900 mb-2">
                      Account Information:
                    </h4>
                    <p className="text-gray-700">
                      When you create an account, we collect information such as
                      your name, email address, and password.
                    </p>
                  </div>

                  <div>
                    <h4 className="text-lg font-medium text-gray-900 mb-2">
                      Input Content:
                    </h4>
                    <p className="text-gray-700">
                      We collect the text, prompts, questions, and other content
                      you submit to our AI Services ("Inputs"). This includes
                      data communicated while using the service.
                    </p>
                  </div>

                  <div>
                    <h4 className="text-lg font-medium text-gray-900 mb-2">
                      Communication Information:
                    </h4>
                    <p className="text-gray-700">
                      When you contact us for support or other purposes, we
                      collect your contact information and the content of your
                      communications.
                    </p>
                  </div>

                  <div>
                    <h4 className="text-lg font-medium text-gray-900 mb-2">
                      Payment Information:
                    </h4>
                    <p className="text-gray-700">
                      If you purchase our paid services, we collect limited
                      billing information, including your name and billing
                      address. Payment transactions are processed securely by
                      trusted third-party payment processors. Intelia does not
                      collect or store your complete payment card details.
                      Third-party processors handle the secure transmission,
                      processing, and storage of payment data in compliance with
                      applicable industry standards (such as PCI DSS).
                    </p>
                  </div>
                </div>

                <h3 className="text-xl font-semibold text-gray-900 mb-3 mt-8">
                  1.2 Information We Collect Automatically
                </h3>

                <div className="space-y-4">
                  <div>
                    <h4 className="text-lg font-medium text-gray-900 mb-2">
                      Usage Data:
                    </h4>
                    <p className="text-gray-700">
                      We collect information about how you use our Services,
                      including the dates and times of access, features used,
                      interactions with our AI models, the time spent on each
                      page, the path taken within the application, and other
                      parameters related to your usage patterns.
                    </p>
                  </div>

                  <div>
                    <h4 className="text-lg font-medium text-gray-900 mb-2">
                      Device Information:
                    </h4>
                    <p className="text-gray-700">
                      We collect information about your device, including device
                      type, operating system, browser type and features, IP
                      addresses or domain names, unique device identifiers, and
                      general location information derived from your IP address.
                    </p>
                  </div>

                  <div>
                    <h4 className="text-lg font-medium text-gray-900 mb-2">
                      Log Information:
                    </h4>
                    <p className="text-gray-700">
                      We maintain system logs that record interaction with our
                      Services, including error reports, performance data,
                      server response codes, and other technical information for
                      operation and maintenance purposes.
                    </p>
                  </div>

                  <div>
                    <h4 className="text-lg font-medium text-gray-900 mb-2">
                      Trackers and Similar Technologies:
                    </h4>
                    <p className="text-gray-700">
                      We use cookies, unique identifiers, web beacons, embedded
                      scripts, and other tracking technologies (collectively
                      referred to as "Trackers") to enhance our Services and
                      improve your user experience. You can control cookies
                      through your browser settings.
                    </p>
                  </div>
                </div>

                <h3 className="text-xl font-semibold text-gray-900 mb-3 mt-8">
                  1.3 AI-Generated Content
                </h3>

                <div>
                  <h4 className="text-lg font-medium text-gray-900 mb-2">
                    Outputs:
                  </h4>
                  <p className="text-gray-700">
                    Our AI Services generate responses based on your Inputs
                    ("Outputs"). While you retain ownership of your Outputs, we
                    may process this information as described in this policy.
                  </p>
                </div>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  2. HOW WE USE YOUR INFORMATION
                </h2>

                <p className="text-gray-700 mb-4">
                  We use your personal information for the following purposes:
                </p>

                <div className="space-y-6">
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-3">
                      2.1 Service Provision
                    </h3>
                    <ul className="list-disc pl-6 text-gray-700 space-y-1">
                      <li>To provide, maintain, and improve our AI Services</li>
                      <li>
                        To process your requests and generate AI responses
                      </li>
                      <li>
                        To manage your account and provide customer support
                      </li>
                      <li>To process payments and manage billing</li>
                    </ul>
                  </div>

                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-3">
                      2.2 Service Improvement
                    </h3>
                    <ul className="list-disc pl-6 text-gray-700 space-y-1">
                      <li>
                        To analyze usage patterns and improve our Services
                      </li>
                      <li>To develop new features and capabilities</li>
                      <li>
                        To enhance the performance and accuracy of our AI models
                      </li>
                      <li>To ensure the safety and security of our Services</li>
                    </ul>
                  </div>

                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-3">
                      2.3 Communication
                    </h3>
                    <ul className="list-disc pl-6 text-gray-700 space-y-1">
                      <li>To respond to your inquiries and provide support</li>
                      <li>
                        To send you important service announcements and updates
                      </li>
                      <li>
                        To notify you about changes to our Services or policies
                      </li>
                    </ul>
                  </div>

                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-3">
                      2.4 Legal and Safety
                    </h3>
                    <ul className="list-disc pl-6 text-gray-700 space-y-1">
                      <li>To comply with applicable laws and regulations</li>
                      <li>
                        To protect against fraud, abuse, and security threats
                      </li>
                      <li>
                        To enforce our Terms of Service and other agreements
                      </li>
                      <li>
                        To protect the rights, property, and safety of Intelia,
                        our users, and others
                      </li>
                    </ul>
                  </div>

                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-3">
                      2.5 Model Training and Improvement
                    </h3>
                    <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                      <p className="text-yellow-800 font-semibold mb-2">
                        Important:
                      </p>
                      <p className="text-yellow-700 text-sm mb-2">
                        We do not use your Inputs or Outputs to train our AI
                        models without your explicit consent, except in the
                        following limited circumstances:
                      </p>
                      <ul className="list-disc pl-6 text-yellow-700 text-sm space-y-1">
                        <li>When content is flagged for safety review</li>
                        <li>
                          When you explicitly provide feedback or report issues
                        </li>
                        <li>
                          When you explicitly opt-in to help improve our
                          Services
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  3. HOW WE SHARE YOUR INFORMATION
                </h2>

                <p className="text-gray-700 mb-4">
                  We may share your personal information in the following
                  circumstances:
                </p>

                <div className="space-y-6">
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-3">
                      3.1 Service Providers
                    </h3>
                    <p className="text-gray-700 mb-2">
                      We may share your information with trusted third-party
                      service providers who assist us in operating our Services,
                      such as:
                    </p>
                    <ul className="list-disc pl-6 text-gray-700 space-y-1">
                      <li>Cloud hosting and data storage providers</li>
                      <li>Payment processors</li>
                      <li>Customer support platforms</li>
                      <li>Analytics and monitoring services</li>
                      <li>Platform services and hosting providers</li>
                      <li>Tag management services</li>
                    </ul>
                    <p className="text-gray-700 mt-2">
                      These service providers are contractually obligated to
                      protect your information and use it only for the purposes
                      specified by us.
                    </p>
                  </div>

                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-3">
                      3.2 Legal Requirements
                    </h3>
                    <p className="text-gray-700 mb-2">
                      We may disclose your information when required by law or
                      in response to:
                    </p>
                    <ul className="list-disc pl-6 text-gray-700 space-y-1">
                      <li>
                        Valid legal process, such as a court order or subpoena
                      </li>
                      <li>Government requests by applicable law</li>
                      <li>
                        Situations involving potential threats to public safety
                      </li>
                      <li>Protection of our legal rights and property</li>
                    </ul>
                  </div>

                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-3">
                      3.3 Business Transfers
                    </h3>
                    <p className="text-gray-700">
                      In the event of a merger, acquisition, or sale of our
                      business, your information may be transferred to the new
                      entity, subject to the same level of protection for your
                      privacy.
                    </p>
                  </div>

                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-3">
                      3.4 Third-Party Data Responsibility
                    </h3>
                    <p className="text-gray-700">
                      You are responsible for any third-party personal data
                      obtained, published, or shared through our Services, and
                      you confirm that you have received the third party's
                      consent to provide such data to us.
                    </p>
                  </div>

                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-3">
                      3.5 Consent
                    </h3>
                    <p className="text-gray-700">
                      We may share your information with your explicit consent
                      or as directed by you.
                    </p>
                  </div>
                </div>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  4. DATA RETENTION
                </h2>

                <p className="text-gray-700 mb-4">
                  We retain your personal information for as long as necessary
                  to provide our Services and fulfill the purposes described in
                  this Privacy Policy.
                </p>

                <div className="bg-gray-50 p-4 rounded-lg mb-4">
                  <p className="font-semibold text-gray-900 mb-2">
                    General Principle:
                  </p>
                  <p className="text-gray-700 text-sm">
                    Personal data shall be processed and stored for as long as
                    required by the purpose for which they have been collected.
                  </p>
                </div>

                <p className="text-gray-700 mb-4">
                  Specific retention periods include:
                </p>

                <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
                  <li>
                    <strong>Personal Data for Contract Performance:</strong>{" "}
                    Retained until the contract between us and you has been
                    fully performed
                  </li>
                  <li>
                    <strong>Personal Data for Legitimate Interests:</strong>{" "}
                    Retained as long as needed to fulfill such purposes
                  </li>
                  <li>
                    <strong>Account Information:</strong> Retained while your
                    account is active and for a reasonable period thereafter
                  </li>
                  <li>
                    <strong>Inputs and Outputs:</strong> Stored according to
                    your account settings and our data retention policies
                  </li>
                  <li>
                    <strong>Usage and Log Data:</strong> Typically retained for
                    up to 24 months for security and service improvement
                    purposes
                  </li>
                  <li>
                    <strong>Communication Records:</strong> Retained for
                    customer service and legal compliance purposes
                  </li>
                </ul>

                <div className="space-y-4">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      Extended Retention:
                    </h3>
                    <p className="text-gray-700 mb-2">
                      We may retain personal data for a longer period when:
                    </p>
                    <ul className="list-disc pl-6 text-gray-700 space-y-1">
                      <li>
                        You have given consent to such processing, as long as
                        such consent is not withdrawn
                      </li>
                      <li>
                        Required to do so for the performance of a legal
                        obligation or upon order of an authority
                      </li>
                      <li>
                        Necessary to protect our rights and interests or those
                        of our users or third parties
                      </li>
                    </ul>
                  </div>

                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      Data Deletion:
                    </h3>
                    <p className="text-gray-700 mb-2">
                      Once the retention period expires, personal data shall be
                      deleted. Therefore, the rights of access, erasure,
                      rectification, and data portability cannot be enforced
                      after the expiration of the retention period.
                    </p>
                    <p className="text-gray-700">
                      You can delete individual conversations and manage your
                      data through your account settings. When you delete your
                      account, we will delete or anonymize your personal
                      information, except as required for legal compliance or
                      legitimate business purposes.
                    </p>
                  </div>
                </div>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  5. YOUR PRIVACY RIGHTS
                </h2>

                <p className="text-gray-700 mb-4">
                  Depending on your location, you may have certain rights
                  regarding your personal information:
                </p>

                <div className="space-y-4">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      5.1 Access and Portability
                    </h3>
                    <p className="text-gray-700">
                      You can access and download your personal information
                      through your account settings.
                    </p>
                  </div>

                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      5.2 Correction
                    </h3>
                    <p className="text-gray-700">
                      You can update or correct your personal information
                      through your account settings or by contacting us.
                    </p>
                  </div>

                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      5.3 Deletion
                    </h3>
                    <p className="text-gray-700">
                      You can delete your conversations, account, and associated
                      data, subject to certain exceptions for legal compliance.
                    </p>
                  </div>

                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      5.5 Object to Processing
                    </h3>
                    <p className="text-gray-700">
                      You have the right to object to the processing of your
                      data, particularly when processing is based on legitimate
                      interests. You can object to processing at any time
                      without needing to justify why your data is being
                      processed for direct marketing purposes.
                    </p>
                  </div>

                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      5.6 Lodge a Complaint
                    </h3>
                    <p className="text-gray-700">
                      You have the right to bring a claim before your competent
                      data protection authority.
                    </p>
                  </div>

                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      5.7 Exercise Your Rights
                    </h3>
                    <p className="text-gray-700">
                      To exercise these rights, please contact us at{" "}
                      <a
                        href="mailto:confidentialite@intelia.com"
                        className="text-blue-600 hover:text-blue-700 underline"
                      >
                        confidentialite@intelia.com
                      </a>{" "}
                      or{" "}
                      <a
                        href="https://intelia.com/contact-2/"
                        className="text-blue-600 hover:text-blue-700 underline"
                      >
                        https://intelia.com/contact-2/
                      </a>
                      . Any requests to exercise your rights can be made free of
                      charge and will be addressed by us as early as possible
                      and always within one month. We will respond to your
                      request within a reasonable timeframe, as required by
                      applicable law.
                    </p>
                  </div>
                </div>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  6. DATA SECURITY
                </h2>

                <p className="text-gray-700 mb-4">
                  We implement appropriate technical, administrative, and
                  physical security measures to protect your personal
                  information against unauthorized access, disclosure,
                  alteration, and destruction. These measures include:
                </p>

                <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-4">
                  <li>Encryption of data in transit and at rest</li>
                  <li>Access controls and authentication systems</li>
                  <li>Regular security assessments and monitoring</li>
                  <li>Employee training on data protection practices</li>
                </ul>

                <p className="text-gray-700 mb-4">
                  Additionally, third-party payment processors engaged to handle
                  billing and payment transactions implement their own security
                  and compliance programs, including certification under the
                  Payment Card Industry Data Security Standard (PCI DSS), to
                  protect sensitive payment information.
                </p>

                <p className="text-gray-700">
                  However, no method of transmission or storage is completely
                  secure, and we cannot guarantee absolute security.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  7. INTERNATIONAL DATA TRANSFERS
                </h2>

                <p className="text-gray-700 mb-4">
                  Our Services are provided from Canada, and your personal
                  information may be processed and stored in Canada or other
                  countries where we or our service providers operate. This
                  includes situations where third-party payment processors
                  manage billing and payment transactions, which may involve
                  processing and storing payment information in jurisdictions
                  outside your country of residence.
                </p>

                <p className="text-gray-700 mb-4">
                  For users in the European Economic Area (EEA), Switzerland, or
                  the United Kingdom, we ensure that any international transfers
                  of personal information are conducted with appropriate
                  safeguards, such as:
                </p>

                <ul className="list-disc pl-6 text-gray-700 space-y-2">
                  <li>Adequacy decisions by the European Commission</li>
                  <li>
                    Standard contractual clauses approved by the European
                    Commission
                  </li>
                  <li>Other legally recognized transfer mechanisms</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  8. CHANGES TO THIS PRIVACY POLICY
                </h2>

                <p className="text-gray-700">
                  We may update this Privacy Policy from time to time to reflect
                  changes in our practices, Services, or applicable law. We will
                  notify you of material changes by posting the updated policy
                  on our website and updating the "Last Updated" date. We
                  encourage you to review this Privacy Policy periodically.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  9. CANADIAN PRIVACY LAW COMPLIANCE
                </h2>

                <p className="text-gray-700 mb-4">
                  For users in Canada, we comply with applicable Canadian
                  privacy laws, including:
                </p>

                <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
                  <li>
                    The Personal Information Protection and Electronic Documents
                    Act (PIPEDA)
                  </li>
                  <li>
                    Quebec's Act respecting the protection of personal
                    information in the private sector
                  </li>
                  <li>Other applicable provincial privacy legislation</li>
                </ul>

                <div className="space-y-4">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      9.1 Consent
                    </h3>
                    <p className="text-gray-700">
                      We obtain your consent for the collection, use, and
                      disclosure of your personal information as required by
                      law. You may withdraw your consent at any time, subject to
                      any applicable legal or contractual restrictions.
                    </p>
                  </div>

                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      9.2 Privacy Officer
                    </h3>
                    <p className="text-gray-700">
                      We have appointed a Privacy Officer who is responsible for
                      ensuring compliance with privacy laws and handling
                      privacy-related inquiries.
                    </p>
                  </div>
                </div>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  10. CONTACT US
                </h2>

                <p className="text-gray-700 mb-4">
                  If you have questions, concerns, or complaints about this
                  Privacy Policy or our privacy practices, please get in touch
                  with us:
                </p>

                <div className="bg-gray-50 p-6 rounded-lg">
                  <p className="font-semibold text-gray-900 mb-2">
                    Intelia Technologies Inc.
                  </p>
                  <p className="text-gray-700 mb-1">839 Rue Papineau</p>
                  <p className="text-gray-700 mb-1">Joliette, QC J6E 2L6</p>
                  <p className="text-gray-700 mb-3">Canada</p>

                  <div className="space-y-1">
                    <p className="text-gray-700">
                      <span className="font-medium">Owner contact email:</span>{" "}
                      <a
                        href="mailto:confidentialite@intelia.com"
                        className="text-blue-600 hover:text-blue-700 underline"
                      >
                        confidentialite@intelia.com
                      </a>
                    </p>
                    <p className="text-gray-700">
                      <span className="font-medium">Contact:</span>{" "}
                      <a
                        href="https://intelia.com/contact-2/"
                        className="text-blue-600 hover:text-blue-700 underline"
                      >
                        https://intelia.com/contact-2/
                      </a>
                    </p>
                  </div>
                </div>

                <div className="bg-blue-50 border-l-4 border-blue-400 p-4 mt-6">
                  <p className="text-blue-800 text-sm">
                    <span className="font-semibold">For users in Canada:</span>{" "}
                    If you are not satisfied with our response to your privacy
                    concern, you may file a complaint with the Office of the
                    Privacy Commissioner of Canada or your applicable provincial
                    privacy commissioner.
                  </p>
                </div>

                <p className="text-sm text-gray-500 mt-6">
                  <span className="font-semibold">Legal Information:</span> This
                  privacy statement has been prepared in accordance with the
                  provisions of multiple legislations, including Article 13/14
                  of Regulation (EU) 2016/679 (General Data Protection
                  Regulation) and applicable Canadian privacy laws.
                </p>

                <p className="text-sm text-gray-500 mt-4 italic">
                  This Privacy Policy is effective as of August 14, 2025, and
                  supersedes all prior agreements and understandings, whether
                  written or oral, between the parties.
                </p>
              </section>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

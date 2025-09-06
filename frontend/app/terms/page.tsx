'use client'

import React from 'react'
import Link from 'next/link'

const InteliaLogo = ({ className = 'w-8 h-8' }: { className?: string }) => (
  <img src="/images/favicon.png" alt="Intelia Logo" className={className} />
)

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <Link href="/" className="flex items-center space-x-3 hover:opacity-80 transition-opacity">
              <InteliaLogo className="w-8 h-8" />
              <span className="text-xl font-bold text-gray-900">Intelia Expert</span>
            </Link>
            <Link href="/" className="text-blue-600 hover:text-blue-700 font-medium transition-colors">
              Back to Home
            </Link>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow-sm border p-8">
          <div className="prose prose-gray max-w-none">
            <h1 className="text-3xl font-bold text-gray-900 mb-8">TERMS OF SERVICE - INTELIA TECHNOLOGIES</h1>

            <p className="text-sm text-gray-500 mb-8">
              <strong>Last Updated:</strong> August 14, 2025
            </p>

            <div className="space-y-8">
              <section>
                <p className="text-gray-700 leading-relaxed">
                  These Terms of Service ("Terms") constitute an agreement between Intelia Technologies Inc., a corporation duly incorporated under the Business Corporations Act (Quebec), having its head office at 839 Papineau, Joliette, Québec J6E 2L6, Canada ("Intelia Expert," "we," "us," or "our") and you ("User" or "you") regarding your use of our artificial intelligence services, platform, and related tools (collectively, the "Services").
                </p>
                <p className="text-gray-700 leading-relaxed mt-4">
                  By using our Services, clicking "I Accept," or otherwise indicating your consent, you agree to be bound by these Terms. If you do not agree to any part of these Terms, please discontinue use of our Services immediately.
                </p>
              </section>

              {/* 1. SERVICES */}
              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">1. SERVICES</h2>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">1.1 Overview</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  Subject to these Terms, we grant you permission to access and use our AI-powered Services for your intended purposes. Our Services include AI models, chat interfaces, content generation tools, and related features.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">1.2 Service Evolution</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  As AI technology continues to evolve, we reserve the right to add, modify, suspend, or discontinue our Services. If such changes materially affect your rights, we will notify you through platform notifications, website announcements, or email.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">1.3 Availability</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  We make no warranty that the Services are available in all jurisdictions. Service features may vary by region.
                </p>
              </section>

              {/* 2. USER ACCOUNTS */}
              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">2. USER ACCOUNTS</h2>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">2.1 Registration</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  You must provide accurate and complete information when creating an account and keep this information updated.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">2.2 Account Security</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  You are responsible for maintaining the security of your account credentials and for all activities that occur under your account. You must immediately notify us of any suspected compromise.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">2.3 Organizational Authority</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  If you are using the Services on behalf of an organization, you must have the authority to bind that organization to these Terms.
                </p>
              </section>

              {/* 3. ACCEPTABLE USE */}
              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">3. ACCEPTABLE USE</h2>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">3.1 Content Responsibility</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  You are responsible for all content you input into our Services ("Input") and must ensure it complies with these Terms and applicable laws. You represent and warrant that you have all necessary rights to provide such Input to our Services.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">3.2 Prohibited Uses</h3>
                <p className="text-gray-700 leading-relaxed mb-2">You may not use our Services to:</p>
                <ul className="list-disc pl-6 text-gray-700 space-y-2">
                  <li>Engage in illegal activities or harm others</li>
                  <li>Infringe upon intellectual property rights</li>
                  <li>Generate harmful, abusive, or discriminatory content</li>
                  <li>Attempt to reverse engineer or duplicate our Services</li>
                  <li>Circumvent our safety measures or content policies</li>
                  <li>Use the Services to compete directly with us</li>
                </ul>

                <h3 className="text-xl font-semibold text-gray-900 mb-3 mt-6">3.3 Compliance</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  Each party will comply with all applicable laws regarding the provision of the Services (for Intelia Technologies) and the use of the Services (for the User), including any relevant data privacy laws and regulations.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">3.4 Policies and Service Terms</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  You may only use the Services in compliance with these Terms, including our Usage Policy and any Service Specific Terms, each of which is incorporated by reference into these Terms. You must cooperate with reasonable requests for information from Intelia Technologies to support compliance with our policies, including to verify your identity and use of the Services.
                </p>
              </section>

              {/* 4. CONTENT AND INTELLECTUAL PROPERTY */}
              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">4. CONTENT AND INTELLECTUAL PROPERTY</h2>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">4.1 Your Content</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  You retain ownership of your Input. By using our Services, you represent that you have all necessary rights to provide such Input.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">4.2 Generated Content</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  Subject to these Terms and applicable law, you own the output generated by our Services in response to your Input ("Output"). However, you acknowledge that similar or identical Output may be generated for other users.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">4.3 Our Intellectual Property</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  We retain all rights to our Services, including our AI models, algorithms, software, and platform. These Terms do not grant you any ownership rights in our intellectual property.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">4.4 Content Accuracy</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  AI-generated content may not always be accurate, complete, or up-to-date. You should verify important information independently before relying on it.
                </p>
              </section>

              {/* 5. PRIVACY AND DATA */}
              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">5. PRIVACY AND DATA</h2>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">5.1 Privacy Policy</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  Your use of our Services is governed by our <Link href="/privacy" className="text-blue-600 hover:text-blue-700 underline">Privacy Policy</Link>, which explains how we collect, use, and protect your personal information.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">5.2 Data Processing</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  We process your data in accordance with applicable Canadian privacy laws, including Quebec's Act respecting the protection of personal information in the private sector, as well as other relevant data protection laws, such as the GDPR and CCPA.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">5.3 Data Protection Compliance</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  All client and prospect data collected, used, shared, or stored as part of this agreement must comply with applicable data protection laws. You agree to ensure that all data is collected with proper consent and acknowledge our right to communicate with you for service-related purposes, as required by applicable data protection and privacy laws.
                </p>
              </section>

              {/* 6. FEES AND PAYMENT */}
              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">6. FEES AND PAYMENT</h2>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">6.1 Pricing</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  Fees for our Services, if any, will be displayed on our platform. We reserve the right to modify pricing with reasonable notice.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">6.2 Billing Terms</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  Billing begins on the activation date of the user’s plan (“Activation Date”). The customer is charged immediately for the upcoming month. Each billing cycle covers a monthly period starting and ending on the anniversary date of the Activation Date.
                </p>
                <p className="text-gray-700 leading-relaxed mb-4">
                  For example, if the Activation Date is the 15th of a month, the billing cycle runs from the 15th to the 14th of the following month. If a month does not contain the same calendar date (e.g., activation on the 31st), the billing cycle will end on the last day of that month.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">6.3 Invoice Format</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  All invoices are issued electronically only (sent by email or made available through the user account). Paper invoices will not be provided, except where required by applicable law.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">6.4 Payment Methods</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  Payments must be made by credit card, bank transfer, or any other method specified on our platform. The registered payment method will be automatically charged on each billing anniversary date, unless the subscription is canceled in accordance with these Terms.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">6.5 Payment Processing with Stripe</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  We use <a href="https://stripe.com/legal" className="text-blue-600 hover:text-blue-700 underline" target="_blank" rel="noreferrer">Stripe</a> and <a href="https://stripe.com/privacy" className="text-blue-600 hover:text-blue-700 underline" target="_blank" rel="noreferrer">Link by Stripe</a> as our third-party payment processors. By providing your payment information, you consent to Stripe processing such data in accordance with its Services Agreement and Privacy Policy.
                </p>
                <p className="text-gray-700 leading-relaxed mb-4">
                  We do not collect or store your complete payment card details. Stripe handles the secure transmission and storage of payment information in compliance with the Payment Card Industry Data Security Standard (PCI DSS). We may receive limited billing details (e.g., name, billing address) necessary to fulfill the transaction and provide customer support.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">6.6 Refund Policy</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  Unless otherwise required by applicable law or expressly stated, all payments are non-refundable. Where a statutory right of withdrawal applies (e.g., a 14-day withdrawal period for consumers), any refund will cover only the unused portion of the service, minus any applicable activation or setup fees.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">6.7 Auto-Renewal</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  Subscriptions automatically renew for successive periods of the same duration (monthly or annual, depending on the chosen plan) at the rates in effect at the time of renewal. Customers may turn off auto-renewal at any time through their account settings or by providing written notice to Intelia Technologies at least fifteen (15) days before the renewal date.
                </p>
              </section>

              {/* 7. DISCLAIMERS AND LIMITATIONS */}
              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">7. DISCLAIMERS AND LIMITATIONS</h2>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">7.1 Service Availability</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  Our Services are provided "as is" and "as available." We do not guarantee uninterrupted or error-free service.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">7.2 Disclaimers</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  TO THE MAXIMUM EXTENT PERMITTED BY LAW, WE DISCLAIM ALL WARRANTIES, EXPRESS OR IMPLIED, INCLUDING WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">7.3 Limitation of Liability</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, OUR TOTAL LIABILITY FOR ANY DAMAGES ARISING FROM THESE TERMS OR YOUR USE OF THE SERVICES SHALL NOT EXCEED THE AMOUNT YOU PAID US IN THE TWELVE MONTHS PRECEDING THE CLAIM.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">7.4 Exclusion of Damages</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  WE SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING LOSS OF PROFITS OR DATA.
                </p>
              </section>

              {/* 8. INDEMNIFICATION */}
              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">8. INDEMNIFICATION</h2>
                <p className="text-gray-700 leading-relaxed mb-4">
                  You agree to indemnify and hold us harmless from any claims, damages, losses, and expenses (including reasonable attorney fees) arising from your use of the Services, violation of these Terms, or infringement of any third-party rights.
                </p>
              </section>

              {/* 9. TERM AND TERMINATION */}
              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">9. TERM AND TERMINATION</h2>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">9.1 Term</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  These Terms remain in effect as long as you use our Services.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">9.2 Termination</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  Either party may terminate these Terms at any time. We reserve the right to suspend or terminate your access immediately if you violate these Terms.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">9.3 Effect of Termination</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  Upon termination, your right to use the Services ceases immediately. Provisions regarding intellectual property, disclaimers, limitations of liability, and governing law shall survive the termination of this agreement.
                </p>
              </section>

              {/* 10. GOVERNING LAW AND DISPUTES */}
              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">10. GOVERNING LAW AND DISPUTES</h2>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">10.1 Governing Law</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  This Agreement shall be governed, interpreted, construed, and enforced by the laws in force in the Province of Quebec and the federal laws of Canada applicable therein, without regard to conflict of law principles.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">10.2 Arbitration</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  Except for the right of either party to apply to a court of competent jurisdiction for a Temporary Restraining Order, Preliminary Injunction, or other equitable relief to preserve the status quo or prevent irreparable harm pending the selection and confirmation of the arbitrator, any disputes, controversies, or claims arising out of or relating to this Agreement or a breach thereof shall be submitted to and finally resolved by arbitration in Montreal, Canada under the rules of the Canadian Commercial Arbitration Center ("CCAC") then in effect. There shall be a single arbitrator, who shall be chosen by mutual agreement of the Parties or in accordance with the CCAC rules. The arbitrator's findings shall be final and binding on the Parties and may be entered in any court of competent jurisdiction for enforcement. Legal fees may be awarded to the prevailing party in the arbitration.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">10.3 Waiver of Jury Trial</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  Each party knowingly, voluntarily, and intentionally waives its right to a trial by jury in any litigation arising out of or relating to this Agreement and the transactions it contemplates. This waiver applies to any litigation, whether sounding in contract, tort, or otherwise.
                </p>
              </section>

              {/* 11. GENERAL PROVISIONS */}
              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">11. GENERAL PROVISIONS</h2>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">11.1 Interpretation</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  The Parties hereto hereby declare that they intend the provisions of this Agreement to apply fairly and without detriment to the interests of any of them, and agree to use their best endeavors to give effect to this Agreement in the spirit in which it was decided. The Parties have participated jointly in the negotiation and drafting of this Agreement. If an ambiguity, question of intent, or interpretation arises, this Agreement shall be construed as if drafted jointly by the Parties, and no presumption or burden of proof shall arise favoring or disfavoring any party based on the authorship of any provision of this Agreement.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">11.2 Entire Agreement</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  These Terms, together with our Privacy Policy and any other policies referenced herein, constitute the entire agreement between you and us and merge, supersede, and cancel all prior discussions, representations, inducements, promises, undertakings, understandings, agreements, or otherwise, whether oral, in writing, or otherwise, between the Parties concerning such subject matter.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">11.3 Modifications</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  We reserve the right to update these Terms from time to time. Material changes will be communicated with reasonable notice. This Agreement cannot be modified or varied by any oral agreement or representation, except in writing, executed by both Parties, which identifies itself as an amendment to this Agreement. Continued use of our Services after changes indicates acceptance of the updated Terms.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">11.4 Severability</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  Suppose any term or other provision of this Agreement is invalid, illegal, or incapable of being enforced by any rule, law, or public policy. In that case, all other conditions and provisions of this Agreement shall remain in full force and effect, so long as the economic or legal substance of the transactions contemplated hereby is not materially adversely affected in any manner by any party.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">11.5 Assignment</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  You may not assign these Terms without our written consent. We may assign these Terms without restriction, and this Agreement shall inure to the benefit of and be binding upon the heirs, executors, administrators, permitted successors, and permitted assigns of the Parties.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">11.6 Independent Contractors</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  Each party is an independent contractor and does not have any power (nor will it represent itself as having any power) to in any way enter into commitments or contracts, assume obligations, give any warranties, make any representation, or incur liability of any kind in the name of the other party or on behalf of the other party. Nothing in this Agreement shall be construed to create a relationship of partners, joint venturers, fiduciaries, master-servants, agencies, or other similar relationships between the Parties.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">11.7 Waiver of Default</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  No failure or delay (i) in exercising any right or remedy, or (ii) in requiring the satisfaction of any condition under this Agreement, and no act, omission, or course of dealing between the Parties operates as a waiver or estoppel of any right, remedy, or condition. A waiver made in writing on one occasion is effective only in that instance and only for the purpose stated.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">11.8 Force Majeure</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  If the performance of any of the obligations contained in this Agreement is delayed, prevented, restricted, or otherwise hindered by legislative action, an act of God, the action of the elements, serious fire, labor disturbance, delays in transportation, shortage of materials or supplies, government restrictions, war, riots, flood, earthquake, epidemic or other conditions beyond the control of either party, performance hereunder by such party, to the extent so hindered, shall be excused.
                </p>

                <h3 className="text-xl font-semibold text-gray-900 mb-3">11.9 Costs</h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                  Each party shall be responsible for its own costs, including the fees of attorneys, accountants, or consultants, incurred in carrying out the activities contemplated by this Agreement.
                </p>
              </section>

              {/* 12. CONTACT INFORMATION */}
              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">12. CONTACT INFORMATION</h2>
                <p className="text-gray-700 leading-relaxed mb-4">
                  If you have questions about these Terms or need to contact us regarding our Services, please reach out to us at:
                </p>

                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="font-semibold text-gray-900">Intelia Technologies Inc.</p>
                  <p className="text-gray-700">Address: 839 Papineau, Joliette, Québec J6E 2L6, Canada</p>
                  <p className="text-gray-700">
                    Contact:{' '}
                    <a href="https://intelia.com/contact-2/" className="text-blue-600 hover:text-blue-700 underline" target="_blank" rel="noreferrer">
                      https://intelia.com/contact-2/
                    </a>
                  </p>
                </div>

                <p className="text-sm text-gray-500 mt-6 italic">
                  These Terms of Service are effective as of August 14, 2025, and supersede all prior agreements and understandings, whether written or oral, between the parties.
                </p>
              </section>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

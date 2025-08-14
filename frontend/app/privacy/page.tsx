// app/privacy/page.tsx
'use client'

import React from 'react'
import Link from 'next/link'

const InteliaLogo = ({ className = "w-8 h-8" }: { className?: string }) => (
  <img 
    src="/images/favicon.png" 
    alt="Intelia Logo" 
    className={className}
  />
)

export default function PrivacyPage() {
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
            <Link 
              href="/" 
              className="text-blue-600 hover:text-blue-700 font-medium transition-colors"
            >
              Retour à l'accueil
            </Link>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow-sm border p-8">
          <div className="prose prose-gray max-w-none">
            <h1 className="text-3xl font-bold text-gray-900 mb-8">Politique de confidentialité</h1>
            
            <p className="text-sm text-gray-500 mb-8">
              <strong>Dernière mise à jour :</strong> 14 août 2025
            </p>

            <div className="space-y-8">
              <section>
                <p className="text-gray-700 leading-relaxed">
                  Intelia Technologies Inc. (« Intelia », « nous », « notre ») s'engage à 
                  protéger votre vie privée et à traiter vos informations personnelles de 
                  manière responsable. Cette Politique de confidentialité explique comment 
                  nous collectons, utilisons, divulguons et protégeons vos informations 
                  personnelles lorsque vous utilisez nos services d'intelligence artificielle, 
                  site Web et applications connexes (collectivement, les « Services »).
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">PORTÉE ET APPLICATION</h2>
                <p className="text-gray-700 leading-relaxed mb-4">
                  Cette Politique de confidentialité s'applique aux informations personnelles 
                  que nous collectons lorsque vous utilisez nos Services en tant qu'utilisateur 
                  individuel, visitez notre site Web ou interagissez autrement avec nous.
                </p>
                
                <div className="bg-blue-50 border-l-4 border-blue-400 p-4 my-6">
                  <p className="text-blue-800 font-semibold mb-2">Note importante pour les utilisateurs professionnels :</p>
                  <p className="text-blue-700 text-sm">
                    Cette Politique de confidentialité ne s'applique pas aux informations 
                    personnelles que nous traitons au nom de clients professionnels qui 
                    utilisent nos services d'entreprise, services API ou autres offres 
                    commerciales. Dans ces cas, nous agissons comme un responsable du 
                    traitement des données, et le client professionnel agit comme le 
                    contrôleur des données.
                  </p>
                </div>

                <p className="text-gray-700 leading-relaxed">
                  En utilisant nos Services en tant qu'utilisateur individuel, vous acceptez 
                  la collecte, l'utilisation et la divulgation de vos informations personnelles 
                  comme décrit dans cette Politique de confidentialité.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">1. INFORMATIONS QUE NOUS COLLECTONS</h2>
                
                <h3 className="text-xl font-semibold text-gray-900 mb-3">1.1 Informations que vous nous fournissez</h3>
                
                <div className="space-y-4">
                  <div>
                    <h4 className="text-lg font-medium text-gray-900 mb-2">Informations de compte :</h4>
                    <p className="text-gray-700">
                      Lorsque vous créez un compte, nous collectons des informations telles que 
                      votre nom, adresse e-mail et mot de passe.
                    </p>
                  </div>

                  <div>
                    <h4 className="text-lg font-medium text-gray-900 mb-2">Contenu d'entrée :</h4>
                    <p className="text-gray-700">
                      Nous collectons le texte, les invites, les questions et autres contenus 
                      que vous soumettez à nos Services d'IA (« Entrées »). Cela inclut les 
                      données communiquées lors de l'utilisation du service.
                    </p>
                  </div>

                  <div>
                    <h4 className="text-lg font-medium text-gray-900 mb-2">Informations de communication :</h4>
                    <p className="text-gray-700">
                      Lorsque vous nous contactez pour obtenir de l'aide ou à d'autres fins, 
                      nous collectons vos informations de contact et le contenu de vos communications.
                    </p>
                  </div>

                  <div>
                    <h4 className="text-lg font-medium text-gray-900 mb-2">Informations de paiement :</h4>
                    <p className="text-gray-700">
                      Si vous achetez nos services payants, nous collectons les informations 
                      de facturation, y compris votre nom, adresse de facturation et détails 
                      de méthode de paiement. Les processeurs de paiement tiers gèrent le 
                      traitement des paiements.
                    </p>
                  </div>
                </div>

                <h3 className="text-xl font-semibold text-gray-900 mb-3 mt-8">1.2 Informations que nous collectons automatiquement</h3>
                
                <div className="space-y-4">
                  <div>
                    <h4 className="text-lg font-medium text-gray-900 mb-2">Données d'utilisation :</h4>
                    <p className="text-gray-700">
                      Nous collectons des informations sur la façon dont vous utilisez nos 
                      Services, y compris les dates et heures d'accès, les fonctionnalités 
                      utilisées, les interactions avec nos modèles d'IA, le temps passé sur 
                      chaque page et d'autres paramètres liés à vos habitudes d'utilisation.
                    </p>
                  </div>

                  <div>
                    <h4 className="text-lg font-medium text-gray-900 mb-2">Informations sur l'appareil :</h4>
                    <p className="text-gray-700">
                      Nous collectons des informations sur votre appareil, y compris le type 
                      d'appareil, le système d'exploitation, le type et les fonctionnalités 
                      du navigateur, les adresses IP ou noms de domaine, les identifiants 
                      uniques d'appareil et les informations de localisation générale dérivées 
                      de votre adresse IP.
                    </p>
                  </div>

                  <div>
                    <h4 className="text-lg font-medium text-gray-900 mb-2">Informations de journal :</h4>
                    <p className="text-gray-700">
                      Nous maintenons des journaux système qui enregistrent l'interaction avec 
                      nos Services, y compris les rapports d'erreur, les données de performance, 
                      les codes de réponse du serveur et d'autres informations techniques pour 
                      le fonctionnement et la maintenance.
                    </p>
                  </div>

                  <div>
                    <h4 className="text-lg font-medium text-gray-900 mb-2">Trackers et technologies similaires :</h4>
                    <p className="text-gray-700">
                      Nous utilisons des cookies, identifiants uniques, balises Web, scripts 
                      intégrés et autres technologies de suivi (collectivement appelées 
                      « Trackers ») pour améliorer nos Services et votre expérience utilisateur. 
                      Vous pouvez contrôler les cookies via les paramètres de votre navigateur.
                    </p>
                  </div>
                </div>

                <h3 className="text-xl font-semibold text-gray-900 mb-3 mt-8">1.3 Contenu généré par l'IA</h3>
                
                <div>
                  <h4 className="text-lg font-medium text-gray-900 mb-2">Sorties :</h4>
                  <p className="text-gray-700">
                    Nos Services d'IA génèrent des réponses basées sur vos Entrées (« Sorties »). 
                    Bien que vous conserviez la propriété de vos Sorties, nous pouvons traiter 
                    ces informations comme décrit dans cette politique.
                  </p>
                </div>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">2. COMMENT NOUS UTILISONS VOS INFORMATIONS</h2>
                
                <p className="text-gray-700 mb-4">Nous utilisons vos informations personnelles aux fins suivantes :</p>
                
                <div className="space-y-6">
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-3">2.1 Fourniture de services</h3>
                    <ul className="list-disc pl-6 text-gray-700 space-y-1">
                      <li>Fournir, maintenir et améliorer nos Services d'IA</li>
                      <li>Traiter vos demandes et générer des réponses d'IA</li>
                      <li>Gérer votre compte et fournir un support client</li>
                      <li>Traiter les paiements et gérer la facturation</li>
                    </ul>
                  </div>

                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-3">2.2 Amélioration des services</h3>
                    <ul className="list-disc pl-6 text-gray-700 space-y-1">
                      <li>Analyser les habitudes d'utilisation et améliorer nos Services</li>
                      <li>Développer de nouvelles fonctionnalités et capacités</li>
                      <li>Améliorer les performances et la précision de nos modèles d'IA</li>
                      <li>Assurer la sécurité et la sûreté de nos Services</li>
                    </ul>
                  </div>

                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-3">2.3 Communication</h3>
                    <ul className="list-disc pl-6 text-gray-700 space-y-1">
                      <li>Répondre à vos demandes et fournir un support</li>
                      <li>Vous envoyer d'importantes annonces et mises à jour de service</li>
                      <li>Vous notifier des changements à nos Services ou politiques</li>
                    </ul>
                  </div>

                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-3">2.4 Légal et sécurité</h3>
                    <ul className="list-disc pl-6 text-gray-700 space-y-1">
                      <li>Se conformer aux lois et réglementations applicables</li>
                      <li>Protéger contre la fraude, l'abus et les menaces de sécurité</li>
                      <li>Faire respecter nos Conditions d'utilisation et autres accords</li>
                      <li>Protéger les droits, la propriété et la sécurité d'Intelia, de nos utilisateurs et d'autres</li>
                    </ul>
                  </div>

                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-3">2.5 Formation et amélioration des modèles</h3>
                    <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                      <p className="text-yellow-800 font-semibold mb-2">Important :</p>
                      <p className="text-yellow-700 text-sm">
                        Nous n'utilisons pas vos Entrées ou Sorties pour entraîner nos modèles 
                        d'IA sans votre consentement explicite, sauf dans les circonstances 
                        limitées suivantes :
                      </p>
                      <ul className="list-disc pl-6 text-yellow-700 text-sm mt-2 space-y-1">
                        <li>Lorsque le contenu est signalé pour examen de sécurité</li>
                        <li>Lorsque vous fournissez explicitement des commentaires ou signalez des problèmes</li>
                        <li>Lorsque vous optez explicitement pour aider à améliorer nos Services</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">5. VOS DROITS À LA VIE PRIVÉE</h2>
                
                <p className="text-gray-700 mb-4">
                  Selon votre emplacement, vous pouvez avoir certains droits concernant vos 
                  informations personnelles :
                </p>
                
                <div className="space-y-4">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">5.1 Accès et portabilité</h3>
                    <p className="text-gray-700">
                      Vous pouvez accéder et télécharger vos informations personnelles via les 
                      paramètres de votre compte.
                    </p>
                  </div>

                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">5.2 Correction</h3>
                    <p className="text-gray-700">
                      Vous pouvez mettre à jour ou corriger vos informations personnelles via 
                      les paramètres de votre compte ou en nous contactant.
                    </p>
                  </div>

                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">5.3 Suppression</h3>
                    <p className="text-gray-700">
                      Vous pouvez supprimer vos conversations, compte et données associées, 
                      sous réserve de certaines exceptions pour la conformité légale.
                    </p>
                  </div>

                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">5.4 Objection au traitement</h3>
                    <p className="text-gray-700">
                      Vous avez le droit de vous opposer au traitement de vos données, 
                      particulièrement lorsque le traitement est basé sur des intérêts légitimes.
                    </p>
                  </div>

                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">5.5 Déposer une plainte</h3>
                    <p className="text-gray-700">
                      Vous avez le droit de porter plainte devant votre autorité compétente 
                      de protection des données.
                    </p>
                  </div>

                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">5.6 Exercer vos droits</h3>
                    <p className="text-gray-700">
                      Pour exercer ces droits, veuillez nous contacter à{' '}
                      <a href="mailto:confidentialite@intelia.com" className="text-blue-600 hover:text-blue-700 underline">
                        confidentialite@intelia.com
                      </a>{' '}
                      ou{' '}
                      <a href="https://intelia.com/contact-2/" className="text-blue-600 hover:text-blue-700 underline">
                        https://intelia.com/contact-2/
                      </a>. 
                      Toute demande d'exercice de vos droits peut être faite gratuitement et 
                      sera traitée dans les plus brefs délais et toujours dans un délai d'un mois.
                    </p>
                  </div>
                </div>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">9. CONFORMITÉ AUX LOIS CANADIENNES SUR LA VIE PRIVÉE</h2>
                
                <p className="text-gray-700 mb-4">
                  Pour les utilisateurs au Canada, nous nous conformons aux lois canadiennes 
                  applicables sur la vie privée, y compris :
                </p>
                
                <ul className="list-disc pl-6 text-gray-700 space-y-2 mb-6">
                  <li>La Loi sur la protection des renseignements personnels et les documents électroniques (LPRPDE)</li>
                  <li>La Loi sur la protection des renseignements personnels dans le secteur privé du Québec</li>
                  <li>Autres législations provinciales applicables sur la vie privée</li>
                </ul>

                <div className="space-y-4">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">9.1 Consentement</h3>
                    <p className="text-gray-700">
                      Nous obtenons votre consentement pour la collecte, l'utilisation et la 
                      divulgation de vos informations personnelles comme requis par la loi. 
                      Vous pouvez retirer votre consentement à tout moment, sous réserve de 
                      toute restriction légale ou contractuelle applicable.
                    </p>
                  </div>

                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">9.2 Responsable de la protection de la vie privée</h3>
                    <p className="text-gray-700">
                      Nous avons nommé un Responsable de la protection de la vie privée qui 
                      est responsable d'assurer la conformité avec les lois sur la vie privée 
                      et de traiter les demandes liées à la vie privée.
                    </p>
                  </div>
                </div>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">10. NOUS CONTACTER</h2>
                
                <p className="text-gray-700 mb-4">
                  Si vous avez des questions, préoccupations ou plaintes concernant cette 
                  Politique de confidentialité ou nos pratiques de confidentialité, 
                  veuillez nous contacter :
                </p>
                
                <div className="bg-gray-50 p-6 rounded-lg">
                  <p className="font-semibold text-gray-900 mb-2">Intelia Technologies Inc.</p>
                  <p className="text-gray-700 mb-1">839 Rue Papineau</p>
                  <p className="text-gray-700 mb-1">Joliette, QC J6E 2L6</p>
                  <p className="text-gray-700 mb-3">Canada</p>
                  
                  <div className="space-y-1">
                    <p className="text-gray-700">
                      <span className="font-medium">Email du propriétaire :</span>{' '}
                      <a href="mailto:confidentialite@intelia.com" className="text-blue-600 hover:text-blue-700 underline">
                        confidentialite@intelia.com
                      </a>
                    </p>
                    <p className="text-gray-700">
                      <span className="font-medium">Contact :</span>{' '}
                      <a href="https://intelia.com/contact-2/" className="text-blue-600 hover:text-blue-700 underline">
                        https://intelia.com/contact-2/
                      </a>
                    </p>
                  </div>
                </div>
                
                <div className="bg-blue-50 border-l-4 border-blue-400 p-4 mt-6">
                  <p className="text-blue-800 text-sm">
                    <span className="font-semibold">Pour les utilisateurs au Canada :</span> Si vous 
                    n'êtes pas satisfait de notre réponse à votre préoccupation concernant la vie 
                    privée, vous pouvez déposer une plainte auprès du Commissariat à la protection 
                    de la vie privée du Canada ou de votre commissaire provincial à la protection 
                    de la vie privée applicable.
                  </p>
                </div>
                
                <p className="text-sm text-gray-500 mt-6">
                  <span className="font-semibold">Information légale :</span> Cette déclaration 
                  de confidentialité a été préparée selon les dispositions de multiples 
                  législations, y compris l'article 13/14 du Règlement (UE) 2016/679 (Règlement 
                  général sur la protection des données) et les lois canadiennes applicables 
                  sur la vie privée.
                </p>
                
                <p className="text-sm text-gray-500 mt-4 italic">
                  Cette Politique de confidentialité est effective à partir du 14 août 2025 
                  et remplace tous les accords et ententes antérieurs, qu'ils soient écrits ou oraux.
                </p>
              </section>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
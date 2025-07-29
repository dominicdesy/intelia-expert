import React, { useState, useEffect } from 'react'

interface PhoneInputProps {
  countryCode: string
  areaCode: string
  phoneNumber: string
  onChange: (data: { country_code: string; area_code: string; phone_number: string }) => void
  className?: string
}

interface PhoneValidation {
  isValidCountry: boolean
  isValidArea: boolean
  isValidNumber: boolean
  errors: string[]
}

// ==================== COMPOSANT PHONE INPUT AVEC STYLING CORRIGÉ ====================
export const PhoneInput: React.FC<PhoneInputProps> = ({
  countryCode,
  areaCode,
  phoneNumber,
  onChange,
  className = ''
}) => {
  const [validation, setValidation] = useState<PhoneValidation>({
    isValidCountry: true,
    isValidArea: true,
    isValidNumber: true,
    errors: []
  })

  // Codes de pays populaires pour l'agriculture
  const countryCodes = [
    { code: '+1', country: 'Canada/USA', flag: '🇨🇦🇺🇸' },
    { code: '+33', country: 'France', flag: '🇫🇷' },
    { code: '+32', country: 'Belgique', flag: '🇧🇪' },
    { code: '+41', country: 'Suisse', flag: '🇨🇭' },
    { code: '+52', country: 'Mexique', flag: '🇲🇽' },
    { code: '+55', country: 'Brésil', flag: '🇧🇷' },
    { code: '+34', country: 'Espagne', flag: '🇪🇸' },
    { code: '+49', country: 'Allemagne', flag: '🇩🇪' },
    { code: '+44', country: 'Royaume-Uni', flag: '🇬🇧' },
    { code: '+39', country: 'Italie', flag: '🇮🇹' }
  ]

  // Fonction de validation des 3 champs séparés
  const validatePhone = (country: string, area: string, number: string): PhoneValidation => {
    const errors: string[] = []
    let isValidCountry = true
    let isValidArea = true
    let isValidNumber = true

    // Si au moins un champ est rempli, valider la cohérence
    const hasAnyField = country || area || number
    
    if (hasAnyField) {
      // Validation code pays
      if (!country || !country.startsWith('+')) {
        isValidCountry = false
        errors.push('Sélectionnez un code pays valide')
      }

      // Validation code régional (optionnel pour certains pays)
      if (country === '+1' && area && !/^\d{3}$/.test(area)) {
        isValidArea = false
        errors.push('Code régional doit contenir 3 chiffres (ex: 514)')
      } else if (country === '+33' && area && !/^\d{1,2}$/.test(area)) {
        isValidArea = false
        errors.push('Code régional français: 1-2 chiffres (ex: 1, 04)')
      }

      // Validation numéro principal
      if (!number) {
        isValidNumber = false
        errors.push('Numéro de téléphone requis')
      } else {
        // Validation selon le pays
        if (country === '+1' && !/^\d{7}$/.test(number.replace(/[\s\-]/g, ''))) {
          isValidNumber = false
          errors.push('Numéro NA: 7 chiffres (ex: 1234567)')
        } else if (country === '+33' && !/^\d{8}$/.test(number.replace(/[\s\-]/g, ''))) {
          isValidNumber = false
          errors.push('Numéro français: 8 chiffres après le code régional')
        } else if (!country.startsWith('+1') && !country.startsWith('+33') && !/^\d{6,10}$/.test(number.replace(/[\s\-]/g, ''))) {
          isValidNumber = false
          errors.push('Numéro: 6 à 10 chiffres')
        }
      }
    }

    return { isValidCountry, isValidArea, isValidNumber, errors }
  }

  // Gestionnaire de changement avec validation
  const handleChange = (field: 'country' | 'area' | 'number', value: string) => {
    const newData = {
      country: field === 'country' ? value : countryCode,
      area: field === 'area' ? value : areaCode,
      number: field === 'number' ? value : phoneNumber
    }

    // Validation temps réel
    const newValidation = validatePhone(newData.country, newData.area, newData.number)
    setValidation(newValidation)

    // Callback vers le parent avec les noms de champs Supabase
    onChange({
      country_code: newData.country,
      area_code: newData.area,
      phone_number: newData.number
    })
  }

  // Validation initiale
  useEffect(() => {
    const initialValidation = validatePhone(countryCode, areaCode, phoneNumber)
    setValidation(initialValidation)
  }, [countryCode, areaCode, phoneNumber])

  // Format d'affichage du numéro complet
  const getFormattedDisplay = () => {
    if (!countryCode && !areaCode && !phoneNumber) return ''
    
    let formatted = countryCode || ''
    if (areaCode) formatted += ` (${areaCode})`
    if (phoneNumber) formatted += ` ${phoneNumber}`
    
    return formatted.trim()
  }

  return (
    <div className="space-y-4">
      {/* Layout responsive avec hauteurs alignées */}
      <div className="space-y-4 lg:space-y-0 lg:grid lg:grid-cols-10 lg:gap-6 lg:items-end">
        {/* Code pays */}
        <div className="lg:col-span-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Code pays
          </label>
          {/* Espace réservé pour maintenir l'alignement */}
          <div className="h-4 mb-1"></div>
          <select
            value={countryCode}
            onChange={(e) => handleChange('country', e.target.value)}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm bg-white ${
              !validation.isValidCountry ? 'border-red-300 bg-red-50' : 'border-gray-300'
            }`}
          >
            <option value="">Sélectionner</option>
            {countryCodes.map(({ code, country, flag }) => (
              <option key={code} value={code}>
                {code} {flag} {country}
              </option>
            ))}
          </select>
        </div>

        {/* Code régional */}
        <div className="lg:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Code régional
          </label>
          {/* Zone d'information avec hauteur fixe */}
          <div className="h-4 mb-1 text-xs text-gray-500">
            {countryCode === '+1' && '(3 chiffres)'}
            {countryCode === '+33' && '(1-2 chiffres)'}
            {!countryCode && '\u00A0'} {/* Espace insécable */}
          </div>
          <input
            type="text"
            value={areaCode}
            onChange={(e) => handleChange('area', e.target.value.replace(/\D/g, ''))}
            placeholder={
              countryCode === '+1' ? '514' :
              countryCode === '+33' ? '1' :
              'Code'
            }
            disabled={!countryCode}
            maxLength={countryCode === '+1' ? 3 : 4}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm disabled:bg-gray-100 disabled:text-gray-500 ${
              !validation.isValidArea ? 'border-red-300 bg-red-50' : 'border-gray-300'
            }`}
          />
        </div>

        {/* Numéro principal */}
        <div className="lg:col-span-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Numéro de téléphone
          </label>
          {/* Zone d'information avec hauteur fixe */}
          <div className="h-4 mb-1 text-xs text-gray-500">
            {countryCode === '+1' && '(7 chiffres)'}
            {countryCode === '+33' && '(8 chiffres)'}
            {!countryCode && '\u00A0'} {/* Espace insécable */}
          </div>
          <input
            type="tel"
            value={phoneNumber}
            onChange={(e) => handleChange('number', e.target.value.replace(/\D/g, ''))}
            placeholder={
              countryCode === '+1' ? '1234567' :
              countryCode === '+33' ? '12345678' :
              'Numéro principal'
            }
            disabled={!countryCode}
            maxLength={countryCode === '+33' ? 8 : 10}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm disabled:bg-gray-100 disabled:text-gray-500 ${
              !validation.isValidNumber ? 'border-red-300 bg-red-50' : 'border-gray-300'
            }`}
          />
        </div>
      </div>

      {/* Aperçu du numéro formaté */}
      {getFormattedDisplay() && (
        <div className="bg-blue-50 border border-blue-200 px-3 py-2 rounded-md">
          <div className="flex items-center space-x-2">
            <span className="text-blue-600">📞</span>
            <span className="text-sm text-blue-800 font-medium">
              {getFormattedDisplay()}
            </span>
          </div>
        </div>
      )}

      {/* Messages d'erreur de validation */}
      {validation.errors.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-md p-3">
          <div className="text-sm text-red-800">
            <p className="font-medium mb-1 flex items-center">
              <span className="text-red-500 mr-1">⚠️</span>
              Format de téléphone :
            </p>
            <ul className="list-disc list-inside space-y-0.5 ml-4">
              {validation.errors.map((error, index) => (
                <li key={index} className="text-xs">{error}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Aide contextuelle selon le pays sélectionné */}
      {countryCode && (
        <div className="bg-gray-50 border border-gray-200 rounded-md p-3">
          <p className="text-xs font-medium text-gray-700 mb-2">
            💡 Exemples pour {countryCodes.find(c => c.code === countryCode)?.flag} {countryCodes.find(c => c.code === countryCode)?.country} :
          </p>
          <div className="text-xs text-gray-600 space-y-1">
            {countryCode === '+1' && (
              <>
                <div>🇨🇦 Montréal: +1 (514) 123-4567</div>
                <div>🇺🇸 New York: +1 (212) 123-4567</div>
              </>
            )}
            {countryCode === '+33' && (
              <>
                <div>🇫🇷 Paris: +33 1 12 34 56 78</div>
                <div>🇫🇷 Lyon: +33 4 12 34 56 78</div>
              </>
            )}
            {countryCode === '+32' && (
              <div>🇧🇪 Bruxelles: +32 2 123 45 67</div>
            )}
            {countryCode === '+41' && (
              <div>🇨🇭 Genève: +41 22 123 45 67</div>
            )}
            {countryCode === '+52' && (
              <div>🇲🇽 Mexico: +52 55 1234 5678</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// Hook pour utilisation dans les formulaires
export const usePhoneValidation = () => {
  const validatePhoneFields = (countryCode: string, areaCode: string, phoneNumber: string) => {
    const errors: string[] = []
    
    // Si aucun champ n'est rempli, c'est valide (optionnel)
    const hasAnyField = countryCode || areaCode || phoneNumber
    if (!hasAnyField) return { isValid: true, errors: [] }
    
    // Si au moins un champ est rempli, valider la cohérence
    if (!countryCode || !countryCode.startsWith('+')) {
      errors.push('Code pays requis')
    }
    
    if (!phoneNumber) {
      errors.push('Numéro principal requis')
    } else {
      // Validation basique numérique
      if (!/^\d{6,10}$/.test(phoneNumber.replace(/[\s\-]/g, ''))) {
        errors.push('Numéro invalide (6-10 chiffres)')
      }
    }
    
    return {
      isValid: errors.length === 0,
      errors
    }
  }
  
  return { validatePhoneFields }
}
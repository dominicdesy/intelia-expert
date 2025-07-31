import React from 'react'

interface PhoneInputProps {
  countryCode: string
  areaCode: string
  phoneNumber: string
  onChange: (data: { country_code: string; area_code: string; phone_number: string }) => void
}

// ==================== COMPOSANT PHONE INPUT SIMPLE ET FINAL ====================
export const PhoneInput: React.FC<PhoneInputProps> = ({
  countryCode,
  areaCode,
  phoneNumber,
  onChange
}) => {
  const countryCodes = [
    { code: '+1', country: 'Canada/USA' },
    { code: '+33', country: 'France' },
    { code: '+32', country: 'Belgique' },
    { code: '+41', country: 'Suisse' },
    { code: '+52', country: 'Mexique' },
    { code: '+55', country: 'Brésil' }
  ]

  const handleChange = (field: 'country' | 'area' | 'number', value: string) => {
    onChange({
      country_code: field === 'country' ? value : countryCode,
      area_code: field === 'area' ? value : areaCode,
      phone_number: field === 'number' ? value : phoneNumber
    })
  }

  return (
    <div className="grid grid-cols-12 gap-3 items-end">
      {/* Code pays */}
      <div className="col-span-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Code pays
        </label>
        <select
          value={countryCode}
          onChange={(e) => handleChange('country', e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm bg-white h-10"
        >
          <option value="">Sélectionner</option>
          {countryCodes.map(({ code, country }) => (
            <option key={code} value={code}>
              {code} {country}
            </option>
          ))}
        </select>
      </div>

      {/* Code régional */}
      <div className="col-span-3">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Code régional
        </label>
        <input
          type="text"
          value={areaCode}
          onChange={(e) => handleChange('area', e.target.value.replace(/\D/g, ''))}
          placeholder="Code"
          disabled={!countryCode}
          maxLength={4}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm disabled:bg-gray-100 disabled:text-gray-500 h-10"
        />
      </div>

      {/* Numéro principal */}
      <div className="col-span-5">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Numéro de téléphone
        </label>
        <input
          type="tel"
          value={phoneNumber}
          onChange={(e) => handleChange('number', e.target.value.replace(/\D/g, ''))}
          placeholder="Numéro principal"
          disabled={!countryCode}
          maxLength={10}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm disabled:bg-gray-100 disabled:text-gray-500 h-10"
        />
      </div>
    </div>
  )
}

// Hook simple
export const usePhoneValidation = () => {
  const validatePhoneFields = (countryCode: string, areaCode: string, phoneNumber: string) => {
    const hasAnyField = countryCode || areaCode || phoneNumber
    if (!hasAnyField) return { isValid: true, errors: [] }
    
    const errors: string[] = []
    if (hasAnyField && !countryCode) errors.push('Code pays requis')
    if (hasAnyField && !phoneNumber) errors.push('Numéro requis')
    
    return { isValid: errors.length === 0, errors }
  }
  
  return { validatePhoneFields }
}
import React, { useState, useEffect, useRef, useMemo } from 'react'

interface PhoneInputProps {
  countryCode: string
  areaCode: string
  phoneNumber: string
  onChange: (data: { country_code: string; area_code: string; phone_number: string }) => void
}

interface PhoneCode {
  code: string
  country: string
  flag?: string
  priority?: number
}

// Codes de secours avec les pays les plus courants
const fallbackPhoneCodes: PhoneCode[] = [
  { code: '+1', country: 'Canada/États-Unis', flag: '🇨🇦🇺🇸', priority: 1 },
  { code: '+33', country: 'France', flag: '🇫🇷', priority: 2 },
  { code: '+32', country: 'Belgique', flag: '🇧🇪', priority: 3 },
  { code: '+41', country: 'Suisse', flag: '🇨🇭', priority: 4 },
  { code: '+49', country: 'Allemagne', flag: '🇩🇪', priority: 5 },
  { code: '+44', country: 'Royaume-Uni', flag: '🇬🇧', priority: 6 },
  { code: '+39', country: 'Italie', flag: '🇮🇹', priority: 7 },
  { code: '+34', country: 'Espagne', flag: '🇪🇸', priority: 8 },
  { code: '+31', country: 'Pays-Bas', flag: '🇳🇱', priority: 9 },
  { code: '+46', country: 'Suède', flag: '🇸🇪', priority: 10 },
  { code: '+47', country: 'Norvège', flag: '🇳🇴', priority: 11 },
  { code: '+45', country: 'Danemark', flag: '🇩🇰', priority: 12 },
  { code: '+358', country: 'Finlande', flag: '🇫🇮', priority: 13 },
  { code: '+52', country: 'Mexique', flag: '🇲🇽', priority: 14 },
  { code: '+55', country: 'Brésil', flag: '🇧🇷', priority: 15 },
  { code: '+61', country: 'Australie', flag: '🇦🇺', priority: 16 },
  { code: '+81', country: 'Japon', flag: '🇯🇵', priority: 17 },
  { code: '+86', country: 'Chine', flag: '🇨🇳', priority: 18 },
  { code: '+91', country: 'Inde', flag: '🇮🇳', priority: 19 },
  { code: '+7', country: 'Russie', flag: '🇷🇺', priority: 20 }
]

// Hook pour récupérer les codes téléphoniques complets
const usePhoneCodes = () => {
  const [phoneCodes, setPhoneCodes] = useState<PhoneCode[]>(fallbackPhoneCodes)
  const [loading, setLoading] = useState(false)
  const [usingFallback, setUsingFallback] = useState(true)
  const abortControllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    const fetchPhoneCodes = async () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
      
      abortControllerRef.current = new AbortController()
      const signal = abortControllerRef.current.signal

      try {
        setLoading(true)
        const response = await fetch(
          'https://restcountries.com/v3.1/all?fields=cca2,name,idd,flag,translations',
          { signal }
        )
        
        if (!response.ok || signal.aborted) return
        
        const data = await response.json()
        
        if (signal.aborted) return
        
        const formattedPhoneCodes = data
          .map((country: any) => ({
            code: (country.idd?.root || '') + (country.idd?.suffixes?.[0] || ''),
            country: country.translations?.fra?.common || country.name.common,
            flag: country.flag,
            cca2: country.cca2
          }))
          .filter((item: any) => 
            item.code && 
            item.code.length > 1 &&
            item.code.startsWith('+') &&
            item.country
          )
          // Regrouper les pays avec le même code téléphonique
          .reduce((acc: any, current: any) => {
            const existing = acc.find((item: any) => item.code === current.code)
            if (existing) {
              // Si plusieurs pays ont le même code, les combiner
              if (!existing.country.includes(current.country)) {
                existing.country += `, ${current.country}`
              }
            } else {
              acc.push({
                code: current.code,
                country: current.country,
                flag: current.flag
              })
            }
            return acc
          }, [])
          .sort((a: PhoneCode, b: PhoneCode) => {
            // Priorité aux codes les plus courants
            const priorityA = fallbackPhoneCodes.find(f => f.code === a.code)?.priority || 999
            const priorityB = fallbackPhoneCodes.find(f => f.code === b.code)?.priority || 999
            
            if (priorityA !== priorityB) {
              return priorityA - priorityB
            }
            
            // Puis tri alphabétique par pays
            return a.country.localeCompare(b.country)
          })
        
        if (formattedPhoneCodes.length >= 100 && !signal.aborted) {
          setPhoneCodes(formattedPhoneCodes)
          setUsingFallback(false)
        }
        
      } catch (error) {
        if (error instanceof Error && error.name !== 'AbortError') {
          console.warn('Erreur récupération codes téléphoniques:', error.message)
        }
      } finally {
        if (!signal.aborted) {
          setLoading(false)
        }
      }
    }

    fetchPhoneCodes()
    
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [])

  return { phoneCodes, loading, usingFallback }
}

export const PhoneInput: React.FC<PhoneInputProps> = ({
  countryCode,
  areaCode,
  phoneNumber,
  onChange
}) => {
  const { phoneCodes, loading, usingFallback } = usePhoneCodes()
  
  const handleChange = (field: 'country' | 'area' | 'number', value: string) => {
    onChange({
      country_code: field === 'country' ? value : countryCode,
      area_code: field === 'area' ? value : areaCode,
      phone_number: field === 'number' ? value : phoneNumber
    })
  }

  // IDs uniques pour les labels - FIX MICROSOFT EDGE
  const componentId = useMemo(() => 
    `phone-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`, 
    []
  )
  const countryId = `${componentId}-country`
  const areaId = `${componentId}-area`
  const numberId = `${componentId}-number`

  return (
    <div>
      {/* Avertissement si utilisation de la liste de secours */}
      {usingFallback && !loading && (
        <div className="mb-3 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
          <div className="flex items-center space-x-1">
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            <span>Liste de codes téléphoniques limitée (service externe temporairement indisponible)</span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-12 gap-3 items-end">
        {/* Code pays avec liste complète */}
        <div className="col-span-4">
          <label htmlFor={countryId} className="block text-sm font-medium text-gray-700 mb-1">
            Code pays
          </label>
          <select
            id={countryId}
            name="countryCode"
            value={countryCode}
            onChange={(e) => handleChange('country', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm bg-white h-10"
            aria-describedby={`${countryId}-help`}
            disabled={loading}
          >
            <option value="">
              {loading ? 'Chargement...' : 'Sélectionner'}
            </option>
            {phoneCodes.map(({ code, country, flag }) => (
              <option key={code} value={code}>
                {flag ? `${flag} ` : ''}{code} {country}
              </option>
            ))}
          </select>
          <div id={`${countryId}-help`} className="sr-only">
            Sélectionnez le code pays pour votre numéro de téléphone
          </div>
          {loading && (
            <div className="mt-1 text-xs text-gray-500">
              Chargement des codes téléphoniques...
            </div>
          )}
        </div>

        {/* Code régional */}
        <div className="col-span-3">
          <label htmlFor={areaId} className="block text-sm font-medium text-gray-700 mb-1">
            Code régional
          </label>
          <input
            type="text"
            id={areaId}
            name="areaCode"
            value={areaCode}
            onChange={(e) => handleChange('area', e.target.value.replace(/\D/g, ''))}
            placeholder="Code"
            disabled={!countryCode}
            maxLength={4}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm disabled:bg-gray-100 disabled:text-gray-500 h-10"
            aria-describedby={`${areaId}-help`}
          />
          <div id={`${areaId}-help`} className="sr-only">
            Code régional de votre région (optionnel)
          </div>
        </div>

        {/* Numéro principal */}
        <div className="col-span-5">
          <label htmlFor={numberId} className="block text-sm font-medium text-gray-700 mb-1">
            Numéro de téléphone
          </label>
          <input
            type="tel"
            id={numberId}
            name="phoneNumber"
            value={phoneNumber}
            onChange={(e) => handleChange('number', e.target.value.replace(/\D/g, ''))}
            placeholder="Numéro principal"
            disabled={!countryCode}
            maxLength={10}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm disabled:bg-gray-100 disabled:text-gray-500 h-10"
            aria-describedby={`${numberId}-help`}
          />
          <div id={`${numberId}-help`} className="sr-only">
            Votre numéro de téléphone principal
          </div>
        </div>
      </div>
    </div>
  )
}

// Hook de validation inchangé
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
import React, { useState, useRef, useEffect } from 'react'
import { useTranslation } from '@/lib/languages/i18n'

interface Country {
  value: string
  label: string
  phoneCode: string
  flag?: string
}

interface CountrySelectProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
  countries?: Country[] // Si fourni, utilise cette liste au lieu de charger depuis l'API
}

// Mapping des codes de langue vers les codes utilisés par REST Countries
const getLanguageCode = (currentLanguage: string): string => {
  const mapping: Record<string, string> = {
    'fr': 'fra',   // Français
    'es': 'spa',   // Espagnol
    'de': 'deu',   // Allemand
    'pt': 'por',   // Portugais
    'nl': 'nld',   // Néerlandais
    'pl': 'pol',   // Polonais
    'zh': 'zho',   // Chinois
    'hi': 'hin',   // Hindi
    'th': 'tha',   // Thaï
    'en': 'eng'    // Anglais (fallback)
  }
  return mapping[currentLanguage] || 'eng'
}

// Hook autonome pour les pays - SANS FALLBACK
const useCountriesAutonomous = () => {
  const { currentLanguage } = useTranslation()
  const languageCode = getLanguageCode(currentLanguage)
  
  const [countries, setCountries] = useState<Country[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    const fetchCountries = async () => {
      // Annuler la requête précédente si elle existe
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
      
      abortControllerRef.current = new AbortController()
      const signal = abortControllerRef.current.signal

      try {
        console.log(`[CountrySelect] Chargement des pays en ${currentLanguage} (${languageCode})...`)
        setLoading(true)
        setError(null)
        
        const response = await fetch('https://restcountries.com/v3.1/all?fields=cca2,name,idd,flag,translations', {
          headers: {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (compatible; Intelia/1.0)',
            'Cache-Control': 'no-cache'
          },
          signal
        })
        
        if (!response.ok) {
          throw new Error(`API Error: ${response.status} ${response.statusText}`)
        }
        
        const data = await response.json()
        console.log(`[CountrySelect] Données reçues: ${data.length} pays`)
        
        if (signal.aborted) return
        
        const formattedCountries = data
          .map((country: any) => {
            let phoneCode = ''
            if (country.idd?.root) {
              phoneCode = country.idd.root
              if (country.idd.suffixes && country.idd.suffixes[0]) {
                phoneCode += country.idd.suffixes[0]
              }
            }
            
            // Récupération du nom selon la langue
            let countryName = country.name?.common || country.cca2
            
            // Essayer d'abord la traduction dans la langue demandée
            if (country.translations && country.translations[languageCode]) {
              countryName = country.translations[languageCode].common || country.translations[languageCode].official
            }
            // Si pas de traduction dans la langue demandée, utiliser l'anglais
            else if (country.name?.common) {
              countryName = country.name.common
            }
            
            return {
              value: country.cca2,
              label: countryName,
              phoneCode: phoneCode,
              flag: country.flag || ''
            }
          })
          .filter((country: Country) => {
            const hasValidCode = country.phoneCode && 
                                country.phoneCode !== 'undefined' && 
                                country.phoneCode !== 'null' &&
                                country.phoneCode.length > 1 &&
                                country.phoneCode.startsWith('+') &&
                                /^\+\d+$/.test(country.phoneCode)
            
            const hasValidInfo = country.value && 
                                country.value.length === 2 &&
                                country.label && 
                                country.label.length > 1
            
            return hasValidCode && hasValidInfo
          })
          .sort((a: Country, b: Country) => {
            // Tri selon la langue actuelle
            const locale = languageCode === 'fra' ? 'fr' : 
                          languageCode === 'spa' ? 'es' :
                          languageCode === 'deu' ? 'de' :
                          languageCode === 'por' ? 'pt' :
                          languageCode === 'nld' ? 'nl' :
                          languageCode === 'pol' ? 'pl' :
                          languageCode === 'zho' ? 'zh' :
                          'en'
            
            return a.label.localeCompare(b.label, locale, { numeric: true })
          })
        
        console.log(`[CountrySelect] Pays traités: ${formattedCountries.length}`)
        
        if (!signal.aborted) {
          setCountries(formattedCountries)
          
          // Logs de debug pour vérifier les traductions
          const france = formattedCountries.find(c => c.value === 'FR')
          const usa = formattedCountries.find(c => c.value === 'US')
          const germany = formattedCountries.find(c => c.value === 'DE')
          
          console.log(`[CountrySelect] Exemples en ${currentLanguage}:`)
          console.log('  France:', france?.label)
          console.log('  USA:', usa?.label)
          console.log('  Germany:', germany?.label)
        }
        
      } catch (err: any) {
        if (err.name !== 'AbortError' && !signal.aborted) {
          console.error('[CountrySelect] Erreur:', err)
          setError(err.message || 'Erreur de chargement des pays')
        }
      } finally {
        if (!signal.aborted) {
          setLoading(false)
        }
      }
    }

    fetchCountries()
    
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [currentLanguage, languageCode]) // Se redéclenche quand la langue change

  return { countries, loading, error }
}

export const CountrySelect: React.FC<CountrySelectProps> = ({
  value,
  onChange,
  placeholder,
  className = "",
  countries: providedCountries
}) => {
  const { t } = useTranslation()
  
  // Utiliser les pays fournis ou charger automatiquement selon la langue
  const { countries: autoCountries, loading, error } = useCountriesAutonomous()
  const countries = providedCountries || autoCountries
  
  const [isOpen, setIsOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  const selectRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLUListElement>(null)

  // Utiliser la traduction par défaut si pas de placeholder fourni
  const finalPlaceholder = placeholder || t('placeholder.countrySelect')

  // Filtrer les pays selon le terme de recherche
  const filteredCountries = countries.filter(country =>
    country.label.toLowerCase().includes(searchTerm.toLowerCase())
  )

  // Trouver le pays sélectionné
  const selectedCountry = countries.find(c => c.value === value)

  // Gérer les clics extérieurs
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (selectRef.current && !selectRef.current.contains(event.target as Node)) {
        setIsOpen(false)
        setSearchTerm('')
        setHighlightedIndex(-1)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Focus sur l'input quand on ouvre
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  // Gérer la navigation au clavier
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
        e.preventDefault()
        setIsOpen(true)
      }
      return
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setHighlightedIndex(prev => 
          prev < filteredCountries.length - 1 ? prev + 1 : 0
        )
        break
      case 'ArrowUp':
        e.preventDefault()
        setHighlightedIndex(prev => 
          prev > 0 ? prev - 1 : filteredCountries.length - 1
        )
        break
      case 'Enter':
        e.preventDefault()
        if (highlightedIndex >= 0 && filteredCountries[highlightedIndex]) {
          onChange(filteredCountries[highlightedIndex].value)
          setIsOpen(false)
          setSearchTerm('')
          setHighlightedIndex(-1)
        }
        break
      case 'Escape':
        setIsOpen(false)
        setSearchTerm('')
        setHighlightedIndex(-1)
        break
    }
  }

  // Faire défiler vers l'élément surligné
  useEffect(() => {
    if (highlightedIndex >= 0 && listRef.current) {
      const highlightedElement = listRef.current.children[highlightedIndex] as HTMLElement
      if (highlightedElement) {
        highlightedElement.scrollIntoView({ block: 'nearest' })
      }
    }
  }, [highlightedIndex])

  const handleSelect = (country: Country) => {
    onChange(country.value)
    setIsOpen(false)
    setSearchTerm('')
    setHighlightedIndex(-1)
  }

  // Afficher un état de chargement
  if (!providedCountries && loading) {
    return (
      <div className={`relative ${className}`}>
        <div className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 flex items-center">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
          <span className="text-gray-500 text-sm">{t('countries.loading')}</span>
        </div>
      </div>
    )
  }

  // Afficher l'erreur de chargement
  if (!providedCountries && error) {
    return (
      <div className={`relative ${className}`}>
        <div className="w-full px-3 py-2 border border-red-300 rounded-lg bg-red-50 flex items-center">
          <svg className="w-4 h-4 text-red-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
          <span className="text-red-700 text-sm">{t('countries.loadingError')}</span>
        </div>
      </div>
    )
  }

  return (
    <div ref={selectRef} className={`relative ${className}`}>
      {/* Bouton principal */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        onKeyDown={handleKeyDown}
        className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-left flex items-center justify-between ${
          isOpen ? 'ring-2 ring-blue-500 border-transparent' : ''
        }`}
        aria-label={selectedCountry ? selectedCountry.label : finalPlaceholder}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        disabled={!providedCountries && (loading || !!error)}
      >
        <span className={selectedCountry ? 'text-gray-900' : 'text-gray-500'}>
          {selectedCountry ? (
            <span className="flex items-center">
              <span className="mr-2">{selectedCountry.flag}</span>
              {selectedCountry.label}
            </span>
          ) : (
            finalPlaceholder
          )}
        </span>
        
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${
            isOpen ? 'transform rotate-180' : ''
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-hidden">
          {/* Champ de recherche */}
          <div className="p-2 border-b border-gray-100">
            <input
              ref={inputRef}
              type="text"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value)
                setHighlightedIndex(-1)
              }}
              onKeyDown={handleKeyDown}
              placeholder={t('countries.searchPlaceholder')}
              className="w-full px-2 py-1 text-sm border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-transparent"
              aria-label={t('countries.searchPlaceholder')}
            />
          </div>

          {/* Liste des pays */}
          <ul 
            ref={listRef} 
            className="max-h-48 overflow-y-auto"
            role="listbox"
            aria-label={t('countries.listLabel')}
          >
            {filteredCountries.length > 0 ? (
              filteredCountries.map((country, index) => (
                <li key={country.value} role="option" aria-selected={country.value === value}>
                  <button
                    type="button"
                    onClick={() => handleSelect(country)}
                    className={`w-full px-3 py-2 text-left flex items-center hover:bg-blue-50 focus:outline-none focus:bg-blue-50 ${
                      index === highlightedIndex ? 'bg-blue-50' : ''
                    } ${
                      country.value === value ? 'bg-blue-100 text-blue-900 font-medium' : 'text-gray-900 bg-white'
                    }`}
                    style={{ 
                      color: country.value === value ? '#1e3a8a' : '#111827',
                      backgroundColor: country.value === value ? '#dbeafe' : (index === highlightedIndex ? '#eff6ff' : '#ffffff')
                    }}
                    aria-label={`${t('countries.select')} ${country.label}`}
                  >
                    <span className="mr-2 text-base" aria-hidden="true">{country.flag}</span>
                    <span className="flex-1">{country.label}</span>
                    {country.value === value && (
                      <svg 
                        className="w-4 h-4 text-blue-600" 
                        fill="none" 
                        viewBox="0 0 24 24" 
                        stroke="currentColor"
                        aria-hidden="true"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </button>
                </li>
              ))
            ) : (
              <li className="px-3 py-4 text-center text-gray-500 text-sm" role="option">
                {`${t('countries.noResults')}: ${searchTerm}`}
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  )
}
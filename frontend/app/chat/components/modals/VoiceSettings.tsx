'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from '@/lib/languages/i18n';
import { apiClient } from '@/lib/api/client';
import { secureLog } from '@/lib/utils/secureLogger';

interface VoiceOption {
  id: string;
  name: string;
  description: string;
  gender: string;
  preview_url: string;
}

interface VoiceSettingsData {
  voice_preference: string;
  voice_speed: number;
  can_use_voice: boolean;
  plan: string;
}

interface VoicesListResponse {
  voices: VoiceOption[];
  default: string;
  recommended_speed_range: { min: number; max: number };
  speed_range: { min: number; max: number };
}

interface VoiceSettingsProps {
  preloadedVoices?: VoiceOption[];
}

export const VoiceSettings: React.FC<VoiceSettingsProps> = ({ preloadedVoices }) => {
  const { t } = useTranslation();
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState('');
  const [error, setError] = useState('');

  const [voicePreference, setVoicePreference] = useState('alloy');
  const [voiceSpeed, setVoiceSpeed] = useState(1.0);
  const [canUseVoice, setCanUseVoice] = useState(false);
  const [plan, setPlan] = useState('essential');

  const [voices, setVoices] = useState<VoiceOption[]>(preloadedVoices || []);
  const [playingVoice, setPlayingVoice] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  // Charger les voix et préférences utilisateur
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    setError('');

    try {
      // Charger voix disponibles si pas déjà préchargées
      if (!preloadedVoices || preloadedVoices.length === 0) {
        const voicesResponse = await apiClient.get('/voice-settings/voices');
        if (voicesResponse.success && voicesResponse.data) {
          const voicesData = voicesResponse.data as VoicesListResponse;
          if (voicesData.voices) {
            setVoices(voicesData.voices);
          }
        }
      }

      // Charger préférences utilisateur (endpoint authentifié)
      const settingsResponse = await apiClient.getSecure('/voice-settings');
      if (settingsResponse.success && settingsResponse.data) {
        const data = settingsResponse.data as VoiceSettingsData;
        setVoicePreference(data.voice_preference);
        setVoiceSpeed(data.voice_speed);
        setCanUseVoice(data.can_use_voice);
        setPlan(data.plan);
      }
    } catch (err: any) {
      secureLog.error('Error loading voice settings:', err);
      setError(t('error.loadVoiceSettings') || 'Failed to load voice settings');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setError('');
    setSaveSuccess('');

    try {
      const response = await apiClient.putSecure('/voice-settings', {
        voice_preference: voicePreference,
        voice_speed: voiceSpeed,
      });

      if (response.success) {
        setSaveSuccess(t('success.voiceSettingsSaved') || 'Voice settings saved successfully!');
        setTimeout(() => setSaveSuccess(''), 3000);
      } else {
        throw new Error(response.error?.message || 'Save failed');
      }
    } catch (err: any) {
      secureLog.error('Error saving voice settings:', err);
      setError(err.message || t('error.saveVoiceSettings') || 'Failed to save voice settings');
    } finally {
      setIsSaving(false);
    }
  };

  const playPreview = (voiceId: string) => {
    if (playingVoice === voiceId) {
      // Stop if already playing
      audioRef.current?.pause();
      setPlayingVoice(null);
      return;
    }

    const voice = voices.find(v => v.id === voiceId);
    if (voice && audioRef.current) {
      audioRef.current.src = voice.preview_url;
      audioRef.current.play();
      setPlayingVoice(voiceId);
    }
  };

  const handleAudioEnded = () => {
    setPlayingVoice(null);
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!canUseVoice) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
        <div className="flex items-start">
          <svg
            className="w-6 h-6 text-yellow-600 mr-3 flex-shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <div>
            <h3 className="text-lg font-medium text-yellow-900 mb-2">
              {t('voiceSettings.upgradeRequired') || 'Upgrade Required'}
            </h3>
            <p className="text-sm text-yellow-800 mb-4">
              {t('voiceSettings.upgradeMessage') ||
                'Voice assistant is only available for Elite and Intelia plans. Upgrade your plan to access this feature.'}
            </p>
            <p className="text-xs text-yellow-700">
              {t('voiceSettings.currentPlan') || 'Your current plan:'} <strong>{plan}</strong>
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Success message */}
      {saveSuccess && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-sm text-green-800">{saveSuccess}</p>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* Voice selector */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-3">
          {t('voiceSettings.selectVoice') || 'Voice Selection'}
        </label>
        <div className="space-y-2">
          {voices.map((voice) => (
            <div
              key={voice.id}
              className={`flex items-center justify-between p-3 border rounded-lg cursor-pointer transition-all ${
                voicePreference === voice.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              }`}
              onClick={() => setVoicePreference(voice.id)}
            >
              <div className="flex items-center space-x-3">
                <input
                  type="radio"
                  name="voice"
                  value={voice.id}
                  checked={voicePreference === voice.id}
                  onChange={() => setVoicePreference(voice.id)}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500"
                />
                <div>
                  <div className="font-medium text-gray-900">{voice.name}</div>
                  <div className="text-sm text-gray-500">{voice.description}</div>
                </div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  playPreview(voice.id);
                }}
                className={`px-3 py-1 text-sm rounded transition-colors ${
                  playingVoice === voice.id
                    ? 'bg-blue-600 text-white'
                    : 'bg-blue-50 text-blue-600 hover:bg-blue-100'
                }`}
              >
                {playingVoice === voice.id ? '⏸' : '▶'}{' '}
                {t('voiceSettings.listen') || 'Listen'}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Speed selector */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {t('voiceSettings.speed') || 'Speech Speed'}: {voiceSpeed}x
        </label>
        <input
          type="range"
          min="0.8"
          max="1.5"
          step="0.1"
          value={voiceSpeed}
          onChange={(e) => setVoiceSpeed(parseFloat(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
        />
        <div className="relative text-xs text-gray-500 mt-1 h-4">
          <span className="absolute left-0">0.8x {t('voiceSettings.slower') || 'Slower'}</span>
          <span className="absolute left-[28.6%] -translate-x-1/2">1.0x {t('voiceSettings.normal') || 'Normal'}</span>
          <span className="absolute left-[57.1%] -translate-x-1/2">1.2x</span>
          <span className="absolute right-0">1.5x {t('voiceSettings.faster') || 'Faster'}</span>
        </div>
      </div>

      {/* Save button */}
      <div className="flex justify-end pt-4">
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSaving
            ? t('common.saving') || 'Saving...'
            : t('common.save') || 'Save'}
        </button>
      </div>

      {/* Hidden audio element */}
      <audio ref={audioRef} onEnded={handleAudioEnded} />
    </div>
  );
};

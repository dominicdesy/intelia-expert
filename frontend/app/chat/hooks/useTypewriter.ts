/**
 * useTypewriter.ts - Hook for typewriter animation effect
 *
 * Simulates typing animation like claude.ai for LLM responses
 */

import { useState, useEffect, useRef } from 'react';

interface UseTypewriterOptions {
  text: string;
  speed?: number; // Characters per frame
  enabled?: boolean; // Enable/disable effect
  onComplete?: () => void;
}

export function useTypewriter({
  text,
  speed = 2,
  enabled = true,
  onComplete
}: UseTypewriterOptions) {
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const indexRef = useRef(0);
  const rafRef = useRef<number>();
  const lastTimeRef = useRef<number>(0);

  useEffect(() => {
    // If disabled, show full text immediately
    if (!enabled) {
      setDisplayedText(text);
      setIsTyping(false);
      return;
    }

    // Reset if text changes
    if (text !== displayedText && !isTyping) {
      indexRef.current = 0;
      setDisplayedText('');
      setIsTyping(true);
      lastTimeRef.current = 0;
    }

    if (!isTyping) return;

    let animationFrameId: number;

    const animate = (currentTime: number) => {
      if (!lastTimeRef.current) {
        lastTimeRef.current = currentTime;
      }

      const deltaTime = currentTime - lastTimeRef.current;

      // Update every ~16ms (60fps) but add multiple characters based on speed
      if (deltaTime >= 16) {
        const currentIndex = indexRef.current;
        const nextIndex = Math.min(currentIndex + speed, text.length);

        setDisplayedText(text.slice(0, nextIndex));
        indexRef.current = nextIndex;
        lastTimeRef.current = currentTime;

        if (nextIndex >= text.length) {
          setIsTyping(false);
          if (onComplete) {
            onComplete();
          }
          return;
        }
      }

      animationFrameId = requestAnimationFrame(animate);
    };

    animationFrameId = requestAnimationFrame(animate);

    return () => {
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
    };
  }, [text, isTyping, enabled, speed, onComplete, displayedText]);

  return {
    displayedText: enabled ? displayedText : text,
    isTyping,
    reset: () => {
      indexRef.current = 0;
      setDisplayedText('');
      setIsTyping(false);
    }
  };
}

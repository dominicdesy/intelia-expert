/**
 * useHeadwaySync - Synchronize Headway viewed articles with server
 * Version: 1.0.0
 * Date: 2025-10-31
 * Description: Persist viewed articles to database for private browsing support
 */

import { useEffect, useCallback, useState } from 'react';
import { apiClient } from '@/lib/api/client';
import { secureLog } from '@/lib/utils/secureLogger';

interface HeadwayWidget {
  getUnseenCount?: () => number;
  markAsRead?: (articleId: string) => void;
  getArticles?: () => Array<{ id: string; read: boolean }>;
}

declare global {
  interface Window {
    Headway?: {
      init: (config: any) => HeadwayWidget | void;
      getUnseenCount?: () => number;
      markAsRead?: (articleId: string) => void;
    };
  }
}

export function useHeadwaySync() {
  const [synced, setSynced] = useState(false);

  /**
   * Fetch viewed articles from server and mark them in Headway
   */
  const syncFromServer = useCallback(async () => {
    try {
      secureLog.log('[HeadwaySync] Fetching viewed articles from server...');

      const response = await apiClient.getSecure<{ article_ids: string[]; count: number }>(
        'headway/viewed'
      );

      if (!response.success || !response.data) {
        secureLog.warn('[HeadwaySync] Failed to fetch viewed articles:', response.error);
        return;
      }

      const { article_ids, count } = response.data;
      secureLog.log(`[HeadwaySync] Retrieved ${count} viewed articles from server`);

      // Mark articles as read in Headway
      if (window.Headway && count > 0) {
        article_ids.forEach(articleId => {
          try {
            window.Headway?.markAsRead?.(articleId);
            secureLog.log(`[HeadwaySync] Marked article ${articleId} as read in Headway`);
          } catch (err) {
            secureLog.warn(`[HeadwaySync] Failed to mark article ${articleId} as read:`, err);
          }
        });
      }

      setSynced(true);
      secureLog.log('[HeadwaySync] Sync complete');
    } catch (error) {
      secureLog.error('[HeadwaySync] Error syncing from server:', error);
    }
  }, []);

  /**
   * Save viewed article to server
   */
  const markAsViewed = useCallback(async (articleId: string) => {
    try {
      secureLog.log(`[HeadwaySync] Saving article ${articleId} to server...`);

      const response = await apiClient.postSecure('headway/mark-viewed', {
        article_id: articleId
      });

      if (response.success) {
        secureLog.log(`[HeadwaySync] Article ${articleId} saved to server`);
      } else {
        secureLog.warn('[HeadwaySync] Failed to save article:', response.error);
      }
    } catch (error) {
      secureLog.error('[HeadwaySync] Error saving article:', error);
    }
  }, []);

  /**
   * Sync on mount (fetch server state and apply to Headway)
   */
  useEffect(() => {
    if (typeof window !== 'undefined' && !synced) {
      // Wait for Headway to be ready
      const checkHeadway = setInterval(() => {
        if (window.Headway) {
          clearInterval(checkHeadway);
          syncFromServer();
        }
      }, 100);

      // Clear interval after 5 seconds if Headway doesn't load
      setTimeout(() => clearInterval(checkHeadway), 5000);

      return () => clearInterval(checkHeadway);
    }
  }, [synced, syncFromServer]);

  return {
    synced,
    syncFromServer,
    markAsViewed
  };
}

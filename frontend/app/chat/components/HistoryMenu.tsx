/**
 * Historymenu
 * Version: 1.4.1
 * Last modified: 2025-10-26
 */
"use client";

import React, { useCallback, useMemo, useState } from "react";
import { useTranslation } from "@/lib/languages/i18n";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import {
  useConversationGroups,
  useConversationActions,
  useCurrentConversation,
} from "../hooks/useChatStore";
import { useAuthStore } from "@/lib/stores/auth";
import { TrashIcon, PlusIcon, MessageCircleIcon } from "../utils/icons";
import type { Conversation, ConversationGroup } from "../../../types";
import { secureLog } from "@/lib/utils/secureLogger";
import { apiClient } from "@/lib/api/client";

export const HistoryMenu = React.memo(() => {
  const { t } = useTranslation();
  const { user } = useAuthStore();

  const { conversationGroups, isLoadingHistory, loadConversations } = useConversationGroups();
  const {
    deleteConversation,
    refreshConversations,
    createNewConversation,
  } = useConversationActions();
  const { currentConversation, loadConversation } = useCurrentConversation();

  // États pour la recherche
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Conversation[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const getGroupTitle = useCallback(
    (title: string): string => {
      switch (title) {
        case "today":
          return t("history.groups.today" as any);
        case "yesterday":
          return t("history.groups.yesterday" as any);
        case "thisWeek":
          return t("history.groups.thisWeek" as any);
        case "thisMonth":
          return t("history.groups.thisMonth" as any);
        case "older":
          return t("history.groups.older" as any);
        default:
          return title;
      }
    },
    [t],
  );

  const handleOpenChange = useCallback(
    async (open: boolean) => {
      if (open && user && !isLoadingHistory) {
        secureLog.log("🔄 [HistoryMenu] Chargement à l'ouverture du menu");
        try {
          await loadConversations(user.id || user.email);
          secureLog.log("✅ [HistoryMenu] Conversations chargées");
        } catch (error) {
          secureLog.error("❌ [HistoryMenu] Erreur chargement:", error);
        }
      }
    },
    [user, isLoadingHistory, loadConversations],
  );

  const handleRefresh = useCallback(
    async (e: Event) => {
      e.preventDefault();
      if (!user) return;
      secureLog.log("🔄 [HistoryMenu] Refresh demandé");
      await refreshConversations(user.id || user.email);
    },
    [user, refreshConversations],
  );

  const handleDeleteSingle = useCallback(
    async (conversationId: string, e: Event) => {
      e.preventDefault();
      e.stopPropagation();
      await deleteConversation(conversationId);
      if (user) await refreshConversations(user.id || user.email);
    },
    [deleteConversation, user, refreshConversations],
  );

  const handleConversationClick = useCallback(
    async (convId: string) => {
      await loadConversation(convId);
    },
    [loadConversation],
  );

  const handleNewConversation = useCallback(() => {
    createNewConversation();
  }, [createNewConversation]);

  const handleSearch = useCallback(
    async (query: string) => {
      if (!query.trim()) {
        setSearchResults([]);
        setSearchError(null);
        return;
      }

      setIsSearching(true);
      setSearchError(null);

      try {
        const response = await apiClient.getSecure<{
          status: string;
          conversations: Conversation[];
          total_count: number;
        }>(`/conversations/search?q=${encodeURIComponent(query.trim())}`);

        if (response.success && response.data) {
          setSearchResults(response.data.conversations);
          secureLog.log(`[Search] Found ${response.data.total_count} results`);
        } else {
          setSearchError(t("history.searchError") || "Search failed");
        }
      } catch (error) {
        secureLog.error("[Search] Error:", error);
        setSearchError(t("history.searchError") || "Search failed");
      } finally {
        setIsSearching(false);
      }
    },
    [t]
  );

  // Ref pour gérer le debounce cleanup
  const debounceTimerRef = React.useRef<NodeJS.Timeout | null>(null);

  const handleSearchInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      setSearchQuery(value);

      // Clear le timer précédent
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }

      // Debounce: rechercher après 300ms d'inactivité (réduit de 500ms pour meilleure réactivité)
      debounceTimerRef.current = setTimeout(() => {
        handleSearch(value);
      }, 300);
    },
    [handleSearch]
  );

  const handleClearSearch = useCallback(() => {
    setSearchQuery("");
    setSearchResults([]);
    setSearchError(null);
  }, []);

  const formatConversationTime = useCallback((timestamp: string): string => {
    try {
      let ts = timestamp;
      if (ts && !ts.endsWith("Z") && !/[+-]\d{2}:\d{2}$/.test(ts)) ts = ts + "Z";
      const d = new Date(ts);
      if (isNaN(d.getTime())) return "—";
      const h = d.getHours().toString().padStart(2, "0");
      const m = d.getMinutes().toString().padStart(2, "0");
      return `${h}:${m}`;
    } catch {
      return "—";
    }
  }, []);

  const totalConversations = useMemo(() => {
    return conversationGroups.reduce(
      (acc: number, g: ConversationGroup) => acc + g.conversations.length,
      0,
    );
  }, [conversationGroups]);

  const notificationBadge = useMemo(() => {
    if (totalConversations <= 0) return null;
    return <span className="notification-badge">{totalConversations}</span>;
  }, [totalConversations]);

  // Détermine si on affiche les résultats de recherche ou la liste normale
  const isSearchActive = searchQuery.trim().length > 0;
  const displayConversations = isSearchActive ? searchResults : null;

  return (
    <div className="relative header-icon-container">
      <DropdownMenu.Root onOpenChange={handleOpenChange}>
        <DropdownMenu.Trigger asChild>
          <button
            className="w-10 h-10 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors flex items-center justify-center border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            title={t("nav.history")}
            aria-label={t("nav.history")}
          >
            <svg
              className="w-5 h-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
            >
              <path
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M8 7H5m0 0v3m0-3l2.2 2.2"
              />
              <path
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 12a9 9 0 10-9 9"
              />
              <path
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 7v5l3 3"
              />
            </svg>
          </button>
        </DropdownMenu.Trigger>

        {notificationBadge}

        <DropdownMenu.Portal>
          <DropdownMenu.Content
            className="w-96 bg-white rounded-lg shadow-xl border border-gray-200 z-50 max-h-[70vh] overflow-hidden flex flex-col animate-in fade-in-0 zoom-in-95"
            sideOffset={8}
            align="start"
            style={{ maxWidth: 'calc(100vw - 1rem)' }}
          >
            {/* Barre de recherche */}
            <div className="p-4 border-b border-gray-200 sticky top-0 bg-white z-10">
              <div className="relative">
                <input
                  type="text"
                  placeholder={t("history.searchPlaceholder") || "Search conversations..."}
                  value={searchQuery}
                  onChange={handleSearchInputChange}
                  className="w-full pl-10 pr-10 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                />
                <svg
                  className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400"
                  fill="none"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                {searchQuery && (
                  <button
                    onClick={handleClearSearch}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                    aria-label="Clear search"
                  >
                    <svg className="w-5 h-5" fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" viewBox="0 0 24 24" stroke="currentColor">
                      <path d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>
              {isSearching && (
                <div className="flex items-center justify-center mt-2 text-sm text-gray-500">
                  <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mr-2"></div>
                  {t("history.searching") || "Searching..."}
                </div>
              )}
              {searchError && (
                <div className="mt-2 text-sm text-red-600">
                  {searchError}
                </div>
              )}
            </div>

            {isLoadingHistory ? (
              <div className="p-6 text-center text-gray-500">
                <div className="flex items-center justify-center space-x-3 mb-2">
                  <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                  <span>{t("history.loadingConversations")}</span>
                </div>
                <p className="text-xs text-gray-400">{t("history.retrievingHistory")}</p>
              </div>
            ) : conversationGroups.length === 0 ? (
              <div className="p-6 text-center text-gray-500">
                <div className="mb-3">
                  <MessageCircleIcon className="w-12 h-12 text-gray-300 mx-auto mb-2" />
                </div>
                <div className="text-sm font-medium text-gray-600 mb-1">
                  {t("history.noConversations")}
                </div>
                <div className="text-xs text-gray-400 mb-4">
                  {t("history.startQuestion")}
                </div>

                <DropdownMenu.Item
                  className="inline-flex items-center space-x-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 transition-colors cursor-pointer outline-none"
                  onSelect={handleNewConversation}
                >
                  <PlusIcon className="w-4 h-4" />
                  <span>{t("history.newConversation")}</span>
                </DropdownMenu.Item>

                {user && (
                  <button
                    onClick={handleRefresh as any}
                    className="ml-2 text-blue-600 hover:text-blue-700 text-xs underline"
                    disabled={isLoadingHistory}
                  >
                    {t("history.refresh")}
                  </button>
                )}
              </div>
            ) : isSearchActive ? (
              /* Résultats de recherche */
              <div className="flex-1 overflow-y-auto">
                {searchResults.length === 0 ? (
                  <div className="p-6 text-center text-gray-500">
                    <div className="mb-3">
                      <svg className="w-12 h-12 text-gray-300 mx-auto mb-2" fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" viewBox="0 0 24 24" stroke="currentColor">
                        <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                    </div>
                    <div className="text-sm font-medium text-gray-600 mb-1">
                      {t("history.noSearchResults") || "No results found"}
                    </div>
                    <div className="text-xs text-gray-400">
                      {t("history.tryDifferentSearch") || `Try searching for something else`}
                    </div>
                  </div>
                ) : (
                  <div className="divide-y divide-gray-100">
                    <div className="px-4 py-2 bg-gray-50 text-xs text-gray-600 sticky top-0">
                      {searchResults.length} {t("history.resultsFound") || "results found"}
                    </div>
                    {searchResults.map((conv: Conversation) => (
                      <DropdownMenu.Item
                        key={conv.id}
                        className={`p-4 hover:bg-gray-50 cursor-pointer transition-colors group outline-none ${
                          currentConversation?.id === conv.id
                            ? "bg-blue-50 border-l-4 border-blue-500"
                            : ""
                        }`}
                        onSelect={() => handleConversationClick(conv.id)}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0 pr-3">
                            <h4 className="text-sm font-medium text-gray-900 truncate mb-2">
                              {conv.title}
                            </h4>
                            {conv.preview && (
                              <p className="text-xs text-gray-500 line-clamp-2 mb-1">
                                {conv.preview}
                              </p>
                            )}
                            <div className="flex items-center space-x-3 text-xs text-gray-400">
                              <span>{formatConversationTime(conv.updated_at)}</span>
                              {conv.message_count != null && (
                                <span>
                                  {conv.message_count} {t("history.messageCount")}
                                </span>
                              )}
                            </div>
                          </div>

                          <div className="flex items-center space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={(e) => handleDeleteSingle(conv.id, e as any)}
                              className="text-red-600 hover:text-red-700 p-1 rounded"
                              title={t("history.deleteConversation")}
                              aria-label={t("history.deleteConversation")}
                            >
                              <TrashIcon className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      </DropdownMenu.Item>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              /* Vue normale par groupe */
              <div className="flex-1 overflow-y-auto">
                {conversationGroups.map((group: ConversationGroup, groupIndex: number) => (
                  <div key={groupIndex} className="border-b border-gray-100 last:border-b-0">
                    <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-medium text-gray-700">
                          {getGroupTitle(group.title)}
                        </span>
                        <span className="text-xs text-gray-400">
                          ({group.conversations.length})
                        </span>
                      </div>
                    </div>

                    <div className="divide-y divide-gray-50">
                      {group.conversations.map((conv: Conversation) => (
                        <DropdownMenu.Item
                          key={conv.id}
                          className={`p-4 hover:bg-gray-50 cursor-pointer transition-colors group outline-none ${
                            currentConversation?.id === conv.id
                              ? "bg-blue-50 border-l-4 border-blue-500"
                              : ""
                          }`}
                          onSelect={() => handleConversationClick(conv.id)}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1 min-w-0 pr-3">
                              <h4 className="text-sm font-medium text-gray-900 truncate mb-2">
                                {conv.title}
                              </h4>

                              <div className="flex items-center space-x-3 text-xs text-gray-400">
                                <span>{formatConversationTime(conv.updated_at)}</span>
                                {conv.message_count != null && (
                                  <span>
                                    {conv.message_count} {t("history.messageCount")}
                                  </span>
                                )}
                              </div>
                            </div>

                            <div className="flex items-center space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
                              <button
                                onClick={(e) => handleDeleteSingle(conv.id, e as any)}
                                className="text-red-600 hover:text-red-700 p-1 rounded"
                                title={t("history.deleteConversation")}
                                aria-label={t("history.deleteConversation")}
                              >
                                <TrashIcon className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                        </DropdownMenu.Item>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>
    </div>
  );
});

HistoryMenu.displayName = "HistoryMenu";

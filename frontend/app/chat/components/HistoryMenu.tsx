import React, { useState, useCallback, useMemo } from "react";
import { useTranslation } from "@/lib/languages/i18n";
import { useMenu } from "@/lib/contexts/MenuContext";
import {
  useConversationGroups,
  useConversationActions,
  useCurrentConversation,
} from "../hooks/useChatStore";
import { useAuthStore } from "@/lib/stores/auth";
import { TrashIcon, PlusIcon, MessageCircleIcon } from "../utils/icons";
import type { Conversation, ConversationGroup } from "../../../types";
import { secureLog } from "@/lib/utils/secureLogger";

export const HistoryMenu = React.memo(() => {
  const { t } = useTranslation();
  // const [isOpen, setIsOpen] = useState(false); // ❌ SUPPRIMÉ - Géré par MenuContext
  const { isMenuOpen, toggleMenu, closeMenu: closeMenuContext } = useMenu(); // ✅ NOUVEAU
  const MENU_ID = 'history-menu'; // ✅ NOUVEAU
  const { user } = useAuthStore();

  const { conversationGroups, isLoadingHistory, loadConversations } =
    useConversationGroups();
  const {
    deleteConversation,
    clearAllConversations,
    refreshConversations,
    createNewConversation,
  } = useConversationActions();
  const { currentConversation, loadConversation } = useCurrentConversation();

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

  const handleToggle = useCallback(async () => {
    const currentlyOpen = isMenuOpen(MENU_ID);
    secureLog.log(`[HistoryMenu] Toggle: ${currentlyOpen ? 'closing' : 'opening'}`);

    toggleMenu(MENU_ID); // ✅ MODIFIÉ
    const newIsOpen = !currentlyOpen;

    if (newIsOpen && user && !isLoadingHistory) {
      secureLog.log(
        "🔄 [HistoryMenu] Chargement à l'ouverture du menu",
      );
      try {
        await loadConversations(user.id || user.email);
        secureLog.log("✅ [HistoryMenu] Conversations chargées");
      } catch (error) {
        secureLog.error("❌ [HistoryMenu] Erreur chargement:", error);
      }
    }
  }, [
    isMenuOpen,
    toggleMenu,
    user,
    isLoadingHistory,
    loadConversations,
  ]);

  const handleRefresh = useCallback(
    async (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (!user) return;
      secureLog.log("🔄 [HistoryMenu] Refresh demandé");
      await refreshConversations(user.id || user.email);
    },
    [user, refreshConversations],
  );

  const handleClearAll = useCallback(
    async (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (!user) return;
      if (!confirm(t("history.confirmClearAll"))) return;
      await clearAllConversations(user.id || user.email);
    },
    [user, clearAllConversations, t],
  );

  const handleDeleteSingle = useCallback(
    async (conversationId: string, e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      await deleteConversation(conversationId);
      if (user) await refreshConversations(user.id || user.email);
    },
    [deleteConversation, user, refreshConversations],
  );

  const handleConversationClick = useCallback(
    async (conv: Conversation, e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      await loadConversation(conv.id);
      closeMenuContext(MENU_ID); // ✅ MODIFIÉ
    },
    [loadConversation, closeMenuContext],
  );

  const handleNewConversation = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      createNewConversation();
      closeMenuContext(MENU_ID); // ✅ MODIFIÉ
    },
    [createNewConversation, closeMenuContext],
  );

  const formatConversationTime = useCallback((timestamp: string): string => {
    try {
      let ts = timestamp;
      if (ts && !ts.endsWith("Z") && !/[+-]\d{2}:\d{2}$/.test(ts))
        ts = ts + "Z";
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

  const debugState = useMemo(() => {
    const currentlyOpen = isMenuOpen(MENU_ID);
    const state = {
      isOpen: currentlyOpen,
      totalConversations,
      conversationGroupsLength: conversationGroups.length,
      isLoadingHistory,
      hasUser: !!user,
    };

    if (currentlyOpen || totalConversations > 0) {
      secureLog.log("[HistoryMenu] État actuel:", state);
    }

    return state;
  }, [
    isMenuOpen,
    totalConversations,
    conversationGroups.length,
    isLoadingHistory,
    user,
  ]);

  const conversationsList = useMemo(() => {
    if (isLoadingHistory) {
      return (
        <div className="p-6 text-center text-gray-500">
          <div className="flex items-center justify-center space-x-3 mb-2">
            <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
            <span>{t("history.loadingConversations")}</span>
          </div>
          <p className="text-xs text-gray-400">
            {t("history.retrievingHistory")}
          </p>
        </div>
      );
    }

    if (conversationGroups.length === 0) {
      return (
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

          <button
            onClick={handleNewConversation}
            className="inline-flex items-center space-x-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 transition-colors"
          >
            <PlusIcon className="w-4 h-4" />
            <span>{t("history.newConversation")}</span>
          </button>

          {user && (
            <button
              onClick={handleRefresh}
              className="ml-2 text-blue-600 hover:text-blue-700 text-xs underline"
              disabled={isLoadingHistory}
            >
              {t("history.refresh")}
            </button>
          )}
        </div>
      );
    }

    return conversationGroups.map(
      (group: ConversationGroup, groupIndex: number) => (
        <div
          key={groupIndex}
          className="border-b border-gray-100 last:border-b-0"
        >
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
              <div
                key={conv.id}
                className={`p-4 hover:bg-gray-50 cursor-pointer transition-colors group ${
                  currentConversation?.id === conv.id
                    ? "bg-blue-50 border-l-4 border-blue-500"
                    : ""
                }`}
                onClick={(e) => handleConversationClick(conv, e)}
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
                      onClick={(e) => handleDeleteSingle(conv.id, e)}
                      className="text-red-600 hover:text-red-700 p-1 rounded"
                      title={t("history.deleteConversation")}
                      aria-label={t("history.deleteConversation")}
                    >
                      <TrashIcon className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ),
    );
  }, [
    isLoadingHistory,
    conversationGroups,
    user,
    currentConversation?.id,
    handleNewConversation,
    handleRefresh,
    handleConversationClick,
    handleDeleteSingle,
    formatConversationTime,
    getGroupTitle,
    t,
  ]);

  const notificationBadge = useMemo(() => {
    if (totalConversations <= 0) return null;

    return <span className="notification-badge">{totalConversations}</span>;
  }, [totalConversations]);

  const handleCloseMenu = useCallback(() => {
    closeMenuContext(MENU_ID); // ✅ MODIFIÉ
  }, [closeMenuContext]);

  return (
    <div className="relative header-icon-container">
      <button
        onClick={handleToggle}
        className="w-10 h-10 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors flex items-center justify-center border border-gray-200"
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

      {notificationBadge}

      {isMenuOpen(MENU_ID) && (
        <div className="absolute left-0 top-full mt-2 w-96 bg-white rounded-lg shadow-xl border border-gray-200 z-50 max-h-[70vh] overflow-hidden flex flex-col">
          <div className="flex-1 overflow-y-auto">{conversationsList}</div>
        </div>
      )}
    </div>
  );
});

HistoryMenu.displayName = "HistoryMenu";
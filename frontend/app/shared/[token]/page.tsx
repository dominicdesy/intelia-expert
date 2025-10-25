"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { MessageCircle, Clock, Eye, AlertCircle, Loader2 } from "lucide-react";
import { secureLog } from "@/lib/utils/secureLogger";
import { useTranslation } from "@/lib/languages/i18n";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sequence_number: number;
  created_at: string;
}

interface Conversation {
  id: string;
  language: string;
  created_at: string;
  messages: Message[];
  message_count: number;
}

interface ShareInfo {
  anonymized: boolean;
  shared_by: string;
  view_count: number;
  expires_at: string | null;
}

interface SharedConversationData {
  conversation: Conversation;
  share_info: ShareInfo;
}

export default function SharedConversationPage() {
  const params = useParams();
  const router = useRouter();
  const token = params?.token as string;
  const { t } = useTranslation();

  const [data, setData] = useState<SharedConversationData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setError(t("error.invalidShareToken") || "Token de partage invalide");
      setIsLoading(false);
      return;
    }

    const fetchSharedConversation = async () => {
      try {
        const response = await fetch(
          `https://expert.intelia.com/api/v1/shared/${token}`
        );

        if (!response.ok) {
          if (response.status === 404) {
            throw new Error(t("shared.notFound"));
          } else if (response.status === 410) {
            throw new Error(t("shared.expired"));
          } else {
            throw new Error(t("shared.loadError"));
          }
        }

        const result = await response.json();
        setData(result);
      } catch (err: any) {
        setError(err.message || t("shared.error"));
        secureLog.error("Erreur chargement conversation partagée:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchSharedConversation();
  }, [token]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 flex items-center justify-center p-4">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">{t("shared.loading")}</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 to-orange-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-xl shadow-lg p-8 text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            {t("shared.unavailable")}
          </h1>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={() => router.push("/")}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            {t("shared.backToHome")}
          </button>
        </div>
      </div>
    );
  }

  const { conversation, share_info } = data;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      {/* Header avec branding */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                <MessageCircle className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">{t("shared.title")}</h1>
                <p className="text-sm text-gray-500">{t("shared.subtitle")}</p>
              </div>
            </div>
            <button
              onClick={() => router.push("/")}
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              {t("shared.tryFree")}
            </button>
          </div>
        </div>
      </div>

      {/* Contenu principal */}
      <div className="max-w-4xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Informations sur le partage */}
        <div className="bg-blue-50 border border-blue-100 rounded-lg p-4 mb-6">
          <div className="flex items-start gap-3">
            <MessageCircle className="w-5 h-5 text-blue-600 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm text-blue-900 font-medium">
                {t("shared.sharedBy").replace("{name}", share_info.shared_by)}
              </p>
              <div className="flex items-center gap-4 mt-2 text-xs text-blue-700">
                <div className="flex items-center gap-1">
                  <Eye size={14} />
                  <span>{t(share_info.view_count > 1 ? "shared.viewCountPlural" : "shared.viewCount").replace("{count}", String(share_info.view_count))}</span>
                </div>
                {share_info.expires_at && (
                  <div className="flex items-center gap-1">
                    <Clock size={14} />
                    <span>
                      {t("shared.expiresOn").replace("{date}", new Date(share_info.expires_at).toLocaleDateString("fr-FR"))}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Messages de la conversation */}
        <div className="space-y-6 mb-8">
          {conversation.messages.map((message) => (
            <div
              key={message.id}
              className={`${
                message.role === "user"
                  ? "bg-white border border-gray-200"
                  : "bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100"
              } rounded-xl p-6 shadow-sm`}
            >
              <div className="flex items-start gap-4">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                    message.role === "user"
                      ? "bg-gray-200 text-gray-700"
                      : "bg-blue-600 text-white"
                  }`}
                >
                  {message.role === "user" ? "Q" : "A"}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-semibold text-gray-900">
                      {message.role === "user" ? t("shared.question") : t("shared.answer")}
                    </span>
                    <span className="text-xs text-gray-500">
                      {new Date(message.created_at).toLocaleDateString("fr-FR", {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                  <div className="prose prose-sm max-w-none text-gray-700">
                    {message.content}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* CTA pour créer un compte */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl p-8 text-center text-white shadow-lg">
          <h2 className="text-2xl font-bold mb-2">
            {t("shared.impressed")}
          </h2>
          <p className="text-blue-100 mb-6 max-w-2xl mx-auto">
            {t("shared.createFreeAccount")}
          </p>
          <div className="flex items-center justify-center gap-4">
            <button
              onClick={() => router.push("/auth/register")}
              className="px-8 py-3 bg-white text-blue-600 rounded-lg font-semibold hover:bg-gray-50 transition-colors shadow-md"
            >
              {t("shared.createAccount")}
            </button>
            <button
              onClick={() => router.push("/auth/login")}
              className="px-8 py-3 bg-blue-700 text-white rounded-lg font-semibold hover:bg-blue-800 transition-colors"
            >
              {t("shared.signIn")}
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-sm text-gray-500">
          <p>
            {t("shared.generatedBy")}{" "}
            <a
              href="https://expert.intelia.com"
              className="text-blue-600 hover:text-blue-700 font-medium"
            >
              {t("shared.title")}
            </a>
          </p>
          {share_info.anonymized && (
            <p className="mt-1 text-xs text-gray-400">
              {t("shared.dataAnonymized")}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

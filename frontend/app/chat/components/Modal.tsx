import { ModalProps } from "../../../types";
import { useTranslation } from "@/lib/languages/i18n";

// ==================== MODAL CORRIGÉE - PROBLÈME DU CARRÉ RÉSOLU ====================
export const Modal = ({ isOpen, onClose, title, children }: ModalProps) => {
  const { t } = useTranslation();

  if (!isOpen) return null;

  return (
    <>
      {/* UN SEUL overlay centralisé - Combine background + centering */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        {/* Modal Container - exactement comme UserInfoModal */}
        <div
          className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl"
              aria-label={t("modal.close")}
              title={t("modal.close")}
            >
              ×
            </button>
          </div>

          {/* Content */}
          <div className="p-6">{children}</div>
        </div>
      </div>
    </>
  );
};

/**
 * Imageuploadaccumulator
 * Version: 1.4.1
 * Last modified: 2025-10-26
 */
// app/chat/components/ImageUploadAccumulator.tsx
"use client";

import React, { useState, useRef } from "react";
import { uploadTempImage, deleteTempImages } from "../services/apiService";
import { secureLog } from "@/lib/utils/secureLogger";

interface UploadedImage {
  image_id: string;
  filename: string;
  size: number;
  preview_url: string;
  upload_time: number;
}

interface ImageUploadAccumulatorProps {
  sessionId: string;
  onImagesReady: (count: number) => void;
  onAnalyzeClick: () => void;
  disabled?: boolean;
}

export const ImageUploadAccumulator: React.FC<ImageUploadAccumulatorProps> = ({
  sessionId,
  onImagesReady,
  onAnalyzeClick,
  disabled = false,
}) => {
  const [images, setImages] = useState<UploadedImage[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    const file = files[0];

    // Validation
    const allowedTypes = ["image/jpeg", "image/jpg", "image/png", "image/webp"];
    if (!allowedTypes.includes(file.type)) {
      setUploadError("Type de fichier non supporté. Utilisez JPG, PNG ou WebP.");
      return;
    }

    const maxSize = 10 * 1024 * 1024; // 10 MB
    if (file.size > maxSize) {
      setUploadError("Image trop volumineuse. Maximum 10 MB.");
      return;
    }

    setUploadError(null);
    setUploading(true);

    try {
      // Créer preview local
      const previewUrl = URL.createObjectURL(file);

      // Upload au backend
      const result = await uploadTempImage(file, sessionId);

      if (!result.success || !result.image_id) {
        throw new Error(result.error || "Échec de l'upload");
      }

      // Ajouter à la liste
      const newImage: UploadedImage = {
        image_id: result.image_id,
        filename: result.filename || file.name,
        size: result.size || file.size,
        preview_url: previewUrl,
        upload_time: Date.now(),
      };

      setImages((prev) => {
        const updated = [...prev, newImage];
        onImagesReady(updated.length);
        return updated;
      });

      secureLog.log(`[ImageUploader] Image uploaded successfully: ${result.image_id}`);
    } catch (error) {
      secureLog.error("[ImageUploader] Upload error:", error);
      setUploadError(
        error instanceof Error ? error.message : "Erreur d'upload de l'image"
      );
    } finally {
      setUploading(false);
      // Reset input
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleRemoveImage = (imageId: string) => {
    setImages((prev) => {
      const updated = prev.filter((img) => img.image_id !== imageId);

      // Libérer l'URL de preview
      const removedImage = prev.find((img) => img.image_id === imageId);
      if (removedImage) {
        URL.revokeObjectURL(removedImage.preview_url);
      }

      onImagesReady(updated.length);
      return updated;
    });
  };

  const handleClearAll = async () => {
    // Libérer toutes les URLs de preview
    images.forEach((img) => URL.revokeObjectURL(img.preview_url));

    // Nettoyer côté serveur
    try {
      await deleteTempImages(sessionId);
    } catch (error) {
      secureLog.warn("[ImageUploader] Error clearing server images:", error);
    }

    setImages([]);
    onImagesReady(0);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="w-full space-y-4">
      {/* Section d'upload */}
      <div className="flex flex-col sm:flex-row gap-3">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/jpg,image/png,image/webp"
          onChange={handleFileSelect}
          disabled={disabled || uploading}
          className="hidden"
          id="image-upload-input"
          aria-label="Sélectionner une image à télécharger"
        />

        <label
          htmlFor="image-upload-input"
          className={`
            flex-1 px-4 py-3 border-2 border-dashed rounded-lg text-center cursor-pointer
            transition-all duration-200
            ${
              disabled || uploading
                ? "border-gray-300 bg-gray-50 text-gray-400 cursor-not-allowed"
                : "border-blue-300 bg-blue-50 hover:bg-blue-100 text-blue-700 hover:border-blue-400"
            }
          `}
        >
          <div className="flex items-center justify-center gap-2">
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m8-8H4"
              />
            </svg>
            <span className="font-medium">
              {uploading ? "Upload en cours..." : "Ajouter une image"}
            </span>
          </div>
        </label>

        {images.length > 0 && (
          <button
            onClick={onAnalyzeClick}
            disabled={disabled || uploading}
            className="px-6 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-semibold rounded-lg transition-colors duration-200 flex items-center gap-2"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
              />
            </svg>
            Analyser {images.length} image{images.length > 1 ? "s" : ""}
          </button>
        )}
      </div>

      {/* Message d'erreur */}
      {uploadError && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          <div className="flex items-start gap-2">
            <svg
              className="w-5 h-5 mt-0.5 flex-shrink-0"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
            <span>{uploadError}</span>
          </div>
        </div>
      )}

      {/* Liste des images uploadées */}
      {images.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-gray-700">
              Images sélectionnées ({images.length})
            </h4>
            <button
              onClick={handleClearAll}
              disabled={disabled}
              className="text-xs text-red-600 hover:text-red-800 font-medium disabled:text-gray-400"
            >
              Tout supprimer
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {images.map((image) => (
              <div
                key={image.image_id}
                className="relative group bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-md transition-shadow duration-200"
              >
                {/* Preview image */}
                <div className="aspect-square bg-gray-100">
                  <img
                    src={image.preview_url}
                    alt={image.filename}
                    className="w-full h-full object-cover"
                  />
                </div>

                {/* Info overlay */}
                <div className="p-2 bg-white border-t border-gray-200">
                  <p className="text-xs font-medium text-gray-700 truncate">
                    {image.filename}
                  </p>
                  <p className="text-xs text-gray-500">
                    {formatFileSize(image.size)}
                  </p>
                </div>

                {/* Remove button */}
                <button
                  onClick={() => handleRemoveImage(image.image_id)}
                  disabled={disabled}
                  className="absolute top-2 right-2 p-1.5 bg-red-500 hover:bg-red-600 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-200 disabled:opacity-50"
                  title="Supprimer"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Message informatif */}
      {images.length === 0 && !uploading && (
        <div className="text-center py-8 text-gray-500 text-sm">
          <svg
            className="w-12 h-12 mx-auto mb-3 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          <p className="font-medium mb-1">Aucune image sélectionnée</p>
          <p className="text-xs">
            Ajoutez une ou plusieurs images pour analyse comparative
          </p>
        </div>
      )}
    </div>
  );
};

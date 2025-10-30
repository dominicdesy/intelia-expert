/**
 * SearchableSelect - Generic searchable dropdown component
 * Version: 1.0.0
 * Date: 2025-10-30
 */
"use client";

import React, { useState, useEffect, useRef } from "react";

export interface SearchableSelectItem {
  id: string;
  label: string;
  subtitle?: string;
  data?: any; // Additional data to pass through
}

interface SearchableSelectProps {
  items: SearchableSelectItem[];
  onSelect: (item: SearchableSelectItem) => void;
  placeholder?: string;
  selectedId?: string;
  className?: string;
  emptyMessage?: string;
}

export const SearchableSelect: React.FC<SearchableSelectProps> = ({
  items,
  onSelect,
  placeholder = "Rechercher...",
  selectedId,
  className = "",
  emptyMessage = "Aucun résultat trouvé"
}) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [filteredItems, setFilteredItems] = useState<SearchableSelectItem[]>(items);
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Filter items based on search term
  useEffect(() => {
    if (!searchTerm) {
      setFilteredItems(items);
      return;
    }

    const term = searchTerm.toLowerCase();
    const filtered = items.filter(item =>
      item.label.toLowerCase().includes(term) ||
      item.subtitle?.toLowerCase().includes(term) ||
      item.id.toLowerCase().includes(term)
    );

    setFilteredItems(filtered);
    setHighlightedIndex(0);
  }, [searchTerm, items]);

  // Handle click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Get selected item display
  const selectedItem = items.find(item => item.id === selectedId);

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === "Enter" || e.key === "ArrowDown") {
        setIsOpen(true);
        e.preventDefault();
      }
      return;
    }

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setHighlightedIndex(prev =>
          prev < filteredItems.length - 1 ? prev + 1 : prev
        );
        break;
      case "ArrowUp":
        e.preventDefault();
        setHighlightedIndex(prev => prev > 0 ? prev - 1 : prev);
        break;
      case "Enter":
        e.preventDefault();
        if (filteredItems[highlightedIndex]) {
          handleSelect(filteredItems[highlightedIndex]);
        }
        break;
      case "Escape":
        e.preventDefault();
        setIsOpen(false);
        setSearchTerm("");
        break;
    }
  };

  const handleSelect = (item: SearchableSelectItem) => {
    onSelect(item);
    setIsOpen(false);
    setSearchTerm("");
  };

  const handleInputFocus = () => {
    setIsOpen(true);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
    if (!isOpen) setIsOpen(true);
  };

  const highlightText = (text: string, highlight: string) => {
    if (!highlight.trim()) {
      return <span>{text}</span>;
    }

    const regex = new RegExp(`(${highlight.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    const parts = text.split(regex);

    return (
      <span>
        {parts.map((part, i) =>
          regex.test(part) ? (
            <mark key={i} className="bg-yellow-200 font-semibold">
              {part}
            </mark>
          ) : (
            <span key={i}>{part}</span>
          )
        )}
      </span>
    );
  };

  return (
    <div className={`relative ${className}`}>
      {/* Selected value display (when not focused) */}
      {!isOpen && selectedItem && (
        <div
          onClick={() => {
            setIsOpen(true);
            inputRef.current?.focus();
          }}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-white cursor-pointer hover:border-blue-500 transition-colors"
        >
          <div className="text-sm font-medium text-gray-900">
            {selectedItem.label}
          </div>
          {selectedItem.subtitle && (
            <div className="text-xs text-gray-500 mt-1">
              {selectedItem.subtitle}
            </div>
          )}
        </div>
      )}

      {/* Search input */}
      {(!selectedItem || isOpen) && (
        <input
          ref={inputRef}
          type="text"
          value={searchTerm}
          onChange={handleInputChange}
          onFocus={handleInputFocus}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      )}

      {/* Dropdown results */}
      {isOpen && (
        <div
          ref={dropdownRef}
          className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-64 overflow-auto"
        >
          {/* Results count */}
          {filteredItems.length > 0 && (
            <div className="px-3 py-2 text-xs text-gray-500 border-b border-gray-100">
              {filteredItems.length} résultat{filteredItems.length > 1 ? 's' : ''}
            </div>
          )}

          {/* Items list */}
          {filteredItems.length > 0 ? (
            <ul className="py-1">
              {filteredItems.map((item, index) => (
                <li
                  key={item.id}
                  onClick={() => handleSelect(item)}
                  className={`px-3 py-2 cursor-pointer transition-colors ${
                    index === highlightedIndex
                      ? 'bg-blue-50 border-l-2 border-blue-500'
                      : 'hover:bg-gray-50'
                  } ${selectedId === item.id ? 'bg-blue-100' : ''}`}
                  onMouseEnter={() => setHighlightedIndex(index)}
                >
                  <div className="text-sm font-medium text-gray-900">
                    {highlightText(item.label, searchTerm)}
                  </div>
                  {item.subtitle && (
                    <div className="text-xs text-gray-500 mt-1">
                      {highlightText(item.subtitle, searchTerm)}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <div className="px-3 py-8 text-center text-sm text-gray-500">
              {emptyMessage}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

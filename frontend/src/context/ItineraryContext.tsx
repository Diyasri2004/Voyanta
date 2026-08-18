"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";

export interface ItineraryItem {
  id?: string;
  name?: string;
  title?: string;
  category?: string;
  description?: string;
  location?: string;
  address?: string;
  navigation_url?: string;
  maps_url?: string;
  image_url?: string;
  image?: string;
}

interface ItineraryContextType {
  savedItems: ItineraryItem[];
  count: number;
  toggleItem: (item: ItineraryItem) => void;
  addItem: (item: ItineraryItem) => void;
  removeItem: (target: number | string) => void;
  clearAll: () => void;
  isSaved: (item: ItineraryItem) => boolean;
}

const ItineraryContext = createContext<ItineraryContextType | undefined>(undefined);

export function ItineraryProvider({ children }: { children: ReactNode }) {
  const [savedItems, setSavedItems] = useState<ItineraryItem[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const local = localStorage.getItem("voyanta_itinerary");
      return local ? JSON.parse(local) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem("voyanta_itinerary", JSON.stringify(savedItems));
    } catch {}
  }, [savedItems]);

  const isSaved = (item: ItineraryItem) => {
    const itemTitle = (item.name || item.title || "").toLowerCase().trim();
    return savedItems.some(
      (i) => (i.name || i.title || "").toLowerCase().trim() === itemTitle
    );
  };

  const toggleItem = (item: ItineraryItem) => {
    const itemTitle = (item.name || item.title || "").toLowerCase().trim();
    setSavedItems((prev) =>
      prev.some((i) => (i.name || i.title || "").toLowerCase().trim() === itemTitle)
        ? prev.filter((i) => (i.name || i.title || "").toLowerCase().trim() !== itemTitle)
        : [...prev, item]
    );
  };

  const addItem = (item: ItineraryItem) => {
    if (!isSaved(item)) {
      setSavedItems((prev) => [...prev, item]);
    }
  };

  const removeItem = (target: number | string) => {
    setSavedItems((prev) => {
      if (typeof target === "number") {
        return prev.filter((_, idx) => idx !== target);
      }
      return prev.filter(
        (i) => (i.name || i.title || "").toLowerCase().trim() !== target.toLowerCase().trim()
      );
    });
  };

  const clearAll = () => {
    setSavedItems([]);
  };

  return (
    <ItineraryContext.Provider
      value={{
        savedItems,
        count: savedItems.length,
        toggleItem,
        addItem,
        removeItem,
        clearAll,
        isSaved,
      }}
    >
      {children}
    </ItineraryContext.Provider>
  );
}

export function useItinerary() {
  const context = useContext(ItineraryContext);
  if (!context) {
    throw new Error("useItinerary must be used within an ItineraryProvider");
  }
  return context;
}

"use client";

import React, { createContext, useContext, useState, ReactNode } from "react";

// Static exchange rates relative to 1 USD
const EXCHANGE_RATES: Record<string, number> = {
  USD: 1,
  EUR: 0.92,
  GBP: 0.79,
  INR: 83.5,
  JPY: 153.2,
  AUD: 1.54,
  CAD: 1.37,
  AED: 3.67,
  SGD: 1.36,
};

const SYMBOLS: Record<string, string> = {
  USD: "$",
  EUR: "€",
  GBP: "£",
  INR: "₹",
  JPY: "¥",
  AUD: "A$",
  CAD: "C$",
  AED: "د.إ",
  SGD: "S$",
};

interface CurrencyContextType {
  currency: string;
  setCurrency: (c: string) => void;
  convertCost: (amountInUsd: number) => number;
  formatCost: (amountInUsd: number) => string;
  formatStringRange: (usdRangeString: string) => string; // e.g. converts "$15 - $30 / person" to "₹1200 - ₹2400 / person"
}

const CurrencyContext = createContext<CurrencyContextType | undefined>(undefined);

export function CurrencyProvider({ children }: { children: ReactNode }) {
  const [currency, setCurrency] = useState("USD");

  const convertCost = (amountInUsd: number) => {
    return amountInUsd * (EXCHANGE_RATES[currency] || 1);
  };

  const formatCost = (amountInUsd: number) => {
    const converted = convertCost(amountInUsd);
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: currency,
      maximumFractionDigits: 0,
    }).format(converted);
  };

  const formatStringRange = (usdRangeString: string) => {
    if (!usdRangeString || currency === "USD") return usdRangeString;
    
    // Find all numbers in the string that come after a $ sign
    return usdRangeString.replace(/\$(\d+)/g, (match, p1) => {
      const num = parseInt(p1, 10);
      if (isNaN(num)) return match;
      const converted = Math.round(num * (EXCHANGE_RATES[currency] || 1));
      return `${SYMBOLS[currency]}${converted}`;
    });
  };

  return (
    <CurrencyContext.Provider value={{ currency, setCurrency, convertCost, formatCost, formatStringRange }}>
      {children}
    </CurrencyContext.Provider>
  );
}

export function useCurrency() {
  const context = useContext(CurrencyContext);
  if (!context) {
    throw new Error("useCurrency must be used within a CurrencyProvider");
  }
  return context;
}

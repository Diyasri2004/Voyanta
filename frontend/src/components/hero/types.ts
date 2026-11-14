import type { Dispatch, FormEvent, SetStateAction } from "react";
import type { TranslationDictionary, LanguageName } from "@/lib/i18n";
import type { TravelersState } from "@/app/page";

export interface TrendingDest {
  name: string;
  country?: string;
}

/** Everything the landing needs from the page's trip-planning state. */
export interface LandingProps {
  t: TranslationDictionary;
  language: LanguageName;
  locationInput: string;
  setLocationInput: (v: string) => void;
  startDate: string;
  returnDate: string;
  minStart: string;
  maxReturn: string;
  minReturn: string;
  onStartDate: (v: string) => void;
  onReturnDate: (v: string) => void;
  daysCount: number;
  travelers: TravelersState;
  setTravelers: Dispatch<SetStateAction<TravelersState>>;
  groupLabel: (type: string) => string;
  trending: TrendingDest[];
  loadingTrending: boolean;
  loading: boolean;
  error: string | null;
  onSubmit: (e?: FormEvent) => void;
}

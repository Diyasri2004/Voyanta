"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/** Chat language codes -> BCP-47 tags used by the browser's speech engines. */
const SPEECH_LANG: Record<string, string> = {
  en: "en-IN", hi: "hi-IN", ta: "ta-IN", te: "te-IN", kn: "kn-IN", ml: "ml-IN", bn: "bn-IN",
  ar: "ar-SA", es: "es-ES", fr: "fr-FR", de: "de-DE", zh: "zh-CN", ru: "ru-RU",
};

/** Turn a markdown reply into something pleasant to hear. */
export function toSpeakable(text: string): string {
  return text
    .replace(/\[([^\]]+)\]\s*\([^)]*\)/g, "$1")
    .replace(/https?:\/\/\S+/g, "")
    .replace(/\*\*|__|`|#/g, "")
    .replace(/^\s*[-•]\s+/gm, "")
    .replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 700);
}

/**
 * Voice for the chat: speech-to-text for asking, text-to-speech for answers.
 * Uses the browser's built-in engines (free, no keys). Works in Chrome, Edge, Safari and Android Chrome.
 */
export function useVoice(langCode: string, onFinalTranscript: (text: string) => void, onInterim: (text: string) => void) {
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [canListen, setCanListen] = useState(false);
  const [canSpeak, setCanSpeak] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recRef = useRef<any>(null);
  const finalRef = useRef(onFinalTranscript);
  const interimRef = useRef(onInterim);
  finalRef.current = onFinalTranscript;
  interimRef.current = onInterim;

  useEffect(() => {
    const w = window as any;
    setCanListen(!!(w.SpeechRecognition || w.webkitSpeechRecognition));
    setCanSpeak(typeof window !== "undefined" && "speechSynthesis" in window);
    return () => {
      try { recRef.current?.abort(); } catch {}
      try { window.speechSynthesis?.cancel(); } catch {}
    };
  }, []);

  const stopSpeaking = useCallback(() => {
    try { window.speechSynthesis?.cancel(); } catch {}
    setSpeaking(false);
  }, []);

  const speak = useCallback((text: string) => {
    if (!("speechSynthesis" in window)) return;
    const clean = toSpeakable(text);
    if (!clean) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(clean);
    const tag = SPEECH_LANG[langCode] || "en-IN";
    u.lang = tag;
    const voices = window.speechSynthesis.getVoices();
    const base = tag.split("-")[0];
    const v = voices.find((x) => x.lang === tag) || voices.find((x) => x.lang.startsWith(base));
    if (v) u.voice = v;
    u.rate = 1.02;
    u.onstart = () => setSpeaking(true);
    u.onend = () => setSpeaking(false);
    u.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(u);
  }, [langCode]);

  const stopListening = useCallback(() => {
    try { recRef.current?.stop(); } catch {}
  }, []);

  const startListening = useCallback(() => {
    const w = window as any;
    const SR = w.SpeechRecognition || w.webkitSpeechRecognition;
    if (!SR) { setError("Voice input is not supported in this browser. Try Chrome or Safari."); return; }
    stopSpeaking();
    setError(null);
    const rec = new SR();
    rec.lang = SPEECH_LANG[langCode] || "en-IN";
    rec.interimResults = true;
    rec.continuous = false;
    rec.maxAlternatives = 1;
    let finalText = "";
    rec.onstart = () => setListening(true);
    rec.onresult = (e: any) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i];
        if (r.isFinal) finalText += r[0].transcript;
        else interim += r[0].transcript;
      }
      interimRef.current((finalText + interim).trim());
    };
    rec.onerror = (e: any) => {
      setListening(false);
      if (e.error === "not-allowed" || e.error === "service-not-allowed") setError("Microphone access is blocked. Allow it in your browser's site settings.");
      else if (e.error === "no-speech") setError("I didn't catch that. Tap the mic and try again.");
      else if (e.error !== "aborted") setError("Voice input hit a problem. Please try again.");
    };
    rec.onend = () => {
      setListening(false);
      const t = finalText.trim();
      if (t) finalRef.current(t);
    };
    recRef.current = rec;
    try { rec.start(); } catch { setListening(false); }
  }, [langCode, stopSpeaking]);

  return { listening, speaking, canListen, canSpeak, error, setError, startListening, stopListening, speak, stopSpeaking };
}

"use client";

import { Fragment, useEffect, useState } from "react";

const URL_OK = /^https?:\/\//i;

/** Inline: **bold** and [label](https://url). Anything else stays plain text. */
function inline(text: string, keyBase: string) {
  const out: React.ReactNode[] = [];
  const re = /\*\*([^*]+)\*\*|\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    if (m[1]) {
      out.push(<strong key={`${keyBase}-b${i}`} className="font-semibold text-[#ffe2ae]">{m[1]}</strong>);
    } else if (m[2] && URL_OK.test(m[3])) {
      out.push(
        <a key={`${keyBase}-a${i}`} href={m[3]} target="_blank" rel="noreferrer noopener"
          className="font-medium text-[#7fd6ff] underline decoration-[#7fd6ff]/40 underline-offset-2 hover:decoration-[#7fd6ff]">
          {m[2]}
        </a>
      );
    }
    last = m.index + m[0].length;
    i++;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export function RichText({ text }: { text: string }) {
  const lines = text.split("\n");
  return (
    <div className="space-y-1.5">
      {lines.map((line, idx) => {
        const bullet = /^\s*[-*•]\s+(.*)$/.exec(line);
        if (bullet) {
          return (
            <div key={idx} className="flex gap-2">
              <span className="mt-[0.55em] h-1 w-1 shrink-0 rounded-full bg-[#ffc36b]" />
              <span>{inline(bullet[1], `l${idx}`)}</span>
            </div>
          );
        }
        if (!line.trim()) return <div key={idx} className="h-1" />;
        return <p key={idx}>{inline(line, `l${idx}`)}</p>;
      })}
    </div>
  );
}

/** Make a half-typed string safe to format (no stray ** or unfinished [link]). */
function safePartial(s: string) {
  let t = s;
  const open = t.lastIndexOf("[");
  if (open !== -1 && !/\]\([^)]*\)/.test(t.slice(open))) t = t.slice(0, open);
  if ((t.match(/\*\*/g) || []).length % 2 === 1) t += "**";
  return t;
}

/** Reveals new assistant replies word by word; instant when `animate` is false or motion is reduced. */
export function TypedText({ text, animate }: { text: string; animate: boolean }) {
  const words = text.split(/(\s+)/);
  const [n, setN] = useState(animate ? 0 : words.length);

  useEffect(() => {
    if (!animate || (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches)) {
      setN(words.length);
      return;
    }
    setN(0);
    const step = Math.max(2, Math.ceil(words.length / 90));
    const id = window.setInterval(() => {
      setN((v) => {
        if (v + step >= words.length) {
          window.clearInterval(id);
          return words.length;
        }
        return v + step;
      });
    }, 22);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, animate]);

  const shown = n >= words.length ? text : safePartial(words.slice(0, n).join(""));
  return <RichText text={shown} />;
}

export function Spacer() {
  return <Fragment />;
}

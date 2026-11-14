import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import "./globals.css";
import Providers from "@/components/Providers";

// Fonts are bundled with the app (OFL licensed) so builds never depend on Google Fonts.
const jakarta = localFont({
  src: "./fonts/PlusJakartaSans.ttf",
  variable: "--font-plus-jakarta",
  weight: "200 800",
  display: "swap",
});

const syne = localFont({
  src: "./fonts/Syne.ttf",
  variable: "--font-syne",
  weight: "400 800",
  display: "swap",
});

const serif = localFont({
  src: [
    { path: "./fonts/InstrumentSerif-Regular.ttf", weight: "400", style: "normal" },
    { path: "./fonts/InstrumentSerif-Italic.ttf", weight: "400", style: "italic" },
  ],
  variable: "--font-serif",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Voyanta — Plan your next journey",
  description:
    "Pick a real destination and dates, and Voyanta builds a day-by-day trip with maps, food, events, budget and a local AI guide.",
};

export const viewport: Viewport = {
  themeColor: "#050912",
  colorScheme: "dark",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${jakarta.variable} ${syne.variable} ${serif.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col font-plus-jakarta bg-[#050912] text-white selection:bg-[#ffc36b] selection:text-[#050912]">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

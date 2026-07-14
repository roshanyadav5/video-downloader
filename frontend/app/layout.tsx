import type { Metadata } from "next";
import { Inter, Lexend, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const body = Inter({ subsets: ["latin"], variable: "--font-body" });
const display = Lexend({ subsets: ["latin"], variable: "--font-display", weight: ["500", "600", "700"] });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "Fetchly — Universal Video Downloader",
  description:
    "Download videos from YouTube, TikTok, Instagram, X, Facebook, and dozens more platforms. Pick your quality, we handle the rest.",
  robots: { index: true, follow: true },
};

// Runs before React hydrates, so the correct theme class is already on
// <html> by the time anything paints — no flash of the wrong theme.
// Falls back to a time-of-day default (dark 6pm-6am) when the visitor
// has no stored preference yet.
const themeInitScript = `
(function() {
  try {
    var stored = localStorage.getItem('theme');
    var theme;
    if (stored === 'light' || stored === 'dark') {
      theme = stored;
    } else {
      var hour = new Date().getHours();
      theme = (hour >= 18 || hour < 6) ? 'dark' : 'light';
    }
    if (theme === 'dark') document.documentElement.classList.add('dark');
  } catch (e) {}
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${body.variable} ${display.variable} ${mono.variable}`}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="font-body antialiased">{children}</body>
    </html>
  );
}

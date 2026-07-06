import type { Metadata } from "next";
import { IBM_Plex_Mono, Fjalla_One } from "next/font/google";
import Nav from "@/components/Nav";
import "./globals.css";

const plexMono = IBM_Plex_Mono({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const fjallaOne = Fjalla_One({
  variable: "--font-display",
  subsets: ["latin"],
  weight: "400",
});

export const metadata: Metadata = {
  title: "log-triage",
  description: "Template review console for log-triage",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${plexMono.variable} ${fjallaOne.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <Nav />
        <main className="flex-1 flex flex-col">{children}</main>
      </body>
    </html>
  );
}

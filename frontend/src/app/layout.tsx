import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "@/styles/globals.css";
import { AppShell } from "@/components/layout/AppShell";
import { ClientProvider } from "@/context/ClientContext";
import { UserProvider } from "@/context/UserContext";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Data Axle-Business Intelligence Platform",
  description:
    "Upload documents by client, ask questions in everyday language, and get answers backed by your files.",
  icons: {
    icon: "/dataaxle_logo.jpg",
    shortcut: "/dataaxle_logo.jpg",
    apple: "/dataaxle_logo.jpg",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans`}>
        <ClientProvider>
          <UserProvider>
            <AppShell>{children}</AppShell>
          </UserProvider>
        </ClientProvider>
      </body>
    </html>
  );
}

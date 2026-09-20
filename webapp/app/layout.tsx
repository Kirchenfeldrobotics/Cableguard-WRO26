import type { Metadata } from "next";
import { IBM_Plex_Mono, Poppins } from "next/font/google";

import { AppShell } from "@/components/layout/app-shell";
import { AuthProvider } from "@/lib/auth/auth-context";
import "./globals.css";

const poppins = Poppins({
  variable: "--font-poppins",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: { default: "CableGuard", template: "%s · CableGuard" },
  description: "Rope inspection console for the CableGuard robot",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${poppins.variable} ${plexMono.variable} antialiased`}>
      <body className="font-sans">
        <AuthProvider>
          <AppShell>{children}</AppShell>
        </AuthProvider>
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import { IBM_Plex_Mono, Poppins } from "next/font/google";

import { Sidebar } from "@/components/layout/sidebar";
import { RobotLinkProvider } from "@/lib/robot/robot-link";
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
        <RobotLinkProvider>
          <div className="flex min-h-screen flex-col gap-3 bg-canvas p-3 lg:flex-row lg:gap-0">
            <Sidebar />
            <main className="min-w-0 flex-auto px-4 pt-[22px] pb-[60px] lg:max-w-[1280px] lg:px-[30px]">
              {children}
            </main>
          </div>
        </RobotLinkProvider>
      </body>
    </html>
  );
}

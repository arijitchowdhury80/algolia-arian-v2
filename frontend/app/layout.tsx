import type { Metadata } from "next";
import { Sora } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./globals.css";

const sora = Sora({
  variable: "--font-sora",
  subsets: ["latin"],
  weight: ["300", "400", "600"],
});

export const metadata: Metadata = {
  title: "Prism — Prospect Intelligence",
  description: "Light goes in. Intelligence comes out.",
};

const bypassAuth = process.env.BYPASS_AUTH === "true";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const content = (
    <html lang="en">
      <body
        className={`${sora.variable} font-[family-name:var(--font-sora)] antialiased text-[#23263B]`}
      >
        <TooltipProvider delay={300}>
          {children}
        </TooltipProvider>
      </body>
    </html>
  );

  if (bypassAuth) {
    return content;
  }

  return <ClerkProvider>{content}</ClerkProvider>;
}

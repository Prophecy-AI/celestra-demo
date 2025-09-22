import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Celestra - HCP Targeting Platform",
  description: "Advanced healthcare professional targeting and analytics platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
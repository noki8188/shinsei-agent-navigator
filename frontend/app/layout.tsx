import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "社内申請ナビゲーター",
  description: "申請・承認・問い合わせ業務を支援するマルチエージェント PoC"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  );
}


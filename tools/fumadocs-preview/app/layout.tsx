import type { ReactNode } from "react";
import { RootProvider } from "fumadocs-ui/provider/next";
import "@fontsource/inter/latin-400.css";
import "@fontsource/inter/latin-500.css";
import "@fontsource/inter/latin-600.css";
import "./style.css";

export const metadata = {
  title: "Flashduty Docs",
  icons: { icon: "/saas-favicon.png" },
};

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <html suppressHydrationWarning>
      <body>
        <RootProvider
          search={{ enabled: false }}
          theme={{ defaultTheme: "light", enableSystem: false }}
        >
          {children}
        </RootProvider>
      </body>
    </html>
  );
}

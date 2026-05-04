"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";
import type * as React from "react";
// import type { ThemeProviderProps } from "next-themes/dist/types"; // Removed potentially problematic import

export function ThemeProvider({
  children,
  ...props
}: React.ComponentProps<typeof NextThemesProvider>) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}

"use client";

import { SpecialZoomLevel, Viewer, Worker } from "@react-pdf-viewer/core";
import { defaultLayoutPlugin } from "@react-pdf-viewer/default-layout";
import { Typography } from "@inspect/ui";
import { Loader } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

interface PDFViewerInternalProps {
  pdfUrl: string;
  height?: string;
}

export default function PDFViewerInternal({ pdfUrl }: PDFViewerInternalProps) {
  const { resolvedTheme } = useTheme();
  const [viewerTheme, setViewerTheme] = useState<"dark" | "light">("light");
  const [workerUrl, setWorkerUrl] = useState<string>("/pdf.worker.min.mjs");

  // Create default layout plugin - just remove sidebar
  const defaultLayoutPluginInstance = defaultLayoutPlugin({
    sidebarTabs: () => [],
  });

  useEffect(() => {
    // Ensure theme is applied only on the client-side after mount
    if (resolvedTheme) {
      setViewerTheme(resolvedTheme === "dark" ? "dark" : "light");
    }
  }, [resolvedTheme]);

  useEffect(() => {
    // Detect whether the .mjs worker was copied; fall back to .js
    fetch("/pdf.worker.min.mjs", { method: "HEAD" })
      .then((res) => {
        if (!res.ok) setWorkerUrl("/pdf.worker.min.js");
      })
      .catch(() => setWorkerUrl("/pdf.worker.min.js"));
  }, []);

  return (
    <div className="h-full w-full">
      {/* Use a local worker file */}
      <Worker workerUrl={workerUrl}>
        <div className="w-full h-full">
          <Viewer
            fileUrl={pdfUrl}
            plugins={[defaultLayoutPluginInstance]}
            defaultScale={SpecialZoomLevel.PageWidth}
            theme={viewerTheme}
            // Custom loader matching app-wide design
            renderLoader={() => (
              <div className="flex items-center justify-center h-full w-full">
                <div className="flex flex-col items-center text-center">
                  <Loader className="w-8 h-8 text-primary mb-4 animate-spin" />
                  <Typography variant="h4" weight="strong" className="text-foreground mb-2">
                    Loading Document...
                  </Typography>
                  <Typography variant="body-sm" tone="muted">
                    Please wait while we load the PDF.
                  </Typography>
                </div>
              </div>
            )}
            // Security hardening for CVE-2024-4367: disable eval in PDF.js
            transformGetDocumentParams={(options) => ({
              ...options,
              isEvalSupported: false,
            })}
          />
        </div>
      </Worker>
    </div>
  );
}

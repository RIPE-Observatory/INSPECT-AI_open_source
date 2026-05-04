"use client";

import dynamic from "next/dynamic";

interface ReactPDFViewerProps {
  pdfUrl: string;
  height?: string;
}

// Dynamic import with SSR disabled - official solution for Next.js
const PDFViewerComponent = dynamic(() => import("./PDFViewerInternal"), {
  ssr: false,
});

export default function ReactPDFViewer({ pdfUrl, height = "600px" }: ReactPDFViewerProps) {
  return (
    <div className="w-full h-full">
      <PDFViewerComponent pdfUrl={pdfUrl} height={height} />
    </div>
  );
}

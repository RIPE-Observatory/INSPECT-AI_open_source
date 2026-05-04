"use client";

import { Button, Typography } from "@inspect/ui";
import { TextWithLinks } from "@/components/ui/text-with-links";
import { GripVertical, Maximize2, Minimize2, X } from "lucide-react";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

export interface GuidanceContent {
  title: string;
  guidelines: string;
  example: string;
}

interface GuidanceModalProps {
  isOpen: boolean;
  onClose: () => void;
  checkNumber: string;
  content: GuidanceContent;
}

export function GuidanceModal({
  isOpen,
  onClose,
  checkNumber,
  content,
}: GuidanceModalProps) {
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [activeTab, setActiveTab] = useState<"guidelines" | "example">("guidelines");
  const [isExpanded, setIsExpanded] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  // Track if we've initialized position for this open session
  const hasInitializedRef = useRef(false);

  // Panel dimensions
  const panelWidth = isExpanded ? 560 : 420;
  const panelHeightVh = isExpanded ? 70 : 50;

  // Initialize position on open, reset state on close
  useLayoutEffect(() => {
    if (!isOpen) {
      hasInitializedRef.current = false;
      setActiveTab("guidelines");
      setIsExpanded(false);
      setIsDragging(false);
      return;
    }

    if (!hasInitializedRef.current) {
      setPosition({
        x: window.innerWidth - 420 - 24,
        y: (window.innerHeight - window.innerHeight * 0.5) / 2,
      });
      hasInitializedRef.current = true;
    }
  }, [isOpen]);

  // Calculate bounded position - ensures panel stays in viewport regardless of size
  const boundedX = Math.max(0, Math.min(position.x, window.innerWidth - panelWidth));
  const boundedY = Math.max(0, Math.min(position.y, window.innerHeight - (panelHeightVh / 100 * window.innerHeight)));

  // Drag start handler
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    // Prevent drag if clicking on a button
    if ((e.target as HTMLElement).closest("button")) return;

    e.preventDefault();
    setIsDragging(true);

    const rect = panelRef.current?.getBoundingClientRect();
    if (rect) {
      setDragOffset({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      });
    }
  }, []);

  // Drag move and end handlers
  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      const currentWidth = isExpanded ? 560 : 420;
      const currentHeight = window.innerHeight * (isExpanded ? 0.7 : 0.5);

      const newX = Math.max(0, Math.min(window.innerWidth - currentWidth, e.clientX - dragOffset.x));
      const newY = Math.max(0, Math.min(window.innerHeight - currentHeight, e.clientY - dragOffset.y));

      setPosition({ x: newX, y: newY });
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging, dragOffset, isExpanded]);

  // Handle escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Don't render if not open
  if (!isOpen) return null;

  return (
    <div
      ref={panelRef}
      className={cn(
        "guidance-panel fixed z-50 overflow-hidden rounded-lg border border-border/60",
        "bg-card backdrop-blur-sm shadow-[var(--shadow-base-lg)] flex flex-col",
        isDragging && "cursor-grabbing select-none"
      )}
      style={{
        left: boundedX,
        top: boundedY,
        width: panelWidth,
        height: `${panelHeightVh}vh`,
      }}
    >
      {/* Header - Draggable */}
      <div
        className="px-3 py-2 border-b border-border flex items-center justify-between cursor-grab active:cursor-grabbing select-none bg-muted/30"
        onMouseDown={handleMouseDown}
      >
        {/* Left - drag hint */}
        <div className="flex items-center gap-2 text-muted-foreground">
          <GripVertical className="h-4 w-4" />
          <Typography variant="body-xs" tone="muted">
            Drag to move
          </Typography>
        </div>

        {/* Center - title */}
        <Typography variant="body-sm" weight="strong" className="text-foreground">
          INSPECT-SR Check {checkNumber}
        </Typography>

        {/* Right - expand/close buttons */}
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="h-7 w-7 p-0 rounded hover:bg-muted"
            title={isExpanded ? "Collapse panel" : "Expand panel"}
          >
            {isExpanded ? (
              <Minimize2 className="h-3.5 w-3.5" />
            ) : (
              <Maximize2 className="h-3.5 w-3.5" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-7 w-7 p-0 rounded bg-destructive/10 hover:bg-destructive hover:text-white"
            title="Close panel"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Tab Buttons */}
      <div className="flex gap-2 px-3 py-2 border-b border-border/50">
        <button
          type="button"
          onClick={() => setActiveTab("guidelines")}
          className={cn(
            "flex-1 px-4 py-2 rounded-md text-sm font-medium",
            activeTab === "guidelines"
              ? "bg-primary text-primary-foreground shadow-sm"
              : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground"
          )}
        >
          Guidelines
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("example")}
          className={cn(
            "flex-1 px-4 py-2 rounded-md text-sm font-medium",
            activeTab === "example"
              ? "bg-primary text-primary-foreground shadow-sm"
              : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground"
          )}
        >
          Example
        </button>
      </div>

      {/* Scrollable Content Area */}
      <div className="flex-1 overflow-y-auto px-3 py-3">
        {activeTab === "guidelines" && (
          <div className="rounded-lg border border-border bg-background p-4">
            <Typography
              variant="body-md"
              className="text-foreground leading-relaxed whitespace-pre-wrap"
            >
              <TextWithLinks
                text={content.guidelines}
                className="text-foreground"
                linkClassName="text-info hover:text-info/80 underline [font-size:inherit] break-all"
                showIcon={false}
              />
            </Typography>
          </div>
        )}

        {activeTab === "example" && (
          <div className="rounded-lg border border-border bg-background p-4">
            {content.example ? (
              <>
                <Typography
                  variant="body-sm"
                  weight="strong"
                  className="text-primary mb-3 block"
                >
                  Real-world Example
                </Typography>
                <Typography
                  variant="body-md"
                  className="text-foreground leading-relaxed whitespace-pre-wrap"
                >
                  <TextWithLinks
                    text={content.example}
                    className="text-foreground"
                    linkClassName="text-info hover:text-info/80 underline [font-size:inherit] break-all"
                    showIcon={false}
                  />
                </Typography>
              </>
            ) : (
              <Typography variant="body-md" tone="muted" className="italic">
                No example available for this check.
              </Typography>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

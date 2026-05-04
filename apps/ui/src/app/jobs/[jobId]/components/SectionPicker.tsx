"use client";

import { Check, Search } from "lucide-react";
import React, { useEffect, useId, useState } from "react";

import {
  Button,
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  Popover,
  PopoverContent,
  PopoverTrigger,
  Typography,
} from "@inspect/ui";
import { cn } from "@inspect/ui";

import { type StatusToken, getStatusIcon } from "../utils/shared";

export interface SectionPickerItem {
  id: string;
  label: string;
  description?: string;
  status?: StatusToken;
}

interface SectionPickerProps {
  items: SectionPickerItem[];
  value: string;
  onValueChange: (id: string) => void;
}

export default function SectionPicker({ items, value, onValueChange }: SectionPickerProps) {
  const [open, setOpen] = useState(false);
  const [isMac, setIsMac] = useState(false);
  const commandListId = useId();

  useEffect(() => {
    if (typeof window === "undefined") return;
    const ua = window.navigator.userAgent;
    setIsMac(/Mac|iPhone|iPad|iPod/.test(ua));
  }, []);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "/") return;
      if (!event.metaKey && !event.ctrlKey) return;

      const target = event.target as HTMLElement | null;
      if (target) {
        const tagName = target.tagName;
        const isEditable =
          target.isContentEditable || tagName === "INPUT" || tagName === "TEXTAREA";
        if (isEditable) return;
      }

      event.preventDefault();
      setOpen((prev) => !prev);
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const selected = items.find((item) => item.id === value) ?? items[0];
  const shortcutLabel = isMac ? "⌘ /" : "Ctrl + /";

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className="w-full justify-between shadow-none transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-controls={commandListId}
        >
          <span className="flex items-center gap-2">
            {selected?.status &&
              selected.status !== "unknown" &&
              getStatusIcon(selected.status, "h-4 w-4")}
            <Typography variant="body-sm" weight="strong" as="span" className="truncate">
              {selected?.label ?? "Select section"}
            </Typography>
          </span>
          <Typography variant="body-sm" tone="muted" as="span" className="ml-2">{shortcutLabel}</Typography>
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="w-[var(--radix-popover-trigger-width)] p-0"
        align="start"
        sideOffset={2}
      >
        <Command>
          <CommandInput placeholder="Search sections..." autoFocus={false} />
          <CommandList id={commandListId}>
            <CommandEmpty>
              <Search className="h-12 w-12 text-muted-foreground/40 mb-4" />
              <div className="text-center space-y-1">
                <Typography variant="body-sm" weight="strong" tone="muted">No sections found</Typography>
                <Typography variant="body-sm" tone="muted" className="opacity-70">
                  Try searching by name or description
                </Typography>
              </div>
            </CommandEmpty>
            <CommandGroup>
              {items.map((item, index) => (
                <React.Fragment key={item.id}>
                  <CommandItem
                    value={item.id}
                    keywords={[item.label, item.description].filter(Boolean) as string[]}
                    onSelect={() => {
                      onValueChange(item.id);
                      setOpen(false);
                    }}
                    className="flex items-start gap-3 px-4 py-3.5"
                  >
                    {item.status && item.status !== "unknown" && (
                      <span className="mt-0.5 flex h-6 w-6 items-center justify-center transition-colors duration-150">
                        {getStatusIcon(item.status, "h-5 w-5")}
                      </span>
                    )}
                    <span className="flex-1 overflow-hidden">
                      <Typography variant="body-sm" weight="strong" as="span" className="block truncate">
                        {item.label}
                      </Typography>
                      {item.description && (
                        <Typography variant="body-xs" tone="muted" as="span" className="block truncate">
                          {item.description}
                        </Typography>
                      )}
                    </span>
                    <Check
                      className={cn(
                        "mt-0.5 h-5 w-5 transition-opacity duration-150",
                        value === item.id ? "opacity-100 text-primary" : "opacity-0",
                      )}
                    />
                  </CommandItem>
                  {index < items.length - 1 && <CommandSeparator />}
                </React.Fragment>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

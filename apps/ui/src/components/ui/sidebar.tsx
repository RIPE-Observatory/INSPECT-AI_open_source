"use client";

import { Slot } from "@radix-ui/react-slot";
import { PanelLeft, X } from "lucide-react";
import * as React from "react";

import { Button, cn, ScrollArea, typographyVariants } from "@inspect/ui";

type SidebarContextValue = {
  open: boolean;
  setOpen: (open: boolean) => void;
  toggle: () => void;
};

const SidebarContext = React.createContext<SidebarContextValue | undefined>(undefined);

function useSidebarContext() {
  const context = React.useContext(SidebarContext);
  if (!context) {
    throw new Error("Sidebar components must be used within a SidebarProvider");
  }
  return context;
}

type SidebarProviderProps = {
  children: React.ReactNode;
  defaultOpen?: boolean;
};

function SidebarProvider({ children, defaultOpen = true }: SidebarProviderProps) {
  const [open, setOpen] = React.useState(defaultOpen);
  const toggle = React.useCallback(() => setOpen((prev) => !prev), []);

  React.useEffect(() => {
    const media = window.matchMedia("(min-width: 768px)");
    const handleChange = (event: MediaQueryListEvent | MediaQueryList) => {
      setOpen(event.matches);
    };

    handleChange(media);
    media.addEventListener("change", handleChange);
    return () => media.removeEventListener("change", handleChange);
  }, []);

  return (
    <SidebarContext.Provider value={{ open, setOpen, toggle }}>
      <div className="flex h-full w-full bg-background">{children}</div>
    </SidebarContext.Provider>
  );
}

const Sidebar = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => {
    const { open } = useSidebarContext();

    return (
      <aside
        ref={ref}
        data-state={open ? "open" : "collapsed"}
        className={cn(
          "relative hidden h-full w-72 shrink-0 flex-col border-r border-border/60 bg-surface transition-all duration-200 ease-[var(--ease-emphasized)] md:flex",
          !open && "-ml-72",
          className,
        )}
        {...props}
      >
        {children}
      </aside>
    );
  },
);
Sidebar.displayName = "Sidebar";

const SidebarMobile = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => {
    const { open, toggle } = useSidebarContext();
    return (
      <div
        ref={ref}
        className={cn(
          "fixed inset-y-0 left-0 z-[var(--z-overlay)] flex w-72 flex-col border-r border-border/60 bg-surface shadow-[var(--shadow-base-lg)] transition-transform duration-200 ease-[var(--ease-emphasized)] md:hidden",
          open ? "translate-x-0" : "-translate-x-full",
          className,
        )}
        {...props}
      >
        <div className="flex items-center justify-between border-b border-border/60 px-4 py-3">
          <span
            className={cn(
              typographyVariants({ variant: "small" }),
              "font-semibold text-foreground",
            )}
          >
            Menu
          </span>
          <Button variant="ghost" size="icon" onClick={toggle} aria-label="Close sidebar">
            <X className="h-4 w-4" />
          </Button>
        </div>
        {children}
      </div>
    );
  },
);
SidebarMobile.displayName = "SidebarMobile";

const SidebarTrigger = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement>
>(({ className, ...props }, ref) => {
  const { toggle } = useSidebarContext();
  return (
    <Button
      ref={ref}
      variant="ghost"
      size="icon"
      className={cn("md:hidden", className)}
      onClick={(event) => {
        toggle();
        props.onClick?.(event);
      }}
      aria-label="Toggle sidebar"
      {...props}
    >
      <PanelLeft className="h-5 w-5" />
    </Button>
  );
});
SidebarTrigger.displayName = "SidebarTrigger";

const SidebarHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("border-b border-border/60 px-4 py-3", className)} {...props} />
  ),
);
SidebarHeader.displayName = "SidebarHeader";

const SidebarContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => (
    <ScrollArea className={cn("flex-1 px-2 py-4", className)}>
      <div ref={ref} className="flex flex-col gap-[var(--space-6)]" {...props}>
        {children}
      </div>
    </ScrollArea>
  ),
);
SidebarContent.displayName = "SidebarContent";

const SidebarFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("mt-auto border-t border-border/60 px-4 py-3", className)}
      {...props}
    />
  ),
);
SidebarFooter.displayName = "SidebarFooter";

const SidebarGroup = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col gap-[var(--space-2)]", className)} {...props} />
  ),
);
SidebarGroup.displayName = "SidebarGroup";

const SidebarGroupLabel = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        typographyVariants({ variant: "small" }),
        "px-2 text-[11px] uppercase tracking-[0.28em] text-muted-foreground",
        className,
      )}
      {...props}
    />
  ),
);
SidebarGroupLabel.displayName = "SidebarGroupLabel";

const SidebarGroupContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col gap-[var(--space-1)]", className)} {...props} />
  ),
);
SidebarGroupContent.displayName = "SidebarGroupContent";

const SidebarMenu = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <nav ref={ref} className={cn("grid gap-[var(--space-1)]", className)} {...props} />
  ),
);
SidebarMenu.displayName = "SidebarMenu";

const SidebarMenuItem = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("group/menu-item", className)} {...props} />
  ),
);
SidebarMenuItem.displayName = "SidebarMenuItem";

type SidebarMenuButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  isActive?: boolean;
  asChild?: boolean;
};

const SidebarMenuButton = React.forwardRef<HTMLButtonElement, SidebarMenuButtonProps>(
  ({ className, isActive, asChild = false, children, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        ref={ref as React.Ref<HTMLButtonElement>}
        data-active={isActive}
        className={cn(
          "flex w-full items-center gap-[var(--space-2)] rounded px-3 py-2",
          typographyVariants({ variant: "small" }),
          "text-sm font-medium text-muted-foreground transition-colors duration-150 ease-[var(--ease-emphasized)]",
          "hover:bg-surface hover:text-foreground data-[active=true]:bg-primary/10 data-[active=true]:text-foreground",
          className,
        )}
        {...props}
      >
        {children}
      </Comp>
    );
  },
);
SidebarMenuButton.displayName = "SidebarMenuButton";

export {
  SidebarProvider,
  useSidebarContext as useSidebar,
  Sidebar,
  SidebarMobile,
  SidebarTrigger,
  SidebarHeader,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
};

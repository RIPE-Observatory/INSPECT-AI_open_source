"use client";

import { AlertCircle, CheckCircle2, Info, XCircle } from "lucide-react";
import { useEffect, useState } from "react";

import { cn, typographyVariants } from "@inspect/ui";

type NotificationType = "success" | "error" | "warning" | "info";

interface AnimatedNotificationProps {
  type?: NotificationType;
  message: string;
  show: boolean;
  onClose?: () => void;
  autoHide?: boolean;
  autoHideDelay?: number;
  className?: string;
  ariaLive?: "polite" | "assertive";
}

const notificationConfig = {
  success: {
    icon: CheckCircle2,
    bgColor: "bg-success/15",
    borderColor: "border-success/40",
    textColor: "text-success",
    iconColor: "text-success",
  },
  error: {
    icon: XCircle,
    bgColor: "bg-destructive/15",
    borderColor: "border-destructive/40",
    textColor: "text-destructive",
    iconColor: "text-destructive",
  },
  warning: {
    icon: AlertCircle,
    bgColor: "bg-warning/15",
    borderColor: "border-warning/40",
    textColor: "text-warning",
    iconColor: "text-warning",
  },
  info: {
    icon: Info,
    bgColor: "bg-info/15",
    borderColor: "border-info/40",
    textColor: "text-info",
    iconColor: "text-info",
  },
};

export function AnimatedNotification({
  type = "success",
  message,
  show,
  onClose,
  autoHide = true,
  autoHideDelay = 3000,
  className,
  ariaLive = "polite",
}: AnimatedNotificationProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);

  const config = notificationConfig[type];
  const Icon = config.icon;

  useEffect(() => {
    if (show) {
      setIsVisible(true);
      setIsAnimating(true);

      if (autoHide) {
        const timer = setTimeout(() => {
          setIsAnimating(false);
          setTimeout(() => {
            setIsVisible(false);
            onClose?.();
          }, 300);
        }, autoHideDelay);

        return () => clearTimeout(timer);
      }
    } else {
      setIsAnimating(false);
      setTimeout(() => {
        setIsVisible(false);
      }, 300);
    }

    return undefined;
  }, [show, autoHide, autoHideDelay, onClose]);

  if (!isVisible) {
    return null;
  }

  return (
    <div
      role="status"
      aria-live={ariaLive}
      aria-atomic="true"
      className={cn(
        "fixed left-1/2 top-20 z-[var(--z-toast)] -translate-x-1/2",
        "flex items-center gap-[var(--space-3)] rounded border bg-surface-elevated/95 px-4 py-3 shadow-[var(--shadow-base-lg)] backdrop-blur-[var(--blur-overlay)] transition-all duration-300 ease-[var(--ease-expressive)]",
        config.bgColor,
        config.borderColor,
        isAnimating ? "translate-y-0 scale-100 opacity-100" : "-translate-y-2 scale-95 opacity-0",
        className,
      )}
    >
      <Icon className={cn("size-5", config.iconColor)} />
      <span
        className={cn(
          typographyVariants({ variant: "small" }),
          "font-medium text-foreground",
          config.textColor,
        )}
      >
        {message}
      </span>
      {!autoHide && onClose && (
        <button
          type="button"
          onClick={() => {
            setIsAnimating(false);
            setTimeout(() => {
              setIsVisible(false);
              onClose();
            }, 300);
          }}
          className={cn(
            "ml-2 rounded p-1 transition-colors duration-200 ease-[var(--ease-emphasized)] hover:bg-foreground/10",
            config.textColor,
          )}
          aria-label="Close notification"
        >
          <XCircle className="size-4" />
        </button>
      )}
    </div>
  );
}

interface SuccessCheckmarkProps {
  show: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function SuccessCheckmark({ show, size = "md", className }: SuccessCheckmarkProps) {
  const sizeConfig = {
    sm: "h-12 w-12",
    md: "h-16 w-16",
    lg: "h-20 w-20",
  } as const;

  if (!show) {
    return null;
  }

  return (
    <div
      className={cn("flex items-center justify-center animate-scale-in", className)}
      role="img"
      aria-label="Success"
    >
      <div
        className={cn(
          "animate-pulse-once rounded bg-success/20 p-3 shadow-[var(--shadow-base-md)]",
          sizeConfig[size],
        )}
      >
        <CheckCircle2 className="h-full w-full animate-check text-success" />
      </div>
    </div>
  );
}

interface LoadingDotsProps {
  className?: string;
}

export function LoadingDots({ className }: LoadingDotsProps) {
  return (
    <div className={cn("flex items-center gap-[var(--space-2)]", className)} aria-label="Loading">
      <span className="h-2 w-2 animate-bounce rounded bg-current [animation-delay:-0.3s]" />
      <span className="h-2 w-2 animate-bounce rounded bg-current [animation-delay:-0.15s]" />
      <span className="h-2 w-2 animate-bounce rounded bg-current" />
    </div>
  );
}

interface ProgressStepsProps {
  steps: string[];
  currentStep: number;
  className?: string;
}

export function ProgressSteps({ steps, currentStep, className }: ProgressStepsProps) {
  return (
    <div
      className={cn("flex items-center justify-between", className)}
      role="progressbar"
      aria-valuenow={currentStep + 1}
      aria-valuemin={1}
      aria-valuemax={steps.length}
    >
      {steps.map((step, index) => {
        const isActive = index === currentStep;
        const isCompleted = index < currentStep;

        return (
          <div key={step} className="flex items-center">
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  "flex size-10 items-center justify-center rounded border-2 transition-all duration-300 ease-[var(--ease-emphasized)]",
                  isCompleted
                    ? "border-primary bg-primary text-primary-foreground"
                    : isActive
                      ? "border-primary text-primary"
                      : "border-border/70 text-muted-foreground",
                )}
              >
                {isCompleted ? (
                  <CheckCircle2 className="size-5" />
                ) : (
                  <span className="text-sm font-semibold">{index + 1}</span>
                )}
              </div>
              <span
                className={cn(
                  "mt-2 text-xs font-medium transition-colors duration-300 ease-[var(--ease-emphasized)]",
                  isActive ? "text-foreground" : "text-muted-foreground",
                )}
              >
                {step}
              </span>
            </div>
            {index < steps.length - 1 && (
              <div className="flex items-center">
                <div
                  className={cn(
                    "mx-4 h-0.5 w-12 transition-all duration-300 ease-[var(--ease-emphasized)] sm:w-20",
                    index < currentStep ? "bg-primary" : "bg-border/70",
                  )}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

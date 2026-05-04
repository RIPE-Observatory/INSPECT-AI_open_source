import { Label, Typography } from "@inspect/ui";
import { AlertTriangle, Check, HelpCircle, Loader, X } from "lucide-react";
import type React from "react";

export type StatusToken = "ok" | "concern" | "attention" | "pending" | "unknown";

export type DataPointStatusType = StatusToken | null;

const STATUS_ICON: Record<
  StatusToken,
  { icon: React.ComponentType<{ className?: string }>; className: string }
> = {
  ok: { icon: Check, className: "text-emerald-400" },
  concern: { icon: X, className: "text-destructive" },
  attention: { icon: AlertTriangle, className: "text-amber-400" },
  pending: { icon: Loader, className: "text-info animate-spin" },
  unknown: { icon: HelpCircle, className: "text-slate-400" },
};

const LEGACY_STATUS_MAP: Record<string, StatusToken> = {
  PASSED: "ok",
  COMPLETED: "ok",
  PROSPECTIVE: "ok",
  FAILED: "attention",
  WARNING: "attention",
  COMPLETED_NOT_FOUND: "attention",
  RETROSPECTIVE: "concern",
  RUNNING: "pending",
  PENDING: "pending",
  LOADING: "pending",
  INDETERMINATE: "unknown",
  NOT_FOUND: "attention",
  COMPLETED_EMPTY: "attention",
};

const normalizeStatusToken = (
  status: DataPointStatusType | string | undefined | null,
): StatusToken => {
  if (!status) return "unknown";
  if (typeof status === "string" && status in STATUS_ICON) {
    return status as StatusToken;
  }

  const key = status.toString().trim().toUpperCase();
  return LEGACY_STATUS_MAP[key] ?? "unknown";
};

export const mapBackendCheckStatusToDataPointStatus = (
  backendStatus?: string,
): DataPointStatusType => {
  if (!backendStatus) return null;

  const upperBackendStatus = backendStatus.toUpperCase();

  if (upperBackendStatus.includes("COMPLETED_SUCCESS")) return "ok";
  if (upperBackendStatus.includes("COMPLETED_NOT_FOUND")) return "attention";
  if (upperBackendStatus.includes("PROSPECTIVE")) return "ok";
  if (upperBackendStatus.includes("RETROSPECTIVE")) return "concern";
  if (upperBackendStatus.includes("DOI_NOT_FOUND_IN_DATABASE")) return "attention";
  if (upperBackendStatus.includes("RUNNING") || upperBackendStatus.includes("PENDING"))
    return "pending";
  if (
    upperBackendStatus.includes("COMPLETED_EMPTY") ||
    upperBackendStatus.includes("NOT_FOUND") ||
    upperBackendStatus.includes("INDETERMINATE")
  )
    return "unknown";
  if (upperBackendStatus.includes("FAILED") || upperBackendStatus.includes("ERROR"))
    return "attention";
  if (
    upperBackendStatus.includes("COMPLETED_PARTIAL") ||
    upperBackendStatus.includes("WITH_WARNINGS")
  )
    return "attention";

  return "unknown";
};

export const getStatusIcon = (status: string | undefined | null, iconSize = "h-4 w-4") => {
  const token = normalizeStatusToken(status ?? null);
  const { icon: Icon, className } = STATUS_ICON[token];
  return <Icon className={`${iconSize} ${className}`} />;
};

export const DataPoint = ({
  label,
  value,
  valueClassName,
  status,
  interpretation,
  isLoading,
  systemComment,
}: {
  label: React.ReactNode;
  value?: React.ReactNode;
  valueClassName?: string;
  status?: DataPointStatusType;
  interpretation?: string | null;
  isLoading?: boolean;
  systemComment?: React.ReactNode | string | null;
}) => (
  <div className="p-4 rounded border border-border bg-card/50 shadow-sm min-h-[auto]">
    <div className="flex items-center justify-between">
      <Label className="text-foreground">
        <Typography variant="body-sm" weight="strong" as="span">{label}</Typography>
      </Label>
      {isLoading ? (
        <div className="flex items-center gap-2">
          {getStatusIcon("LOADING", "h-4 w-4")}
          <Typography variant="body-xs" tone="muted" as="span">Loading...</Typography>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          {value && (
            <Typography variant="body-sm" className={valueClassName || "text-foreground"}>{value}</Typography>
          )}
          {getStatusIcon(status ?? undefined, "h-4 w-4")}
        </div>
      )}
    </div>
    {!isLoading && (systemComment || interpretation) && (
      <div className="my-2 border-t border-border" />
    )}
    {!isLoading && systemComment && (
      <Typography variant="body-sm" tone="muted" className="mb-1">System Comment: {systemComment}</Typography>
    )}
    {!isLoading && interpretation && (
      <Typography variant="body-sm" tone="muted">AI Comment: {interpretation}</Typography>
    )}
    {!isLoading &&
      !value &&
      !interpretation &&
      !systemComment &&
      status !== "ok" &&
      status !== "pending" && (
        <div className="flex items-center justify-between mt-1">
          <div />
          <Typography variant="body-sm" tone="muted">Not available</Typography>
        </div>
      )}
  </div>
);

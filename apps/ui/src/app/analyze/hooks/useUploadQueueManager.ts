import { useCallback, useEffect, useRef, useState } from "react";

// Types for upload queue
export interface UploadedFile {
  id: string; // Unique identifier for React key
  file: File; // Store the actual File object
  progress: number;
  status: "pending" | "queued" | "uploading" | "processing" | "completed" | "error";
  jobId?: string;
  error?: string;
  timestamp: Date;
  isPlaceholder?: boolean; // Indicates file was reconstructed and needs re-selection
  originalSize?: number;
  queuePosition?: number; // Position in upload queue (1-indexed)
}

export interface QueueInfo {
  files: UploadedFile[];
  timestamp: Date;
  isValid: boolean;
}

export type SaveStatus = "idle" | "saving" | "saved" | "error";

export interface QueueManagerReturn {
  saveStatus: SaveStatus;
  lastSaved: Date | null;
  timeSinceLastSave: string | null;
  hasUnsavedChanges: boolean;
  isQueueAvailable: boolean;
  queueInfo: QueueInfo | null;
  restoreQueue: () => void;
  dismissQueue: () => void;
  forceSave: () => void;
  clearCurrentQueue: () => void;
}

// Add environment prefix for storage key isolation
const ENV_PREFIX =
  typeof window !== "undefined" ? process.env.NEXT_PUBLIC_APP_ENV || "local" : "local";
const STORAGE_KEY = `${ENV_PREFIX}:inspect-ai-upload-queue`;

// Utility functions
const isLocalStorageAvailable = (): boolean => {
  try {
    const test = "__localStorage_test__";
    localStorage.setItem(test, test);
    localStorage.removeItem(test);
    return true;
  } catch {
    return false;
  }
};

interface StoredQueueFile {
  file: {
    name: string;
    size: number;
    type: string;
  };
  originalSize?: number;
  jobId?: string;
  progress: number;
  status: UploadedFile["status"];
  error?: string;
  timestamp: string;
}

interface StoredQueueData {
  files: StoredQueueFile[];
  timestamp: string;
  version: string;
}

const saveQueue = (files: UploadedFile[]): boolean => {
  try {
    const queueData = {
      files: files.map((f) => ({
        file: {
          name: f.file.name,
          size: f.file.size,
          type: f.file.type,
        },
        originalSize: f.originalSize ?? f.file.size,
        jobId: f.jobId,
        progress: f.progress,
        status: f.status,
        error: f.error,
        timestamp: f.timestamp.toISOString(),
      })),
      timestamp: new Date().toISOString(),
      version: "2.0",
    };

    localStorage.setItem(STORAGE_KEY, JSON.stringify(queueData));
    return true;
  } catch {
    return false;
  }
};

const loadQueue = (): QueueInfo | null => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return null;

    const parsed = JSON.parse(stored) as StoredQueueData;

    // Validate stored data
    if (!parsed.files || !Array.isArray(parsed.files) || !parsed.timestamp) {
      return null;
    }

    const restoredFiles: UploadedFile[] = parsed.files.map((f: StoredQueueFile) => {
      const metadata = f.file || { name: "unknown.pdf", size: 0, type: "application/pdf" };
      const placeholderFile = new File([], metadata.name ?? "unknown.pdf", {
        type: metadata.type ?? "application/pdf",
      });
      const hasServerJob = Boolean(f.jobId);
      const requiresReselect =
        !hasServerJob &&
        (f.status === "pending" || f.status === "queued" || f.status === "uploading");

      return {
        id: `${metadata.name}-${Date.now()}-${Math.random()}`, // Generate unique ID on restore
        file: placeholderFile,
        progress: hasServerJob ? (f.progress ?? 0) : 0,
        status: hasServerJob ? (f.status === "uploading" ? "processing" : f.status) : "pending",
        jobId: f.jobId,
        error: requiresReselect
          ? "⚠️ File reselection required - browsers cannot restore file contents from storage"
          : (f.error ?? undefined),
        timestamp: new Date(f.timestamp ?? parsed.timestamp),
        isPlaceholder: requiresReselect,
        originalSize: f.originalSize ?? metadata.size ?? placeholderFile.size,
      } satisfies UploadedFile;
    });

    return {
      files: restoredFiles,
      timestamp: new Date(parsed.timestamp),
      isValid: restoredFiles.length > 0,
    };
  } catch {

    // If localStorage is corrupted, try to clear it and return null
    try {
      clearQueue();
    } catch {
      // Intentionally ignored
    }

    return null;
  }
};

const clearQueue = (): void => {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
      // Intentionally ignored
    }
};

const getTimeSinceLastSave = (lastSaved: Date): string => {
  const now = new Date();
  const diffMs = now.getTime() - lastSaved.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffDays > 0) {
    return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;
  }
  if (diffHours > 0) {
    return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
  }
  if (diffMins > 0) {
    return `${diffMins} minute${diffMins > 1 ? "s" : ""} ago`;
  }
  return "Just now";
};

export const useUploadQueueManager = (
  files: UploadedFile[],
  onQueueRestore: (files: UploadedFile[]) => void,
  debounceMs = 2000,
): QueueManagerReturn => {
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [isQueueAvailable, setIsQueueAvailable] = useState(false);
  const [queueInfo, setQueueInfo] = useState<QueueInfo | null>(null);
  const [timeSinceLastSave, setTimeSinceLastSave] = useState<string | null>(null);

  const debounceTimerRef = useRef<NodeJS.Timeout | undefined>(undefined);
  const filesRef = useRef<UploadedFile[]>(files);
  const isRestoringRef = useRef(false);
  const hasUserInteractedRef = useRef(false);
  const initialLoadRef = useRef(true);

  // Update files ref when files change
  useEffect(() => {
    filesRef.current = files;
  }, [files]);

  // Check for existing queue on mount
  useEffect(() => {
    if (!isLocalStorageAvailable()) return;

    const existingQueue = loadQueue();
    if (existingQueue?.isValid) {
      setQueueInfo(existingQueue);
      setIsQueueAvailable(true);
      setLastSaved(existingQueue.timestamp);
    }

    // Mark initial load as complete after a short delay
    setTimeout(() => {
      initialLoadRef.current = false;
    }, 100);
  }, []);

  // Update time since last save periodically
  useEffect(() => {
    if (!lastSaved) return;

    const updateTimeDisplay = () => {
      setTimeSinceLastSave(getTimeSinceLastSave(lastSaved));
    };

    updateTimeDisplay();
    const interval = setInterval(updateTimeDisplay, 30000); // Update every 30 seconds

    return () => clearInterval(interval);
  }, [lastSaved]);

  // Debounced save function
  const performSave = useCallback(() => {
    if (!isLocalStorageAvailable()) {
      setSaveStatus("error");
      return;
    }

    setSaveStatus("saving");
    setHasUnsavedChanges(false);

    // Small delay to show saving state
    setTimeout(() => {
      const success = saveQueue(filesRef.current);

      if (success) {
        const now = new Date();
        setSaveStatus("saved");
        setLastSaved(now);

        // Only clear queue available state if user has actually interacted
        if (hasUserInteractedRef.current) {
          setIsQueueAvailable(false);
        }

        // Reset to idle after 2 seconds
        setTimeout(() => {
          setSaveStatus("idle");
        }, 2000);
      } else {
        setSaveStatus("error");
        setTimeout(() => {
          setSaveStatus("idle");
        }, 3000);
      }
    }, 100);
  }, []);

  // Debounced save effect
  useEffect(() => {
    // Don't auto-save during initial load
    if (initialLoadRef.current) {
      return;
    }

    // Don't auto-save if we're in the middle of restoring a queue
    if (isRestoringRef.current) {
      isRestoringRef.current = false;
      return;
    }

    // Only save if there are files to save
    if (files.length === 0) {
      return;
    }

    // Mark that user has interacted with the queue
    hasUserInteractedRef.current = true;
    setHasUnsavedChanges(true);

    // Clear existing timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Set new timer
    debounceTimerRef.current = setTimeout(() => {
      performSave();
    }, debounceMs);

    // Cleanup
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [files, debounceMs]);

  // Restore queue function
  const restoreQueue = useCallback(() => {
    if (queueInfo) {
      isRestoringRef.current = true;
      hasUserInteractedRef.current = true;
      onQueueRestore(queueInfo.files);
      setIsQueueAvailable(false);
      setQueueInfo(null);
      setLastSaved(queueInfo.timestamp);
      setSaveStatus("idle");
      setHasUnsavedChanges(queueInfo.files.some((file) => file.isPlaceholder));
    }
  }, [onQueueRestore, queueInfo]);

  // Dismiss queue function
  const dismissQueue = useCallback(() => {
    hasUserInteractedRef.current = true;
    clearQueue();
    setIsQueueAvailable(false);
    setQueueInfo(null);
  }, []);

  // Force save function (for manual save button)
  const forceSave = useCallback(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    performSave();
  }, [performSave]);

  // Clear current queue function
  const clearCurrentQueue = useCallback(() => {
    clearQueue();
    setLastSaved(null);
    setTimeSinceLastSave(null);
    setIsQueueAvailable(false);
    setQueueInfo(null);
    setSaveStatus("idle");
    setHasUnsavedChanges(false);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  return {
    saveStatus,
    lastSaved,
    timeSinceLastSave,
    hasUnsavedChanges,
    isQueueAvailable,
    queueInfo,
    restoreQueue,
    dismissQueue,
    forceSave,
    clearCurrentQueue,
  };
};

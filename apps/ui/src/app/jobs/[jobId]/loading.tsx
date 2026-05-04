import { Loader } from "lucide-react";

export default function Loading() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <div className="flex flex-col items-center p-8 border border-border rounded bg-background max-w-md text-center">
        <Loader className="w-8 h-8 text-primary mb-4 animate-spin" />
        <h4 className="text-lg font-semibold text-foreground mb-2">Loading Assessments...</h4>
        <p className="text-sm text-muted-foreground">
          Please wait while we retrieve the latest assessments.
        </p>
      </div>
    </div>
  );
}

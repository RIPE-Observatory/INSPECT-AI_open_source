import { SignUp } from "@clerk/nextjs";
import { redirect } from "next/navigation";
import { isAuthDisabled } from "@/lib/auth-mode";

export default function SignUpPage() {
  if (isAuthDisabled()) {
    redirect("/");
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <SignUp
        routing="path"
        path="/sign-up"
        signInUrl="/sign-in"
        fallbackRedirectUrl="/"
        forceRedirectUrl="/"
      />
    </div>
  );
}

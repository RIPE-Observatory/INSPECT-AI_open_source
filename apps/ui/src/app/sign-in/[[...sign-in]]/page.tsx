import { SignIn } from "@clerk/nextjs";
import { redirect } from "next/navigation";
import { isAuthDisabled } from "@/lib/auth-mode";

export default function SignInPage() {
  if (isAuthDisabled()) {
    redirect("/");
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <SignIn
        routing="path"
        path="/sign-in"
        signUpUrl="/sign-up"
        fallbackRedirectUrl="/"
        forceRedirectUrl="/"
      />
    </div>
  );
}

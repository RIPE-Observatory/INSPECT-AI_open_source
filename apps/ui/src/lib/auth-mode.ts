export function isAuthDisabled(): boolean {
  return (
    process.env.NEXT_PUBLIC_DISABLE_AUTH === "true" ||
    !process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
  );
}

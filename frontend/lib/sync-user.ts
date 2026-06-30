import "server-only";
import { currentUser } from "@clerk/nextjs/server";

const PRISM_API_URL = process.env.PRISM_API_URL ?? "http://127.0.0.1:8000";

/** Mirror the Clerk-verified user into the PRISM backend (loopback) as the tenant
 *  key. Idempotent + fail-open: a backend hiccup must never block the render. */
export async function syncUser(): Promise<void> {
  const user = await currentUser();
  if (!user) return;
  const email = user.primaryEmailAddress?.emailAddress ?? null;
  const name = [user.firstName, user.lastName].filter(Boolean).join(" ") || null;
  try {
    await fetch(`${PRISM_API_URL}/api/v1/users/upsert`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: user.id, email, name }),
    });
  } catch {
    /* fail-open: identity capture is best-effort per load */
  }
}

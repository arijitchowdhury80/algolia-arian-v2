import { AppShell } from "@/components/layout/app-shell";
import { syncUser } from "@/lib/sync-user";

export default async function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  await syncUser();
  return <AppShell>{children}</AppShell>;
}

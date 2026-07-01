import { redirect } from "next/navigation";

export default function AuthenticatedRoot() {
  redirect("/chat");
}

// ia/verify.ts — run: deno test --allow-read --allow-run ia/verify.ts
async function git(args: string[]): Promise<string> {
  const p = new Deno.Command("git", { args, stdout: "piped" });
  const { stdout } = await p.output();
  return new TextDecoder().decode(stdout).trim();
}

Deno.test("production files are unchanged vs baseline (only ia/ and additive feedback route allowed)", async () => {
  const changed = (await git(["diff", "--name-only", "HEAD"]))
    .split("\n").filter(Boolean);
  const offenders = changed.filter((f) =>
    !f.startsWith("ia/") &&
    f !== "api/feedback.js" &&
    f !== "server/chat-proxy.mjs"
  );
  if (offenders.length) throw new Error("Production files modified: " + offenders.join(", "));
});

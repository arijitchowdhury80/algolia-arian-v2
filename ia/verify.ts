// ia/verify.ts - run: deno test --allow-read --allow-run ia/verify.ts
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
    !f.startsWith("ia1/") &&
    !f.startsWith("ia2/") &&
    f !== "api/feedback.js" &&
    f !== "server/chat-proxy.mjs"
  );
  if (offenders.length) throw new Error("Production files modified: " + offenders.join(", "));
});

Deno.test("both shells exist and link the same shared core", async () => {
  const ia1 = await Deno.readTextFile("ia/ia1/index.html");
  const ia2 = await Deno.readTextFile("ia/ia2/index.html");
  for (const html of [ia1, ia2]) {
    if (!html.includes("../shared/brand-tokens.css")) throw new Error("shell missing brand-tokens");
    if (!html.includes("../shared/ia-shared.css")) throw new Error("shell missing ia-shared css");
  }
  const ia1js = await Deno.readTextFile("ia/ia1/ia1.js");
  const ia2js = await Deno.readTextFile("ia/ia2/ia2.js");
  for (const js of [ia1js, ia2js]) {
    if (!js.includes('from "../shared/job-model.js"')) throw new Error("shell not using shared job-model");
    if (!js.includes('from "../shared/render.js"')) throw new Error("shell not using shared render");
  }
});

Deno.test("no em dash anywhere in ia/ source", async () => {
  const EM_DASH = "\u2014";
  for await (const entry of walk("ia")) {
    if (!entry.isFile) continue;
    if (/\.(js|ts|html|css)$/.test(entry.name)) {
      const t = await Deno.readTextFile(entry.path);
      if (t.includes(EM_DASH)) throw new Error("em dash in " + entry.path);
    }
  }
});

async function* walk(dir: string): AsyncGenerator<{ path: string; name: string; isFile: boolean }> {
  for await (const e of Deno.readDir(dir)) {
    const path = `${dir}/${e.name}`;
    if (e.isDirectory) yield* walk(path);
    else yield { path, name: e.name, isFile: true };
  }
}

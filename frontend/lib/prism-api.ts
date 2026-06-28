const PRISM_API_URL = process.env.PRISM_API_URL || "http://localhost:8000";

export async function prismFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${PRISM_API_URL}${path}`;
  const method = options?.method ?? "GET";
  const startMs = Date.now();

  console.info("[prism-api] request started", {
    method,
    path,
    url,
    timestamp: new Date().toISOString(),
  });

  try {
    let res = await fetch(url, {
      ...options,
      redirect: "manual",
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    // Follow 307 redirects while preserving method and body
    if (res.status === 307 || res.status === 308) {
      const redirectUrl = res.headers.get("location");
      console.info("[prism-api] following redirect", {
        from: url,
        to: redirectUrl,
        status: res.status,
      });
      if (redirectUrl) {
        res = await fetch(redirectUrl, {
          ...options,
          headers: {
            "Content-Type": "application/json",
            ...options?.headers,
          },
        });
      }
    }

    const durationMs = Date.now() - startMs;

    if (!res.ok) {
      const errorBody = await res.text();
      console.error("[prism-api] HTTP error response", {
        method,
        path,
        status: res.status,
        statusText: res.statusText,
        durationMs,
        errorBody: errorBody.substring(0, 500),
      });
      throw new Error(
        `PRISM API error ${res.status}: ${errorBody.substring(0, 200)}`
      );
    }

    const data = await res.json();

    console.info("[prism-api] request complete", {
      method,
      path,
      status: res.status,
      durationMs,
      responseKeys: data ? Object.keys(data).slice(0, 10) : [],
    });

    return data;
  } catch (error) {
    const durationMs = Date.now() - startMs;
    const message =
      error instanceof Error ? error.message : "Unknown PRISM API error";

    console.error("[prism-api] request failed", {
      method,
      path,
      url,
      durationMs,
      error: message,
      errorType: error instanceof Error ? error.constructor.name : typeof error,
    });

    throw error;
  }
}

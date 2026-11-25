import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { resolve, extname, sep } from "node:path";

const root = resolve(import.meta.dirname, "../out");
const types = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".webp": "image/webp",
  ".woff2": "font/woff2",
  ".txt": "text/plain",
};
const port = Number(process.env.PORT ?? 3341);
const server = createServer(async (request, response) => {
  try {
    const path = resolve(
      root,
      `.${decodeURIComponent(new URL(request.url, "http://localhost").pathname)}`,
    );
    if (path !== root && !path.startsWith(root + sep)) {
      response.writeHead(403).end();
      return;
    }
    const info = await stat(path);
    const target = info.isDirectory() ? resolve(path, "index.html") : path;
    response.writeHead(200, {
      "Content-Type": types[extname(target)] ?? "application/octet-stream",
    });
    response.end(await readFile(target));
  } catch {
    response.writeHead(404, { "Content-Type": "text/plain" }).end("Not found");
  }
});
server.listen(port, "127.0.0.1", () =>
  console.log(`Static Fumadocs preview: http://127.0.0.1:${port}`),
);

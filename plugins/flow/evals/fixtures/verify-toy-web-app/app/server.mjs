// Toy server for verify-toy-web-app fixture. POST /api/submit returns 201.
// Not meant to be executed by the eval harness — illustrates what the running
// app surface looks like to bundled /verify.

import http from "node:http";

const server = http.createServer((req, res) => {
  if (req.method === "POST" && req.url === "/api/submit") {
    res.writeHead(201);
    res.end();
    return;
  }
  res.writeHead(404);
  res.end();
});

server.listen(3000, () => {
  console.log("toy server listening on http://localhost:3000");
});

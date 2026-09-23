import { Hono } from "hono";
import { zValidator } from "@hono/zod-validator";
import { z } from "zod";
import { SQL } from "bun";
import products from "../data/products.json";

const workers = Number(process.env.WORKERS ?? 1);
const poolSize = Math.max(1, Math.floor(Number(process.env.DB_POOL_TOTAL ?? 20) / workers));

const sql = new SQL({ url: process.env.DATABASE_URL!, max: poolSize });

const ItemIn = z.object({
  name: z.string().min(1).max(200),
  price: z.number().positive(),
  tags: z.array(z.string()).max(20).default([]),
});

const app = new Hono();

app.get("/health", (c) => c.json({ ok: true }));

// Serialized on every request, like ORJSONResponse in FastAPI.
app.get("/static", (c) => c.json(products));

app.post("/items", zValidator("json", ItemIn), async (c) => {
  const { name, price, tags } = c.req.valid("json");
  const [row] = await sql`
    INSERT INTO items (name, price, tags)
    VALUES (${name}, ${price}, ${sql.array(tags, "text")})
    RETURNING id`;
  return c.json({ id: Number(row.id) }, 201);
});

Bun.serve({ port: 3000, reusePort: true, fetch: app.fetch });

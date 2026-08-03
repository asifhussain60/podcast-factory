import { type RouteConfig, index, route } from "@react-router/dev/routes";

export default [
  index("routes/home.tsx"),
  route("favicon.ico", "routes/favicon.ico.ts"),
  // Not part of the product surface: a side-by-side of the three candidate
  // marks in every theme, so the choice is made from the real thing. Delete it
  // once the mark is settled.
  route("brand", "routes/brand.tsx"),
] satisfies RouteConfig;

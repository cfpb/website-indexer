import esbuild from "esbuild";

import { scripts } from "./scripts.js";

const baseConfig = {
  logLevel: "info",
  bundle: true,
  minify: true,
  sourcemap: true,
  external: ["*.png", "*.woff2", "*.gif"],
  loader: {
    ".svg": "text",
  },
  outdir: "./viewer/static",
  outbase: "./viewer/static_src",
  plugins: [],
};

const arg = process.argv.slice(2)[0];

(async function () {
  const scriptsConfig = scripts(baseConfig);

  if (arg === "watch") {
    const ctx = await esbuild.context(scriptsConfig);
    await ctx.watch();
    // Not disposing context here as the user will ctrl+c to end watching.
  } else {
    const ctx = await esbuild.context(scriptsConfig);
    await ctx.rebuild();
    await ctx.dispose();
  }
})();

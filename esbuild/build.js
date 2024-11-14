import esbuild from 'esbuild';

import { scripts } from './scripts.js';

const baseConfig = {
  logLevel: 'info',
  bundle: true,
  minify: true,
  sourcemap: true,
  external: ['*.png', '*.woff2', '*.gif'],
  loader: {
    '.svg': 'text',
  },
  outdir: "./viewer/static",
  outbase: "./viewer/static_src",
  plugins: [],
};

(async function () {
  const scriptsConfig = scripts(baseConfig);
  const ctx = await esbuild.context(scriptsConfig);

  await ctx.rebuild();
  await ctx.dispose();
})();

import { context } from "esbuild";
import { copy } from "esbuild-plugin-copy";
import autoprefixer from "autoprefixer";
import { promises, readdirSync } from "fs";
import { dirname } from "path";
import postcss from "postcss";
import less from "less";

const modules = "./node_modules";

// Copied from https://github.com/cfpb/consumerfinance.gov/blob/fcb4eab638db45003cac57432b89c0a249bc2aff/esbuild/plugins/postcss.js
const postCSSPlugin = ({ plugins = [], lessOptions = {} }) => ({
  name: "less-and-postcss",
  setup(build) {
    build.onLoad({ filter: /.\.less$/ }, async (args) => {
      const fileContent = await promises.readFile(args.path, {
        encoding: "utf-8",
      });
      const lessResult = await less.render(fileContent, {
        ...lessOptions,
        filename: args.path,
        rootpath: dirname(args.path),
      });
      const result = await postcss(plugins).process(lessResult.css, {
        from: args.path,
      });

      return {
        contents: result.css,
        loader: "css",
        watchFiles: lessResult.imports,
      };
    });
  },
});

(async function () {
  const watch = process.argv.slice(2)[0] === "--watch";

  const ctx = await context({
    entryPoints: [
      "viewer/static_src/js/main.js",
      "viewer/static_src/css/main.less",
    ],
    bundle: true,
    sourcemap: true,
    minify: true,
    logLevel: "debug",
    outbase: "viewer/static_src",
    outdir: "viewer/static",
    external: ["*.png", "*.woff", "*.woff2", "*.gif"],
    loader: {
      ".svg": "text",
    },
    plugins: [
      copy({
        assets: [
          {
            from: ["viewer/static_src/query-string-filtering.docx"],
            to: ["."],
          },
          {
            from: [`${modules}/@cfpb/cfpb-icons/src/icons/*`],
            to: ["./icons"],
          },
        ],
      }),
      postCSSPlugin({
        plugins: [autoprefixer],
        lessOptions: {
          math: "always",
          paths: [
            ...readdirSync(`${modules}/@cfpb`).map(
              (v) => `${modules}/@cfpb/${v}/src`
            ),
            `${modules}`,
          ],
        },
      }),
    ],
  });

  if (watch) {
    await ctx.watch();
  } else {
    await ctx.rebuild();
    return await ctx.dispose();
  }
})();

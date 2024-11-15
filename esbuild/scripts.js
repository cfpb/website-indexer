import { pluginPostCssSass } from "./plugins/plugin-postcss-sass.js";
import { copy } from "esbuild-plugin-copy";
import autoprefixer from "autoprefixer";

const jsPaths = [];

const entryFileList = ["./viewer/static_src/js/main.js"];
entryFileList.forEach((file) => {
  jsPaths.push(file);
});

/**
 * @param {object} baseConfig - The base esbuild configuration.
 * @returns {object} The modified configuration object.
 */
function scripts(baseConfig) {
  return {
    ...baseConfig,
    entryPoints: jsPaths,
    target: "es6",
    plugins: baseConfig.plugins.concat([
      copy({
        assets: [
          {
            from: ["./viewer/static_src/query-string-filtering.docx"],
            to: ["."],
          },
          {
            from: [
              "./node_modules/@cfpb/cfpb-design-system/src/components/cfpb-icons/icons/*",
            ],
            to: ["./icons"],
          },
        ],
      }),
      pluginPostCssSass({
        plugins: [autoprefixer],
      }),
      copy({
        assets: [
          {
            from: ["./viewer/static/js/main.css"],
            to: ["./css/main.css"],
          },
          {
            from: ["./viewer/static/js/main.css.map"],
            to: ["./css/main.css.map"],
          },
        ],
      }),
    ]),
  };
}

export { scripts };

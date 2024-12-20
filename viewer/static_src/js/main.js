export * as MainStyles from "../css/main.scss";

import { Expandable } from "@cfpb/cfpb-design-system";

const docElement = document.documentElement;
docElement.className = docElement.className.replace(
  /(^|\s)no-js(\s|$)/,
  "$1$2",
);

Expandable.init();

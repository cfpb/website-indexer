import { Expandable } from "@cfpb/cfpb-expandables";

const docElement = document.documentElement;
docElement.className = docElement.className.replace(
  /(^|\s)no-js(\s|$)/,
  "$1$2",
);

Expandable.init();

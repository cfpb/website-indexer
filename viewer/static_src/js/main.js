import { ExpandableGroup } from "@cfpb/cfpb-expandables";

const docElement = document.documentElement;
docElement.className = docElement.className.replace(
  /(^|\s)no-js(\s|$)/,
  "$1$2"
);

ExpandableGroup.init();

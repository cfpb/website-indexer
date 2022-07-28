import Expandable from '@cfpb/cfpb-expandables/src/Expandable.js';

Expandable.init();

// Easiest way to return user to their search results without having
// to handle any sort of internal state management.
const breadcrumb = document.getElementById('breadcrumb_link');
if (breadcrumb) {
  breadcrumb.addEventListener('click', ev => {
    ev.preventDefault();
    window.location.href = document.referrer;
  });
}

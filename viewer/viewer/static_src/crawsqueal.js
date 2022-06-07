import Expandable from '@cfpb/cfpb-expandables/src/Expandable.js';

Expandable.init();

// Easiest way to return user to their search results without having
// to handle any sort of internal state management.
const breadcrumb = document.getElementById( 'breadcrumb_link' );
if ( breadcrumb ) {
  breadcrumb.addEventListener( 'click', ev => {
    ev.preventDefault();
    window.location.href = document.referrer;
  });
}

// Copy the sidebar filter values over to the search form so they're
// submitted with the search term.
const form = document.getElementById( 'search_form' );
const filters = document.getElementById( 'filters' );
if ( form && filters ) {
  // Hide the sidebar's update button. It's only needed if JS is disabled.
  document.getElementById( 'update-button' ).classList.add( 'u-hidden' );
  form.addEventListener( 'submit', ev => {
    const searchType = filters.querySelector( 'input[name="search_type"]:checked' ).value || 'links';
    const paginateBy = filters.querySelector( 'input[name="paginate_by"]:checked' ).value || '50';
    form.querySelector( 'input[name="search_type"]' ).value = searchType;
    form.querySelector( 'input[name="paginate_by"]' ).value = paginateBy;
  });
}

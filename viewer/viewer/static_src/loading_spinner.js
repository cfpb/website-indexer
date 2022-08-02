const startLoading = () => {
  document.body.style.opacity = 0.5;
};

const stopLoading = () => {
  document.body.style.opacity = 1;
};

const createResultItem = (data) => {
  const div = document.createElement("div");
  div.innerHTML = `<li class="results_item">
    <h4>
      <a class="a-link a-link__icon" href="${data.url}">
        <span class="a-link_text u-truncate">${data.title}</span>
        <svg class="cf-icon-svg" viewBox="0 0 14 19" xmlns="http://www.w3.org/2000/svg">
          <path d="M13.017 3.622v4.6a.554.554 0 0 1-1.108 0V4.96L9.747 7.122a1.65 1.65 0 0 1 .13.646v5.57A1.664 1.664 0 0 1 8.215 15h-5.57a1.664 1.664 0 0 1-1.662-1.663v-5.57a1.664 1.664 0 0 1 1.662-1.662h5.57A1.654 1.654 0 0 1 9 6.302l2.126-2.126H7.863a.554.554 0 1 1 0-1.108h4.6a.554.554 0 0 1 .554.554zM8.77 8.1l-2.844 2.844a.554.554 0 0 1-.784-.783l2.947-2.948H2.645a.555.555 0 0 0-.554.555v5.57a.555.555 0 0 0 .554.553h5.57a.555.555 0 0 0 .554-.554z"></path>
        </svg></a>
    </h4>
    <div class="u-truncate">${data.url}</div>
    <a href="/page/?url=${data.url}">
      Details
    </a>
  </li>`;
  return div;
};

const fetchResults = (params) => {
  const q = params.q;
  const search_type = params.search_type;

  startLoading();
  fetch(`/?q=${q}&search_type=${search_type}&format=json`)
    .then((response) => {
      stopLoading();
      return response.json();
    })
    .then((data) => {
      const container = document.querySelector(".results_list .m-list");
      container.innerHTML = "";
      data.results.forEach((result) => {
        const resultItemEl = createResultItem(result);
        container.appendChild(resultItemEl);
      });
    });
};

// Sample queries
fetchResults({ q: "money", search_type: "text" });
fetchResults({ q: "dog", search_type: "links" });

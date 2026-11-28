{% include "js/layout.js" %}
document.addEventListener("DOMContentLoaded", function () {
{% include "js/filter-controls.js" %}
{% include "js/opened-row.js" %}
  read();
  apply();
  openFromQuery(true);
});

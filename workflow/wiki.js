const search = document.querySelector("#wiki-search");
const output = document.querySelector("#match-count");
const entries = Array.from(document.querySelectorAll(".wiki-card"));
const keys = new Map(entries.map(entry => [
  entry.id, (entry.textContent + " " + (entry.dataset.tags || "")).toLowerCase()
]));

function filterEntries() {
  const terms = search.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
  let visible = 0;
  for (const entry of entries) {
    entry.hidden = !terms.every(term => keys.get(entry.id).includes(term));
    if (!entry.hidden) visible++;
  }
  output.textContent = "顯示 " + visible + " / " + entries.length + " 個條目";
  document.querySelector("#no-result").hidden = visible !== 0;
}

search.addEventListener("input", filterEntries);
document.addEventListener("click", event => {
  const link = event.target.closest("a[href^='#']");
  if (!link || !search.value) return;
  const target = document.getElementById(link.hash.slice(1));
  if (target?.closest(".wiki-card")?.hidden) {
    search.value = "";
    filterEntries();
  }
});
filterEntries();

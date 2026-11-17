const slides = Array.from(document.querySelectorAll(".slide"));
const previous = document.querySelector("#previous");
const next = document.querySelector("#next");
const select = document.querySelector("#slide-select");
const pageCount = document.querySelector("#page-count");
const bar = document.querySelector("#bar");
let current = 0;

function showSlide(index, updateHash = true) {
  current = Math.max(0, Math.min(index, slides.length - 1));
  slides.forEach((slide, position) => { slide.hidden = position !== current; });
  const active = slides[current];
  previous.disabled = current === 0;
  next.disabled = current === slides.length - 1;
  select.value = active.id;
  pageCount.textContent = String(current + 1).padStart(2, "0") + " / " + String(slides.length).padStart(2, "0");
  bar.style.width = ((current + 1) / slides.length * 100) + "%";
  if (updateHash) {
    history.replaceState(null, "", "#" + active.id);
    window.scrollTo({ top: 0, behavior: "instant" });
  }
}

function showFromHash() {
  const index = slides.findIndex(slide => "#" + slide.id === location.hash);
  showSlide(index < 0 ? 0 : index, false);
}

previous.addEventListener("click", () => showSlide(current - 1));
next.addEventListener("click", () => showSlide(current + 1));
select.addEventListener("change", () => showSlide(slides.findIndex(slide => slide.id === select.value)));
window.addEventListener("hashchange", showFromHash);

document.addEventListener("keydown", event => {
  if (event.altKey || event.ctrlKey || event.metaKey ||
      event.target.matches("input, select, textarea") || event.target.isContentEditable) return;
  const movements = { ArrowLeft: current - 1, ArrowRight: current + 1, Home: 0, End: slides.length - 1 };
  if (!Object.hasOwn(movements, event.key)) return;
  event.preventDefault();
  showSlide(movements[event.key]);
});

for (const quiz of document.querySelectorAll(".quiz")) {
  const choices = Array.from(quiz.querySelectorAll(".answer"));
  const feedback = quiz.querySelector(".feedback");
  for (const choice of choices) {
    choice.addEventListener("click", () => {
      for (const other of choices) {
        delete other.dataset.state;
        other.setAttribute("aria-pressed", String(other === choice));
      }
      const correct = choice.dataset.correct === "true";
      choice.dataset.state = correct ? "correct" : "retry";
      feedback.textContent = correct ? "答對了。 " + quiz.dataset.explanation : "再想想，然後試一次。";
    });
  }
}

showFromHash();

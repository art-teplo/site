// Точка фокуса фото в админке (apps/content/widgets.py): клик по превью
// пишет «x y» в процентах в поле image_focus, рядом — как фото обрежется
// в вертикальной (4:5) и горизонтальной (16:9) рамке.
(() => {
  const parse = (value) => {
    const [x, y] = String(value || "").trim().split(/\s+/).map(Number);
    const ok = (n) => Number.isFinite(n) && n >= 0 && n <= 100;
    return ok(x) && ok(y) ? [x, y] : [50, 50];
  };

  const setup = (picker) => {
    if (picker.dataset.ready) return;
    picker.dataset.ready = "1";
    const input = picker.querySelector("input.focus-input");
    const stage = picker.querySelector(".focus-picker__stage");
    const img = picker.querySelector(".focus-picker__img");
    const dot = picker.querySelector(".focus-picker__dot");
    const empty = picker.querySelector(".focus-picker__empty");
    const crops = picker.querySelectorAll(".focus-picker__crop");

    const place = () => {
      const [x, y] = parse(input.value);
      dot.style.left = `${x}%`;
      dot.style.top = `${y}%`;
      crops.forEach((c) => (c.style.backgroundPosition = `${x}% ${y}%`));
    };

    const show = (src) => {
      if (!src) return;
      img.src = src;
      crops.forEach((c) => (c.style.backgroundImage = `url("${src}")`));
      stage.hidden = false;
      empty.hidden = true;
      place();
    };

    img.addEventListener("click", (event) => {
      const rect = img.getBoundingClientRect();
      const x = Math.round(((event.clientX - rect.left) / rect.width) * 100);
      const y = Math.round(((event.clientY - rect.top) / rect.height) * 100);
      input.value = `${Math.min(100, Math.max(0, x))} ${Math.min(100, Math.max(0, y))}`;
      input.dispatchEvent(new Event("change", { bubbles: true }));
      place();
    });
    input.addEventListener("input", place);

    // Поле «фото» той же формы: то же имя с префиксом инлайна, без _focus
    const fileName = picker.dataset.focusFor.replace(/image_focus$/, "image");
    const file = input.form?.querySelector(`input[type="file"][name="${fileName}"]`);
    file?.addEventListener("change", () => {
      if (file.files?.[0]) show(URL.createObjectURL(file.files[0]));
    });
    show(input.dataset.src);
  };

  const init = (root = document) => root.querySelectorAll(".focus-picker").forEach(setup);
  document.addEventListener("DOMContentLoaded", () => init());
  // Новая строка инлайна («Добавить ещё»)
  document.addEventListener("formset:added", (event) => init(event.target));
})();

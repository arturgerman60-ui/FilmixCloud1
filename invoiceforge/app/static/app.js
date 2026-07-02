// Динамическое добавление/удаление строк позиций в форме документа.
function addRow() {
  const table = document.getElementById("items-table");
  if (!table) return;
  const tbody = table.querySelector("tbody");
  const row = document.createElement("tr");
  row.innerHTML = `
    <td><input name="item_description" placeholder="Товар / услуга" /></td>
    <td><input name="item_quantity" type="number" step="0.01" value="1" /></td>
    <td><input name="item_price" type="number" step="0.01" value="0" /></td>
    <td><button type="button" class="btn btn-sm btn-danger" onclick="removeRow(this)">×</button></td>
  `;
  tbody.appendChild(row);
}

function removeRow(button) {
  const row = button.closest("tr");
  const tbody = row.parentElement;
  if (tbody.children.length > 1) {
    row.remove();
  } else {
    row.querySelectorAll("input").forEach((input) => {
      input.value = input.type === "number" ? "0" : "";
    });
  }
}

// Подсветка активного пункта меню.
document.querySelectorAll(".nav-item").forEach((link) => {
  if (link.getAttribute("href").split("?")[0] === location.pathname) {
    link.style.background = "var(--panel-2)";
    link.style.color = "var(--text)";
  }
});

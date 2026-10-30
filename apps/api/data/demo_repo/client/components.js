/**
 * UI Component rendering helpers for TaskBoard.
 */

function renderTaskCard(task) {
  const card = document.createElement("div");
  card.className = `task-card status-${task.status}`;
  card.setAttribute("data-id", task.id);

  const titleEl = document.createElement("h4");
  titleEl.textContent = task.title;

  const descEl = document.createElement("p");
  descEl.textContent = task.description || "No description provided.";

  const statusBadge = document.createElement("span");
  statusBadge.className = "badge";
  statusBadge.textContent = task.status;

  card.appendChild(titleEl);
  card.appendChild(descEl);
  card.appendChild(statusBadge);

  return card;
}

function renderColumn(title, tasks, containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = `<h3>${title} (${tasks.length})</h3>`;
  tasks.forEach((t) => {
    container.appendChild(renderTaskCard(t));
  });
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { renderTaskCard, renderColumn };
}

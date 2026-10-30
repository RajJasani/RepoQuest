/**
 * Main application entrypoint for TaskBoard frontend.
 */

/* global fetchTasks, createTask, updateTaskStatus, renderColumn */

class TaskBoardApp {
  constructor() {
    this.tasks = [];
  }

  async init() {
    console.log("Initializing TaskBoard client application...");
    try {
      await this.loadBoard();
      this.attachEventListeners();
    } catch (err) {
      console.error("Initialization error:", err);
    }
  }

  async loadBoard() {
    const data = await fetchTasks();
    this.tasks = data.tasks || [];
    this.render();
  }

  render() {
    const backlog = this.tasks.filter((t) => t.status === "backlog");
    const inProgress = this.tasks.filter((t) => t.status === "in_progress");
    const completed = this.tasks.filter((t) => t.status === "completed");

    if (typeof renderColumn === "function") {
      renderColumn("Backlog", backlog, "col-backlog");
      renderColumn("In Progress", inProgress, "col-in-progress");
      renderColumn("Completed", completed, "col-completed");
    }
  }

  attachEventListeners() {
    const form = document.getElementById("new-task-form");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const titleInput = document.getElementById("task-title");
      const title = titleInput ? titleInput.value.trim() : "";
      if (!title) return;

      await createTask(title);
      titleInput.value = "";
      await this.loadBoard();
    });
  }
}

if (typeof window !== "undefined") {
  window.addEventListener("DOMContentLoaded", () => {
    const app = new TaskBoardApp();
    app.init();
  });
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { TaskBoardApp };
}


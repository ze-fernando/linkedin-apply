from collections.abc import Callable
from dataclasses import dataclass
from html import escape

SEARCH_PATH = "/jobs/search/"

SEARCH_PAGE_SCRIPT = """
const panel = document.getElementById("panel");
const showPanel = (jobId) => {
  const template = document.getElementById(`panel-${jobId}`);
  if (template) {
    setTimeout(() => { panel.innerHTML = template.innerHTML; }, 50);
  }
};
document.addEventListener("click", (event) => {
  const card = event.target.closest(".job-card-container");
  if (!card) return;
  const jobId = card.getAttribute("data-job-id");
  history.pushState({}, "", `?currentJobId=${jobId}`);
  showPanel(jobId);
});
const observer = new IntersectionObserver((entries) => {
  for (const entry of entries) {
    const item = entry.target;
    if (entry.isIntersecting && !item.children.length) {
      item.innerHTML = document.getElementById(`card-${item.dataset.occludableJobId}`).innerHTML;
    }
  }
});
document.querySelectorAll("li[data-occludable-job-id]").forEach((item) => observer.observe(item));
const lateItems = document.getElementById("late-items");
setTimeout(() => {
  const list = document.querySelector("ul");
  for (const item of [...lateItems.content.children]) {
    const added = list.appendChild(item.cloneNode(true));
    observer.observe(added);
  }
}, 1500);
"""


@dataclass(frozen=True)
class FakeJob:
    id: str
    title: str
    company: str = "Empresa Alfa"
    location: str = "Brasil (Remoto)"
    description: str = "Vaga para C# e ASP.NET Core."
    easy_apply: bool = True
    panel_loads: bool = True


def render_card(job: FakeJob) -> str:
    return f"""
    <div><div class="display-flex job-card-container job-card-list" data-job-id="{job.id}">
      <div class="artdeco-entity-lockup__content">
        <div class="artdeco-entity-lockup__title">
          <a class="job-card-container__link" href="/jobs/view/{job.id}/"><span><strong>{escape(job.title)}</strong></span></a>
        </div>
        <div class="artdeco-entity-lockup__subtitle"><span>{escape(job.company)}</span></div>
        <div class="artdeco-entity-lockup__caption"><ul><li><span>{escape(job.location)}</span></li></ul></div>
      </div>
    </div></div>
    """


def render_panel(job: FakeJob) -> str:
    apply_label = "Candidatura simplificada" if job.easy_apply else "Candidatar-se"
    return f"""
    <div class="job-details-jobs-unified-top-card__company-name"><a>{escape(job.company)}</a></div>
    <div class="job-details-jobs-unified-top-card__job-title"><h1><a href="/jobs/view/{job.id}/">{escape(job.title)}</a></h1></div>
    <div class="job-details-jobs-unified-top-card__tertiary-description-container"><span>
      <span class="tvm__text">Brasil</span><span class="tvm__text"> · </span><span class="tvm__text"><span>há 1 dia</span></span>
    </span></div>
    <div class="job-details-fit-level-preferences"><button><strong>Remoto</strong></button></div>
    <button class="jobs-apply-button" data-job-id="{job.id}"><span>{apply_label}</span></button>
    <div id="job-details"><p>{escape(job.description)}</p></div>
    """


def render_list_item(job: FakeJob, rendered: bool) -> str:
    return f'<li style="height: 400px" data-occludable-job-id="{job.id}">{render_card(job) if rendered else ""}</li>'


def build_search_page(jobs: list[FakeJob], rendered_cards: int, initial_items: int) -> str:
    items = "".join(render_list_item(job, position < rendered_cards) for position, job in enumerate(jobs[:initial_items]))
    late_items = "".join(render_list_item(job, False) for job in jobs[initial_items:])
    templates = "".join(f'<template id="card-{job.id}">{render_card(job)}</template>' for job in jobs)
    templates += "".join(
        f'<template id="panel-{job.id}">{render_panel(job)}</template>' for job in jobs if job.panel_loads
    )
    first_panel = render_panel(jobs[0]) if jobs and jobs[0].panel_loads else ""
    return f"""<!doctype html>
<html lang="pt-BR">
<body>
<ul>{items}</ul>
<div class="jobs-search__job-details--container" id="panel">{first_panel}</div>
{templates}
<template id="late-items">{late_items}</template>
<script>{SEARCH_PAGE_SCRIPT}</script>
</body>
</html>"""

from html import escape

from autoapply.modules.tailoring.models import EducationEntry, ExperienceEntry, ResumeDocument, SkillLine, TextRun

STYLE = """
@page { size: A4; margin: 0.99cm 1.5cm 0.85cm 1.5cm; }
* { box-sizing: border-box; }
body { margin: 0; font-family: Calibri, Carlito, "Liberation Sans", Arial, sans-serif; font-size: 10pt;
  line-height: 1.18; color: #2b2b2b; }
p { margin: 0; }
.name { font-size: 16pt; font-weight: bold; color: #1f3a5f; margin-bottom: 1pt; }
.headline { font-size: 10.5pt; color: #444444; margin-bottom: 3pt; }
.contact { font-size: 9.5pt; color: #333333; margin-bottom: 2pt; }
h2 { font-size: 11pt; font-weight: bold; text-transform: uppercase; color: #1f3a5f; margin: 5.5pt 0 1.7pt;
  padding-bottom: 1pt; border-bottom: 0.75pt solid #bbbbbb; }
.summary { margin-bottom: 1.3pt; }
.entry-header { display: flex; justify-content: space-between; align-items: baseline; margin: 4.5pt 0 0.8pt; }
.entry-title { font-size: 10.5pt; font-weight: bold; color: #222222; }
.education .entry-title { font-size: 10pt; }
.entry-period { font-size: 9.5pt; color: #444444; white-space: nowrap; padding-left: 12pt; }
.company { font-style: italic; margin-bottom: 3pt; }
.company-name { color: #1f3a5f; }
.company-detail, .institution { font-size: 9.5pt; color: #444444; }
.institution { font-style: italic; color: #1f3a5f; margin-bottom: 2pt; }
ul { margin: 0; padding-left: 18pt; list-style: disc; }
li { margin-bottom: 0.9pt; padding-left: 2pt; }
li::marker { font-size: 8pt; color: #2b2b2b; }
.lead, .label, .language-label { font-weight: bold; }
.lead { color: #1a1a1a; }
.label, .language-label { color: #1f3a5f; }
.skill { margin-bottom: 1.3pt; }
.headline, .contact, .company, .institution, .languages { white-space: pre-wrap; }
"""


def render_section(title: str, body: str) -> str:
    return f'<section><h2>{escape(title)}</h2>{body}</section>'


def render_experience(entry: ExperienceEntry) -> str:
    bullets = "".join(
        f'<li><span class="lead">{escape(bullet.lead)}</span>{escape(bullet.text)}</li>' for bullet in entry.bullets
    )
    return (
        f'<div class="entry"><div class="entry-header"><span class="entry-title">{escape(entry.title)}</span>'
        f'<span class="entry-period">{escape(entry.period)}</span></div>'
        f'<p class="company"><span class="company-name">{escape(entry.company)}</span>'
        f'<span class="company-detail">{escape(entry.company_detail)}</span></p><ul>{bullets}</ul></div>'
    )


def render_education(entry: EducationEntry) -> str:
    return (
        '<div class="entry education"><div class="entry-header">'
        f'<span class="entry-title">{escape(entry.course)}</span>'
        f'<span class="entry-period">{escape(entry.period)}</span></div>'
        f'<p class="institution">{escape(entry.institution)}</p></div>'
    )


def render_skill_line(line: SkillLine) -> str:
    return f'<p class="skill"><span class="label">{escape(line.label)}: </span>{escape(", ".join(line.items))}</p>'


def render_language_run(run: TextRun) -> str:
    text = escape(run.text)
    return f'<span class="language-label">{text}</span>' if run.bold else text


def render_resume_html(document: ResumeDocument) -> str:
    contacts = "".join(f'<p class="contact">{escape(line)}</p>' for line in document.contact_lines)
    summary = "".join(f'<p class="summary">{escape(line)}</p>' for line in document.summary.split("\n"))
    sections = [
        render_section("Resumo Profissional", summary),
        render_section("Experiência Profissional", "".join(map(render_experience, document.experiences))),
        render_section("Formação", "".join(map(render_education, document.education))),
        render_section("Competências Técnicas", "".join(map(render_skill_line, document.skill_lines))),
        render_section("Idiomas", f'<p class="languages">{"".join(map(render_language_run, document.languages))}</p>'),
    ]
    return (
        f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>{escape(document.name)}</title>'
        f"<style>{STYLE}</style></head><body>"
        f'<header><p class="name">{escape(document.name)}</p><p class="headline">{escape(document.headline)}</p>'
        f'{contacts}</header>{"".join(sections)}</body></html>'
    )

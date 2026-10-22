import sqlite3

from autoapply.modules.applying.job_answers import JOB_ANSWERS_FILE
from autoapply.modules.applying.models import PendingGroup, PendingQuestion
from autoapply.modules.applying.store import list_job_folders, list_pending_questions
from autoapply.modules.config.answers import normalize_question
from autoapply.modules.jobs.models import Job, JobStatus
from autoapply.modules.jobs.store import list_jobs

CONFIG_ANSWER_PLACE = "config.md"


def build_group(questions: list[PendingQuestion], jobs: dict[str, Job], places: dict[str, str]) -> PendingGroup:
    first = questions[0]
    job_ids = list(dict.fromkeys(question.job_id for question in questions))
    return PendingGroup(
        question=first.question,
        field_kind=first.field_kind,
        options=first.options,
        jobs=[jobs[job_id] for job_id in job_ids],
        answer_places=list(dict.fromkeys(places.get(job_id, CONFIG_ANSWER_PLACE) for job_id in job_ids)),
    )


def group_pending_questions(connection: sqlite3.Connection) -> list[PendingGroup]:
    jobs = {job.id: job for job in list_jobs(connection, JobStatus.PENDING_QUESTION)}
    places = {job_id: str(folder / JOB_ANSWERS_FILE) for job_id, folder in list_job_folders(connection).items()}
    grouped: dict[str, list[PendingQuestion]] = {}
    for question in list_pending_questions(connection):
        if question.job_id in jobs:
            grouped.setdefault(normalize_question(question.question), []).append(question)
    groups = [build_group(questions, jobs, places) for questions in grouped.values()]
    return sorted(groups, key=lambda group: len(group.jobs), reverse=True)

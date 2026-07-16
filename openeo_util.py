import os
import time


ACTIVE_JOB_STATUSES = {"queued", "running"}
JOB_SCHEDULING_POLL_INTERVAL_SECONDS = int(os.getenv("OPENEO_JOB_SCHEDULING_POLL_INTERVAL_SECONDS", "15"))
MAX_PARALLEL_ACTIVE_JOBS = int(os.getenv("OPENEO_MAX_PARALLEL_ACTIVE_JOBS", "5"))
JOB_LISTING_LIMIT = None


def get_active_backend_jobs(conn):
    active_jobs = []
    for job_metadata in conn.list_jobs(limit=JOB_LISTING_LIMIT):
        status = job_metadata.get("status")
        if status in ACTIVE_JOB_STATUSES:
            active_jobs.append(job_metadata)

    return active_jobs


def wait_until_below_active_job_limit(conn) -> None:
    while True:
        active_jobs = get_active_backend_jobs(conn)
        if len(active_jobs) < MAX_PARALLEL_ACTIVE_JOBS:
            return

        active_job_ids = ", ".join(
            f"{job_metadata.get('id', 'unknown')} ({job_metadata.get('status')})"
            for job_metadata in active_jobs
        )
        print(
            "Waiting to schedule next openEO job. "
            f"{len(active_jobs)} active jobs for this authenticated openEO account "
            f"(limit: {MAX_PARALLEL_ACTIVE_JOBS}): {active_job_ids}"
        )
        time.sleep(JOB_SCHEDULING_POLL_INTERVAL_SECONDS)


def get_backend_version(conn):
    """
    Returns the openEO API version implemented by the connected backend
    (e.g. "1.2.0"), or None if the capabilities document can't be fetched.
    """
    try:
        return conn.capabilities().api_version()
    except Exception as e:
        print(f"could not fetch openEO backend version! {e}")
        return None


def configure_batch_job_tracking(conn, jobs):
    def create_job_logged(*args, **kwargs):
        job = conn.create_job_orig(*args, **kwargs)
        print(f"Tracking execution for job: {job.job_id}")
        job.start_orig = job.start

        def start_job_waiting(*start_args, **start_kwargs):
            wait_until_below_active_job_limit(conn)
            return job.start_orig(*start_args, **start_kwargs)

        # start_and_wait() delegates to start(), while some callers might still use the legacy start_job().
        job.start = start_job_waiting
        job.start_job = start_job_waiting
        jobs.append(job)
        return job

    conn.execute = None  # We prevent sync execution until we have it logged
    conn.create_job_orig = conn.create_job
    conn.create_job = create_job_logged  # log all batch jobs to enable tracking

    return conn

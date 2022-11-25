import sys
sys.path.append("./dependencies")

from pytz import utc

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.base import JobLookupError
from apscheduler.triggers.date import DateTrigger

class Scheduler(object):
    jobstores = {
        'default': RedisJobStore(jobs_key='dispatched_trips_jobs', run_times_key='dispatched_trips_running', host='localhost', port=6379)
    }

    executors = {
        'default': ThreadPoolExecutor(20)
    }

    job_defaults = {
        'coalesce': False,
        'max_instances': 3
    }

    def __init__(self) -> None:
        self.scheduler = BackgroundScheduler(
            jobstores=self.jobstores,
            executors=self.executors,
            job_defaults=self.job_defaults,
            timezone=utc
        )

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        print("Shuting down Scheduler...")
        self.scheduler.shutdown()

    def start(self):
        self.scheduler.start()

    def add(self, callback, server, datetime):
        existing_jobs = self.get_jobs_by_server(server)

        if len(existing_jobs) > 0:
            message = "Job '%s' for '%s' already scheduled for '%s'." % (existing_jobs[server]["id"], server, existing_jobs[server]["scheduledDateTime"])
            print(message)
            return { "status": "failed", "statusMessage": message }

        trigger = DateTrigger(
            run_date=datetime
        )
        
        message = "Added Job for server '%s' to run at '%s'." % (server, datetime)
        self.scheduler.add_job(callback, trigger=trigger, args=[server])
        print(message)

        return { "status": "success", "statusMessage": message }

    def delete(self, id):
        try:
            self.scheduler.remove_job(id)
            print("Job '%s' deleted." % id)
            return { "status": "success", "statusMessage": "Job '%s' deleted." % id }
        except JobLookupError as err:
            print("Job not found: " + id)
            return { "status": "failed", "statusMessage": "Job not found: " + id }

    def list(self):
        return self.get_jobs()

    def get_jobs(self):
        jobdict = {}

        for job in self.scheduler.get_jobs():
            jobdict[job.id] = {
                "server": job.args[0],
                "scheduledDateTime": job.next_run_time
            }

        return jobdict

    def get_job(self, id):
        jobdict = {}

        for job in [self.scheduler.get_job(id)]:
            jobdict[job.id] = {
                "server": job.args[0],
                "scheduledDateTime": job.next_run_time
            }

        return jobdict

    def get_jobs_by_server(self, server):
        jobdict = {}

        for job in self.scheduler.get_jobs():
            if job.args[0] == server:
                jobdict[job.id] = {
                    "server": job.args[0],
                    "scheduledDateTime": job.next_run_time
                }

        return jobdict

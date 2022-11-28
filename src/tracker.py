import redis
import sys
sys.path.append("./dependencies")

from redis.commands.json.path import Path

class Tracker(object):
    def __init__(self) -> None:
        print("Connecting to Redis...")
        self.connection = redis.Redis(port=55000)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        print("Shuting down Tracker...")

    def set(self, job_id, status, datetime):
        message = "Status update for job '%s': '%s' at '%s'." % (
            job_id, status, datetime)

        job = {
            "status": status,
            "statusDatetime": datetime
        }

        self.connection.json().set(f"job:{job_id}", Path.root_path(), job)
        self.connection.bgsave()

        print(message)

        return {"status": "success", "statusMessage": message}

    def get(self, job_id):
        result = self.connection.json().get(f"job:{job_id}")

        if result is not None:
            result["jobId"] = job_id

        print(result)

        return result

    def get_all(self):
        result = []

        for key in self.connection.scan_iter("job:*"):
            job = self.connection.json().get(key.decode("utf-8"))
            job["jobId"] = key.decode("utf-8").split(":")[1]

            result.append(job)

        print(result)

        return result
import sys
sys.path.append("./dependencies")

import json
import jsonschema
import os
import redis

from jsonschema import validate

from queue_helper import Queue
from tracker import Tracker

def send_job(server):
    patching_queue_name = "rhel-patching"
    print(server)

class Main(object):
    
    tracking_queue_name = "rhel-patching.jobtracker"

    def __init__(self) -> None:
        print("Loading validation schema...")
        self.payloadSchema = self.get_validation_schema()

        print("Starting Queue Listener...")
        self.tracking_queue = Queue(
            self.tracking_queue_name,
            self.process_message
        )

        self.tracker = Tracker()
        self.tracking_queue.start()

    def get_validation_schema(self):
        with open('%s/schemas/default.json' % os.path.dirname(__file__), 'r') as f:
            schema_data = f.read()

        return json.loads(schema_data)

    def process_message(self, channel, method_frame, properties, body):
        print(" [x] Received %r" % body)

        message_is_valid, validation_message = self.message_valid(body)

        if message_is_valid:
            payload = json.loads(body)

            try:
                if payload["action"] == "set":
                    return_payload = self.tracker.set(payload["jobId"], payload["status"], payload["statusDateTime"])
                elif payload["action"] == "get":
                    if "jobId" in payload:
                        return_payload = self.tracker.get(payload["jobId"])
                    else:
                        return_payload = self.tracker.get_all()
                else:
                    return_payload = { "status": "failed", "message": "Unknown action: " + payload["action"] }
            except redis.exceptions.ConnectionError as err:
                return_payload = { "status": "retry", "message": err.args[0] }
        else:
            return_payload = { "status": "failed", "message": validation_message}

        if "status" in return_payload and return_payload["status"] == "failed":
            self.tracking_queue.reject(False, method_frame.delivery_tag)
        elif "status" in return_payload and return_payload["status"] == "retry":
            self.tracking_queue.reject(False, method_frame.delivery_tag)
        else:
            self.tracking_queue.accept(method_frame.delivery_tag)
        
        print(json.dumps(return_payload, sort_keys=True, indent=4, separators=(',', ': '), default=str))

    def message_valid(self, message):
        try:
            payload = json.loads(message)
        except ValueError as err:
            message = "Invalid JSON message: " + message.decode("utf8")
            return False, message

        try:
            validate(
                instance=payload,
                schema=self.payloadSchema,
                format_checker=jsonschema.FormatChecker()
            )
        except Exception as err:
            message = "Invalid message passed: " + err.message
            print("Payload: " + json.dumps(payload, sort_keys=True, indent=4, separators=(',', ': '), default=str))
            return False, message

        return True, None
        
if __name__ == "__main__":
    main = Main()
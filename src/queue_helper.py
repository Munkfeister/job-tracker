from gc import callbacks
import queue
import pika

class Queue(object):

    def __init__(self, queue, callback):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters("localhost"))
        self.channel = self.connection.channel()
        
        self.channel.exchange_declare("dlx", "fanout")
        self.channel.queue_declare("dead_letter_queue")

        self.channel.queue_declare(queue=queue)
        self.channel.basic_consume(
            queue=queue,
            auto_ack=False,
            on_message_callback=callback,
            arguments={
                "x-dead-letter-exchange": "dlx"
            }
        )

    def start(self):
        print("Waiting for messages...")
        self.channel.start_consuming()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        print("Shuting down Queue...")
        self.connection.close()

    def reject(self, requeue, delivery_tag):
        print(" [*] Sending rejection to RabbitMQ. Requeue: " + str(requeue))
        self.channel.basic_reject(delivery_tag=delivery_tag, requeue=requeue)

    def accept(self, delivery_tag):
        print(" [*] Sending success to RabbitMQ")
        self.channel.basic_ack(delivery_tag=delivery_tag)

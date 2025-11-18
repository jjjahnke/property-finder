import os
import pika
import json
import logging
from sqlalchemy import create_engine, text
import time

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [CONSUMER] - %(message)s')

# RabbitMQ connection details
RABBITMQ_USER = os.getenv('RABBITMQ_DEFAULT_USER', 'user')
RABBITMQ_PASS = os.getenv('RABBITMQ_DEFAULT_PASS', 'password')
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
RABBITMQ_URL = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}/"
EXCHANGE_NAME = 'property_events_exchange'
QUEUE_NAME = 'property_events_queue'
ROUTING_KEY = 'property.event.sale'

# Database connection details
DB_USER = os.getenv('POSTGRES_USER', 'user')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', 'timescaledb')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'property_finder')
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- Main Consumer Logic ---

def get_db_connection():
    """Establishes and returns a database connection."""
    while True:
        try:
            engine = create_engine(DATABASE_URL)
            connection = engine.connect()
            logging.info("Successfully connected to the database.")
            return connection
        except Exception as e:
            logging.error(f"Failed to connect to the database: {e}. Retrying in 5 seconds...")
            time.sleep(5)

def setup_rabbitmq():
    """Sets up RabbitMQ connection, channel, exchange, and queue."""
    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            channel = connection.channel()
            channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='topic', durable=True)
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            channel.queue_bind(exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key=ROUTING_KEY)
            channel.basic_qos(prefetch_count=1) # Process one message at a time
            logging.info("Successfully connected to RabbitMQ and set up channel.")
            return connection, channel
        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"Failed to connect to RabbitMQ: {e}. Retrying in 5 seconds...")
            time.sleep(5)

def main():
    """Main function to consume messages and insert them into the database."""
    db_connection = get_db_connection()
    mq_connection, channel = setup_rabbitmq()

    def callback(ch, method, properties, body):
        """Callback function to process a message."""
        try:
            event_data = json.loads(body)
            logging.info(f"Received event for parcel_id: {event_data.get('parcel_id')}")

            # Prepare the insert statement
            stmt = text("""
                INSERT INTO property_events (parcel_id, event_type, event_date, data, source)
                VALUES (:parcel_id, :event_type, :event_date, :data, :source)
            """)
            
            # Execute the insert
            db_connection.execute(stmt, {
                "parcel_id": event_data.get('parcel_id'),
                "event_type": event_data.get('event_type'),
                "event_date": event_data.get('event_date'),
                "data": json.dumps(event_data.get('data')), # Ensure data is a JSON string
                "source": event_data.get('source')
            })
            db_connection.commit() # Commit the transaction

            logging.info(f"Successfully inserted event for parcel_id: {event_data.get('parcel_id')}")
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON message: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False) # Discard malformed message
        except Exception as e:
            logging.error(f"An error occurred processing message: {e}")
            # Requeue the message to be tried again later
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            # A more robust solution might use a dead-letter queue.

    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    try:
        logging.info('Waiting for messages. To exit press CTRL+C')
        channel.start_consuming()
    except KeyboardInterrupt:
        logging.info("Shutting down consumer...")
    finally:
        mq_connection.close()
        db_connection.close()
        logging.info("Connections closed.")

if __name__ == '__main__':
    main()

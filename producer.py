import os
import pandas as pd
import pika
import json
import logging
import zipfile
import glob

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# RabbitMQ connection details from environment variables
RABBITMQ_USER = os.getenv('RABBITMQ_DEFAULT_USER', 'user')
RABBITMQ_PASS = os.getenv('RABBITMQ_DEFAULT_PASS', 'password')
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq') # Use the service name from docker-compose
RABBITMQ_URL = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}/"
EXCHANGE_NAME = 'property_events_exchange'
QUEUE_NAME = 'property_events_queue'
ROUTING_KEY = 'property.event.sale'

DATA_DIR = '/app/data'

# --- Main Producer Logic ---

def find_csv_zip_path():
    """Finds the first file ending with 'CSV.zip' in the data directory."""
    search_pattern = os.path.join(DATA_DIR, '*CSV.zip')
    zip_files = glob.glob(search_pattern)
    if not zip_files:
        logging.error(f"No '*CSV.zip' file found in {DATA_DIR}")
        return None
    if len(zip_files) > 1:
        logging.warning(f"Multiple CSV.zip files found. Using the first one: {zip_files[0]}")
    return zip_files[0]

def publish_events():
    """
    Reads property event data from a CSV.zip file and publishes each event
    to a RabbitMQ exchange.
    """
    logging.info("Starting event producer...")

    csv_zip_path = find_csv_zip_path()
    if not csv_zip_path:
        return

    logging.info(f"Found CSV zip file: {csv_zip_path}")

    try:
        # Pandas can read directly from a zip archive
        with zipfile.ZipFile(csv_zip_path, 'r') as z:
            # Find the first CSV file in the zip archive
            csv_filename = next((f for f in z.namelist() if f.lower().endswith('.csv')), None)
            if not csv_filename:
                logging.error(f"No CSV file found inside {csv_zip_path}")
                return
            
            logging.info(f"Reading CSV file: {csv_filename}")
            with z.open(csv_filename) as f:
                df = pd.read_csv(f, low_memory=False, encoding='latin-1')

        logging.info(f"Successfully read {len(df)} rows from the CSV.")
        logging.info(f"Original columns: {df.columns.tolist()}")

    except Exception as e:
        logging.error(f"Failed to read or process CSV file: {e}")
        return

    # --- RabbitMQ Connection Setup ---
    try:
        logging.info(f"Connecting to RabbitMQ at {RABBITMQ_HOST}...")
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        channel = connection.channel()

        # Declare a durable exchange
        channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='topic', durable=True)
        # Declare a durable queue
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        # Bind the queue to the exchange with the routing key
        channel.queue_bind(exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key=ROUTING_KEY)

        logging.info("Successfully connected to RabbitMQ and declared exchange/queue.")

    except pika.exceptions.AMQPConnectionError as e:
        logging.error(f"Failed to connect to RabbitMQ: {e}")
        return

    # --- Data Transformation & Publishing ---
    # This section will likely need adjustment based on the actual CSV schema.
    # Making assumptions for now.
    column_mapping = {
        'PropertyID': 'parcel_id',
        'DocumentDate': 'event_date',
    }
    
    # Rename columns for consistency
    df_renamed = df.rename(columns=column_mapping)

    required_cols = ['parcel_id', 'event_date']
    if not all(col in df_renamed.columns for col in required_cols):
        logging.error(f"Missing one or more required columns after mapping: {required_cols}")
        logging.error(f"Available columns: {df_renamed.columns.tolist()}")
        return

    # Convert all columns to a dictionary-friendly format
    # Replace NaN with None for clean JSON conversion
    df_renamed = df_renamed.where(pd.notnull(df_renamed), None)
    
    logging.info("Starting to publish events...")
    published_count = 0
    for index, row in df_renamed.iterrows():
        try:
            # Convert the entire row to a dictionary for the 'data' payload
            row_data = row.to_dict()

            # Construct the event message
            event_data = {
                'parcel_id': row['parcel_id'],
                'event_type': 'sale', # Hardcoded for now
                'event_date': pd.to_datetime(row['event_date']).isoformat(),
                'source': 'RETR_CSV',
                'data': row_data # Include the full row data
            }

            message_body = json.dumps(event_data, default=str) # Use default=str to handle any non-serializable types

            # Publish the message
            channel.basic_publish(
                exchange=EXCHANGE_NAME,
                routing_key=ROUTING_KEY,
                body=message_body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                ))
            published_count += 1
            if published_count % 1000 == 0:
                 logging.info(f"Published {published_count} events...")

        except Exception as e:
            logging.warning(f"Failed to process or publish row {index}: {e}")
            logging.warning(f"Row data: {row.to_dict()}")

    # --- Cleanup ---
    connection.close()
    logging.info(f"Finished publishing. Total events published: {published_count}")

if __name__ == "__main__":
    publish_events()

from datetime import datetime, timezone, timedelta

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from kafka import KafkaProducer
import json


def unix_to_datetime(timestamp):
    """
    Converts a Unix timestamp to a datetime object.

    Args:
    - timestamp (float): Unix timestamp in seconds.

    Returns:
    - datetime: Datetime object representing the corresponding date and time.
    """
    return datetime.utcfromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')


def datetime_to_unix(date_string):
    # Convert the input string to a datetime object
    date_object = datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')

    # Calculate the Unix timestamp in seconds
    unix_timestamp = int(date_object.replace(tzinfo=timezone.utc).timestamp())

    # Convert to milliseconds
    unix_milliseconds = unix_timestamp * 1000

    return unix_milliseconds


def unix_to_date(timestamp):
    """
    Converts a Unix timestamp to a datetime object.

    Args:
    - timestamp (float): Unix timestamp in seconds.

    Returns:
    - datetime: Datetime object representing the corresponding date.
    """
    return datetime.utcfromtimestamp(timestamp / 1000).strftime('%Y-%m-%d')


def unix_to_time(timestamp):
    """
    Converts a Unix timestamp to a datetime object.

    Args:
    - timestamp (float): Unix timestamp in seconds.

    Returns:
    - time: time object representing the corresponding time.
    """
    return datetime.utcfromtimestamp(timestamp / 1000).strftime('%H:%M:%S')


def sendKafkaProducer(value):
    # Create a KafkaProducer instance
    producer = KafkaProducer(bootstrap_servers='localhost:9092',
                             value_serializer=lambda v: json.dumps(v).encode('utf-8'))

    # Send a JSON-encoded message to the 'candlestickStream' topic
    producer.send('candlestickStream', value={'data': value})

    # Flush messages to ensure they are sent immediately
    producer.flush()

    # Close the producer
    producer.close()


def castToDataType(data):
    # Transforming data types
    transformed_data = [
        # EVENT_TIME TIMESTAMP
        datetime.strptime(data[0], '%Y-%m-%d %H:%M:%S'),
        data[1],  # SYMBOL TEXT
        float(data[2]),  # OPEN DOUBLE
        float(data[3]),  # CLOSE DOUBLE
        float(data[4]),  # HIGH DOUBLE
        float(data[5]),  # LOW DOUBLE
        # START_TIME TIMESTAMP
        datetime.strptime(data[6], '%Y-%m-%d %H:%M:%S'),
        # CLOSE_TIME TIMESTAMP
        datetime.strptime(data[7], '%Y-%m-%d %H:%M:%S'),
        float(data[8]),  # BASE_ASSET_VOLUME DOUBLE
        int(data[9]),  # NUMBER_OF_TRADES INT
        float(data[10]),  # QUOTE_ASSET_VOLUME DOUBLE
        # KLINE_CLOSED BOOLEAN (convert 'False' to False, everything else to True)
        data[11] == 'True'
    ]

    return (transformed_data)


def insert_data_candlesticks(data):
    # Establish a connection to the Cassandra cluster
    cluster = Cluster(['localhost'], port=9042)
    session = cluster.connect()

    # Switch to your keyspace
    session.set_keyspace('dmsb_tfm')

    # Insert data
    insert_query = session.prepare("""
        INSERT INTO candlesticks (
            EVENT_TIME,
            SYMBOL,
            OPEN,
            CLOSE,
            HIGH,
            LOW,
            START_TIME,
            CLOSE_TIME,
            BASE_ASSET_VOLUME,
            NUMBER_OF_TRADES,
            QUOTE_ASSET_VOLUME,
            KLINE_CLOSED
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """)

    result = 'Data inserted'
    # Execute the insertion query
    try:
        session.execute(insert_query, data)
    except Exception as e:
        # print(f"An error occurred while inserting data: {e}")
        result = f'Error inserting data: {e}'

    # Close the connection
    cluster.shutdown()
    return result

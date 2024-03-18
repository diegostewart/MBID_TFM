from kafka import KafkaProducer
from cassandra.cluster import Cluster
import json
import time
from statsmodels.tsa.arima.model import ARIMA
import pandas as pd

#################################################################################################
# OPEN 2 GIT BASH CONSOLES AND RUN ()
# context/kafka/bin/zookeeper-server-start.sh context/kafka/config/zookeeper.properties
# context/kafka/bin/kafka-server-start.sh context/kafka/config/server.properties
#################################################################################################

# Set up Kafka producer
producer = KafkaProducer(bootstrap_servers='localhost:9092',
                         value_serializer=lambda v: json.dumps(v).encode('utf-8'))

# Set up Cassandra connection
cluster = Cluster(['localhost'], port=9042)
session = cluster.connect()
session.set_keyspace('dmsb_tfm')

# Initialize variable to store the timestamp or identifier of the last processed row

try:
    while True:
        # Execute Cassandra query
        query = "SELECT * FROM candlesticks LIMIT 1000"
        result = session.execute(query)
        rows = [row._asdict() for row in result]

        # This is the df from our table. It is ordered by event_time as designed in cassandra
        df_candlesticks = pd.DataFrame(rows)

        # We get the time used for the prediction:
        df_prediction_start_time = df_candlesticks['start_time']
        prediction_start_time = df_prediction_start_time.iloc[0]

        # Filter only the ended candles to permorm our model
        df_kline_closed = df_candlesticks[df_candlesticks['kline_closed'] == True]

        # Used to limit the amount of rows applied to ARIMA
        df_kline_closed = df_kline_closed.head(20)

        print(len(df_kline_closed))
        # Create our each df
        df_close = df_kline_closed[['start_time', 'close']]
        df_open = df_kline_closed[['start_time', 'open']]
        df_high = df_kline_closed[['start_time', 'high']]
        df_low = df_kline_closed[['start_time', 'low']]

        # Create the ARIMA model
        close_model = ARIMA(df_close['close'].tolist(), order=(4, 1, 0))
        open_model = ARIMA(df_open['open'].tolist(), order=(4, 1, 0))
        high_model = ARIMA(df_high['high'].tolist(), order=(4, 1, 0))
        low_model = ARIMA(df_low['low'].tolist(), order=(4, 1, 0))

        # Fit the model
        close_model_fit = close_model.fit()
        open_model_fit = open_model.fit()
        high_model_fit = high_model.fit()
        low_model_fit = low_model.fit()

        # Get our predictions.
        close_prediction = close_model_fit.forecast()[0]
        open_prediction = open_model_fit.forecast()[0]
        high_prediction = high_model_fit.forecast()[0]
        low_prediction = low_model_fit.forecast()[0]

        # Send data to Kafka topic
        # Convert row to a dictionary (or any format suitable for your use case)
        message = {'start_time': str(prediction_start_time), 'open': open_prediction,
                   'high': high_prediction, 'low': low_prediction, 'close': close_prediction}

        # Send the message to Kafka topic
        print(message)
        future = producer.send('candlestickStream', value=message)
        # Get the result of the send operation
        # Wait for up to 60 seconds for the send operation to complete
        result = future.get(timeout=60)
        print("Message sent:", result)
        print("-----------------------")

        # Flush messages to ensure they are sent immediately
        producer.flush()
        time.sleep(3)

except KeyboardInterrupt:
    # Close connections if the program is terminated by a keyboard interrupt (Ctrl+C)
    producer.close()
    session.shutdown()
    cluster.shutdown()
    print('All connections have been closed')

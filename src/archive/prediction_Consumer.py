from kafka import KafkaConsumer
import json
from functions import insert_data_candlesticks, castToDataType

#################################################################################################
# OPEN 2 GIT BASH CONSOLES AND RUN ()
# context/kafka/bin/zookeeper-server-start.sh context/kafka/config/zookeeper.properties
# context/kafka/bin/kafka-server-start.sh context/kafka/config/server.properties
#################################################################################################

# Set up Kafka consumer
consumer = KafkaConsumer('candlestickStream', bootstrap_servers='localhost:9092', group_id='btceur3', enable_auto_commit=True,  # Enable automatic offset commits
                         auto_commit_interval_ms=5000)

# Continuously poll for records and process them
for message in consumer:
    # Decode and deserialize the message value
    value = json.loads(message.value.decode('utf-8'))
    # print(f"Received message: value={value}")
    print(value['data'])

    # We insert the data into our table:
    # try:
    #     insert_data_candlesticks(castToDataType(value['data']))
    # except:
    #     print('ERROR')

# Close consumer
consumer.close()

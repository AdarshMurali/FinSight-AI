FROM apache/flink:1.18-scala_2.12-java11

# Install Python 3 (not included in the base Flink image)
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends python3 python3-pip python3-dev && \
    rm -rf /var/lib/apt/lists/* && \
    ln -sf /usr/bin/python3 /usr/bin/python

# Copy pre-downloaded Kafka SQL connector JAR (avoids network fetch at build time)
COPY flink-sql-connector-kafka-3.1.0-1.18.jar /opt/flink/lib/

# Install PyFlink (must match cluster version 1.18) and streaming dependencies
RUN pip3 install --no-cache-dir \
    apache-flink==1.18.0 \
    kafka-python==2.0.2 \
    chromadb>=0.5.0 \
    openai>=1.40.0 \
    vaderSentiment==3.3.2 \
    python-dotenv==1.0.1 \
    requests==2.32.3

#!/bin/bash

# List of dependencies to check and install
dependencies=("curl" "tar" "java")

# Function to check if a command is available
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install a package
install_package() {
    if command_exists "apt-get"; then
        sudo apt-get update
        sudo apt-get install -y "$1"
    elif command_exists "yum"; then
        sudo yum install -y "$1"
    else
        echo "Unsupported package manager. Please install $1 manually."
        exit 1
    fi
}

# Function to download and extract a binary archive
download_and_extract() {
    URL=$1
    DIR=$2

    # Download
    curl -k -O "$URL"

    # Extract
    tar -xvf "$(basename $URL)"

    # Rename the extracted directory
    mv "$(tar -tf $(basename $URL) | head -1 | cut -f 1 -d '/')" "dependencies/$DIR"

    # Clean up downloaded archive
    rm "$(basename $URL)"
}

# Check and install dependencies
for dep in "${dependencies[@]}"; do
    if ! command_exists "$dep"; then
        echo "$dep is not installed. Installing..."
        install_package "$dep"
    else
        echo "$dep is already installed."
    fi
done

# Install ZooKeeper
echo "Installing ZooKeeper..."
download_and_extract "https://dlcdn.apache.org/zookeeper/zookeeper-3.8.3/apache-zookeeper-3.8.3-bin.tar.gz" "zookeeper"

# Install Kafka
echo "Installing Kafka..."
download_and_extract "https://dlcdn.apache.org/kafka/3.6.1/kafka_2.13-3.6.1.tgz" "kafka"

echo "All dependencies, ZooKeeper, and Kafka are installed."

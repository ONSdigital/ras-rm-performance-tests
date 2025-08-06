import json
import time

import requests
import os
from concurrent.futures import TimeoutError

from google.cloud import pubsub_v1

project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
subscription_id = os.getenv('PUBSUB_SUBSCRIPTION_ID')
environment_base_url = os.getenv('ENVIRONMENT_BASE_URL', 'http://localhost:8082')

# Number of seconds the subscriber should listen for messages
timeout = 180.0

subscriber = pubsub_v1.SubscriberClient()
# The `subscription_path` method creates a fully qualified identifier
# in the form `projects/{project_id}/subscriptions/{subscription_id}`
subscription_path = subscriber.subscription_path(project_id, subscription_id)


def callback(message: pubsub_v1.subscriber.message.Message) -> None:
    print(f"Received {message}.")
    data = json.loads(message.data.decode("utf-8"))
    source_url = data["notify"]["personalisation"]["ACCOUNT_VERIFICATION_URL"]
    print(source_url)
    url = source_url.replace("http://localhost:8080", environment_base_url)
    print(url)
    start = time.time()
    response = requests.get(url)
    latency = time.time() - start
    print(f"Status code: {response.status_code}")
    if "You've activated your account" not in response.text:
        print("Activation text not found in response page.")
    else:
        print("Account successfully activated.")
    print(f"Request latency: {latency:.3f} seconds")
    message.ack()


streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
print(f"Listening for messages on {subscription_path}..\n")

# Wrap subscriber in a 'with' block to automatically call close() when done.
with subscriber:
    try:
        # When `timeout` is not set, result() will block indefinitely,
        # unless an exception is encountered first.
        streaming_pull_future.result(timeout=timeout)
    except TimeoutError:
        streaming_pull_future.cancel()  # Trigger the shutdown.
        streaming_pull_future.result()  # Block until the shutdown is complete.

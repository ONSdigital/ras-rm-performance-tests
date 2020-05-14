from locust import HttpLocust, TaskSet, task, events, between
import datetime
import sys
from .dataloader import load_data

# This will only be run on Master and should be used for loading test data
if '--master' in sys.argv:
  load_data()

class FrontstageTasks(TaskSet):
  @task(1)
  def status(self):
    response = self.client.get("/sign-in")

class FrontstageLocust(HttpLocust):
  task_set = FrontstageTasks
  wait_time = between(5, 15)
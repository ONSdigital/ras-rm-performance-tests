from locust import HttpLocust, TaskSet, task, events, between
import datetime
import logging
import sys

# This will only be run on Master and should be used for loading test data
if '--master' in sys.argv:
  logger = logging.getLogger()
  logger.info('This is a setup line')

class ElbTasks(TaskSet):
  @task(1)
  def status(self):
    response = self.client.get("/sign-in")

class ElbWarmer(HttpLocust):
  task_set = ElbTasks
  wait_time = between(5, 15)